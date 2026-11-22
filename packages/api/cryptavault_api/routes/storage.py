"""Storage target management and health endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from cryptavault_api.db import get_db
from cryptavault_api.deps.supabase import AuthenticatedUser, get_admin_user, get_current_user
from cryptavault_api.models import FileVersion, StorageTarget
from cryptavault_api.secrets import encrypt_config
from cryptavault_api.serializers import target_public
from cryptavault_api.services.policy import CLOUD_TARGET_KINDS, require_flag
from cryptavault_api.services.storage import test_target

router = APIRouter(prefix="/api/storage", tags=["storage"])

VALID_KINDS = {"local", "s3", "gdrive", "dropbox", "onedrive"}


class CreateTargetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: str = Field(min_length=2, max_length=20)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    is_default: bool = False


class UpdateTargetRequest(BaseModel):
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    is_default: bool | None = None


def _validate_kind(kind: str) -> str:
    clean = kind.lower().strip()
    if clean not in VALID_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"Kind must be one of: {', '.join(sorted(VALID_KINDS))}.",
        )
    return clean


def _clear_defaults(db: Session, name: str | None = None) -> None:
    for target in db.scalars(select(StorageTarget)).all():
        if target.name != name:
            target.is_default = False


@router.get("/targets")
def list_targets(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    targets = list(db.scalars(select(StorageTarget).order_by(StorageTarget.name)).all())
    return [target_public(target) for target in targets]


@router.post("/targets", status_code=status.HTTP_201_CREATED)
def create_target(
    payload: CreateTargetRequest,
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    name = payload.name.strip()
    if db.get(StorageTarget, name) is not None:
        raise HTTPException(status_code=409, detail="A storage target with that name exists.")
    kind = _validate_kind(payload.kind)
    if kind in CLOUD_TARGET_KINDS:
        require_flag(
            db,
            "enable_cloud_connectors",
            "Cloud storage connectors are disabled by the administrator.",
        )
    if payload.is_default:
        _clear_defaults(db)
    target = StorageTarget(
        name=name,
        kind=kind,
        config_json=encrypt_config(payload.config),
        enabled=payload.enabled,
        is_default=payload.is_default,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target_public(target)


@router.patch("/targets/{name}")
def update_target(
    name: str,
    payload: UpdateTargetRequest,
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    target = db.get(StorageTarget, name)
    if target is None:
        raise HTTPException(status_code=404, detail="Storage target not found.")
    if target.kind in CLOUD_TARGET_KINDS:
        require_flag(
            db,
            "enable_cloud_connectors",
            "Cloud storage connectors are disabled by the administrator.",
        )
    if payload.config is not None:
        target.config_json = encrypt_config(payload.config)
    if payload.enabled is not None:
        target.enabled = payload.enabled
    if payload.is_default:
        _clear_defaults(db, name)
        target.is_default = True
        target.enabled = True
    db.commit()
    db.refresh(target)
    return target_public(target)


@router.delete("/targets/{name}")
def delete_target(
    name: str,
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    target = db.get(StorageTarget, name)
    if target is None:
        raise HTTPException(status_code=404, detail="Storage target not found.")
    in_use = db.scalar(select(FileVersion).where(FileVersion.storage_target == name).limit(1))
    if in_use is not None:
        raise HTTPException(
            status_code=409,
            detail="Storage target still contains files. Move or delete them first.",
        )
    db.delete(target)
    db.commit()
    return {"status": "deleted", "name": name}


@router.post("/targets/{name}/test")
def test_storage_target(
    name: str,
    admin: AuthenticatedUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    target = db.get(StorageTarget, name)
    if target is None:
        raise HTTPException(status_code=404, detail="Storage target not found.")
    return test_target(target)


@router.get("/health")
def storage_health(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    targets = list(db.scalars(select(StorageTarget).order_by(StorageTarget.name)).all())
    return [test_target(target) for target in targets]
