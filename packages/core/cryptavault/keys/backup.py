"""Key Backup and Recovery via BIP-39 24-Word Mnemonics for CryptaVault.

Provides cold-storage disaster recovery:
- Exports a 256-bit high-entropy 24-word mnemonic phrase.
- Wraps master keys using recovery keys derived from the mnemonic seed.
- Validates BIP-39 checksums and unwraps master keys offline without server involvement.
"""

from __future__ import annotations

import secrets
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from mnemonic import Mnemonic

from cryptavault.crypto.symmetric import AES256GCM, InvalidTagError


class RecoveryError(Exception):
    """Base exception for mnemonic backup and recovery."""


class InvalidMnemonicError(RecoveryError):
    """Raised when a mnemonic word list fails BIP-39 wordlist or checksum validation."""


class RecoveryBundleTamperedError(RecoveryError):
    """Raised when a recovery bundle payload does not match expected authentication tags."""


class KeyRecoveryManager:
    """Manages generation, export, and verification of BIP-39 recovery bundles."""

    RECOVERY_INFO = b"cryptavault:recovery-bundle:v1"

    def __init__(self, language: str = "english") -> None:
        self.mnemo = Mnemonic(language)
        self.cipher = AES256GCM()

    def export_recovery_bundle(
        self,
        master_key: bytes,
        passphrase: str = "",
    ) -> tuple[str, dict[str, Any]]:
        """Generate a 24-word mnemonic and wrap the master key inside a recovery bundle.

        Returns (mnemonic_phrase, recovery_bundle_dict).
        """
        if len(master_key) != 32:
            raise ValueError("Master key must be exactly 32 bytes")

        # 256-bit entropy produces standard 24-word mnemonic
        mnemonic_phrase = self.mnemo.generate(strength=256)
        seed = self.mnemo.to_seed(mnemonic_phrase, passphrase=passphrase)

        # Derive 32-byte wrapping key from mnemonic seed
        salt = secrets.token_bytes(16)
        wrap_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.RECOVERY_INFO,
        ).derive(seed)

        nonce, ciphertext = self.cipher.encrypt_auto_nonce(
            wrap_key,
            master_key,
            self.RECOVERY_INFO,
        )

        bundle = {
            "version": 1,
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "wrapped_master_key": ciphertext.hex(),
            "word_count": 24,
        }
        return mnemonic_phrase, bundle

    def import_recovery_bundle(
        self,
        mnemonic_phrase: str,
        bundle: dict[str, Any],
        passphrase: str = "",
    ) -> bytes:
        """Unwrap master key from recovery bundle using 24-word mnemonic phrase."""
        cleaned_phrase = " ".join(mnemonic_phrase.strip().split())

        # Validate BIP-39 dictionary and checksum
        if not self.mnemo.check(cleaned_phrase):
            raise InvalidMnemonicError(
                "Invalid mnemonic phrase: wordlist mismatch or failed checksum"
            )

        words = cleaned_phrase.split()
        if len(words) != 24:
            raise InvalidMnemonicError(f"Expected 24-word mnemonic phrase, got {len(words)} words")

        seed = self.mnemo.to_seed(cleaned_phrase, passphrase=passphrase)
        salt = bytes.fromhex(bundle["salt"])
        nonce = bytes.fromhex(bundle["nonce"])
        ciphertext = bytes.fromhex(bundle["wrapped_master_key"])

        wrap_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.RECOVERY_INFO,
        ).derive(seed)

        try:
            return self.cipher.decrypt(wrap_key, nonce, ciphertext, self.RECOVERY_INFO)
        except InvalidTagError as exc:
            raise RecoveryBundleTamperedError(
                "Recovery bundle decryption failed: incorrect mnemonic/passphrase or corrupted bundle"
            ) from exc

    def verify_recovery_bundle(
        self,
        mnemonic_phrase: str,
        bundle: dict[str, Any],
        passphrase: str = "",
    ) -> bool:
        """Test whether a mnemonic phrase successfully unwraps the recovery bundle."""
        try:
            recovered = self.import_recovery_bundle(mnemonic_phrase, bundle, passphrase=passphrase)
            return len(recovered) == 32
        except Exception:  # noqa: BLE001
            return False
