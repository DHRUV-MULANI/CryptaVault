"""Tests for the public crypto catalog and adaptive profile endpoints."""

from cryptavault_api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_catalog_lists_all_families() -> None:
    response = client.get("/api/crypto/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert payload["catalog_total"] >= 60
    assert {"symmetric", "hash", "kdf", "kem", "signature"}.issubset(set(payload["families"]))
    first = payload["algorithms"][0]
    assert first["wire_id_hex"].startswith("0x")
    assert isinstance(first["runtime_available"], bool)


def test_catalog_filters_and_lookup() -> None:
    response = client.get("/api/crypto/catalog", params={"family": "symmetric"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] > 0
    assert all(item["family"] == "symmetric" for item in payload["algorithms"])

    detail = client.get("/api/crypto/catalog/aes-256-gcm")
    assert detail.status_code == 200
    assert detail.json()["algorithm_id"] == "aes-256-gcm"
    assert detail.json()["family"] == "symmetric"

    missing = client.get("/api/crypto/catalog/not-a-real-cipher")
    assert missing.status_code == 404


def test_catalog_rejects_unknown_status_filter() -> None:
    response = client.get("/api/crypto/catalog", params={"status": "bogus"})
    assert response.status_code == 422


def test_profiles_endpoint_has_six_bands() -> None:
    response = client.get("/api/crypto/profiles")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 6
    levels = [profile["level"] for profile in payload["profiles"]]
    assert levels == [
        "PERFORMANCE",
        "STANDARD",
        "BALANCED",
        "STRONG",
        "PQ_STRONG",
        "MAXIMUM",
    ]
    pq = next(profile for profile in payload["profiles"] if profile["level"] == "PQ_STRONG")
    assert pq["post_quantum_protected"] is True
    assert pq["slider_band"] == [80.0, 90.0]
