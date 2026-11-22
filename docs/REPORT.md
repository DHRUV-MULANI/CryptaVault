# CryptaVault: An Adaptive Hybrid Zero-Knowledge Cryptographic Storage Framework

**Project Technical Report — Dynamic Stack, Version 2.0.0**  
**Author / Engineering Team**: CryptaVault Core Team  
**Date**: November 2026  
**Repository**: `CryptaVault` monorepo — Python core, FastAPI backend, React web client, Typer CLI, admin console scaffold

---

## 1. Abstract

Cloud storage normally trusts the provider with either plaintext or server-held encryption keys. CryptaVault removes that trust requirement for file contents and file metadata. The client derives a master key from the user's passphrase, generates a fresh per-file key for every upload or version, encrypts chunks with authenticated encryption, seals the metadata manifest, and sends only ciphertext and wrapped keys to the backend.

The current dynamic deployment is a complete local full-stack application:

- React + Vite browser client using Web Crypto
- FastAPI coordination API
- Neon Postgres metadata, identity, roles, shares, quotas, and policy
- S3-compatible ciphertext storage, demonstrated with SeaweedFS
- Typer remote CLI that produces and consumes the same wire format as the browser

The original Python cryptographic engine remains available for offline use. It adds the `CVV2` pipeline, catalog-selected primitives, Merkle integrity roots, Ed25519 and hybrid post-quantum signatures, key recovery, storage connectors, benchmarking, and advisory tooling. The dynamic web/remote path uses a portable `CVW1` subset so that a file uploaded in the browser can be downloaded and decrypted from the CLI, and vice versa.

**Core result:** the API and database can authenticate users, enforce workspace roles, enforce share expiry/use limits/revocation, track quotas, and coordinate storage while remaining unable to read file names, plaintext, master keys, raw file keys, or share capability keys.

---

## 2. Problem Statement and Threat Model

### 2.1 Problem

Server-side encryption protects data at rest but leaves the provider able to decrypt. A breach, insider, subpoena, or misconfigured bucket therefore exposes user data. A zero-knowledge design must push encryption and key custody to the client and keep the server useful for coordination rather than confidentiality.

A second problem is cryptographic agility. A storage system built today may need different algorithms, chunk sizes, and post-quantum readiness over its lifetime. CryptaVault therefore separates policy and profile selection from the stored container format.

### 2.2 Threat model

| Asset | Trust assumption |
|---|---|
| Plaintext files | Never sent to the API, database, or object storage |
| Passphrase and master key | Exist only in the client process / browser memory |
| Raw per-file keys | Wrapped before leaving the client |
| File names and manifests | Encrypted before leaving the client |
| Ciphertext | May be stored on an untrusted S3-compatible service |
| Neon metadata | May be read by an attacker; contains no decryptable content |
| API | May be compromised or coerced; must not be able to decrypt |
| Share link | Capability; bearer can decrypt while policy permits |

The adversary may read the database, inspect stored objects, observe network traffic, and call the API. The design assumes TLS protects transport integrity, the client device is not compromised, and the user protects the passphrase.

### 2.3 Security goals

1. **Confidentiality:** no plaintext or readable file name reaches the server.
2. **Integrity:** modified or reordered ciphertext fails authentication before release.
3. **Client key custody:** the server never sees the master key or raw file key.
4. **Authorization:** workspace membership and roles are enforced server-side.
5. **Share policy:** expiry, use limits, revocation, and passphrase checks are enforced server-side.
6. **Fail closed:** wrong keys, unsupported formats, and policy violations abort rather than degrade.
7. **Interoperability:** web uploads and CLI downloads use the same container and manifest rules.

---

## 3. Architecture

