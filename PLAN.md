# CryptaVault — Master Execution Plan
## AI-Assisted Adaptive Hybrid Cryptographic Storage Framework

**Project**: CryptaVault
**Type**: Research + Software Engineering + Applied Cryptography + Number Theory
**Language**: Python 3.11+ (crypto core) · TypeScript (web client + admin)
**Interface**: REST API (FastAPI) + Web Client (WASM crypto) + Admin Console (React SPA) + CLI (Typer)
**Database / Backend-as-a-Service**: **Supabase** (PostgreSQL + Auth + RLS)
**Post-Quantum**: Real liboqs integration via `oqs-python` (server) / `oqs-wasm` (browser)
**AI**: Rule-based heuristic engine + optional cloud LLM (OpenAI/Anthropic)
**Team**: Solo
**Duration**: 16 weeks (4 months)
**Difficulty**: Advanced — Final Year Minor Project

---

## 0. Locked Decisions

| # | Decision | Choice | Rationale |
|---|-----------|--------|-----------|
| 1 | Primary crypto language | Python 3.11+ | Richest crypto ecosystem, PQ bindings, fast prototyping |
| 2 | Database / BaaS | **Supabase** (PostgreSQL) | Relational fit for users/keys/shares/audit; built-in auth; RLS; self-hostable |
| 3 | Zero-knowledge boundary | **Client-side crypto via WebAssembly** | Spec mandates providers never see plaintext/keys; crypto runs in browser |
| 4 | Auth methods | Email/pw + Google + GitHub + Microsoft + Apple + Magic Link + Passkeys/WebAuthn | "Many login methods" requirement; Supabase Auth supports all |
| 5 | User dashboard | HTMX + Tailwind (server-rendered via FastAPI) | Minimal JS, fast, simple |
| 6 | Admin console | **React + shadcn/ui SPA** | "Big admin page" benefits from SPA; rich component library |
| 7 | Admin routing | **Separate subdomain** (`admin.cryptavault.app`) | Security isolation, separate auth scope, cookie scoping |
| 8 | Post-quantum | Real liboqs (Kyber + Dilithium) | Academically strong, genuine PQ security |
| 9 | AI assistant | Rule-based core + optional cloud LLM | Deterministic offline core; LLM for natural-language explanations |
| 10 | AI data minimization | LLM receives metadata ONLY (type, size, mode) — never plaintext/keys/contents | Zero-knowledge boundary enforcement |
| 11 | Forward secrecy | Ratcheted per-file ephemeral keys wrapped by rotated master | Closest at-rest analogue; documented honestly |
| 12 | Benchmark Lab | Kept | Strong academic value for technical-depth grading |
| 13 | Evaluation focus | Technical depth | Crypto/math rigor, benchmarks, architecture over UI polish |
| 14 | Secure deletion | Best-effort (overwrite + memory wipe) | Honest about SSD/journaling FS limitations |

## 1. Out of Scope (Deferred to Future Work)

These items from the original spec are explicitly deferred beyond the 4-month minor project:

- Tunnel-based transfer (WebRTC / QUIC / WireGuard concepts)
- HSM / TPM integration
- Multi-device encrypted synchronization
- Threshold cryptography for shared key recovery
- Secure team workspaces with role-based access (lite RBAC in admin only)
- Decentralized storage backends (IPFS, Filecoin)
- Encrypted searchable indexes
- Secure mobile clients (native)
- Enterprise policy management
- Compliance reporting (GDPR, HIPAA)
- SDKs for Python, JavaScript, Go, Java, C# (the Python core + TS web client ARE the first SDKs)
- Azure Blob, MinIO, WebDAV, SMB, NAS, custom REST storage providers (plugin interface supports them; impl deferred)
- SMS OTP via Twilio (passkeys/WebAuthn chosen instead — more secure, no cost)

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CRYPTAVAULT ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────┘

  ┌────────────────┐        ┌────────────────┐        ┌────────────────┐
  │  Web Client    │        │  Admin Console  │        │  CLI (Typer)   │
  │  (React + WASM)│        │  (React SPA)    │        │  (Python)      │
  │                                 │                │        │                │
  │  ┌──────────┐  │        │  ┌───────────┐  │        │  ┌───────────┐ │
  │  │ Crypto   │  │        │  │ User mgmt │  │        │  │ Crypto   │ │
  │  │ (WASM)   │  │        │  │ Audit log │  │        │  │ (native) │ │
  │  │ Keys here│  │        │  │ Providers │  │        │  │ Keys here│ │
  │  └──────────┘  │        │  └───────────┘  │        │  └───────────┘ │
  └───────┬────────┘        └───────┬────────┘        └───────┬────────┘
          │                         │                         │
          │ HTTPS/REST              │ HTTPS/REST              │ HTTPS/REST
          │ (JWT + cookies)         │ (Admin JWT + RBAC)      │ (API token)
          ▼                         ▼                         ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    API GATEWAY (FastAPI)                          │
  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐  │
  │  │ Auth    │ │ Users   │ │ Shares   │ │ Audit  │ │ Orchestrate│ │
  │  │ (Supab) │ │ (Supab) │ │ (tokens) │ │ (log)  │ │ (RPC)     │  │
  │  └─────────┘ └─────────┘ └──────────┘ └────────┘ └───────────┘  │
  │  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐ │
  │  │ Benchmarks  │ │ AI Advisory │ │ Profile cfg│ │ Admin API│ │
  │  └─────────────┘ └──────────────┘ └────────────┘ └──────────┘ │
  └────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    SUPABASE (PostgreSQL)                          │
  │  ┌──────┐ ┌──────┐ ┌──────────┐ ┌────────┐ ┌────────────────┐ │
  │  │users │ │keys_ │ │share_    │ │audit_  │ │benchmark_      │ │
  │  │      │ │manifest│ tokens   │ │ log    │ │ results        │ │
  │  └──────┘ └──────┘ └──────────┘ └────────┘ └────────────────┘ │
  │  + Row Level Security (RLS) on every table                      │
  └─────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────┐
  │              STORAGE CONNECTORS (encrypted-only)                 │
  │  ┌──────┐ ┌──────┐ ┌─────────────────────────────────────────┐ │
  │  │Local │ │ SFTP │ │ Cloud: GDrive / OneDrive / Dropbox     │ │
  │  └──────┘ └──────┘ └─────────┬───────────────────────────────┘ │
  └──────────────────────────────┼──────────────────────────────────┘
                                 │
                                 ▼
                    Storage Providers (see ciphertext only)
                    NEVER plaintext, NEVER encryption keys
```

### Zero-Knowledge Boundary (Critical)

The zero-knowledge boundary is enforced at the **client**:

1. **Encryption keys** are generated, stored, and used **entirely in the browser** (WebAssembly) or **on the local device** (CLI). Keys never traverse the network.
2. **File encryption** happens client-side. The API server only ever receives ciphertext + encrypted manifests.
3. **The API server + Supabase** coordinate accounts, share tokens, audit logs, and orchestration — but cannot decrypt user files (no keys stored server-side in the database).
4. **Supabase Auth** manages identity, but the user's master key is derived from their password via Argon2id **in the browser**, not on the server. The server only sees the auth hash (Supabase's responsibility) and the encrypted key manifest.
5. **The admin console** can manage users, view audit logs, toggle feature flags — but **cannot** read user files (no key access).

## 3. Module Map (Monorepo Layout)

```
CryptaVault/
├── packages/
│   ├── core/                     # Python crypto core (also ships to WASM)
│   │   └── cryptavault/
│   │       ├── crypto/           # symmetric, asymmetric, pq, hybrid, hash, kdf
│   │       ├── signatures/       # ECDSA, Ed25519, Dilithium, hybrid
│   │       ├── integrity/        # per-file hash, Merkle trees
│   │       ├── keys/            # KMS: hierarchy, keystore, rotate, backup
│   │       ├── adaptive/        # Security profiles + engine
│   │       ├── compression/     # detect, policy, algorithms
│   │       ├── pipeline/        # chunked, parallel, resume, queue, orchestrator
│   │       ├── metadata/        # encrypted manifest, secure delete
│   │       ├── sharing/         # packages, tokens, QR, invitation
│   │       ├── storage/         # connector ABC + impls (local, sftp, cloud)
│   │       ├── plugins/         # registry + interfaces
│   │       ├── benchmark/       # crypto benchmark lab
│   │       └── ai/              # rules + llm
│   ├── api/                      # FastAPI backend
│   │   └── cryptavault_api/
│   │       ├── auth/            # Supabase Auth integration, JWT verify
│   │       ├── routes/         # users, keys, shares, audit, benchmarks, ai, admin
│   │       ├── middleware/      # RBAC, rate limit, request id
│   │       ├── models/          # Pydantic schemas + ORM
│   │       ├── deps/            # Supabase client, current_user
│   │       └── main.py
│   ├── web/                      # React web client (user-facing dashboard)
│   │   └── src/
│   │       ├── crypto/          # WASM loader, async crypto wrappers
│   │       ├── components/      # upload, download, share, dashboard widgets
│   │       ├── pages/          # dashboard, files, shares, benchmarks, profile
│   │       └── lib/            # supabase client, api client
│   ├── admin/                    # React admin console (shadcn/ui)
│   │   └── src/
│   │       ├── features/        # users, sessions, providers, audit, flags, health
│   │       ├── components/       # data tables, charts, dialogs, filters
│   │       └── lib/            # admin api client, rbac checks
│   ├── wasm/                     # Build config to compile core/ → WASM
│   │   └── build.sh             # Pyodide/PyScript packaging
│   └── cli/                      # Typer CLI
│       └── cryptavault_cli/
│           └── commands/         # upload, download, share, keys, profile, benchmark
├── docs/                         # SRS, phase specs, research, setup, API
├── research/                     # Number theory notes + annotated impls
├── benchmarks/                   # Benchmark results (CSV/JSON)
├── examples/                     # Usage examples
├── supabase/                     # DB migrations + RLS policies
├── .github/workflows/            # CI
├── pyproject.toml
├── package.json
├── turbo.json                    # Monorepo build orchestration
└── README.md
```

## 4. Phase Breakdown — 16 Weeks, 17 Phases, 74 Tasks

| Wk | Phase | Focus | Tasks |
|----|-------|-------|-------|
| 1 | P0 | Bootstrap (repo, deps, liboqs, OAuth, Supabase) | 7 |
| 2–3 | P1 | Classical Crypto Core | 5 |
| 4 | P2 | Post-Quantum Crypto | 4 |
| 5 | P3 | Signatures + Integrity | 5 |
| 6 | P4 | Key Management | 5 |
| 7 | P5 | Adaptive Security Engine | 6 |
| 8 | P6 | Compression | 5 |
| 9 | P7 | Streaming Pipeline | 5 |
| 10 | P8 | Metadata + Secure Deletion | 4 |
| 11 | P9 | API + Auth Backend (Supabase) | 6 |
| 12 | P10 | Storage Connectors | 7 |
| 13 | P11 | Secure Sharing | 6 |
| 14 | P12 | Web Client (WASM Crypto) | 5 |
| 14 | P13 | Admin Console (React SPA) | 5 |
| 15 | P14 | Dashboard + Benchmark Lab | 5 |
| 15 | P15 | AI Assistant | 4 |
| 16 | P16 | Integration + Report | 5 |
| | | **Total** | **74** |

### Phase Dependencies

```
P0 ──┬─► P1 ──► P2 ──► P3 ──► P4 ──► P5 ──► P6 ──► P7 ──► P8 ──────────┐
     │                                                                  │
     ├─► P9 (API + Auth) ────────────────────────────► P11 (Sharing) ──┤
     │                                  ▲                               │
     └─► P10 (Storage) ─────────────────┼───────────────────────────────┤
                                        ▼                               │
                                        P12 (Web Client WASM) ─────────►│
                                        P13 (Admin SPA) ──────────────►│
                                        P14 (Dashboard + Bench) ─────►│
                                        P15 (AI) ────────────────────►│
                                                                       ▼
                                                                   P16 (Integration + Report)
