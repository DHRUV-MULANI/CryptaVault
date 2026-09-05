"""Cryptographic share token and package distribution routes."""

from __future__ import annotations

import os
from datetime import UTC
from typing import Any

from cryptavault.sharing.qr import generate_qr_png
from cryptavault.sharing.token import ShareTokenManager
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/api/shares", tags=["shares"])

# In-memory share record store (backed by Supabase share_tokens table in production)
_SHARE_STORE: dict[str, dict[str, Any]] = {}
_SHARE_SECRET_KEY = os.urandom(32)


class CreateShareRequest(BaseModel):
    file_id: str = Field(..., description="ID of the file to share")
    filename: str = Field(..., description="Obfuscated or display filename")
    ciphertext_ref: str = Field(..., description="Storage URI or ciphertext locator")
    expires_at_iso: str | None = Field(
        default=None, description="ISO timestamp for token expiration"
    )
    max_uses: int = Field(
        default=1, description="Allowed downloads before auto-revocation (1 for one-time)"
    )
    password_protected: bool = Field(default=False)
    share_package_json: str | None = Field(
        default=None, description="Full signed SharePackage JSON"
    )
    custom_domain: str | None = Field(
        default=None,
        description="Custom domain or Cloudflare public domain (e.g. https://vault.yourdomain.com)",
    )


class ShareSummaryResponse(BaseModel):
    token_id: str
    file_id: str
    filename: str
    share_url: str
    created_at_iso: str
    expires_at_iso: str | None
    max_uses: int
    current_uses: int
    is_active: bool
    password_protected: bool


@router.post("", response_model=ShareSummaryResponse)
def create_share(
    payload: CreateShareRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ShareSummaryResponse:
    """Create a new signed cryptographic share token."""
    token = ShareTokenManager.create_token(
        secret_key=_SHARE_SECRET_KEY,
        file_id=payload.file_id,
        expires_at_iso=payload.expires_at_iso,
        max_uses=payload.max_uses,
    )

    base_domain = (
        payload.custom_domain
        or os.getenv("PUBLIC_SHARE_DOMAIN")
        or os.getenv("CUSTOM_SHARE_DOMAIN")
        or "https://cryptavault.local"
    ).rstrip("/")
    share_url = f"{base_domain}/share/{token.token_id}"

    record = {
        "token_id": token.token_id,
        "owner_id": user.id,
        "file_id": payload.file_id,
        "filename": payload.filename,
        "ciphertext_ref": payload.ciphertext_ref,
        "share_url": share_url,
        "nonce_hex": token.nonce_hex,
        "created_at_iso": token.created_at_iso,
        "expires_at_iso": token.expires_at_iso,
        "max_uses": token.max_uses,
        "current_uses": 0,
        "signature_b64": token.signature_b64,
        "is_active": True,
        "password_protected": payload.password_protected,
        "share_package_json": payload.share_package_json,
    }
    _SHARE_STORE[token.token_id] = record

    return ShareSummaryResponse(
        token_id=token.token_id,
        file_id=payload.file_id,
        filename=payload.filename,
        share_url=share_url,
        created_at_iso=token.created_at_iso,
        expires_at_iso=token.expires_at_iso,
        max_uses=token.max_uses,
        current_uses=0,
        is_active=True,
        password_protected=payload.password_protected,
    )


@router.get("", response_model=list[ShareSummaryResponse])
def list_user_shares(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[ShareSummaryResponse]:
    """List all active and expired shares created by the current user."""
    default_domain = (os.getenv("PUBLIC_SHARE_DOMAIN") or "https://cryptavault.local").rstrip("/")
    user_shares = [
        ShareSummaryResponse(
            token_id=r["token_id"],
            file_id=r["file_id"],
            filename=r["filename"],
            share_url=r.get("share_url", f"{default_domain}/share/{r['token_id']}"),
            created_at_iso=r["created_at_iso"],
            expires_at_iso=r["expires_at_iso"],
            max_uses=r["max_uses"],
            current_uses=r["current_uses"],
            is_active=r["is_active"],
            password_protected=r["password_protected"],
        )
        for r in _SHARE_STORE.values()
        if r["owner_id"] == user.id
    ]
    return user_shares


@router.get("/{token_id}")
def get_public_share_info(token_id: str) -> dict[str, Any]:
    """Public endpoint to verify share validity without exposing secret keys."""
    record = _SHARE_STORE.get(token_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share token not found.",
        )
    if not record["is_active"]:
        if record["current_uses"] >= record["max_uses"]:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Share token usage limit has been reached.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share token has been revoked.",
        )

    # Check expiration
    from datetime import datetime

    if record["expires_at_iso"]:
        exp = datetime.fromisoformat(record["expires_at_iso"])
        if datetime.now(UTC) > exp:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Share token has expired.",
            )

    # Check use exhaustion
    if record["current_uses"] >= record["max_uses"]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share token usage limit has been reached.",
        )

    return {
        "token_id": token_id,
        "file_id": record["file_id"],
        "filename": record["filename"],
        "ciphertext_ref": record["ciphertext_ref"],
        "expires_at_iso": record["expires_at_iso"],
        "remaining_uses": record["max_uses"] - record["current_uses"],
        "password_protected": record["password_protected"],
        "share_package_json": record.get("share_package_json"),
    }


@router.post("/{token_id}/consume")
def consume_share(token_id: str) -> dict[str, Any]:
    """Consume one use of the share token."""
    record = _SHARE_STORE.get(token_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share token not found.",
        )
    if not record["is_active"]:
        if record["current_uses"] >= record["max_uses"]:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Share token usage limit exhausted.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share token has been revoked.",
        )

    # Check expiration
    from datetime import datetime

    if record["expires_at_iso"]:
        exp = datetime.fromisoformat(record["expires_at_iso"])
        if datetime.now(UTC) > exp:
            record["is_active"] = False
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share token has expired.")

    if record["current_uses"] >= record["max_uses"]:
        record["is_active"] = False
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share token usage limit exhausted.",
        )

    record["current_uses"] += 1
    if record["current_uses"] >= record["max_uses"]:
        record["is_active"] = False

    return {
        "status": "consumed",
        "file_id": record["file_id"],
        "ciphertext_ref": record["ciphertext_ref"],
        "remaining_uses": max(0, record["max_uses"] - record["current_uses"]),
        "share_package_json": record.get("share_package_json"),
    }


@router.delete("/{token_id}")
def revoke_share(
    token_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    """Revoke a share token."""
    record = _SHARE_STORE.get(token_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found.")
    if record["owner_id"] != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke another user's share."
        )

    record["is_active"] = False
    return {"status": "revoked", "token_id": token_id}


@router.get("/{token_id}/qr")
def get_share_qr(token_id: str, domain: str | None = None) -> Response:
    """Generate and return PNG QR code for the share link."""
    record = _SHARE_STORE.get(token_id)
    if not record or not record["is_active"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found.")

    base_domain = (
        domain or os.getenv("PUBLIC_SHARE_DOMAIN") or "https://cryptavault.local"
    ).rstrip("/")
    url = f"{base_domain}/share/{token_id}"
    png_bytes = generate_qr_png(url)
    return Response(content=png_bytes, media_type="image/png")