```text
┌──────────────────────────── CLIENT BOUNDARY ────────────────────────────┐
│  Browser (React + Web Crypto)              Remote CLI (Python)          │
│                                                                         │
│  passphrase                                  passphrase                 │
│      │ PBKDF2-SHA256                             │ PBKDF2-SHA256          │
│      ▼                                           ▼                      │
│  auth verifier + master key             auth verifier + master key     │
│      │                                           │                      │
│      ├─ per-file raw key (AES-256)               ├─ per-file raw key    │
│      ├─ gzip optional                            ├─ gzip optional       │
│      ├─ chunked AES-256-GCM                      ├─ chunked AES-256-GCM │
│      ├─ sealed metadata manifest                 ├─ sealed manifest     │
│      └─ wrapped raw key                          └─ wrapped raw key     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ JWT + ciphertext / wrapped keys / policy
                               ▼
┌──────────────────────────── SERVER BOUNDARY ────────────────────────────┐
│  FastAPI 2.0.0                                                          │
│   ├─ auth, users, profile, admin                                        │
│   ├─ workspaces, members, roles, quotas                                 │
│   ├─ files, versions, trash, restore, download                          │
│   ├─ shares, public policy, download enforcement, revocation            │
│   ├─ storage targets, health, fallback                                  │
│   └─ dashboard and feature flags                                        │
│                                                                         │
│  Neon Postgres                              S3-compatible storage      │
│   users, verifiers, salts                    ciphertext objects only   │
│   workspaces, roles, quotas                                             │
│   encrypted metadata, wrapped keys                                      │
│   shares, policy, flags                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Why two client paths?

The browser cannot directly use every primitive supported by the Python engine. The dynamic path therefore standardizes on a portable subset:

- PBKDF2-SHA256 for passphrase derivation
- AES-256-GCM for chunk encryption
- gzip for optional compression
- SHA-256 for plaintext integrity
- JSON container `CVW1`, base64url share manifests

The offline engine keeps the full catalog and `CVV2` pipeline. This separation preserves the research contribution while giving the final-year demonstration a reliable, cross-client workflow.

---

## 4. Cryptographic Design (Dynamic Path)

### 4.1 Account and vault derivation

On registration the client generates:

- a random auth salt
- a random vault salt
- an auth verifier derived from the passphrase and auth salt
- a master key derived from the passphrase and vault salt
- a sealed vault check under the master key

The server stores the salts, verifier, KDF iteration count, and sealed check. It does not store the passphrase or master key. On login the client repeats the derivation, authenticates with the verifier, and locally validates the sealed check.

PBKDF2-SHA256 uses 210,000 iterations and a 16-byte salt in the current browser/remote path. The offline CLI keystore path uses Argon2id.

### 4.2 File encryption

For each upload or version:

1. Generate a fresh 256-bit raw file key.
2. Optionally gzip the plaintext.
3. Split the payload into profile-sized chunks.
4. Encrypt each chunk with AES-256-GCM and a fresh 96-bit nonce.
5. Bind the chunk with AAD:

```text
cryptavault:web:v1:<fileId>:<chunkIndex>:<isFinal>
```

6. Serialize the container:

```json
{
  "magic": "CVW1",
  "v": 1,
  "fileId": "<uuid>",
  "createdAt": "<iso8601>",
  "profile": "BALANCED",
  "compression": "gzip",
  "chunkSize": 4194304,
  "chunks": [
    { "i": 0, "f": 1, "iv": "<base64>", "ct": "<base64>" }
  ]
}
```

7. Seal the metadata manifest with the master key under `filemeta:<fileId>`.
8. Wrap the raw file key with the master key under `filekey:<fileId>`.

The plaintext SHA-256 is stored inside the sealed manifest and also sent as a non-secret content tag for coordination. Integrity is verified by the client after decryption.

### 4.3 Metadata manifest

The sealed manifest contains:

- display name
- MIME type
- original size
- plaintext SHA-256
- chunk count
- compression mode
- selected profile
- creation timestamp

Neon stores the encrypted manifest and its IV, not the readable values.

### 4.4 Key wrapping

The raw file key never leaves the client unwrapped. The wrapped key and IV are stored in Neon. The master key required to unwrap it exists only in the client.

### 4.5 Sharing

The browser creates a share manifest with the same metadata and a wrapped raw file key. A share key is either:

- a random 256-bit capability key placed in the URL fragment (`k`), or
- a PBKDF2 key derived from a recipient passphrase and a random salt.

The raw file key is sealed with the share key under `sharekey:v1`. The server receives only:

- token
- file ID and version
- expiry
- maximum uses
- password verifier if passphrase-protected
- revocation state

The server never receives the share manifest or capability key. The public viewer retrieves policy and ciphertext, then decrypts entirely in the browser.

### 4.6 Offline engine (`CVV2`)

The Python core additionally supports:

- catalog-driven algorithm selection
- Zstandard compression
- chunked AES-256-GCM or ChaCha20-Poly1305
- BLAKE3, SHA-2, or SHA-3 Merkle roots
- Ed25519 and hybrid post-quantum signatures
- BIP-39 key recovery
- Argon2id keystores
- local, S3-compatible, SFTP, FTPS, and cloud connector abstractions

Post-quantum operations fail closed when native `liboqs` is unavailable.

---

## 5. Backend Design

### 5.1 Persistence

Neon Postgres stores:

| Entity | Fields |
|---|---|
| User | email, display name, role, quota, used bytes, status, salts, verifier, sealed check |
| Workspace | name, owner, default profile, storage target |
| Workspace member | user, workspace, role |
| File object | workspace, owner, current version, deleted timestamp |
| File version | encrypted manifest, IV, wrapped key, IV, ciphertext size, content tag, profile, storage key |
| Share | token, file, version, owner, expiry, max uses, uses, password hash, revoked |
| Storage target | type, endpoint, bucket, credentials reference, health state |
| System setting | feature flags |
| Quota/admin state | per-user quota and suspension |

The database contains no plaintext file name, plaintext content, master key, raw file key, or share capability key.

### 5.2 API surface (implemented)

| Area | Representative routes |
|---|---|
| Auth | `POST /api/auth/prelogin`, `/register`, `/login`, `/logout`, `GET/PATCH /api/auth/me` |
| Workspaces | `GET/POST /api/workspaces`, `PATCH/DELETE /api/workspaces/{id}` |
| Members | `GET/POST /api/workspaces/{id}/members`, `PATCH/DELETE /api/workspaces/{id}/members/{userId}` |
| Files | `GET /api/workspaces/{id}/files`, `POST /api/workspaces/{id}/files/upload` |
| Versions | `GET /api/files/{id}/versions`, `POST /api/files/{id}/restore/{version}` |
| Download | `GET /api/files/{id}/download?version=N` |
| Lifecycle | `PATCH/DELETE /api/files/{id}`, `POST /api/files/{id}/untrash`, `DELETE /api/files/{id}/permanent` |
| Shares | `GET/POST /api/shares`, `GET /api/shares/{token}`, `POST /api/shares/{token}/download`, `DELETE /api/shares/{token}` |
| Storage | `GET/POST /api/storage/targets`, `POST /api/storage/targets/{id}/test` |
| Dashboard | `GET /api/dashboard` |
| Admin | `GET /api/admin/users`, `PATCH /api/admin/users/{id}`, flags, health |
| System | `GET /health`, `GET /ready` |

### 5.3 Authorization

Workspace roles are enforced in the service layer:

| Role | Capabilities |
|---|---|
| owner | Full workspace control, deletion, members |
| admin | Member management and file operations |
| editor | Upload, version, rename, trash, share |
| viewer | Read/list/download only |

Quota checks occur before ciphertext storage. Suspended users are rejected at authentication. Admin routes require an admin account.

### 5.4 Storage

The storage service resolves the workspace's preferred target, writes the ciphertext object, records the storage key, and falls back or reports health. The local demonstration uses SeaweedFS on port 9000. MinIO is not usable in this environment because Docker is unavailable and the community download endpoint returns `410 Gone`.

Cloud connectors are configuration-ready but require OAuth applications and credentials before they become operational.

### 5.5 Feature flags and maintenance mode

Administrator flags are enforced by shared policy helpers. Disabling sharing blocks new share creation, disabling versions blocks version uploads and restores, and disabling cloud connectors blocks new Google Drive, Dropbox, and OneDrive targets. Maintenance mode pauses mutating routes for non-admin accounts while keeping reads available; administrators bypass the pause. Existing share links are not retroactively revoked by the sharing flag, so revocation remains an explicit action.

### 5.6 Server-enforced share policy

On every public share request the API checks:

1. token exists
2. not revoked
3. not expired
4. use count below maximum
5. file exists and is not trashed
6. shared version exists
7. passphrase verifier matches when protected

Only then does it stream ciphertext and increment the use count. A revoked or exhausted share returns HTTP 410.

---

## 6. Web Client

The React client provides:

| Page | Purpose |
|---|---|
| Dashboard | Live quota, workspace totals, storage mix, decrypted recent files |
| Vault | Upload, download, versions, rename, trash, share |
| Shares | Server share list, revocation, locally saved links |
| Workspaces | Create/select, members, roles, storage target |
| Share viewer | Public decryptor for `#/s/<token>?m=...&k=...` |
| Admin | Users, roles, quotas, suspension, flags, storage tests, health |
| Settings | Profile, auto-lock, share TTL, compression, theme |
| Status | Health, readiness, storage, browser crypto self-test |
| Catalog | 88 algorithms and six profiles |
| Academy | Zero-knowledge explainer |

