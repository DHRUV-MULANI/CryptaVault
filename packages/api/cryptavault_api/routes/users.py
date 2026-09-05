"""User profile and encrypted manifest synchronization routes."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

# In-memory storage for user profiles and manifests (backed by Supabase table in production)
_USER_MANIFEST_STORE: dict[str, dict[str, Any]] = {}
_USER_PROFILE_STORE: dict[str, dict[str, Any]] = {}


class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    default_security_profile: str | None = None


class EncryptedManifestSyncRequest(BaseModel):
    """Payload representing an encrypted manifest ciphertext envelope.

    Zero-Knowledge Invariant: The server receives only ciphertext. Plaintext file names,
    keys, and directories remain strictly encrypted with user's client-side master key.
    """

    manifest_version: int = Field(default=1)
    ciphertext_b64: str = Field(..., description="AES-256-GCM encrypted manifest JSON")
    nonce_b64: str = Field(..., description="12-byte initialization vector")
    hash_blake3_hex: str = Field(..., description="BLAKE3 hash of the ciphertext envelope")
    file_count: int = Field(default=0)


class EncryptedManifestResponse(BaseModel):
    manifest_version: int
    ciphertext_b64: str
    nonce_b64: str
    hash_blake3_hex: str
    file_count: int
    updated_at: str


@router.get("/me")
def get_user(user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    """Get current user settings and storage quota."""
    profile = _USER_PROFILE_STORE.get(user.id, {})
    return {
        "id": user.id,
        "email": user.email,
        "display_name": profile.get(
            "display_name", user.user_metadata.get("display_name", user.id)
        ),
        "quota_bytes": 10 * 1024 * 1024 * 1024,  # 10 GB default tier
        "used_bytes": profile.get("used_bytes", 0),
        "security_profile": profile.get("default_security_profile", "BALANCED"),
    }


@router.patch("/me")
def update_user(
    payload: UserUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update current user profile settings."""
    profile = _USER_PROFILE_STORE.setdefault(user.id, {})
    if payload.display_name is not None:
        profile["display_name"] = payload.display_name
    if payload.default_security_profile is not None:
        profile["default_security_profile"] = payload.default_security_profile
    return {"status": "updated", "profile": profile}


@router.get("/me/manifest", response_model=EncryptedManifestResponse)
def get_user_manifest(
    user: AuthenticatedUser = Depends(get_current_user),
) -> EncryptedManifestResponse:
    """Retrieve the user's latest client-side encrypted manifest."""
    manifest = _USER_MANIFEST_STORE.get(user.id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No manifest found for current user.",
        )
    return EncryptedManifestResponse(**manifest)


@router.put("/me/manifest")
def put_user_manifest(
    payload: EncryptedManifestSyncRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload new client-side encrypted manifest.

    Enforces cross-user isolation: User A cannot read or write User B's manifest.
    """
    from datetime import datetime

    now_iso = datetime.now(UTC).isoformat()
    record = {
        "manifest_version": payload.manifest_version,
        "ciphertext_b64": payload.ciphertext_b64,
        "nonce_b64": payload.nonce_b64,
        "hash_blake3_hex": payload.hash_blake3_hex,
        "file_count": payload.file_count,
        "updated_at": now_iso,
    }
    _USER_MANIFEST_STORE[user.id] = record
    return {
        "status": "synchronized",
        "hash_blake3_hex": payload.hash_blake3_hex,
        "updated_at": now_iso,
    }
