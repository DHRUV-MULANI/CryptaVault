"""Post-Quantum Cryptography Primitives for CryptaVault.

Integrates liboqs for NIST standardized Post-Quantum algorithms:
- ML-KEM / Kyber (FIPS 203): Lattice-based Key Encapsulation Mechanism
- ML-DSA / Dilithium (FIPS 204): Lattice-based Digital Signatures

Supports NIST security levels 1, 3, and 5:
- Level 1: Kyber512 / ML-KEM-512, Dilithium2 / ML-DSA-44
- Level 3: Kyber768 / ML-KEM-768, Dilithium3 / ML-DSA-65 (CryptaVault Default PQ)
- Level 5: Kyber1024 / ML-KEM-1024, Dilithium5 / ML-DSA-87 (CryptaVault Maximum PQ)
"""

from __future__ import annotations

from typing import ClassVar

try:
    import oqs

    OQS_AVAILABLE = True
except ImportError:
    oqs = None  # type: ignore[assignment]
    OQS_AVAILABLE = False

from cryptavault.plugins.registry import (
    KemAlgorithm,
    SignatureAlgorithm,
    register_kem,
    register_signature,
)


class PostQuantumError(Exception):
    """Base exception for post-quantum cryptographic errors."""


class OqsNotAvailableError(PostQuantumError):
    """Raised when liboqs / oqs-python is not installed or available on this platform."""


# ====================================================================
# Helper to resolve OQS mechanism names (Kyber vs ML-KEM, Dilithium vs ML-DSA)
# ====================================================================


def _resolve_kem_mechanism(preferred_names: list[str]) -> str:
    if not OQS_AVAILABLE:
        raise OqsNotAvailableError("liboqs is required for post-quantum KEM operations")
    enabled = oqs.get_enabled_kem_mechanisms()
    for name in preferred_names:
        if name in enabled:
            return name
    raise PostQuantumError(
        f"None of the requested KEM mechanisms {preferred_names} are enabled in liboqs."
    )


def _resolve_sig_mechanism(preferred_names: list[str]) -> str:
    if not OQS_AVAILABLE:
        raise OqsNotAvailableError("liboqs is required for post-quantum signature operations")
    enabled = oqs.get_enabled_sig_mechanisms()
    for name in preferred_names:
        if name in enabled:
            return name
    raise PostQuantumError(
        f"None of the requested Signature mechanisms {preferred_names} are enabled in liboqs."
    )


# ====================================================================
# Kyber / ML-KEM Implementation
# ====================================================================


class KyberKem(KemAlgorithm):
    """NIST ML-KEM / CRYSTALS-Kyber Key Encapsulation Mechanism."""

    name: ClassVar[str] = "kyber"

    def __init__(self, level: int = 3) -> None:
        self.level = level
        if level == 1:
            self.mechanism_name = _resolve_kem_mechanism(["Kyber512", "ML-KEM-512"])
        elif level == 3:
            self.mechanism_name = _resolve_kem_mechanism(["Kyber768", "ML-KEM-768"])
        elif level == 5:
            self.mechanism_name = _resolve_kem_mechanism(["Kyber1024", "ML-KEM-1024"])
        else:
            raise ValueError(f"Invalid NIST security level: {level}. Choose 1, 3, or 5.")

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate (public_key, secret_key) bytes."""
        with oqs.KeyEncapsulation(self.mechanism_name) as client:
            public_key = client.generate_keypair()
            secret_key = client.export_secret_key()
            return bytes(public_key), bytes(secret_key)

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        """Encapsulate shared secret against peer public key.

        Returns (shared_secret, ciphertext).
        """
        with oqs.KeyEncapsulation(self.mechanism_name) as client:
            ciphertext, shared_secret = client.encap_secret(public_key)
            return bytes(shared_secret), bytes(ciphertext)

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate ciphertext using secret key to recover shared secret."""
        with oqs.KeyEncapsulation(self.mechanism_name, secret_key=secret_key) as client:
            return bytes(client.decap_secret(ciphertext))


@register_kem("kyber768")
class Kyber768(KyberKem):
    """Kyber768 / ML-KEM-768 (NIST Level 3) default PQ KEM."""

    name: ClassVar[str] = "kyber768"

    def __init__(self) -> None:
        super().__init__(level=3)


@register_kem("kyber1024")
class Kyber1024(KyberKem):
    """Kyber1024 / ML-KEM-1024 (NIST Level 5) maximum PQ KEM."""

    name: ClassVar[str] = "kyber1024"

    def __init__(self) -> None:
        super().__init__(level=5)


# ====================================================================
# Dilithium / ML-DSA Implementation
# ====================================================================


class DilithiumSig(SignatureAlgorithm):
    """NIST ML-DSA / CRYSTALS-Dilithium Digital Signature Scheme."""

    name: ClassVar[str] = "dilithium"

    def __init__(self, level: int = 3) -> None:
        self.level = level
        if level == 1:
            self.mechanism_name = _resolve_sig_mechanism(["ML-DSA-44", "Dilithium2"])
        elif level == 3:
            self.mechanism_name = _resolve_sig_mechanism(["ML-DSA-65", "Dilithium3"])
        elif level == 5:
            self.mechanism_name = _resolve_sig_mechanism(["ML-DSA-87", "Dilithium5"])
        else:
            raise ValueError(f"Invalid NIST security level: {level}. Choose 1, 3, or 5.")

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate (public_key, secret_key) bytes."""
        with oqs.Signature(self.mechanism_name) as signer:
            public_key = signer.generate_keypair()
            secret_key = signer.export_secret_key()
            return bytes(public_key), bytes(secret_key)

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign message using secret key."""
        with oqs.Signature(self.mechanism_name, secret_key=private_key) as signer:
            return bytes(signer.sign(message))

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify signature using public key. Returns False on mismatch or error."""
        with oqs.Signature(self.mechanism_name) as verifier:
            try:
                return bool(verifier.verify(message, signature, public_key))
            except Exception:  # noqa: BLE001
                return False


@register_signature("dilithium3")
class Dilithium3(DilithiumSig):
    """Dilithium3 / ML-DSA-65 (NIST Level 3) default PQ signature."""

    name: ClassVar[str] = "dilithium3"

    def __init__(self) -> None:
        super().__init__(level=3)


@register_signature("dilithium5")
class Dilithium5(DilithiumSig):
    """Dilithium5 / ML-DSA-87 (NIST Level 5) maximum PQ signature."""

    name: ClassVar[str] = "dilithium5"

    def __init__(self) -> None:
        super().__init__(level=5)