The client stores the JWT in `localStorage`, keeps the master key in memory, and auto-locks after a configurable interval. Generated share links are saved locally under `cryptavault.share.link.{token}` because the server cannot reconstruct them.

### 6.1 Compatibility decision

The dynamic viewer accepts only server shares with a manifest. Legacy static links of the form `#/share?d=...` embedded a self-contained container and cannot be resolved through the new API; they are intentionally unsupported.

---

## 7. Remote CLI

The `cryptavault remote` command group is a full API client:

```bash
cryptavault remote auth login --email demo@cryptavault.dev
cryptavault remote workspace list
cryptavault remote files upload report.pdf --profile BALANCED
cryptavault remote files download FILE_ID --output restored.pdf
cryptavault remote files versions FILE_ID
cryptavault remote files share FILE_ID --ttl 24 --max-uses 5
cryptavault remote shares decrypt 'http://localhost:3000/#/s/...'
```

It stores only the JWT and vault bootstrap in a session file, prompts for the passphrase per command, derives the master key locally, and implements the same `CVW1` encryption, key wrapping, metadata sealing, share manifest, and integrity verification as the browser.

The CLI was smoke-tested against the live local stack:

- login as a demo user
- upload `v1`
- list and decrypt
- upload `v2` with `--version-of`
- decrypt both versions
- rename
- create a capability share and decrypt it anonymously
- create a passphrase share and decrypt it with the password
- permanently delete and confirm workspace usage returns to zero

