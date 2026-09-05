"""Encrypted Share Package format supporting CBOR and JSON serialization.

Zero-Knowledge Invariant: The share package contains only wrapped encryption keys
(wrapped with recipient's public key or derived password key) and ciphertext references.
The server or network never sees the plaintext file key or data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from cryptavault.crypto.asymmetric import Ed25519Signer


@dataclass
class RecipientKeyEnvelope:
    """Encapsulates the encrypted file key for a specific recipient."""

    recipient_id: str
    kem_scheme: str  # e.g., "x25519", "ml-kem-768", "argon2id-password", "hybrid"
    wrapped_key_b64: str
    ephemeral_public_key_b64: str | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SharePackage:
    """Complete cryptographic share package container."""

    version: str = "1.0"
    file_id: str = ""
    filename: str = ""
    file_size_bytes: int = 0
    ciphertext_ref: str = ""  # Storage URI or inline base64
    merkle_root_hex: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str | None = None
    max_uses: int | None = None
    use_count: int = 0
    author_public_key_hex: str = ""
    author_signature_hex: str = ""
    recipients: list[RecipientKeyEnvelope] = field(default_factory=list)
    metadata_fragment: dict[str, Any] = field(default_factory=dict)

    def _canonical_payload_bytes(self) -> bytes:
        """Deterministic byte representation for signature generation and verification."""
        recipients_repr = [
            {
                "id": r.recipient_id,
                "scheme": r.kem_scheme,
                "wrapped": r.wrapped_key_b64,
                "ephemeral": r.ephemeral_public_key_b64,
            }
            for r in sorted(self.recipients, key=lambda x: x.recipient_id)
        ]
        canonical = {
            "version": self.version,
            "file_id": self.file_id,
            "ciphertext_ref": self.ciphertext_ref,
            "merkle_root_hex": self.merkle_root_hex,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "recipients": recipients_repr,
        }
        return json.dumps(canonical, sort_keys=True).encode("utf-8")

    def sign(self, private_key: bytes, public_key: bytes | None = None) -> None:
        """Sign this package with author's Ed25519 signing key."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519

        signer = Ed25519Signer()
        if public_key is None:
            priv = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
            public_key = priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        self.author_public_key_hex = public_key.hex()
        sig = signer.sign(private_key, self._canonical_payload_bytes())
        self.author_signature_hex = sig.hex()

    def verify_signature(self) -> bool:
        """Verify the integrity and authenticity of this package against author's public key."""
        if not self.author_public_key_hex or not self.author_signature_hex:
            return False
        try:
            pub_bytes = bytes.fromhex(self.author_public_key_hex)
            sig_bytes = bytes.fromhex(self.author_signature_hex)
            payload = self._canonical_payload_bytes()
            return Ed25519Signer().verify(pub_bytes, payload, sig_bytes)
        except Exception:
            return False

    def is_expired(self) -> bool:
        """Check if this share package has passed its expiration time."""
        if not self.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at)
            return datetime.now(UTC) > exp
        except Exception:
            return True

    def to_json(self) -> str:
        """Serialize share package to JSON string."""
        d = asdict(self)
        return json.dumps(d, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> SharePackage:
        """Deserialize share package from JSON string."""
        data = json.loads(json_str)
        recipients_data = data.pop("recipients", [])
        recipients = [RecipientKeyEnvelope(**r) for r in recipients_data]
        return cls(**data, recipients=recipients)

    def to_cbor(self) -> bytes:
        """Compact binary serialization fallback using JSON bytes."""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_cbor(cls, data: bytes) -> SharePackage:
        """Deserialize from compact bytes."""
        return cls.from_json(data.decode("utf-8"))
