"""Local account registration, login, and session endpoints."""

from __future__ import annotations

import base64
import json
import uuid
from hashlib import sha256
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from cryptavault_api.db import get_db
from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user
from cryptavault_api.models import User, Workspace, WorkspaceMember
from cryptavault_api.security import (
    create_access_token,
    hash_verifier,
    verify_verifier,
)
from cryptavault_api.serializers import user_public
from cryptavault_api.services.workspaces import workspace_summary

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PreloginRequest(BaseModel):
    email: EmailStr


class PreLoginResponse(BaseModel):
    exists: bool
    auth_salt_b64: str
    kdf_iterations: int


class VaultCheck(BaseModel):
    ivB64: str
    ctB64: str


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    auth_salt_b64: str = Field(min_length=16, max_length=128)
    auth_verifier: str = Field(min_length=16, max_length=256)
    vault_salt_b64: str = Field(min_length=16, max_length=128)
    vault_check: VaultCheck
    kdf_iterations: int = Field(default=210_000, ge=100_000, le=2_000_000)


class LoginRequest(BaseModel):
    email: EmailStr
    auth_verifier: str = Field(min_length=16, max_length=256)


class UserEnvelope(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]
    vault: dict[str, Any]
    workspaces: list[dict[str, Any]]


class MeResponse(BaseModel):
    user: dict[str, Any]
    vault: dict[str, Any]
    workspaces: list[dict[str, Any]]


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    default_profile: str | None = Field(default=None, max_length=20)


def _decode_b64(value: str) -> bytes:
    """Validate base64; accepts plain base64 or dot-separated base64 parts (iv.ct)."""
    try:
        parts = value.split(".")
        if len(parts) == 1:
            return base64.b64decode(value, validate=True)
        if len(parts) == 2:
            base64.b64decode(parts[0], validate=True)
            return base64.b64decode(parts[1], validate=True)
        raise ValueError("too many parts")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid base64 encoding.",
        ) from exc


def _vault_payload(user: User) -> dict[str, Any]:
    return {
        "salt_b64": user.vault_salt_b64,
        "check": json.loads(user.vault_check_json),
        "kdf_iterations": user.kdf_iterations,
    }


def _workspace_payloads(db: Session, user_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at)
    ).all()
    return [workspace_summary(db, workspace, role) for workspace, role in rows]


def _session_envelope(db: Session, user: User) -> UserEnvelope:
    return UserEnvelope(
        access_token=create_access_token(user),
        user=user_public(user),
        vault=_vault_payload(user),
        workspaces=_workspace_payloads(db, user.id),
    )


@router.post("/prelogin", response_model=PreLoginResponse)
def prelogin(payload: PreloginRequest, db: Session = Depends(get_db)) -> PreLoginResponse:
    """Return the per-user auth KDF salt without revealing whether the account exists."""
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        dummy = base64.b64encode(sha256(email.encode()).digest()[:16]).decode()
        return PreLoginResponse(exists=False, auth_salt_b64=dummy, kdf_iterations=210_000)
    return PreLoginResponse(
        exists=True,
        auth_salt_b64=user.auth_salt_b64,
        kdf_iterations=user.kdf_iterations,
    )


@router.post("/register", response_model=UserEnvelope, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserEnvelope:
    """Create a local account from client-derived auth and vault key material."""
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    _decode_b64(payload.auth_salt_b64)
    _decode_b64(payload.vault_salt_b64)
    _decode_b64(payload.auth_verifier)

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_verifier(payload.auth_verifier),
        auth_salt_b64=payload.auth_salt_b64,
        kdf_iterations=payload.kdf_iterations,
        vault_salt_b64=payload.vault_salt_b64,
        vault_check_json=json.dumps(payload.vault_check.model_dump()),
    )
    db.add(user)
    db.flush()

    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Personal vault",
        owner_id=user.id,
        default_profile="BALANCED",
    )
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(user)
    return _session_envelope(db, user)


@router.post("/login", response_model=UserEnvelope)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> UserEnvelope:
    """Exchange a client-derived auth verifier for a JWT access token."""
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or user.suspended:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or passphrase.",
        )
    if not verify_verifier(payload.auth_verifier, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or passphrase.",
        )
    return _session_envelope(db, user)


@router.get("/me", response_model=MeResponse)
def me(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    user = db.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return MeResponse(
        user=user_public(user),
        vault=_vault_payload(user),
        workspaces=_workspace_payloads(db, user.id),
    )


@router.patch("/me", response_model=MeResponse)
def update_me(
    payload: ProfileUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    """Update safe profile fields; key material is never accepted here."""
    user = db.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.default_profile is not None:
        user.default_profile = payload.default_profile.strip().upper()
    db.commit()
    db.refresh(user)
    return MeResponse(
        user=user_public(user),
        vault=_vault_payload(user),
        workspaces=_workspace_payloads(db, user.id),
    )


@router.post("/logout")
def logout() -> dict[str, str]:
    """JWT logout is client-side; this endpoint exists for API symmetry."""
    return {"status": "logged_out"}
