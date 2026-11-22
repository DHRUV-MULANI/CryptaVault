# CryptaVault

**AI-assisted adaptive hybrid cryptographic storage with a strict client-side zero-knowledge boundary.**

CryptaVault encrypts files and metadata on the client, selects cryptographic primitives from a versioned catalog, and stores only ciphertext, wrapped keys, integrity metadata, and non-identifying policy records. The current dynamic deployment is a local full-stack application: React + Vite web client, FastAPI coordination API, Neon Postgres metadata, S3-compatible ciphertext storage (SeaweedFS locally), and a Typer CLI that shares the same remote API and wire format.

[![Tests](https://img.shields.io/badge/tests-165%20passing-brightgreen.svg)](packages/core/tests)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![API](https://img.shields.io/badge/API-FastAPI%202.0.0-009688.svg)](packages/api)
[![Web](https://img.shields.io/badge/web-React%20%2B%20Vite-646CFF.svg)](packages/web)

> The GitHub Pages workflow can host the SPA assets, but the dynamic application requires a reachable FastAPI instance. GitHub Pages cannot host the API, Neon database, or S3 bucket. The reproducible demo runs locally; see [docs/demo.md](docs/demo.md).

---

## How it works

```
Client boundary (plaintext and private keys never leave)
┌──────────────────────────────────────────────────────────────────────┐
│ CLI (Python)                          Browser (React + WebCrypto)    │
│                                                                      │
│ passphrase ──► PBKDF2 ──► master key ──► per-file key                │
│ file ──► optional gzip ──► chunked AES-256-GCM ──► CVW1 container    │
│                    encrypted manifest + wrapped key ─┘               │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ ciphertext + wrapped keys only
                                   ▼
        FastAPI ──► Neon Postgres (metadata, auth, shares, policy)
                └─► S3-compatible storage (ciphertext objects)
```

1. **Authenticate locally.** The browser and remote CLI derive an auth verifier and a 256-bit master key from the passphrase with PBKDF2-SHA256 (210,000 iterations). The verifier authenticates the account; the master key stays in the client.
2. **Generate a per-file key.** Every file version gets a fresh 256-bit key. File names, hashes, and manifests are sealed separately with the master key under an AAD bound to the file ID.
3. **Choose a profile.** Six profiles control chunk size, catalog primitives, KDF cost, compression, post-quantum readiness, and multi-layer policy. `BALANCED` is the default.
4. **Encrypt before storage.** The web client and remote CLI produce compatible `CVW1` containers: gzip-optional payload, chunked AES-256-GCM with authenticated boundaries, and a plaintext SHA-256 integrity hash.
5. **Persist only ciphertext.** Neon stores users, workspaces, roles, quotas, file/version metadata, wrapped keys, shares, and policy flags. S3 receives ciphertext objects only. No plaintext, master key, or raw file key reaches the API.
6. **Fail closed.** A tampered chunk, wrong key, reordered container, expired/revoked share, or hash mismatch aborts decryption before plaintext is released.

The core Python engine additionally supports the full `CVV2` pipeline with catalog-selected algorithms, Merkle roots, signatures, and post-quantum operations. The dynamic web/remote path intentionally uses the portable browser-compatible `CVW1` subset so the same file can be uploaded in the browser and downloaded from the CLI, or vice versa.

---

## Six security profiles

| Profile | Slider | Core AEAD | Hash | KDF (Argon2id) | Chunk | Post-quantum | Multi-layer |
|---|---|---:|---|---:|---:|---|---|
| `PERFORMANCE` | 0–20 | AES-256-GCM | BLAKE3 | 32 MiB / t=2 | 4 MiB | No | No |
| `STANDARD` | 20–40 | AES-256-GCM | SHA-256 | 48 MiB / t=3 | 4 MiB | No | No |
| `BALANCED` | 40–60 | AES-256-GCM | SHA-256 | 64 MiB / t=3 | 4 MiB | Hybrid readiness | No |
| `STRONG` | 60–80 | ChaCha20-Poly1305 | BLAKE3 | 64 MiB / t=4 | 8 MiB | Yes | No |
| `PQ_STRONG` | 80–90 | AES-256-GCM | SHA3-512 | 96 MiB / t=5 | 8 MiB | Yes | No |
| `MAXIMUM` | 90–100 | AES-256-GCM cascade | SHA3-512 | 128 MiB / t=5 | 16 MiB | Yes | Yes |

The dynamic web/remote path mirrors the profile names, descriptions, and chunk sizes, but uses PBKDF2 at the vault level, gzip for optional compression, and AES-256-GCM for container chunks. See [docs/crypto_catalog.md](docs/crypto_catalog.md) for the 88-algorithm catalog.

---

## Features

| Area | What is implemented | Documentation |
|---|---|---|
| Dynamic auth | Local accounts, PBKDF2 verifier, JWT sessions, auto-lock, profile updates | [docs/api.md](docs/api.md) |
| Workspaces | Owner/editor/viewer/admin roles, members, quotas, per-workspace storage target | [docs/api.md](docs/api.md) |
| Encrypted vault | Chunked client-side upload, immutable versions, rename, trash/restore, permanent delete | [docs/portal.md](docs/portal.md) |
| Secure sharing | Server-enforced expiry/uses/revocation, passphrase, recipient email, 8-digit PIN, QR, link regeneration, received-shares inbox | [docs/api.md](docs/api.md) |
| Live dashboard | User/admin aggregates, storage mix, quota, recent files, activity counters | [docs/portal.md](docs/portal.md) |
| Admin console | Role/quota/suspension controls, feature flags, storage health tests, system health | [docs/portal.md](docs/portal.md) |
| Remote CLI | Login/register, workspaces, upload/download, versions, trash, shares, share decryption | [docs/cli.md](docs/cli.md) |
| Storage | S3-compatible local SeaweedFS, fallback/health checks, config-ready cloud connectors | [docs/api.md](docs/api.md) |
| Adaptive profiles | Six profiles, slider resolution, persisted active profile, profile API | [docs/crypto_catalog.md](docs/crypto_catalog.md) |
| Crypto catalog | Versioned catalog, lifecycle gates, 88 algorithms, wire IDs, implemented/runtime flags | [docs/crypto_catalog.md](docs/crypto_catalog.md) |
| Core pipeline | Compression, chunked AEAD, Merkle integrity, signatures, `CVV2` framing, legacy `CVV1` read path | [docs/container_format.md](docs/container_format.md) |
| AI advisory | Offline knowledge base and explain/advise commands with data minimization | [docs/cli.md](docs/cli.md) |
| Integrity and shredding | Merkle proofs, detached signatures, DoD-style multi-pass overwrite | [docs/cli.md](docs/cli.md) |
| Zero-knowledge model | Boundaries, threat model, what the server can and cannot see, limitations | [docs/security_model.md](docs/security_model.md) |

---

## Local full-stack quickstart

### Prerequisites

- Python 3.11 and `uv`
- Node.js 20+ and `pnpm` (the repo examples use `npx -y pnpm`)
- A Neon Postgres database (or a local Postgres URL)
- An S3-compatible bucket; the demo uses SeaweedFS because Docker/MinIO are unavailable in this environment
- Optional: native `liboqs` for post-quantum core tests

### 1. Install

```bash
git clone https://github.com/DHRUV-MULANI/CryptaVault.git
cd CryptaVault

uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e packages/core -e packages/api -e packages/cli

npx -y pnpm install
```

### 2. Configure `.env`

Create `.env` in the repo root (it is ignored). Required values:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
JWT_SECRET=replace-with-a-32-byte-or-longer-random-secret
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=cryptavault
PUBLIC_SHARE_DOMAIN=http://localhost:3000
CRYPTAVAULT_ENV=development
```

Optional cloud connectors: `GDRIVE_*`, `DROPBOX_*`, and `ONEDRIVE_*`. They remain config-ready until OAuth applications are supplied.

### 3. Start the local S3 service

The demo uses SeaweedFS on port 9000. See [docs/demo.md](docs/demo.md) for the exact local command and bucket bootstrap. MinIO is not usable in this environment because the community download endpoint returns `410 Gone`, and Docker is unavailable.

### 4. Start the API

```bash
.venv/bin/uvicorn cryptavault_api.main:app --host 127.0.0.1 --port 8000
# OpenAPI: http://127.0.0.1:8000/docs
# Health:  http://127.0.0.1:8000/health
```

### 5. Start the web client

```bash
npx -y pnpm --filter @cryptavault/web dev
# http://localhost:3000
```

The web client calls `http://localhost:8000` by default. Override with `VITE_API_URL` when building or running elsewhere.

### 6. Sign in

Seed/demo accounts in the local database:

| Account | Password | Role |
|---|---|---|
| `admin@cryptavault.dev` | `CryptaVaultDemo!2026` | admin |
| `demo@cryptavault.dev` | `CryptaVaultDemo!2026` | user |
| `viewer@cryptavault.dev` | `CryptaVaultDemo!2026` | viewer |

The accounts are seeded by the API startup path when `CRYPTAVAULT_SEED_DEMO=true` (the default) and no users exist yet. If your database was created before the `.dev` migration, recreate or reseed the demo users.

---

## Web client quickstart

1. Open `http://localhost:3000` and sign in with a demo account.
2. **Dashboard** shows live quota, storage mix, workspace totals, and decrypted recent files.
3. **Vault** uploads a file: it is compressed when useful, chunked, encrypted with a fresh key, and uploaded as ciphertext. The matching manifest is sealed with your master key.
4. **Versions** adds an immutable version; **Trash** restores or permanently deletes.
5. **Share** creates a server-enforced link with expiry/use limits, optional passphrase, optional recipient email, and an 8-digit PIN (auto-assigned if omitted). The decryption key stays in the URL fragment; the server never receives it.
6. **Shares** lists owned shares and "Shared with me" inbox; owner can copy link/QR, change PIN, regenerate link, or revoke. Recipient-email users bypass PIN when logged in.
7. **Workspaces** manages members, roles, quotas, and the active workspace.
8. **Admin** is visible to admin accounts and controls users, quotas, suspension, flags, storage tests, and health.
9. **Status** checks `/health`, `/ready`, storage targets, browser crypto support, and the AES-GCM self-test.
10. **Catalog** and **Academy** remain reference pages for the 88 algorithms and the zero-knowledge model.

Public share links use the form:

```text
http://localhost:3000/#/s/<token>?k=<raw-share-key>
```

The key fragment is client-only. PIN/password are server-enforced access controls; recipient-email users skip PIN when logged in.

---

## Dynamic remote CLI quickstart

The `remote` commands use the same API and `CVW1` wire format as the web client. The session file stores the JWT and vault bootstrap, never the master key or passphrase.

```bash
# Login and inspect the session
.venv/bin/cryptavault remote auth login --email demo@cryptavault.dev
.venv/bin/cryptavault remote auth whoami

# Workspaces
.venv/bin/cryptavault remote workspace list
.venv/bin/cryptavault remote workspace create "Thesis evidence"
.venv/bin/cryptavault remote workspace use "Thesis evidence"
.venv/bin/cryptavault remote workspace members

# Encrypt/upload, list, and round-trip
.venv/bin/cryptavault remote files upload report.pdf --profile BALANCED
.venv/bin/cryptavault remote files list
.venv/bin/cryptavault remote files download FILE_ID --output restored.pdf

# Immutable versions and trash
.venv/bin/cryptavault remote files upload report.pdf --version-of FILE_ID
.venv/bin/cryptavault remote files versions FILE_ID
.venv/bin/cryptavault remote files restore FILE_ID 1
.venv/bin/cryptavault remote files trash FILE_ID
.venv/bin/cryptavault remote files untrash FILE_ID

# Share and decrypt anonymously
.venv/bin/cryptavault remote files share FILE_ID --ttl 24 --max-uses 5
.venv/bin/cryptavault remote shares list
.venv/bin/cryptavault remote shares decrypt 'http://localhost:3000/#/s/...'
.venv/bin/cryptavault remote shares revoke TOKEN
```

Use `CRYPTAVAULT_SESSION=/path/to/session.json` to isolate a demo session and `CRYPTAVAULT_API_URL` to target another API. Add `--passphrase` to non-interactive commands.

### Local core CLI

The original offline cryptographic toolkit remains available:

```bash
cryptavault status
cryptavault profiles
cryptavault profile set --slider 85
cryptavault keygen --output vault.keystore --passphrase "correct horse battery staple"
cryptavault pipeline-encrypt document.pdf --output document.vault --profile MAXIMUM
cryptavault pipeline-decrypt document.vault --output restored.pdf --profile MAXIMUM
cryptavault encrypt --input secrets.txt --output secrets.enc --profile BALANCED
cryptavault decrypt --input secrets.enc --output secrets.txt
cryptavault sign release.tar.gz --output-sig release.sig
cryptavault verify release.tar.gz --sig release.sig --pubkey release.pub
cryptavault merkle --dir ./data
cryptavault shred obsolete.db --passes 3
cryptavault share create document.vault --timed 3600 --qr
cryptavault teach zero-knowledge
cryptavault ai advise document.pdf
```

See [docs/cli.md](docs/cli.md) for the full offline command reference.

---

## Testing and quality

```bash
# Python
.venv/bin/pytest -q --hypothesis-seed=0
.venv/bin/ruff check .
.venv/bin/black --check .
.venv/bin/mypy packages/core/cryptavault packages/api/cryptavault_api packages/cli/cryptavault_cli

# Web
npx -y pnpm --filter @cryptavault/web run typecheck
npx -y pnpm --filter @cryptavault/web run build
```

Current suite: **165 tests passing**, ruff/mypy clean for the dynamic packages, and the web client typechecks and builds. The backend tests use an isolated SQLite database under `/tmp/opencode/cryptavault-tests/`; production uses Neon Postgres.

---

## Project layout

```
packages/
├── core/    # catalog, adaptive engine, crypto, pipeline, keys, integrity, storage, sharing
├── api/     # FastAPI auth, workspaces, files, shares, storage, dashboard, admin
├── cli/     # Typer offline toolkit + `cryptavault remote` API client
├── web/     # React + Vite zero-knowledge dynamic client
├── admin/   # separate governance console scaffold
└── wasm/    # WebAssembly binding scaffold
docs/        # demo, portal, CLI, deployment, catalog, container, security, API references
scripts/     # catalog export and utility scripts
.github/     # CI and GitHub Pages deployment workflows
```

---

## Security and limitations

- Plaintext, passphrases, master keys, and raw file keys never leave the client boundary. Neon and S3 receive ciphertext, wrapped keys, encrypted manifests, and non-identifying metadata only.
- The server can enforce share expiry, use limits, revocation, passphrase policy, workspace roles, quotas, and account status. It cannot decrypt file contents or names.
- Share links are capability URLs: anyone with the link and optional passphrase can decrypt while the share is valid. Revocation and expiry stop future API downloads, but a recipient who already decrypted a file keeps that plaintext.
- The server never stores decryptable share URLs; generated links are kept in the creating browser's local storage.
- Dynamic web/remote encryption buffers each file in memory. The core pipeline is chunked but the orchestration is not yet fully bounded-memory streaming.
- Cloud connectors are config-ready but not operational without OAuth applications and credentials.
- Workspace membership shares metadata and policy, not a shared vault key. A member can manage files they uploaded; decrypting another member's uploads requires the same master key.
- Feature flags are stored in the database but not yet enforced across every route.
- Passphrase rotation is not implemented for dynamic accounts; the UI disables it and points to a future CLI migration.
- Post-quantum operations require native `liboqs`. Without it, affected core operations fail closed with `OqsNotAvailableError`.
- This is a research and final-year project deployment, not an audited production cryptographic product.

Full details: [docs/security_model.md](docs/security_model.md).

---

## Documentation

- [End-to-end demo runbook](docs/demo.md)
- [Technical report](docs/REPORT.md)
- [Presentation deck](docs/CryptaVault_Dynamic_Stack.pptx)
- [Web portal guide](docs/portal.md)
- [CLI reference](docs/cli.md)
- [API reference](docs/api.md)
- [Deployment guide](docs/deployment.md)
- [Crypto catalog and profiles](docs/crypto_catalog.md)
- [Container formats](docs/container_format.md)
- [Security model](docs/security_model.md)
- [Architecture](ARCHITECTURE.md)
- [Software requirements](SRS.md)
- [Changelog](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).
