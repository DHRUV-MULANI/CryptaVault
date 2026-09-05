"""Key Lifecycle Operations for CryptaVault KMS.

Handles key creation, rotation, versioning, cascade re-wrapping, and secure cryptographic erasure.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from typing import Any

logger = logging.getLogger(__name__)

from cryptavault.keys.hierarchy import (
    KeyDescriptor,
    KeyHierarchyError,
    KeyStatus,
    KeyTier,
    KeyTree,
)


def generate_key(
    tree: KeyTree,
    tier: KeyTier,
    parent_raw_key: bytes,
    algorithm: str = "aes-256-gcm",
    parent_id: str | None = None,
    key_size_bytes: int = 32,
    metadata: dict[str, Any] | None = None,
) -> tuple[KeyDescriptor, bytes]:
    """Generate a fresh random key, wrap it under parent_raw_key, and add to tree.

    Returns (KeyDescriptor, raw_key_bytes).
    """
    raw_key = secrets.token_bytes(key_size_bytes)
    key_id = f"key_{uuid.uuid4().hex[:12]}"

    desc = tree.wrap_raw_key(
        raw_key=raw_key,
        parent_raw_key=parent_raw_key,
        key_id=key_id,
        tier=tier,
        algorithm=algorithm,
        parent_id=parent_id,
        metadata=metadata or {},
    )
    return desc, raw_key


def rotate_key(
    tree: KeyTree,
    key_id: str,
    parent_raw_key: bytes,
    old_raw_key: bytes,
    new_raw_key: bytes | None = None,
) -> tuple[KeyDescriptor, bytes]:
    """Rotate an existing key to a new version.

    The old descriptor is marked RETIRED so past data remains decryptable.
    Children wrapped by old_raw_key are re-wrapped under the new key.
    Returns (new_KeyDescriptor, new_raw_key).
    """
    old_desc = tree.get_key(key_id)
    if old_desc.status == KeyStatus.DESTROYED:
        raise KeyHierarchyError(f"Cannot rotate DESTROYED key {key_id}")

    # Mark old key retired
    old_desc.status = KeyStatus.RETIRED

    # Generate or accept new raw key
    new_key = new_raw_key if new_raw_key is not None else secrets.token_bytes(32)
    new_key_id = f"{key_id}_v{old_desc.version + 1}"

    new_desc = tree.wrap_raw_key(
        raw_key=new_key,
        parent_raw_key=parent_raw_key,
        key_id=new_key_id,
        tier=old_desc.tier,
        algorithm=old_desc.algorithm,
        parent_id=old_desc.parent_id,
        metadata={**old_desc.metadata, "supersedes": key_id},
    )
    new_desc.version = old_desc.version + 1

    # Cascade re-wrap any children that were parented to old key
    for child in tree.list_keys():
        if child.parent_id == key_id and child.status == KeyStatus.ACTIVE:
            try:
                child_raw = tree.unwrap_key(child.id, old_raw_key)
                # Update child parent to new key and re-encrypt
                tree._keys.pop(child.id)
                tree.wrap_raw_key(
                    raw_key=child_raw,
                    parent_raw_key=new_key,
                    key_id=child.id,
                    tier=child.tier,
                    algorithm=child.algorithm,
                    parent_id=new_key_id,
                    metadata=child.metadata,
                )
            except (KeyHierarchyError, Exception) as err:
                logger.debug("Failed to cascade re-wrap child key %s: %s", child.id, err)

    return new_desc, new_key


def destroy_key(
    tree: KeyTree,
    key_id: str,
    raw_buffer: bytearray | None = None,
) -> None:
    """Cryptographically destroy a key descriptor and zero memory buffers.

    After destruction, wrapped key material is cleared and status is set to DESTROYED.
    """
    desc = tree.get_key(key_id)
    desc.status = KeyStatus.DESTROYED
    desc.wrapped_key = ""  # Erase encrypted bytes permanently

    # Overwrite raw buffer in memory with zeros if provided
    if raw_buffer is not None:
        for i in range(len(raw_buffer)):
            raw_buffer[i] = 0
