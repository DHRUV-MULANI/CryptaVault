# Phase P15 — AI Security Assistant (Week 15)

## Objective
Build the rule-based heuristic recommender (deterministic, offline), an optional pluggable LLM provider (OpenAI/Anthropic) with strict data minimization, the AI chat endpoint, and a static knowledge base fallback for offline operation.

## Prerequisites
- P6 (Compression Gate) — file type detection + policy for recommendations.
- P9 (API Gate) — endpoints for AI chat.

## Tasks

### Task 15.1 — Rule-Based Heuristic Recommender
**Files**: `packages/core/cryptavault/ai/rules.py`
**Action**:
- Rules:
  - File type ∈ {JPEG, MP4, ZIP} → skip compression.
  - File size > 10GB → AES-256-GCM + chunked + skip compress.
  - File type == TEXT and < 100MB → zstd compress.
  - Profile == MAXIMUM and filename pattern (key, wallet, seed) → multi-layer + FS ratchet + full audit.
  - VM image (>1GB, compressed) → skip compress, AES-256-GCM parallel, large chunks.
- Output `Recommendation {encryption_algo, compression_mode, chunk_size, parallel_workers, rationale_text}`.
**Verify**: 15 known scenarios produce expected recommendations; rationale explains each choice.
**Done**: Recommender correct; rationale human-readable.

### Task 15.2 — Optional LLM Provider Interface
**Files**: `packages/core/cryptavault/ai/llm.py`, `docs/ai_data_minimization.md`
**Action**:
- `AiProvider` ABC: `recommend(metadata)`, `explain(concept)`, `analyze_upload(metadata)`.
- `OpenAiProvider`, `AnthropicProvider` via their SDKs.
- **Critical data minimization**: only send `file_type`, `size`, `profile`, requested concept; NEVER plaintext, keys, contents, names. Enforce by code (allowlist), not just policy.
- Prompt template: "You are a crypto advisory assistant. Explain concept: X. Do not request sensitive data."
**Verify**: Mock LLM returns canned response; data-minimization unit test (no file-content in request body).
**Done**: LLM pluggable; data minimization enforced by code; documented.

### Task 15.3 — AI Assistant Chat Endpoint
**Files**: `packages/api/cryptavault_api/routes/ai.py`
**Action**:
- `/api/ai/chat` accepts question → routes rule-based or LLM.
- Concept explanation → LLM (if configured) or static KB fallback.
- "Analyze this upload" → recommendation from rule-based; user confirms to apply.
- "Apply recommendation" endpoint updates profile/config.
**Verify**: "explain AES-GCM" → LLM/static response; "what compression for 20GB VM image?" → rule-based.
**Done**: Chat endpoint works; recommendation→apply loop clean.

### Task 15.4 — Static Knowledge Base Fallback
**Files**: `packages/core/cryptavault/ai/knowledge_base.py`
**Action**:
- Curated entries: AES-GCM, ChaCha20-Poly1305, RSA vs ECC, Kyber, Dilithium, Argon2id, forward secrecy, zero-knowledge storage, Merkle trees, AEAD, KDF, hybrid encryption.
- Each: concept name, short explanation, when-to-use, security level, performance note.
**Verify**: Known concept → entry found; unknown → "configure LLM for richer explanations".
**Done**: Fallback useful offline; >20 concepts; cited academically.

## Phase Gate Criteria (AI Gate)
- [ ] Rule-based recommender correct across 15 scenarios
- [ ] LLM provider pluggable (OpenAI or Anthropic)
- [ ] Data minimization enforced by code (allowlist); unit test no-leak passes
- [ ] Chat endpoint routes correctly
- [ ] Static KB fallback works offline (≥20 concepts)

## Risks
- R8 (LLM data leak) — enforced by code (allowlist) + unit test. Policy alone is insufficient.