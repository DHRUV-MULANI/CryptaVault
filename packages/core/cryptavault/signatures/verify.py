"""Tamper & Corruption Detection for CryptaVault.

Provides structured file verification distinguishing between:
- VALID: Signature and content hash perfectly match.
- TAMPERED: File modified (hash or signature mismatch).
- CORRUPTED: File truncated or size does not match manifest.
- MISSING_KEY: Invalid, missing, or mismatched cryptographic key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from cryptavault.crypto.hash import Blake3
from cryptavault.signatures.base import MissingKeyError, SignatureContext


class VerificationStatus(str, Enum):
    """Categorized status of a file integrity verification."""

    VALID = "VALID"
    TAMPERED = "TAMPERED"
    CORRUPTED = "CORRUPTED"
    MISSING_KEY = "MISSING_KEY"


@dataclass(frozen=True)
class VerificationResult:
    """Detailed diagnostic report for a file verification."""

    status: VerificationStatus
    file_path: str
    message: str
    actual_size_bytes: int
    expected_size_bytes: int | None = None
    actual_hash: str | None = None
    expected_hash: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.status == VerificationStatus.VALID


def verify_file(
    file_path: str | Path,
    signature: bytes | None,
    public_key: bytes | None,
    algorithm: str = "ed25519",
    expected_hash: str | None = None,
    expected_size_bytes: int | None = None,
) -> VerificationResult:
    """Analyze a file for integrity, corruption, or active tampering."""
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        return VerificationResult(
            status=VerificationStatus.CORRUPTED,
            file_path=str(path),
            message="File does not exist on disk",
            actual_size_bytes=0,
            expected_size_bytes=expected_size_bytes,
            diagnostics={"error": "FileNotFound"},
        )

    actual_size = path.stat().st_size

    # Check for truncation / size mismatch
    if expected_size_bytes is not None and actual_size != expected_size_bytes:
        return VerificationResult(
            status=VerificationStatus.CORRUPTED,
            file_path=str(path),
            message=f"File size mismatch: expected {expected_size_bytes} bytes, got {actual_size} bytes (possible truncation)",
            actual_size_bytes=actual_size,
            expected_size_bytes=expected_size_bytes,
            diagnostics={
                "size_delta": actual_size - expected_size_bytes,
                "is_truncated": actual_size < expected_size_bytes,
            },
        )

    # Compute actual BLAKE3 content hash
    hasher = Blake3()
    stream_hasher = hasher.streaming()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            stream_hasher.update(chunk)
    actual_hash = stream_hasher.hexdigest()

    # Check content hash if expected hash was provided
    if expected_hash is not None and actual_hash.lower() != expected_hash.strip().lower():
        return VerificationResult(
            status=VerificationStatus.TAMPERED,
            file_path=str(path),
            message="Content hash mismatch: file content has been altered",
            actual_size_bytes=actual_size,
            expected_size_bytes=expected_size_bytes,
            actual_hash=actual_hash,
            expected_hash=expected_hash,
            diagnostics={"tamper_type": "hash_mismatch"},
        )

    # Check key and signature
    if public_key is None or len(public_key) == 0:
        return VerificationResult(
            status=VerificationStatus.MISSING_KEY,
            file_path=str(path),
            message="Verification public key was not provided or is empty",
            actual_size_bytes=actual_size,
            expected_size_bytes=expected_size_bytes,
            actual_hash=actual_hash,
            expected_hash=expected_hash,
            diagnostics={"error": "MissingPublicKey"},
        )

    if signature is None or len(signature) == 0:
        return VerificationResult(
            status=VerificationStatus.TAMPERED,
            file_path=str(path),
            message="Cryptographic signature is missing or zero-length",
            actual_size_bytes=actual_size,
            expected_size_bytes=expected_size_bytes,
            actual_hash=actual_hash,
            expected_hash=expected_hash,
            diagnostics={"error": "EmptySignature"},
        )

    try:
        ctx = SignatureContext(algorithm=algorithm, public_key=public_key)
        # Verify directly using the computed BLAKE3 digest to avoid re-reading disk
        digest_bytes = bytes.fromhex(actual_hash)
        valid = ctx.signer.verify(public_key, digest_bytes, signature)
    except MissingKeyError as exc:
        return VerificationResult(
            status=VerificationStatus.MISSING_KEY,
            file_path=str(path),
            message=str(exc),
            actual_size_bytes=actual_size,
            expected_size_bytes=expected_size_bytes,
            actual_hash=actual_hash,
            expected_hash=expected_hash,
            diagnostics={"error": "MissingKeyError"},
        )
    except Exception as exc:  # noqa: BLE001
        return VerificationResult(
            status=VerificationStatus.TAMPERED,
            file_path=str(path),
            message=f"Signature verification failed with error: {exc}",
            actual_size_bytes=actual_size,
            expected_size_bytes=expected_size_bytes,
            actual_hash=actual_hash,
            expected_hash=expected_hash,
            diagnostics={"error": str(exc)},
        )

    if not valid:
        return VerificationResult(
            status=VerificationStatus.TAMPERED,
            file_path=str(path),
            message="Cryptographic signature verification rejected: file or signature was modified",
            actual_size_bytes=actual_size,
            expected_size_bytes=expected_size_bytes,
            actual_hash=actual_hash,
            expected_hash=expected_hash,
            diagnostics={"tamper_type": "invalid_signature"},
        )

    return VerificationResult(
        status=VerificationStatus.VALID,
        file_path=str(path),
        message="Signature and content hash verified successfully",
        actual_size_bytes=actual_size,
        expected_size_bytes=expected_size_bytes,
        actual_hash=actual_hash,
        expected_hash=expected_hash,
        diagnostics={"algorithm": algorithm},
    )
