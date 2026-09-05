"""Symmetric AEAD Ciphers for CryptaVault.

Provides AES-256-GCM and ChaCha20-Poly1305 authenticated symmetric encryption
wrapping cryptography.hazmat.primitives.ciphers.aead with strict validation,
fail-closed authentication tag checking, and registration into the plugin system.
"""

from __future__ import annotations

import secrets
from typing import ClassVar

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import (
    AESGCM,
)
from cryptography.hazmat.primitives.ciphers.aead import (
    ChaCha20Poly1305 as HazmatChaCha20Poly1305,
)

from cryptavault.plugins.registry import EncryptionAlgorithm, register_encryption


class CryptoError(Exception):
    """Base exception for cryptographic failures."""


class InvalidTagError(CryptoError):
    """Raised when ciphertext authentication tag verification fails."""


class InvalidKeyError(CryptoError):
    """Raised when a cryptographic key does not match required dimensions."""


class InvalidNonceError(CryptoError):
    """Raised when a nonce/IV does not match required length."""


@register_encryption("aes-256-gcm")
class AES256GCM(EncryptionAlgorithm):
    """AES-256 in Galois/Counter Mode (GCM) AEAD cipher."""

    name: ClassVar[str] = "aes-256-gcm"
    key_size_bytes: ClassVar[int] = 32
    nonce_size_bytes: ClassVar[int] = 12

    def __init__(self) -> None:
        pass

    def encrypt(
        self,
        key: bytes,
        nonce: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Encrypt plaintext with associated data.

        Returns ciphertext with 16-byte authentication tag appended.
        """
        self._validate_params(key, nonce)
        cipher = AESGCM(key)
        return cipher.encrypt(nonce, plaintext, aad)

    def encrypt_auto_nonce(
        self,
        key: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> tuple[bytes, bytes]:
        """Auto-generate a secure random 96-bit nonce and encrypt plaintext.

        Returns (nonce, ciphertext).
        """
        nonce = secrets.token_bytes(self.nonce_size_bytes)
        ciphertext = self.encrypt(key, nonce, plaintext, aad)
        return nonce, ciphertext

    def decrypt(
        self,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Decrypt ciphertext and authenticate against associated data.

        Raises InvalidTagError if the authentication tag does not match.
        """
        self._validate_params(key, nonce)
        cipher = AESGCM(key)
        try:
            return cipher.decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise InvalidTagError(
                "AES-256-GCM authentication tag verification failed. "
                "Ciphertext, tag, or associated authenticated data corrupted."
            ) from exc

    def _validate_params(self, key: bytes, nonce: bytes) -> None:
        if len(key) != self.key_size_bytes:
            raise InvalidKeyError(
                f"AES-256-GCM requires a {self.key_size_bytes}-byte key, got {len(key)} bytes"
            )
        if len(nonce) != self.nonce_size_bytes:
            raise InvalidNonceError(
                f"AES-256-GCM requires a {self.nonce_size_bytes}-byte nonce, got {len(nonce)} bytes"
            )


@register_encryption("chacha20-poly1305")
class ChaCha20Poly1305(EncryptionAlgorithm):
    """ChaCha20 stream cipher with Poly1305 MAC AEAD cipher."""

    name: ClassVar[str] = "chacha20-poly1305"
    key_size_bytes: ClassVar[int] = 32
    nonce_size_bytes: ClassVar[int] = 12

    def __init__(self) -> None:
        pass

    def encrypt(
        self,
        key: bytes,
        nonce: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Encrypt plaintext with associated data.

        Returns ciphertext with 16-byte Poly1305 authentication tag appended.
        """
        self._validate_params(key, nonce)
        cipher = HazmatChaCha20Poly1305(key)
        return cipher.encrypt(nonce, plaintext, aad)

    def encrypt_auto_nonce(
        self,
        key: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> tuple[bytes, bytes]:
        """Auto-generate a secure random 96-bit nonce and encrypt plaintext.

        Returns (nonce, ciphertext).
        """
        nonce = secrets.token_bytes(self.nonce_size_bytes)
        ciphertext = self.encrypt(key, nonce, plaintext, aad)
        return nonce, ciphertext

    def decrypt(
        self,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Decrypt ciphertext and authenticate against associated data.

        Raises InvalidTagError if Poly1305 tag verification fails.
        """
        self._validate_params(key, nonce)
        cipher = HazmatChaCha20Poly1305(key)
        try:
            return cipher.decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise InvalidTagError(
                "ChaCha20-Poly1305 authentication tag verification failed. "
                "Ciphertext, tag, or associated authenticated data corrupted."
            ) from exc

    def _validate_params(self, key: bytes, nonce: bytes) -> None:
        if len(key) != self.key_size_bytes:
            raise InvalidKeyError(
                f"ChaCha20-Poly1305 requires a {self.key_size_bytes}-byte key, got {len(key)} bytes"
            )
        if len(nonce) != self.nonce_size_bytes:
            raise InvalidNonceError(
                f"ChaCha20-Poly1305 requires a {self.nonce_size_bytes}-byte nonce, got {len(nonce)} bytes"
            )
