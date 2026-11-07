# CryptaVault

**AI-assisted adaptive hybrid cryptographic storage with a strict client-side zero-knowledge boundary.**

CryptaVault encrypts files and metadata on the client, selects cryptographic primitives from a versioned catalog, and stores only ciphertext, wrapped keys, and integrity metadata. It ships a Python cryptographic engine, a Typer CLI, a FastAPI coordination backend, and a browser portal that runs entirely on GitHub Pages.

**Live portal:** https://dhruv-mulani.github.io/CryptaVault/

[![Tests](https://img.shields.io/badge/tests-161%20passing-brightgreen.svg)](packages/core/tests)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Portal](https://img.shields.io/badge/portal-GitHub%20Pages-blue.svg)](https://dhruv-mulani.github.io/CryptaVault/)

---

## How it works

```
Client boundary (plaintext and private keys never leave)
┌──────────────────────────────────────────────────────────────────────┐
│ CLI (Python)                          Browser portal (WebCrypto)     │
│                                                                      │
│ passphrase ──► KDF ──► master key ──► per-file key                   │
│ file ──► entropy check ──► optional compression ──► chunked AEAD     │
│                                                      │               │
│                    encrypted manifest + wrapped key ─┘               │
│                    Merkle root + optional signature                   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ ciphertext only
                                   ▼
        Local disk / IndexedDB / Supabase / S3-compatible / SFTP / FTPS
```

1. **Derive a key.** The CLI uses Argon2id; the static browser portal uses PBKDF2-SHA256 (210,000 iterations) because WebCrypto exposes PBKDF2 in every target browser. The derived master key stays in memory.
2. **Generate a per-file key.** Every file gets a fresh 256-bit key. File names, hashes, and manifests are sealed separately with the master key.
3. **Choose a profile.** A 0–100 slider maps to six profiles. The profile controls the AEAD cipher, hash, signature/KEM selection, KDF cost, chunk size, and whether post-quantum and multi-layer modes are enabled.
4. **Encrypt before storage.** Files are chunked with authenticated boundaries (AES-256-GCM or ChaCha20-Poly1305). The core pipeline adds a BLAKE3/SHA-2/SHA-3 Merkle root and an optional Ed25519 or hybrid post-quantum signature.
5. **Persist only ciphertext.** Storage receives a container, an encrypted manifest, and a wrapped file key. No plaintext, no master key, and no readable file name crosses the boundary.
6. **Fail closed.** A tampered chunk, reordered chunk, wrong Merkle root, wrong algorithm binding, or bad signature aborts decryption before plaintext is released.

The exact algorithms and stable wire IDs used for a file are recorded in its container header. Old files remain decryptable after defaults change, and unknown algorithms fail closed instead of silently downgrading.

---

## Six security profiles

| Profile | Slider | AEAD | Hash | KDF (Argon2id) | Chunk | Post-quantum | Multi-layer |
|---|---|---:|---|---:|---:|---|---|
| `PERFORMANCE` | 0–20 | AES-256-GCM | BLAKE3 | 32 MiB / t=2 | 4 MiB | No | No |
| `STANDARD` | 20–40 | AES-256-GCM | SHA-256 | 48 MiB / t=3 | 4 MiB | No | No |
| `BALANCED` | 40–60 | AES-256-GCM | SHA-256 | 64 MiB / t=3 | 4 MiB | Hybrid readiness | No |
| `STRONG` | 60–80 | ChaCha20-Poly1305 | BLAKE3 | 64 MiB / t=4 | 8 MiB | Yes | No |
| `PQ_STRONG` | 80–90 | AES-256-GCM | SHA3-512 | 96 MiB / t=5 | 8 MiB | Yes | No |
| `MAXIMUM` | 90–100 | AES-256-GCM cascade | SHA3-512 | 128 MiB / t=5 | 16 MiB | Yes | Yes |

The browser portal mirrors the profile names, profile descriptions, and chunk sizes, but uses PBKDF2 at the vault level and gzip for optional compression. See [docs/crypto_catalog.md](docs/crypto_catalog.md) for the complete 88-algorithm catalog, stable wire IDs, and API surface.

---

## Features

| Area | What is implemented | Documentation |
|---|---|---|
| Adaptive profiles | Six profiles, slider resolution, persisted active profile, profile API | [docs/crypto_catalog.md](docs/crypto_catalog.md) |
| Crypto catalog | Versioned catalog, lifecycle gates, 88 algorithms, wire IDs, implemented/runtime flags | [docs/crypto_catalog.md](docs/crypto_catalog.md) |
| Core pipeline | Compression, chunked AEAD, Merkle integrity, signatures, `CVV2` framing, legacy `CVV1` read path | [docs/container_format.md](docs/container_format.md) |
| Keys and recovery | Encrypted keystore, BIP-39 mnemonic recovery, keystore inspection | [docs/cli.md](docs/cli.md) |
| Secure sharing | Capability links, passphrase-protected shares, encrypted bundles, timed links, QR codes | [docs/cli.md](docs/cli.md), [docs/portal.md](docs/portal.md) |
| Web portal | Local vault, file encryption, shares, encrypted messages, catalog browser, academy, settings, diagnostics | [docs/portal.md](docs/portal.md) |
| Admin and governance | Local policy flags, inventory, audit export, wipe; API admin routes | [docs/portal.md](docs/portal.md), [docs/api.md](docs/api.md) |
| Storage connectors | Local, Supabase, SFTP, FTPS, mock, and cloud connector scaffolding | [docs/api.md](docs/api.md), [docs/deployment.md](docs/deployment.md) |
| Integrity and shredding | Merkle proofs, detached signatures, DoD-style multi-pass overwrite | [docs/cli.md](docs/cli.md) |
| AI advisory | Offline knowledge base and explain/advise commands with data minimization | [docs/cli.md](docs/cli.md) |
| Zero-knowledge model | Boundaries, threat model, what the server can and cannot see, limitations | [docs/security_model.md](docs/security_model.md) |
| GitHub Pages deployment | Automatic build and deploy on every push to `main` | [docs/deployment.md](docs/deployment.md) |

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+ and pnpm (web portal)
- `uv` (recommended for Python)
- Optional: native `liboqs` shared library for post-quantum KEM/signature tests

### CLI

```bash
git clone https://github.com/DHRUV-MULANI/CryptaVault.git
cd CryptaVault

uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e packages/core -e packages/cli
source .venv/bin/activate

cryptavault --help
cryptavault status
```

To install the optional post-quantum extra:

```bash
uv pip install --python .venv/bin/python -e 'packages/core[pq]'
# The Python package still needs the native liboqs shared library at runtime.
```

### Web portal

```bash
pnpm install
pnpm --filter @cryptavault/web dev
# Open the printed localhost URL, usually http://localhost:5173
```

For a production build with the GitHub Pages base path:

```bash
VITE_BASE=/CryptaVault/ pnpm --filter @cryptavault/web build
```

### API

```bash
uv pip install --python .venv/bin/python -e packages/core -e packages/api
.venv/bin/uvicorn cryptavault_api.main:app --host 127.0.0.1 --port 8000 --reload
# OpenAPI: http://127.0.0.1:8000/docs
```

The static portal does not require the API. The API is only needed for Supabase-backed identity, server-coordinated sharing, encrypted storage uploads, admin governance, audit chains, and metrics.

---

## CLI quickstart

```bash
# Hardware, profile, and post-quantum readiness
cryptavault status
cryptavault profiles
cryptavault profile list
cryptavault profile set --slider 85     # resolves to PQ_STRONG

# Generate a 256-bit master key + 24-word BIP-39 recovery phrase
cryptavault keygen --output vault.keystore --passphrase "correct horse battery staple"
cryptavault inspect-keystore --keystore vault.keystore --passphrase "correct horse battery staple"

# Full pipeline: compression, chunked AEAD, Merkle tree, signature
cryptavault pipeline-encrypt document.pdf --output document.vault --profile MAXIMUM
cryptavault pipeline-decrypt document.vault --output restored.pdf --profile MAXIMUM

# Lightweight authenticated encryption and integrity tools
cryptavault encrypt --input secrets.txt --output secrets.enc --profile BALANCED
cryptavault decrypt --input secrets.enc --output secrets.txt
cryptavault sign release.tar.gz --output-sig release.sig
cryptavault verify release.tar.gz --sig release.sig --pubkey release.pub
cryptavault merkle --dir ./data
cryptavault shred obsolete.db --passes 3

# Sharing, storage, learning, and advisory
cryptavault share create document.vault --timed 3600 --qr
cryptavault storage upload document.vault local://./vault-data
cryptavault teach zero-knowledge
cryptavault ai advise document.pdf
```

See [docs/cli.md](docs/cli.md) for every command, option, and example.

## Web portal quickstart

1. Open https://dhruv-mulani.github.io/CryptaVault/.
2. Create a local vault with a passphrase of at least 10 characters and choose a default profile.
3. Upload a file from **Vault**. It is read, compressed if useful, chunked, encrypted, and stored in IndexedDB in this browser.
4. Create a share from the file row. Small files produce a self-contained link; larger payloads produce an encrypted `.cvshare.json` bundle.
5. Open **Shares** to inspect or revoke the local share record, or **Share viewer** to decrypt a link or bundle.
6. Use **Messages** for local encrypted notes, **Catalog** for all 88 algorithms, **Academy** for an implementation-aligned explainer, and **Status** to run a browser crypto self-test.
7. Use **Settings** to rotate the passphrase, export an encrypted backup, or wipe the vault. **Admin** holds local policy flags and the audit log.

The portal stores data only in this browser. Clearing site data, using a different browser, or a private window loses local access unless you exported a backup. See [docs/portal.md](docs/portal.md).

---

## Testing and quality

```bash
# Python
.venv/bin/python -m pytest packages/core/tests packages/api/tests packages/cli/tests --hypothesis-seed=0
.venv/bin/ruff check .
.venv/bin/black --check .
.venv/bin/mypy packages/core/cryptavault packages/api/cryptavault_api packages/cli/cryptavault_cli

# Web
pnpm --filter @cryptavault/web typecheck
pnpm --filter @cryptavault/web build
```

Current suite: **161 tests passing**, ruff/black/mypy clean, and the portal builds with Vite.

---

## Project layout

```
packages/
├── core/    # catalog, adaptive engine, crypto, pipeline, keys, integrity, storage, sharing
├── api/     # FastAPI routers for auth, users, shares, storage, audit, admin, metrics, crypto catalog
├── cli/     # Typer CLI: keys, encrypt/decrypt, pipeline, profiles, sharing, storage, teach, AI
├── web/     # React + Vite + Tailwind zero-knowledge portal
├── admin/   # separate governance console scaffold
└── wasm/    # WebAssembly binding scaffold
docs/        # portal, CLI, deployment, catalog, container, security, API references
scripts/     # catalog export and utility scripts
.github/     # CI and GitHub Pages deployment workflows
```

---

## Security and limitations

- Plaintext and private keys never leave the client boundary. The API and storage backends receive ciphertext, encrypted manifests, wrapped keys, and non-identifying metadata only.
- The static portal's share links are **capability URLs**: anyone with the link and optional passphrase can decrypt. Revoking a local share record cannot invalidate a link or bundle that was already copied.
- Static-deployment share expiry is advisory. The API can enforce server-side expiry and one-time consumption.
- The portal's encrypted messages are local-only in this deployment. Cross-device delivery requires the API relay.
- The core orchestrator currently buffers the whole file for compression/decryption even though the chunk encryptor itself is incremental. True bounded-memory streaming is a documented roadmap item, not a current claim.
- Post-quantum operations require the native `liboqs` library. Without it, affected tests and operations fail closed with `OqsNotAvailableError`.
- This is a research and portfolio deployment, not an audited production cryptographic product.

Full details: [docs/security_model.md](docs/security_model.md).

---

## Documentation

- [Web portal guide](docs/portal.md)
- [CLI reference](docs/cli.md)
- [Deployment guide](docs/deployment.md)
- [Crypto catalog and profiles](docs/crypto_catalog.md)
- [Container formats](docs/container_format.md)
- [Security model](docs/security_model.md)
- [API reference](docs/api.md)
- [Architecture](ARCHITECTURE.md)
- [Software requirements](SRS.md)
- [Changelog](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).
