"""Small response serializers shared by API routes."""

from __future__ import annotations

from typing import Any

from cryptavault_api.models import (
    FileObject,
    FileVersion,
    Share,
    StorageTarget,
    User,
    Workspace,
    WorkspaceMember,
)


def user_public(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "suspended": user.suspended,
        "quota_bytes": user.quota_bytes,
        "used_bytes": user.used_bytes,
        "default_profile": user.default_profile,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def member_public(member: WorkspaceMember, user: User) -> dict[str, Any]:
    return {
        "user_id": member.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": member.role,
        "joined_at": member.created_at.isoformat() if member.created_at else None,
    }


def workspace_public(
    workspace: Workspace,
    role: str,
    *,
    file_count: int = 0,
    total_bytes: int = 0,
) -> dict[str, Any]:
    return {
        "id": workspace.id,
        "name": workspace.name,
        "owner_id": workspace.owner_id,
        "role": role,
        "default_profile": workspace.default_profile,
        "storage_target": workspace.storage_target,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
        "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else None,
    }


def version_public(version: FileVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "file_id": version.file_id,
        "version": version.version,
        "encrypted_meta": version.encrypted_meta,
        "meta_iv": version.meta_iv,
        "wrapped_key": version.wrapped_key,
        "wrapped_iv": version.wrapped_iv,
        "ciphertext_size": version.ciphertext_size,
        "content_tag": version.content_tag,
        "profile": version.profile,
        "storage_target": version.storage_target,
        "storage_key": version.storage_key,
        "created_by": version.created_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def file_public(file: FileObject, version: FileVersion, version_count: int = 1) -> dict[str, Any]:
    return {
        "id": file.id,
        "workspace_id": file.workspace_id,
        "owner_id": file.owner_id,
        "current_version": file.current_version,
        "version_count": version_count,
        "deleted_at": file.deleted_at.isoformat() if file.deleted_at else None,
        "created_at": file.created_at.isoformat() if file.created_at else None,
        "updated_at": file.updated_at.isoformat() if file.updated_at else None,
        **{
            key: version_public(version)[key]
            for key in (
                "encrypted_meta",
                "meta_iv",
                "wrapped_key",
                "wrapped_iv",
                "ciphertext_size",
                "content_tag",
                "profile",
                "storage_target",
                "storage_key",
            )
        },
    }


def share_public(share: Share, share_url: str, *, pin: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "token": share.token,
        "file_id": share.file_id,
        "version": share.version,
        "share_url": share_url,
        "recipient_email": share.recipient_email,
        "created_at": share.created_at.isoformat() if share.created_at else None,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
        "max_uses": share.max_uses,
        "uses": share.uses,
        "remaining_uses": max(0, share.max_uses - share.uses),
        "password_protected": bool(share.password_hash),
        "pin_protected": bool(share.pin_hash),
        "revoked": share.revoked,
    }
    if pin is not None:
        data["pin"] = pin
    return data


def target_public(target: StorageTarget, *, include_config: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": target.name,
        "kind": target.kind,
        "enabled": target.enabled,
        "is_default": target.is_default,
        "created_at": target.created_at.isoformat() if target.created_at else None,
    }
    if include_config:
        result["config"] = target.config_json
    return result
