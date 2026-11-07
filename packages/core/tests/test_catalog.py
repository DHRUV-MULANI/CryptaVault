"""Tests for the crypto catalog, algorithm agility, and cascaded AEAD."""

import pytest
from cryptavault.adaptive.engine import AdaptiveEngine, MultiLayerEncryptor, resolve_aead
from cryptavault.adaptive.profiles import get_profile
from cryptavault.crypto.cascade import CascadeAEAD
from cryptavault.crypto.catalog import (
    AlgorithmRejectedError,
    AlgorithmUnavailableError,
    CryptoFamily,
    catalog,
)
from cryptavault.crypto.symmetric import InvalidTagError
from cryptavault.plugins.registry import encryption_registry


def test_every_registered_symmetric_cipher_is_catalogued() -> None:
    """Every encryption plugin must have catalog metadata and pass usability checks."""
    for name in encryption_registry.list_available():
        spec = catalog.require_usable(name, CryptoFamily.SYMMETRIC)
        assert spec.algorithm_id == name


def test_wire_ids_are_unique_and_roundtrip() -> None:
    """Wire identifiers are permanent and must resolve back to their spec."""
    seen: set[int] = set()
    for spec in catalog.specs:
        assert spec.wire_id not in seen
        seen.add(spec.wire_id)
        assert catalog.from_wire_id(spec.wire_id) is spec


def test_alias_resolution() -> None:
    """Common names and NIST aliases resolve to canonical identifiers."""
    assert catalog.resolve_id("aes256gcm") == "aes-256-gcm"
    assert catalog.resolve_id("Kyber768") == "ml-kem-768"
    assert catalog.resolve_id("dilithium3") == "ml-dsa-65"
    assert catalog.resolve_id("SHA-256") == "sha256"
    assert catalog.get("kyber").algorithm_id == "ml-kem-768"


def test_forbidden_algorithms_are_rejected() -> None:
    """Broken algorithms cannot be selected even with legacy opt-in."""
    for forbidden in ("md5", "sike-p434", "rainbow"):
        with pytest.raises(AlgorithmRejectedError):
            catalog.require_usable(forbidden, allow_legacy=True)


def test_legacy_and_experimental_require_opt_in() -> None:
    """Legacy and experimental algorithms are gated behind explicit opt-in."""
    with pytest.raises(AlgorithmRejectedError):
        catalog.require_usable("sha1")
    with pytest.raises(AlgorithmRejectedError):
        catalog.require_usable("sqisign")
    assert catalog.get("sqisign").status.value == "experimental"


def test_unimplemented_algorithms_are_rejected() -> None:
    """Catalogued-but-unimplemented algorithms fail closed at resolution time."""
    with pytest.raises(AlgorithmUnavailableError):
        catalog.require_usable("xchacha20-poly1305", CryptoFamily.SYMMETRIC)
    with pytest.raises(AlgorithmUnavailableError):
        catalog.require_usable("frodokem-976", CryptoFamily.KEM)


def test_family_mismatch_is_rejected() -> None:
    """An algorithm cannot be used as a member of the wrong family."""
    with pytest.raises(AlgorithmRejectedError):
        catalog.require_usable("blake3", CryptoFamily.SYMMETRIC)


@pytest.mark.parametrize(
    "algorithm_id",
    [spec.algorithm_id for spec in catalog.list(CryptoFamily.SYMMETRIC, implemented_only=True)],
)
def test_symmetric_aead_roundtrip_and_tamper(algorithm_id: str) -> None:
    """Every implemented AEAD roundtrips and fails closed on tampering."""
    cipher = resolve_aead(algorithm_id)
    key = b"K" * cipher.key_size_bytes
    nonce, ciphertext = cipher.encrypt_auto_nonce(key, b"agility payload", aad=b"ctx")
    assert cipher.decrypt(key, nonce, ciphertext, aad=b"ctx") == b"agility payload"

    tampered = ciphertext[:-1] + bytes([ciphertext[-1] ^ 0x01])
    with pytest.raises(InvalidTagError):
        cipher.decrypt(key, nonce, tampered, aad=b"ctx")
    with pytest.raises(InvalidTagError):
        cipher.decrypt(key, nonce, ciphertext, aad=b"wrong-context")


def test_cascade_roundtrip_and_tamper() -> None:
    """A cascade verifies every layer and rejects any tampering."""
    cascade = CascadeAEAD(("chacha20-poly1305", "aes-256-gcm"))
    key = b"R" * 32
    nonce, payload = cascade.encrypt_auto_nonce(key, b"layered secret", aad=b"aad")
    assert cascade.decrypt(key, nonce, payload, aad=b"aad") == b"layered secret"

    tampered = bytearray(payload)
    tampered[-1] ^= 0x01
    with pytest.raises(InvalidTagError):
        cascade.decrypt(key, nonce, bytes(tampered), aad=b"aad")


def test_engine_uses_registry_not_hardcoded_ciphers() -> None:
    """The engine can run any catalogued AEAD chosen by a profile."""
    engine = AdaptiveEngine()
    profile = get_profile("PERFORMANCE").model_copy(update={"symmetric_cipher": "aes-128-gcm"})
    config = engine.resolve(profile)
    assert config.symmetric_cipher == "aes-128-gcm"

    key = b"Z" * 16
    nonce, ciphertext = engine.encrypt_block(config, key, b"adaptive", aad=b"x")
    assert engine.decrypt_block(config, key, nonce, ciphertext, aad=b"x") == b"adaptive"


def test_multi_layer_encryptor_accepts_alternative_ciphers() -> None:
    """The cascade order is configurable rather than hardcoded."""
    ml = MultiLayerEncryptor(inner="aes-256-gcm", outer="aes-256-gcm-siv")
    key = b"L" * 32
    nonce, payload = ml.encrypt(key, b"alternative cascade", aad=b"aad")
    assert ml.decrypt(key, nonce, payload, aad=b"aad") == b"alternative cascade"
