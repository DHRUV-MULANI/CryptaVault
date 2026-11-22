"""Password verification and JWT helpers for local CryptaVault accounts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from cryptavault_api.models import User
from cryptavault_api.settings import settings

_hasher = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=2)


def hash_verifier(verifier: str) -> str:
    """Hash the client-derived auth verifier before persistence."""
    return _hasher.hash(verifier)


def verify_verifier(verifier: str, stored_hash: str) -> bool:
    """Return True when the client-derived verifier matches the stored hash."""
    try:
        return _hasher.verify(stored_hash, verifier)
    except (VerifyMismatchError, ValueError):
        return False


def create_access_token(user: User) -> str:
    """Issue a signed access token without exposing any file key material."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed access token."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "exp", "type"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload
