"""Forward Secrecy Key Ratchet for CryptaVault.

Implements an at-rest key ratchet based on HMAC/HKDF forward state transformation.
Each file is encrypted with a unique ephemeral key derived from the current ratchet state.
Once advanced, old states cannot derive future file keys, limiting the blast radius of any
single key compromise.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


@dataclass(frozen=True)
class RatchetState:
    """Snapshot of current ratchet position (chain key and counter)."""

    chain_key_hex: str
    counter: int


class RatchetKdf:
    """At-rest forward-secrecy key ratchet.

    Inspired by the Signal Double Ratchet forward-step mechanism.
    Each file operation triggers:
    1. Derivation of an independent 256-bit file encryption key.
    2. One-way hash transformation of the internal chain key.
    """

    FILE_KEY_INFO = b"cryptavault:ratchet:file-key:v1"
    CHAIN_STEP_INFO = b"cryptavault:ratchet:chain-step:v1"

    def __init__(self, initial_root_key: bytes | None = None) -> None:
        self._chain_key = initial_root_key or secrets.token_bytes(32)
        self._counter = 0

    @property
    def counter(self) -> int:
        """Current ratchet step counter."""
        return self._counter

    def next_key(self, extra_salt: bytes | None = None) -> bytes:
        """Advance ratchet by one step and return a unique 32-byte file key."""
        counter_bytes = self._counter.to_bytes(8, "big")
        salt = (extra_salt or b"") + counter_bytes

        # 1. Derive output file key
        file_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.FILE_KEY_INFO,
        ).derive(self._chain_key)

        # 2. Advance chain key via one-way transformation
        new_chain = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.CHAIN_STEP_INFO,
        ).derive(self._chain_key)

        self._chain_key = new_chain
        self._counter += 1

        return file_key

    def snapshot(self) -> RatchetState:
        """Export current ratchet position for state persistence."""
        return RatchetState(
            chain_key_hex=self._chain_key.hex(),
            counter=self._counter,
        )

    @classmethod
    def from_snapshot(cls, state: RatchetState | dict[str, Any]) -> RatchetKdf:
        """Restore ratchet from saved state."""
        if isinstance(state, dict):
            state = RatchetState(
                chain_key_hex=state["chain_key_hex"],
                counter=state["counter"],
            )
        instance = cls(initial_root_key=bytes.fromhex(state.chain_key_hex))
        instance._counter = state.counter
        return instance
