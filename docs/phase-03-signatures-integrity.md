# Phase P3 — Signatures + Integrity (Week 5)

## Objective
Build a uniform signature abstraction, tamper/corruption detection, per-file integrity hashing, Merkle trees for folder integrity, and an integrity report generator.

## Prerequisites
- P2 (PQ Gate) passed — hybrid signatures available.

## Tasks

### Task 3.1 — Digital Signature Abstraction Layer
**Files**: `packages/core/cryptavault/signatures/base.py`
**Action**:
- `SignatureContext` holds active algorithm + key; `sign(file_path)` streams file → hashes → signs; `verify(file_path, signature)`.
- Works across ECDSA, Ed25519, Dilithium, Hybrid (via plugin registry).
**Verify**: All four algorithms round-trip via common interface; missing keys rejected.
**Done**: One API, four backends; streaming sign of 1GB works without full load.

### Task 3.2 — Tamper & Corruption Detection
**Files**: `packages/core/cryptavault/signatures/verify.py`
**Action**:
- `verify_file(path, signature, public_key) -> VerificationResult` with enum: `VALID`, `TAMPERED`, `CORRUPTED`, `MISSING_KEY`.
- Byte modification → `TAMPERED`; truncation → `CORRUPTED`; wrong key → `MISSING_KEY`.
- Structured result with diagnostic details (which check failed, offset if detectable).
**Verify**: Flip byte at start/middle/end → `TAMPERED`; truncate → `CORRUPTED`; wrong key → `MISSING_KEY`.
**Done**: All tamper scenarios detected; result includes diagnostic info for report.

### Task 3.3 — Per-File Integrity Hashing
**Files**: `packages/core/cryptavault/integrity/file_hash.py`
**Action**:
- `compute_file_hash(path, algorithm='blake3') -> digest` streaming in 1MB chunks.
- Support SHA-256, SHA3-512, BLAKE3 via plugin registry.
- Store digest in encrypted manifest (P8).
**Verify**: Round-trip; different algorithm produces different but valid digest; 1GB file hashes without OOM.
**Done**: Streaming hash works; pluggable; 1GB test passes.

### Task 3.4 — Merkle Tree for Folders
**Files**: `packages/core/cryptavault/integrity/merkle.py`
**Action**:
- `MerkleTree`: `build(leaf_hashes) -> root`, `proof(leaf_index) -> list[bytes]`, `verify_proof(leaf, proof, root) -> bool`.
- Leaves = per-file BLAKE3; internals = SHA-256(L ‖ R). Serialize root + proof to portable format.
**Verify**: Round-trip build→proof→verify on 1000 leaves; tamper one leaf → proof fails; tamper internal → fail; Hypothesis property.
**Done**: Merkle proof works; tamper at any level detected; proof size O(log n).

### Task 3.5 — Integrity Report Generator
**Files**: `packages/core/cryptavault/integrity/report.py`
**Action**:
- `generate_report(folder_path, manifest) -> IntegrityReport`: enumerate files, verify hashes + signatures, produce table + JSON.
- Integrate Merkle proof verification for subset verification.
**Verify**: Clean folder → all VALID; tampered folder → lists each tampered file with reason.
**Done**: Report shows VALID/TAMPERED per file; JSON export; supports partial verification.

## Phase Gate Criteria (Integrity Gate)
- [ ] Signature abstraction works across all 4 algorithms
- [ ] Tamper/corruption detection covers all 3 failure modes
- [ ] Per-file hash handles 1GB without OOM
- [ ] Merkle verify works on 1000 leaves with tamper detection
- [ ] Integrity report renders human + JSON

## Open Questions
- None.