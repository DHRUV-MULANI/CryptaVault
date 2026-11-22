"""Capability-link sharing with expiry, passphrases, PIN, and download limits."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from cryptavault.sharing.qr import generate_qr_png
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cryptavault_api.db import get_db
from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user, get_optional_user
from cryptavault_api.models import FileObject, FileVersion, Share
from cryptavault_api.security import hash_verifier, verify_verifier
from cryptavault_api.serializers import share_public
from cryptavault_api.services.policy import enforce_write_access, require_flag
from cryptavault_api.services.storage import download_ciphertext
from cryptavault_api.services.workspaces import require_workspace
from cryptavault_api.settings import settings

router = APIRouter(prefix="/api/shares", tags=["shares"])


class CreateShareRequest(BaseModel):
    file_id: str
    version: int | None = None
    expires_at: datetime | None = None
    max_uses: int = Field(default=1, ge=1, le=10_000)
    password: str | None = Field(default=None, min_length=4, max_length=256)
    recipient_email: str | None = Field(default=None, max_length=320)
    pin: str | None = Field(default=None, description="8-digit access PIN; auto-assigned if omitted")

    @field_validator("recipient_email")
    @classmethod
    def _norm_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        return v or None

    @field_validator("pin")
    @classmethod
    def _norm_pin(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not (v.isdigit() and len(v) == 8):
            raise ValueError("PIN must be exactly 8 digits")
        return v


class DownloadShareRequest(BaseModel):
    password: str | None = None
    pin: str | None = None


class UpdatePinRequest(BaseModel):
    pin: str | None = Field(default=None, description="New 8-digit PIN, or null to auto-generate")

    @field_validator("pin")
    @classmethod
    def _norm_pin(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not (v.isdigit() and len(v) == 8):
            raise ValueError("PIN must be exactly 8 digits")
        return v


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _share_url(token: str) -> str:
    return f"{settings.public_share_domain}/#/s/{token}"


def _generate_pin() -> str:
    return f"{secrets.randbelow(90_000_000) + 10_000_000}"


def _is_recipient(share: Share, current: AuthenticatedUser | None) -> bool:
    if not share.recipient_email or current is None:
        return False
    return current.email.lower() == share.recipient_email.lower()


def _validate_share(share: Share) -> None:
    if share.revoked:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share has been revoked.")
    if share.expires_at and datetime.now(UTC) > _aware(share.expires_at):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share has expired.")
    if share.uses >= share.max_uses:
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Share download limit reached."
        )


def _require_owner_or_admin(share: Share, current: AuthenticatedUser) -> None:
    if share.owner_id != current.id and current.role != "admin":
        raise HTTPException(status_code=403, detail="Cannot modify another user's share.")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_share(
    payload: CreateShareRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    file = db.get(FileObject, payload.file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id, "editor")
    enforce_write_access(db, current.role)
    require_flag(db, "enable_sharing", "Sharing is disabled by the administrator.")
    if file.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Cannot share a trashed file.")
    expires_at = _aware(payload.expires_at) if payload.expires_at is not None else None
    if expires_at is not None and expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="expires_at must be in the future.")
    version = payload.version or file.current_version
    record = db.scalar(
        select(FileVersion).where(
            FileVersion.file_id == file.id,
            FileVersion.version == version,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    pin = payload.pin or _generate_pin()
    token = secrets.token_urlsafe(24)
    share = Share(
        token=token,
        file_id=file.id,
        version=version,
        owner_id=current.id,
        recipient_email=payload.recipient_email,
        expires_at=expires_at,
        max_uses=payload.max_uses,
        password_hash=hash_verifier(payload.password) if payload.password else None,
        pin_hash=hash_verifier(pin),
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share_public(share, _share_url(token), pin=pin)


@router.get("")
def list_shares(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    shares = list(
        db.scalars(
            select(Share).where(Share.owner_id == current.id).order_by(Share.created_at.desc())
        ).all()
    )
    return [share_public(share, _share_url(share.token)) for share in shares]


@router.get("/received")
def list_received_shares(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    email = current.email.lower()
    shares = list(
        db.scalars(
            select(Share)
            .where(func.lower(Share.recipient_email) == email)
            .order_by(Share.created_at.desc())
        ).all()
    )
    results: list[dict[str, Any]] = []
    for share in shares:
        file = db.get(FileObject, share.file_id)
        if file is None or file.deleted_at is not None:
            continue
        record = db.scalar(
            select(FileVersion).where(
                FileVersion.file_id == share.file_id,
                FileVersion.version == share.version,
            )
        )
        if record is None:
            continue
        item = share_public(share, _share_url(share.token))
        item["owner_id"] = share.owner_id
        item["ciphertext_size"] = record.ciphertext_size
        item["profile"] = record.profile
        item["file_deleted"] = False
        results.append(item)
    return results


@router.get("/{token}")
def public_share_info(
    token: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser | None = Depends(get_optional_user),
) -> dict[str, Any]:
    share = db.get(Share, token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found.")
    _validate_share(share)
    file = db.get(FileObject, share.file_id)
    if file is None or file.deleted_at is not None:
        raise HTTPException(status_code=410, detail="Shared file is no longer available.")
    record = db.scalar(
        select(FileVersion).where(
            FileVersion.file_id == share.file_id,
            FileVersion.version == share.version,
        )
    )
    if record is None:
        raise HTTPException(status_code=410, detail="Shared version is no longer available.")
    recipient_match = _is_recipient(share, current)
    return {
        "token": share.token,
        "file_id": share.file_id,
        "version": share.version,
        "ciphertext_size": record.ciphertext_size,
        "content_tag": record.content_tag,
        "profile": record.profile,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
        "remaining_uses": max(0, share.max_uses - share.uses),
        "password_protected": bool(share.password_hash),
        "pin_protected": bool(share.pin_hash),
        "pin_required": bool(share.pin_hash) and not recipient_match,
        "recipient_email": share.recipient_email,
        "recipient_match": recipient_match,
        "download_url": f"/api/shares/{share.token}/download",
    }


@router.post("/{token}/download")
def download_shared_file(
    token: str,
    payload: DownloadShareRequest | None = None,
    db: Session = Depends(get_db),
    current: AuthenticatedUser | None = Depends(get_optional_user),
) -> StreamingResponse:
    share = db.get(Share, token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found.")
    _validate_share(share)
    recipient_match = _is_recipient(share, current)
    if share.password_hash:
        password = payload.password if payload else None
        if not password or not verify_verifier(password, share.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect share passphrase.")
    if share.pin_hash and not recipient_match:
        pin = payload.pin if payload else None
        if not pin or not verify_verifier(pin, share.pin_hash):
            raise HTTPException(status_code=401, detail="Incorrect share PIN.")
    file = db.get(FileObject, share.file_id)
    if file is None or file.deleted_at is not None:
        raise HTTPException(status_code=410, detail="Shared file is no longer available.")
    record = db.scalar(
        select(FileVersion).where(
            FileVersion.file_id == share.file_id,
            FileVersion.version == share.version,
        )
    )
    if record is None:
        raise HTTPException(status_code=410, detail="Shared version is no longer available.")
    stream, target_name = download_ciphertext(db, record.storage_target, record.storage_key)
    share.uses += 1
    db.commit()
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file.id}.v{record.version}.cv"',
            "X-CV-Version": str(record.version),
            "X-CV-Storage-Target": target_name,
            "X-CV-Remaining-Uses": str(max(0, share.max_uses - share.uses)),
        },
    )


@router.patch("/{token}/pin")
def update_share_pin(
    token: str,
    payload: UpdatePinRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    share = db.get(Share, token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found.")
    _require_owner_or_admin(share, current)
    pin = payload.pin or _generate_pin()
    share.pin_hash = hash_verifier(pin)
    db.commit()
    db.refresh(share)
    return share_public(share, _share_url(token), pin=pin)


@router.post("/{token}/regenerate")
def regenerate_share_link(
    token: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    share = db.get(Share, token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found.")
    _require_owner_or_admin(share, current)
    if share.revoked:
        raise HTTPException(status_code=409, detail="Cannot regenerate a revoked share.")
    new_token = secrets.token_urlsafe(24)
    # Primary key change: create new row, delete old
    new_share = Share(
        token=new_token,
        file_id=share.file_id,
        version=share.version,
        owner_id=share.owner_id,
        recipient_email=share.recipient_email,
        expires_at=share.expires_at,
        max_uses=share.max_uses,
        uses=share.uses,
        password_hash=share.password_hash,
        pin_hash=share.pin_hash,
        revoked=share.revoked,
        created_at=share.created_at,
    )
    db.add(new_share)
    db.delete(share)
    db.commit()
    db.refresh(new_share)
    return share_public(new_share, _share_url(new_token))


@router.delete("/{token}")
def revoke_share(
    token: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    share = db.get(Share, token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found.")
    _require_owner_or_admin(share, current)
    share.revoked = True
    db.commit()
    return {"status": "revoked", "token": token}


@router.get("/{token}/qr")
def share_qr(
    token: str,
    key: str | None = Query(default=None, description="Optional URL fragment key material"),
    manifest: str | None = Query(
        default=None,
        alias="m",
        description="Optional base64url share manifest",
    ),
    db: Session = Depends(get_db),
) -> Response:
    share = db.get(Share, token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found.")
    _validate_share(share)
    url = _share_url(token)
    params = []
    if manifest:
        params.append(f"m={manifest}")
    if key:
        params.append(f"k={key}")
    if params:
        url = f"{url}?{'&'.join(params)}"
    return Response(content=generate_qr_png(url), media_type="image/png")
