"""Storage target resolution with transparent local fallback."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from cryptavault.storage.base import StorageConnector
from cryptavault.storage.cloud.dropbox import DropboxStorage
from cryptavault.storage.cloud.gdrive import GoogleDriveStorage
from cryptavault.storage.cloud.onedrive import OneDriveStorage
from cryptavault.storage.local import LocalStorage
from cryptavault.storage.s3 import S3Storage
from sqlalchemy import select
from sqlalchemy.orm import Session

from cryptavault_api.models import StorageTarget, Workspace
from cryptavault_api.secrets import decrypt_config
from cryptavault_api.settings import settings


@dataclass(frozen=True)
class StoredObject:
    target: str
    key: str
    size: int
    etag: str | None = None


def connector_for(target: StorageTarget) -> StorageConnector:
    """Build a connector from an encrypted target record."""
    config: dict[str, Any] = decrypt_config(target.config_json)
    if target.kind == "local":
        return LocalStorage(config.get("root", str(settings.local_storage_path)))
    if target.kind == "s3":
        return S3Storage(
            bucket_name=str(config.get("bucket", "cryptavault")),
            endpoint_url=str(config.get("endpoint", "")),
            access_key_id=str(config.get("access_key", "")),
            secret_access_key=str(config.get("secret_key", "")),
            region_name=str(config.get("region", "us-east-1")),
            force_path_style=bool(config.get("path_style", True)),
        )
    if target.kind == "gdrive":
        return GoogleDriveStorage(
            credentials_file=config.get("credentials_file"),
            token_file=config.get("token_file"),
            folder_id=config.get("folder_id"),
        )
    if target.kind == "dropbox":
        return DropboxStorage(
            access_token=config.get("access_token"),
            refresh_token=config.get("refresh_token"),
            app_key=config.get("app_key"),
            app_secret=config.get("app_secret"),
        )
    if target.kind == "onedrive":
        return OneDriveStorage(
            client_id=config.get("client_id"),
            client_secret=config.get("client_secret"),
            tenant_id=config.get("tenant_id"),
            root_folder=str(config.get("root_folder", "CryptaVault")),
        )
    raise ValueError(f"Unsupported storage target kind: {target.kind}")


def _ordered_targets(db: Session, workspace: Workspace) -> list[StorageTarget]:
    targets = list(db.scalars(select(StorageTarget).where(StorageTarget.enabled.is_(True))).all())
    by_name = {target.name: target for target in targets}
    ordered: list[StorageTarget] = []
    if workspace.storage_target and workspace.storage_target in by_name:
        ordered.append(by_name[workspace.storage_target])
    for target in targets:
        if target.is_default and target not in ordered:
            ordered.append(target)
    for target in targets:
        if target.kind == "local" and target not in ordered:
            ordered.append(target)
    for target in sorted(targets, key=lambda item: item.name):
        if target not in ordered:
            ordered.append(target)
    return ordered


def upload_ciphertext(
    db: Session,
    workspace: Workspace,
    storage_key: str,
    payload: bytes,
    *,
    preferred_target: str | None = None,
) -> StoredObject:
    """Upload ciphertext to the first healthy target, falling back to local disk."""
    targets = _ordered_targets(db, workspace)
    if preferred_target:
        preferred = [t for t in targets if t.name == preferred_target]
        targets = preferred + [t for t in targets if t.name != preferred_target]
    errors: list[str] = []
    for target in targets:
        try:
            connector = connector_for(target)
            connector.authenticate()
            uri = connector.upload(io.BytesIO(payload), storage_key, size=len(payload))
            etag = uri.rsplit("/", 1)[-1] if uri else None
            return StoredObject(
                target=target.name,
                key=storage_key,
                size=len(payload),
                etag=etag,
            )
        except Exception as exc:
            errors.append(f"{target.name}: {exc}")
    raise ConnectionError("All storage targets failed: " + " | ".join(errors))


def download_ciphertext(db: Session, target_name: str, storage_key: str) -> tuple[io.BytesIO, str]:
    """Return ciphertext bytes and the resolved target name."""
    target = db.get(StorageTarget, target_name)
    if target is None:
        raise FileNotFoundError(f"Storage target '{target_name}' is not configured.")
    connector = connector_for(target)
    connector.authenticate()
    stream = connector.download(storage_key)
    return io.BytesIO(stream.read()), target.name


def delete_ciphertext(db: Session, target_name: str, storage_key: str) -> bool:
    target = db.get(StorageTarget, target_name)
    if target is None:
        return False
    try:
        connector = connector_for(target)
        connector.authenticate()
        return connector.delete(storage_key)
    except Exception:
        return False


def test_target(target: StorageTarget) -> dict[str, Any]:
    try:
        connector = connector_for(target)
        connector.authenticate()
        return {"name": target.name, "ok": True, "kind": target.kind}
    except Exception as exc:
        return {"name": target.name, "ok": False, "kind": target.kind, "error": str(exc)}
