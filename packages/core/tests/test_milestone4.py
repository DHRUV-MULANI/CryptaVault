"""Milestone 4 test suite: Admin Governance, Benchmark Lab, AI Advisory, and Full Integration."""

import json

from cryptavault.ai.knowledge_base import list_concepts, lookup_concept
from cryptavault.ai.llm import OfflineAiProvider, SanitizedMetadata
from cryptavault.ai.rules import RuleBasedRecommender
from cryptavault.benchmark.suite import BenchmarkSuite
from cryptavault_api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# ==========================================
# 1. Benchmark Lab Tests
# ==========================================


def test_benchmark_suite_execution_and_export() -> None:
    """Verify BenchmarkSuite runs across primitives and exports valid CSV and JSON."""
    suite = BenchmarkSuite()
    results = suite.run_all(payload_size_bytes=64 * 1024, iterations=1)
    assert len(results) >= 7

    # Verify JSON export
    json_str = suite.to_json()
    parsed = json.loads(json_str)
    assert len(parsed) == len(results)
    assert parsed[0]["algorithm"]

    # Verify CSV export
    csv_str = suite.to_csv()
    assert "throughput_mb_s" in csv_str
    assert "latency_ms" in csv_str
    assert "nist_level" in csv_str


# ==========================================
# 2. AI Security Advisory & Data Minimization Tests
# ==========================================


def test_ai_rule_based_recommender_scenarios() -> None:
    """Verify RuleBasedRecommender against key scenarios."""
    # Scenario 1: Pre-compressed media skips compression
    rec_jpg = RuleBasedRecommender.advise("vacation.jpg", 5 * 1024 * 1024, "BALANCED")
    assert rec_jpg.compression_mode == "none"

    rec_mp4 = RuleBasedRecommender.advise("video.mp4", 500 * 1024 * 1024, "BALANCED")
    assert rec_mp4.compression_mode == "none"

    rec_zip = RuleBasedRecommender.advise("archive.zip", 20 * 1024 * 1024, "BALANCED")
    assert rec_zip.compression_mode == "none"

    # Scenario 2: Massive dataset (>10GB) skips compression, optimizes for throughput
    rec_big = RuleBasedRecommender.advise("backup.tar", 15 * 1024 * 1024 * 1024, "BALANCED")
    assert rec_big.compression_mode == "none"
    assert rec_big.chunk_size_bytes == 16 * 1024 * 1024
    assert rec_big.parallel_workers == 8

    # Scenario 3: Highly compressible structured text uses Zstandard
    rec_txt = RuleBasedRecommender.advise("dataset.csv", 2 * 1024 * 1024, "BALANCED")
    assert rec_txt.compression_mode == "zstd"

    rec_json = RuleBasedRecommender.advise("database.json", 10 * 1024 * 1024, "BALANCED")
    assert rec_json.compression_mode == "zstd"

    # Scenario 4: Sensitive credentials enforce multi-layer and forward secrecy
    rec_sec = RuleBasedRecommender.advise("wallet_seed.txt", 1024, "BALANCED")
    assert rec_sec.forward_secrecy is True
    assert rec_sec.multi_layer is True

    # Scenario 5: MAXIMUM profile always enforces dual-layer and forward secrecy
    rec_max = RuleBasedRecommender.advise("project.bin", 5 * 1024 * 1024, "MAXIMUM")
    assert rec_max.forward_secrecy is True
    assert rec_max.multi_layer is True


def test_ai_data_minimization_isolation() -> None:
    """Verify that SanitizedMetadata strips filenames and paths to guarantee zero leak."""
    sanitized = SanitizedMetadata.sanitize(
        filename="/home/user/super_secret_personal_financials.pdf",
        size_bytes=1048576,
        profile_level="BALANCED",
    )
    # The file name and path must NOT be present
    assert "super_secret" not in sanitized.file_category
    assert "/home/user" not in sanitized.file_category
    assert sanitized.file_category == "pdf"
    assert sanitized.size_bytes == 1048576


def test_ai_knowledge_base_concepts() -> None:
    """Verify curated knowledge base lookups and explanations."""
    concepts = list_concepts()
    assert len(concepts) >= 10

    # Lookup Kyber
    kyber = lookup_concept("kyber-768")
    assert kyber is not None
    assert "FIPS 203" in kyber["nist_standard"]

    # Lookup Argon2id
    argon = lookup_concept("argon2id")
    assert argon is not None
    assert "Memory-hard" in argon["description"]

    # Provider explain
    provider = OfflineAiProvider()
    explanation = provider.explain_concept("aes-256-gcm")
    assert "AES-256-GCM" in explanation


