"""Comprehensive tests for AES-256-GCM and ChaCha20-Poly1305 ciphers.

Includes NIST KAT vectors, Hypothesis property-based testing, authentication tag
integrity checks, error paths, and plugin registry integration.
"""

import os

import pytest
from cryptavault.crypto.symmetric import (
    AES256GCM,
    ChaCha20Poly1305,
    InvalidKeyError,
    InvalidNonceError,
    InvalidTagError,
)
from cryptavault.plugins.registry import encryption_registry
from hypothesis import given, settings
from hypothesis import strategies as st

# ====================================================================
# 1. NIST SP 800-38D Known Answer Test (KAT) for AES-256-GCM
# ====================================================================


def test_aes_256_gcm_nist_kat() -> None:
    """NIST SP 800-38D Test Case 14 (AES-256-GCM)."""
    key = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000000")
    nonce = bytes.fromhex("000000000000000000000000")
    plaintext = bytes.fromhex(
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    aad = b""
    expected_ciphertext = bytes.fromhex(
        "cea7403d4d606b6e074ec5d3baf39d18"
        "726003ca37a62a74d1a2f58e7506358e"
        "dd4ab1284d4ae17b41e85924470c36f7"
        "4741cbe181bb7f30617c1de3ab0c3a1f"
    )
    expected_tag = bytes.fromhex("5d5c0cd0c7b0138ac868f227d053cd0b")

    cipher = AES256GCM()
    result = cipher.encrypt(key, nonce, plaintext, aad)
    assert result == expected_ciphertext + expected_tag

    decrypted = cipher.decrypt(key, nonce, result, aad)
    assert decrypted == plaintext


# ====================================================================
# 2. RFC 8439 Known Answer Test (KAT) for ChaCha20-Poly1305
# ====================================================================


def test_chacha20_poly1305_rfc8439_kat() -> None:
    """RFC 8439 Section 2.8.2 KAT vector."""
    key = bytes.fromhex("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f")
    nonce = bytes.fromhex("070000004041424344454647")
    plaintext = (
        b"Ladies and Gentlemen of the class of '99: If I could offer you "
        b"only one tip for the future, sunscreen would be it."
    )
    aad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")

    expected_ciphertext_hex = (
        "d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d6"
        "3dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b36"
        "92ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc"
        "3ff4def08e4b7a9de576d26586cec64b6116"
    )
    expected_tag_hex = "1ae10b594f09e26a7e902ecbd0600691"
    expected_full = bytes.fromhex(expected_ciphertext_hex + expected_tag_hex)

    cipher = ChaCha20Poly1305()
    result = cipher.encrypt(key, nonce, plaintext, aad)
    assert result == expected_full

    decrypted = cipher.decrypt(key, nonce, result, aad)
    assert decrypted == plaintext


# ====================================================================
# 3. Hypothesis Property Testing
# ====================================================================


@settings(max_examples=100)
@given(
    plaintext=st.binary(min_size=0, max_size=16384),
    aad=st.binary(min_size=0, max_size=512),
)
def test_aes_256_gcm_hypothesis_roundtrip(plaintext: bytes, aad: bytes) -> None:
    """Property test: encrypt then decrypt restores original plaintext for any data."""
    key = os.urandom(32)
    cipher = AES256GCM()
    nonce, ciphertext = cipher.encrypt_auto_nonce(key, plaintext, aad)

    decrypted = cipher.decrypt(key, nonce, ciphertext, aad)
    assert decrypted == plaintext


@settings(max_examples=100)
@given(
    plaintext=st.binary(min_size=0, max_size=16384),
    aad=st.binary(min_size=0, max_size=512),
)
def test_chacha20_poly1305_hypothesis_roundtrip(plaintext: bytes, aad: bytes) -> None:
    """Property test: encrypt then decrypt restores original plaintext for ChaCha20."""
    key = os.urandom(32)
    cipher = ChaCha20Poly1305()
    nonce, ciphertext = cipher.encrypt_auto_nonce(key, plaintext, aad)

    decrypted = cipher.decrypt(key, nonce, ciphertext, aad)
    assert decrypted == plaintext


# ====================================================================
# 4. Fail-Closed Tampering & AAD Integrity
# ====================================================================


def test_tampered_ciphertext_fails_aes_gcm() -> None:
    """Flipping a single bit in ciphertext must cause InvalidTagError."""
    key = os.urandom(32)
    cipher = AES256GCM()
    nonce, ciphertext = cipher.encrypt_auto_nonce(key, b"Secret Financial Data", b"aad-header")

    # Tamper with the ciphertext
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0x01

    with pytest.raises(InvalidTagError):
        cipher.decrypt(key, nonce, bytes(tampered), b"aad-header")


def test_tampered_aad_fails_aes_gcm() -> None:
    """Modifying authenticated associated data must fail decryption."""
    key = os.urandom(32)
    cipher = AES256GCM()
    nonce, ciphertext = cipher.encrypt_auto_nonce(key, b"Critical Payload", b"user-id-1234")

    with pytest.raises(InvalidTagError):
        cipher.decrypt(key, nonce, ciphertext, b"user-id-5678")


def test_tampered_ciphertext_fails_chacha() -> None:
    """Flipping a bit in ChaCha20 ciphertext must trigger InvalidTagError."""
    key = os.urandom(32)
    cipher = ChaCha20Poly1305()
    nonce, ciphertext = cipher.encrypt_auto_nonce(key, b"Health Record Payload", b"metadata")

    tampered = bytearray(ciphertext)
    tampered[-1] ^= 0xFF

    with pytest.raises(InvalidTagError):
        cipher.decrypt(key, nonce, bytes(tampered), b"metadata")


# ====================================================================
# 5. Parameter Validation Tests
# ====================================================================


def test_invalid_key_length_raises() -> None:
    """Passing keys not equal to 32 bytes must raise InvalidKeyError."""
    cipher = AES256GCM()
    with pytest.raises(InvalidKeyError, match="requires a 32-byte key"):
        cipher.encrypt(b"short-key", os.urandom(12), b"test")

    chacha = ChaCha20Poly1305()
    with pytest.raises(InvalidKeyError, match="requires a 32-byte key"):
        chacha.encrypt(os.urandom(16), os.urandom(12), b"test")


def test_invalid_nonce_length_raises() -> None:
    """Passing nonces not equal to 12 bytes must raise InvalidNonceError."""
    cipher = AES256GCM()
    with pytest.raises(InvalidNonceError, match="requires a 12-byte nonce"):
        cipher.encrypt(os.urandom(32), b"bad-nonce", b"test")

    chacha = ChaCha20Poly1305()
    with pytest.raises(InvalidNonceError, match="requires a 12-byte nonce"):
        chacha.encrypt(os.urandom(32), os.urandom(16), b"test")


# ====================================================================
# 6. Plugin Registry Discovery
# ====================================================================


def test_symmetric_ciphers_registered() -> None:
    """Ensure both ciphers are properly registered in the plugin architecture."""
    assert "aes-256-gcm" in encryption_registry.list_available()
    assert "chacha20-poly1305" in encryption_registry.list_available()

    aes_cls = encryption_registry.get("aes-256-gcm")
    chacha_cls = encryption_registry.get("chacha20-poly1305")

    assert aes_cls is AES256GCM
    assert chacha_cls is ChaCha20Poly1305
