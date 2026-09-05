"""Encrypted Keystore Storage for CryptaVault KMS.

Protects the KeyTree envelope with Argon2id memory-hard key derivation and AES-256-GCM
authenticated encryption. Ensures zero-knowledge: plaintext keys never hit persistent storage.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from cryptavault.crypto.kdf import Argon2id
from cryptavault.crypto.symmetric import AES256GCM, InvalidTagError
from cryptavault.keys.hierarchy import KeyTree


class KeystoreError(Exception):
    """Base exception for keystore operations."""


class KeystoreAuthError(KeystoreError):
    """Raised when the master password is incorrect or authentication fails."""


class KeystoreTamperedError(KeystoreError):
    """Raised when the keystore file has been corrupted or tampered with."""


class Keystore:
    """Encrypted container for KeyTree persistence."""

    ENVELOPE_VERSION = 1
    AAD_CONTEXT = b"cryptavault:keystore:v1"

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,  # 64 MiB
        parallelism: int = 4,
    ) -> None:
        self.time_cost = time_cost
        self.memory_cost = memory_cost
        self.parallelism = parallelism
        self.argon2 = Argon2id()
        self.cipher = AES256GCM()

    def encrypt_tree(
        self,
        tree: KeyTree,
        master_password: str | bytes,
    ) -> dict[str, Any]:
        """Encrypt a KeyTree into a secure serialized JSON envelope."""
        password_bytes = (
            master_password.encode("utf-8") if isinstance(master_password, str) else master_password
        )
        salt = secrets.token_bytes(16)

        # Derive master envelope encryption key via Argon2id
        derived_key = self.argon2.derive(
            password=password_bytes,
            salt=salt,
            length=32,
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
        )

        plaintext = tree.to_json().encode("utf-8")
        nonce, ciphertext = self.cipher.encrypt_auto_nonce(
            derived_key,
            plaintext,
            self.AAD_CONTEXT,
        )

        return {
            "version": self.ENVELOPE_VERSION,
            "salt": salt.hex(),
            "argon2_params": {
                "time_cost": self.time_cost,
                "memory_cost": self.memory_cost,
                "parallelism": self.parallelism,
            },
            "nonce": nonce.hex(),
            "encrypted_blob": ciphertext.hex(),
        }

    def decrypt_tree(
        self,
        envelope: dict[str, Any],
        master_password: str | bytes,
    ) -> KeyTree:
        """Decrypt an encrypted envelope dictionary back into a KeyTree."""
        if envelope.get("version") != self.ENVELOPE_VERSION:
            raise KeystoreError(f"Unsupported keystore envelope version: {envelope.get('version')}")

        password_bytes = (
            master_password.encode("utf-8") if isinstance(master_password, str) else master_password
        )

        salt = bytes.fromhex(envelope["salt"])
        params = envelope.get("argon2_params", {})
        time_cost = params.get("time_cost", self.time_cost)
        memory_cost = params.get("memory_cost", self.memory_cost)
        parallelism = params.get("parallelism", self.parallelism)

        derived_key = self.argon2.derive(
            password=password_bytes,
            salt=salt,
            length=32,
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

        nonce = bytes.fromhex(envelope["nonce"])
        ciphertext = bytes.fromhex(envelope["encrypted_blob"])

        try:
            plaintext = self.cipher.decrypt(
                derived_key,
                nonce,
                ciphertext,
                self.AAD_CONTEXT,
            )
        except InvalidTagError as exc:
            raise KeystoreAuthError(
                "Keystore decryption failed. Incorrect master password or tampered keystore."
            ) from exc

        try:
            tree_json = plaintext.decode("utf-8")
            return KeyTree.from_json(tree_json)
        except Exception as exc:
            raise KeystoreTamperedError("Decrypted keystore payload is corrupt JSON") from exc

    def save_file(
        self,
        tree: KeyTree,
        master_password: str | bytes,
        file_path: str | Path,
    ) -> None:
        """Save encrypted keystore to a file on disk."""
        envelope = self.encrypt_tree(tree, master_password)
        Path(file_path).write_text(json.dumps(envelope, indent=2), encoding="utf-8")

    def load_file(
        self,
        master_password: str | bytes,
        file_path: str | Path,
    ) -> KeyTree:
        """Load and decrypt keystore from a file on disk."""
        content = Path(file_path).read_text(encoding="utf-8")
        envelope = json.loads(content)
        return self.decrypt_tree(envelope, master_password)
