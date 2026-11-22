"""Dashboard aggregates for the dynamic web portal and admin console."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from cryptavault_api.db import get_db
from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user
from cryptavault_api.models import (
    FileObject,
    FileVersion,
    Share,
    StorageTarget,
    User,
    Workspace,
    WorkspaceMember,
)
from cryptavault_api.serializers import file_public, user_public

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _user_workspace_ids(db: Session, user_id: str) -> list[str]:
    return list(
        db.scalars(
            select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
        ).all()
    )


def _current_versions() -> Any:
    return and_(
        FileVersion.file_id == FileObject.id,
        FileVersion.version == FileObject.current_version,
    )


@router.get("")
def dashboard(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace_ids = _user_workspace_ids(db, current.id)
    files_total = 0
    trash_total = 0
    bytes_total = 0
    recent: list[dict[str, Any]] = []
    storage_rows: list[dict[str, Any]] = []
    if workspace_ids:
        files_total = int(
            db.scalar(
                select(func.count(FileObject.id)).where(
                    FileObject.workspace_id.in_(workspace_ids),
                    FileObject.deleted_at.is_(None),
                )
            )
            or 0
        )
        trash_total = int(
            db.scalar(
                select(func.count(FileObject.id)).where(
                    FileObject.workspace_id.in_(workspace_ids),
                    FileObject.deleted_at.is_not(None),
                )
            )
            or 0
        )
        bytes_total = int(
            db.scalar(
                select(func.coalesce(func.sum(FileVersion.ciphertext_size), 0))
                .join(FileObject, _current_versions())
                .where(
                    FileObject.workspace_id.in_(workspace_ids),
                    FileObject.deleted_at.is_(None),
                )
            )
            or 0
        )
        recent_files = list(
            db.scalars(
                select(FileObject)
                .where(
                    FileObject.workspace_id.in_(workspace_ids),
                    FileObject.deleted_at.is_(None),
                )
                .order_by(FileObject.updated_at.desc())
                .limit(8)
            ).all()
        )
        for file in recent_files:
            version = db.scalar(
                select(FileVersion).where(
                    FileVersion.file_id == file.id,
                    FileVersion.version == file.current_version,
                )
            )
            if version:
                recent.append(file_public(file, version))
        storage_rows = [
            {"target": row[0], "files": int(row[1] or 0), "bytes": int(row[2] or 0)}
            for row in db.execute(
                select(
                    FileVersion.storage_target,
                    func.count(FileVersion.id),
                    func.coalesce(func.sum(FileVersion.ciphertext_size), 0),
                )
                .join(FileObject, _current_versions())
                .where(
                    FileObject.workspace_id.in_(workspace_ids),
                    FileObject.deleted_at.is_(None),
                )
                .group_by(FileVersion.storage_target)
            ).all()
        ]

    active_shares = int(
        db.scalar(
            select(func.count(Share.token)).where(
                Share.owner_id == current.id,
                Share.revoked.is_(False),
                Share.uses < Share.max_uses,
            )
        )
        or 0
    )
    return {
        "workspaces": len(workspace_ids),
        "files": files_total,
        "trash": trash_total,
        "bytes": bytes_total,
        "active_shares": active_shares,
        "storage": storage_rows,
        "recent_files": recent,
        "quota_bytes": next(
            (user.quota_bytes for user in [db.get(User, current.id)] if user is not None),
            0,
        ),
        "used_bytes": next(
            (user.used_bytes for user in [db.get(User, current.id)] if user is not None),
            0,
        ),
    }


@router.get("/admin")
def admin_dashboard(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if current.role != "admin":
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")
    users = list(db.scalars(select(User).order_by(User.created_at.desc())).all())
    files_total = int(db.scalar(select(func.count(FileObject.id))) or 0)
    bytes_total = int(
        db.scalar(select(func.coalesce(func.sum(FileVersion.ciphertext_size), 0))) or 0
    )
    shares_total = int(db.scalar(select(func.count(Share.token))) or 0)
    workspaces_total = int(db.scalar(select(func.count(Workspace.id))) or 0)
    targets = list(db.scalars(select(StorageTarget).order_by(StorageTarget.name)).all())
    return {
        "users_total": len(users),
        "users_active": len([user for user in users if not user.suspended]),
        "files_total": files_total,
        "bytes_total": bytes_total,
        "shares_total": shares_total,
        "workspaces_total": workspaces_total,
        "storage_targets": [
            {
                "name": target.name,
                "kind": target.kind,
                "enabled": target.enabled,
                "is_default": target.is_default,
            }
            for target in targets
        ],
        "recent_users": [user_public(user) for user in users[:8]],
    }
