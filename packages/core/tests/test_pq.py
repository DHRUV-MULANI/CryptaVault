"""Unit and integration tests for Post-Quantum Cryptography and Hybrid Schemes.

Tests:
- Kyber768 and Kyber1024 KEM (NIST FIPS 203)
- Dilithium3 and Dilithium5 Digital Signatures (NIST FIPS 204)
- HybridKemPQ (X25519 + Kyber768 dual encapsulation)
- HybridSigPQ (Ed25519 + Dilithium3 dual signatures)
- Fail-closed tamper resistance and plugin registry integration
"""

import struct

from cryptavault.crypto.hybrid import HybridKemPQ, HybridSigPQ
from cryptavault.crypto.pq import Dilithium3, Dilithium5, Kyber768, Kyber1024
from cryptavault.plugins.registry import kem_registry, signature_registry

# ====================================================================
# 1. Post-Quantum KEM Tests (Kyber768 & Kyber1024)
# ====================================================================


def test_kyber768_roundtrip() -> None:
    """Ensure Kyber768 encapsulates and decapsulates identical shared secret."""
    kem = Kyber768()
    pub, priv = kem.keypair()
    assert len(pub) > 0
    assert len(priv) > 0

    secret_client, ciphertext = kem.encapsulate(pub)
    assert len(secret_client) == 32
    assert len(ciphertext) > 0

    secret_server = kem.decapsulate(priv, ciphertext)
    assert secret_server == secret_client


def test_kyber1024_roundtrip() -> None:
    """Ensure Kyber1024 (NIST Level 5) roundtrips successfully."""
    kem = Kyber1024()
    pub, priv = kem.keypair()

    secret_client, ciphertext = kem.encapsulate(pub)
    assert len(secret_client) == 32

    secret_server = kem.decapsulate(priv, ciphertext)
    assert secret_server == secret_client


def test_kyber768_tampered_ciphertext_produces_wrong_secret() -> None:
    """Tampering with Kyber ciphertext must result in mismatched shared secret."""
    kem = Kyber768()
    pub, priv = kem.keypair()

    secret_client, ciphertext = kem.encapsulate(pub)

    tampered_ct = bytearray(ciphertext)
    tampered_ct[0] ^= 0x01

    secret_server = kem.decapsulate(priv, bytes(tampered_ct))
    assert secret_server != secret_client


# ====================================================================
# 2. Post-Quantum Signatures (Dilithium3 & Dilithium5)
# ====================================================================


def test_dilithium3_sign_and_verify() -> None:
    """Ensure Dilithium3 produces valid signatures and rejects tampering."""
    sig = Dilithium3()
    pub, priv = sig.keypair()

    message = b"Root-Level Zero-Knowledge Master Manifest Signature"
    signature = sig.sign(priv, message)
    assert len(signature) > 0

    # Valid verify
    assert sig.verify(pub, message, signature) is True

    # Tampered message
    assert sig.verify(pub, b"Altered Manifest Data", signature) is False

    # Tampered signature
    tampered_sig = bytearray(signature)
    tampered_sig[0] ^= 0x01
    assert sig.verify(pub, message, bytes(tampered_sig)) is False


def test_dilithium5_sign_and_verify() -> None:
    """Ensure Dilithium5 (NIST Level 5) operates correctly."""
    sig = Dilithium5()
    pub, priv = sig.keypair()

    message = b"Critical HSM Root Seed"
    signature = sig.sign(priv, message)
    assert sig.verify(pub, message, signature) is True
    assert sig.verify(pub, message + b"!", signature) is False


# ====================================================================
# 3. Hybrid KEM (X25519 + Kyber768)
# ====================================================================


def test_hybrid_kem_pq_roundtrip() -> None:
    """Ensure Alice and Bob arrive at identical composite shared secret."""
    hybrid = HybridKemPQ()
    pub, priv = hybrid.keypair()

    secret_alice, ciphertext = hybrid.encapsulate(pub)
    assert len(secret_alice) == 32

    secret_bob = hybrid.decapsulate(priv, ciphertext)
    assert secret_bob == secret_alice


def test_hybrid_kem_pq_tampered_ecdh_component_fails() -> None:
    """Tampering with the ECDH portion must result in a completely different secret."""
    hybrid = HybridKemPQ()
    pub, priv = hybrid.keypair()

    secret_alice, ciphertext = hybrid.encapsulate(pub)

    # Ciphertext starts with [2-byte c_ct_len] followed by c_ct
    tampered_ct = bytearray(ciphertext)
    tampered_ct[2] ^= 0x01  # Flip a byte in the ECDH ciphertext

    secret_bob = hybrid.decapsulate(priv, bytes(tampered_ct))
    assert secret_bob != secret_alice


def test_hybrid_kem_pq_tampered_kyber_component_fails() -> None:
    """Tampering with the Kyber portion must result in a completely different secret."""
    hybrid = HybridKemPQ()
    pub, priv = hybrid.keypair()

    secret_alice, ciphertext = hybrid.encapsulate(pub)

    c_ct_len = struct.unpack(">H", ciphertext[:2])[0]
    tampered_ct = bytearray(ciphertext)
    tampered_ct[2 + c_ct_len] ^= 0x01  # Flip a byte in the Kyber ciphertext

    secret_bob = hybrid.decapsulate(priv, bytes(tampered_ct))
    assert secret_bob != secret_alice


# ====================================================================
# 4. Hybrid Signatures (Ed25519 + Dilithium3)
# ====================================================================


def test_hybrid_sig_pq_roundtrip() -> None:
    """Ensure hybrid signatures verify when both signatures are valid."""
    hybrid = HybridSigPQ()
    pub, priv = hybrid.keypair()

    msg = b"Transaction ID #99214: Client Key Rotation Event"
    sig = hybrid.sign(priv, msg)

    assert hybrid.verify(pub, msg, sig) is True
    assert hybrid.verify(pub, b"Tampered Message", sig) is False


def test_hybrid_sig_pq_tampered_classical_fails() -> None:
    """If the classical Ed25519 signature is corrupted, verification must fail."""
    hybrid = HybridSigPQ()
    pub, priv = hybrid.keypair()

    msg = b"Secure Audit Ledger Entry"
    sig = bytearray(hybrid.sign(priv, msg))

    # Flip byte in Ed25519 signature (starts at offset 2)
    sig[2] ^= 0x01
    assert hybrid.verify(pub, msg, bytes(sig)) is False


def test_hybrid_sig_pq_tampered_pq_fails() -> None:
    """If the post-quantum Dilithium signature is corrupted, verification must fail."""
    hybrid = HybridSigPQ()
    pub, priv = hybrid.keypair()

    msg = b"Secure Audit Ledger Entry"
    sig = bytearray(hybrid.sign(priv, msg))

    c_sig_len = struct.unpack(">H", sig[:2])[0]
    # Flip byte in Dilithium signature
    sig[2 + c_sig_len] ^= 0x01
    assert hybrid.verify(pub, msg, bytes(sig)) is False


# ====================================================================
# 5. Plugin Registry Integration
# ====================================================================


def test_pq_plugins_registered() -> None:
    """Ensure PQ and Hybrid primitives are discoverable in plugin registries."""
    assert "kyber768" in kem_registry.list_available()
    assert "kyber1024" in kem_registry.list_available()
    assert "hybrid-kem-pq" in kem_registry.list_available()

    assert "dilithium3" in signature_registry.list_available()
    assert "dilithium5" in signature_registry.list_available()
    assert "hybrid-sig-pq" in signature_registry.list_available()
