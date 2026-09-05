"""Key Hierarchy & Tree Structures for CryptaVault KMS.

Implements the multi-tier key hierarchy:
- MASTER: Root user key derived client-side via Argon2id (never leaves client device).
- DATA: Per-file / per-folder symmetric encryption keys (wrapped by Master or parent key).
- SHARE: Ephemeral or recipient-wrapped keys for secure sharing tokens.
- SESSION: Transient in-memory keys for authenticated streaming tunnels.

Enforces zero-knowledge storage: serialized key trees only ever contain encrypted (wrapped) keys.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from cryptavault.crypto.symmetric import AES256GCM, InvalidTagError


class KeyTier(str, Enum):
    """Hierarchical key classification."""

    MASTER = "MASTER"
    DATA = "DATA"
    SHARE = "SHARE"
    SESSION = "SESSION"


class KeyStatus(str, Enum):
    """Lifecycle status of a cryptographic key."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    DESTROYED = "DESTROYED"


class KeyHierarchyError(Exception):
    """Base exception for key hierarchy operations."""


class KeyNotFoundError(KeyHierarchyError):
    """Raised when looking up an unregistered key ID."""


class KeyWrappingError(KeyHierarchyError):
    """Raised when encrypting or decrypting wrapped keys fails."""


@dataclass
class KeyDescriptor:
    """Metadata and wrapped representation of a cryptographic key."""

    id: str
    tier: KeyTier
    algorithm: str
    version: int = 1
    status: KeyStatus = KeyStatus.ACTIVE
    parent_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    wrapped_key: str = ""  # Hex-encoded: [12-byte nonce] + [ciphertext] + [16-byte tag]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata and wrapped key for storage/transport."""
        return {
            "id": self.id,
            "tier": self.tier.value,
            "algorithm": self.algorithm,
            "version": self.version,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "wrapped_key": self.wrapped_key,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KeyDescriptor:
        """Construct descriptor from dictionary."""
        return cls(
            id=data["id"],
            tier=KeyTier(data["tier"]),
            algorithm=data["algorithm"],
            version=data.get("version", 1),
            status=KeyStatus(data.get("status", KeyStatus.ACTIVE.value)),
            parent_id=data.get("parent_id"),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            wrapped_key=data.get("wrapped_key", ""),
            metadata=data.get("metadata", {}),
        )


class KeyTree:
    """Manages the hierarchy of wrapped keys and parent-child wrapping relations."""

    def __init__(self) -> None:
        self._keys: dict[str, KeyDescriptor] = {}
        self._cipher = AES256GCM()

    def add_key(self, descriptor: KeyDescriptor) -> None:
        """Register a key descriptor in the tree."""
        if descriptor.id in self._keys:
            raise KeyHierarchyError(f"Key ID {descriptor.id} already exists in tree")
        if descriptor.parent_id and descriptor.parent_id not in self._keys:
            raise KeyHierarchyError(
                f"Parent key {descriptor.parent_id} does not exist in hierarchy"
            )
        self._keys[descriptor.id] = descriptor

    def get_key(self, key_id: str) -> KeyDescriptor:
        """Retrieve key descriptor by ID."""
        if key_id not in self._keys:
            raise KeyNotFoundError(f"Key {key_id} not found in hierarchy")
        return self._keys[key_id]

    def find_root(self) -> KeyDescriptor | None:
        """Find the root MASTER key in the tree (key with no parent)."""
        for k in self._keys.values():
            if k.tier == KeyTier.MASTER and k.parent_id is None:
                return k
        return None

    def list_keys(self) -> list[KeyDescriptor]:
        """Return list of all keys in tree."""
        return list(self._keys.values())

    def wrap_raw_key(
        self,
        raw_key: bytes,
        parent_raw_key: bytes,
        key_id: str,
        tier: KeyTier = KeyTier.DATA,
        algorithm: str = "aes-256-gcm",
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KeyDescriptor:
        """Encrypt raw_key with parent_raw_key using AES-256-GCM and store in tree."""
        aad = f"cryptavault:keywrap:v1:{key_id}".encode()
        nonce, ciphertext = self._cipher.encrypt_auto_nonce(parent_raw_key, raw_key, aad)
        wrapped_payload = nonce + ciphertext

        desc = KeyDescriptor(
            id=key_id,
            tier=tier,
            algorithm=algorithm,
            parent_id=parent_id,
            wrapped_key=wrapped_payload.hex(),
            metadata=metadata or {},
        )
        self.add_key(desc)
        return desc

    def unwrap_key(self, key_id: str, parent_raw_key: bytes) -> bytes:
        """Decrypt wrapped key payload using parent_raw_key."""
        desc = self.get_key(key_id)
        if desc.status == KeyStatus.DESTROYED:
            raise KeyHierarchyError(f"Cannot unwrap key {key_id}: key has been DESTROYED")

        wrapped_bytes = bytes.fromhex(desc.wrapped_key)
        if len(wrapped_bytes) < 12 + 16:
            raise KeyWrappingError("Wrapped key payload is corrupt or truncated")

        nonce = wrapped_bytes[:12]
        ciphertext = wrapped_bytes[12:]
        aad = f"cryptavault:keywrap:v1:{key_id}".encode()

        try:
            return self._cipher.decrypt(parent_raw_key, nonce, ciphertext, aad)
        except InvalidTagError as exc:
            raise KeyWrappingError(
                f"Failed to unwrap key {key_id}: parent key invalid or ciphertext tampered"
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        """Serialize tree containing ONLY wrapped key descriptors."""
        return {
            "keys": {k_id: desc.to_dict() for k_id, desc in self._keys.items()},
        }

    def to_json(self, indent: int = 2) -> str:
        """Export tree as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KeyTree:
        """Reconstitute tree from serialized wrapped descriptors."""
        tree = cls()
        keys_dict = data.get("keys", {})
        # Insert parents before children
        for k_id, k_data in keys_dict.items():
            desc = KeyDescriptor.from_dict(k_data)
            tree._keys[k_id] = desc
        return tree

    @classmethod
    def from_json(cls, json_str: str) -> KeyTree:
        """Load tree from JSON string."""
        return cls.from_dict(json.loads(json_str))