```

Critical path: P0 → P1 → P2 → P3 → P4 → P5 → P7 → P8 → P12 → P16

## 5. Detailed Task Breakdown

### Phase P0 — Project Bootstrap (Week 1) — 7 Tasks

#### Task 0.1 — Monorepo & Packaging Scaffold
**Deliverable**: Monorepo structure with Python + TypeScript workspace setup.
- Initialize git repo at `/home/boss/tools/CryptaVault`.
- Create `pyproject.toml` (Python workspace: `packages/core`, `packages/api`, `packages/cli`) with PEP 621 metadata, version `0.1.0`, dev deps (pytest, hypothesis, ruff, black, mypy, httpx).
- Create `package.json` (TS workspace: `packages/web`, `packages/admin`) with pnpm workspaces, turbo.json for build orchestration.
- Create directory tree per Module Map above; add `.gitignore`, `README.md` skeleton, `LICENSE` (MIT), `AGENTS.md` with build/lint/test commands for both ecosystems.
- **Acceptance**: `pip install -e packages/core packages/api packages/cli` succeeds; `pnpm install` succeeds; `python -c "import cryptavault"` works; `ruff check .` + `black --check .` + `mypy packages` clean; `pnpm typecheck` clean.

#### Task 0.2 — liboqs Build Verification (HARD BLOCKER)
**Deliverable**: Working `liboqs` + `oqs-python` (server) and `oqs-wasm` (browser) with KAT baseline.
- Clone `open-quantum-safe/liboqs`; build with CMake (`-DOQS_USE_OPENSSL=ON`).
- Install `oqs-python` bindings; verify Kyber768 + Dilithium3 KATs.
- Verify `oqs-wasm` builds for browser via Emscripten (or use prebuilt `oqs-wasm` package).
- If native build fails, create `Dockerfile.dev` with prebuilt liboqs; document in `docs/setup.md`.
- Record exact liboqs commit hash + versions in `docs/setup.md`; capture KAT outputs as `packages/core/tests/kat/pq_baseline.json`.
- **Acceptance**: `python -c "import oqs; print(oqs.get_enabled_kem_mechanisms())"` lists Kyber variants; Dilithium sign/verify round-trips; `oqs-wasm` loads in a JS smoke test; baseline KAT file committed.

#### Task 0.3 — Core Library Dependencies & Smoke Tests
**Deliverable**: All runtime deps installed + importable, failures surfaced early.
- Pin in `packages/core/pyproject.toml`: `cryptography`, `argon2-cffi`, `blake3`, `zstandard`, `python-lzma`, `brotli`, `paramiko`, `qrcode[pil]`, `typer`, `rich`, `pydantic`, `httpx`, `mnemonic`.
- Pin in `packages/api/pyproject.toml`: `fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart`, `supabase`, `gotrue`, `psycopg2-binary`, `redis` (optional), `httpx`, `pydantic`.
- Pin in `packages/web/package.json`: `react`, `react-dom`, `vite`, `typescript`, `tailwindcss`, `@supabase/supabase-js`, `@tanstack/react-query`, `wouter`, `lucide-react`.
- Pin in `packages/admin/package.json`: `react`, `react-dom`, `vite`, `typescript`, `shadcn/ui`, `@tanstack/react-table`, `recharts`, `@supabase/supabase-js`, `zustand`.
- Write `packages/core/tests/test_smoke_imports.py` importing each library.
- **Acceptance**: All smoke imports succeed; `pytest packages/core/tests/test_smoke_imports.py` green; `pnpm build` for web/admin succeeds on bare scaffolds.

#### Task 0.4 — CI Pipeline (GitHub Actions)
**Deliverable**: Automated quality gates on every push.
- Create `.github/workflows/ci.yml`: lint (ruff + eslint) → format check (black + prettier) → typecheck (mypy + tsc) → pytest (with hypothesis) → web build.
- Matrix: Python 3.11/3.12 × Node 20; cache pip + pnpm + liboqs build via `actions/cache`.
- Add `pytest --hypothesis-seed=0` for deterministic property tests; `pnpm test` for TS unit tests.
- **Acceptance**: CI green on trivial placeholder tests; a deliberately broken commit is rejected.

#### Task 0.5 — OAuth + Cloud Provider Registrations (PARALLEL, KICK OFF EARLY)
**Deliverable**: OAuth client credentials for all auth + storage providers.
- **Google**: Google Cloud project → Enable Drive API + Identity → OAuth 2.0 Client ID → scopes `drive.file`, `openid email profile`.
- **Microsoft**: Entra ID → App registration → `Files.ReadWrite` (OneDrive) + `openid email profile` → platform "Web" + "SPA".
- **GitHub**: GitHub OAuth App → scope `user:email`.
- **Apple**: Apple Developer → Sign in with Apple → Service ID + key (nice-to-have; only if Apple dev account available).
- **Dropbox**: Dropbox Developer Console → app → `files.content.readwrite` + `account_info.read`.
- Store client_id/secret in Supabase project settings (not local files); document redirect URIs in `docs/oauth_setup.md`.
- **Acceptance**: All OAuth client IDs issued; Supabase Auth providers configured for Google/GitHub/MS/Apple; Dropbox + GDrive storage credentials stored.

#### Task 0.6 — Supabase Project & Schema Foundation
**Deliverable**: Supabase project provisioned with initial schema + RLS policies.
- Create Supabase project; note project URL + anon key + service role key (in OS keyring / env).
- Write `supabase/migrations/0001_init.sql`:
  - `profiles` table (extends `auth.users` via `uid uuid references auth.users`): `display_name`, `created_at`, `role` (user/admin/auditor), `quota_bytes`, `suspended`.
  - `key_manifests` table: `user_id`, `encrypted_manifest` (bytea), `manifest_nonce`, `updated_at`.
  - `share_tokens` table: `token_id`, `owner_id`, `file_ref`, `expires_at`, `max_uses`, `current_uses`, `password_hash` (nullable), `wrapped_key` (bytea).
  - `audit_log` table: `id`, `user_id`, `operation`, `target`, `metadata` (jsonb), `prev_hash`, `entry_hash`, `signature`, `created_at`.
  - `benchmark_results` table: `id`, `user_id`, `algorithm`, `metric`, `value`, `created_at`.
  - `feature_flags` table: `flag`, `enabled`, `description`.
- Write RLS policies in `supabase/migrations/0002_rls.sql`: users read/update own rows; admins read all; auditors read audit_log only.
- Run migrations via `supabase db push` (local dev) and confirm in Supabase dashboard.
- **Acceptance**: Tables created; RLS policies enforce user-isolation; a test user cannot read another user's `key_manifests`.

#### Task 0.7 — Plugin Architecture Skeleton
**Deliverable**: Typed registry + ABCs enabling future extensions without core changes.
- Define `packages/core/cryptavault/plugins/registry.py` with typed registries: `StorageConnector`, `CompressionAlgorithm`, `HashAlgorithm`, `EncryptionAlgorithm`, `SignatureAlgorithm`, `KemAlgorithm`, `KdfAlgorithm`, `AiProvider`.
- Define `@register_storage`, `@register_compression`, etc. decorators.
- Define ABCs with abstract methods only (see ARCHITECTURE.md for contracts).
- Register entry-point group `cryptavault.plugins` in `packages/core/pyproject.toml`.
- Write `packages/core/tests/test_registry.py`: register dummy plugins, retrieve by name, ensure duplicates raise.
- **Acceptance**: Registry round-trips dummy plugin; entry-point discovery test passes; documented in `docs/plugin_development.md`.

---

### Phase P1 — Classical Cryptography Core (Weeks 2–3) — 5 Tasks

#### Task 1.1 — Symmetric Cipher Module (`crypto/symmetric.py`)
**Deliverable**: AES-256-GCM + ChaCha20-Poly1305 with uniform AEAD API.
- Implement `AES256GCM` and `ChaCha20Poly1305` classes wrapping `cryptography.hazmat.primitives.ciphers.aead`.
- API: `encrypt(key: bytes[32], nonce: bytes[12], plaintext: bytes, aad: bytes) -> bytes`, `decrypt(key, nonce, ciphertext_and_tag, aad) -> bytes`.
- Auto-generate 96-bit random nonce when not provided; return `(nonce, ciphertext)` tuple.
- Constant-time tag comparison; fail-closed on mismatch (raise `InvalidTagError`).
- Register both as `EncryptionAlgorithm` plugins.
- **Tests**: NIST GCM / Wycheproof test vectors; Hypothesis round-trip property, AAD mismatch rejection, nonce-reuse resistance demo (negative test).
- **Acceptance**: All KATs pass; Hypothesis survives 100 examples; type annotations complete.

#### Task 1.2 — Asymmetric Cipher Module (`crypto/asymmetric.py`)
**Deliverable**: RSA-4096 + ECC (X25519 ECDH, Ed25519 sig, ECDSA P-256/P-384).
- Implement `RSA4096`: OAEP encrypt/decrypt (SHA-256), PSS sign/verify.
- Implement `X25519`: `exchange(private, peer_public) -> shared_secret`.
- Implement `Ed25519` and `ECDSA(P-256/P-384)`: sign/verify with canonical serialization.
- Uniform `KeyPair` dataclass: `private_pem(password=None)`, `public_pem()`, `from_pem(pem, password)`.
- Register as `SignatureAlgorithm` plugins (Ed25519, ECDSA) and `KemAlgorithm` (X25519).
- **Tests**: KAT vectors; ECDH two-party agreement; signature verify rejects tampered message; PEM round-trip with/without password.
- **Acceptance**: All KATs pass; Hypothesis round-trips; PEM serialization secure (PKCS#8 encrypted).

#### Task 1.3 — Hash Module (`crypto/hash.py`)
**Deliverable**: SHA-256, SHA3-512, BLAKE3 with streaming + plugin registration.
- Implement `Sha256`, `Sha3512`, `Blake3` classes with `digest(data, size=None) -> bytes`.
- Implement streaming variant: `streaming() -> ctx` with `update(chunk)`, `finalize() -> bytes`.
- Register each as `HashAlgorithm` plugin.
- **Tests**: NIST SHA-2/SHA-3 vectors; BLAKE3 official vectors; streaming hash of 1GB temp file equals full-bytes hash.
- **Acceptance**: All KATs pass; streaming ≈ full hash match; size override honored.

#### Task 1.4 — KDF Module (`crypto/kdf.py`)
**Deliverable**: Argon2id, PBKDF2-HMAC-SHA256, HKDF-SHA256.
- Implement `Argon2id`: params `t=3, m=64MiB, p=4` (tunable); `derive(password, salt, length=32)`.
- Implement `Pbkdf2`: `iterations=600000` (OWASP min for SHA-256); fallback if Argon2 unavailable.
- Implement `HkdfSha256`: `extract(salt, ikm)`, `expand(prk, info, length)`, `derive(ikm, salt, info, length)`.
- Register each as `KdfAlgorithm` plugin.
- **Tests**: RFC 5869 HKDF KATs; Argon2id round-trip; PBKDF2 KATs; timing test (Argon2id ≤100ms on dev hardware).
- **Acceptance**: All KATs pass; params documented; Argon2id runs in ≤100ms.

#### Task 1.5 — Hybrid KEM (Classical) (`crypto/hybrid.py`)
**Deliverable**: Composite KEM combining X25519 ECDH + HKDF for key encapsulation.
- Implement `HybridKemClassical`: `encapsulate(peer_public_key) -> (ciphertext, shared_secret)`, `decapsulate(private_key, ciphertext) -> shared_secret`.
- Flow: ephemeral X25519 keypair → ECDH with peer public → HKDF(shared) → shared secret + ephemeral public as ciphertext.
- **Tests**: Two-party round-trip; Hypothesis key independence; ephemeral keys unique per call.
- **Acceptance**: Round-trip works; shared secret matches both sides; ephemeral keys unique.

---

### Phase P2 — Post-Quantum Cryptography (Week 4) — 4 Tasks

#### Task 2.1 — liboqs Kyber KEM Integration (`crypto/pq.py`)
**Deliverable**: Kyber512/768/1024 KEM via liboqs, registered as plugin.
- Implement `KyberKem`: `keypair() -> (public, secret)`, `encapsulate(public_key) -> (ciphertext, shared_secret)`, `decapsulate(secret_key, ciphertext) -> shared_secret`.
- Support `KYBER_512`, `KYBER_768`, `KYBER_1024` mapped to NIST security levels 1/3/5.
- Register as `KemAlgorithm` plugin.
- **Tests**: NIST PQC KAT vectors for Kyber768 & Kyber1024; Hypothesis round-trip; ciphertext tampering → mismatched secret (fail-closed downstream).
- **Acceptance**: All Kyber KATs pass; tamper test confirms decapsulation yields wrong secret.

#### Task 2.2 — liboqs Dilithium Signature Integration (`crypto/pq.py`)
**Deliverable**: Dilithium2/3/5 signatures via liboqs, registered as plugin.
- Implement `DilithiumSig`: `keypair()`, `sign(secret_key, message)`, `verify(public_key, message, signature) -> bool`.
- Map Dilithium2/3/5 to NIST levels 1/3/5.
- Register as `SignatureAlgorithm` plugin.
- **Tests**: NIST PQC KAT vectors; tampered message → verify failure; tampered signature → verify failure.
- **Acceptance**: All KATs pass; verify rejects single-bit flip in message or signature.

#### Task 2.3 — Hybrid KEM (X25519 + Kyber) (`crypto/hybrid.py`)
**Deliverable**: PQ-hybrid KEM resistant to "harvest now, decrypt later".
- Implement `HybridKemPQ`: `encapsulate(peer_public_key) -> (ciphertext, shared_secret)`; `ciphertext = (ecdh_ciphertext, kyber_ciphertext)`, `shared_secret = HKDF(ecdh_secret ‖ kyber_secret)`.
- `decapsulate(private_key, ciphertext) -> shared_secret` (dual decap, combine via HKDF).
- Public key = `(x25519_pub, kyber_pub)`; private key = `(x25519_priv, kyber_priv)`.
- **Tests**: Two-party round-trip; tamper ECDH component → mismatch; tamper Kyber component → mismatch; Hypothesis independence.
- **Acceptance**: Round-trip matches; either-component tamper detected; composition proof in `research/notes/hybrid_kem.md`.

#### Task 2.4 — Hybrid Signature (Ed25519 + Dilithium) (`crypto/hybrid.py`)
**Deliverable**: PQ-hybrid signature requiring BOTH classical and PQ verification.
- Implement `HybridSigPQ`: `sign(message) -> (ed25519_sig, dilithium_sig)`; `verify(public_key, message, signature) -> bool` returns True only if BOTH pass.
- Public key = `(ed25519_pub, dilithium_pub)`.
- **Tests**: Round-trip; flipping one signature → fail; flipping message → both fail.
- **Acceptance**: Both signatures required; either tamper → fail; doc in `research/notes/hybrid_sig.md`.

---

### Phase P3 — Signatures + Integrity (Week 5) — 5 Tasks

#### Task 3.1 — Digital Signature Abstraction Layer (`signatures/base.py`)
**Deliverable**: Uniform `Signer`/`Verifier` interfaces across ECDSA, Ed25519, Dilithium, Hybrid.
- Implement `SignatureContext` holding active algorithm + key; `sign(file_path)` (streams file → hashes → signs), `verify(file_path, signature)`.
- **Tests**: All four algorithms round-trip via common interface; missing keys rejected.
- **Acceptance**: One API, four backends; streaming sign of 1GB works without full load.

#### Task 3.2 — Tamper & Corruption Detection (`signatures/verify.py`)
**Deliverable**: Verification engine detecting tampering, modification, corruption.
- `verify_file(path, signature, public_key) -> VerificationResult` with enum: `VALID`, `TAMPERED`, `CORRUPTED`, `MISSING_KEY`.
- Byte modification → `TAMPERED`; truncation → `CORRUPTED`; wrong key → `MISSING_KEY`.
- Emit structured result with diagnostic details.
- **Tests**: Flip byte at start/middle/end → `TAMPERED`; truncate → `CORRUPTED`; wrong key → `MISSING_KEY`.
- **Acceptance**: All tamper scenarios detected; result includes diagnostic info.

#### Task 3.3 — Per-File Integrity Hashing (`integrity/file_hash.py`)
**Deliverable**: BLAKE3-dominant per-file hash with configurable algorithm.
- `compute_file_hash(path, algorithm='blake3') -> digest` streaming in 1MB chunks.
- Store digest in encrypted manifest alongside file metadata.
- Support SHA-256, SHA3-512, BLAKE3 via plugin registry.
- **Tests**: Round-trip; different algorithm produces different but valid digest; 1GB file hashes without OOM.
- **Acceptance**: Streaming hash works; algorithm pluggable; 1GB test passes.

#### Task 3.4 — Merkle Tree for Folders (`integrity/merkle.py`)
**Deliverable**: Merkle tree over file hashes with O(log n) tamper localization.
- Implement `MerkleTree`: `build(leaf_hashes) -> root`, `proof(leaf_index) -> list[bytes]`, `verify_proof(leaf, proof, root) -> bool`.
- Leaves = per-file BLAKE3 hashes; internal nodes = SHA-256(parent_left ‖ parent_right).
- Serialize root + proof to portable format for sharing.
- **Tests**: Round-trip build→proof→verify on 1000 leaves; tamper one leaf → proof fails; Hypothesis property.
- **Acceptance**: Merkle proof works; tamper at any level detected; proof size O(log n).

#### Task 3.5 — Integrity Report Generator (`integrity/report.py`)
**Deliverable**: Human-readable + JSON integrity report for a folder/file set.
- `generate_report(folder_path, manifest) -> IntegrityReport`: enumerate files, verify hashes + signatures, produce table + JSON.
- Integrate Merkle proof verification for subset verification.
- **Tests**: Clean folder → all VALID; tampered folder → lists each tampered file with reason.
- **Acceptance**: Report shows VALID/TAMPERED per file; JSON export; supports partial verification.

---

### Phase P4 — Key Management System (Week 6) — 5 Tasks

#### Task 4.1 — Key Hierarchy & Data Structures (`keys/hierarchy.py`)
**Deliverable**: Hierarchical key tree: master → data keys → share keys.
- Define `KeyTier`: `MASTER`, `DATA`, `SHARE`, `SESSION` (ephemeral).
- Define `KeyDescriptor` dataclass: `id`, `tier`, `algorithm`, `created_at`, `version`, `parent_id`, `wrapped_key`.
- Master key derived from user password via Argon2id **client-side**; data keys derived/random and wrapped.
- Implement `KeyTree`: `add_key`, `get_key(id)`, `rotate_key(id)`, `find_root()`.
- **Tests**: Tree round-trips; parent-child enforced; rotating parent re-wraps children.
- **Acceptance**: Hierarchy enforced; rotation cascades; JSON serialization (wrapped keys only) works.

#### Task 4.2 — Encrypted Keystore (`keys/keystore.py`)
**Deliverable**: On-disk (CLI) / browser-storage (web) encrypted keystore holding wrapped keys only.
- `Keystore.save(tree, master_password)` / `Keystore.load(master_password)`.
- File format: JSON envelope `{version, salt, argon2_params, encrypted_blob}`; blob = AES-256-GCM(tree_json, key=Argon2id(password, salt)).
- Browser variant: encrypt keystore, store in `localStorage` or `IndexedDB` (encrypted at rest with password-derived key, decrypted in memory only on unlock).
- **Tests**: Save→load round-trip; wrong password → fail; tamper keystore file → GCM tag failure.
- **Acceptance**: Keystore round-trips; wrong password rejected; tamper detected.

#### Task 4.3 — Key Generation, Rotation & Versioning (`keys/operations.py`)
**Deliverable**: Full CRUD: generate, rotate, version, destroy.
- `generate_key(tier, algorithm) -> KeyDescriptor`: random or derived; assigns new id + version.
- `rotate_key(id) -> new_descriptor`: generate new key, re-wrap children, mark old as `RETIRED` (decrypt old, not encrypt new).
- `version_key(id)`: increment version, keep history.
- `destroy_key(id)`: remove + cryptographically erase (overwrite memory + mark `DESTROYED`).
- **Tests**: Generate→rotate → new key encrypts; old files decrypt with retired key; destroy → unrecoverable.
- **Acceptance**: Rotation seamless; backward compat for decryption; destroy irreversible.

#### Task 4.4 — Key Backup & Recovery (`keys/backup.py`)
**Deliverable**: Export master key wrapped by recovery key; import for recovery.
- `export_recovery_bundle(master_password) -> bundle`: recovery key (random 256-bit) wraps master; 24-word mnemonic via `mnemonic` lib.
- `import_recovery_bundle(mnemonic, bundle) -> KeyTree`: re-derive recovery key, unwrap master.
- `verify_recovery_bundle(mnemonic, bundle) -> bool` for offline verification.
- **Tests**: Export→import round-trip; wrong mnemonic → fail; partial mnemonic → fail.
- **Acceptance**: Mnemonic round-trips; wrong words rejected; procedure documented in `docs/key_recovery.md`.

#### Task 4.5 — Key Import/Export (Interop) (`keys/io.py`)
**Deliverable**: Import/export keys in standard formats (PEM, DER, raw bytes).
- `export_key(id, format='pem', password=None) -> bytes`: PKCS#8 PEM for asymmetric; raw bytes for symmetric (warn).
- `import_key(data, format, password=None, tier) -> KeyDescriptor`.
- Validate key strength on import (reject <256-bit symmetric, <2048-bit RSA).
- **Tests**: PEM round-trip; import rejects weak keys; invalid format → clear error.
- **Acceptance**: Standard PEM interop works; weak keys rejected; format auto-detected.

---

### Phase P5 — Adaptive Security Engine (Week 7) — 6 Tasks

#### Task 5.1 — Security Profile Definition (`adaptive/profiles.py`)
**Deliverable**: 5 preset profiles mapping slider % to algorithm combinations.
- Define `SecurityProfile` dataclass with all algorithm fields + flags (`metadata_encryption`, `audit_logging`, `forward_secrecy`).
- Presets:
  - `PERFORMANCE` (0–20%): AES-128-GCM, X25519, ECDSA-P256, SHA-256, PBKDF2, fast compress, minimal integrity, no metadata enc, no FS, no audit.
  - `STANDARD` (20–50%): AES-256-GCM, X25519, ECDSA-P256, SHA-256, Argon2id, smart compress, full integrity, metadata enc, no FS, no audit.
  - `STRONG` (50–80%): AES-256-GCM + ChaCha20-Poly1305, X25519, Ed25519, SHA-256, Argon2id, smart compress, full integrity, metadata enc, optional FS, optional audit.
  - `MAXIMUM` (80–100%): AES-256-GCM + ChaCha20-Poly1305, Hybrid KEM (X25519+Kyber768), Hybrid sig (Ed25519+Dilithium3), SHA3-512/BLAKE3, Argon2id, full compress, Merkle integrity, metadata enc, FS ratchet, full audit.
  - `BALANCED` (35–65%): user-tunable midpoint.
- **Tests**: Each profile initializes; slider mapping correct; invalid % → ValueError.
- **Acceptance**: 5 profiles defined; slider→profile resolution works; documented in `docs/profiles.md`.

#### Task 5.2 — Adaptive Engine Core (`adaptive/engine.py`)
**Deliverable**: Engine consumes profile + file metadata → emits concrete `PipelineConfig`.
- `AdaptiveEngine.resolve(profile, file_metadata) -> PipelineConfig`: maps profile to plugin instances via registry.
- Tunable knobs: `chunk_size` scales with file size; `parallel_workers` scales with CPU/core count.
- **Tests**: Each profile → expected config; large file → larger chunks; CPU detection → correct workers.
- **Acceptance**: Valid `PipelineConfig` for all 5 profiles; chunk/worker scaling documented.

#### Task 5.3 — Multi-Layer Encryption Mode (`adaptive/engine.py`)
**Deliverable**: For MAXIMUM profile, encrypt data twice (AES outer, ChaCha inner).
- `multi_layer_encrypt(data, keys, algos)`: inner ChaCha, outer AES; reverse for decrypt.
- Independent keys per layer (HKDF-derived with different `info` strings).
- **Tests**: Round-trip; tamper outer → detected; tamper inner → detected; Hypothesis.
- **Acceptance**: Two-layer works; either tamper detected; overhead measured.

#### Task 5.4 — Forward Secrecy (Ratcheted Per-File Keys) (`adaptive/forward_secrecy.py`)
**Deliverable**: Per-file ephemeral keys derived via ratchet from master.
- `RatchetKdf`: `next_key() -> file_key` (HKDF with counter salt); `current_state() -> snapshot`.
- Each file encrypted with own key; file key wrapped by current ratchet key, stored in manifest.
- Honest doc: true FS is a session property; ratchet approximates for at-rest.
- **Tests**: Two files → different keys; ratchet advances; compromise old state → can't derive new.
- **Acceptance**: Per-file keys unique; ratchet advances; limitation in `research/notes/forward_secrecy.md`.

#### Task 5.5 — Audit Logging (`adaptive/audit.py`)
**Deliverable**: For MAXIMUM profile, tamper-evident hash-chained audit log.
- `AuditLog.append(entry)`: each entry includes `prev_hash`, `entry_hash`, signed by master key.
- Log fields: timestamp, operation, file_id, key_id, profile, outcome, signature.
- Sync to Supabase `audit_log` table (server stores but cannot forge — hash chain verified client-side).
- **Tests**: Append→verify chain; tamper entry → invalid; missing signature → flagged.
- **Acceptance**: Append-only log verified; tamper detection; export JSON for report.

#### Task 5.6 — Profile Persistence & CLI Binding (`adaptive/store.py` + `cli/profile.py`)
**Deliverable**: User sets/gets/lists profiles via CLI; persisted in config.
- `cryptavault profile set --slider 75` → resolves to STRONG preset, saves to `~/.cryptavault/config.toml`.
- `cryptavault profile list` → table of presets with algorithm matrix.
- `cryptavault profile get` → current profile.
- **Tests**: Set→get round-trip; invalid slider rejected; listing matches presets.
- **Acceptance**: CLI commands work; profile persisted.

---

### Phase P6 — Intelligent Compression Engine (Week 8) — 5 Tasks

#### Task 6.1 — File Type Detection (`compression/detect.py`)
**Deliverable**: Detect file type by magic bytes (not extension).
- `detect_file_type(path) -> FileType` enum (`IMAGE_JPEG`, `VIDEO_MP4`, `ARCHIVE_ZIP`, `TEXT`, `BINARY_UNKNOWN`).
- Signature table for already-compressed: JPEG, PNG, GIF, MP4, ZIP, GZIP, XZ, ZST, BROTLI, RAR, 7Z, MP3, AAC, HEIC.
- **Tests**: Detect JPEG, MP4, ZIP, plain text, unknown binary.
- **Acceptance**: ≥30 file types detected; compressed skip list documented.

#### Task 6.2 — Skip-Compression Decision Logic (`compression/policy.py`)
**Deliverable**: Policy engine for compress/no-compress based on type + sample ratio.
- `should_compress(file_type, path, profile) -> bool`: False for already-compressed; sample 1MB for unknown; compress if ratio < 0.95.
- Profile ties in: PERFORMANCE fast sample; MAXIMUM full sample.
- **Tests**: JPEG → False; plain text → True; random.bin → False; small text → True.
- **Acceptance**: Correct across 20 diverse file types; threshold documented.

#### Task 6.3 — Compression Algorithms (`compression/algorithms.py`)
**Deliverable**: zstd, LZMA, Brotli, Gzip with uniform streaming interface, registered as plugins.
- `Zstd`, `Lzma`, `Brotli`, `Gzip` classes: `compress(stream) -> stream`, `decompress(stream) -> stream`.
- Streaming: file-like or generators; no full file in memory.
- Auto-select best by ratio for text-like (zstd default; if ratio > 0.7 use LZMA).
- Register each as `CompressionAlgorithm` plugin.
- **Tests**: Round-trip each; 1GB → no OOM; ratio test on 100MB random text.
- **Acceptance**: All round-trip; streaming confirmed; auto-selection picks best.

#### Task 6.4 — Compression Ratio Measurement (`compression/metrics.py`)
**Deliverable**: Instrumentation capturing ratio, time, CPU, memory.
- `measure(algo, data) -> CompressionMetrics {ratio, time_ms, cpu_pct, mem_peak_mb}`.
- Export to dashboard + report as CSV.
- **Tests**: Sane values; ratio matches manual calculation.
- **Acceptance**: Metrics accurate; CSV export.

#### Task 6.5 — Compression in Pipeline Integration (`pipeline/compression_stage.py`)
**Deliverable**: Pipeline stage wrapping compression with skip policy + metrics.
- `CompressionStage.run(input_stream, file_metadata, profile) -> (output_stream, compression_metadata)`.
- If skip → pass-through with `compression=None`; else compress + record metadata.
- **Tests**: JPEG → pass-through; text → compressed with ratio in metadata.
- **Acceptance**: E2E integration test across JPEG + text file.

---

### Phase P7 — High-Speed Streaming Encryption Pipeline (Week 9) — 5 Tasks

#### Task 7.1 — Chunked Streaming Encryption (`pipeline/chunked_encryption.py`)
**Deliverable**: Large files in chunks with per-chunk AEAD.
- `ChunkedEncryptor.encrypt(file_stream, key, chunk_size, aad_prefix) -> EncryptedChunkStream` yielding `(nonce, ciphertext, tag)` per chunk.
- Chunk index in AAD for ordering integrity; file-level nonce prefix (random 96-bit).
- `ChunkedDecryptor` reverses; verifies per-chunk tag; fails fast on tamper.
- **Tests**: 1GB round-trip; memory peak < 200MB; tamper middle chunk → fail at that chunk.
- **Acceptance**: 1GB works; memory bounded; per-chunk tamper detected.

#### Task 7.2 — Parallel Encryption Workers (`pipeline/parallel.py`)
**Deliverable**: Multi-process chunk encryption for CPU utilization.
- `ParallelChunkedEncryptor` via `ProcessPoolExecutor` with `n_workers` from profile.
- Chunks encrypted out-of-order; tagged with index for reordering on decrypt.
- Worker processes receive key via `multiprocessing` shareable memory or sealed bytes (not command line).
- **Tests**: 1GB parallel vs serial → ≥2x speedup on 4-core; output identical to serial; tamper detection intact.
- **Acceptance**: Speedup measured; bitwise-identical output; documented benchmarks.

#### Task 7.3 — Resume Interrupted Operations (`pipeline/resume.py`)
**Deliverable**: Resume encryption/upload from last completed chunk.
- `OperationManifest`: per-file state recording completed chunk indices + hashes + key id + profile.
- On resume: skip completed; continue from next; verify each completed chunk's hash; re-do if mismatched.
- **Tests**: Encrypt 1GB → kill at 50% → resume → completes; corrupt completed chunk → re-do.
- **Acceptance**: Resume works; corrupted chunks re-done; integrity verified.

#### Task 7.4 — Background Queue (`pipeline/queue.py`)
**Deliverable**: Queue-based pipeline for background processing of multiple files.
- `PipelineQueue`: enqueue `(file_path, profile, storage_target)`; worker processes; status callbacks.
- API: `enqueue`, `list_pending`, `cancel(job_id)`, `status(job_id)`.
- Persist queue state to survive restart.
- **Tests**: Enqueue 3 files → all complete; cancel mid-flight → cleaned up; restart → pending resume.
- **Acceptance**: Multi-file handled; cancellation clean; persisted restart works.

#### Task 7.5 — Pipeline Orchestrator (`pipeline/orchestrator.py`)
**Deliverable**: Coordinator composing all stages: compress → encrypt → sign → integrity → metadata → storage.
- `PipelineOrchestrator.run(file_path, profile, storage_target) -> OperationResult` threading streams through stages.
- Each stage receives input stream, emits output stream + metadata into manifest builder.
- Result includes manifest entry, metrics, integrity root, signature.
- **Tests**: E2E on 1GB through all stages; manifest sanity; decrypt reverses cleanly.
- **Acceptance**: Full pipeline E2E works; manifest complete; metrics captured.

---

### Phase P8 — Metadata Protection + Secure Deletion (Week 10) — 4 Tasks

#### Task 8.1 — Metadata Model (`metadata/model.py`)
**Deliverable**: Structured metadata schema for encrypted manifest.
- `FileMetadata` dataclass: `original_name`, `original_size`, `mime_type`, `created_at/modified_at`, `chunk_count`, `compression_algo`, `encryption_algo`, `iv/salt`, `key_id`, `signature`, `integrity_hash`, `merkle_proof`.
- `Manifest` dataclass: `files`, `folder_structure`, `root_hash`, `manifest_version`, `encrypted: bool`.
- **Tests**: Round-trip serialization; required fields enforced; schema versioning.
- **Acceptance**: Schema complete; serialization stable; documented in `docs/manifest_format.md`.

#### Task 8.2 — Encrypted Manifest (`metadata/encrypted_manifest.py`)
**Deliverable**: Manifest encrypted as a whole (metadata protection).
- Encrypt manifest with metadata key (HKDF from master with `info="metadata"`) via AES-256-GCM.
- Store encrypted manifest as `.cryptavault-manifest.enc` on storage provider.
- Sync manifest hash to Supabase `key_manifests` table for cross-device discovery (manifest body encrypted; only hash + ref stored server-side).
- **Tests**: Save→load round-trip; tamper → GCM fail; wrong key → fail.
- **Acceptance**: Manifest encrypted; round-trips; tamper detected; provider sees only ciphertext filename.

#### Task 8.3 — Secure Deletion of Temp Files & Memory (`metadata/secure_delete.py`)
**Deliverable**: Best-effort secure deletion: overwrite temps, wipe buffers, clean cache.
- `secure_delete_file(path)`: overwrite zeros → random → zeros; fsync; unlink.
- Memory buffers: `ctypes.memset(0)` on `bytearray` after use.
- Document impossibility on SSDs/journaling FS; advise FDE for guarantee.
- Maintain `~/.cryptavault/tmp/`; wipe on exit.
- **Tests**: Temp file overwritten (inspect pre-unlink); memory buffer zeroed (read post-wipe).
- **Acceptance**: Overwrite verified; memory wipe verified; limitation in `docs/secure_deletion.md`.

#### Task 8.4 — Metadata Encryption Toggle & Config (`metadata/options.py`)
**Deliverable**: Profile-driven metadata encryption toggle.
- Surface `metadata_encryption` flag per profile; orchestrator respects.
- Optional fields: file size encryption, timestamp randomization (to midnight) for MAXIMUM.
- **Tests**: PERFORMANCE → plaintext manifest (warn); STANDARD+ → encrypted; MAXIMUM → timestamps randomized.
- **Acceptance**: Profile toggles respected; optional fields randomized.

---

### Phase P9 — API + Auth Backend with Supabase (Week 11) — 6 Tasks

#### Task 9.1 — FastAPI App Scaffold + Supabase Client
**Deliverable**: FastAPI app with Supabase client wiring + health endpoints.
- `packages/api/cryptavault_api/main.py`: FastAPI app, CORS, request-id middleware, error handlers.
- `cryptavault_api/deps.py`: `get_supabase()` (async client), `get_current_user()` (verifies JWT from Supabase Auth via `gotrue`), `get_admin_user()` (checks `role=admin`).
- Endpoints: `/health`, `/ready` (DB ping), `/docs` (OpenAPI).
- **Tests**: `httpx.AsyncClient` smoke tests; `/health` returns 200; unauthenticated `/me` returns 401.
- **Acceptance**: App boots; Supabase client connects; health checks pass.

#### Task 9.2 — Supabase Auth Integration (Multi-Provider)
**Deliverable**: Auth supporting Email/PW + Google + GitHub + MS + Apple + Magic Link + Passkeys.
- Configure Supabase Auth providers in dashboard: Email, Google, GitHub, Microsoft, Apple, Magic Link, WebAuthn.
- `/api/auth/session` endpoint: exchanges Supabase access token for app session (HMAC-signed cookie, 15-min access / 7-day refresh).
- `/api/auth/me` returns user profile + role.
- `/api/auth/logout` invalidates session.
- **Tests**: Token verification; expired token → 401; role extraction correct.
- **Acceptance**: All providers work end-to-end in browser; session cookies set; logout clears.

#### Task 9.3 — User Routes + RLS Verification
**Deliverable**: User profile + key manifest sync endpoints.
- `/api/users/me` GET/PATCH (display_name, quota).
- `/api/users/me/manifest` GET (encrypted manifest ref) / PUT (upload encrypted manifest body to storage, update hash in DB).
- Verify RLS: user A cannot GET user B's manifest (test with two users).
- **Tests**: Round-trip manifest upload; cross-user isolation enforced.
- **Acceptance**: RLS enforced; manifest syncs; cross-user reads blocked.

#### Task 9.4 — Share Token Routes
**Deliverable**: CRUD for share tokens (create, verify, consume, revoke).
- `/api/shares` POST (create token, store wrapped key, expiry, max_uses) / GET (list own).
- `/api/shares/{id}` GET (public, verify signature + expiry) / DELETE (revoke).
- `/api/shares/{id}/consume` POST (increment uses; reject if over max or expired).
- **Tests**: Create→consume round-trip; expired → rejected; over-uses → rejected; revoke → 404.
- **Acceptance**: Token lifecycle enforced; expiry + use-limit correct.

#### Task 9.5 — Audit Log Routes
**Deliverable**: Append + query audit entries (hash chain verified client-side).
- `/api/audit` POST (append entry with `prev_hash`, `entry_hash`, `signature`) / GET (list own, paginated).
- `/api/audit/verify` POST (client sends chain; server stores but verification is client-side to avoid server forging).
- Admin: `/api/admin/audit` GET (all users, filtered).
- **Tests**: Append→list round-trip; tamper detection via client verify; admin sees all.
- **Acceptance**: Audit chain works; tamper detection client-side; admin access correct.

#### Task 9.6 — Rate Limiting + Request Validation
**Deliverable**: Rate limiting + Pydantic validation on all routes.
- Middleware: rate limit (per-user, per-IP) via Redis or in-memory LRU; 100 req/min default, stricter on auth.
- Pydantic schemas for all request/response bodies; reject unknown fields.
- Request-id propagation; structured JSON logs.
- **Tests**: Rate limit kicks in at 101st req; invalid schema → 422; log entries present.
- **Acceptance**: Rate limit enforced; validation strict; logs structured.

---

### Phase P10 — Storage Connectors (Week 12) — 7 Tasks

#### Task 10.1 — StorageConnector ABC + Mock Connector (`storage/base.py`)
**Deliverable**: Uniform storage interface + mock for testing.
- `StorageConnector` ABC: `authenticate()`, `upload(stream, remote_path)`, `download(remote_path) -> stream`, `list(prefix)`, `delete(remote_path)`, `stat(remote_path)`, `move(src, dst)`, `mkdir(path)`.
- Streams = file-like or generators (no full load by contract).
- `MockStorage` in-memory dict for unit tests.
- **Tests**: Mock round-trips all methods; streaming download yields chunks.
- **Acceptance**: ABC contract clear; mock enables pipeline tests without network.

#### Task 10.2 — Local Filesystem Connector (`storage/local.py`)
**Deliverable**: Local-disk connector with streaming + atomic move.
- `LocalStorage(root_path)`: maps remote paths to FS paths; streaming upload/download; atomic write (tmp + rename).
- **Tests**: Round-trip 100MB; nested dirs; move across dirs.
- **Acceptance**: Local connector works; streaming; atomic writes.

#### Task 10.3 — SFTP Connector (`storage/sftp.py`)
**Deliverable**: SFTP via Paramiko with streaming + key/password auth.
- `SftpStorage(host, port, username, key_path_or_password)`.
- Streaming via `SFTPClient.putfo/getfo`; connection pooling; reconnect on failure.
- **Tests**: Round-trip vs `atmoz/sftp` docker; key + password auth.
- **Acceptance**: Round-trips via SFTP; streaming; failures retried.

#### Task 10.4 — FTP Connector (`storage/ftp.py`)
**Deliverable**: FTP via stdlib `ftplib` with streaming + PASV.
- `FtpStorage(host, port, username, password)`: PASV, FTP-S if supported.
- Streaming via `storbinary`/`retrbinary`.
- **Tests**: Round-trip vs `vsftpd` docker.
- **Acceptance**: FTP round-trips; PASV used.

#### Task 10.5 — Google Drive Connector (`storage/cloud/gdrive.py`)
**Deliverable**: GDrive via `google-api-python-client` with OAuth + resumable upload.
- `GoogleDriveStorage`: OAuth via `google-auth`; scope `drive.file`.
- Resumable upload for ≥100MB; streaming download via `get_media`.
- Map paths to Drive file IDs; cache locally.
- **Tests**: OAuth dance; round-trip 50MB; resumable interrupted → resumes.
- **Acceptance**: OAuth works; 50MB round-trip; resumable upload.

#### Task 10.6 — OneDrive Connector (`storage/cloud/onedrive.py`)
**Deliverable**: OneDrive via Microsoft Graph API with OAuth + chunked upload.
- `OneDriveStorage`: OAuth via MSAL; Graph `/me/drive/items`.
- Chunked upload via `createUploadSession`; download via `/content`.
- **Tests**: OAuth dance; round-trip 50MB; resumable upload.
- **Acceptance**: OAuth works; 50MB round-trip; chunked upload.

#### Task 10.7 — Dropbox Connector + URI Auto-Detection (`storage/cloud/dropbox.py` + `storage/registry.py`)
**Deliverable**: Dropbox connector via SDK + URI scheme resolution for all connectors.
- `DropboxStorage`: OAuth2 via `dropbox` SDK; scope `files.content.readwrite`.
- Chunked upload via `upload_session/start→append→finish` for ≥150MB; streaming download via `download_iter`.
- `resolve_storage(uri) -> StorageConnector` parses `local://`, `sftp://`, `ftp://`, `gdrive://`, `onedrive://`, `dropbox://`.
- **Tests**: Dropbox round-trip 50MB; URI auto-detection for each scheme.
- **Acceptance**: Dropbox works; URI resolution unified; documented in `docs/storage_uris.md`.

