"""Admin user governance, feature flags, and system health."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cryptavault_api.db import database_healthy, get_db
from cryptavault_api.deps.supabase import AuthenticatedUser, get_admin_user
from cryptavault_api.models import FileObject, Share, StorageTarget, SystemSetting, User, Workspace
from cryptavault_api.security import create_access_token
from cryptavault_api.serializers import user_public
from cryptavault_api.services.policy import DEFAULT_FLAGS, flag_value
from cryptavault_api.services.storage import test_target

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UpdateUserAdminRequest(BaseModel):
    suspended: bool | None = None
    quota_bytes: int | None = None
    role: str | None = None
    display_name: str | None = None


class FlagToggleRequest(BaseModel):
    enabled: bool


def _flag_value(db: Session, key: str) -> bool:
    return flag_value(db, key)


@router.get("/users")
def list_all_users(
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return [user_public(user) for user in db.scalars(select(User).order_by(User.created_at)).all()]


@router.patch("/users/{user_id}")
def update_user_status(
    user_id: str,
    payload: UpdateUserAdminRequest,
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.suspended is not None:
        user.suspended = payload.suspended
    if payload.quota_bytes is not None:
        if payload.quota_bytes < 0:
            raise HTTPException(status_code=422, detail="Quota cannot be negative.")
        user.quota_bytes = payload.quota_bytes
    if payload.role is not None:
        if payload.role not in {"user", "admin"}:
            raise HTTPException(status_code=422, detail="Role must be user or admin.")
        if user.id == admin.id and payload.role != "admin":
            raise HTTPException(status_code=400, detail="You cannot demote your own admin account.")
        user.role = payload.role
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()[:120]
    db.commit()
    db.refresh(user)
    return {"status": "updated", "user": user_public(user)}


@router.post("/impersonate/{user_id}")
def impersonate_user(
    user_id: str,
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target user not found.")
    if target.suspended:
        raise HTTPException(status_code=409, detail="Cannot impersonate a suspended user.")
    return {
        "status": "impersonation_granted",
        "impersonated_user": target.id,
        "impersonated_by": admin.id,
        "access_token": create_access_token(target),
        "expires_in_seconds": 600,
    }


@router.get("/flags")
def get_feature_flags(
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    return {key: _flag_value(db, key) for key in DEFAULT_FLAGS}


@router.put("/flags/{flag_name}")
def set_feature_flag(
    flag_name: str,
    payload: FlagToggleRequest,
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if flag_name not in DEFAULT_FLAGS:
        raise HTTPException(status_code=404, detail=f"Unknown flag: {flag_name}")
    record = db.get(SystemSetting, flag_name)
    if record is None:
        record = SystemSetting(key=flag_name, value=json.dumps(payload.enabled))
        db.add(record)
    else:
        record.value = json.dumps(payload.enabled)
    db.commit()
    return {"flag": flag_name, "enabled": payload.enabled}


@router.get("/health")
def get_admin_system_health(
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    targets = list(db.scalars(select(StorageTarget)).all())
    return {
        "status": "healthy" if database_healthy() else "degraded",
        "database": "connected" if database_healthy() else "unavailable",
        "users": int(db.scalar(select(func.count(User.id))) or 0),
        "workspaces": int(db.scalar(select(func.count(Workspace.id))) or 0),
        "files": int(db.scalar(select(func.count(FileObject.id))) or 0),
        "shares": int(db.scalar(select(func.count(Share.token))) or 0),
        "storage_targets": [test_target(target) for target in targets],
    }
