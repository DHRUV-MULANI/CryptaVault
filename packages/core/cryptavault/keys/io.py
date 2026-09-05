"""Key Import and Export Interoperability for CryptaVault KMS.

Provides standard PEM (PKCS#8) export/import with optional password encryption,
raw symmetric key import/export, format auto-detection, and key-strength validation.
"""

from __future__ import annotations

import re
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from cryptavault.crypto.asymmetric import KeyPair
from cryptavault.keys.hierarchy import KeyDescriptor, KeyTier


class KeyError(Exception):
    """Base exception for key input/output errors."""


class WeakKeyError(KeyError):
    """Raised when an imported key does not meet security threshold standards."""


class InvalidFormatError(KeyError):
    """Raised when key data cannot be parsed according to specified format."""


def validate_key_strength(raw_key: bytes, algorithm: str) -> None:
    """Validate that key meets minimum enterprise security thresholds.

    Rules:
    - Symmetric keys must be at least 256 bits (32 bytes).
    - RSA keys must be at least 2048 bits (4096 bits recommended).
    """
    algo = algorithm.lower()
    if "aes" in algo or "chacha" in algo or algo in ("symmetric", "data"):
        if len(raw_key) < 32:
            raise WeakKeyError(
                f"Symmetric key is too weak: minimum 256 bits (32 bytes) required, got {len(raw_key) * 8} bits"
            )
    elif "rsa" in algo:
        # Check RSA bit length
        try:
            priv = serialization.load_der_private_key(raw_key, password=None)
            if isinstance(priv, rsa.RSAPrivateKey) and priv.key_size < 2048:
                raise WeakKeyError(
                    f"RSA key is too weak: minimum 2048 bits required, got {priv.key_size} bits"
                )
        except (ValueError, TypeError):
            pass


def export_key(
    raw_key: bytes,
    algorithm: str,
    export_format: str = "pem",
    password: bytes | None = None,
    public_key: bytes | None = None,
) -> bytes:
    """Export key material to standardized format (PEM for asymmetric, raw/hex for symmetric)."""
    fmt = export_format.strip().lower()

    if fmt == "pem":
        if public_key is None:
            # For symmetric keys, PEM is not natively standard; export as PKCS#8 or raise
            raise InvalidFormatError(
                "PEM export requires an asymmetric keypair. For symmetric keys, use 'raw' or 'hex'."
            )
        pair = KeyPair(algorithm=algorithm, public_bytes=public_key, private_bytes=raw_key)
        _, priv_pem = pair.to_pem(password=password)
        return priv_pem
    elif fmt == "raw":
        return raw_key
    elif fmt == "hex":
        return raw_key.hex().encode("utf-8")
    else:
        raise InvalidFormatError(
            f"Unsupported export format: {export_format}. Use 'pem', 'raw', or 'hex'."
        )


def import_key(
    data: bytes,
    algorithm: str = "aes-256-gcm",
    import_format: str | None = None,
    password: bytes | None = None,
    tier: KeyTier = KeyTier.DATA,
) -> tuple[KeyDescriptor, bytes]:
    """Import key material with automatic format detection and strength validation.

    Returns (KeyDescriptor, raw_key_bytes).
    """
    detected_format = import_format

    # Auto-detect format if not explicitly passed
    if detected_format is None:
        trimmed = data.strip()
        if trimmed.startswith(b"-----BEGIN"):
            detected_format = "pem"
        elif re.fullmatch(b"[0-9a-fA-F]+", trimmed) and len(trimmed) % 2 == 0:
            detected_format = "hex"
        else:
            detected_format = "raw"

    raw_key: bytes

    if detected_format == "pem":
        try:
            priv_obj = serialization.load_pem_private_key(data, password=password)
            raw_key = priv_obj.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        except Exception as exc:
            raise InvalidFormatError(f"Failed to parse PEM key: {exc}") from exc
    elif detected_format == "hex":
        try:
            raw_key = bytes.fromhex(data.decode("utf-8").strip())
        except Exception as exc:
            raise InvalidFormatError(f"Failed to decode hex key: {exc}") from exc
    elif detected_format == "raw":
        raw_key = data
    else:
        raise InvalidFormatError(f"Unknown key format: {detected_format}")

    # Enforce strength validation
    validate_key_strength(raw_key, algorithm)

    key_id = f"imported_{uuid.uuid4().hex[:10]}"
    desc = KeyDescriptor(
        id=key_id,
        tier=tier,
        algorithm=algorithm,
        metadata={"imported": True, "format": detected_format},
    )
    return desc, raw_key
