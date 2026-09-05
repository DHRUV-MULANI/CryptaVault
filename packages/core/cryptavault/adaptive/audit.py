"""Tamper-Evident Audit Logging for CryptaVault.

Implements an append-only, cryptographic hash-chained audit trail.
Each log entry binds to the hash of the preceding entry, making historical
tampering, record deletion, or unauthorized insertion mathematically detectable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from cryptavault.crypto.asymmetric import Ed25519Signer


@dataclass
class AuditEntry:
    """Single immutable audit log entry."""

    index: int
    timestamp: str
    action: str
    file_id: str
    key_id: str
    profile: str
    outcome: str
    details: dict[str, Any]
    prev_hash: str
    entry_hash: str = ""
    signature_hex: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 digest over canonical JSON representation."""
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "action": self.action,
            "file_id": self.file_id,
            "key_id": self.key_id,
            "profile": self.profile,
            "outcome": self.outcome,
            "details": self.details,
            "prev_hash": self.prev_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


class AuditLog:
    """Tamper-evident append-only cryptographic audit logger."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(
        self, signer: Ed25519Signer | None = None, private_key: bytes | None = None
    ) -> None:
        self._entries: list[AuditEntry] = []
        self._signer = signer
        self._private_key = private_key

    @property
    def entries(self) -> list[AuditEntry]:
        """Return all audit entries."""
        return list(self._entries)

    def append(
        self,
        action: str,
        file_id: str = "",
        key_id: str = "",
        profile: str = "",
        outcome: str = "SUCCESS",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Append an entry, hash-chaining to the previous entry."""
        prev_hash = self._entries[-1].entry_hash if self._entries else self.GENESIS_HASH
        idx = len(self._entries)
        timestamp = datetime.now(UTC).isoformat()

        entry = AuditEntry(
            index=idx,
            timestamp=timestamp,
            action=action,
            file_id=file_id,
            key_id=key_id,
            profile=profile,
            outcome=outcome,
            details=details or {},
            prev_hash=prev_hash,
        )
        entry.entry_hash = entry.compute_hash()

        # Optional signature
        if self._signer and self._private_key:
            sig = self._signer.sign(self._private_key, entry.entry_hash.encode("utf-8"))
            entry.signature_hex = sig.hex()

        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """Verify the cryptographic hash-chain across all entries.

        Returns True if all hashes match and prev_hash links are unbroken.
        """
        for i, entry in enumerate(self._entries):
            # 1. Verify prev_hash link
            expected_prev = self._entries[i - 1].entry_hash if i > 0 else self.GENESIS_HASH
            if entry.prev_hash != expected_prev:
                return False

            # 2. Verify entry hash
            if entry.compute_hash() != entry.entry_hash:
                return False

        return True

    def to_json(self) -> str:
        """Export audit log to JSON."""
        return json.dumps([asdict(e) for e in self._entries], indent=2)

    @classmethod
    def from_json(cls, data: str) -> AuditLog:
        """Construct audit log from JSON string."""
        raw_list = json.loads(data)
        log = cls()
        for r in raw_list:
            entry = AuditEntry(**r)
            log._entries.append(entry)
        return log
