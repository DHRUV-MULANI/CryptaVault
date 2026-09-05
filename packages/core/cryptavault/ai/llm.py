"""Pluggable AI provider interface with code-enforced Data Minimization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from cryptavault.ai.knowledge_base import lookup_concept
from cryptavault.ai.rules import Recommendation, RuleBasedRecommender


@dataclass
class SanitizedMetadata:
    """Strictly filtered metadata envelope passed to AI providers.

    Data Minimization Invariant: File contents, raw encryption keys, private paths,
    and user personal data are NEVER included in this data structure.
    """

    file_category: str
    size_bytes: int
    profile_level: str
    is_media: bool

    @classmethod
    def sanitize(cls, filename: str, size_bytes: int, profile_level: str) -> SanitizedMetadata:
        # Strip path and keep only non-identifying extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        is_media = ext in ("jpg", "jpeg", "png", "mp4", "mov", "mp3", "zip", "tar", "gz")
        return cls(
            file_category=ext,
            size_bytes=size_bytes,
            profile_level=profile_level,
            is_media=is_media,
        )


class AiProvider(ABC):
    """Abstract interface for AI security advisory engines."""

    @abstractmethod
    def advise_upload(self, sanitized: SanitizedMetadata) -> Recommendation:
        """Provide tailored cryptographic recommendation for an upload."""
        ...

    @abstractmethod
    def explain_concept(self, concept: str) -> str:
        """Provide educational explanation of a cryptographic concept."""
        ...


class OfflineAiProvider(AiProvider):
    """Zero-network deterministic AI advisor using rules and curated knowledge base."""

    def advise_upload(self, sanitized: SanitizedMetadata) -> Recommendation:
        fake_filename = f"file.{sanitized.file_category}"
        return RuleBasedRecommender.advise(
            filename=fake_filename,
            size_bytes=sanitized.size_bytes,
            profile_level=sanitized.profile_level,
        )

    def explain_concept(self, concept: str) -> str:
        info = lookup_concept(concept)
        if info:
            return (
                f"**{info['name']}** ({info['category']})\n\n"
                f"{info['description']}\n\n"
                f"- **Security Level**: {info['security_level']}\n"
                f"- **When to Use**: {info['when_to_use']}\n"
                f"- **Standard**: {info.get('nist_standard', 'NIST Standard')}"
            )
        return (
            f"Concept '{concept}' is not in the offline local knowledge base. "
            "CryptaVault supports AES-256-GCM, ChaCha20-Poly1305, Argon2id, ML-KEM-768 (Kyber), "
            "ML-DSA-65 (Dilithium), Merkle Trees, and Post-Quantum Hybrid Cryptography."
        )