# ==========================================
# 3. Admin & Metrics API Endpoints Tests
# ==========================================


def test_api_admin_routes_and_rbac(api_client, auth_headers) -> None:
    """Verify admin endpoints enforce real JWT RBAC and impersonation."""
    user_headers = auth_headers("demo@cryptavault.dev")
    admin_headers = auth_headers("admin@cryptavault.dev")

    res_user = api_client.get("/api/admin/users", headers=user_headers)
    assert res_user.status_code == 403

    res_admin = api_client.get("/api/admin/users", headers=admin_headers)
    assert res_admin.status_code == 200
    users = res_admin.json()
    assert len(users) >= 2
    target = next(user for user in users if user["email"] == "demo@cryptavault.dev")

    imp_res = api_client.post(f"/api/admin/impersonate/{target['id']}", headers=admin_headers)
    assert imp_res.status_code == 200
    assert imp_res.json()["impersonated_user"] == target["id"]
    assert imp_res.json()["access_token"]

    flags_res = api_client.get("/api/admin/flags", headers=admin_headers)
    assert flags_res.status_code == 200
    assert flags_res.json()["enable_sharing"] is True


def test_api_metrics_and_security_badge() -> None:
    """Verify metrics and security badge endpoints."""
    res_bench = client.get("/api/metrics/benchmark")
    assert res_bench.status_code == 200
    assert len(res_bench.json()) >= 5

    res_badge = client.get("/api/metrics/security-badge?profile=MAXIMUM")
    assert res_badge.status_code == 200
    badge = res_badge.json()
    assert badge["classical_bits"] == 256
    assert badge["pq_bits"] == 192


def test_api_ai_recommend_and_chat() -> None:
    """Verify AI advisory and chat endpoints."""
    req_body = {
        "filename": "source_code.py",
        "size_bytes": 10240,
        "profile_level": "BALANCED",
    }
    res_rec = client.post("/api/ai/recommend", json=req_body)
    assert res_rec.status_code == 200
    assert res_rec.json()["compression_mode"] == "zstd"

    res_chat = client.post("/api/ai/chat", json={"message": "explain kyber-768"})
    assert res_chat.status_code == 200
    assert "FIPS 203" in res_chat.json()["reply"]

    res_concepts = client.get("/api/ai/concepts")
    assert res_concepts.status_code == 200
    assert len(res_concepts.json()) >= 10


def test_storage_target_admin_and_ciphertext_upload(api_client, auth_headers) -> None:
    """Verify S3/cloud target registry plus the zero-knowledge upload API."""
    import uuid

    from cryptavault.storage.cloud.r2 import CloudflareR2Storage
    from cryptavault.storage.registry import resolve_storage

    r2_conn = resolve_storage("r2://my-test-vault")
    assert isinstance(r2_conn, CloudflareR2Storage)
    assert r2_conn.scheme == "r2"

    headers = auth_headers("admin@cryptavault.dev")
    targets = api_client.get("/api/storage/targets", headers=headers)
    assert targets.status_code == 200
    assert any(target["name"] == "local" for target in targets.json())

    workspace_id = api_client.get("/api/workspaces", headers=headers).json()[0]["id"]
    file_id = str(uuid.uuid4())
    form = {
        "file_id": file_id,
        "version": "1",
        "encrypted_meta": "ZW5jcnlwdGVkLW1ldGE=",
        "meta_iv": "MTIzNDU2Nzg5MDEy",
        "wrapped_key": "d3JhcHBlZC1rZXk=",
        "wrapped_iv": "MTIzNDU2Nzg5MDEy",
        "profile": "MAXIMUM",
        "storage_target": "local",
    }
    upload = api_client.post(
        f"/api/workspaces/{workspace_id}/files/upload",
        headers=headers,
        data=form,
        files={"ciphertext": ("test.cv", b"CIPHERTEXT_TEST_PAYLOAD", "application/octet-stream")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["storage_target"] == "local"

    files = api_client.get(f"/api/workspaces/{workspace_id}/files", headers=headers)
    assert files.status_code == 200
    assert any(item["id"] == file_id for item in files.json())

    api_client.delete(f"/api/files/{file_id}/permanent", headers=headers)
