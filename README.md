# CryptaVault

**AI-Assisted Adaptive Hybrid Cryptographic Storage Framework**  
*Enforcing strict client-side zero-knowledge boundaries across heterogeneous multi-cloud and on-premise targets.*

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-130%20passing-brightgreen.svg)](packages/core/tests)
[![Typecheck](https://img.shields.io/badge/mypy-clean-success.svg)](packages/core)
[![Post-Quantum](https://img.shields.io/badge/NIST-FIPS%20203%20%2F%20204-purple.svg)](docs/REPORT.md)

---

## Overview

CryptaVault is an enterprise-grade cryptographic storage ecosystem designed to protect sensitive data against both classical adversaries and future quantum computers ("Harvest Now, Decrypt Later"). 

Unlike conventional cloud storage systems where service providers hold the keys, CryptaVault enforces a strict **Zero-Knowledge Client Boundary**: plaintext files and private encryption keys **never leave your device**. Only authenticated ciphertext, encrypted metadata manifests, and zero-knowledge tokens reach remote storage targets.

---

## Architectural Highlights

```
+-----------------------------------------------------------------------------+
|                            CLIENT BOUNDARY (ZK)                             |
|                                                                             |
|  [ CLI Workstation (Typer/Rich) ]  or  [ Web Browser (React + WASM) ]       |
|       |                                                                     |
|       +--> Argon2id Master Key Derivation (24-word BIP-39 Mnemonic Backup)  |
|       +--> 5-Tier Adaptive Security Engine (PERFORMANCE -> MAXIMUM)         |
|       +--> Entropy Detection & Pre-Compression (Zstandard, Snappy)         |
|       +--> Chunked AEAD Streaming (AES-256-GCM / ChaCha20-Poly1305)         |
|       +--> BLAKE3 Merkle Tree & Post-Quantum Hybrid Signatures (FIPS 204)   |
|       +--> DoD 5220.22-M 3-Pass Physical Overwrite File Shredder            |
+-------+---------------------------------------------------------------------+
        |
        | [ ENCRYPTED CIPHERTEXT ONLY ]
        v
+-----------------------------------------------------------------------------+
|                          SERVER & STORAGE BACKENDS                          |
|                                                                             |
|  FastAPI Zero-Knowledge Backend (Port 8000)                                 |
|   - Supabase Auth JWT Verification & Role-Based Access Control              |
|   - Encrypted Manifest Synchronization with BLAKE3 Hash Integrity           |
|   - Timed One-Time Share Link Coordination (HMAC-SHA256)                    |
|   - Live Telemetry Server-Sent Events (/api/metrics/stream)                 |
|   - AI Educational Security Advisory (Code-Level Data Minimization)         |
|                                                                             |
|  Multi-Backend Storage Connectors:                                          |
|   - Supabase Storage (Private 'vaults' bucket)                              |
|   - Remote SFTP Server (Paramiko streaming)                                 |
|   - Remote FTPS Server (Explicit TLS PASV mode)                             |
|   - Atomic Local Storage Connector                                          |
+-----------------------------------------------------------------------------+
```

---

## Key Features

- **Post-Quantum Hybrid Cryptography**: Combines classical algorithms with NIST FIPS 203 (ML-KEM-768 / Kyber) and FIPS 204 (ML-DSA-65 / Dilithium-3) in an AND-composition structure.
- **5-Tier Adaptive Security Engine**: Dynamically shifts ciphers, KDF iterations, and compression levels based on a 0–100% security slider.
- **Fail-Closed Chunk Streaming**: Decrypts chunk-by-chunk; any tampered byte immediately halts processing before corrupt data reaches disk.
- **Multi-Backend Storage**: Unified abstraction supporting Supabase, SFTP, FTPS, and local drives.
- **Zero-Knowledge Sharing**: One-time access tokens, password-wrapped envelopes, timed links, and QR codes.
- **AI-Assisted Security Advisory**: Smart cryptographic recommendations with strict data minimization (file contents and keys are never sent).
- **Admin Governance Console**: Impersonation audits, runtime feature flags, and live SSE performance metrics.

---

## Quickstart

### 1. Command-Line Interface (CLI)

```bash
# Check CPU hardware acceleration (AES-NI, AVX2) and zero-knowledge bounds
cryptavault status

# Generate master key and BIP-39 mnemonic phrase
cryptavault keygen --output vault.keystore --passphrase "my-passphrase"

# Encrypt file through full streaming pipeline
cryptavault pipeline-encrypt document.pdf --output document.vault --profile MAXIMUM

# Decrypt file with fail-closed integrity verification
cryptavault pipeline-decrypt document.vault --output document_restored.pdf --profile MAXIMUM

# Run cross-primitive micro-benchmarks
cryptavault benchmark

# Ask AI security advisor
cryptavault ai advise document.pdf
cryptavault ai explain "ML-KEM-768"
```

### 2. Web Client & Admin Console

```bash
# Start FastAPI Zero-Knowledge Backend (Port 8000)
.venv/bin/uvicorn cryptavault_api.main:app --host 0.0.0.0 --port 8000 --reload

# Start Web Client (Port 3000)
cd packages/web && npm run dev -- --port 3000

# Start Admin Console (Port 3001)
cd packages/admin && npm run dev -- --port 3001
```

- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Web Client**: [http://localhost:3000](http://localhost:3000)
- **Admin Console**: [http://localhost:3001](http://localhost:3001)

---

## Project Structure

```
CryptaVault/
├── packages/
│   ├── core/           # Python cryptographic engine, adaptive pipeline, storage connectors
│   ├── api/            # FastAPI zero-knowledge backend with Supabase Auth
│   ├── cli/            # Typer & Rich interactive command-line interface
│   ├── web/            # React client-side encryption web app with Vite
│   ├── admin/          # React governance console with live SSE telemetry
│   └── wasm/           # WebAssembly bindings configuration
├── docs/
│   ├── REPORT.md       # Comprehensive academic project technical report
│   ├── cli.md          # CLI reference documentation
│   ├── demo.md         # Reproducible step-by-step showcase script
│   └── ...             # Architectural and phase specification guides
└── pyproject.toml      # Python workspace configuration
```

---

## Testing & Quality Assurance

```bash
# Run full automated test suite (130 tests)
pytest

# Static type checking (98 files)
mypy packages/core/cryptavault packages/api/cryptavault_api packages/cli/cryptavault_cli

# Code formatting & linting
black --check .
ruff check .

# Frontend Turborepo build
npx -y turbo run build
```

---

## Documentation Links

- [Academic Technical Report (REPORT.md)](docs/REPORT.md)
- [CLI Reference Guide (docs/cli.md)](docs/cli.md)
- [Demonstration Showcase Script (docs/demo.md)](docs/demo.md)
- [Software Requirements Specification (SRS.md)](SRS.md)
- [Architecture Deep-Dive (ARCHITECTURE.md)](ARCHITECTURE.md)
- [Changelog](CHANGELOG.md)

---

## License

MIT License — see [LICENSE](LICENSE) for details.