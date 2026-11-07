"""Tests for the crypto-agile CVV2 container format and legacy compatibility."""

import io

import pytest
from cryptavault.adaptive.engine import AdaptiveEngine
from cryptavault.adaptive.profiles import get_profile
from cryptavault.crypto.asymmetric import Ed25519Signer, SignatureVerificationError
from cryptavault.crypto.symmetric import InvalidTagError
from cryptavault.pipeline.chunked_encryption import ChunkedEncryptor
from cryptavault.pipeline.container import (
    CONTAINER_MAGIC,
    AlgorithmBinding,
    ContainerHeader,
    ContainerIntegrityError,
    ContainerTrailer,
    encode_header,
    read_header,
    read_trailer,
    write_header,
    write_trailer,
)
from cryptavault.pipeline.orchestrator import PipelineOrchestrator


def _header() -> ContainerHeader:
    return ContainerHeader(
        file_id="file-42",
        profile="BALANCED",
        compression="zstd",
        chunk_size_bytes=4 * 1024 * 1024,
        multi_layer=False,
        algorithms={
            "symmetric": AlgorithmBinding("symmetric", "aes-256-gcm", 0x0103),
            "hash": AlgorithmBinding("hash", "sha256", 0x0201),
            "kdf": AlgorithmBinding("kdf", "argon2id", 0x0301),
            "signature": AlgorithmBinding("signature", "ed25519", 0x0501),
            "kem": AlgorithmBinding("kem", "x25519", 0x0401),
        },
    )


def test_header_roundtrip_is_deterministic() -> None:
    """Headers serialize deterministically so signatures can bind the exact bytes."""
    header = _header()
    buf = io.BytesIO()
    raw = write_header(buf, header)
    assert raw.startswith(CONTAINER_MAGIC)

    buf.seek(0)
    parsed = read_header(buf)
    assert parsed == header
    assert encode_header(parsed) == raw
    assert parsed.binding("symmetric").algorithm_id == "aes-256-gcm"


def test_header_rejects_missing_family_and_duplicate_wires() -> None:
    """Malformed headers fail closed instead of guessing defaults."""
    data = _header().to_dict()
    del data["algorithms"]["kem"]
    with pytest.raises(ContainerIntegrityError):
        ContainerHeader.from_dict(data)

    data = _header().to_dict()
    data["algorithms"]["kem"]["wire_id"] = 0x0103
    with pytest.raises(ContainerIntegrityError):
        ContainerHeader.from_dict(data)


def test_trailer_roundtrip_and_missing_trailer() -> None:
    """Trailers roundtrip and a stripped trailer is detected."""
    trailer = ContainerTrailer(chunk_count=3, merkle_root_hex="ab" * 32, signature_hex="cd" * 8)
    buf = io.BytesIO()
    write_trailer(buf, trailer)
    buf.seek(0)
    assert read_trailer(buf) == trailer

    with pytest.raises(ContainerIntegrityError):
        read_trailer(io.BytesIO(b""))


def test_container_records_algorithms_and_decrypts_without_profile_hint() -> None:
    """Decryption is driven by the persisted header, not by caller-supplied defaults."""
    orch = PipelineOrchestrator()
    payload = b"Crypto-agile payload " * 500
    key = b"K" * 32

    encrypted = io.BytesIO()
    result = orch.run_encryption(
        io.BytesIO(payload), encrypted, key, profile_or_name="STANDARD", file_id="agile-1"
    )
    assert result.chunk_count >= 1

    encrypted.seek(0)
    header = read_header(encrypted)
    assert header.profile == "STANDARD"
    assert header.binding("symmetric").algorithm_id == "aes-256-gcm"
    assert header.binding("hash").algorithm_id == "sha256"

    encrypted.seek(0)
    decrypted = io.BytesIO()
    orch.run_decryption(encrypted, decrypted, key, profile_or_name="MAXIMUM")
    assert decrypted.getvalue() == payload


def test_signed_container_verifies_and_rejects_wrong_key() -> None:
    """A signature binds the header digest and Merkle root and fails closed."""
    signer = Ed25519Signer()
    public_key, private_key = signer.keypair()
    wrong_public_key, _ = signer.keypair()

    orch = PipelineOrchestrator()
    payload = b"signed content" * 400
    key = b"S" * 32
    encrypted = io.BytesIO()
    result = orch.run_encryption(
        io.BytesIO(payload),
        encrypted,
        key,
        profile_or_name="PERFORMANCE",
        signing_key=private_key,
    )
    assert result.signature_hex

    encrypted.seek(0)
    decrypted = io.BytesIO()
    orch.run_decryption(encrypted, decrypted, key, verification_key=public_key)
    assert decrypted.getvalue() == payload

    encrypted.seek(0)
    with pytest.raises(SignatureVerificationError):
        orch.run_decryption(encrypted, io.BytesIO(), key, verification_key=wrong_public_key)


def test_tampered_chunk_is_rejected() -> None:
    """Any modified ciphertext byte fails per-chunk authentication."""
    orch = PipelineOrchestrator()
    payload = b"tamper me " * 300
    key = b"T" * 32
    encrypted = io.BytesIO()
    orch.run_encryption(io.BytesIO(payload), encrypted, key, profile_or_name="BALANCED")

    blob = bytearray(encrypted.getvalue())
    blob[len(encode_header(read_header(io.BytesIO(blob)))) + 30] ^= 0xFF
    with pytest.raises((InvalidTagError, ContainerIntegrityError)):
        orch.run_decryption(io.BytesIO(bytes(blob)), io.BytesIO(), key)


def test_legacy_cvv1_container_still_decrypts() -> None:
    """Existing CVV1 files remain readable after the format upgrade."""
    orch = PipelineOrchestrator()
    profile = get_profile("BALANCED")
    config = orch.engine.resolve(profile)
    key = b"L" * 32
    file_id = "legacy-1"
    payload = b"legacy container payload" * 100

    legacy = io.BytesIO()
    fid = file_id.encode()
    comp = b"none"
    legacy.write(b"CVV1" + bytes([len(fid)]) + fid + bytes([len(comp)]) + comp)
    encryptor = ChunkedEncryptor(AdaptiveEngine())
    for chunk in encryptor.encrypt_stream(io.BytesIO(payload), key, config, file_id=file_id):
        legacy.write(chunk.serialize())

    legacy.seek(0)
    decrypted = io.BytesIO()
    orch.run_decryption(legacy, decrypted, key, profile_or_name="BALANCED")
    assert decrypted.getvalue() == payload
