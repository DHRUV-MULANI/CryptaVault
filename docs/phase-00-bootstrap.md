# Phase P0 — Project Bootstrap (Week 1)

## Objective
Scaffold the monorepo, verify all hard-blocker dependencies (`liboqs`, `Supabase`, OAuth), establish CI, and lay the plugin architecture foundation.

## Prerequisites
None (first phase).

## Tasks

### Task 0.1 — Monorepo & Packaging Scaffold
**Files**: `pyproject.toml`, `package.json`, `turbo.json`, `README.md`, `LICENSE`, `AGENTS.md`, `.gitignore`, `packages/{core,api,web,admin,wasm,cli}/`
**Action**:
- Initialize git repo at `/home/boss/tools/CryptaVault`.
- Create `pyproject.toml` (Python workspace: `packages/core`, `packages/api`, `packages/cli`) with PEP 621 metadata, version `0.1.0`, dev deps (pytest, hypothesis, ruff, black, mypy, httpx).
- Create `package.json` (TS workspace: `packages/web`, `packages/admin`) with pnpm workspaces, `turbo.json`.
- Create directory tree per ARCHITECTURE.md Module Map; add `.gitignore` (Python, `.env`, key files).
**Verify**: `pip install -e packages/core packages/api packages/cli` succeeds; `pnpm install` succeeds; `python -c "import cryptavault"` works.
**Done**: Repo scaffolded; lint (`ruff`, `black --check`, `mypy`) clean; `pnpm typecheck` clean; `import cryptavault` works.

### Task 0.2 — liboqs Build Verification (HARD BLOCKER)
**Files**: `docs/setup.md`, `Dockerfile.dev`, `packages/core/tests/kat/pq_baseline.json`
**Action**:
- Clone `open-quantum-safe/liboqs`; build with CMake (`-DOQS_USE_OPENSSL=ON`).
- Install `oqs-python` bindings; verify Kyber768 + Dilithium3 KATs.
- Verify `oqs-wasm` builds via Emscripten (or use prebuilt).
- If native build fails, create `Dockerfile.dev`; document fallback.
- Record liboqs commit hash + versions in `docs/setup.md`; capture KAT outputs as `tests/kat/pq_baseline.json`.
**Verify**: `python -c "import oqs; print(oqs.get_enabled_kem_mechanisms())"` lists Kyber; Dilithium sign/verify round-trips; JS smoke test loads `oqs-wasm`.
**Done**: liboqs works on target platform; KAT baseline file committed; setup documentation complete.

### Task 0.3 — Core Library Dependencies & Smoke Tests
**Files**: `packages/core/pyproject.toml`, `packages/api/pyproject.toml`, `packages/web/package.json`, `packages/admin/package.json`, `packages/core/tests/test_smoke_imports.py`
**Action**:
- Pin runtime deps per package (see PLAN.md Task 0.3 for full list).
- Write smoke test importing each Python library; build web/admin bare scaffolds.
**Verify**: `pytest packages/core/tests/test_smoke_imports.py` green; `pnpm build` for web/admin succeeds.
**Done**: All dependencies importable; failures surface immediately.

### Task 0.4 — CI Pipeline (GitHub Actions)
**Files**: `.github/workflows/ci.yml`
**Action**:
- Workflow: lint (ruff + eslint) → format check (black + prettier) → typecheck (mypy + tsc) → pytest (with `--hypothesis-seed=0`) → `pnpm test` → `pnpm build`.
- Matrix: Python 3.11/3.12 × Node 20; cache pip + pnpm + liboqs build.
**Verify**: CI green on placeholder tests; a deliberately broken commit is rejected.
**Done**: Automated quality gates on every push.

### Task 0.5 — OAuth + Cloud Provider Registrations (PARALLEL)
**Files**: `docs/oauth_setup.md`
**Action**:
- Register Google (Drive API + Identity), Microsoft (Entra ID — OneDrive + OIDC), GitHub (OAuth App), Apple (optional), Dropbox (storage).
- Configure Supabase Auth providers for Google/GitHub/MS/Apple in Supabase dashboard.
- Store client_id/secret in Supabase project settings (not local files).
- Document redirect URIs.
**Verify**: All OAuth client IDs issued; test OAuth dance completes for each provider.
**Done**: Cloud + auth provider credentials ready; documented in `docs/oauth_setup.md`.

### Task 0.6 — Supabase Project & Schema Foundation
**Files**: `supabase/migrations/0001_init.sql`, `supabase/migrations/0002_rls.sql`
**Action**:
- Create Supabase project; store URL + anon key + service role key in OS keyring / env.
- Write `0001_init.sql`: tables `profiles`, `key_manifests`, `share_tokens`, `audit_log`, `benchmark_results`, `feature_flags`, `sessions` (see ARCHITECTURE.md for full schema).
- Write `0002_rls.sql`: RLS policies enforcing user-isolation; admins read all; auditors read audit_log only.
- Run migrations via `supabase db push`.
**Verify**: Tables created; RLS policies enforce user isolation; test user A cannot read user B's `key_manifests`.
**Done**: Database schema + RLS live on Supabase; users isolated.

### Task 0.7 — Plugin Architecture Skeleton
**Files**: `packages/core/cryptavault/plugins/registry.py`, `packages/core/tests/test_registry.py`, `docs/plugin_development.md`
**Action**:
- Define typed registries: `StorageConnector`, `CompressionAlgorithm`, `HashAlgorithm`, `EncryptionAlgorithm`, `SignatureAlgorithm`, `KemAlgorithm`, `KdfAlgorithm`, `AiProvider`.
- Define `@register_*` decorators + ABCs with abstract methods only.
- Register entry-point group `cryptavault.plugins` in `pyproject.toml`.
- Test: register dummy plugin, retrieve by name, ensure duplicates raise.
**Verify**: `pytest packages/core/tests/test_registry.py` green; entry-point discovery test passes.
**Done**: Registry round-trips dummy plugin; documented in `docs/plugin_development.md`.

## Phase Gate Criteria (Setup Gate)
- [ ] Repo scaffolded; lint/type clean
- [ ] liboqs works; Kyber + Dilithium KAT baseline committed
- [ ] All smoke imports succeed
- [ ] CI green
- [ ] OAuth credentials issued for all required providers
- [ ] Supabase project provisioned with tables + RLS
- [ ] Plugin registry tested

## Risks Specific to This Phase
- R1 (liboqs build failure) — highest priority; resolve before any crypto code
- R3 (OAuth approval delays) — start early; test-mode apps
- R10 (Supabase free tier) — use local Supabase for dev

## Open Questions
- None — all decisions locked from planning conversation.