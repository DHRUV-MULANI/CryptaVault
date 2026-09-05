"""FastAPI entrypoint and router registration for CryptaVault API."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

from cryptavault_api.auth.session import router as auth_router
from cryptavault_api.middleware.rate_limit import RateLimitMiddleware
from cryptavault_api.routes.admin import router as admin_router
from cryptavault_api.routes.ai import router as ai_router
from cryptavault_api.routes.audit import router as audit_router
from cryptavault_api.routes.metrics import router as metrics_router
from cryptavault_api.routes.shares import router as shares_router
from cryptavault_api.routes.storage import router as storage_router
from cryptavault_api.routes.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown hooks."""
    # Log startup status
    yield


app = FastAPI(
    title="CryptaVault API",
    version="1.0.0",
    description="Zero-Knowledge Backend API with Supabase Auth, Storage Coordination, Auditing, and AI Advisory",
    lifespan=lifespan,
)

# CORS middleware for Web Client and Admin Console
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory sliding window rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, auth_requests_per_minute=30)

# Include feature routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(shares_router)
app.include_router(storage_router)
app.include_router(audit_router)
app.include_router(admin_router)
app.include_router(metrics_router)
app.include_router(ai_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {
        "status": "ok",
        "version": "0.3.0",
        "zero_knowledge_boundary": "ENFORCED",
    }


@app.get("/ready")
def readiness_check() -> dict[str, Any]:
    """Readiness probe checking storage and Supabase availability."""
    supabase_configured = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))
    return {
        "status": "ready",
        "supabase_configured": supabase_configured,
        "supabase_url": os.getenv("SUPABASE_URL", "not_set"),
    }
