"""Adaptive Cryptographic Engine for CryptaVault.

Resolves abstract security profiles into concrete, hardware-optimized
pipeline configurations and implements multi-layer encryption for high-assurance workloads.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from cryptavault.adaptive.profiles import SecurityProfile, get_profile
from cryptavault.crypto.symmetric import (
    AES256GCM,
    ChaCha20Poly1305,
    InvalidTagError,
)


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
    """Dual-layer authenticated encryption for MAXIMUM security profile.

    Applies inner ChaCha20-Poly1305 followed by outer AES-256-GCM using two
    cryptographically independent keys derived via HKDF-SHA256 from the master key.
    Both authentication tags must strictly pass for successful decryption (fail-closed).
    """

    INNER_INFO = b"cryptavault:multi-layer:inner:chacha20"
    OUTER_INFO = b"cryptavault:multi-layer:outer:aes256gcm"

    def __init__(self) -> None:
        self.inner_cipher = ChaCha20Poly1305()
        self.outer_cipher = AES256GCM()

    def _derive_keys(self, root_key: bytes) -> tuple[bytes, bytes]:
        """Derive 2 independent 32-byte keys from root key."""
        inner_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=self.INNER_INFO,
        ).derive(root_key)

        outer_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=self.OUTER_INFO,
        ).derive(root_key)

        return inner_key, outer_key

    def encrypt(
        self,
        root_key: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> tuple[bytes, bytes]:
        """Perform dual-layer encryption: inner ChaCha20, outer AES-256-GCM.

        Returns (outer_nonce, multi_layer_envelope).
        Envelope format: [12-byte inner_nonce][outer_ciphertext (encrypting inner_ciphertext)]
        """
        inner_key, outer_key = self._derive_keys(root_key)

        # 1. Inner encryption (ChaCha20-Poly1305)
        inner_nonce, inner_ct = self.inner_cipher.encrypt_auto_nonce(inner_key, plaintext, aad=aad)

        # 2. Outer encryption (AES-256-GCM)
        outer_nonce, outer_ct = self.outer_cipher.encrypt_auto_nonce(outer_key, inner_ct, aad=aad)

        # Combine: inner_nonce (12 bytes) + outer_ciphertext
        payload = inner_nonce + outer_ct
        return outer_nonce, payload

    def decrypt(
        self,
        root_key: bytes,
        outer_nonce: bytes,
        payload: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Reverse dual-layer encryption: outer AES-256-GCM first, then inner ChaCha20-Poly1305."""
        if len(payload) < 28:  # 12-byte inner nonce + minimum 16-byte tag
            raise InvalidTagError("Multi-layer ciphertext payload is truncated")

        inner_nonce = payload[:12]
        outer_ct = payload[12:]

        inner_key, outer_key = self._derive_keys(root_key)

        # 1. Outer decryption
        inner_ct = self.outer_cipher.decrypt(outer_key, outer_nonce, outer_ct, aad=aad)

        # 2. Inner decryption
        return self.inner_cipher.decrypt(inner_key, inner_nonce, inner_ct, aad=aad)


class AdaptiveEngine:
    """Core Adaptive Cryptographic Engine.

    Calculates optimal chunk sizes, parallel workers, and algorithm pipelines
    based on security profiles, hardware capabilities, and file sizing.
    """

    def __init__(self) -> None:
        self._multi_layer = MultiLayerEncryptor()
        self._aes = AES256GCM()
        self._chacha = ChaCha20Poly1305()

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

        # Dynamic chunk scaling based on file size:
        # < 100MB: default profile chunk size (e.g. 4MB)
        # 100MB - 1GB: at least 4MB
        # 1GB - 10GB: at least 8MB
        # > 10GB: 16MB
        chunk_size = profile.chunk_size_bytes
        if file_size_bytes >= 10 * 1024 * 1024 * 1024:
            chunk_size = max(chunk_size, 16 * 1024 * 1024)
        elif file_size_bytes >= 1024 * 1024 * 1024:
            chunk_size = max(chunk_size, 8 * 1024 * 1024)

        # Parallel worker allocation based on CPU
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
        """Encrypt a block using configured cipher or multi-layer pipeline."""
        if config.multi_layer:
            return self._multi_layer.encrypt(key, plaintext, aad=aad)

        if config.symmetric_cipher.lower() == "aes-256-gcm":
            return self._aes.encrypt_auto_nonce(key, plaintext, aad=aad)
        return self._chacha.encrypt_auto_nonce(key, plaintext, aad=aad)

    def decrypt_block(
        self,
        config: PipelineConfig,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Decrypt a block using configured cipher or multi-layer pipeline."""
        if config.multi_layer:
            return self._multi_layer.decrypt(key, nonce, ciphertext, aad=aad)

        if config.symmetric_cipher.lower() == "aes-256-gcm":
            return self._aes.decrypt(key, nonce, ciphertext, aad=aad)
        return self._chacha.decrypt(key, nonce, ciphertext, aad=aad)
