# Phase P6 — Intelligent Compression Engine (Week 8)

## Objective
Build file-type detection by magic bytes, skip-compression policy (avoid already-compressed files), four compression algorithms (zstd/LZMA/Brotli/Gzip) with streaming, ratio measurement, and pipeline integration as a stage.

## Prerequisites
- P5 (Engine Gate) — profile informs compression policy.

## Tasks

### Task 6.1 — File Type Detection
**Files**: `packages/core/cryptavault/compression/detect.py`
**Action**:
- `detect_file_type(path) -> FileType` via magic bytes (not extension). Enum: `IMAGE_JPEG`, `VIDEO_MP4`, `ARCHIVE_ZIP`, `TEXT`, `BINARY_UNKNOWN`.
- Signature table for already-compressed: JPEG, PNG, GIF, MP4, ZIP, GZIP, XZ, ZST, BROTLI, RAR, 7Z, MP3, AAC, HEIC.
**Verify**: Detect JPEG, MP4, ZIP, plain text, unknown binary.
**Done**: ≥30 file types detected; skip list documented.

### Task 6.2 — Skip-Compression Decision Logic
**Files**: `packages/core/cryptavault/compression/policy.py`
**Action**:
- `should_compress(file_type, path, profile) -> bool`: False for already-compressed; sample 1MB for unknown; compress if ratio < 0.95.
- Profile ties: PERFORMANCE fast sample; MAXIMUM full sample.
**Verify**: JPEG → False; plain text → True; random.bin → False; small text → True.
**Done**: Correct across 20 diverse file types; threshold documented.

### Task 6.3 — Compression Algorithms
**Files**: `packages/core/cryptavault/compression/algorithms.py`
**Action**:
- `Zstd`, `Lzma`, `Brotli`, `Gzip` classes: `compress(stream) -> stream`, `decompress(stream) -> stream`. Streaming (file-like or generators; no full file in memory).
- Auto-select best by ratio (zstd default; if >0.7 use LZMA).
- Register each as `CompressionAlgorithm` plugin.
**Verify**: Round-trip each; 1GB → no OOM; ratio test on 100MB random text.
**Done**: All round-trip; streaming confirmed; auto-selection picks best.

### Task 6.4 — Compression Ratio Measurement
**Files**: `packages/core/cryptavault/compression/metrics.py`
**Action**:
- `measure(algo, data) -> CompressionMetrics {ratio, time_ms, cpu_pct, mem_peak_mb}`.
- Export to dashboard + report as CSV.
**Verify**: Sane values; ratio matches manual calculation.
**Done**: Metrics accurate; CSV export.

### Task 6.5 — Compression in Pipeline Integration
**Files**: `packages/core/cryptavault/pipeline/compression_stage.py`
**Action**:
- `CompressionStage.run(input_stream, file_metadata, profile) -> (output_stream, compression_metadata)`.
- If `should_compress` False → pass-through with `compression=None`; else compress + record metadata.
**Verify**: JPEG → pass-through; text → compressed with ratio in metadata.
**Done**: E2E integration test across JPEG + text.

## Phase Gate Criteria (Compression Gate)
- [ ] ≥30 magic-byte signatures detected
- [ ] Skip policy works (JPEG skip, text compress)
- [ ] 4 algorithms round-trip with streaming (1GB no OOM)
- [ ] Metrics captured for dashboard
- [ ] Pipeline stage integrates with policy

## AI Assistant Parallel Hook
- Rule-based recommender (P15.1) will consume `detect_file_type` + `should_compress` — design `should_compress` to be callable standalone.