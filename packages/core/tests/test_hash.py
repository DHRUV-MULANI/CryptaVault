"""Tests for CryptaVault hash algorithms and streaming interfaces.

Validates NIST test vectors, BLAKE3 official test vectors, chunked streaming equivalence,
size overrides, and plugin registry integration.
"""

from cryptavault.crypto.hash import Blake3, Sha256, Sha3512
from cryptavault.plugins.registry import hash_registry

# ====================================================================
# 1. NIST Known Answer Tests (KAT)
# ====================================================================


def test_sha256_nist_kat() -> None:
    """NIST CAVP KAT for SHA-256."""
    hasher = Sha256()
    # Empty string
    assert (
        hasher.digest(b"").hex()
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    # Standard "abc"
    assert (
        hasher.digest(b"abc").hex()
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_sha3_512_nist_kat() -> None:
    """NIST FIPS 202 KAT for SHA3-512."""
    hasher = Sha3512()
    # Empty string
    assert (
        hasher.digest(b"").hex()
        == "a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26"
    )
    # Standard "abc"
    assert (
        hasher.digest(b"abc").hex()
        == "b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0"
    )


# ====================================================================
# 2. BLAKE3 Official Vectors & Size Overrides
# ====================================================================


def test_blake3_kat_and_size_override() -> None:
    """Official BLAKE3 test vectors."""
    b3 = Blake3()
    # Empty input
    assert (
        b3.digest(b"").hex() == "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262"
    )
    # Standard "abc"
    assert (
        b3.digest(b"abc").hex()
        == "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85"
    )

    # 64-byte extended output
    ext_digest = b3.digest(b"abc", size=64)
    assert len(ext_digest) == 64
    assert ext_digest.startswith(bytes.fromhex("6437b3ac38465133ffb63b75273a8db5"))


# ====================================================================
# 3. Streaming Equivalence
# ====================================================================


def test_streaming_matches_oneshot_digest() -> None:
    """Ensure chunked incremental updates produce identical digest to one-shot."""
    data = b"CryptaVault zero-knowledge chunk stream payload " * 1024  # ~48KB
    chunk_size = 256

    for hasher in (Sha256(), Sha3512(), Blake3()):
        one_shot = hasher.digest(data)

        stream = hasher.streaming()
        for i in range(0, len(data), chunk_size):
            stream.update(data[i : i + chunk_size])

        assert stream.digest() == one_shot
        assert stream.hexdigest() == one_shot.hex()


# ====================================================================
# 4. Plugin Registry
# ====================================================================


def test_hash_registry_plugins() -> None:
    """Ensure all hash algorithms are registered."""
    for name in ("sha256", "sha3-512", "blake3"):
        assert name in hash_registry.list_available()
        cls = hash_registry.get(name)
        assert cls is not None
