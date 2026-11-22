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


def test_api_local_auth_and_workspace_isolation(api_client, auth_headers) -> None:
    """Verify local accounts, JWT sessions, and workspace isolation."""
    unknown = api_client.post("/api/auth/prelogin", json={"email": "nobody@cryptavault.dev"})
    assert unknown.status_code == 200
    assert unknown.json()["exists"] is False

    admin_headers = auth_headers("admin@cryptavault.dev")
    me = api_client.get("/api/auth/me", headers=admin_headers)
    assert me.status_code == 200
    admin_workspace_ids = {workspace["id"] for workspace in me.json()["workspaces"]}
    assert admin_workspace_ids

    viewer_headers = auth_headers("viewer@cryptavault.dev")
    viewer_me = api_client.get("/api/auth/me", headers=viewer_headers)
    assert viewer_me.status_code == 200
    viewer_workspace_ids = {workspace["id"] for workspace in viewer_me.json()["workspaces"]}

    private_workspace = next(iter(admin_workspace_ids - viewer_workspace_ids), None)
    if private_workspace:
        denied = api_client.get(
            f"/api/workspaces/{private_workspace}/files", headers=viewer_headers
        )
        assert denied.status_code == 403


def test_api_share_token_consume_flow(api_client, auth_headers) -> None:
    """Verify encrypted file sharing with expiry/use limits and public download."""
    import uuid

    headers = auth_headers("demo@cryptavault.dev")
    workspaces = api_client.get("/api/workspaces", headers=headers).json()
    workspace_id = workspaces[0]["id"]
    file_id = str(uuid.uuid4())
    form = {
        "file_id": file_id,
        "version": "1",
        "encrypted_meta": "ZW5jcnlwdGVkLW1ldGE=",
        "meta_iv": "MTIzNDU2Nzg5MDEy",
        "wrapped_key": "d3JhcHBlZC1rZXk=",
        "wrapped_iv": "MTIzNDU2Nzg5MDEy",
        "profile": "BALANCED",
        "storage_target": "local",
    }
    upload = api_client.post(
        f"/api/workspaces/{workspace_id}/files/upload",
        headers=headers,
        data=form,
        files={"ciphertext": ("report.cv", b"encrypted-report-body", "application/octet-stream")},
    )
    assert upload.status_code == 201, upload.text

    create = api_client.post(
        "/api/shares",
        headers=headers,
        json={"file_id": file_id, "max_uses": 1, "password": "share-pass"},
    )
    assert create.status_code == 201, create.text
    token = create.json()["token"]

    inspect = api_client.get(f"/api/shares/{token}")
    assert inspect.status_code == 200
    assert inspect.json()["file_id"] == file_id
    assert inspect.json()["remaining_uses"] == 1
    assert inspect.json()["password_protected"] is True

    wrong = api_client.post(f"/api/shares/{token}/download", json={"password": "wrong-pass"})
    assert wrong.status_code == 401

    consume = api_client.post(f"/api/shares/{token}/download", json={"password": "share-pass"})
    assert consume.status_code == 200
    assert consume.content == b"encrypted-report-body"

    exhausted = api_client.post(f"/api/shares/{token}/download", json={"password": "share-pass"})
    assert exhausted.status_code == 410

    api_client.delete(f"/api/files/{file_id}/permanent", headers=headers)


def test_api_audit_feature_is_not_exposed(api_client) -> None:
    """Audit logging is intentionally excluded from the dynamic product scope."""
    assert api_client.get("/api/audit").status_code == 404
    assert api_client.post("/api/audit", json={}).status_code == 404
