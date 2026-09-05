# CryptaVault — Agent Guidelines & Tooling Reference

## Repository Overview
CryptaVault is an AI-Assisted Adaptive Hybrid Cryptographic Storage Framework enforcing client-side zero-knowledge encryption across multi-backend cloud and on-premise targets.

## Workspace Ecosystems

### Python Ecosystem (`packages/core`, `packages/api`, `packages/cli`)
- **Python Version**: 3.11 (enforced via `.venv` managed with `uv`).
- **Package Management**: `uv` (`uv pip install -e <package>`).
- **Linting & Formatting**:
  - `ruff check .`
  - `black --check .` (or `black .` to format)
- **Type Checking**:
  - `mypy packages/core/cryptavault packages/api/cryptavault_api packages/cli/cryptavault_cli`
- **Testing**:
  - `pytest` (run with `--hypothesis-seed=0` for deterministic property testing)

### TypeScript / Web Ecosystem (`packages/web`, `packages/admin`, `packages/wasm`)
- **Node Version**: Node 20+
- **Package Management**: `pnpm` (via `npx -y pnpm`)
- **Orchestration**: `turbo` (`npx -y turbo run build`, `npx -y turbo run typecheck`)
- **Type Checking**:
  - `npx -y pnpm run typecheck`
- **Testing**:
  - `npx -y pnpm run test`
- **Build**:
  - `npx -y pnpm run build`

## Zero-Knowledge Boundary Invariants
1. Plaintext data and user encryption keys **NEVER** leave the client boundary (WASM browser client or CLI).
2. The FastAPI backend and Supabase database **ONLY** store ciphertext, encrypted manifests, and zero-knowledge auth metadata.
3. Master keys are derived client-side via Argon2id.