---

### Phase P11 — Secure Sharing System (Week 13) — 6 Tasks

#### Task 11.1 — Encrypted Share Package Format (`sharing/package.py`)
**Deliverable**: Portable `.cvshare` package with ciphertext + wrapped key + signature + proof.
- `SharePackage`: `version`, `file_id`, `encrypted_key` (per-recipient), `ciphertext_ref`, `signature`, `merkle_root`, `manifest_fragment`.
- Serialize to JSON or CBOR.
- Single-file shares inline ciphertext; large files reference storage (recipient needs access).
- **Tests**: Round-trip; tamper ciphertext → verify fails; tamper signature → fails.
- **Acceptance**: Format stable; tamper detection; documented in `docs/share_format.md`.

#### Task 11.2 — One-Time Access Tokens (`sharing/token.py`)
**Deliverable**: Single-use tokens; invalid after first use.
- Token = signed random 256-bit nonce + expiry + file_id + use_count; stored in Supabase `share_tokens`.
- HMAC with master key; verify signature before granting; increment use_count.
- **Tests**: Valid → access; reuse → rejected; expired → rejected; tampered → rejected.
- **Acceptance**: One-time enforced; tamper/expiry handled.

#### Task 11.3 — Time-Limited Links (`sharing/timed_link.py`)
**Deliverable**: Links with expiry timestamp; verified server-side.
- Encode token + expiry in URL; signature prevents tampering.
- `verify_link(url) -> (valid, file_id, remaining_time)`.
- **Tests**: Valid within window; expired → rejected; tampered expiry → rejected.
- **Acceptance**: Time-limited enforced; tamper-resistant.

