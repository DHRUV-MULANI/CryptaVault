"""Milestone 2 test suite: Adaptive Engine, Compression, Chunked Pipeline, and Manifests."""

import io
from pathlib import Path

from cryptavault.adaptive.audit import AuditLog
from cryptavault.adaptive.engine import AdaptiveEngine, MultiLayerEncryptor
from cryptavault.adaptive.forward_secrecy import RatchetKdf
from cryptavault.adaptive.profiles import resolve_slider
from cryptavault.compression.algorithms import compress, decompress
from cryptavault.compression.detect import detect_file_type
from cryptavault.compression.policy import should_compress
from cryptavault.metadata.encrypted_manifest import EncryptedManifestManager
from cryptavault.metadata.model import FileMetadata, Manifest
from cryptavault.metadata.secure_delete import secure_delete_file
from cryptavault.pipeline.orchestrator import PipelineOrchestrator


def test_adaptive_slider_and_engine() -> None:
    """Verify slider maps to 6 tiers and engine resolves configuration."""
    assert resolve_slider(10).level.value == "PERFORMANCE"
    assert resolve_slider(30).level.value == "STANDARD"
    assert resolve_slider(50).level.value == "BALANCED"
    assert resolve_slider(70).level.value == "STRONG"
    assert resolve_slider(85).level.value == "PQ_STRONG"
    assert resolve_slider(95).level.value == "MAXIMUM"

    engine = AdaptiveEngine()
    config = engine.resolve("MAXIMUM", file_size_bytes=2 * 1024 * 1024 * 1024)
    assert config.multi_layer is True
    assert config.chunk_size_bytes >= 8 * 1024 * 1024


def test_multi_layer_encryption_roundtrip() -> None:
    """Verify dual-layer ChaCha20 + AES-GCM encryption."""
    ml = MultiLayerEncryptor()
    key = b"A" * 32
    plaintext = b"State-sponsored level protection test payload"
    aad = b"context-maximum"

    nonce, payload = ml.encrypt(key, plaintext, aad=aad)
    recovered = ml.decrypt(key, nonce, payload, aad=aad)
    assert recovered == plaintext


def test_compression_detect_and_policy() -> None:
    """Verify file type detection and skip policy for pre-compressed assets."""
    jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    text_data = b"Repeated text data " * 50

    assert detect_file_type(jpeg_header).is_pre_compressed is True
    assert should_compress(jpeg_header) is False

    assert should_compress(text_data) is True
    z_comp = compress(text_data, "zstd")
    assert len(z_comp) < len(text_data)
    assert decompress(z_comp, "zstd") == text_data


def test_forward_secrecy_ratchet() -> None:
    """Verify ratchet produces unique sequential keys and advances state."""
    ratchet = RatchetKdf()
    key1 = ratchet.next_key()
    key2 = ratchet.next_key()
    assert key1 != key2
    assert ratchet.counter == 2


def test_audit_log_hash_chain() -> None:
    """Verify append-only hash-chained audit logging."""
    audit = AuditLog()
    e1 = audit.append(action="ENCRYPT", file_id="file1.txt")
    e2 = audit.append(action="DECRYPT", file_id="file1.txt")
    assert e2.prev_hash == e1.entry_hash
    assert audit.verify_chain() is True

    # Tamper with an entry
    e1.action = "TAMPERED_ACTION"
    assert audit.verify_chain() is False


def test_encrypted_manifest_roundtrip() -> None:
    """Verify encrypted manifest serialization and retrieval."""
    manifest = Manifest(vault_id="vault-test-001")
    meta = FileMetadata(
        file_id="f-01",
        original_name="test.txt",
        original_size_bytes=100,
        mime_type="text/plain",
        created_at="2026-09-05T00:00:00Z",
        modified_at="2026-09-05T00:00:00Z",
        chunk_count=1,
        compression_algo="zstd",
        encryption_algo="aes-256-gcm",
        key_id="k-01",
        merkle_root_hex="abc123root",
        signature_hex="sig123hex",
        extra_attributes={},
    )
    manifest.add_file(meta)

    mgr = EncryptedManifestManager()
    key = b"M" * 32
    enc_blob = mgr.encrypt_manifest(manifest, key)
    dec_manifest = mgr.decrypt_manifest(enc_blob, key)

    assert dec_manifest.vault_id == "vault-test-001"
    assert "f-01" in dec_manifest.files


def test_pipeline_orchestrator_e2e(tmp_path: Path) -> None:
    """Verify full pipeline: compression -> chunked AEAD -> Merkle -> recovery."""
    payload = b"Large streaming payload simulation test content " * 1000
    in_stream = io.BytesIO(payload)
    out_stream = io.BytesIO()
    key = b"K" * 32

    orch = PipelineOrchestrator()
    res = orch.run_encryption(in_stream, out_stream, encryption_key=key, profile_or_name="BALANCED")
    assert res.chunk_count >= 1
    assert len(res.merkle_root_hex) == 64

    # Decrypt
    out_stream.seek(0)
    dec_stream = io.BytesIO()
    recovered_size = orch.run_decryption(
        out_stream, dec_stream, encryption_key=key, profile_or_name="BALANCED"
    )
    assert recovered_size == len(payload)
    assert dec_stream.getvalue() == payload


def test_secure_deletion(tmp_path: Path) -> None:
    """Verify DoD multi-pass file overwrite and deletion."""
    test_f = tmp_path / "sensitive.txt"
    test_f.write_text("Extremely sensitive cryptographic secret")
    assert test_f.exists()

    secure_delete_file(test_f, passes=3)
    assert not test_f.exists()
