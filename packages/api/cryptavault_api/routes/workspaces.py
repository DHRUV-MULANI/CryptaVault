"""Workspace CRUD, membership, and role management."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cryptavault_api.db import get_db
from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user
from cryptavault_api.models import (
    FileObject,
    Share,
    StorageTarget,
    User,
    Workspace,
    WorkspaceMember,
)
from cryptavault_api.serializers import member_public
from cryptavault_api.services.policy import enforce_write_access
from cryptavault_api.services.storage import delete_ciphertext
from cryptavault_api.services.workspaces import (
    ROLE_RANK,
    release_quota_for_versions,
    require_workspace,
    workspace_summary,
)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

VALID_ROLES = {"viewer", "editor", "admin", "owner"}


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    default_profile: str = Field(default="BALANCED", max_length=20)
    storage_target: str | None = Field(default=None, max_length=80)


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    default_profile: str | None = Field(default=None, max_length=20)
    storage_target: str | None = Field(default=None, max_length=80)


class MemberRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="viewer", max_length=20)


class MemberUpdateRequest(BaseModel):
    role: str = Field(max_length=20)


@router.get("")
def list_workspaces(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == current.id)
        .order_by(Workspace.created_at)
    ).all()
    return [workspace_summary(db, workspace, role) for workspace, role in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: CreateWorkspaceRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.storage_target and db.get(StorageTarget, payload.storage_target) is None:
        raise HTTPException(status_code=404, detail="Storage target not found.")
    enforce_write_access(db, current.role)
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name=payload.name.strip(),
        owner_id=current.id,
        default_profile=payload.default_profile,
        storage_target=payload.storage_target,
    )
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=current.id, role="owner"))
    db.commit()
    db.refresh(workspace)
    return workspace_summary(db, workspace, "owner")


@router.get("/{workspace_id}")
def get_workspace_detail(
    workspace_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace, role = require_workspace(db, workspace_id, current.id)
    return workspace_summary(db, workspace, role)


@router.patch("/{workspace_id}")
def update_workspace(
    workspace_id: str,
    payload: UpdateWorkspaceRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace, role = require_workspace(db, workspace_id, current.id, "admin")
    enforce_write_access(db, current.role)
    if payload.storage_target and db.get(StorageTarget, payload.storage_target) is None:
        raise HTTPException(status_code=404, detail="Storage target not found.")
    if payload.name is not None:
        workspace.name = payload.name.strip()
    if payload.default_profile is not None:
        workspace.default_profile = payload.default_profile
    if payload.storage_target is not None:
        workspace.storage_target = payload.storage_target or None
    db.commit()
    db.refresh(workspace)
    return workspace_summary(db, workspace, role)


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    workspace, _ = require_workspace(db, workspace_id, current.id, "owner")
    enforce_write_access(db, current.role)
    files = list(db.scalars(select(FileObject).where(FileObject.workspace_id == workspace_id)))
    file_ids = [file.id for file in files]
    if file_ids:
        # Shares reference files, so remove them before deleting the workspace tree.
        db.execute(delete(Share).where(Share.file_id.in_(file_ids)))
    versions = []
    for file in files:
        versions.extend(file.versions)
    release_quota_for_versions(db, versions)
    for version in versions:
        delete_ciphertext(db, version.storage_target, version.storage_key)
        db.delete(version)
    for file in files:
        db.delete(file)
    for member in list(
        db.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id))
    ):
        db.delete(member)
    db.delete(workspace)
    db.commit()
    return {"status": "deleted", "workspace_id": workspace_id}


@router.get("/{workspace_id}/members")
def list_members(
    workspace_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    require_workspace(db, workspace_id, current.id)
    members = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at)
    ).all()
    return [member_public(member, user) for member, user in members]


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    workspace_id: str,
    payload: MemberRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_workspace(db, workspace_id, current.id, "admin")
    enforce_write_access(db, current.role)
    role = payload.role.lower().strip()
    if role not in VALID_ROLES or role == "owner":
        raise HTTPException(status_code=422, detail="Role must be viewer, editor, or admin.")
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if user is None:
        raise HTTPException(status_code=404, detail="No registered user with that email.")
    existing = db.get(WorkspaceMember, (workspace_id, user.id))
    if existing:
        existing.role = role
    else:
        db.add(WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role))
    db.commit()
    return {"status": "added", "user_id": user.id, "role": role}


@router.patch("/{workspace_id}/members/{user_id}")
def update_member(
    workspace_id: str,
    user_id: str,
    payload: MemberUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _, actor_role = require_workspace(db, workspace_id, current.id, "admin")
    enforce_write_access(db, current.role)
    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Workspace member not found.")
    if member.role == "owner":
        raise HTTPException(status_code=403, detail="The workspace owner role cannot be changed.")
    if actor_role != "owner" and payload.role == "admin":
        raise HTTPException(status_code=403, detail="Only the owner can grant admin.")
    role = payload.role.lower().strip()
    if role not in VALID_ROLES or role == "owner":
        raise HTTPException(status_code=422, detail="Role must be viewer, editor, or admin.")
    member.role = role
    db.commit()
    return {"status": "updated", "user_id": user_id, "role": role}


@router.delete("/{workspace_id}/members/{user_id}")
def remove_member(
    workspace_id: str,
    user_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    _, actor_role = require_workspace(db, workspace_id, current.id, "admin")
    enforce_write_access(db, current.role)
    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Workspace member not found.")
    if member.role == "owner":
        raise HTTPException(status_code=403, detail="The owner cannot be removed.")
    if actor_role != "owner" and ROLE_RANK.get(member.role, 0) >= ROLE_RANK.get(actor_role, 0):
        raise HTTPException(status_code=403, detail="You cannot remove an equal or higher role.")
    db.delete(member)
    db.commit()
    return {"status": "removed", "user_id": user_id}
