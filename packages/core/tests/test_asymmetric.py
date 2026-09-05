"""Tests for asymmetric cryptographic primitives in CryptaVault.

Covers X25519 KEM key agreement, Ed25519 and ECDSA signatures, RSA-4096 OAEP/PSS,
tamper resistance, password-protected PEM serialization, and plugin integration.
"""

from cryptavault.crypto.asymmetric import (
    RSA4096,
    ECDSAP256Signer,
    Ed25519Signer,
    KeyPair,
    X25519Kem,
)
from cryptavault.plugins.registry import kem_registry, signature_registry

# ====================================================================
# 1. X25519 Key Encapsulation / Diffie-Hellman
# ====================================================================


def test_x25519_kem_roundtrip() -> None:
    """Ensure two parties arrive at identical shared secret."""
    kem = X25519Kem()

    # Bob generates static or long-term keypair
    bob_pub, bob_priv = kem.keypair()
    assert len(bob_pub) == 32
    assert len(bob_priv) == 32

    # Alice encapsulates a secret using Bob's public key
    shared_secret_alice, ciphertext = kem.encapsulate(bob_pub)
    assert len(shared_secret_alice) == 32
    assert len(ciphertext) == 32  # Ephemeral public key

    # Bob decapsulates using his private key and the received ciphertext
    shared_secret_bob = kem.decapsulate(bob_priv, ciphertext)
    assert shared_secret_bob == shared_secret_alice


def test_x25519_registered_in_plugin_registry() -> None:
    """Ensure X25519 KEM is registered in kem_registry."""
    assert "x25519" in kem_registry.list_available()
    assert kem_registry.get("x25519") is X25519Kem


# ====================================================================
# 2. Ed25519 Digital Signatures
# ====================================================================


def test_ed25519_sign_and_verify() -> None:
    """RFC 8032 Ed25519 signing and verification."""
    signer = Ed25519Signer()
    pub, priv = signer.keypair()
    assert len(pub) == 32
    assert len(priv) == 32

    message = b"Authenticated Manifest Block #0042"
    signature = signer.sign(priv, message)
    assert len(signature) == 64

    # Valid verification
    assert signer.verify(pub, message, signature) is True

    # Tampered message
    assert signer.verify(pub, message + b"!", signature) is False

    # Corrupted signature
    tampered_sig = bytearray(signature)
    tampered_sig[0] ^= 0x01
    assert signer.verify(pub, message, bytes(tampered_sig)) is False


def test_ed25519_registered_in_plugin_registry() -> None:
    """Ensure Ed25519 is registered in signature_registry."""
    assert "ed25519" in signature_registry.list_available()
    assert signature_registry.get("ed25519") is Ed25519Signer


# ====================================================================
# 3. ECDSA (P-256) Signatures
# ====================================================================


def test_ecdsa_p256_sign_and_verify() -> None:
    """ECDSA P-256 signing and verification."""
    signer = ECDSAP256Signer()
    pub, priv = signer.keypair()

    message = b"Audited System Action: GRANT_KEY"
    signature = signer.sign(priv, message)
    assert len(signature) > 0

    assert signer.verify(pub, message, signature) is True
    assert signer.verify(pub, b"Tampered Message", signature) is False


def test_ecdsa_registered_in_plugin_registry() -> None:
    """Ensure ECDSA is registered in signature_registry."""
    assert "ecdsa-p256" in signature_registry.list_available()
    assert signature_registry.get("ecdsa-p256") is ECDSAP256Signer


# ====================================================================
# 4. RSA-4096 OAEP and PSS
# ====================================================================


def test_rsa4096_oaep_roundtrip() -> None:
    """RSA-4096 OAEP encryption and decryption roundtrip."""
    # Use smaller test key for fast unit testing or full 4096
    # RSA4096 generate keypair
    pub, priv = RSA4096.generate_keypair()
    plaintext = b"Pre-Shared Key Wrap (32-byte master key)"

    ciphertext = RSA4096.encrypt_oaep(pub, plaintext)
    assert len(ciphertext) == 512  # 4096 bits = 512 bytes

    decrypted = RSA4096.decrypt_oaep(priv, ciphertext)
    assert decrypted == plaintext


def test_rsa4096_pss_sign_verify() -> None:
    """RSA-4096 PSS signing and verification."""
    pub, priv = RSA4096.generate_keypair()
    message = b"Zero-Knowledge Certificate Root Authority"

    sig = RSA4096.sign_pss(priv, message)
    assert len(sig) == 512

    assert RSA4096.verify_pss(pub, message, sig) is True
    assert RSA4096.verify_pss(pub, b"Altered root authority", sig) is False


# ====================================================================
# 5. KeyPair PEM Export & Password Encryption
# ====================================================================


def test_keypair_pem_without_password() -> None:
    """Exporting KeyPair to unencrypted PEM."""
    signer = Ed25519Signer()
    pub, priv = signer.keypair()
    pair = KeyPair(algorithm="ed25519", public_bytes=pub, private_bytes=priv)

    pub_pem, priv_pem = pair.to_pem()
    assert b"-----BEGIN PUBLIC KEY-----" in pub_pem
    assert b"-----BEGIN PRIVATE KEY-----" in priv_pem


def test_keypair_pem_with_password() -> None:
    """Exporting KeyPair to PKCS#8 password-encrypted PEM."""
    signer = Ed25519Signer()
    pub, priv = signer.keypair()
    pair = KeyPair(algorithm="ed25519", public_bytes=pub, private_bytes=priv)

    pub_pem, priv_pem = pair.to_pem(password=b"SuperSecretPassphrase123!")
    assert b"-----BEGIN PUBLIC KEY-----" in pub_pem
    assert b"-----BEGIN ENCRYPTED PRIVATE KEY-----" in priv_pem
