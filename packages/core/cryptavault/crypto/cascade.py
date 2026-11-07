"""Composable Cascade AEAD for CryptaVault.

A cascade encrypts plaintext through two or more independent AEAD layers. Every
layer derives its own key from the root key, so compromise of one layer's key or
one primitive does not expose the plaintext. Every authentication tag must verify
(fail-closed). This is the primitive behind the MAXIMUM security profile.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from typing import ClassVar

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from cryptavault.crypto.symmetric import InvalidTagError
from cryptavault.plugins.registry import (
    EncryptionAlgorithm,
    encryption_registry,
    register_encryption,
)

CASCADE_CONTEXT: bytes = b"cryptavault:cascade:v1"


class CascadeAEAD(EncryptionAlgorithm):
    """Layered AEAD built from an ordered list of registered cipher identifiers."""

    name: ClassVar[str] = "cascade"
    key_size_bytes: ClassVar[int] = 32
    nonce_size_bytes: ClassVar[int] = 12
    cipher_ids: ClassVar[tuple[str, ...]] = ("chacha20-poly1305", "aes-256-gcm")

    def __init__(self, cipher_ids: Sequence[str] | None = None) -> None:
        ids = tuple(cipher_ids) if cipher_ids is not None else self.cipher_ids
        if len(ids) < 2:
            raise ValueError("A cascade requires at least two cipher layers")
        normalized = tuple(encryption_registry.get(cipher_id).name for cipher_id in ids)
        self._cipher_ids = normalized
        self._ciphers = tuple(encryption_registry.get(cipher_id)() for cipher_id in normalized)

    def _derive_key(self, root_key: bytes, layer_index: int) -> bytes:
        cipher = self._ciphers[layer_index]
        info = CASCADE_CONTEXT + f":{layer_index}:{self._cipher_ids[layer_index]}".encode()
        return HKDF(
            algorithm=hashes.SHA256(),
            length=cipher.key_size_bytes,
            salt=None,
            info=info,
        ).derive(root_key)

    def encrypt_auto_nonce(
        self,
        key: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> tuple[bytes, bytes]:
        """Generate the outer nonce and run the cascade."""
        nonce = secrets.token_bytes(self._ciphers[-1].nonce_size_bytes)
        return nonce, self.encrypt(key, nonce, plaintext, aad=aad)

    def encrypt(
        self,
        key: bytes,
        nonce: bytes,
        plaintext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Encrypt through every layer, innermost first.

        Inner nonces are embedded in the payload; the caller-supplied nonce is
        used by the outermost layer.
        """
        if len(key) != self.key_size_bytes:
            raise ValueError(
                f"Cascade requires a {self.key_size_bytes}-byte root key, got {len(key)}"
            )
        if len(nonce) != self._ciphers[-1].nonce_size_bytes:
            raise ValueError(
                f"Cascade requires a {self._ciphers[-1].nonce_size_bytes}-byte outer nonce, "
                f"got {len(nonce)}"
            )

        embedded_nonces: list[bytes] = []
        data = plaintext
        for index in range(len(self._ciphers) - 1):
            cipher = self._ciphers[index]
            inner_nonce = secrets.token_bytes(cipher.nonce_size_bytes)
            data = cipher.encrypt(self._derive_key(key, index), inner_nonce, data, aad)
            embedded_nonces.append(inner_nonce)

        outer_index = len(self._ciphers) - 1
        outer = self._ciphers[outer_index]
        data = outer.encrypt(self._derive_key(key, outer_index), nonce, data, aad)
        return b"".join(embedded_nonces) + data

    def decrypt(
        self,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        aad: bytes = b"",
    ) -> bytes:
        """Reverse the cascade, outermost first, verifying every tag."""
        if len(key) != self.key_size_bytes:
            raise ValueError(
                f"Cascade requires a {self.key_size_bytes}-byte root key, got {len(key)}"
            )
        outer_index = len(self._ciphers) - 1
        outer = self._ciphers[outer_index]
        if len(nonce) != outer.nonce_size_bytes:
            raise ValueError(
                f"Cascade requires a {outer.nonce_size_bytes}-byte outer nonce, got {len(nonce)}"
            )

        embedded_total = sum(cipher.nonce_size_bytes for cipher in self._ciphers[:-1])
        if len(ciphertext) <= embedded_total:
            raise InvalidTagError("Cascade ciphertext is truncated before any layer tag")

        embedded_nonces: list[bytes] = []
        offset = 0
        for cipher in self._ciphers[:-1]:
            embedded_nonces.append(ciphertext[offset : offset + cipher.nonce_size_bytes])
            offset += cipher.nonce_size_bytes
        data = ciphertext[offset:]

        data = outer.decrypt(self._derive_key(key, outer_index), nonce, data, aad)
        for index in range(len(self._ciphers) - 2, -1, -1):
            cipher = self._ciphers[index]
            data = cipher.decrypt(self._derive_key(key, index), embedded_nonces[index], data, aad)
        return data


@register_encryption("cascade-chacha20-aes256gcm")
class CascadeChaCha20AES256GCM(CascadeAEAD):
    """Inner ChaCha20-Poly1305 under outer AES-256-GCM."""

    name: ClassVar[str] = "cascade-chacha20-aes256gcm"
    cipher_ids: ClassVar[tuple[str, ...]] = ("chacha20-poly1305", "aes-256-gcm")


__all__ = ["CASCADE_CONTEXT", "CascadeAEAD", "CascadeChaCha20AES256GCM"]
