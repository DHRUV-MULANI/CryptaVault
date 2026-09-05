# Software Requirements Specification (SRS)
## CryptaVault — AI-Assisted Adaptive Hybrid Cryptographic Storage Framework

**Version**: 1.0
**Date**: 2026-08-04
**Status**: Final (Planning)
**Author**: CryptaVault Project

---

## Table of Contents
1. Introduction
2. Overall Description
3. Functional Requirements
4. Non-Functional Requirements
5. External Interface Requirements
6. System Architecture
7. Database Requirements
8. Security Requirements
9. Cryptographic Requirements
10. Performance Requirements
11. AI Assistant Requirements
12. Admin Console Requirements
13. API Requirements
14. Plugin Architecture Requirements
15. Acceptance Criteria
16. Constraints & Assumptions
17. Out of Scope
18. Glossary

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) defines the functional, non-functional, security, cryptographic, performance, and interface requirements for **CryptaVault** — an extensible cryptographic framework that provides secure, intelligent, and storage-independent encryption services for any storage backend.

The framework acts as a cryptographic layer between users and storage providers, ensuring all uploaded data is encrypted client-side, compressed when beneficial, digitally signed, integrity-protected, and stored in encrypted form — without the storage provider (or the framework's own backend) ever accessing plaintext or encryption keys.

### 1.2 Scope
CryptaVault provides:
- Universal storage connectors (Local, SFTP, FTP, Google Drive, OneDrive, Dropbox) with plugin extension.
- An adaptive security engine allowing users to select a speed/security profile (0–100%).
- Hybrid classical + post-quantum cryptography (AES, ChaCha20, ECC, Kyber, Dilithium).
- Intelligent compression with file-type detection.
- Chunked streaming encryption pipeline for large files.
- Hierarchical key management with recovery.
- Digital signatures and Merkle-tree-based folder integrity.
- Secure sharing (one-time, time-limited, password, QR, public-key invitation).
- A web client with browser-side WebAssembly crypto (zero-knowledge boundary).
- An admin console (React SPA) for user/audit/flag/health management.
- A CLI (Python) for automation and full feature parity.
- A benchmark lab for comparative crypto algorithm measurement.
- An AI security assistant (rule-based core + optional cloud LLM).

### 1.3 Definitions, Acronyms, Abbreviations
See Glossary (section 18).

### 1.4 References
- NIST FIPS 197 (AES), FIPS 202 (SHA-3), FIPS 203 (Kyber ML-KEM), FIPS 204 (Dilithium ML-DSA).
- RFC 5869 (HKDF), 8439 (ChaCha20-Poly1305), 7748 (Curve25519), 8032 (EdDSA), 3394 (AES-KW).
- Signal Double Ratchet (Perrin & Marlinspike).
- BLAKE3 spec (Orr, Aumentado, Hopwood).
- liboqs (open-quantum-safe/liboqs).
- Supabase documentation (https://supabase.com/docs).
- Original Diffie-Hellman 1976 ("New Directions in Cryptography").

### 1.5 Overview
Section 2 describes overall product vision and user classes. Section 3 lists functional requirements (FR-*). Section 4 lists non-functional requirements (NFR-*). Sections 5–14 specify detailed subsystem requirements. Section 15 lists acceptance criteria mapped to requirements.

---

## 2. Overall Description

### 2.1 Product Vision
CryptaVault is a zero-knowledge cryptographic framework — not a storage application. It sits between users and storage providers, enforcing:
1. Client-side encryption (keys never traverse network in plaintext).
2. Adaptive cryptography (user chooses speed/security tradeoff).
3. Hybrid classical + post-quantum algorithms for transition security.
4. Integrity, signatures, and Merkle-tree folder proofs.
5. Storage independence (pluggable connectors).

### 2.2 User Classes

| Class | Description | Auth |
|-------|-------------|------|
| End User | Encrypts, stores, shares files | Email/pw + OAuth + Magic Link + Passkeys |
| Admin | Manages users, audit, flags, providers | Supabase Auth + admin role (subdomain `admin.*`) |
| Auditor | Read-only access to audit logs | Supabase Auth + auditor role |
| Developer | Extends framework via plugins | SDK + plugin registry |

### 2.3 Operating Environment
- **Backend**: FastAPI (Python 3.11+) on Render/Railway/Fly.io.
- **Database / Auth**: Supabase (PostgreSQL managed, RLS enforced).
- **Web Client**: Static React SPA on Vercel (`app.cryptavault.app`).
- **Admin Console**: Static React SPA on Vercel (`admin.cryptavault.app`).
- **WASM Crypto**: Pyodide/PyScript-packaged crypto core + oqs-wasm for PQ.
- **CLI**: Python wheel via pip.
- **Browsers**: Evergreen Chrome, Firefox, Safari (WASM + WebCrypto + WebAuthn).

### 2.4 Constraints
- 4-month minor project duration (single developer).
- Zero-knowledge boundary: backend never receives plaintext or keys.
- All cryptography must be library-backed (cryptography, liboqs) — no hand-rolled primitives in production paths.
- Supabase free tier limits apply during development.

### 2.5 Assumptions
- liboqs builds successfully on the developer's platform (or Docker dev container fallback).
- OAuth providers approve test-mode apps within Week 1.
- oqs-wasm is available for browser PQ crypto (or graceful fallback to classical-only in web client).
- Admin and user apps deployed on separate subdomains for cookie scoping.

---

## 3. Functional Requirements

### 3.1 Authentication (FR-AUTH)
| ID | Requirement |
|----|-------------|
| FR-AUTH-01 | System SHALL support email + password authentication with rate limiting. |
| FR-AUTH-02 | System SHALL support Google OAuth via Supabase Auth. |
| FR-AUTH-03 | System SHALL support GitHub OAuth. |
| FR-AUTH-04 | System SHALL support Microsoft (Entra ID) OAuth. |
| FR-AUTH-05 | System SHOULD support Apple Sign-In (nice-to-have). |
| FR-AUTH-06 | System SHALL support magic link (passwordless email). |
| FR-AUTH-07 | System SHALL support passkeys/WebAuthn. |
| FR-AUTH-08 | System SHALL issue HMAC-signed session cookies (15-min access / 7-day refresh). |
| FR-AUTH-09 | System SHALL revoke sessions on logout. |
| FR-AUTH-10 | Admin endpoints SHALL require `role=admin` verified server-side. |

### 3.2 User Management (FR-USER)
| ID | Requirement |
|----|-------------|
| FR-USER-01 | System SHALL provide profile (display_name, quota, role). |
| FR-USER-02 | Users SHALL update own display_name. |
| FR-USER-03 | Admins SHALL list/suspend/delete users. |
| FR-USER-04 | Admins SHALL edit user quota. |
| FR-USER-05 | Admins SHALL impersonate users (10-min token, audited `impersonated_by`). |
| FR-USER-06 | Role escalation SHALL be denied for non-admins. |

### 3.3 Key Management (FR-KEYS)
| ID | Requirement |
|----|-------------|
| FR-KEYS-01 | System SHALL generate keys hierarchically: master → data → share → session. |
| FR-KEYS-02 | Master key SHALL be derived via Argon2id from password **client-side**. |
| FR-KEYS-03 | Keystore SHALL be encrypted with AES-256-GCM keyed by Argon2id(password, salt). |
| FR-KEYS-04 | System SHALL support key rotation; old keys RETIRED (decrypt old, not encrypt new). |
| FR-KEYS-05 | System SHALL support key versioning with backward compatibility. |
| FR-KEYS-06 | System SHALL support key destruction (memory overwrite + DESTROYED mark). |
| FR-KEYS-07 | System SHALL export/import keys via PKCS#8 PEM (asymmetric) and raw bytes (symmetric, with warning). |
| FR-KEYS-08 | System SHALL reject import of weak keys (<256-bit symmetric, <2048-bit RSA). |
| FR-KEYS-09 | System SHALL support 24-word mnemonic backup (BIP-39 style) of master key. |
| FR-KEYS-10 | Recovery SHALL require correct mnemonic; wrong words rejected. |
| FR-KEYS-11 | Keys SHALL NEVER traverse network in plaintext. |

### 3.4 Adaptive Security (FR-ADAPT)
| ID | Requirement |
|----|-------------|
| FR-ADAPT-01 | System SHALL provide 5 security profiles: PERFORMANCE, STANDARD, BALANCED, STRONG, MAXIMUM. |
| FR-ADAPT-02 | Profiles SHALL map to algorithm combinations via plugin registry. |
| FR-ADAPT-03 | User SHALL select profile via slider (0–100%). |
| FR-ADAPT-04 | MAXIMUM profile SHALL use multi-layer encryption (AES outer + ChaCha inner). |
| FR-ADAPT-05 | MAXIMUM profile SHALL use forward-secrecy ratchet (per-file ephemeral keys). |
| FR-ADAPT-06 | MAXIMUM profile SHALL enable tamper-evident audit logging. |
| FR-ADAPT-07 | MAXIMUM profile SHALL randomize file timestamps to midnight UTC. |
| FR-ADAPT-08 | Profile SHALL persist in user config (CLI `~/.cryptavault/config.toml`). |

### 3.5 Compression (FR-COMP)
| ID | Requirement |
|----|-------------|
| FR-COMP-01 | System SHALL detect file type by magic bytes (not extension). |
| FR-COMP-02 | System SHALL skip compression for already-compressed types (JPEG, MP4, ZIP, etc.). |
| FR-COMP-03 | System SHALL support zstd, LZMA, Brotli, Gzip. |
| FR-COMP-04 | All compression SHALL be streaming (no full file in memory). |
| FR-COMP-05 | System SHALL auto-select best algorithm by ratio. |
| FR-COMP-06 | System SHALL measure and report compression ratio, time, CPU, memory. |

### 3.6 Encryption Pipeline (FR-PIPE)
| ID | Requirement |
|----|-------------|
| FR-PIPE-01 | System SHALL encrypt files in chunks (chunk size scales with file size, ≥4MB for ≥1GB files). |
| FR-PIPE-02 | Each chunk SHALL be encrypted with AEAD; chunk index in AAD for ordering. |
| FR-PIPE-03 | System SHALL use a random 96-bit file-level nonce prefix. |
| FR-PIPE-04 | System SHALL support parallel encryption via `ProcessPoolExecutor` (CLI) / Web Workers (browser). |
| FR-PIPE-05 | System SHALL resume interrupted operations from last completed chunk. |
| FR-PIPE-06 | Resumed chunks SHALL be hash-verified; mismatched re-done. |
| FR-PIPE-07 | System SHALL provide a background queue for multi-file processing. |
| FR-PIPE-08 | Queue SHALL persist state across process restart. |
| FR-PIPE-09 | Memory peak SHALL stay below 200MB for 1GB file. |
| FR-PIPE-10 | System SHALL fail-closed on any chunk tag mismatch. |

### 3.7 Signatures & Integrity (FR-SIG)
| ID | Requirement |
|----|-------------|
| FR-SIG-01 | System SHALL support ECDSA, Ed25519, Dilithium, and Hybrid (Ed25519+Dilithium) signatures. |
| FR-SIG-02 | Hybrid signature SHALL require BOTH verifications to pass. |
| FR-SIG-03 | System SHALL detect tampering, modification, and corruption distinctly. |
| FR-SIG-04 | Per-file integrity SHALL use BLAKE3 by default (SHA-256, SHA3-512 optional). |
| FR-SIG-05 | Folder integrity SHALL use Merkle trees with O(log n) inclusion proofs. |
| FR-SIG-06 | System SHALL generate human-readable + JSON integrity reports. |
| FR-SIG-07 | Merkle tree SHALL support partial/subset verification. |

### 3.8 Metadata Protection (FR-META)
| ID | Requirement |
|----|-------------|
| FR-META-01 | Manifest SHALL encrypt: file names, folder structure, chunk count, algorithm metadata. |
| FR-META-02 | Manifest SHALL be encrypted as a whole via AES-256-GCM with metadata key (HKDF-derived). |
| FR-META-03 | MAXIMUM profile SHALL additionally encrypt file size and randomize timestamps. |
| FR-META-04 | Manifest SHALL sync only its hash to backend (body never stored plaintext server-side). |
| FR-META-05 | System SHALL securely delete temp files (overwrite + unlink). |
| FR-META-06 | System SHALL wipe memory buffers (`ctypes.memset(0)`) after use. |

### 3.9 Storage Connectors (FR-STOR)
| ID | Requirement |
|----|-------------|
| FR-STOR-01 | System SHALL provide a `StorageConnector` ABC for all storage providers. |
| FR-STOR-02 | System SHALL implement connectors for Local, SFTP, FTP, Google Drive, OneDrive, Dropbox. |
| FR-STOR-03 | Connectors SHALL accept streams (no full-file load). |
| FR-STOR-04 | Connectors SHALL handle OAuth flows for cloud providers. |
| FR-STOR-05 | Large uploads (≥100MB) SHALL use resumable/chunked upload protocols. |
| FR-STOR-06 | System SHALL auto-detect connector from URI scheme (`local://`, `sftp://`, `gdrive://`, etc.). |
| FR-STOR-07 | Storage providers SHALL never receive plaintext or encryption keys. |

### 3.10 Secure Sharing (FR-SHARE)
| ID | Requirement |
|----|-------------|
| FR-SHARE-01 | System SHALL generate encrypted share packages (ciphertext + wrapped key + signature + proof). |
| FR-SHARE-02 | System SHALL support one-time access tokens (single-use, expiry, signed). |
| FR-SHARE-03 | System SHALL support time-limited links (expiry timestamp server-verified). |
| FR-SHARE-04 | System SHALL support password-protected shares (Argon2id wrap). |
| FR-SHARE-05 | System SHALL generate QR codes (ASCII + PNG) for share URLs/compact packages. |
| FR-SHARE-06 | System SHALL support invitation shares (recipient public key; hybrid KEM). |
| FR-SHARE-07 | Invitation shares SHALL support multiple recipients per package. |
| FR-SHARE-08 | MAXIMUM profile invitation shares SHALL use hybrid KEM (X25519+Kyber). |

### 3.11 AI Assistant (FR-AI)
| ID | Requirement |
|----|-------------|
| FR-AI-01 | System SHALL provide a rule-based heuristic recommender (deterministic, offline). |
| FR-AI-02 | Recommender SHALL analyze file type + size + profile and recommend encryption, compression, chunk size, workers, with rationale. |
| FR-AI-03 | System SHALL support an optional pluggable LLM provider (OpenAI or Anthropic). |
| FR-AI-04 | LLM SHALL receive ONLY metadata (file_type, size, profile, concept) — NEVER plaintext, keys, contents, filenames. |
| FR-AI-05 | Data minimization SHALL be enforced by code (allowlist), not just policy. |
| FR-AI-06 | System SHALL provide a static knowledge base fallback (≥20 concepts) for offline operation. |
| FR-AI-07 | AI chat endpoint SHALL route questions to rule-based or LLM based on type. |
| FR-AI-08 | "Apply recommendation" SHALL update user profile/config. |

### 3.12 Benchmark Lab (FR-BENCH)
| ID | Requirement |
|----|-------------|
| FR-BENCH-01 | System SHALL benchmark AES, ChaCha20, RSA, ECC, Kyber, Dilithium, hybrid algorithms. |
| FR-BENCH-02 | Metrics per algorithm SHALL include encryption speed, decryption speed, key size, sig gen/verify time, CPU, memory. |
| FR-BENCH-03 | System SHALL parameterize benchmarks by payload size (1KB, 1MB, 100MB, 1GB) + iterations. |
| FR-BENCH-04 | Results SHALL export as CSV and JSON. |
| FR-BENCH-05 | Web UI SHALL render comparison bar charts and tables. |

### 3.13 Dashboard (FR-DASH)
| ID | Requirement |
|----|-------------|
| FR-DASH-01 | User dashboard SHALL display live metrics during encrypt/upload (speed, CPU, RAM, encryption rate, compression ratio). |
| FR-DASH-02 | Metrics SHALL stream via SSE (≤2s latency). |
| FR-DASH-03 | Dashboard SHALL display profile selector with algorithm matrix. |
| FR-DASH-04 | Dashboard SHALL show job queue with status. |
| FR-DASH-05 | Dashboard SHALL show estimated brute-force resistance (classical + PQ bits, color-coded). |

### 3.14 Admin Console (FR-ADMIN)
| ID | Requirement |
|----|-------------|
| FR-ADMIN-01 | Admin console SHALL be a React SPA on subdomain `admin.cryptavault.app`. |
| FR-ADMIN-02 | Admin SHALL manage users (list, suspend, delete, edit quota, impersonate). |
| FR-ADMIN-03 | Admin SHALL view audit logs (filterable by user, operation, date, outcome). |
| FR-ADMIN-04 | Admin SHALL export audit logs as CSV. |
| FR-ADMIN-05 | Admin SHALL revoke user sessions. |
| FR-ADMIN-06 | Admin SHALL configure org-wide storage provider credentials. |
| FR-ADMIN-07 | Admin SHALL toggle feature flags (`enable_pq`, `enable_passkeys`, etc.). |
| FR-ADMIN-08 | Flag changes SHALL take effect immediately (middleware check). |
| FR-ADMIN-09 | Admin SHALL view system health (Supabase status, API latency p50/p95, queue depth, provider reachability). |
| FR-ADMIN-10 | Admin SHALL view reports (signups/day, encrypt ops/day, storage used, benchmark aggregates). |
| FR-ADMIN-11 | Impersonation SHALL be audited with `impersonated_by` field and 10-min token expiry. |
| FR-ADMIN-12 | Admin endpoints SHALL enforce rate limit (30 req/min). |

### 3.15 CLI (FR-CLI)
| ID | Requirement |
|----|-------------|
| FR-CLI-01 | CLI SHALL provide commands: init, upload, download, verify, share, receive, keys (subcommands), profile (subcommands), benchmark run, dashboard. |
| FR-CLI-02 | CLI SHALL use `rich` for tables and progress bars. |
| FR-CLI-03 | Each command SHALL have complete `--help`. |

### 3.16 Plugin Architecture (FR-PLUG)
| ID | Requirement |
|----|-------------|
| FR-PLUG-01 | System SHALL provide plugin registries for: StorageConnector, CompressionAlgorithm, HashAlgorithm, EncryptionAlgorithm, SignatureAlgorithm, KemAlgorithm, KdfAlgorithm, AiProvider. |
| FR-PLUG-02 | Plugins SHALL register via `@register_*` decorators or entry-point group `cryptavault.plugins`. |
| FR-PLUG-03 | Core SHALL import implementations only via registry (no direct imports of specific algos). |

### 3.17 Web Client / Zero-Knowledge (FR-WEB)
| ID | Requirement |
|----|-------------|
| FR-WEB-01 | Web client SHALL perform encryption/decryption client-side via WebAssembly. |
| FR-WEB-02 | Keys SHALL be generated, stored (encrypted), and used entirely in browser. |
| FR-WEB-03 | Keys SHALL NEVER be sent to backend in plaintext. |
| FR-WEB-04 | Web client SHALL derive master key from password via Argon2id in WASM. |
| FR-WEB-05 | Browser keystore SHALL persist encrypted (localStorage/IndexedDB); decrypted in memory only on unlock. |

---

## 4. Non-Functional Requirements

### 4.1 Performance (NFR-PERF)
| ID | Requirement |
|----|-------------|
| NFR-PERF-01 | 1GB file encrypt+decrypt SHALL complete with peak memory < 200MB. |
| NFR-PERF-02 | Parallel encryption SHALL achieve ≥2x speedup on 4-core CPU vs serial. |
| NFR-PERF-03 | SSE metrics latency SHALL be ≤2 seconds. |
| NFR-PERF-04 | API p95 latency SHALL be < 500ms (excluding file transfer). |
| NFR-PERF-05 | Argon2id derivation SHALL run in ≤100ms on target hardware. |
| NFR-PERF-06 | Benchmark suite SHALL complete in ≤10 minutes. |

### 4.2 Security (NFR-SEC)
| ID | Requirement |
|----|-------------|
| NFR-SEC-01 | All crypto SHALL use vetted libraries (cryptography, liboqs); no hand-rolled primitives in production. |
| NFR-SEC-02 | Tag comparison SHALL be constant-time. |
| NFR-SEC-03 | All verification failures SHALL fail-closed (no partial/default decryption). |
| NFR-SEC-04 | TLS 1.3 for all network communication; HSTS enabled. |
| NFR-SEC-05 | RLS SHALL isolate user data in database. |
| NFR-SEC-06 | Admin endpoints SHALL require admin role verified server-side. |
| NFR-SEC-07 | Audit log SHALL be tamper-evident (hash chain + master-key signature). |
| NFR-SEC-08 | LLM data minimization SHALL be code-enforced (allowlist). |
| NFR-SEC-09 | Rate limiting SHALL prevent brute-force (>1000 req/min per user → block; >20/min on auth). |
| NFR-SEC-10 | PBKDF2 iteration count SHALL meet OWASP minimum (600,000 for SHA-256). |

### 4.3 Reliability (NFR-REL)
| ID | Requirement |
|----|-------------|
| NFR-REL-01 | Interrupted operations SHALL resume from last completed chunk. |
| NFR-REL-02 | Queue state SHALL persist across process restart. |
| NFR-REL-03 | System SHALL handle connector failure with retry. |

### 4.4 Portability (NFR-PORT)
| ID | Requirement |
|----|-------------|
| NFR-PORT-01 | Backend SHALL run on Python 3.11 and 3.12. |
| NFR-PORT-02 | Web client SHALL run on evergreen Chrome, Firefox, Safari. |
| NFR-PORT-03 | WASM Shall load successfully on all supported browsers. |
| NFR-PORT-04 | CLI SHALL install via pip on Linux, macOS, Windows. |

### 4.5 Maintainability (NFR-MAINT)
| ID | Requirement |
|----|-------------|
| NFR-MAINT-01 | Code SHALL pass ruff (lint), black (format), mypy (typecheck). |
| NFR-MAINT-02 | Frontend SHALL pass eslint + prettier + tsc. |
| NFR-MAINT-03 | All public functions SHALL have type annotations. |
| NFR-MAINT-04 | Test coverage target: ≥80% for crypto core. |

### 4.6 Usability (NFR-UX)
| ID | Requirement |
|----|-------------|
| NFR-UX-01 | All 7 auth methods SHALL be discoverable from a single login page. |
| NFR-UX-02 | Dashboard SHALL show clear profile + algorithm matrix. |
| NFR-UX-03 | Upload SHALL show progress bar + cancel option. |
| NFR-UX-04 | CLI SHALL provide table-formatted output via `rich`. |

---

## 5. External Interface Requirements

### 5.1 User Interfaces
- **Web Client** (React): login, dashboard, files, shares, benchmarks, profile pages.
- **Admin Console** (React + shadcn/ui): dashboard, users, sessions, audit, flags, providers, health, reports pages.
- **CLI** (Typer + Rich): command-line interface.

### 5.2 Hardware Interfaces
- Filesystem / external drives via Local connector.
- SFTP servers via Paramiko.
- USB devices via Local connector (mounted path).

### 5.3 Software Interfaces
- **Supabase**: PostgreSQL, Auth, RLS.
- **liboqs**: Kyber + Dilithium (server + WASM).
- **Storage providers**: Google Drive, OneDrive, Dropbox
- **OAuth providers**: Google, Microsoft, GitHub, Apple (auth).
- **LLM providers** (optional): OpenAI, Anthropic

### 5.4 Communications Interfaces
- REST + JSON over HTTPS (TLS 1.3) for API.
- SSE for live metrics.
- WebSocket (optional, future).
- OAuth 2.0 flows for cloud auth.
- WebAuthn/Passkeys via browser.

---

## 6. System Architecture

See `ARCHITECTURE.md` for full architecture, module map, data flow diagram, deployment topology, and plugin interface contracts.

Key points:
- Monorepo: `packages/{core,api,web,admin,wasm,cli}`.
- Zero-knowledge boundary: crypto runs client-side (WASM in browser / native in CLI).
- API = coordination layer (FastAPI + Supabase).
- Plugin registry for all pluggable components.

---

## 7. Database Requirements

See `ARCHITECTURE.md` Section 5 (Database Schema) for full SQL DDL + RLS policies.

Tables:
- `profiles` (extends `auth.users`): display_name, role, quota, suspended.
- `key_manifests`: encrypted_manifest (bytea), nonce, hash.
- `share_tokens`: file_ref, wrapped_key, expiry, max_uses, password_hash.
- `audit_log`: hash-chained, signed.
- `benchmark_results`: per-algo metrics.
- `feature_flags`: toggleable flags.
- `sessions`: includes impersonation tracking.

RLS: users see own data; admins see all; auditors see audit_log only. No plaintext keys in DB.

---

## 8. Security Requirements

### 8.1 Threat Model
| Threat | Mitigation |
|--------|-----------|
| Storage provider reads plaintext | Client-side encryption; provider sees only ciphertext |
| Backend server compromised | No keys stored server-side; manifests encrypted with client-derived key |
| Database breached | RLS isolates; manifests + tokens encrypted; no plaintext keys |
| MITM | TLS 1.3 + HSTS |
| Admin impersonates user | Audited; short-lived tokens; admin role |
| LLM data leak | Code-enforced data minimization (allowlist) |
| OAuth compromise | Token rotation; minimal scopes; revoke on detection |
| Password brute-force | Argon2id; rate limiting; passkeys |

### 8.2 Crypto Standards
- AES-256-GCM (FIPS 197), ChaCha20-Poly1305 (RFC 8439).
- X25519 (RFC 7748), Ed25519 (RFC 8032), RSA-4096 OAEP/PSS.
- SHA-256/SHA3-512 (FIPS 202), BLAKE3.
- Argon2id, PBKDF2-SHA256 (600k iter), HKDF-SHA256 (RFC 5869).
- Kyber KEM (FIPS 203), Dilithium sig (FIPS 204) via liboqs.

### 8.3 Key Management
- Hierarchical keys; master from Argon2id(password) client-side; data keys wrapped.
- Rotation with RETIRED state for backward compatibility.
- Mnemonic backup (24-word BIP-39-style).
- Secure deletion best-effort with honest documentation.

---

## 9. Cryptographic Requirements

### 9.1 Algorithm Matrix per Profile

| Profile | % | Symmetric | KEM | Sig | Hash | KDF |
|---------|---|-----------|-----|-----|------|-----|
| PERFORMANCE | 0–20 | AES-128-GCM | X25519 | ECDSA-P256 | SHA-256 | PBKDF2 |
| STANDARD | 20–50 | AES-256-GCM | X25519 | ECDSA-P256 | SHA-256 | Argon2id |
| BALANCED | 35–65 | AES-256-GCM | X25519 | Ed25519 | SHA-256 | Argon2id |
| STRONG | 50–80 | AES-256 + ChaCha20 | X25519 | Ed25519 | SHA-256 | Argon2id |
| MAXIMUM | 80–100 | AES-256 + ChaCha20 | Hybrid (X25519+Kyber768) | Hybrid (Ed25519+Dilithium3) | SHA3-512/BLAKE3 | Argon2id |

### 9.2 Hybrid Constructions
- Hybrid KEM: `shared_secret = HKDF(ecdh_secret ‖ kyber_secret)`.
- Hybrid Sig: both Ed25519 AND Dilithium must verify.

### 9.3 Forward Secrecy
- At-rest approximation via ratcheted per-file keys (HKDF with counter salt).
- Honest documentation: true FS is a session property; ratchets approximate for at-rest.

### 9.4 KAT Validation
- All primitives SHALL pass NIST/Wycheproof KAT vectors.
- PQ primitives SHALL pass NIST PQC test vectors.
- Hypothesis property tests SHALL cover all round-trips.

---

## 10. Performance Requirements

See NFR-PERF-01 through NFR-PERF-06.

---

## 11. AI Assistant Requirements

See FR-AI-01 through FR-AI-08.

Critical constraint: data minimization enforced by code (allowlist of fields sent to LLM).

---

## 12. Admin Console Requirements

See FR-ADMIN-01 through FR-ADMIN-12 and NFR-SEC-06, NFR-SEC-12.

---

## 13. API Requirements

See ARCHITECTURE.md Section 6 (API Surface) for full route table.

Key requirements:
- REST + JSON; OpenAPI at `/docs`.
- All endpoints require auth (except public health + share consume).
- Rate limited + Pydantic-validated.
- RBAC enforced.
- SSE for live metrics.
- Request-id propagation; structured JSON logs.

---

## 14. Plugin Architecture Requirements

See FR-PLUG-01 through FR-PLUG-03 and ARCHITECTURE.md Section 7 (Plugin Interface Contracts).

---

## 15. Acceptance Criteria

The project is accepted when ALL of these are met:

| # | Criterion | Mapped Requirements |
|---|-----------|---------------------|
| AC-01 | All 7 auth methods work in browser | FR-AUTH-01 through FR-AUTH-07 |
| AC-02 | Zero-knowledge: keys never traverse network in plaintext | FR-WEB-02, FR-KEYS-11, NFR-SEC-09 |
| AC-03 | 1GB file encrypt+decrypt with < 200MB peak memory | NFR-PERF-01 |
| AC-04 | Parallel speedup ≥2x on 4-core | NFR-PERF-02 |
| AC-05 | Resume interrupted ops from last chunk | NFR-REL-01, FR-PIPE-05 |
| AC-06 | 5 profiles resolve to correct algorithm configs | FR-ADAPT-01 through FR-ADAPT-03 |
| AC-07 | Kyber + Dilithium KATs pass | NFR-SEC-01, crypto requirements |
| AC-08 | Hybrid KEM/sig require both halves | FR-SIG-02, crypto requirements |
| AC-09 | Merkle verify works on 1000 leaves with tamper detection | FR-SIG-05 |
| AC-10 | All share modes work (one-time, time-limited, password, QR, invitation) | FR-SHARE-01 through FR-SHARE-08 |
| AC-11 | ≥5 storage connectors round-trip 50MB | FR-STOR-02 |
| AC-12 | Browser crypto round-trips 100MB file; keys stay in browser | FR-WEB-01 through FR-WEB-05 |
| AC-13 | Admin CRUD + RBAC + impersonation audited | FR-ADMIN-01 through FR-ADMIN-12 |
| AC-14 | Benchmark suite runs all algos; exports CSV/JSON; web charts render | FR-BENCH-01 through FR-BENCH-05 |
| AC-15 | Live metrics stream ≤2s latency | FR-DASH-02, NFR-PERF-03 |
| AC-16 | AI recommender correct across 15 scenarios; LLM no data leak | FR-AI-02, FR-AI-04, FR-AI-05 |
| AC-17 | E2E matrix 216 scenarios pass | all FRs |
| AC-18 | 16 research notes annotated + cited | (academic deliverable) |
| AC-19 | Final report submission-ready with benchmarks + threat model | (academic deliverable) |
| AC-20 | Demo reproducible; tag v1.0.0 | (release) |

---

## 16. Constraints & Assumptions

See ARCHITECTURE.md and RISKS.md.

Key constraints:
- 4-month single-developer project.
- Supabase free tier during dev.
- liboqs build availability.

---

## 17. Out of Scope

Explicitly NOT in this version (future work):
- Tunnel-based transfer (WebRTC/QUIC/WireGuard).
- HSM/TPM integration.
- Multi-device encrypted sync.
- Threshold cryptography.
- Team workspaces with full RBAC (lite admin only here).
- IPFS / decentralized storage.
- Encrypted searchable indexes.
- Native mobile clients.
- Enterprise policy + compliance reporting.
- Multi-language SDKs (Python core + TS web ARE the first SDKs).
- Azure Blob, MinIO, WebDAV, SMB, NAS, custom REST storage impls (plugin interface supports them).
- SMS OTP (passkeys/WebAuthn preferred).

---

## 18. Glossary

| Term | Definition |
|------|------------|
| AEAD | Authenticated Encryption with Associated Data (e.g., GCM, ChaCha20-Poly1305). |
| Argon2id | Memory-hard password hashing (PHC winner). |
| BLAKE3 | Fast hash with tree mode + keyed hashing. |
| CBOR | Concise Binary Object Representation (binary JSON alternative). |
| ChaCha20-Poly1305 | Stream cipher + MAC (RFC 8439). |
| DH / ECDH | (Elliptic Curve) Diffie-Hellman key exchange. |
| Dilithium | Lattice-based PQ signature (FIPS 204). |
| Forward Secrecy (FS) | Compromise of long-term keys doesn't reveal past session keys. |
| HKDF | HMAC-based Key Derivation Function (RFC 5869). |
| KAT | Known Answer Test (vectors validating crypto correctness). |
| KEM | Key Encapsulation Mechanism (e.g., Kyber). |
| KMS | Key Management System. |
| Kyber | Lattice-based PQ KEM (FIPS 203). |
| Merkle Tree | Hash tree enabling O(log n) integrity proofs. |
| OAEP / PSS | RSA encryption / signature padding schemes. |
| Passkey | WebAuthn-based passwordless credentials. |
| PQ / PQC | Post-Quantum Cryptography / Cryptography. |
| RLS | Row-Level Security (PostgreSQL / Supabase). |
| Shor's Algorithm | Quantum algorithm that breaks RSA/ECDH. |
| SSE | Server-Sent Events (HTTP streaming). |
| Supabase | Open-source Firebase alternative on PostgreSQL. |
| WASM | WebAssembly — bytecode sandbox in browsers. |
| WebAuthn | Web Authentication API for passkeys/security keys. |
| Wycheproof | Google's crypto API misuse test vectors. |
| Zero-Knowledge | Service provider cannot access user data (keys + plaintext never leave client). |

---

_End of SRS.md_