#### Task 11.4 — Password-Protected Sharing (`sharing/password.py`)
**Deliverable**: Share protected by user-chosen password.
- Sender: wrap share key with Argon2id-derived key from password; include salt + params.
- Recipient: enter password → Argon2id → unwrap share key → decrypt.
- **Tests**: Correct password → decrypt; wrong → fail; empty allowed.
- **Acceptance**: Password protection enforced; Argon2id tuning documented.

#### Task 11.5 — QR Code Share Generation (`sharing/qr.py`)
**Deliverable**: QR encoding share URL or compact package for offline sharing.
- `qrcode` lib; encode URL (timed link) or compact package (small keys ≤2KB).
- Print ASCII to terminal or save PNG.
- **Tests**: Generate → decode → match; size limits documented.
- **Acceptance**: QR round-trips; ASCII + PNG output.

#### Task 11.6 — Invitation Share (Public-Key Recipient) (`sharing/invitation.py`)
**Deliverable**: Invite recipient by their public key; only they can decrypt.
- Sender wraps share key with Hybrid KEM (X25519+Kyber for PQ-share).
- Package includes per-recipient wrapped key; multiple recipients supported.
- **Tests**: Recipient with matching key → decrypt; wrong key → fail; multiple recipients each decrypt.
- **Acceptance**: Invitation enforced; multi-recipient works; PQ-hybrid for MAX profile.

