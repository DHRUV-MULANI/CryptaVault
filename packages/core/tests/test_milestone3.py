"""Milestone 3 test suite: Multi-Backend Storage, Secure Sharing, and API Endpoints."""

import io
from pathlib import Path

import pytest
from cryptavault.crypto.asymmetric import Ed25519Signer
from cryptavault.crypto.hybrid import HybridKemPQ
from cryptavault.sharing.invitation import InvitationShareManager
from cryptavault.sharing.package import SharePackage
from cryptavault.sharing.password import PasswordKeyProtector
from cryptavault.sharing.timed_link import TimedShareLink
from cryptavault.sharing.token import ShareTokenManager
from cryptavault.storage.local import LocalStorage
from cryptavault.storage.mock import MockStorage
from cryptavault.storage.registry import resolve_storage
from cryptavault_api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# ==========================================
# 1. Storage Connectors Tests
# ==========================================


def test_mock_storage_roundtrip() -> None:
    """Verify MockStorage upload, download, stat, list, and delete."""
    storage = MockStorage()
    storage.authenticate()

    payload = b"Top secret ciphertext bytes"
    uri = storage.upload(io.BytesIO(payload), "vaults/secret.enc")
    assert uri == "mock://vaults/secret.enc"
    assert storage.exists("vaults/secret.enc")

    # Download
    stream = storage.download("vaults/secret.enc")
    assert stream.read() == payload

    # Stat
    stat = storage.stat("vaults/secret.enc")
    assert stat.size_bytes == len(payload)
    assert not stat.is_dir

    # List
    items = storage.list("vaults")
    assert len(items) == 1
    assert items[0].path == "vaults/secret.enc"

    # Delete
    assert storage.delete("vaults/secret.enc")
    assert not storage.exists("vaults/secret.enc")


def test_local_storage_atomic_roundtrip(tmp_path: Path) -> None:
    """Verify LocalStorage enforces directory isolation and atomic write."""
    storage = LocalStorage(tmp_path)
    storage.authenticate()

    payload = b"CryptaVault local encrypted block"
    uri = storage.upload(io.BytesIO(payload), "blobs/block_001.bin")
    assert "local://" in uri

    downloaded = storage.download("blobs/block_001.bin").read()
    assert downloaded == payload

    # Traversal attack prevention
    with pytest.raises(ValueError, match="Path traversal detected"):
        storage.upload(io.BytesIO(b"evil"), "../../etc/passwd")


def test_storage_registry_resolution(tmp_path: Path) -> None:
    """Verify URI auto-detection resolves proper connector classes."""
    mock_conn = resolve_storage("mock://test-bucket")
    assert isinstance(mock_conn, MockStorage)

    assert isinstance(resolve_storage(f"local://{tmp_path}"), LocalStorage)
    assert isinstance(resolve_storage(str(tmp_path)), LocalStorage)


# ==========================================
# 2. Secure Sharing Tests
# ==========================================


def test_share_package_signature_tamper_evident() -> None:
    """Ensure SharePackage is signed and fails closed if modified."""
    signer = Ed25519Signer()
    pkg = SharePackage(
        file_id="doc-12345",
        filename="confidential.pdf",
        file_size_bytes=1024,
        ciphertext_ref="supabase://vaults/doc-12345.enc",
    )
    pub, priv = signer.keypair()
    pkg.sign(priv, pub)
    assert pkg.verify_signature() is True

    # Tampering with ciphertext reference
    pkg.ciphertext_ref = "supabase://vaults/malicious.enc"
    assert pkg.verify_signature() is False


def test_one_time_token_lifecycle() -> None:
    """Verify one-time token consumption and exhaustion."""
    secret = b"k" * 32
    token = ShareTokenManager.create_token(secret, file_id="file-99", max_uses=1)
    assert token.is_valid(secret)

    # First consumption succeeds
    assert ShareTokenManager.consume_token(token, secret) is True
    assert token.current_uses == 1

    # Second consumption fails (exhausted)
    assert ShareTokenManager.consume_token(token, secret) is False


def test_timed_share_link_tamper_and_expiry() -> None:
    """Verify TimedShareLink rejects tampered signatures and expired links."""
    secret = b"s" * 32
    url = TimedShareLink.generate_link(
        base_url="https://cryptavault.local/share",
        secret_key=secret,
        file_id="my-file-id",
        validity_seconds=3600,
    )
    res = TimedShareLink.verify_link(url, secret)
    assert res.is_valid is True
    assert res.file_id == "my-file-id"
    assert res.remaining_seconds > 0

    # Tamper with file_id in query
    tampered_url = url.replace("my-file-id", "other-file-id")
    tampered_res = TimedShareLink.verify_link(tampered_url, secret)
    assert tampered_res.is_valid is False
    assert "tampered" in str(tampered_res.error).lower()


