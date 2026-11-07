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
    AESCCM,
    AESGCM,
    AESGCMSIV,
    AESOCB3,
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


class _HazmatAEAD(EncryptionAlgorithm):
    """Shared validation and fail-closed handling for ``cryptography`` AEADs."""

    key_size_bytes: ClassVar[int]
    nonce_size_bytes: ClassVar[int]
    _display_name: ClassVar[str]
    _aead_factory: ClassVar[type]

    def _validate_params(self, key: bytes, nonce: bytes) -> None:
        if len(key) != self.key_size_bytes:
            raise InvalidKeyError(
                f"{self._display_name} requires a {self.key_size_bytes}-byte key, "
                f"got {len(key)} bytes"
            )
        if len(nonce) != self.nonce_size_bytes:
            raise InvalidNonceError(
                f"{self._display_name} requires a {self.nonce_size_bytes}-byte nonce, "
                f"got {len(nonce)} bytes"
            )

    def encrypt(
        self,
        key: bytes,
        nonce: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Encrypt plaintext and associated data, appending the AEAD tag."""
        self._validate_params(key, nonce)
        return bytes(self._aead_factory(key).encrypt(nonce, plaintext, aad))

    def encrypt_auto_nonce(
        self,
        key: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> tuple[bytes, bytes]:
        """Generate a random nonce and encrypt."""
        nonce = secrets.token_bytes(self.nonce_size_bytes)
        return nonce, self.encrypt(key, nonce, plaintext, aad)

    def decrypt(
        self,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Decrypt and verify the AEAD tag, failing closed on any mismatch."""
        self._validate_params(key, nonce)
        try:
            return bytes(self._aead_factory(key).decrypt(nonce, ciphertext, aad))
        except InvalidTag as exc:
            raise InvalidTagError(
                f"{self._display_name} authentication tag verification failed. "
                "Ciphertext, tag, or associated authenticated data corrupted."
            ) from exc


@register_encryption("aes-128-gcm")
class AES128GCM(_HazmatAEAD):
    """AES-128 in Galois/Counter Mode."""

    name: ClassVar[str] = "aes-128-gcm"
    key_size_bytes: ClassVar[int] = 16
    nonce_size_bytes: ClassVar[int] = 12
    _display_name: ClassVar[str] = "AES-128-GCM"
    _aead_factory: ClassVar[type] = AESGCM


@register_encryption("aes-192-gcm")
class AES192GCM(_HazmatAEAD):
    """AES-192 in Galois/Counter Mode."""

    name: ClassVar[str] = "aes-192-gcm"
    key_size_bytes: ClassVar[int] = 24
    nonce_size_bytes: ClassVar[int] = 12
    _display_name: ClassVar[str] = "AES-192-GCM"
    _aead_factory: ClassVar[type] = AESGCM


@register_encryption("aes-128-ccm")
class AES128CCM(_HazmatAEAD):
    """AES-128 in Counter with CBC-MAC mode."""

    name: ClassVar[str] = "aes-128-ccm"
    key_size_bytes: ClassVar[int] = 16
    nonce_size_bytes: ClassVar[int] = 12
    _display_name: ClassVar[str] = "AES-128-CCM"
    _aead_factory: ClassVar[type] = AESCCM


@register_encryption("aes-256-ccm")
class AES256CCM(_HazmatAEAD):
    """AES-256 in Counter with CBC-MAC mode."""

    name: ClassVar[str] = "aes-256-ccm"
    key_size_bytes: ClassVar[int] = 32
    nonce_size_bytes: ClassVar[int] = 12
    _display_name: ClassVar[str] = "AES-256-CCM"
    _aead_factory: ClassVar[type] = AESCCM


@register_encryption("aes-256-gcm-siv")
class AES256GCMSIV(_HazmatAEAD):
    """AES-256-GCM-SIV nonce-misuse-resistant AEAD."""

    name: ClassVar[str] = "aes-256-gcm-siv"
    key_size_bytes: ClassVar[int] = 32
    nonce_size_bytes: ClassVar[int] = 12
    _display_name: ClassVar[str] = "AES-256-GCM-SIV"
    _aead_factory: ClassVar[type] = AESGCMSIV


@register_encryption("aes-256-ocb3")
class AES256OCB3(_HazmatAEAD):
    """AES-256 in Offset Codebook mode version 3."""

    name: ClassVar[str] = "aes-256-ocb3"
    key_size_bytes: ClassVar[int] = 32
    nonce_size_bytes: ClassVar[int] = 12
    _display_name: ClassVar[str] = "AES-256-OCB3"
    _aead_factory: ClassVar[type] = AESOCB3
