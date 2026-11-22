# Phase P1 — Classical Cryptography Core (Weeks 2–3)

## Objective
Implement all classical cryptographic primitives (symmetric, asymmetric, hash, KDF, hybrid KEM) with NIST/Wycheproof KAT validation and Hypothesis property tests.

## Prerequisites
- P0 (Setup Gate) passed — liboqs works, registry skeleton in place.

## Tasks

### Task 1.1 — Symmetric Cipher Module
**Files**: `packages/core/cryptavault/crypto/symmetric.py`, corresponding `tests/`
**Action**:
- Implement `AES256GCM` and `ChaCha20Poly1305` wrapping `cryptography.hazmat.primitives.ciphers.aead`.
- API: `encrypt(key[32], nonce[12], plaintext, aad) -> bytes`, `decrypt(...)`. Auto-generate nonce; return `(nonce, ciphertext)`. Constant-time tag comparison; `InvalidTagError` on mismatch.
- Register both as `EncryptionAlgorithm` plugins.
**Verify**: NIST GCM/Wycheproof KATs pass; Hypothesis round-trip property survives 100 examples; AAD mismatch rejects; nonce-reuse demo (negative test) confirms detection.
**Done**: All KATs green; type-complete; documented.

### Task 1.2 — Asymmetric Cipher Module
**Files**: `packages/core/cryptavault/crypto/asymmetric.py`
**Action**:
- `RSA4096`: OAEP encrypt/decrypt (SHA-256), PSS sign/verify.
- `X25519`: `exchange(private, peer_public) -> shared_secret`.
- `Ed25519`, `ECDSA(P-256/P-384)`: sign/verify.
- Uniform `KeyPair` dataclass: PEM with optional PKCS#8 password encryption.
- Register as `SignatureAlgorithm` (Ed25519, ECDSA) and `KemAlgorithm` (X25519) plugins.
**Verify**: KAT vectors pass; ECDH two-party agreement matches; signature verify rejects tampered message; PEM round-trips with/without password.
**Done**: All KATs pass; Hypothesis round-trips; PEM secure.

### Task 1.3 — Hash Module
**Files**: `packages/core/cryptavault/crypto/hash.py`
**Action**:
- `Sha256`, `Sha3512`, `Blake3` classes with `digest(data, size=None)` + streaming (`streaming()` → `update`/`finalize`).
- Register each as `HashAlgorithm` plugin.
**Verify**: NIST SHA-2/SHA-3 vectors pass; BLAKE3 official vectors pass; streaming 1GB temp file matches full-bytes hash.
**Done**: All KATs pass; streaming works; size override honored.

### Task 1.4 — KDF Module
**Files**: `packages/core/cryptavault/crypto/kdf.py`
**Action**:
- `Argon2id` (tunable: `t=3, m=64MiB, p=4`); `Pbkdf2` (600000 iterations, SHA-256); `HkdfSha256` (extract/expand/derive).
- Register each as `KdfAlgorithm` plugin.
**Verify**: RFC 5869 HKDF KATs pass; Argon2id round-trip; PBKDF2 KATs; Argon2id ≤100ms on dev hardware.
**Done**: All KATs pass; params documented; timing acceptable.

### Task 1.5 — Hybrid KEM (Classical)
**Files**: `packages/core/cryptavault/crypto/hybrid.py`
**Action**:
- `HybridKemClassical`: ephemeral X25519 → ECDH → HKDF → shared secret; ciphertext = ephemeral public key.
**Verify**: Two-party round-trip; shared secret matches both sides; ephemeral keys unique per call; Hypothesis independence.
**Done**: Round-trip works; ephemeral key generation confirmed.

## Phase Gate Criteria (Crypto Gate)
- [ ] Symmetric KATs + Hypothesis green
- [ ] Asymmetric KATs + PEM round-trip green
- [ ] Hash streaming matches full-bytes on 1GB
- [ ] KDF KATs + Argon2id timing acceptable
- [ ] Hybrid KEM classical round-trip

## Open Questions
- None — use `cryptography` lib primitives; do NOT hand-roll.