---

### Phase P12 — Web Client (WASM Crypto) (Week 14) — 5 Tasks

#### Task 12.1 — WASM Crypto Build Pipeline
**Deliverable**: Python core compiled to WASM, loadable in browser.
- Use Pyodide or PyScript to package `packages/core` → `packages/wasm/cryptavault.wasm`.
- Verify `oqs-wasm` (post-quantum primitives) loads and runs Kyber/Dilithium in browser.
- Expose async JS API: `import { encrypt, decrypt, sign, verify, kem_encapsulate } from 'cryptavault-wasm'`.
- **Tests**: Node smoke test imports WASM, runs AES-256-GCM round-trip, Kyber KEM round-trip.
- **Acceptance**: WASM loads in browser; PQ primitives work in browser; JS API documented.

#### Task 12.2 — Web Client Scaffold (React + Vite + Tailwind)
**Deliverable**: React app with auth + routing + Supabase client.
- Vite + React + TypeScript + Tailwind; `@supabase/supabase-js` client.
- `wouter` for routing: `/login`, `/dashboard`, `/files`, `/shares`, `/benchmarks`, `/profile`.
- Auth gate: redirect to `/login` if no session; session via Supabase.
- **Tests**: Render login page; auth flow with email/pw; dashboard renders placeholder.
- **Acceptance**: App boots; auth flow works; routing correct.

