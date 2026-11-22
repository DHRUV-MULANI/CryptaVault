# Phase P13 — Admin Console (React SPA) (Week 14)

## Objective
Build the admin console as a React SPA using shadcn/ui, hosted on a separate subdomain (`admin.cryptavault.app`), with RBAC-protected routing, user management (including impersonation), audit log viewer, session revocation, storage provider admin, feature flags, system health, and analytics reports.

## Prerequisites
- P9 (API Gate) — admin endpoints available.
- P0 (Setup Gate) — Supabase project + admin role concept.

## Tasks

### Task 13.1 — Admin Scaffold (React + shadcn/ui + Vite)
**Files**: `packages/admin/src/{App.tsx, features/, components/, lib/}`
**Action**:
- Vite + React + TS + Tailwind + `shadcn/ui` (Button, DataTable, Dialog, Tabs, Form, Card).
- Auth: separate Supabase Auth call with admin role check; admin cookie scope `admin.cryptavault.app`.
- Routing: `/admin/dashboard`, `/admin/users`, `/admin/sessions`, `/admin/providers`, `/admin/audit`, `/admin/flags`, `/admin/health`, `/admin/reports`.
**Verify**: Login as admin → dashboard renders; login as user → 403.
**Done**: Admin isolated; RBAC enforced; scaffold renders.

### Task 13.2 — User Management Feature
**Files**: `packages/admin/src/features/users/`
**Action**:
- `DataTable` with search, sort, filter (role, suspended, created_at).
- Row actions: Suspend, Delete, Edit Quota, Impersonate (short-lived admin-signed token; audit log entry).
- Detail drawer: profile, storage usage, active sessions, recent audit entries.
**Verify**: Suspend → user cannot login; edit quota persists; impersonation → audit entry.
**Done**: CRUD works; impersonation audited; RLS-enforced.

### Task 13.3 — Audit Log + Sessions + Providers
**Files**: `packages/admin/src/features/{audit,sessions,providers}/`
**Action**:
- Audit: `DataTable` with filters (user, operation, date range, outcome); export CSV; show hash chain verify status.
- Sessions: list active sessions per user; revoke (invalidate JWT cookie server-side).
- Providers: list configured storage providers + add/remove org-wide credentials.
**Verify**: Filter audit by user → only their entries; revoke session → user re-logged; add provider credential persists.
**Done**: Audit filtered/exported; sessions revocable; providers editable.

### Task 13.4 — Feature Flags + System Health + Reports
**Files**: `packages/admin/src/features/{flags,health,reports}/`
**Action**:
- Flags: list (`enable_pq`, `enable_passkeys`, `enable_sharing`, `maintenance_mode`); toggle; impact immediate via API middleware.
- Health: Supabase DB status, API latency p50/p95, queue depth, storage provider reachability.
- Reports: signups/day (line), encrypt ops/day (bar), storage used (area), benchmark aggregates (table). Charts via `recharts`.
**Verify**: Toggle flag → API rejects PQ operations when off; health reflects DB down; reports render mock data.
**Done**: Flags actionable; health live; reports interactive.

### Task 13.5 — Admin API Serverside Enforcement
**Files**: `packages/api/cryptavault_api/routes/admin.py`, `packages/api/cryptavault_api/middleware/`
**Action**:
- `/api/admin/*` routes gated by `get_admin_user()` dependency.
- Impersonation: `/api/admin/impersonate/{user_id}` issues 10-min admin-signed token accepted as that user; `impersonated_by` audit field.
- Rate limit admin endpoints stricter (30 req/min).
**Verify**: User token → 403 on admin routes; admin token → 200; impersonated token works + audit shows `impersonated_by`.
**Done**: Admin-only enforced; impersonation audited; rate-limited.

## Phase Gate Criteria (Admin Gate)
- [ ] Admin SPA isolated on subdomain with RBAC
- [ ] User CRUD + suspend + impersonation (audited) works
- [ ] Audit log viewer with filters + CSV export
- [ ] Session revocation works
- [ ] Feature flags toggles actionable via API
- [ ] System health dashboard live
- [ ] Reports render charts
- [ ] Server enforces admin-only on all `/api/admin/*`

## Risks
- R14 (impersonation misuse) — short-lived tokens + mandatory audit + admin role + rate limit.