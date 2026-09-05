"""Append-only tamper-evident audit log routes."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from cryptavault.adaptive.audit import AuditLog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from cryptavault_api.deps.supabase import AuthenticatedUser, get_admin_user, get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])

# In-memory store of audit records per user (backed by Supabase audit_logs table in production)
_AUDIT_STORE: list[dict[str, Any]] = []


class AppendAuditRequest(BaseModel):
    operation: str = Field(..., description="Action: e.g., ENCRYPT, DECRYPT, SHRED, SHARE")
    file_id: str
    file_hash: str
    profile_level: str
    signature: str = Field(..., description="Client Ed25519 signature over entry hash")
    public_key: str = Field(..., description="Client public key")
    extra: dict[str, Any] = Field(default_factory=dict)


class VerifyChainRequest(BaseModel):
    entries: list[dict[str, Any]]


@router.post("")
def append_audit_entry(
    payload: AppendAuditRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Append a new client-signed tamper-evident entry to the user's audit hash-chain."""
    user_entries = [e for e in _AUDIT_STORE if e["user_id"] == user.id]
    prev_hash = user_entries[-1]["entry_hash"] if user_entries else AuditLog.GENESIS_HASH

    from datetime import datetime
    from hashlib import sha256

    timestamp = datetime.now(UTC).isoformat()
    canonical_data = (
        f"{prev_hash}:{payload.operation}:{payload.file_id}:{payload.file_hash}:{timestamp}"
    )
    entry_hash = sha256(canonical_data.encode()).hexdigest()

    record = {
        "index": len(user_entries),
        "user_id": user.id,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
        "operation": payload.operation,
        "file_id": payload.file_id,
        "file_hash": payload.file_hash,
        "timestamp": timestamp,
        "signature": payload.signature,
        "public_key": payload.public_key,
        "extra": payload.extra,
    }
    _AUDIT_STORE.append(record)
    return {"status": "recorded", "entry_hash": entry_hash, "index": record["index"]}


@router.get("")
def list_user_audit(
    limit: int = 50,
    offset: int = 0,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve the current user's audit entries."""
    user_entries = [e for e in _AUDIT_STORE if e["user_id"] == user.id]
    paginated = user_entries[offset : offset + limit]
    return {
        "total": len(user_entries),
        "limit": limit,
        "offset": offset,
        "entries": paginated,
    }


@router.post("/verify")
def verify_audit_chain(payload: VerifyChainRequest) -> dict[str, Any]:
    """Cryptographically verify the continuity of an audit chain."""
    entries = payload.entries
    if not entries:
        return {"valid": True, "entries_checked": 0}

    expected_prev = AuditLog.GENESIS_HASH
    from hashlib import sha256

    for idx, entry in enumerate(entries):
        if entry.get("prev_hash") != expected_prev:
            return {
                "valid": False,
                "broken_at_index": idx,
                "reason": f"prev_hash mismatch. Expected {expected_prev}, got {entry.get('prev_hash')}",
            }
        canonical_data = f"{entry.get('prev_hash')}:{entry.get('operation')}:{entry.get('file_id')}:{entry.get('file_hash')}:{entry.get('timestamp')}"
        computed_hash = sha256(canonical_data.encode()).hexdigest()
        if computed_hash != entry.get("entry_hash"):
            return {
                "valid": False,
                "broken_at_index": idx,
                "reason": f"Hash integrity failure at entry {idx}",
            }
        expected_prev = computed_hash

    return {"valid": True, "entries_checked": len(entries), "chain_head": expected_prev}


@router.get("/admin/all")
def get_admin_audit_logs(
    limit: int = 100,
    admin: AuthenticatedUser = Depends(get_admin_user),
) -> dict[str, Any]:
    """Admin endpoint: view system-wide audit logs across all users."""
    return {
        "total": len(_AUDIT_STORE),
        "limit": limit,
        "entries": _AUDIT_STORE[:limit],
    }
