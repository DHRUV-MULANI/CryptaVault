"""Digital Signature Abstraction Layer for CryptaVault.

Provides a uniform, algorithm-agnostic SignatureContext for streaming sign and verify
operations across classical (Ed25519, ECDSA) and post-quantum / hybrid schemes (Dilithium, HybridSigPQ).
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from cryptavault.crypto.hash import Blake3
from cryptavault.plugins.registry import SignatureAlgorithm, signature_registry


class SignatureContextError(Exception):
    """Base exception for signature context operations."""


class MissingKeyError(SignatureContextError):
    """Raised when an operation requires a key that was not provided."""


class SignatureContext:
    """Unified context holding algorithm identity, signing, and verification keys."""

    def __init__(
        self,
        algorithm: str = "ed25519",
        public_key: bytes | None = None,
        private_key: bytes | None = None,
    ) -> None:
        self.algorithm_name = algorithm.strip().lower()
        self.public_key = public_key
        self.private_key = private_key
        self.hasher = Blake3()

        # Retrieve algorithm implementation from plugin registry
        self._plugin_cls = signature_registry.get(self.algorithm_name)
        self.signer: SignatureAlgorithm = self._plugin_cls()

    def generate_keys(self) -> tuple[bytes, bytes]:
        """Generate and store a new keypair in this context, returning (public, private)."""
        pub, priv = self.signer.keypair()
        self.public_key = pub
        self.private_key = priv
        return pub, priv

    def sign_bytes(self, data: bytes) -> bytes:
        """Sign raw data bytes in-memory."""
        if not self.private_key:
            raise MissingKeyError(
                f"Cannot sign: private key not configured in context for '{self.algorithm_name}'"
            )
        # For large data or streaming compatibility, digest via BLAKE3 before signing
        digest = self.hasher.digest(data)
        return self.signer.sign(self.private_key, digest)

    def verify_bytes(self, data: bytes, signature: bytes) -> bool:
        """Verify signature over raw data bytes in-memory."""
        if not self.public_key:
            raise MissingKeyError(
                f"Cannot verify: public key not configured in context for '{self.algorithm_name}'"
            )
        digest = self.hasher.digest(data)
        return self.signer.verify(self.public_key, digest, signature)

    def sign_stream(self, stream: BinaryIO, chunk_size: int = 1024 * 1024) -> bytes:
        """Stream data in chunks without loading entire content into memory, then sign."""
        if not self.private_key:
            raise MissingKeyError("Private key required for signing stream")

        streaming_hash = self.hasher.streaming()
        while chunk := stream.read(chunk_size):
            streaming_hash.update(chunk)
        digest = streaming_hash.digest()
        return self.signer.sign(self.private_key, digest)

    def verify_stream(
        self,
        stream: BinaryIO,
        signature: bytes,
        chunk_size: int = 1024 * 1024,
    ) -> bool:
        """Stream data in chunks and verify signature against calculated digest."""
        if not self.public_key:
            raise MissingKeyError("Public key required for verifying stream")

        streaming_hash = self.hasher.streaming()
        while chunk := stream.read(chunk_size):
            streaming_hash.update(chunk)
        digest = streaming_hash.digest()
        return self.signer.verify(self.public_key, digest, signature)

    def sign_file(self, file_path: str | Path) -> bytes:
        """Open a file and stream its content through the signature engine."""
        path = Path(file_path)
        with path.open("rb") as f:
            return self.sign_stream(f)

    def verify_file(self, file_path: str | Path, signature: bytes) -> bool:
        """Open a file and verify its signature via streaming."""
        path = Path(file_path)
        with path.open("rb") as f:
            return self.verify_stream(f, signature)