#### Task 12.3 — Browser Crypto Wrappers + Key Vault
**Deliverable**: JS-friendly async wrappers around WASM crypto + browser key vault.
- `src/crypto/index.ts`: `encryptFile(file, profile)`, `decryptFile(blob, profile)`, `signFile`, `verifyFile`, `kemEncapsulate`.
- Key vault: master key derived in WASM from password (Argon2id); stored decrypted in memory only; persisted encrypted in `localStorage` via `keystore` module.
- Streaming: chunk file via `Blob.slice` + `ReadableStream`; encrypt chunks with WASM; assemble.
- **Tests**: Encrypt 100MB file in browser; memory bounded; decrypt round-trips.
- **Acceptance**: Browser crypto works; memory < 200MB on 1GB; keys never leave browser.

#### Task 12.4 — Upload/Download/Share UI
**Deliverable**: React UI for upload (with progress), download, share flow.
- Upload: drag-drop or file picker → WASM encrypt → chunked upload to storage connector (via API-signed URL).  Progress bar + cancel.
- Download: list files from manifest → WASM decrypt → save.
- Share: dialog with options (QR, time limit, password, recipient pubkey).
- **Tests**: Manual E2E: upload 50MB encrypted file → appears in list → download → decrypts → bytes match original.
- **Acceptance**: Full round-trip in browser; progress + cancel work; share dialog functional.