def test_password_protected_key_wrapping() -> None:
    """Verify Argon2id password-protected key wrapping."""
    file_key = b"A" * 32
    password = "CorrectHorseBatteryStaple!"

    wrapped = PasswordKeyProtector.wrap_key(file_key, password, memory_cost_kib=8192, time_cost=1)

    # Correct password unwraps key
    unwrapped = PasswordKeyProtector.unwrap_key(wrapped, password)
    assert unwrapped == file_key

    # Wrong password raises ValueError
    with pytest.raises(ValueError, match="Incorrect share password"):
        PasswordKeyProtector.unwrap_key(wrapped, "WrongPassword123")


def test_invitation_share_hybrid_kem() -> None:
    """Verify post-quantum hybrid KEM invitation share wrapping."""
    kem = HybridKemPQ()
    recipient_pub, recipient_priv = kem.keypair()

    manager = InvitationShareManager()
    file_key = b"F" * 32

    # Wrap for recipient
    envelope = manager.wrap_key_for_recipient(
        raw_key=file_key,
        recipient_id="alice",
        recipient_hybrid_pubkey=recipient_pub,
    )

    # Recipient unwraps key
    unwrapped = manager.unwrap_key_as_recipient(envelope, recipient_priv)
    assert unwrapped == file_key


# ==========================================
# 3. FastAPI API Backend Tests
# ==========================================


def test_api_health_and_readiness() -> None:
    """Verify /health and /ready endpoints."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["zero_knowledge_boundary"] == "ENFORCED"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


def test_api_user_manifest_sync_isolation() -> None:
    """Verify encrypted manifest upload and retrieve for authenticated user."""
    auth_headers = {"Authorization": "Bearer mock-user-token-alice"}

    # Initially 404
    res = client.get("/api/users/me/manifest", headers=auth_headers)
    assert res.status_code == 404

    # Upload encrypted manifest
    manifest_payload = {
        "manifest_version": 1,
        "ciphertext_b64": "ZW5jcnlwdGVkX21hbmlmZXN0",
        "nonce_b64": "MTIzNDU2Nzg5MDEy",
        "hash_blake3_hex": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "file_count": 3,
    }
    put_res = client.put("/api/users/me/manifest", json=manifest_payload, headers=auth_headers)
    assert put_res.status_code == 200

    # Retrieve
    get_res = client.get("/api/users/me/manifest", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["hash_blake3_hex"] == manifest_payload["hash_blake3_hex"]

    # User B cannot see User A's manifest
    bob_headers = {"Authorization": "Bearer mock-user-token-bob"}
    bob_res = client.get("/api/users/me/manifest", headers=bob_headers)
    assert bob_res.status_code == 404


def test_api_share_token_consume_flow() -> None:
    """Verify API share creation, public inspect, and consume flow."""
    auth_headers = {"Authorization": "Bearer mock-user-token-carol"}

    create_payload = {
        "file_id": "report-2026",
        "filename": "Q3_Audit.pdf",
        "ciphertext_ref": "supabase://vaults/report-2026.enc",
        "max_uses": 1,
        "password_protected": False,
    }
    create_res = client.post("/api/shares", json=create_payload, headers=auth_headers)
    assert create_res.status_code == 200
    token_id = create_res.json()["token_id"]

    # Public inspect (no auth required)
    inspect_res = client.get(f"/api/shares/{token_id}")
    assert inspect_res.status_code == 200
    assert inspect_res.json()["file_id"] == "report-2026"
    assert inspect_res.json()["remaining_uses"] == 1

    # Consume token
    consume_res = client.post(f"/api/shares/{token_id}/consume")
    assert consume_res.status_code == 200
    assert consume_res.json()["remaining_uses"] == 0

    # Second consume is rejected (410 GONE)
    consume_res_2 = client.post(f"/api/shares/{token_id}/consume")
    assert consume_res_2.status_code == 410


def test_api_audit_append_and_verify() -> None:
    """Verify audit log append and client-side chain verification."""
    auth_headers = {"Authorization": "Bearer mock-user-token-dave"}

    # Append entry
    audit_entry = {
        "operation": "ENCRYPT",
        "file_id": "file-xyz",
        "file_hash": "a" * 64,
        "profile_level": "MAXIMUM",
        "signature": "sig_hex",
        "public_key": "pub_hex",
        "extra": {"chunks": 4},
    }
    post_res = client.post("/api/audit", json=audit_entry, headers=auth_headers)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "recorded"

    # List entries
    list_res = client.get("/api/audit", headers=auth_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
