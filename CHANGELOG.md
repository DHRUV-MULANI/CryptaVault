# CryptaVault Changelog

All notable changes to the CryptaVault project are documented in this file.
The project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-11-08

### Dynamic Multi-User Stack: Web, API, Neon and Remote CLI

#### Backend and persistence
- Replaced the static Supabase-oriented coordination path with local accounts, PBKDF2 verifiers, JWT sessions, and an SQLAlchemy persistence layer.
- Added Neon Postgres metadata for users, vault bootstrap, workspaces, roles, quotas, file versions, encrypted manifests, wrapped keys, shares, storage targets, settings, and admin state.
- Added authenticated routes for auth/profile, workspaces/members, encrypted upload/version/download, rename, trash/restore/permanent delete, shares, storage health, dashboard, and admin.
- Added per-user quota enforcement, workspace RBAC, share expiry/use-limit/revocation enforcement, passphrase share checks, storage target fallback, and service health/readiness endpoints.
- Enforced administrator feature flags: sharing, version history, cloud connectors, and maintenance-mode write pauses now change route behavior instead of being display-only.
- Made deletion share-safe and quota-correct: deleting a workspace or file removes its shares first, and ciphertext bytes are refunded to the user who created each version.
- Rejected share creation with a non-future expiry and added manifest support to the share QR endpoint.
- Added S3-compatible ciphertext storage with a working SeaweedFS local target and config-ready cloud connectors.

#### Web client
- Reworked the React portal into a dynamic client: remote login/register/unlock, JWT sessions, workspace switching, remote file upload/download, version restore, trash, rename, server shares, public share viewer, live dashboard, workspace management, admin console, settings, and status diagnostics.
- Standardized the browser `CVW1` container: PBKDF2-SHA256 vault derivation, per-file AES-256-GCM keys, chunk AAD, optional gzip, sealed metadata manifests, wrapped keys, and SHA-256 verification.
- Added server-share manifests with capability and passphrase modes; generated links are stored locally because the server never receives decryptable URL material.

#### Remote CLI
- Added `cryptavault remote` with auth, workspace, files, and shares command groups.
- Implemented session persistence, PBKDF2 login/register, workspace selection, encrypted upload/download, immutable versions, rename, restore, trash/untrash, permanent delete, share creation, share listing/revocation, and anonymous share decryption.
- Made CLI containers and share manifests compatible with the web client, including version records and metadata AAD by file ID.

#### Documentation and verification
- Rewrote README, demo runbook, portal guide, CLI reference, and technical report for the dynamic stack.
- Added a 15-slide presentation deck and reproducible generator.
- Verified 165 Python tests, ruff, black, mypy, web typecheck, web production build, and a live web/API/Neon/SeaweedFS + CLI smoke flow.

---

## [1.1.0] - 2026-11-07

### Deployable Portal, Six Profiles, and Crypto Catalog

#### Web portal
- Replaced the prototype web client with a complete zero-knowledge portal: local vault creation and unlock, file encryption, chunked AES-256-GCM, optional gzip, encrypted manifests, wrapped per-file keys, rename/delete, self-contained share links, encrypted share bundles, share viewer, encrypted local messages, catalog browser, academy, admin console, settings, and diagnostics.
- Added IndexedDB persistence, passphrase rotation, encrypted backup export/restore, local audit log, auto-lock, policy flags, and browser crypto self-test.
- Added Tailwind/PostCSS/Vite configuration and hash routing for static hosting.
- Added automatic GitHub Pages deployment for every push to `main`.

#### Profiles and catalog
- Added the sixth `PQ_STRONG` profile (80–90 slider) with SHA3-512, hybrid KEM/signatures, and forward secrecy.
- Updated CLI profile listings, slider resolution, API security badges, and tests for all six bands.
- Added `/api/crypto/catalog`, `/api/crypto/catalog/{algorithm_id}`, and `/api/crypto/profiles`.
- Added a generated web catalog snapshot with 88 algorithms across 9 families and stable wire IDs.
- Added the catalog export script and expanded CORS for the Pages origin.

#### Documentation and quality
- Rewrote the README with architecture, installation, CLI, portal, and feature documentation.
- Added portal, CLI, deployment, catalog, container format, security model, and API references.
- Verified 161 tests, ruff, black, mypy, web/admin typecheck, and monorepo builds.

---

