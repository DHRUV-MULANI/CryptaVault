"""Feature-flag and maintenance policy helpers.

The admin console stores flags in ``system_settings``. Routes call these helpers
so a stored flag always has an effect instead of being display-only.
"""

from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from cryptavault_api.models import SystemSetting

DEFAULT_FLAGS: dict[str, bool] = {
    "enable_sharing": True,
    "enable_versions": True,
    "enable_cloud_connectors": True,
    "maintenance_mode": False,
    "demo_mode": True,
}

CLOUD_TARGET_KINDS = {"gdrive", "dropbox", "onedrive"}


def flag_value(db: Session, key: str) -> bool:
    """Return the stored flag value, falling back to the compiled default."""
    record = db.get(SystemSetting, key)
    if record is None:
        return DEFAULT_FLAGS.get(key, False)
    try:
        return bool(json.loads(record.value))
    except (TypeError, ValueError):
        return record.value.strip().lower() in {"1", "true", "yes", "on"}


def require_flag(db: Session, key: str, detail: str) -> None:
    """Reject the request when an administrator has disabled a feature."""
    if not flag_value(db, key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def enforce_write_access(db: Session, user_role: str) -> None:
    """Block non-admin mutations while maintenance mode is enabled."""
    if flag_value(db, "maintenance_mode") and user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CryptaVault is in maintenance mode. Mutating operations are paused.",
        )
