# Phase P12 — Web Client (WASM Crypto) (Week 14)

## Objective
Compile the Python crypto core to WebAssembly, scaffold the React web client, build browser crypto wrappers and in-browser key vault, implement upload/download/share UI, and live performance widgets. Enforce the zero-knowledge boundary: keys never leave the browser.

## Prerequisites
- P7 (Pipeline Gate) — pipeline logic to mirror in browser.
- P11 (Sharing Gate) — share package format to consume.
- P9 (API Gate) — auth + share endpoints.

## Tasks

### Task 12.1 — WASM Crypto Build Pipeline
**Files**: `packages/wasm/build.sh`, `packages/wasm/cryptavault.wasm`, JS smoke test
**Action**:
- Use Pyodide or PyScript to package `packages/core` → `packages/wasm/cryptavault.wasm`.
- Verify `oqs-wasm` loads + runs Kyber/Dilithium in browser.
- Expose async JS API: `import { encrypt, decrypt, sign, verify, kem_encapsulate } from 'cryptavault-wasm'`.
**Verify**: Node smoke test imports WASM, runs AES-256-GCM round-trip, Kyber KEM round-trip.
**Done**: WASM loads in browser; PQ primitives work (or graceful fallback); JS API documented.

### Task 12.2 — Web Client Scaffold (React + Vite + Tailwind)
**Files**: `packages/web/src/{App.tsx, pages/, lib/, components/}`
**Action**:
- Vite + React + TS + Tailwind; `@supabase/supabase-js` client.
- `wouter` routing: `/login`, `/dashboard`, `/files`, `/shares`, `/benchmarks`, `/profile`.
- Auth gate: redirect `/login` if no session.
**Verify**: Render login page; auth flow with email/pw; dashboard renders placeholder.
**Done**: App boots; auth flow works; routing correct.

### Task 12.3 — Browser Crypto Wrappers + Key Vault
**Files**: `packages/web/src/crypto/`, `packages/web/src/crypto/keyvault.ts`
**Action**:
- `src/crypto/index.ts`: `encryptFile`, `decryptFile`, `signFile`, `verifyFile`, `kemEncapsulate` (async wrappers around WASM).
- Key vault: master key derived in WASM from password (Argon2id); decrypted in memory only; encrypted keystore persisted in `localStorage`/`IndexedDB`.
- Streaming: chunk file via `Blob.slice` + `ReadableStream`; encrypt chunks with WASM; assemble.
**Verify**: Encrypt 100MB file in browser; memory bounded; decrypt round-trips.
**Done**: Browser crypto works; memory < 200MB on 1GB; keys never leave browser.

### Task 12.4 — Upload/Download/Share UI
**Files**: `packages/web/src/components/`, `packages/web/src/pages/files.tsx`
**Action**:
- Upload: drag-drop / file picker → WASM encrypt → chunked upload (via signed URL). Progress bar + cancel.
- Download: list files from manifest → WASM decrypt → save.
- Share: dialog with options (QR, time limit, password, recipient pubkey).
**Verify**: Manual E2E: upload 50MB → appears in list → download → decrypts → bytes match original.
**Done**: Full round-trip in browser; progress + cancel; share dialog functional.

### Task 12.5 — Browser Performance Dashboard Widgets
**Files**: `packages/web/src/components/metrics/`
**Action**:
- `PerformanceObserver` + `performance.memory` (Chrome) for metrics; stream via SSE or poll `/api/metrics` (server reports storage-side speed).
- Charts via `recharts` (small bundle) or pure SVG.
- Profile slider with algorithm matrix display.
**Verify**: Metrics render during 100MB upload; slider updates; values sane.
**Done**: Live metrics visible; slider works; charts readable.

## Phase Gate Criteria (Web Client Gate)
- [ ] WASM crypto loads in browser; AES + Kyber round-trip
- [ ] React app boots; auth flow works
- [ ] Browser encryption of 100MB with < 200MB memory; keys stay in browser
- [ ] Upload → download → decrypt round-trip matches original bytes
- [ ] Live metrics + profile slider render

## Risks
- R2 (oqs-wasm unavailable) → web falls back to classical-only; PQ available via CLI; document clearly.
- R11 (WASM perf) → use Web Workers for parallelism; document browser vs native perf delta.
- R13 (browser keystore loss) → mnemonic backup + recovery flow.