#### Task 12.5 — Browser Performance Dashboard Widgets
**Deliverable**: Live metrics during browser encrypt/upload (speed, CPU, memory, profile).
- `PerformanceObserver` + `performance.memory` (Chrome) for metrics; stream via SSE or poll `/api/metrics` (server reports storage-side speed).
- Charts via `recharts` (small bundle) or pure SVG.
- Profile slider with algorithm matrix display.
- **Tests**: Metrics render during 100MB upload; slider updates; values sane.
- **Acceptance**: Live metrics visible; slider works; charts readable.

---

### Phase P13 — Admin Console (React SPA) (Week 14) — 5 Tasks

#### Task 13.1 — Admin Scaffold (React + shadcn/ui + Vite)
**Deliverable**: Admin SPA scaffold with RBAC-protected routing.
- Vite + React + TypeScript + Tailwind + `shadcn/ui` (Button, DataTable, Dialog, Tabs, Form, Card).
- Auth: separate Supabase Auth call with admin role check; admin cookie scope `admin.cryptavault.app`.
- Routing: `/admin/dashboard`, `/admin/users`, `/admin/sessions`, `/admin/providers`, `/admin/audit`, `/admin/flags`, `/admin/health`, `/admin/reports`.
- **Tests**: Login as admin → dashboard renders; login as user → 403.
- **Acceptance**: Admin isolated; RBAC enforced; scaffold renders.

#### Task 13.2 — User Management Feature
**Deliverable**: User list + suspend/delete/quota edit + impersonation.
- `DataTable` with search, sort, filter (role, suspended, created_at).
- Row actions: Suspend (set `suspended=true`), Delete (cascade via Supabase), Edit Quota (prompt), Impersonate (generate short-lived admin-signed token; audit log entry).
- Detail drawer: profile, storage usage, active sessions, recent audit entries.
- **Tests**: Suspend → user cannot login; edit quota → persists; impersonation → audit entry.
- **Acceptance**: CRUD works; impersonation audited; RLS-enforced.

#### Task 13.3 — Audit Log + Sessions + Providers
**Deliverable**: Audit log viewer (filterable + export), session revoke, provider credentials admin.
- Audit: `DataTable` with filters (user, operation, date range, outcome); export CSV; show hash chain verify status.
- Sessions: list active sessions per user; revoke (invalidate JWT cookie server-side).
- Providers: list configured storage providers (GDrive, Dropbox, OneDrive) + add/remove org-wide credentials.
- **Tests**: Filter audit by user → only their entries; revoke session → user re-logged; add provider credential → persists.
- **Acceptance**: Audit filtered/exported; sessions revocable; providers editable.

#### Task 13.4 — Feature Flags + System Health + Reports
**Deliverable**: Feature flag toggles, system health dashboard, analytics reports.
- Flags: list (`enable_pq`, `enable_passkeys`, `enable_sharing`, `maintenance_mode`); toggle on/off; impact immediate via API middleware check.
- Health: Supabase DB status, API latency p50/p95, queue depth, storage provider reachability (ping).
- Reports: signups per day (line chart), encrypt ops per day (bar), storage used (area), benchmark aggregates across users (table).
- Charts via `recharts`.
- **Tests**: Toggle flag → API rejects PQ operations when off; health reflects DB down; reports render with mock data.
- **Acceptance**: Flags actionable; health live; reports interactive.

#### Task 13.5 — Admin API Serverside Enforcement
**Deliverable**: Server endpoints enforcing admin-only access on all admin routes.
- `/api/admin/*` routes all gated by `get_admin_user()` dependency.
- Impersonation: `/api/admin/impersonate/{user_id}` issues short-lived (10-min) admin-signed token that the API accepts as that user (with `impersonated_by` audit field).
- Rate limit admin endpoints stricter (30 req/min).
- **Tests**: User token → 403 on admin routes; admin token → 200; impersonated token → works + audit log shows `impersonated_by`.
- **Acceptance**: Admin-only enforced; impersonation audited; rate-limited.

---

### Phase P14 — Dashboard + Benchmark Lab (Week 15) — 5 Tasks

#### Task 14.1 — Benchmark Lab Comparative Suite (`benchmark/suite.py`)
**Deliverable**: Benchmark all algorithms (AES, ChaCha20, RSA, ECC, Kyber, Dilithium, hybrid) across metrics.
- Each benchmark: encrypt/sign N bytes or M iterations; measure time, CPU, memory, key size, sig size.
- Parameterize: payload sizes (1KB, 1MB, 100MB, 1GB), iteration counts.
- Export CSV + JSON to `benchmarks/` directory.
- **Tests**: Benchmark suite completes in ≤10 min; results sane (AES faster than RSA; Kyber faster than RSA-4096).
- **Acceptance**: Full suite runs; CSV/JSON exported; academically useful comparison.

#### Task 14.2 — Benchmark Lab Web UI (`packages/admin/features/benchmarks/`)
**Deliverable**: Admin + user page rendering benchmark results as charts.
- Bar charts: encryption speed per algo (MB/s), key size (bytes), sig gen/verify time (ms).
- Tables: usability rating (AES vs ChaCha on mobile vs server, RSA vs ECC vs Dilithium).
- Use `recharts`; load JSON from `/api/benchmark`.
- **Tests**: Manual verification; charts render; data matches CSV.
- **Acceptance**: Charts readable; comparison clear; suitable for report screenshots.

#### Task 14.3 — Live Performance Metrics (SSE)
**Deliverable**: Real-time metrics stream for upload speed, CPU, RAM, encryption speed.
- `MetricsCollector`: subscribes to pipeline orchestrator events; emits metrics every 1s.
- SSE endpoint `/api/metrics/stream` pushes JSON events.
- Frontend HTMX `hx-sse` OR React `EventSource` updates DOM live.
- **Tests**: Metrics flow; SSE delivers; CPU/RAM via `psutil` (server) or `performance.memory` (browser).
- **Acceptance**: Dashboard updates live during 1GB encrypt+upload; ≤2s latency.

#### Task 14.4 — Performance Dashboard Page (User-Facing)
**Deliverable**: HTMX/Tailwind page showing live metrics + profile selector.
- Cards: current profile + algorithm matrix, live speed graph, CPU/RAM gauges, compression ratio, security level badge.
- Profile slider control calls `/api/profile` to update.
- Job queue table with status badges.
- **Tests**: Manual visual verification; slider persists; live updates during operation.
- **Acceptance**: Dashboard renders; slider works; live metrics visible.

