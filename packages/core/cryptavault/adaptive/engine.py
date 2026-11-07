"""Adaptive Cryptographic Engine for CryptaVault.

Resolves abstract security profiles into concrete, hardware-optimized
pipeline configurations and executes pluggable AEAD (including cascaded
multi-layer) primitives resolved through the crypto catalog.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

from cryptavault.adaptive.profiles import SecurityProfile, get_profile
from cryptavault.crypto.cascade import CascadeAEAD
from cryptavault.crypto.catalog import CryptoFamily, catalog
from cryptavault.crypto.symmetric import InvalidTagError
from cryptavault.plugins.registry import EncryptionAlgorithm, encryption_registry


def resolve_aead(algorithm_id: str) -> EncryptionAlgorithm:
    """Resolve a registered, catalog-approved AEAD instance by identifier."""
    spec = catalog.require_usable(algorithm_id, CryptoFamily.SYMMETRIC)
    return encryption_registry.get(spec.algorithm_id)()


@dataclass(frozen=True)
class PipelineConfig:
    """Concrete execution parameters resolved from a SecurityProfile and file metadata."""

    profile: SecurityProfile
    chunk_size_bytes: int
    parallel_workers: int
    symmetric_cipher: str
    hash_algorithm: str
    signature_algorithm: str
    kem_algorithm: str
    multi_layer: bool
    compression_enabled: bool


class MultiLayerEncryptor:
    """Cascaded authenticated encryption for the MAXIMUM security profile.

    Applies an inner AEAD followed by an outer AEAD using independent keys
    derived via HKDF-SHA256. Both authentication tags must strictly pass for
    successful decryption (fail-closed).
    """

    INNER_ID = "chacha20-poly1305"
    OUTER_ID = "aes-256-gcm"

    def __init__(self, inner: str = INNER_ID, outer: str = OUTER_ID) -> None:
        inner_spec = catalog.require_usable(inner, CryptoFamily.SYMMETRIC)
        outer_spec = catalog.require_usable(outer, CryptoFamily.SYMMETRIC)
        self.inner_id = inner_spec.algorithm_id
        self.outer_id = outer_spec.algorithm_id
        self._cascade = CascadeAEAD((self.inner_id, self.outer_id))

    def encrypt(
        self,
        root_key: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> tuple[bytes, bytes]:
        """Perform cascaded encryption, returning (outer_nonce, envelope)."""
        return self._cascade.encrypt_auto_nonce(root_key, plaintext, aad=aad)

    def decrypt(
        self,
        root_key: bytes,
        outer_nonce: bytes,
        payload: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Reverse cascaded encryption, verifying every layer tag."""
        return self._cascade.decrypt(root_key, outer_nonce, payload, aad=aad)


class AdaptiveEngine:
    """Core Adaptive Cryptographic Engine.

    Calculates optimal chunk sizes, parallel workers, and algorithm pipelines
    based on security profiles, hardware capabilities, and file sizing.
    """

    def __init__(self) -> None:
        self._multi_layer = MultiLayerEncryptor()

    def resolve(
        self,
        profile_or_name: SecurityProfile | str,
        file_size_bytes: int = 0,
        cpu_count: int | None = None,
    ) -> PipelineConfig:
        """Resolve a profile and file metadata to concrete PipelineConfig."""
        profile = (
            profile_or_name
            if isinstance(profile_or_name, SecurityProfile)
            else get_profile(profile_or_name)
        )

        chunk_size = profile.chunk_size_bytes
        if file_size_bytes >= 10 * 1024 * 1024 * 1024:
            chunk_size = max(chunk_size, 16 * 1024 * 1024)
        elif file_size_bytes >= 1024 * 1024 * 1024:
            chunk_size = max(chunk_size, 8 * 1024 * 1024)

        detected_cpus = cpu_count or os.cpu_count() or 4
        if profile.level.value == "PERFORMANCE":
            workers = max(2, min(detected_cpus, 8))
        elif profile.level.value == "MAXIMUM":
            workers = max(1, min(detected_cpus // 2, 4))
        else:
            workers = max(2, min(detected_cpus, 4))

        return PipelineConfig(
            profile=profile,
            chunk_size_bytes=chunk_size,
            parallel_workers=workers,
            symmetric_cipher=profile.symmetric_cipher,
            hash_algorithm=profile.hash_algorithm,
            signature_algorithm=profile.signature_algorithm,
            kem_algorithm=profile.kem_algorithm,
            multi_layer=profile.multi_layer_encryption,
            compression_enabled=True,
        )

    def encrypt_block(
        self,
        config: PipelineConfig,
        key: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> tuple[bytes, bytes]:
        """Encrypt a block using the configured cipher or cascade pipeline."""
        if config.multi_layer:
            return self._multi_layer.encrypt(key, plaintext, aad=aad)

        cipher = resolve_aead(config.symmetric_cipher)
        nonce = secrets.token_bytes(cipher.nonce_size_bytes)
        return nonce, cipher.encrypt(key, nonce, plaintext, aad)

    def decrypt_block(
        self,
        config: PipelineConfig,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Decrypt a block using the configured cipher or cascade pipeline."""
        if config.multi_layer:
            return self._multi_layer.decrypt(key, nonce, ciphertext, aad=aad)

        cipher = resolve_aead(config.symmetric_cipher)
        return cipher.decrypt(key, nonce, ciphertext, aad)


__all__ = [
    "AdaptiveEngine",
    "InvalidTagError",
    "MultiLayerEncryptor",
    "PipelineConfig",
    "resolve_aead",
]
