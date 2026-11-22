"""FastAPI entrypoint and router registration for CryptaVault API."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from cryptavault_api.db import database_healthy, init_db
from cryptavault_api.middleware.rate_limit import RateLimitMiddleware
from cryptavault_api.routes.admin import router as admin_router
from cryptavault_api.routes.ai import router as ai_router
from cryptavault_api.routes.auth import router as auth_router
from cryptavault_api.routes.crypto import router as crypto_router
from cryptavault_api.routes.dashboard import router as dashboard_router
from cryptavault_api.routes.files import router as files_router
from cryptavault_api.routes.metrics import router as metrics_router
from cryptavault_api.routes.shares import router as shares_router
from cryptavault_api.routes.storage import router as storage_router
from cryptavault_api.routes.workspaces import router as workspaces_router
from cryptavault_api.settings import settings

logger = logging.getLogger("cryptavault_api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the schema and seed the local demo on startup."""
    try:
        init_db()
        logger.info("Database schema ready and demo data seeded.")
    except Exception:
        logger.exception("Database initialization failed; API starting in degraded mode.")
    yield


app = FastAPI(
    title="CryptaVault API",
    version="2.0.0",
    description=(
        "Zero-knowledge storage API: local accounts, workspaces, encrypted file "
        "versioning, capability shares, multi-target storage, dashboard, and admin."
    ),
    lifespan=lifespan,
)

_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
    "https://dhruv-mulani.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*_DEFAULT_ORIGINS, *settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-CV-Version",
        "X-CV-Storage-Target",
        "X-CV-Ciphertext-Size",
        "X-CV-Remaining-Uses",
    ],
)

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_rpm,
    auth_requests_per_minute=settings.rate_limit_auth_rpm,
)

app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(files_router)
app.include_router(shares_router)
app.include_router(storage_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(metrics_router)
app.include_router(ai_router)
app.include_router(crypto_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "zero_knowledge_boundary": "ENFORCED",
        "audit_logging": "DISABLED",
    }


@app.get("/ready")
def readiness_check() -> dict[str, Any]:
    """Readiness probe checking the metadata database."""
    healthy = database_healthy()
    return {
        "status": "ready" if healthy else "degraded",
        "database": "connected" if healthy else "unavailable",
        "environment": settings.environment,
        "default_storage": settings.default_storage,
        "api_origin": os.getenv("CRYPTAVAULT_API_ORIGIN", "http://localhost:8000"),
    }
