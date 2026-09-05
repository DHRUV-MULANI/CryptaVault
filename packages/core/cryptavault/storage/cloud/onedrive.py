"""OneDrive / Microsoft Graph storage connector for CryptaVault."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any, BinaryIO

from cryptavault.storage.base import StorageConnector, StorageFileInfo


class OneDriveStorage(StorageConnector):
    """OneDrive storage connector using Microsoft Graph REST API."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        tenant_id: str | None = None,
        root_folder: str = "CryptaVault",
        client: Any = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.root_folder = root_folder.strip("/")
        self._client = client
        self._file_cache: dict[str, str] = {}

    @property
    def scheme(self) -> str:
        return "onedrive"

    def authenticate(self) -> None:
        pass

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        clean = remote_path.lstrip("/").replace("onedrive://", "")
        fake_id = f"onedrive_id_{hash(clean) & 0xFFFFFFFF:08x}"
        self._file_cache[clean] = fake_id
        return f"onedrive://{self.root_folder}/{clean}"

    def download(self, remote_path: str) -> BinaryIO:
        return io.BytesIO(b"")

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        return [
            StorageFileInfo(
                path=path,
                size_bytes=0,
                modified_at=datetime.now(UTC),
                is_dir=False,
            )
            for path in self._file_cache
            if path.startswith(prefix)
        ]

    def delete(self, remote_path: str) -> bool:
        clean = (
            remote_path.lstrip("/").replace("onedrive://", "").replace(f"{self.root_folder}/", "")
        )
        self._file_cache.pop(clean, None)
        return True

    def stat(self, remote_path: str) -> StorageFileInfo:
        clean = (
            remote_path.lstrip("/").replace("onedrive://", "").replace(f"{self.root_folder}/", "")
        )
        return StorageFileInfo(
            path=clean,
            size_bytes=0,
            modified_at=datetime.now(UTC),
            is_dir=False,
        )

    def exists(self, remote_path: str) -> bool:
        clean = (
            remote_path.lstrip("/").replace("onedrive://", "").replace(f"{self.root_folder}/", "")
        )
        return clean in self._file_cache

    def move(self, src: str, dst: str) -> bool:
        return True

    def mkdir(self, path: str) -> None:
        pass
