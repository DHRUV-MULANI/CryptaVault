"""Tests for Classical Hybrid KEM (X25519 + HKDF-SHA256).

Covers two-party key encapsulation roundtrip, ephemeral key freshness,
binding of public key material, and plugin registry integration.
"""

from cryptavault.crypto.hybrid import HybridKemClassical
from cryptavault.plugins.registry import kem_registry


def test_hybrid_kem_roundtrip() -> None:
    """Ensure Alice and Bob arrive at the exact same 32-byte shared secret."""
    kem = HybridKemClassical()

    bob_pub, bob_priv = kem.keypair()
    assert len(bob_pub) == 32
    assert len(bob_priv) == 32

    # Alice encapsulates
    shared_alice, ciphertext = kem.encapsulate(bob_pub)
    assert len(shared_alice) == 32
    assert len(ciphertext) == 32

    # Bob decapsulates
    shared_bob = kem.decapsulate(bob_priv, ciphertext)
    assert shared_bob == shared_alice


def test_hybrid_kem_ephemeral_freshness() -> None:
    """Ensure consecutive encapsulations produce unique ephemeral keys and shared secrets."""
    kem = HybridKemClassical()
    pub, _ = kem.keypair()

    secret1, eph1 = kem.encapsulate(pub)
    secret2, eph2 = kem.encapsulate(pub)

    assert eph1 != eph2
    assert secret1 != secret2


def test_hybrid_kem_tampered_ciphertext_fails() -> None:
    """Tampering with ephemeral key must result in different derived secret."""
    kem = HybridKemClassical()
    bob_pub, bob_priv = kem.keypair()

    secret_alice, ciphertext = kem.encapsulate(bob_pub)

    # Flip a byte in the ephemeral public key (ciphertext)
    tampered_ct = bytearray(ciphertext)
    tampered_ct[0] ^= 0x01

    secret_bob = kem.decapsulate(bob_priv, bytes(tampered_ct))
    assert secret_bob != secret_alice


def test_hybrid_kem_registered_in_registry() -> None:
    """Ensure hybrid classical KEM is registered in kem_registry."""
    assert "hybrid-kem-classical" in kem_registry.list_available()
    assert kem_registry.get("hybrid-kem-classical") is HybridKemClassical
