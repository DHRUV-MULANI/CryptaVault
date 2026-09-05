"""Cryptographic Hash Primitives for CryptaVault.

Implements one-shot and incremental streaming hashing for:
- SHA-256 (NIST FIPS 180-4)
- SHA3-512 (NIST FIPS 202)
- BLAKE3 (High-speed tree hash with arbitrary output length)

All implementations adhere to the HashAlgorithm and StreamingHash plugin interfaces.
"""

from __future__ import annotations

import hashlib
from typing import Any, ClassVar

import blake3

from cryptavault.plugins.registry import (
    HashAlgorithm,
    StreamingHash,
    register_hash,
)


class HashError(Exception):
    """Base exception for hashing failures."""


# ====================================================================
# Streaming Hash Implementations
# ====================================================================


class GenericStreamingHash(StreamingHash):
    """Wrapper around hashlib hash objects."""

    def __init__(self, hash_obj: Any) -> None:
        self._hasher = hash_obj

    def update(self, data: bytes) -> None:
        """Feed bytes into the running digest."""
        self._hasher.update(data)

    def digest(self) -> bytes:
        """Return the current digest bytes without mutating state."""
        return bytes(self._hasher.copy().digest())

    def hexdigest(self) -> str:
        """Return hex-encoded digest string."""
        return str(self._hasher.copy().hexdigest())


class Blake3StreamingHash(StreamingHash):
    """Wrapper around blake3 streaming hasher with variable output length."""

    def __init__(self, size: int = 32) -> None:
        self._hasher = blake3.blake3()
        self.size = size

    def update(self, data: bytes) -> None:
        """Feed bytes into BLAKE3 tree hasher."""
        self._hasher.update(data)

    def digest(self, length: int | None = None) -> bytes:
        """Return digest of requested length (defaults to initialized size)."""
        out_len = length if length is not None else self.size
        return self._hasher.copy().digest(length=out_len)

    def hexdigest(self, length: int | None = None) -> str:
        """Return hex-encoded digest string."""
        out_len = length if length is not None else self.size
        return self._hasher.copy().hexdigest(length=out_len)


# ====================================================================
# Hash Algorithm Plugins
# ====================================================================


@register_hash("sha256")
class Sha256(HashAlgorithm):
    """SHA-256 cryptographic hash (32-byte digest)."""

    name: ClassVar[str] = "sha256"

    def digest(self, data: bytes, size: int | None = None) -> bytes:
        """Compute one-shot SHA-256 digest."""
        res = hashlib.sha256(data).digest()
        if size is not None:
            return res[:size]
        return res

    def streaming(self) -> StreamingHash:
        """Return incremental streaming hasher."""
        return GenericStreamingHash(hashlib.sha256())


@register_hash("sha3-512")
class Sha3512(HashAlgorithm):
    """SHA3-512 cryptographic hash (64-byte digest)."""

    name: ClassVar[str] = "sha3-512"

    def digest(self, data: bytes, size: int | None = None) -> bytes:
        """Compute one-shot SHA3-512 digest."""
        res = hashlib.sha3_512(data).digest()
        if size is not None:
            return res[:size]
        return res

    def streaming(self) -> StreamingHash:
        """Return incremental streaming hasher."""
        return GenericStreamingHash(hashlib.sha3_512())


@register_hash("blake3")
class Blake3(HashAlgorithm):
    """BLAKE3 cryptographic tree hash with variable output length."""

    name: ClassVar[str] = "blake3"

    def digest(self, data: bytes, size: int | None = None) -> bytes:
        """Compute BLAKE3 digest with optional size override."""
        out_len = size if size is not None else 32
        return blake3.blake3(data).digest(length=out_len)

    def streaming(self, size: int = 32) -> StreamingHash:
        """Return incremental streaming hasher."""
        return Blake3StreamingHash(size=size)