---

## 8. Testing and Results

### 8.1 Automated verification

```bash
.venv/bin/pytest -q --hypothesis-seed=0
.venv/bin/ruff check .
.venv/bin/black --check .
.venv/bin/mypy packages/core/cryptavault packages/api/cryptavault_api packages/cli/cryptavault_cli
npx -y pnpm --filter @cryptavault/web run typecheck
npx -y pnpm --filter @cryptavault/web run build
```

| Check | Result |
|---|---|
| Python tests | **165 passed** |
| Ruff | clean |
| Black | clean |
| Mypy | clean for core, API, CLI |
| Web typecheck | pass |
| Web production build | pass |
| CLI remote smoke | pass |
| Web/API/S3 smoke | pass |

The Python test suite isolates state in `/tmp/opencode/cryptavault-tests/cryptavault-test.db` and uses real PBKDF2/JWT login fixtures. Production configuration uses Neon Postgres.

### 8.2 Demonstrated behaviors

- registration, login, logout, profile update
- JWT-protected workspaces and role enforcement
- encrypted upload with quota accounting
- immutable version creation and restore
- rename through metadata re-sealing
- trash, restore, permanent delete
- public share creation, passphrase gate, download, use limit, revocation
- storage target health and fallback
- dashboard and admin aggregates
- CLI/API/web-compatible encryption and share manifests

### 8.3 Performance notes

The dynamic path is optimized for correctness and interoperability, not benchmark records. Files are buffered in client memory, gzip is optional, and chunk size follows the selected profile. The offline core includes its own benchmark command for primitive-level measurements.

---

## 9. Security Analysis

### 9.1 What the server can see

- account email and display name
- workspace names and role assignments
- ciphertext size and version count
- profile name and compression mode
- SHA-256 plaintext tag
- share policy and use counts
- storage path and target

### 9.2 What the server cannot see

- plaintext contents
- file names and MIME type (inside sealed manifest)
- master key
- raw file keys
- share manifest and capability key
- passphrase
- decrypted file hash preimage

The plaintext SHA-256 content tag is a correlation risk for low-entropy known files. It is used for integrity comparison and could be replaced by an HMAC-derived tag in future work.

### 9.3 Attacks and mitigations

