# Phase P7 — High-Speed Streaming Encryption Pipeline (Week 9)

## Objective
Build the chunked streaming encryption pipeline handling large files (1GB+) without full-file load: chunked AEAD encryption, parallel workers, resume of interrupted operations, background queue, and the orchestrator that composes all stages.

## Prerequisites
- P5 (Engine Gate) — adaptive engine provides `PipelineConfig` (chunk size, workers).
- P6 (Compression Gate) — compression stage available.
- P1 (Crypto Gate) — AEAD primitives available.

## Tasks

### Task 7.1 — Chunked Streaming Encryption
**Files**: `packages/core/cryptavault/pipeline/chunked_encryption.py`
**Action**:
- `ChunkedEncryptor.encrypt(file_stream, key, chunk_size, aad_prefix) -> EncryptedChunkStream` yielding `(nonce, ciphertext, tag)` per chunk.
- Chunk index in AAD for ordering integrity; file-level nonce prefix (random 96-bit).
- `ChunkedDecryptor` reverses; verifies per-chunk tag; fails fast on tamper.
**Verify**: 1GB round-trip; memory peak < 200MB; tamper middle chunk → fail at that chunk.
**Done**: 1GB works; memory bounded; per-chunk tamper detected.

### Task 7.2 — Parallel Encryption Workers
**Files**: `packages/core/cryptavault/pipeline/parallel.py`
**Action**:
- `ParallelChunkedEncryptor` via `ProcessPoolExecutor` with `n_workers` from profile.
- Chunks encrypted out-of-order; tagged with index for reordering on decrypt.
- Worker processes receive key via `multiprocessing` shareable memory or sealed bytes (NOT command line).
**Verify**: 1GB parallel vs serial → ≥2x speedup on 4-core; output bitwise identical; tamper detection intact.
**Done**: Speedup measured; output identical to serial; documented benchmarks.

### Task 7.3 — Resume Interrupted Operations
**Files**: `packages/core/cryptavault/pipeline/resume.py`
**Action**:
- `OperationManifest`: per-file state (completed chunk indices + hashes, key id, profile).
- On resume: skip completed; continue from next; verify each completed chunk's hash; re-do if mismatched.
**Verify**: Encrypt 1GB → kill at 50% → resume completes; corrupt completed chunk → re-done.
**Done**: Resume works; corrupted chunks re-done; integrity verified.

### Task 7.4 — Background Queue
**Files**: `packages/core/cryptavault/pipeline/queue.py`
**Action**:
- `PipelineQueue`: enqueue `(file_path, profile, storage_target)`; worker processes; status callbacks.
- API: `enqueue`, `list_pending`, `cancel(job_id)`, `status(job_id)`.
- Persist queue state to survive restart.
**Verify**: Enqueue 3 files → all complete; cancel mid-flight → cleaned up; restart → pending resume.
**Done**: Multi-file handled; cancellation clean; persisted restart works.

### Task 7.5 — Pipeline Orchestrator
**Files**: `packages/core/cryptavault/pipeline/orchestrator.py`
**Action**:
- `PipelineOrchestrator.run(file_path, profile, storage_target) -> OperationResult` threading streams through stages: compress → encrypt → sign → integrity → metadata → storage.
- Each stage emits metadata into manifest builder.
- Result includes manifest entry, metrics (time, speed, ratio), integrity root, signature.
**Verify**: E2E on 1GB through all stages; manifest sanity; decrypt reverses cleanly.
**Done**: Full pipeline E2E works; manifest complete; metrics captured.

## Phase Gate Criteria (Pipeline Gate)
- [ ] 1GB file E2E through orchestrator with < 200MB peak memory
- [ ] Parallel speedup ≥2x on 4-core
- [ ] Interrupted operations resume correctly
- [ ] Background queue handles multi-file + cancel + restart
- [ ] Decrypt reverses all stages cleanly

## Open Questions
- Browser WASM may not support `ProcessPoolExecutor` — use Web Workers for browser parallelism (P12 handles this).