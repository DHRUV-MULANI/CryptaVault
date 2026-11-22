"""Encrypted file upload, versioning, download, trash, and restore routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cryptavault_api.db import get_db
from cryptavault_api.deps.supabase import AuthenticatedUser, get_current_user
from cryptavault_api.models import FileObject, FileVersion, Share, User
from cryptavault_api.serializers import file_public, version_public
from cryptavault_api.services.policy import enforce_write_access, require_flag
from cryptavault_api.services.storage import (
    delete_ciphertext,
    download_ciphertext,
    upload_ciphertext,
)
from cryptavault_api.services.workspaces import (
    release_quota_for_versions,
    require_workspace,
)

router = APIRouter(prefix="/api", tags=["files"])


class RenameRequest(BaseModel):
    encrypted_meta: str = Field(min_length=1)
    meta_iv: str = Field(min_length=1)


def _current_version(db: Session, file: FileObject) -> FileVersion:
    version = db.scalar(
        select(FileVersion).where(
            FileVersion.file_id == file.id,
            FileVersion.version == file.current_version,
        )
    )
    if version is None:
        raise HTTPException(status_code=500, detail="File version metadata is missing.")
    return version


def _version_count(db: Session, file_id: str) -> int:
    rows = db.scalars(select(FileVersion).where(FileVersion.file_id == file_id)).all()
    return len(rows)


def _file_response(db: Session, file: FileObject) -> dict[str, Any]:
    return file_public(file, _current_version(db, file), _version_count(db, file.id))


@router.get("/workspaces/{workspace_id}/files")
def list_files(
    workspace_id: str,
    include_deleted: bool = Query(default=False),
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    require_workspace(db, workspace_id, current.id)
    query = (
        select(FileObject)
        .where(FileObject.workspace_id == workspace_id)
        .order_by(FileObject.updated_at.desc())
    )
    if not include_deleted:
        query = query.where(FileObject.deleted_at.is_(None))
    files = list(db.scalars(query).all())
    return [_file_response(db, file) for file in files]


@router.get("/workspaces/{workspace_id}/trash")
def list_trash(
    workspace_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    require_workspace(db, workspace_id, current.id)
    files = list(
        db.scalars(
            select(FileObject)
            .where(
                FileObject.workspace_id == workspace_id,
                FileObject.deleted_at.is_not(None),
            )
            .order_by(FileObject.deleted_at.desc())
        ).all()
    )
    return [_file_response(db, file) for file in files]


@router.post("/workspaces/{workspace_id}/files/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    workspace_id: str,
    ciphertext: UploadFile = File(...),
    file_id: str = Form(...),
    version: int = Form(...),
    encrypted_meta: str = Form(...),
    meta_iv: str = Form(...),
    wrapped_key: str = Form(...),
    wrapped_iv: str = Form(...),
    content_tag: str = Form(default=""),
    profile: str = Form(default="BALANCED"),
    storage_target: str | None = Form(default=None),
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace, _ = require_workspace(db, workspace_id, current.id, "editor")
    enforce_write_access(db, current.role)
    try:
        file_uuid = str(uuid.UUID(file_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="file_id must be a UUID.") from exc
    if version < 1:
        raise HTTPException(status_code=422, detail="version must be positive.")
    if version > 1:
        require_flag(db, "enable_versions", "Version history is disabled by the administrator.")

    payload = await ciphertext.read()
    if not payload:
        raise HTTPException(status_code=422, detail="Ciphertext payload is empty.")

    user = db.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.used_bytes + len(payload) > user.quota_bytes:
        raise HTTPException(status_code=413, detail="Storage quota exceeded.")

    file = db.get(FileObject, file_uuid)
    if file is not None and file.workspace_id != workspace_id:
        raise HTTPException(status_code=409, detail="File belongs to another workspace.")
    if file is not None:
        if file.deleted_at is not None:
            raise HTTPException(status_code=409, detail="Restore the file before adding a version.")
        if version != file.current_version + 1:
            raise HTTPException(
                status_code=409,
                detail=f"Next version must be {file.current_version + 1}.",
            )
    elif version != 1:
        raise HTTPException(status_code=422, detail="A new file must start at version 1.")

    existing_version = db.scalar(
        select(FileVersion).where(
            FileVersion.file_id == file_uuid,
            FileVersion.version == version,
        )
    )
    if existing_version is not None:
        raise HTTPException(status_code=409, detail="That version already exists.")

    storage_key = f"workspaces/{workspace_id}/files/{file_uuid}/v{version}.cv"
    stored = upload_ciphertext(
        db,
        workspace,
        storage_key,
        payload,
        preferred_target=storage_target,
    )

    try:
        if file is None:
            file = FileObject(
                id=file_uuid,
                workspace_id=workspace_id,
                owner_id=current.id,
                current_version=version,
            )
            db.add(file)
            db.flush()
        else:
            file.current_version = version
            file.updated_at = datetime.now(UTC)

        db.add(
            FileVersion(
                id=str(uuid.uuid4()),
                file_id=file_uuid,
                version=version,
                encrypted_meta=encrypted_meta,
                meta_iv=meta_iv,
                wrapped_key=wrapped_key,
                wrapped_iv=wrapped_iv,
                ciphertext_size=len(payload),
                content_tag=content_tag,
                profile=profile,
                storage_target=stored.target,
                storage_key=stored.key,
                created_by=current.id,
            )
        )
        user.used_bytes += len(payload)
        db.commit()
        db.refresh(file)
    except Exception:
        db.rollback()
        delete_ciphertext(db, stored.target, stored.key)
        raise

    return _file_response(db, file)


@router.get("/files/{file_id}")
def get_file(
    file_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id)
    return _file_response(db, file)


@router.get("/files/{file_id}/versions")
def list_versions(
    file_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id)
    versions = list(
        db.scalars(
            select(FileVersion)
            .where(FileVersion.file_id == file_id)
            .order_by(FileVersion.version.desc())
        ).all()
    )
    return [
        {**version_public(version), "is_current": version.version == file.current_version}
        for version in versions
    ]


@router.get("/files/{file_id}/download")
def download_file(
    file_id: str,
    version: int | None = Query(default=None),
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id)
    target_version = version or file.current_version
    record = db.scalar(
        select(FileVersion).where(
            FileVersion.file_id == file_id,
            FileVersion.version == target_version,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    stream, target_name = download_ciphertext(db, record.storage_target, record.storage_key)
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_id}.v{target_version}.cv"',
            "X-CV-Version": str(target_version),
            "X-CV-Storage-Target": target_name,
            "X-CV-Ciphertext-Size": str(record.ciphertext_size),
        },
    )


@router.patch("/files/{file_id}")
def rename_file(
    file_id: str,
    payload: RenameRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id, "editor")
    enforce_write_access(db, current.role)
    version = _current_version(db, file)
    version.encrypted_meta = payload.encrypted_meta
    version.meta_iv = payload.meta_iv
    file.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(file)
    return _file_response(db, file)


@router.post("/files/{file_id}/restore/{version}")
def restore_version(
    file_id: str,
    version: int,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id, "editor")
    enforce_write_access(db, current.role)
    require_flag(db, "enable_versions", "Version history is disabled by the administrator.")
    record = db.scalar(
        select(FileVersion).where(FileVersion.file_id == file_id, FileVersion.version == version)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    file.current_version = version
    file.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(file)
    return _file_response(db, file)


@router.delete("/files/{file_id}")
def trash_file(
    file_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id, "editor")
    enforce_write_access(db, current.role)
    file.deleted_at = datetime.now(UTC)
    db.commit()
    return {"status": "trashed", "file_id": file_id}


@router.post("/files/{file_id}/untrash")
def untrash_file(
    file_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id, "editor")
    enforce_write_access(db, current.role)
    file.deleted_at = None
    db.commit()
    return {"status": "restored", "file_id": file_id}


@router.delete("/files/{file_id}/permanent")
def permanently_delete_file(
    file_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    file = db.get(FileObject, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found.")
    require_workspace(db, file.workspace_id, current.id, "editor")
    enforce_write_access(db, current.role)
    versions = list(file.versions)
    if versions:
        db.execute(delete(Share).where(Share.file_id == file_id))
    release_quota_for_versions(db, versions)
    for version in versions:
        delete_ciphertext(db, version.storage_target, version.storage_key)
        db.delete(version)
    db.delete(file)
    db.commit()
    return {"status": "deleted", "file_id": file_id}
