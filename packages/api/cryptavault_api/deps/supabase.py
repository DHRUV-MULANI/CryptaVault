"""Authentication dependencies for local JWT-backed CryptaVault accounts.

The module name is kept for backwards compatibility with the existing route
imports, but the implementation no longer depends on Supabase. Supabase Auth is
optional for deployments that want an external identity provider.
"""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cryptavault_api.db import get_db
from cryptavault_api.models import User
from cryptavault_api.security import decode_access_token


class AuthenticatedUser(BaseModel):
    """Normalized authenticated user identity."""

    id: str
    email: str | None = None
    role: str = "user"
    display_name: str = ""
    app_metadata: dict[str, Any] = {}
    user_metadata: dict[str, Any] = {}


def _to_authenticated_user(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        app_metadata={"role": user.role},
        user_metadata={"display_name": user.display_name},
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """Validate a Bearer JWT and load the active user from Postgres."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(parts[1])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, str(payload.get("sub", "")))
    if user is None or user.suspended:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is missing or suspended.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _to_authenticated_user(user)


async def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthenticatedUser | None:
    """Optional authentication returning a user when a valid token is present."""
    if not authorization:
        return None
    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None


async def get_admin_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Ensure current user has the 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privilege required for this endpoint.",
        )
    return current_user
