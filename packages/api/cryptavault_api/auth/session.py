"""Supabase multi-provider authentication and session routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SessionExchangeRequest(BaseModel):
    """Payload to exchange Supabase JWT access token for application session."""

    access_token: str = Field(..., description="Supabase access token from OAuth or password login")
    refresh_token: str | None = Field(default=None, description="Supabase refresh token")


class UserProfileResponse(BaseModel):
    id: str
    email: str | None
    role: str
    metadata: dict[str, Any]


@router.post("/session")
def create_session(payload: SessionExchangeRequest, response: Response) -> dict[str, str]:
    """Exchange Supabase access token for a secure session cookie."""
    # Set HTTP-only secure cookie for web client
    response.set_cookie(
        key="cv_session",
        value=payload.access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=15 * 60,  # 15 minutes
    )
    return {"status": "session_created", "token_type": "bearer"}


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    user: AuthenticatedUser = Depends(get_current_user),
) -> UserProfileResponse:
    """Return the authenticated user profile and roles."""
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        metadata={**user.user_metadata, **user.app_metadata},
    )


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Invalidate session cookies."""
    response.delete_cookie(key="cv_session")
    return {"status": "logged_out"}
