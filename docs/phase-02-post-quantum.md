# Phase P2 — Post-Quantum Cryptography (Week 4)

## Objective
Integrate liboqs Kyber KEM and Dilithium signatures, then build PQ-hybrid KEM and signature schemes combining classical + post-quantum primitives for "harvest now, decrypt later" resistance.

## Prerequisites
- P1 (Crypto Gate) passed — classical primitives (X25519, Ed25519) available.

## Tasks

### Task 2.1 — liboqs Kyber KEM Integration
**Files**: `packages/core/cryptavault/crypto/pq.py`, `packages/core/tests/kat/`
**Action**:
- Implement `KyberKem`: `keypair()`, `encapsulate(public_key) -> (ciphertext, shared_secret)`, `decapsulate(secret_key, ciphertext) -> shared_secret`.
- Support `KYBER_512/768/1024` → NIST levels 1/3/5.
- Register as `KemAlgorithm` plugin.
**Verify**: NIST PQC KAT vectors for Kyber768 & Kyber1024 pass; Hypothesis round-trip; ciphertext tampering → mismatched secret (fail-closed downstream).
**Done**: All Kyber KATs pass; tamper test confirms decapsulation yields wrong secret (downstream AEAD detects).

### Task 2.2 — liboqs Dilithium Signature Integration
**Files**: `packages/core/cryptavault/crypto/pq.py`
**Action**:
- Implement `DilithiumSig`: `keypair()`, `sign(secret_key, message)`, `verify(public_key, message, signature) -> bool`.
- Map Dilithium2/3/5 → NIST levels 1/3/5.
- Register as `SignatureAlgorithm` plugin.
**Verify**: NIST PQC KAT vectors pass; tampered message → verify failure; tampered signature → verify failure.
**Done**: All KATs pass; verify rejects single-bit flips in message or signature.

### Task 2.3 — Hybrid KEM (X25519 + Kyber)
**Files**: `packages/core/cryptavault/crypto/hybrid.py`, `research/notes/hybrid_kem.md`
**Action**:
- `HybridKemPQ`: `encapsulate(peer_public_key) -> (ciphertext, shared_secret)`; `ciphertext = (ecdh_ciphertext, kyber_ciphertext)`, `shared_secret = HKDF(ecdh_secret ‖ kyber_secret)`.
- `decapsulate(private_key, ciphertext) -> shared_secret` (dual decap, combine via HKDF).
- Public key = `(x25519_pub, kyber_pub)`; private = `(x25519_priv, kyber_priv)`.
**Verify**: Two-party round-trip; tamper ECDH component → mismatch; tamper Kyber component → mismatch; Hypothesis independence.
**Done**: Round-trip matches; either-component tamper detected; composition proof documented in `research/notes/hybrid_kem.md`.

### Task 2.4 — Hybrid Signature (Ed25519 + Dilithium)
**Files**: `packages/core/cryptavault/crypto/hybrid.py`, `research/notes/hybrid_sig.md`
**Action**:
- `HybridSigPQ`: `sign(message) -> (ed25519_sig, dilithium_sig)`; `verify(public_key, message, signature) -> bool` returns True only if BOTH pass.
- Public key = `(ed25519_pub, dilithium_pub)`.
**Verify**: Round-trip; flip one signature → fail; flip message → both fail.
**Done**: Both signatures required; either tamper → fail; documented in `research/notes/hybrid_sig.md`.

## Phase Gate Criteria (PQ Gate)
- [ ] Kyber KEM KATs pass
- [ ] Dilithium sig KATs pass
- [ ] Hybrid KEM (X25519+Kyber) round-trips; composition documented
- [ ] Hybrid Sig (Ed25519+Dilithium) requires both; either-tamper fail

## Risks
- R1 (liboqs build) — should be resolved in P0; if not, this phase is blocked.
- R2 (oqs-wasm) — only relevant when web client uses PQ in P12; if WASM unavailable, web falls back to classical + defers PQ to CLI.