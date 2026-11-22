"""Runtime configuration for the CryptaVault API."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Environment-backed settings with safe local defaults."""

    def __init__(self) -> None:
        self.app_name = "CryptaVault API"
        self.environment = os.getenv("CRYPTAVAULT_ENV", "development")
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.jwt_secret = os.getenv("JWT_SECRET", "").strip()
        self.jwt_algorithm = "HS256"
        self.access_token_minutes = int(os.getenv("CRYPTAVAULT_TOKEN_MINUTES", "720"))
        self.storage_secret = os.getenv("STORAGE_SECRET", "").strip()
        self.local_storage_path = Path(
            os.getenv("CRYPTAVAULT_LOCAL_STORAGE", "./data/vault")
        ).resolve()
        self.default_storage = os.getenv("CRYPTAVAULT_STORAGE_DEFAULT", "s3").strip() or "s3"
        self.seed_demo = os.getenv("CRYPTAVAULT_SEED_DEMO", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.public_share_domain = os.getenv("PUBLIC_SHARE_DOMAIN", "http://localhost:3000").rstrip(
            "/"
        )
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv("CRYPTAVAULT_CORS_ORIGINS", "").split(",")
            if origin.strip()
        ]
        self.rate_limit_rpm = int(os.getenv("CRYPTAVAULT_RATE_LIMIT_RPM", "240"))
        self.rate_limit_auth_rpm = int(os.getenv("CRYPTAVAULT_RATE_LIMIT_AUTH_RPM", "60"))

        if not self.database_url:
            fallback = Path("./data/cryptavault.db").resolve()
            fallback.parent.mkdir(parents=True, exist_ok=True)
            self.database_url = f"sqlite:///{fallback}"
        if not self.jwt_secret:
            self.jwt_secret = "change-me-in-production-cryptavault-local-demo"
        if not self.storage_secret:
            self.storage_secret = self.jwt_secret


settings = Settings()
