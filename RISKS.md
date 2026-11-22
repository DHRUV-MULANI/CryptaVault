# CryptaVault — Risks, Assumptions & Mitigations

## 1. Critical Risks

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|-----------|
| R1 | liboqs build fails on dev machine | Blocks all PQ work | Medium | Week 1 hard blocker test (Task 0.2); fallback to Docker dev container with prebuilt liboqs; alternative `oqs-python` wheels |
| R2 | `oqs-wasm` unavailable / outdated for browser | PQ not available in web client | Medium | WASM build tries `oqs-wasm`; if unavailable, web client uses classical-only with clear "PQ available via CLI" notice; CLI always has PQ |
| R3 | OAuth approval takes days/weeks | Delays P10 cloud connectors | Medium | Kick off in P0 (Task 0.5); use "test mode" apps for demo; develop against Mock connector first |
| R4 | Performance goals infeasible (parallel speedup, memory bounds) | Demo underwhelms | Medium | Benchmark early (P14 can start in P7); document actual vs target; optimize hot paths only if needed |
| R5 | Forward secrecy approximation not academically defensible | Report weak point | Low-Medium | Document as ratcheted per-file keys (honest); cite Signal Double Ratchet as analogous; do not claim "true FS" |
| R6 | Secure deletion impossible on SSDs/journaling FS | False claim risk | High | Document impossibility honestly; implement best-effort (overwrite + memory wipe); advise FDE for real guarantee |
| R7 | 1GB file E2E tests too slow for CI | CI slow; dev friction | Medium | Use 10MB for CI, 1GB for nightly/manual; parametrize file size in tests |
| R8 | LLM data-minimization leak | Security flaw | Low | Enforce by code (allowlist of fields sent); unit test no-content-leak; never include file names/keys/contents in LLM prompts |
| R9 | Scope creep on original 16 features | Incomplete core | High | Track deferred features explicitly in Out of Scope; reject additions unless they replace existing scope |
| R10 | Supabase free tier limits (DB size, auth MAU) | Hitting quota during dev | Low | Self-host Postgres fallback; monitor usage; use local Supabase for dev (supabase CLI) |
| R11 | WASM crypto performance too slow for 1GB in browser | Web demo fails | Medium | Optimize chunked encryption in WASM; use Web Workers for parallelism; document browser vs native perf delta in report |
| R12 | Pyodide/PyScript WASM packaging breaks with liboqs native deps | WASM build fails | Medium | Pure-Python fallback for non-PQ primitives in WASM; compile liboqs to WASM via Emscripten as last resort; document if PQ deferred to CLI |
| R13 | Browser `localStorage`/`IndexedDB` keystore loses keys | User locked out | Medium | Encourage mnemonic backup (Task 4.4); session unlock requires password re-entry; document recovery clearly |
| R14 | Admin impersonation misused | Audit/security incident | Low | Short-lived (10-min) tokens; mandatory `impersonated_by` audit field; admin role required; rate-limited |
| R15 | Rate limiting blocks legitimate large file uploads | Poor UX | Low | Per-user rate limits higher (1000 req/min) than per-IP; chunked uploads count as single operation |

## 2. Assumptions

These are the locked decisions from the planning conversation:

1. **Primary crypto language**: Python 3.11+ (crypto core).
2. **Database / BaaS**: **Supabase** (PostgreSQL + Auth + RLS).
3. **Zero-knowledge boundary**: Client-side crypto via **WebAssembly** (browser) or **native Python** (CLI). Keys never traverse network.
4. **Auth methods**: Email/password + Google + GitHub + Microsoft + Apple + Magic Link + Passkeys/WebAuthn (all via Supabase Auth).
5. **User dashboard**: HTMX + Tailwind (server-rendered via FastAPI).
6. **Admin console**: **React + shadcn/ui SPA**.
7. **Admin routing**: **Separate subdomain** (`admin.cryptavault.app`) for security isolation, separate cookie scope.
8. **Post-quantum**: Real liboqs (Kyber + Dilithium) for genuine PQ security.
9. **AI assistant**: Rule-based core + optional cloud LLM (OpenAI/Anthropic).
10. **AI data minimization**: LLM receives metadata ONLY (type, size, mode) — never plaintext/keys/contents.
11. **Forward secrecy**: Ratcheted per-file ephemeral keys wrapped by rotated master (honest about limitation).
12. **Benchmark Lab**: Kept for academic value.
13. **Evaluation focus**: Technical depth (crypto/math rigor, benchmarks, architecture) over UI polish.
14. **Secure deletion**: Best-effort (overwrite + memory wipe); honest about SSD/journaling FS limitations.

## 3. Deferred to Future Scope (Explicitly Out of Plan)

These items from the original spec are NOT in the 4-month plan:

- Tunnel-based transfer (WebRTC / QUIC / WireGuard concepts)
- HSM / TPM integration
- Multi-device encrypted synchronization
- Threshold cryptography for shared key recovery
- Secure team workspaces with role-based access (lite RBAC in admin only — not full team workspaces)
- Decentralized storage backends (IPFS, Filecoin)
- Encrypted searchable indexes
- Secure mobile clients (native)
- Enterprise policy management
- Compliance reporting (GDPR, HIPAA)
- SDKs for Python, JavaScript, Go, Java, C# (the Python core + TS web client ARE the first SDKs)
- Azure Blob, MinIO, WebDAV, SMB, NAS, custom REST storage providers (plugin interface supports them; impl deferred)
- SMS OTP via Twilio (passkeys/WebAuthn chosen instead — more secure, no cost)

## 4. Risk Monitoring & Escalation

Each phase gate (see ROADMAP.md) serves as a risk checkpoint. If a gate fails:

1. **Triage**: Identify root cause (build failure, performance shortfall, integration gap).
2. **Mitigate**: Apply specific mitigation from table above; if no documented mitigation, escalate to user.
3. **Document**: Update RISKS.md with new risk if discovered.
4. **Decide**: Continue with mitigation, defer feature, or descope (move to Out of Scope list).
5. **Recover**: Re-run gate criteria; do not proceed to dependent phases until gate passes.

### Hard Blockers (Stop Everything Until Resolved)

- **Task 0.2 (liboqs build)** — if this fails, all PQ work is blocked. Must resolve before P1.
- **Task 9.2 (Supabase Auth)** — if auth providers can't be configured, all user-facing work blocked.
- **Task 12.1 (WASM build)** — if WASM packaging fails, web client falls back to API-side crypto OR web client is deferred in favor of CLI-only demo. Decision point only if task fails.

### Soft Blockers (Workaround Exists)

- Any specific storage provider OAuth (use Mock connector; continue with others).
- LLM provider unavailable (rule-based recommender + static KB works standalone).
- Apple OAuth unavailable (skip — other 6 providers suffice for "many login methods").
- Browser memory limits (use smaller test files in browser demo; 1GB demo via CLI).

---

_End of RISKS.md_