## [1.0.0] - 2026-09-05

### Production Release — Full Ecosystem Integration

#### Phase P13: Admin Governance & Server Enforcement
- Implemented `/api/admin/users`, `/api/admin/impersonate/{user_id}`, `/api/admin/flags`, and `/api/admin/health` in `packages/api`.
- Added strict RBAC validation with audit trail logging for administrative impersonation.
- Created dynamic feature flag toggles (Enable Post-Quantum, Require 2FA, Strict ZK).

#### Phase P14: Comparative Benchmark Lab & Live Telemetry
- Created `BenchmarkSuite` in `packages/core/cryptavault/benchmark/suite.py` measuring throughput, latency, key sizes, memory, and NIST security levels across:
  - AES-256-GCM (Hardware AES-NI)
  - ChaCha20-Poly1305 (Constant-Time)
  - BLAKE3 (Tree Hash AVX2)
  - SHA-256 (FIPS 180-4)
  - ML-KEM-768 (Kyber-768 / FIPS 203)
  - ML-DSA-65 (Dilithium-3 / FIPS 204)
  - Hybrid KEM (X25519 + Kyber768)
  - Argon2id (RFC 9106)
- Built `/api/metrics/benchmark`, `/api/metrics/security-badge`, and `/api/metrics/stream` (Server-Sent Events real-time telemetry).

#### Phase P15: AI-Assisted Security Advisory
- Implemented `RuleBasedRecommender.advise()` evaluating 15 known data scenarios.
- Curated offline cryptographic knowledge base with 20+ primitives, standards, and concepts.
- Enforced code-level data minimization via `SanitizedMetadata`: zero file contents, private paths, or encryption keys are ever transmitted.
- Added CLI commands: `cryptavault ai advise <file>`, `cryptavault ai explain <concept>`, `cryptavault ai concepts`.

#### Phase P16: Final Integration, Quality Gates & Academic Documentation
- Generated academic report (`docs/REPORT.md`), CLI reference guide (`docs/cli.md`), and reproducible showcase demo script (`docs/demo.md`).
- Unified end-to-end integration test suite (`test_milestone4.py`) with 130 passing tests across the repository.
- Verified strict zero-knowledge invariants and zero static type checking or linting errors.

---

## [0.3.0] - Milestone 3: Storage & Secure Sharing
- Implemented FastAPI Zero-Knowledge backend with Supabase Auth session management.
- Added encrypted user manifest synchronization (`/api/users/me/manifest`) with BLAKE3 tamper detection.
- Developed multi-backend storage connectors: `LocalStorage` (atomic safe writes), `SupabaseStorage` (`vaults` bucket), `SftpStorage` (Paramiko streaming), `FtpStorage` (FTPS explicit TLS), and Cloud storage stubs.
- Built zero-knowledge sharing engine with HMAC-SHA256 one-time access tokens, timed share links, Argon2id password wrapping, and ASCII/PNG QR code rendering.
- Connected React Web Client (`packages/web`) and Admin Governance Console (`packages/admin`) with Turborepo.

---

## [0.2.0] - Milestone 2: Adaptive Engine & Streaming Pipeline
- Implemented 5-tier adaptive security engine (`PERFORMANCE`, `BALANCED`, `STRONG`, `MAXIMUM`) with continuous slider mapping (0.0% to 100.0%).
- Added intelligent magic-byte header detection and entropy analysis for adaptive compression (Zstandard, Snappy, Deflate).
- Built chunked streaming AEAD encryption/decryption pipeline with fail-closed container headers and BLAKE3 Merkle Tree audit roots.
- Implemented DoD 5220.22-M 3-pass overwrite secure file shredding with `fsync`.

---

## [0.1.0] - Milestone 1: Core Cryptography & KMS
- Implemented classical authenticated symmetric encryption (AES-256-GCM, ChaCha20-Poly1305).
- Integrated native `liboqs` post-quantum primitives: Kyber-768 (ML-KEM) and Dilithium-3 (ML-DSA).
- Created AND-composition post-quantum hybrid KEM (X25519 + Kyber-768) and dual digital signatures (Ed25519 + Dilithium-3).
- Built 3-tier Key Management Service (KMS), encrypted keystore envelopes, and BIP-39 24-word mnemonic phrase disaster recovery.
- Scaffolding of Typer/Rich CLI and monorepo workspace.
