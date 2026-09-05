"""Metadata Privacy Policies and Sanitization for CryptaVault."""

from __future__ import annotations

from datetime import UTC, datetime

from cryptavault.adaptive.profiles import SecurityProfile
from cryptavault.metadata.model import FileMetadata


def apply_metadata_privacy_policy(
    metadata: FileMetadata,
    profile: SecurityProfile,
) -> FileMetadata:
    """Sanitize and apply privacy protections to file metadata based on active security profile.

    For MAXIMUM profile:
    - Normalizes timestamps to midnight UTC to prevent clock-skew correlation and activity fingerprinting.
    - Strips non-essential filesystem attributes.
    """
    if profile.level.value == "MAXIMUM":
        # Round timestamp to 00:00:00 UTC
        try:
            dt = datetime.fromisoformat(metadata.created_at)
            normalized_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
            norm_str = normalized_dt.isoformat()
            metadata.created_at = norm_str
            metadata.modified_at = norm_str
        except (ValueError, TypeError):
            pass

        # Scrub device-specific extra attributes
        metadata.extra_attributes = {}

    return metadata
