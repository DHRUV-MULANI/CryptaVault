"""Shared pytest setup: isolate the dynamic API from the developer database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_TEST_ROOT = Path("/tmp/opencode/cryptavault-tests")
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
_TEST_DB = _TEST_ROOT / "cryptavault-test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["JWT_SECRET"] = "cryptavault-test-jwt-secret-32-bytes-minimum"
os.environ["STORAGE_SECRET"] = "cryptavault-test-storage-secret"
os.environ["CRYPTAVAULT_SEED_DEMO"] = "true"
os.environ["CRYPTAVAULT_STORAGE_DEFAULT"] = "local"
os.environ["CRYPTAVAULT_LOCAL_STORAGE"] = str(_TEST_ROOT / "vault")
os.environ["PUBLIC_SHARE_DOMAIN"] = "http://localhost:3000"
# Keep the suite deterministic: rate limiting is covered by its own policy, and
# hundreds of API calls share the TestClient's single client address.
os.environ["CRYPTAVAULT_RATE_LIMIT_RPM"] = "100000"
os.environ["CRYPTAVAULT_RATE_LIMIT_AUTH_RPM"] = "100000"

DEMO_EMAIL = "admin@cryptavault.dev"
DEMO_USER_EMAIL = "demo@cryptavault.dev"
DEMO_VIEWER_EMAIL = "viewer@cryptavault.dev"
DEMO_PASSWORD = "CryptaVaultDemo!2026"


@pytest.fixture(scope="session", autouse=True)
def _initialize_database():
    from cryptavault_api.db import init_db

    init_db()


@pytest.fixture(scope="session")
def api_client():
    from cryptavault_api.main import app
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def login(api_client):
    import base64
    import hashlib

    from cryptavault_api.seed import DEMO_PASSWORD as seed_password

    def _login(email: str = DEMO_EMAIL, password: str = seed_password) -> dict:
        pre = api_client.post("/api/auth/prelogin", json={"email": email})
        assert pre.status_code == 200, pre.text
        salt = base64.b64decode(pre.json()["auth_salt_b64"])
        iterations = pre.json()["kdf_iterations"]
        verifier = base64.b64encode(
            hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, dklen=32)
        ).decode()
        response = api_client.post(
            "/api/auth/login",
            json={"email": email, "auth_verifier": verifier},
        )
        assert response.status_code == 200, response.text
        return response.json()

    return _login


@pytest.fixture
def auth_headers(login):
    def _headers(email: str = DEMO_EMAIL) -> dict[str, str]:
        session = login(email)
        return {"Authorization": f"Bearer {session['access_token']}"}

    return _headers
