"""AI security advisory and interactive cryptographic assistant routes."""

from __future__ import annotations

from typing import Any

from cryptavault.ai.knowledge_base import list_concepts
from cryptavault.ai.llm import OfflineAiProvider, SanitizedMetadata
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ai", tags=["ai"])
_ai_provider = OfflineAiProvider()


class AdvisoryRequest(BaseModel):
    filename: str = Field(..., description="File name (only extension is used for minimization)")
    size_bytes: int = Field(..., description="File size in bytes")
    profile_level: str = Field(default="BALANCED", description="Desired security tier")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or concept query")


@router.post("/recommend")
def get_recommendation(payload: AdvisoryRequest) -> dict[str, Any]:
    """Provide intelligent cryptographic and pipeline recommendations with strict data minimization."""
    sanitized = SanitizedMetadata.sanitize(
        filename=payload.filename,
        size_bytes=payload.size_bytes,
        profile_level=payload.profile_level,
    )
    rec = _ai_provider.advise_upload(sanitized)
    return rec.to_dict()


@router.post("/chat")
def chat_with_assistant(payload: ChatRequest) -> dict[str, str]:
    """Interactive educational cryptographic assistant."""
    query = payload.message.strip()

    # Check for direct concept lookup
    explanation = _ai_provider.explain_concept(query)
    return {
        "reply": explanation,
        "mode": "offline-knowledge-base",
    }


@router.get("/concepts")
def get_concepts() -> list[str]:
    """List all available concepts in the cryptographic knowledge base."""
    return list_concepts()
