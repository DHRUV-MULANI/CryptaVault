# Phase P14 — Dashboard + Benchmark Lab (Week 15)

## Objective
Build the crypto benchmark lab comparative suite, web UI for benchmark charts, live performance metrics via SSE, user-facing performance dashboard page (HTMX/Tailwind), and estimated brute-force resistance indicator.

## Prerequisites
- P12 (Web Client Gate) — web app shell ready for dashboard widgets.
- P13 (Admin Gate) — admin SPA ready for benchmark charts.
- P7 (Pipeline Gate) — pipeline emits metrics.

## Tasks

### Task 14.1 — Benchmark Lab Comparative Suite
**Files**: `packages/core/cryptavault/benchmark/suite.py`, `benchmarks/`
**Action**:
- Benchmark all algorithms: AES, ChaCha20, RSA, ECC, Kyber, Dilithium, hybrid.
- Metrics per algo: time, CPU, memory, key size, sig size. Parameterize by payload (1KB, 1MB, 100MB, 1GB) + iterations.
- Export CSV + JSON to `benchmarks/` directory.
**Verify**: Suite completes in ≤10 min; results sane (AES faster than RSA; Kyber faster than RSA-4096).
**Done**: Full suite runs; CSV/JSON exported; academically useful comparison.

### Task 14.2 — Benchmark Lab Web UI
**Files**: `packages/admin/src/features/benchmarks/`
**Action**:
- Bar charts: encryption speed per algo (MB/s), key size (bytes), sig gen/verify time (ms).
- Tables: usability rating (AES vs ChaCha on mobile vs server; RSA vs ECC vs Dilithium).
- Use `recharts`; load JSON from `/api/benchmark`.
**Verify**: Manual verification; charts render; data matches CSV.
**Done**: Charts readable; comparison clear; suitable for report screenshots.

### Task 14.3 — Live Performance Metrics (SSE)
**Files**: `packages/api/cryptavault_api/routes/metrics.py`, `packages/core/cryptavault/pipeline/` (event emission)
**Action**:
- `MetricsCollector`: subscribes to pipeline orchestrator events; emits JSON metrics every 1s.
- SSE endpoint `/api/metrics/stream` pushes events.
- Frontend HTMX `hx-sse` OR React `EventSource` updates DOM live.
**Verify**: Metrics flow; SSE delivers; CPU/RAM via `psutil` (server) or `performance.memory` (browser).
**Done**: Dashboard updates live during 1GB encrypt+upload; ≤2s latency.

### Task 14.4 — Performance Dashboard Page (User-Facing)
**Files**: `packages/api/cryptavault_api/templates/`, `packages/web/src/pages/dashboard.tsx`
**Action**:
- HTMX/Tailwind page (or React, depending on user-client choice) showing live metrics + profile selector.
- Cards: current profile + algorithm matrix, live speed graph, CPU/RAM gauges, compression ratio, security level badge.
- Profile slider control calls `/api/profile`.
- Job queue table with status badges.
**Verify**: Manual visual verification; slider persists; live updates during operation.
**Done**: Dashboard renders; slider works; live metrics visible.

### Task 14.5 — Estimated Brute-Force Resistance Indicator
**Files**: `packages/web/src/components/SecurityBadge.tsx`, `packages/admin/src/features/security/`, `research/notes/security_levels.md`
**Action**:
- Each algo maps to bits of security: AES-128 → 128, AES-256 → 256, RSA-4096 → ~140, Kyber768 → 192, Dilithium3 → 192.
- Display "Classical: N bits · Post-Quantum: M bits"; color badge (green ≥192, yellow 128, red <128).
- Year-of-security estimate (NIST levels 1/3/5 → 2030+/2040+/beyond).
**Verify**: Badge updates with profile; values correct per NIST guidelines.
**Done**: Badge visible; values honest; documented.

## Phase Gate Criteria (Dashboard + Bench Gate)
- [ ] Benchmark suite runs all algos, exports CSV/JSON
- [ ] Benchmark charts render in admin
- [ ] Live metrics stream via SSE; ≤2s latency
- [ ] User dashboard renders live metrics + slider
- [ ] Security badge shows classical + PQ bits

## Open Questions
- HTMX vs React for user dashboard: plan supports both; primary implementation in React (web client already React) for consistency. HTMX used for server-rendered fallback views.