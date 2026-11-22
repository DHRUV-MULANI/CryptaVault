"""Symmetric encryption for storage credentials stored in Postgres."""

from __future__ import annotations

import base64
import json
from hashlib import sha256
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from cryptavault_api.settings import settings

_key = base64.urlsafe_b64encode(sha256(settings.storage_secret.encode()).digest())
_fernet = Fernet(_key)


def encrypt_config(config: dict[str, Any]) -> str:
    """Encrypt a storage target configuration for at-rest storage."""
    payload = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return _fernet.encrypt(payload).decode()


def decrypt_config(value: str) -> dict[str, Any]:
    """Decrypt a stored storage target configuration."""
    if not value:
        return {}
    try:
        payload = _fernet.decrypt(value.encode())
    except InvalidToken as exc:
        raise ValueError("Storage configuration cannot be decrypted with this key.") from exc
    data = json.loads(payload.decode())
    if not isinstance(data, dict):
        raise TypeError("Storage configuration must be a JSON object.")
    return data
