# CryptaVault — Architecture

## 1. High-Level Architecture

CryptaVault enforces a strict **zero-knowledge boundary**: cryptographic keys never leave the client device, file encryption happens client-side, and the backend (API + Supabase + storage providers) only ever sees ciphertext and encrypted metadata.

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

## 2. Zero-Knowledge Boundary (Critical Invariant)

The zero-knowledge boundary is enforced at the **client**:

1. **Encryption keys** are generated, stored, and used entirely in the browser (WebAssembly) or on the local device (CLI). Keys never traverse the network in plaintext.
2. **File encryption** happens client-side. The API server only ever receives ciphertext + encrypted manifests.
3. **The API server + Supabase** coordinate accounts, share tokens, audit logs, and orchestration — but cannot decrypt user files (no keys stored server-side in the database).
4. **Supabase Auth** manages identity, but the user's master key is derived from their password via Argon2id **in the browser**, not on the server. The server only sees Supabase's auth hash (Supabase's responsibility) and the encrypted key manifest.
5. **The admin console** can manage users, view audit logs, toggle feature flags — but **cannot** read user files (no key access).

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Storage provider reads plaintext | Client-side encryption; provider sees only ciphertext |
| Backend server compromised | No keys stored server-side; manifests encrypted with client-derived key |
| Database (Supabase) breached | RLS isolates users; manifests + tokens encrypted; no plaintext keys |
| MITM on network | TLS 1.3; HSTS; certificate pinning (admin) |
| Admin impersonates user | Impersonation audited; short-lived tokens; admin role required |
| LLM leaks user data | Data minimization: only metadata (type, size, mode) sent to LLM |
| OAuth provider compromise | Token rotation; minimal scopes; revoke on detection |
| Password brute-force | Argon2id (memory-hard); rate limiting; 2FA via passkeys |

## 3. Monorepo Layout

```
CryptaVault/
├── packages/
│   ├── core/                     # Python crypto core (also ships to WASM)
│   │   └── cryptavault/
│   │       ├── crypto/           # symmetric, asymmetric, pq, hybrid, hash, kdf
│   │       ├── signatures/       # ECDSA, Ed25519, Dilithium, hybrid
│   │       ├── integrity/        # per-file hash, Merkle trees
│   │       ├── keys/             # KMS: hierarchy, keystore, rotate, backup
│   │       ├── adaptive/         # Security profiles + engine
│   │       ├── compression/      # detect, policy, algorithms
│   │       ├── pipeline/         # chunked, parallel, resume, queue, orchestrator
│   │       ├── metadata/         # encrypted manifest, secure delete
│   │       ├── sharing/          # packages, tokens, QR, invitation
│   │       ├── storage/          # connector ABC + impls (local, sftp, cloud)
│   │       ├── plugins/          # registry + interfaces
│   │       ├── benchmark/        # crypto benchmark lab
│   │       └── ai/               # rules + llm
│   ├── api/                      # FastAPI backend
│   │   └── cryptavault_api/
│   │       ├── auth/             # Supabase Auth integration, JWT verify
│   │       ├── routes/           # users, keys, shares, audit, benchmarks, ai, admin
│   │       ├── middleware/       # RBAC, rate limit, request id
│   │       ├── models/           # Pydantic schemas + ORM
│   │       ├── deps/             # Supabase client, current_user
│   │       └── main.py
│   ├── web/                      # React web client (user-facing dashboard)
│   │   └── src/
│   │       ├── crypto/           # WASM loader, async crypto wrappers
│   │       ├── components/       # upload, download, share, dashboard widgets
│   │       ├── pages/            # dashboard, files, shares, benchmarks, profile
│   │       └── lib/              # supabase client, api client
│   ├── admin/                    # React admin console (shadcn/ui)
│   │   └── src/
│   │       ├── features/         # users, sessions, providers, audit, flags, health
│   │       ├── components/       # data tables, charts, dialogs, filters
│   │       └── lib/              # admin api client, rbac checks
│   ├── wasm/                     # Build config to compile core/ → WASM
│   │   └── build.sh              # Pyodide/PyScript packaging
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

## 4. Data Flow

```
User Input (file, storage target, profile)
     │
     ▼
┌─────────────────┐
│ AI Advisory     │ ← metadata only (type, size, profile)
│ (rules + LLM)   │   → recommendation
└────────┬────────┘
         │ (user confirms)
         ▼
┌─────────────────┐
│ Adaptive Engine  │ ← profile + file metadata
│ → PipelineConfig│   → resolved algorithms + chunk size + workers
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ PIPELINE ORCHESTRATOR (streaming)        │
│  ┌──────────────┐                        │
│  │ Compression  │ ← skip policy          │
│  └──────┬───────┘                        │
│         ▼                                │
│  ┌──────────────┐                        │
│  │ Chunked      │ ← parallel workers     │
│  │ Encryption   │   (AES/ChaCha/multi)   │
│  └──────┬───────┘                        │
│         ▼                                │
│  ┌──────────────┐                        │
│  │ Signature    │ ← Ed25519/Dilithium    │
│  └──────┬───────┘                        │
│         ▼                                │
│  ┌──────────────┐                        │
│  │ Integrity    │ ← BLAKE3 + Merkle      │
│  └──────┬───────┘                        │
│         ▼                                │
│  ┌──────────────┐                        │
│  │ Metadata     │ ← encrypted manifest   │
│  └──────┬───────┘                        │
└─────────┼────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Storage         │ ← ciphertext + encrypted manifest only
│ Connector       │   (Local / SFTP / FTP / Cloud)
└────────┬────────┘
         │
         ▼
    Storage Provider
    (never sees plaintext)
```

## 5. Database Schema (Supabase / PostgreSQL)

```sql
-- supabase/migrations/0001_init.sql

-- Extends auth.users with app-specific fields
create table public.profiles (
  uid          uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  role         text not null default 'user' check (role in ('user','admin','auditor')),
  quota_bytes  bigint not null default 5368709120,  -- 5 GB default
  suspended    boolean not null default false,
  created_at   timestamptz not null default now()
);

-- Encrypted key manifests (plaintext keys NEVER stored)
create table public.key_manifests (
  user_id           uuid not null references public.profiles(uid) on delete cascade,
  encrypted_manifest bytea not null,              -- AES-256-GCM encrypted KeyTree JSON
  manifest_nonce    bytea not null,               -- GCM nonce
  manifest_hash     text not null,               -- BLAKE3 of plaintext manifest (for integrity)
  updated_at        timestamptz not null default now(),
  primary key (user_id)
);

-- Share tokens (one-time / time-limited / password-protected)
create table public.share_tokens (
  token_id      uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references public.profiles(uid) on delete cascade,
  file_ref      text not null,                    -- storage URI of ciphertext
  wrapped_key   bytea not null,                   -- recipient-wrapped share key
  expires_at    timestamptz,                      -- null = no expiry
  max_uses      int not null default 1,
  current_uses  int not null default 0,
  password_hash text,                            -- Argon2id hash if password-protected (null otherwise)
  created_at    timestamptz not null default now()
);

-- Tamper-evident audit log (hash-chained)
create table public.audit_log (
  id          bigserial primary key,
  user_id     uuid references public.profiles(uid) on delete cascade,
  operation   text not null,                      -- 'encrypt','decrypt','share','rotate', etc.
  target      text,                               -- file_id or key_id
  metadata    jsonb,                              -- additional context
  prev_hash   text not null,                      -- hash of previous entry
  entry_hash  text not null,                      -- hash of this entry
  signature   bytea not null,                     -- signed by user master key
  created_at  timestamptz not null default now()
);

-- Benchmark results
create table public.benchmark_results (
  id          bigserial primary key,
  user_id     uuid references public.profiles(uid) on delete set null,
  algorithm   text not null,                      -- 'AES-256-GCM','Kyber768', etc.
  metric      text not null,                      -- 'encrypt_mbps','key_size_bytes', etc.
  value       double precision not null,
  created_at  timestamptz not null default now()
);

-- Feature flags
create table public.feature_flags (
  flag        text primary key,                   -- 'enable_pq','enable_passkeys', etc.
  enabled     boolean not null default true,
  description text
);

-- Sessions for impersonation tracking
create table public.sessions (
  session_id      uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(uid),
  impersonated_by uuid references public.profiles(uid),  -- null unless impersonated
  issued_at       timestamptz not null default now(),
  expires_at     timestamptz not null,
  revoked        boolean not null default false
);
```

### Row Level Security (RLS)

```sql
-- supabase/migrations/0002_rls.sql

alter table public.profiles enable row level security;
alter table public.key_manifests enable row level security;
alter table public.share_tokens enable row level security;
alter table public.audit_log enable row level security;
alter table public.benchmark_results enable row level security;
alter table public.sessions enable row level security;

-- Profiles: users see themselves; admins see all
create policy "users_select_own_profile" on public.profiles
  for select using (auth.uid() = uid);
create policy "users_update_own_profile" on public.profiles
  for update using (auth.uid() = uid);
create policy "admin_all_profiles" on public.profiles
  for all using (
    exists (select 1 from public.profiles p where p.uid = auth.uid() and p.role = 'admin')
  );

-- Key manifests: only owner can read/update
create policy "owner_manifest" on public.key_manifests
  for all using (auth.uid() = user_id);

-- Share tokens: owner CRUD; anyone with valid token can consume (verified server-side)
create policy "owner_share_tokens" on public.share_tokens
  for all using (auth.uid() = owner_id);

-- Audit log: owner read; admin read all
create policy "owner_audit_read" on public.audit_log
  for select using (auth.uid() = user_id);
create policy "admin_audit_read" on public.audit_log
  for select using (
    exists (select 1 from public.profiles p where p.uid = auth.uid() and p.role = 'admin')
  );

-- Benchmark results: owner + admin
create policy "owner_benchmark" on public.benchmark_results
  for select using (auth.uid() = user_id or user_id is null);
create policy "admin_benchmark" on public.benchmark_results
  for all using (
    exists (select 1 from public.profiles p where p.uid = auth.uid() and p.role = 'admin')
  );

-- Sessions: owner + admin
create policy "owner_sessions" on public.sessions
  for select using (auth.uid() = user_id);
create policy "admin_sessions" on public.sessions
  for select using (
    exists (select 1 from public.profiles p where p.uid = auth.uid() and p.role = 'admin')
  );
```

## 6. API Surface (FastAPI)

| Method | Path | Scope | Purpose |
|--------|------|-------|---------|
| GET | `/health` | public | Health check |
| GET | `/ready` | public | DB ping |
| GET | `/api/auth/session` | public | Exchange Supabase token → app session cookie |
| GET | `/api/auth/me` | user | Current user profile + role |
| POST | `/api/auth/logout` | user | Invalidate session |
| GET/PATCH | `/api/users/me` | user | Profile read/update |
| GET/PUT | `/api/users/me/manifest` | user | Encrypted key manifest sync |
| POST | `/api/shares` | user | Create share token |
| GET | `/api/shares` | user | List own shares |
| GET/DELETE | `/api/shares/{id}` | user/public | Get/revoke share |
| POST | `/api/shares/{id}/consume` | public | Consume use |
| POST | `/api/audit` | user | Append audit entry |
| GET | `/api/audit` | user | List own audit entries |
| POST | `/api/audit/verify` | user | Verify hash chain |
| GET | `/api/benchmark` | user | List benchmark results |
| POST | `/api/benchmark/run` | user | Trigger benchmark |
| GET | `/api/metrics/stream` | user | SSE live metrics |
| POST | `/api/ai/chat` | user | AI assistant chat |
| POST | `/api/ai/recommend` | user | Get recommendation |
| POST | `/api/ai/explain` | user | Explain concept |
| GET/PUT | `/api/profile` | user | Get/set security profile |
| GET/POST/DELETE | `/api/admin/users` | admin | User CRUD |
| POST | `/api/admin/impersonate/{id}` | admin | Impersonate user |
| GET | `/api/admin/audit` | admin | All audit entries (filtered) |
| POST | `/api/admin/sessions/{id}/revoke` | admin | Revoke session |
| GET/POST/PATCH | `/api/admin/providers` | admin | Storage provider credentials |
| GET/PUT | `/api/admin/flags` | admin | Feature flags |
| GET | `/api/admin/health` | admin | System health (DB, queue, providers) |
| GET | `/api/admin/reports/signups` | admin | Signup analytics |
| GET | `/api/admin/reports/operations` | admin | Encrypt ops analytics |
| GET | `/api/admin/reports/storage` | admin | Storage usage analytics |

## 7. Plugin Interface Contracts

```python
# packages/core/cryptavault/plugins/registry.py

class StorageConnector(ABC):
    @abstractmethod
    def authenticate(self) -> None: ...
    @abstractmethod
    def upload(self, stream: BinaryIO, remote_path: str) -> None: ...
    @abstractmethod
    def download(self, remote_path: str) -> BinaryIO: ...
    @abstractmethod
    def list(self, prefix: str = "") -> list[RemoteFile]: ...
    @abstractmethod
    def delete(self, remote_path: str) -> None: ...
    @abstractmethod
    def stat(self, remote_path: str) -> RemoteStat: ...
    @abstractmethod
    def move(self, src: str, dst: str) -> None: ...
    @abstractmethod
    def mkdir(self, path: str) -> None: ...

class CompressionAlgorithm(ABC):
    name: str
    @abstractmethod
    def compress(self, stream: BinaryIO) -> BinaryIO: ...
    @abstractmethod
    def decompress(self, stream: BinaryIO) -> BinaryIO: ...

class EncryptionAlgorithm(ABC):
    key_size_bytes: int
    nonce_size_bytes: int
    @abstractmethod
    def encrypt(self, key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes: ...
    @abstractmethod
    def decrypt(self, key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes: ...

class HashAlgorithm(ABC):
    name: str
    @abstractmethod
    def digest(self, data: bytes, size: int | None = None) -> bytes: ...
    @abstractmethod
    def streaming(self) -> 'StreamingHash': ...

class SignatureAlgorithm(ABC):
    @abstractmethod
    def keypair(self) -> tuple[bytes, bytes]: ...
    @abstractmethod
    def sign(self, private_key: bytes, message: bytes) -> bytes: ...
    @abstractmethod
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool: ...

class KemAlgorithm(ABC):
    @abstractmethod
    def keypair(self) -> tuple[bytes, bytes]: ...
    @abstractmethod
    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]: ...
    @abstractmethod
    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes: ...

class KdfAlgorithm(ABC):
    @abstractmethod
    def derive(self, password: bytes, salt: bytes, length: int, **params) -> bytes: ...

class AiProvider(ABC):
    @abstractmethod
    def recommend(self, file_metadata: dict) -> dict: ...
    @abstractmethod
    def explain(self, concept: str) -> str: ...
```

## 8. Security Profiles (Adaptive Engine)

| Profile | % | Symmetric | Asym/KEM | Sig | Hash | KDF | Compress | Metadata Enc | FS | Audit |
|---------|---|-----------|----------|-----|------|-----|----------|--------------|-----|-------|
| PERFORMANCE | 0–20 | AES-128-GCM | X25519 | ECDSA-P256 | SHA-256 | PBKDF2 | fast | no | no | no |
| STANDARD | 20–50 | AES-256-GCM | X25519 | ECDSA-P256 | SHA-256 | Argon2id | smart | yes | no | no |
| BALANCED | 35–65 | AES-256-GCM | X25519 | Ed25519 | SHA-256 | Argon2id | smart | yes | opt | opt |
| STRONG | 50–80 | AES-256 + ChaCha20 | X25519 | Ed25519 | SHA-256 | Argon2id | smart | yes | opt | opt |
| MAXIMUM | 80–100 | AES-256 + ChaCha20 | Hybrid (X25519+Kyber768) | Hybrid (Ed25519+Dilithium3) | SHA3-512/BLAKE3 | Argon2id | full | yes | yes | yes |

## 9. Deployment Topology

| Component | Hosting | Notes |
|-----------|---------|-------|
| FastAPI API | Render / Railway / Fly.io | Worker process for queue |
| Supabase (Postgres + Auth) | Supabase managed | RLS enforced |
| React Web Client (user) | Vercel | `app.cryptavault.app` |
| React Admin Console | Vercel | `admin.cryptavault.app` (separate subdomain) |
| Storage backends | User-chosen (Local/SFTP/Cloud) | Framework abstracts via connectors |
| Cloudflare R2 | Framework's own backup storage | For "framework-managed" option |
| Background workers (queue) | Same host as FastAPI or separate worker dyno | Persisted queue state |

## 10. Key Design Principles

1. **Plugin-first**: Every pluggable component (storage, compression, encryption, hash, signature, KDF, AI) uses the same registry pattern. No core module imports a specific implementation directly — all go through the registry.
2. **Stream-everywhere**: No stage of the pipeline holds the full file in memory. Streams flow chunk-by-chunk from source through compression, encryption, signing, integrity, to storage.
3. **Zero-knowledge boundary**: Storage connectors + API + DB receive only ciphertext + encrypted manifests. Plaintext, keys, and unencrypted metadata never cross the storage connector or API interface.
4. **Profile-driven**: All algorithm choices resolve at runtime from the user's security profile, not hardcoded. Profiles map to plugin instances via the registry.
5. **Fail-closed**: Every verification (tag, signature, hash, token, integrity) rejects on mismatch — never returns partial or default-decrypted data.
6. **Academic-grade**: Every primitive has KAT tests + property tests; benchmarks produce data for the report; research annotations explain the "why" behind each design.
7. **Honest limitations**: Secure deletion, forward secrecy, and other impossibilities are documented honestly, not claimed falsely.

---

_End of ARCHITECTURE.md_