| Attack | Mitigation |
|---|---|
| Database breach | Ciphertext and wrapped keys only; master key absent |
| Object storage breach | Ciphertext only; per-file keys wrapped |
| Chunk tampering | AES-GCM authentication and hash check |
| Chunk reordering | AAD binds file ID, index, and final flag |
| Metadata tampering | Manifest sealed with master key and AAD |
| Link sharing | Capability URL; optional passphrase; server policy |
| Share replay after revocation | Server checks revocation on every download |
| Unauthorized workspace access | JWT + role checks on every route |
| Quota abuse | Pre-upload quota check and admin controls |
| Stolen JWT | Limited by token lifetime; does not expose plaintext without master key |

### 9.4 Residual risks

- A compromised client device can capture plaintext and keys.
- A recipient who decrypts a shared file keeps that plaintext after revocation.
- Workspace members do not share a common master key, so another member's uploads are not decryptable without that member's key.
- Maintenance mode pauses writes for non-admin accounts, but reads remain available by design.
- Passphrase rotation is not implemented for dynamic accounts.
- Cloud connectors are not fully operational without OAuth credentials.
- The project is not independently audited.

---

## 10. Limitations and Future Work

1. **Passphrase rotation:** re-wrap account keys and update the verifier, including key migration for existing files.
2. **Shared workspace vault key:** distribute a workspace key wrapped for each member to enable true team decryption.
3. **Streaming:** replace whole-file buffering with bounded-memory streaming in the dynamic path.
4. **Keyed integrity tags:** replace plaintext SHA-256 tags with HMAC tags to reduce confirmation attacks.
5. **Broader policy scope:** extend flag enforcement to any future write surfaces and add per-workspace policy overrides.
6. **Cloud OAuth:** complete Google Drive, Dropbox, and OneDrive connectors.
7. **Post-quantum dynamic path:** add optional hybrid KEM/signature support where browser and CLI runtimes allow.
8. **Audit/tamper evidence:** intentionally out of scope for this iteration.
9. **Browser test automation:** add Playwright coverage for login, upload, share, and viewer flows.
10. **Operational hardening:** rate limits, key rotation, backup/restore drills, and deployment monitoring.

---

## 11. Conclusion

CryptaVault demonstrates that a storage backend can remain useful for identity, collaboration, policy, quota, and sharing while being unable to read user data. The dynamic stack combines a real API, a real database, real object storage, a browser client, and a CLI around a strict client-side key boundary. The same encrypted file can be produced in the browser and consumed by the CLI, and server-enforced share policy works without giving the server decryptable link material.

The project delivers a runnable full-stack demonstration, a tested zero-knowledge workflow, and a documented path from the portable `CVW1` implementation to the broader adaptive and post-quantum research engine.

---

## Appendix A — Reproduce the demo

See [demo.md](demo.md) for the complete runbook.

```bash
# Terminal 1: S3
cd /tmp/opencode/seaweed
./weed server -dir=/tmp/opencode/seaweed/data -ip=127.0.0.1 \
  -master.port=9333 -volume.port=9340 -filer.port=9341 \
  -s3 -s3.port=9000 -s3.config=/tmp/opencode/seaweed/s3.json

# Terminal 2: API
.venv/bin/uvicorn cryptavault_api.main:app --host 127.0.0.1 --port 8000

# Terminal 3: web
npx -y pnpm --filter @cryptavault/web dev
```

## Appendix B — Demo accounts

| Email | Password | Role |
|---|---|---|
| `admin@cryptavault.dev` | `CryptaVaultDemo!2026` | admin |
| `demo@cryptavault.dev` | `CryptaVaultDemo!2026` | user |
| `viewer@cryptavault.dev` | `CryptaVaultDemo!2026` | viewer |

## Appendix C — Key source files

| Area | Files |
|---|---|
| API entry | `packages/api/cryptavault_api/main.py` |
| Settings/DB | `settings.py`, `db.py`, `models.py` |
| Auth | `routes/auth.py`, `security.py`, `deps/supabase.py` |
| Files | `routes/files.py`, `services/storage.py` |
| Shares | `routes/shares.py` |
| Web API/crypto | `packages/web/src/lib/api.ts`, `crypto.ts`, `vault.tsx` |
| Web pages | `packages/web/src/pages/` |
| CLI remote | `packages/cli/cryptavault_cli/commands/remote.py` |
| Core crypto | `packages/core/cryptavault/crypto/`, `pipeline/` |
