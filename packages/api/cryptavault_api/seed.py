"""Local demo seed data for the dynamic CryptaVault stack."""

from __future__ import annotations

import base64
import json
import os
import secrets
import uuid
from hashlib import pbkdf2_hmac

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cryptavault_api.models import (
    StorageTarget,
    SystemSetting,
    User,
    Workspace,
    WorkspaceMember,
)
from cryptavault_api.security import hash_verifier
from cryptavault_api.services.policy import DEFAULT_FLAGS
from cryptavault_api.settings import settings

VERIFIER_PLAINTEXT = b"cryptavault:verifier:v1"
DEMO_PASSWORD = "CryptaVaultDemo!2026"


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode()


def _derive_auth_verifier(passphrase: str, salt: bytes, iterations: int = 210_000) -> str:
    raw = pbkdf2_hmac("sha256", passphrase.encode(), salt, iterations, dklen=32)
    return _b64(raw)


def _vault_check(passphrase: str, salt: bytes, iterations: int = 210_000) -> dict[str, str]:
    key = pbkdf2_hmac("sha256", passphrase.encode(), salt, iterations, dklen=32)
    iv = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(iv, VERIFIER_PLAINTEXT, b"vault:verifier")
    return {"ivB64": _b64(iv), "ctB64": _b64(ciphertext)}


def _create_demo_user(
    db: Session,
    email: str,
    display_name: str,
    role: str = "user",
    workspace_name: str = "Personal vault",
) -> User:
    auth_salt = secrets.token_bytes(16)
    vault_salt = secrets.token_bytes(16)
    verifier = _derive_auth_verifier(DEMO_PASSWORD, auth_salt)
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        display_name=display_name,
        password_hash=hash_verifier(verifier),
        auth_salt_b64=_b64(auth_salt),
        kdf_iterations=210_000,
        vault_salt_b64=_b64(vault_salt),
        vault_check_json=json.dumps(_vault_check(DEMO_PASSWORD, vault_salt)),
        role=role,
        quota_bytes=10 * 1024 * 1024 * 1024,
    )
    db.add(user)
    db.flush()

    workspace = Workspace(
        id=str(uuid.uuid4()),
        name=workspace_name,
        owner_id=user.id,
        default_profile="BALANCED",
    )
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    return user


def _seed_storage_targets(db: Session) -> None:
    existing = db.scalar(select(func.count()).select_from(StorageTarget)) or 0
    if existing:
        return

    from cryptavault_api.secrets import encrypt_config

    local_config = {"root": str(settings.local_storage_path)}
    s3_config = {
        "endpoint": os.getenv("S3_ENDPOINT", "http://127.0.0.1:9000"),
        "bucket": os.getenv("S3_BUCKET", "cryptavault"),
        "access_key": os.getenv("S3_ACCESS_KEY", "minioadmin"),
        "secret_key": os.getenv("S3_SECRET_KEY", "minioadmin"),
        "region": os.getenv("S3_REGION", "us-east-1"),
        "path_style": os.getenv("S3_FORCE_PATH_STYLE", "true").lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        },
    }
    db.add(
        StorageTarget(
            name="local",
            kind="local",
            config_json=encrypt_config(local_config),
            enabled=True,
            is_default=settings.default_storage == "local",
        )
    )
    db.add(
        StorageTarget(
            name="s3",
            kind="s3",
            config_json=encrypt_config(s3_config),
            enabled=True,
            is_default=settings.default_storage != "local",
        )
    )


def _seed_settings(db: Session) -> None:
    for key, value in DEFAULT_FLAGS.items():
        if db.get(SystemSetting, key) is None:
            db.add(SystemSetting(key=key, value=json.dumps(value)))


def seed_defaults(db: Session) -> None:
    """Seed storage targets, flags, and demo accounts once."""
    _seed_storage_targets(db)
    _seed_settings(db)

    existing_users = db.scalar(select(func.count()).select_from(User)) or 0
    if not existing_users and settings.seed_demo:
        admin = _create_demo_user(
            db,
            "admin@cryptavault.dev",
            "Demo Admin",
            role="admin",
            workspace_name="Admin vault",
        )
        _create_demo_user(
            db,
            "demo@cryptavault.dev",
            "Demo User",
            workspace_name="Personal vault",
        )
        _create_demo_user(
            db,
            "viewer@cryptavault.dev",
            "Team Viewer",
            workspace_name="Viewer vault",
        )
        # Give the demo user a shared team workspace.
        team = Workspace(
            id=str(uuid.uuid4()),
            name="Final Year Team",
            owner_id=admin.id,
            default_profile="STRONG",
        )
        db.add(team)
        db.flush()
        db.add(WorkspaceMember(workspace_id=team.id, user_id=admin.id, role="owner"))
        demo = db.scalar(select(User).where(User.email == "demo@cryptavault.dev"))
        viewer = db.scalar(select(User).where(User.email == "viewer@cryptavault.dev"))
        if demo:
            db.add(WorkspaceMember(workspace_id=team.id, user_id=demo.id, role="editor"))
        if viewer:
            db.add(WorkspaceMember(workspace_id=team.id, user_id=viewer.id, role="viewer"))

    db.commit()