#### Task 14.5 — Estimated Brute-Force Resistance Indicator
**Deliverable**: Security-level badge estimating classical + PQ resistance.
- Each algo maps to bits of security (AES-128 → 128, AES-256 → 256, RSA-4096 → ~140, Kyber768 → 192, Dilithium3 → 192).
- Display "Classical: N bits · Post-Quantum: M bits"; color badge (green ≥192, yellow 128, red <128).
- Include rough year-of-security estimate (NIST levels 1/3/5).
- **Tests**: Badge updates with profile; values correct per NIST guidelines.
- **Acceptance**: Badge visible; values honest; documented in `research/notes/security_levels.md`.

---

### Phase P15 — AI Security Assistant (Week 15) — 4 Tasks

#### Task 15.1 — Rule-Based Heuristic Recommender (`ai/rules.py`)
**Deliverable**: Deterministic advisory engine analyzing file metadata → recommends crypto/compression/storage.
- Rules:
  - File type ∈ {JPEG, MP4, ZIP} → skip compression.
  - File size > 10GB → AES-256-GCM (fast, parallel) + chunked + skip compress.
  - File type == TEXT and size < 100MB → zstd compress.
  - Profile == MAXIMUM and filename pattern {key, wallet, seed} → multi-layer + FS ratchet + full audit.
  - VM image (>1GB, compressed) → skip compress, AES-256-GCM parallel, large chunks.
- Output `Recommendation {encryption_algo, compression_mode, chunk_size, parallel_workers, rationale_text}`.
- **Tests**: 15 known scenarios produce expected recommendations; rationale explains each choice.
- **Acceptance**: Recommender correct; rationale human-readable.

#### Task 15.2 — Optional LLM Provider Interface (`ai/llm.py`)
**Deliverable**: Pluggable LLM (OpenAI or Anthropic) for natural-language explanations.
- `AiProvider` ABC: `recommend(metadata)`, `explain(concept)`, `analyze_upload(metadata)`.
- `OpenAiProvider` and `AnthropicProvider` via their SDKs.
- **Critical**: data minimization — only send file_type, size, profile, requested concept; NEVER plaintext, keys, contents, names.
- Prompt template enforced: "You are a crypto advisory assistant. Explain concept: X. Do not request sensitive data."
- **Tests**: Mock LLM returns canned response; data-minimization unit test (no file content in request body).
- **Acceptance**: LLM pluggable; data minimization enforced by code; documented in `docs/ai_data_minimization.md`.

#### Task 15.3 — AI Assistant Chat Endpoint
**Deliverable**: `/api/ai/chat` accepts question → routes rule-based or LLM.
- Concept explanation → LLM (if configured) or static knowledge base fallback.
- "Analyze this upload" → `recommendation` from rule-based; user confirms to apply.
- "Apply recommendation" endpoint updates profile/config.
- **Tests**: "explain AES-GCM" → LLM/static response; "what compression for 20GB VM image?" → rule-based.
- **Acceptance**: Chat endpoint works; recommendation→apply loop clean.

#### Task 15.4 — Static Knowledge Base Fallback (`ai/knowledge_base.py`)
**Deliverable**: Offline concept explanations for when LLM not configured.
- Curated entries: AES-GCM, ChaCha20-Poly1305, RSA vs ECC, Kyber, Dilithium, Argon2id, forward secrecy, zero-knowledge storage, Merkle trees, AEAD, KDF, hybrid encryption.
- Each: concept name, short explanation, when-to-use, security level, performance note.
- **Tests**: Known concept → entry found; unknown → "configure LLM for richer explanations".
- **Acceptance**: Fallback useful offline; >20 concepts; cited academically.

---

### Phase P16 — Integration, Polish & Report (Week 16) — 5 Tasks

#### Task 16.1 — End-to-End Test Matrix
**Deliverable**: E2E tests covering profiles × providers × operations × clients.
- Matrix:
  - Profiles: PERFORMANCE, STANDARD, STRONG, MAXIMUM (4).
  - Storage: Local, SFTP, Mock-Cloud (3) [skip real OAuth in CI].
  - Clients: CLI, Web (WASM), Admin.
  - Operations: upload, download, verify, share, sign, integrity.
- ≥ 4 × 3 × 3 × 6 = 216 scenarios via `pytest.mark.parametrize`.
- 1GB + 10KB test files.
- **Acceptance**: All scenarios pass; matrix documented.

#### Task 16.2 — CLI Polish & Documentation
**Deliverable**: Complete CLI command set with help + docs.
- Commands: `init`, `upload`, `download`, `verify`, `share`, `receive`, `keys {generate,rotate,backup,recover,import,export,list}`, `profile {set,get,list}`, `benchmark run --all`, `dashboard`.
- `rich` for tables + progress bars.
- **Tests**: `--help` per command; smoke test each.
- **Acceptance**: All commands work; help complete; `docs/cli.md` generated.

#### Task 16.3 — Number Theory Research Annotations (`research/`)
**Deliverable**: Written notes + annotated reference implementations supporting the report.
- Topics (annotated minimal impls + 1-2 page notes each): see `RESEARCH.md` for full list.
- **Acceptance**: All topics have annotated notes; academically cited; supports report.

#### Task 16.4 — Final Report (`docs/REPORT.md`)
**Deliverable**: Comprehensive project report.
- Sections: Abstract, Introduction, Literature Review, Architecture, Algorithms (classical + PQ), Security Analysis, Performance Benchmarks, Implementation Details, Testing, AI Assistant, Limitations & Future Work, Conclusion, References.
- Include threat model + zero-knowledge proofs + FS approximation + secure deletion limits.
- Embed benchmark charts + screenshots.
- **Acceptance**: Report complete; benchmarks embedded; citations present.

#### Task 16.5 — Demo Script & Release Tag
**Deliverable**: Reproducible demo script + tagged release.
- Demo: init → upload 1GB (MAXIMUM) → dashboard live → share via QR → receive + verify → benchmark lab output.
- Tag `v1.0.0`; `CHANGELOG.md`; final README with quickstart + screenshots + architecture diagram.
- **Acceptance**: Demo reproducible; tag clean; README polished.

---

## 6. Verification & Academic Rigor

- KAT tests for every primitive (NIST, Wycheproof, RFC test vectors).
- Property-based tests (Hypothesis) for round-trips: encrypt→decrypt, sign→verify, compress→decompress, Merkle build→proof→verify.
- Benchmark Lab produces CSV/JSON + charts for the report (encryption speed, key size, sig gen/verify time, CPU/mem).
- Comparative table: classical vs hybrid vs PQ (security level, performance cost).
- E2E scenario: encrypt 1 GB + 20 GB files across 3 profiles × 3 providers × 3 clients, capture dashboard screenshots.
- Zero-knowledge proof: network capture confirms no plaintext/keys traverse backend (demonstrate at demo).

## 7. Risk Summary (See RISKS.md for detail)

- **liboqs build failure** → Docker dev container fallback.
- **WASM perf / oqs-wasm availability** → Native CLI fallback for PQ; web client uses classical unless oqs-wasm available.
- **OAuth approval delays** → Mock connectors first; test-mode apps.
- **Secure deletion impossibility** → Document honestly; best-effort only.
- **Forward secrecy approximation** → Document as ratcheted per-file keys, cite Signal Double Ratchet.
- **LLM data-minimization leak** → Enforce by code (allowlist); unit test no-leak.

## 8. Milestone Gates

| Gate | Week | Criteria |
|------|------|----------|
| Setup | 1 | liboqs works, repo scaffolded, OAuth creds obtained, Supabase project provisioned |
| Crypto Core | 3 | Classical primitives pass all KATs |
| PQ Integrated | 4 | Kyber + Dilithium round-trip; hybrid KEM works |
| Integrity | 5 | Merkle + signatures verify tamper across 1000 leaves |
| KMS | 6 | Generate/rotate/backup/recover/destroy all work |
| Engine | 7 | 5 profiles resolve to correct configs |
| Compression | 8 | 4 algorithms stream + skip policy works |
| Pipeline | 9 | 1GB file E2E through orchestrator |
| Metadata | 10 | Encrypted manifest round-trips |
| API + Auth | 11 | Supabase Auth + FastAPI routes + RLS verified |
| Storage | 12 | 5 connectors round-trip 50MB |
| Sharing | 13 | QR + token + password + invitation shares work |
| Web Client | 14 | Browser crypto round-trips 100MB; keys stay in browser |
| Admin | 14 | Admin SPA CRUD + RBAC enforced |
| Dashboard + Bench | 15 | Live metrics + benchmark charts render |
| AI | 15 | Recommender + optional LLM work; no data leak |
| Release | 16 | Demo reproducible; report complete; tag v1.0.0 |

## 9. File Index

| File | Purpose |
|------|---------|
| `PLAN.md` (this file) | Master plan: 74 tasks, 17 phases, 16 weeks |
| `ROADMAP.md` | Phase timeline + dependency graph |
| `ARCHITECTURE.md` | API + WASM + Supabase + Admin architecture |
| `RISKS.md` | Risks, assumptions, mitigations |
| `RESEARCH.md` | Number theory + crypto research deliverables |
| `SRS.md` | Software Requirements Specification |
| `docs/phase-00-bootstrap.md` → `phase-16-integration-report.md` | Per-phase specs (17 files) |

---

_End of PLAN.md_