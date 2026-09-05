"""Invitation-based file sharing with Public-Key Hybrid Post-Quantum KEM."""

from __future__ import annotations

import base64
import os

from cryptavault.crypto.hybrid import HybridKemPQ
from cryptavault.crypto.symmetric import AES256GCM
from cryptavault.sharing.package import RecipientKeyEnvelope


class InvitationShareManager:
    """Handles hybrid post-quantum recipient encapsulation for secure sharing."""

    def __init__(self) -> None:
        self.kem = HybridKemPQ()
        self.cipher = AES256GCM()

    def wrap_key_for_recipient(
        self,
        raw_key: bytes,
        recipient_id: str,
        recipient_hybrid_pubkey: bytes,
    ) -> RecipientKeyEnvelope:
        """Encapsulate a shared secret to recipient's hybrid public key and wrap the file key."""
        # 1. KEM Encapsulation -> 32-byte shared secret + ephemeral ciphertext
        shared_secret, kem_ciphertext = self.kem.encapsulate(recipient_hybrid_pubkey)

        # 2. AES-256-GCM wrap raw_key using the shared secret
        aad = f"cryptavault:recipient:{recipient_id}".encode()
        nonce = os.urandom(12)
        wrapped_key = self.cipher.encrypt(shared_secret, nonce, raw_key, aad=aad)

        # Combined envelope payload: [12-byte nonce][wrapped_key + 16-byte tag]
        full_wrapped_bytes = nonce + wrapped_key

        return RecipientKeyEnvelope(
            recipient_id=recipient_id,
            kem_scheme="x25519-kyber768",
            wrapped_key_b64=base64.b64encode(full_wrapped_bytes).decode("utf-8"),
            ephemeral_public_key_b64=base64.b64encode(kem_ciphertext).decode("utf-8"),
        )

    def unwrap_key_as_recipient(
        self,
        envelope: RecipientKeyEnvelope,
        recipient_hybrid_privkey: bytes,
    ) -> bytes:
        """Decapsulate the shared secret and unwrap the file encryption key."""
        if envelope.kem_scheme != "x25519-kyber768":
            raise ValueError(f"Unsupported KEM scheme: {envelope.kem_scheme}")

        if not envelope.ephemeral_public_key_b64:
            raise ValueError("Missing ephemeral KEM ciphertext in recipient envelope")

        kem_ciphertext = base64.b64decode(envelope.ephemeral_public_key_b64)
        full_wrapped = base64.b64decode(envelope.wrapped_key_b64)

        # 1. Decapsulate shared secret
        shared_secret = self.kem.decapsulate(recipient_hybrid_privkey, kem_ciphertext)

        # 2. Extract nonce and ciphertext
        nonce = full_wrapped[:12]
        wrapped_key = full_wrapped[12:]
        aad = f"cryptavault:recipient:{envelope.recipient_id}".encode()

        return self.cipher.decrypt(shared_secret, nonce, wrapped_key, aad=aad)
