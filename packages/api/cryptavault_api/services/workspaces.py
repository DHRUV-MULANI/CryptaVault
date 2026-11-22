"""Workspace membership and role helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from cryptavault_api.models import FileObject, FileVersion, User, Workspace, WorkspaceMember

ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3, "owner": 4}


def member_role(db: Session, workspace_id: str, user_id: str) -> str | None:
    member = db.get(WorkspaceMember, (workspace_id, user_id))
    return member.role if member else None


def get_workspace(db: Session, workspace_id: str) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return workspace


def require_workspace(
    db: Session, workspace_id: str, user_id: str, minimum: str = "viewer"
) -> tuple[Workspace, str]:
    workspace = get_workspace(db, workspace_id)
    role = member_role(db, workspace_id, user_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )
    if ROLE_RANK.get(role, 0) < ROLE_RANK[minimum]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires workspace role '{minimum}' or higher.",
        )
    return workspace, role


def workspace_stats(db: Session, workspace_id: str) -> dict[str, int]:
    row = db.execute(
        select(
            func.count(FileObject.id),
            func.coalesce(func.sum(FileVersion.ciphertext_size), 0),
        )
        .join(
            FileVersion,
            and_(
                FileVersion.file_id == FileObject.id,
                FileVersion.version == FileObject.current_version,
            ),
        )
        .where(
            FileObject.workspace_id == workspace_id,
            FileObject.deleted_at.is_(None),
        )
    ).one()
    return {"file_count": int(row[0] or 0), "total_bytes": int(row[1] or 0)}


def release_quota_for_versions(db: Session, versions: list[FileVersion]) -> int:
    """Credit ciphertext bytes back to whichever user created each version.

    Quota is charged to the uploader, not the file owner, so a workspace member
    who adds a version to another member's file must receive the refund.
    """
    freed_by_user: dict[str, int] = {}
    for version in versions:
        freed_by_user[version.created_by] = (
            freed_by_user.get(version.created_by, 0) + version.ciphertext_size
        )
    total = 0
    for user_id, amount in freed_by_user.items():
        user = db.get(User, user_id)
        if user is None:
            continue
        user.used_bytes = max(0, user.used_bytes - amount)
        total += amount
    return total


def workspace_summary(db: Session, workspace: Workspace, role: str) -> dict[str, Any]:
    stats = workspace_stats(db, workspace.id)
    return {
        "id": workspace.id,
        "name": workspace.name,
        "owner_id": workspace.owner_id,
        "role": role,
        "default_profile": workspace.default_profile,
        "storage_target": workspace.storage_target,
        "file_count": stats["file_count"],
        "total_bytes": stats["total_bytes"],
        "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
        "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else None,
    }
