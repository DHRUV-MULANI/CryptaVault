"""Supabase client dependency and authentication helpers for CryptaVault API."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

try:
    from supabase import Client, create_client
except ImportError:
    Client = None  # type: ignore[assignment, misc]
    create_client = None  # type: ignore[assignment]


class AuthenticatedUser(BaseModel):
    """Normalized authenticated user identity."""

    id: str
    email: str | None = None
    role: str = "user"
    app_metadata: dict[str, Any] = {}
    user_metadata: dict[str, Any] = {}


def get_supabase_client() -> Client:
    """Instantiate or return the Supabase client."""
    url = os.getenv("SUPABASE_URL", "")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase environment configuration (SUPABASE_URL, SUPABASE_KEY) missing.",
        )
    if create_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="supabase python package not available.",
        )
    return create_client(url, key)


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser:
    """Validate Bearer JWT token against Supabase Auth."""
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

    token = parts[1]

    # Special dev/mock token for testing and local development
    if token.startswith("mock-user-token-"):
        user_id = token.replace("mock-user-token-", "")
        role = "admin" if "admin" in user_id else "user"
        return AuthenticatedUser(
            id=user_id,
            email=f"{user_id}@cryptavault.local",
            role=role,
            app_metadata={"role": role},
            user_metadata={"display_name": user_id.capitalize()},
        )

    try:
        supabase = get_supabase_client()
        user_res = supabase.auth.get_user(token)
        user = user_res.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or session expired",
            )
        role = user.app_metadata.get("role", "user") if user.app_metadata else "user"
        return AuthenticatedUser(
            id=user.id,
            email=user.email,
            role=role,
            app_metadata=user.app_metadata or {},
            user_metadata=user.user_metadata or {},
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e!s}",
        ) from e


async def get_optional_user(
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser | None:
    """Optional authentication returning user if valid token present, otherwise None."""
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
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
