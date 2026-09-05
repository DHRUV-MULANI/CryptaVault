"""Password-Protected Key Wrapping using Argon2id and AES-256-GCM."""

from __future__ import annotations

import base64
import os
from typing import Any

from cryptavault.crypto.kdf import Argon2id
from cryptavault.crypto.symmetric import AES256GCM


class PasswordKeyProtector:
    """Derives an Argon2id wrapping key from a user password and wraps/unwraps the file key."""

    @staticmethod
    def wrap_key(
        raw_key: bytes,
        password: str,
        memory_cost_kib: int = 65536,
        time_cost: int = 3,
        parallelism: int = 4,
    ) -> dict[str, Any]:
        """Wrap raw_key with an Argon2id-derived key from password using AES-256-GCM."""
        salt = os.urandom(16)
        wrapping_key = Argon2id().derive(
            password=password.encode("utf-8"),
            salt=salt,
            length=32,
            time_cost=time_cost,
            memory_cost=memory_cost_kib,
            parallelism=parallelism,
        )

        cipher = AES256GCM()
        nonce = os.urandom(12)
        ciphertext = cipher.encrypt(wrapping_key, nonce, raw_key, aad=b"cryptavault:password_wrap")

        return {
            "salt_b64": base64.b64encode(salt).decode("utf-8"),
            "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
            "wrapped_ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
            "kdf": {
                "algorithm": "argon2id",
                "memory_cost_kib": memory_cost_kib,
                "time_cost": time_cost,
                "parallelism": parallelism,
            },
        }

    @staticmethod
    def unwrap_key(wrapped_envelope: dict[str, Any], password: str) -> bytes:
        """Unwrap raw_key using password. Raises ValueError if password is incorrect."""
        salt = base64.b64decode(wrapped_envelope["salt_b64"])
        nonce = base64.b64decode(wrapped_envelope["nonce_b64"])
        ciphertext = base64.b64decode(wrapped_envelope["wrapped_ciphertext_b64"])
        kdf_params = wrapped_envelope.get("kdf", {})

        wrapping_key = Argon2id().derive(
            password=password.encode("utf-8"),
            salt=salt,
            length=32,
            time_cost=kdf_params.get("time_cost", 3),
            memory_cost=kdf_params.get("memory_cost_kib", 65536),
            parallelism=kdf_params.get("parallelism", 4),
        )

        cipher = AES256GCM()
        try:
            return cipher.decrypt(wrapping_key, nonce, ciphertext, aad=b"cryptavault:password_wrap")
        except Exception as e:
            raise ValueError("Incorrect share password or corrupted key envelope") from e
