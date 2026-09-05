"""Key Derivation Functions (KDF) for CryptaVault.

Provides:
- Argon2id (Memory-hard password-based key derivation for master keys)
- PBKDF2-HMAC-SHA256 (Standards-compliant fallback KDF, 600k iterations)
- HKDF-SHA256 (RFC 5869 extract-and-expand key derivation for cryptographic pipelines)

All implementations adhere to the KdfAlgorithm plugin interface.
"""

from __future__ import annotations

from typing import Any, ClassVar

import argon2.low_level
from argon2.low_level import Type as ArgonType
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF, HKDFExpand
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from cryptavault.plugins.registry import KdfAlgorithm, register_kdf


class KdfError(Exception):
    """Base exception for Key Derivation failures."""


class InvalidSaltError(KdfError):
    """Raised when salt is insufficient in length."""


# ====================================================================
# Argon2id Master Key Derivation
# ====================================================================


@register_kdf("argon2id")
class Argon2id(KdfAlgorithm):
    """Argon2id memory-hard key derivation function for master keys."""

    name: ClassVar[str] = "argon2id"
    DEFAULT_TIME_COST: ClassVar[int] = 3
    DEFAULT_MEMORY_COST: ClassVar[int] = 65536  # 64 MiB in KiB
    DEFAULT_PARALLELISM: ClassVar[int] = 4

    def derive(
        self,
        password: bytes,
        salt: bytes,
        length: int = 32,
        **params: Any,
    ) -> bytes:
        """Derive length bytes from password and salt using Argon2id.

        Params:
            time_cost: Number of iterations (default: 3)
            memory_cost: Memory usage in KiB (default: 65536 / 64MiB)
            parallelism: Number of threads (default: 4)
        """
        if len(salt) < 16:
            raise InvalidSaltError(f"Argon2id requires at least 16 bytes of salt, got {len(salt)}")

        t = int(params.get("time_cost", self.DEFAULT_TIME_COST))
        m = int(params.get("memory_cost", self.DEFAULT_MEMORY_COST))
        p = int(params.get("parallelism", self.DEFAULT_PARALLELISM))

        return argon2.low_level.hash_secret_raw(
            secret=password,
            salt=salt,
            time_cost=t,
            memory_cost=m,
            parallelism=p,
            hash_len=length,
            type=ArgonType.ID,
        )


# ====================================================================
# PBKDF2-HMAC-SHA256
# ====================================================================


@register_kdf("pbkdf2-sha256")
class Pbkdf2(KdfAlgorithm):
    """PBKDF2-HMAC-SHA256 key derivation with OWASP-recommended iteration count."""

    name: ClassVar[str] = "pbkdf2-sha256"
    DEFAULT_ITERATIONS: ClassVar[int] = 600000

    def derive(
        self,
        password: bytes,
        salt: bytes,
        length: int = 32,
        **params: Any,
    ) -> bytes:
        """Derive length bytes from password and salt using PBKDF2-HMAC-SHA256."""
        if len(salt) < 16:
            raise InvalidSaltError(f"PBKDF2 requires at least 16 bytes of salt, got {len(salt)}")

        iterations = int(params.get("iterations", self.DEFAULT_ITERATIONS))
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password)


# ====================================================================
# HKDF-SHA256 (RFC 5869)
# ====================================================================


@register_kdf("hkdf-sha256")
class HkdfSha256(KdfAlgorithm):
    """HMAC-based Extract-and-Expand Key Derivation Function (RFC 5869) using SHA-256."""

    name: ClassVar[str] = "hkdf-sha256"

    def derive(
        self,
        password: bytes,
        salt: bytes,
        length: int = 32,
        **params: Any,
    ) -> bytes:
        """Derive pseudorandom key bytes from input key material (IKM) and salt.

        Params:
            info: Context and application specific information (bytes, default b"")
        """
        info = params.get("info", b"")
        effective_salt = salt if salt else None
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=effective_salt,
            info=info,
        )
        return hkdf.derive(password)

    @staticmethod
    def extract(salt: bytes | None, ikm: bytes) -> bytes:
        """Extract a pseudorandom key (PRK) of fixed length (32 bytes for SHA-256)."""
        import hmac

        effective_salt = salt if (salt is not None and len(salt) > 0) else b"\x00" * 32
        return hmac.new(effective_salt, ikm, "sha256").digest()

    @staticmethod
    def expand(prk: bytes, info: bytes, length: int) -> bytes:
        """Expand PRK to desired output key length."""
        hkdf_expand = HKDFExpand(
            algorithm=hashes.SHA256(),
            length=length,
            info=info,
        )
        return hkdf_expand.derive(prk)
