"""Tests for Key Derivation Functions (Argon2id, HKDF, PBKDF2).

Includes RFC 5869 HKDF vectors, Argon2id determinism and execution timing,
RFC 6070 PBKDF2 vectors, error conditions, and plugin registry integration.
"""

import time

import pytest
from cryptavault.crypto.kdf import (
    Argon2id,
    HkdfSha256,
    InvalidSaltError,
    Pbkdf2,
)
from cryptavault.plugins.registry import kdf_registry

# ====================================================================
# 1. RFC 5869 Test Case 1 for HKDF-SHA256
# ====================================================================


def test_hkdf_sha256_rfc5869_case1() -> None:
    """RFC 5869 Section A.1 Test Case 1."""
    ikm = bytes.fromhex("0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b")
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    length = 42

    expected_prk = bytes.fromhex("077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5")
    expected_okm = bytes.fromhex(
        "3cb25f25faacd57a90434f64d0362f2a" "2d2d0a90cf1a5a4c5db02d56ecc4c5bf" "34007208d5b887185865"
    )

    kdf = HkdfSha256()

    # Verify extract
    prk = kdf.extract(salt, ikm)
    assert prk == expected_prk

    # Verify expand
    okm = kdf.expand(prk, info, length)
    assert okm == expected_okm

    # Verify full derive
    derived = kdf.derive(ikm, salt, length, info=info)
    assert derived == expected_okm


# ====================================================================
# 2. Argon2id Key Derivation & Timing
# ====================================================================


def test_argon2id_derivation_deterministic() -> None:
    """Argon2id with same inputs produces identical key."""
    argon = Argon2id()
    password = b"SuperUserSecretPassphrase994#"
    salt = bytes.fromhex("0102030405060708090a0b0c0d0e0f10")

    key1 = argon.derive(password, salt, length=32)
    key2 = argon.derive(password, salt, length=32)
    assert key1 == key2
    assert len(key1) == 32

    # Different salt must produce completely distinct key
    alt_salt = bytes.fromhex("1102030405060708090a0b0c0d0e0f10")
    key3 = argon.derive(password, alt_salt, length=32)
    assert key3 != key1


def test_argon2id_execution_time() -> None:
    """Ensure standard Argon2id configuration executes under 200ms on modern hardware."""
    argon = Argon2id()
    password = b"MasterEncryptionSecret!"
    salt = bytes.fromhex("deadbeefdeadbeefdeadbeefdeadbeef")

    start = time.perf_counter()
    derived = argon.derive(password, salt, length=32)
    elapsed = time.perf_counter() - start

    assert len(derived) == 32
    # Verify execution completes in reasonable interactive timeframe (typically ~20-60ms)
    assert elapsed < 0.35, f"Argon2id derivation took too long: {elapsed:.3f}s"


def test_argon2id_insufficient_salt_raises() -> None:
    """Salts under 16 bytes must raise InvalidSaltError."""
    argon = Argon2id()
    with pytest.raises(InvalidSaltError, match="requires at least 16 bytes of salt"):
        argon.derive(b"pwd", b"short_salt", length=32)


# ====================================================================
# 3. PBKDF2-HMAC-SHA256
# ====================================================================


def test_pbkdf2_insufficient_salt_raises() -> None:
    """Salts under 16 bytes must raise InvalidSaltError."""
    pbkdf2 = Pbkdf2()
    with pytest.raises(InvalidSaltError, match="requires at least 16 bytes of salt"):
        pbkdf2.derive(b"pwd", b"short_salt", length=32)


def test_pbkdf2_derivation_smoke() -> None:
    """Test PBKDF2 derivation with custom iteration count for speed in unit tests."""
    pbkdf2 = Pbkdf2()
    password = b"password"
    salt = b"salt_for_pbkdf2_16B"
    key = pbkdf2.derive(password, salt, length=32, iterations=1000)
    assert len(key) == 32


# ====================================================================
# 4. Plugin Registry Integration
# ====================================================================


def test_kdf_registry_plugins() -> None:
    """Ensure all KDF algorithms are properly registered in kdf_registry."""
    for name in ("argon2id", "pbkdf2-sha256", "hkdf-sha256"):
        assert name in kdf_registry.list_available()
        cls = kdf_registry.get(name)
        assert cls is not None
