"""Encrypted Manifest Storage and Zero-Knowledge Serialization for CryptaVault."""

from __future__ import annotations

from cryptavault.crypto.symmetric import AES256GCM
from cryptavault.metadata.model import Manifest


class EncryptedManifestManager:
    """Manages encryption and decryption of vault manifests using AES-256-GCM."""

    AAD_CONTEXT = b"cryptavault:manifest:v1"

    def __init__(self) -> None:
        self.cipher = AES256GCM()

    def encrypt_manifest(self, manifest: Manifest, metadata_key: bytes) -> bytes:
        """Serialize and encrypt a manifest container into a zero-knowledge envelope.

        Wire format: [12-byte nonce][ciphertext + 16-byte tag]
        """
        raw_json = manifest.to_json().encode("utf-8")
        nonce, ciphertext = self.cipher.encrypt_auto_nonce(
            metadata_key, raw_json, aad=self.AAD_CONTEXT
        )
        return nonce + ciphertext

    def decrypt_manifest(self, payload: bytes, metadata_key: bytes) -> Manifest:
        """Decrypt and deserialize an encrypted manifest envelope."""
        nonce = payload[:12]
        ciphertext = payload[12:]
        plaintext_json = self.cipher.decrypt(metadata_key, nonce, ciphertext, aad=self.AAD_CONTEXT)
        return Manifest.from_json(plaintext_json.decode("utf-8"))
