# Phase P9 — API + Auth Backend with Supabase (Week 11)

## Objective
Build the FastAPI backend integrating Supabase Auth (multi-provider: email/pw + Google + GitHub + MS + Apple + magic link + passkeys), user routes with RLS verification, share token routes, audit log routes, and rate limiting.

## Prerequisites
- P0 (Setup Gate) — Supabase project + OAuth providers configured.
- P4 (KMS Gate) — key manifest format known for sync endpoint.
- P3 (Integrity Gate) — audit log hash-chain schema.

## Tasks

### Task 9.1 — FastAPI App Scaffold + Supabase Client
**Files**: `packages/api/cryptavault_api/main.py`, `deps.py`, `middleware/`
**Action**:
- FastAPI app, CORS, request-id middleware, error handlers.
- `get_supabase()` (async client), `get_current_user()` (verifies JWT via `gotrue`), `get_admin_user()` (checks `role=admin`).
- Endpoints: `/health`, `/ready` (DB ping), `/docs`.
**Verify**: `httpx.AsyncClient` smoke tests; `/health` 200; unauth `/me` → 401.
**Done**: App boots; Supabase client connects; health checks pass.

### Task 9.2 — Supabase Auth Integration (Multi-Provider)
**Files**: `packages/api/cryptavault_api/auth/`
**Action**:
- Configure Supabase Auth providers in dashboard: Email, Google, GitHub, Microsoft, Apple, Magic Link, WebAuthn (passkeys).
- `/api/auth/session`: exchange Supabase access token → app session cookie (HMAC-signed, 15-min access / 7-day refresh).
- `/api/auth/me` → user profile + role. `/api/auth/logout` → invalidate session.
**Verify**: All providers work end-to-end in browser; session cookies set; logout clears; expired token → 401; role extraction correct.
**Done**: All 7 auth methods functional; session management works.

### Task 9.3 — User Routes + RLS Verification
**Files**: `packages/api/cryptavault_api/routes/users.py`
**Action**:
- `/api/users/me` GET/PATCH (display_name, quota).
- `/api/users/me/manifest` GET (encrypted manifest ref) / PUT (upload encrypted body to storage, update hash in DB).
- Verify RLS: user A cannot GET user B's manifest.
**Verify**: Round-trip manifest upload; cross-user isolation enforced (test with two users).
**Done**: RLS enforced; manifest syncs; cross-user reads blocked.

### Task 9.4 — Share Token Routes
**Files**: `packages/api/cryptavault_api/routes/shares.py`
**Action**:
- `/api/shares` POST (create token, store wrapped key, expiry, max_uses) / GET (list own).
- `/api/shares/{id}` GET (public, verify sig + expiry) / DELETE (revoke).
- `/api/shares/{id}/consume` POST (increment uses; reject if over max or expired).
**Verify**: Create→consume round-trip; expired → rejected; over-uses → rejected; revoke → 404.
**Done**: Token lifecycle enforced; expiry + use-limit correct.

### Task 9.5 — Audit Log Routes
**Files**: `packages/api/cryptavault_api/routes/audit.py`
**Action**:
- `/api/audit` POST (append entry with `prev_hash`, `entry_hash`, `signature`) / GET (list own, paginated).
- `/api/audit/verify` POST (client sends chain; server stores but verification is client-side to avoid server forging).
- Admin: `/api/admin/audit` GET (all users, filtered).
**Verify**: Append→list round-trip; tamper detection via client verify; admin sees all.
**Done**: Audit chain works; tamper detection client-side; admin access correct.

### Task 9.6 — Rate Limiting + Request Validation
**Files**: `packages/api/cryptavault_api/middleware/rate_limit.py`
**Action**:
- Rate limit (per-user, per-IP) via Redis or in-memory LRU; 100 req/min default; stricter on auth (20/min).
- Pydantic schemas for all request/response bodies; reject unknown fields.
- Request-id propagation; structured JSON logs.
**Verify**: Rate limit kicks in at 101st req; invalid schema → 422; log entries present.
**Done**: Rate limit enforced; validation strict; logs structured.

## Phase Gate Criteria (API Gate)
- [ ] All 7 auth methods work end-to-end in browser
- [ ] User routes respect RLS (cross-user isolation)
- [ ] Share token lifecycle (create/consume/revoke/expiry) enforced
- [ ] Audit log hash chain appends + verifies + admin reads all
- [ ] Rate limiting + Pydantic validation enforced

## Risks
- R10 (Supabase free tier) — monitor; use local Supabase for dev.
- R14 (admin impersonation) — addressed in P13, not here.