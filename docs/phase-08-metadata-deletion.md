# Phase P8 — Metadata Protection + Secure Deletion (Week 10)

## Objective
Define the encrypted manifest schema (filenames/sizes/structure encrypted), implement encrypted manifest round-trip, secure deletion (best-effort), and profile-driven metadata encryption toggles (including optional timestamp randomization for MAXIMUM).

## Prerequisites
- P7 (Pipeline Gate) — pipeline orchestrator exists to host manifest builder.

## Tasks

### Task 8.1 — Metadata Model
**Files**: `packages/core/cryptavault/metadata/model.py`, `docs/manifest_format.md`
**Action**:
- `FileMetadata` dataclass: `original_name`, `original_size`, `mime_type`, `created_at/modified_at`, `chunk_count`, `compression_algo`, `encryption_algo`, `iv/salt`, `key_id`, `signature`, `integrity_hash`, `merkle_proof`.
- `Manifest` dataclass: `files`, `folder_structure`, `root_hash`, `manifest_version`, `encrypted: bool`.
**Verify**: Round-trip serialization; required fields enforced; schema versioning.
**Done**: Schema complete; serialization stable; documented.

### Task 8.2 — Encrypted Manifest
**Files**: `packages/core/cryptavault/metadata/encrypted_manifest.py`
**Action**:
- Encrypt manifest with metadata key (HKDF from master with `info="metadata"`) via AES-256-GCM.
- Store as `.cryptavault-manifest.enc` on storage provider.
- Sync manifest hash to Supabase `key_manifests` table (body stays encrypted; only hash + ref stored server-side).
**Verify**: Save→load round-trip; tamper → GCM fail; wrong key → fail.
**Done**: Manifest encrypted; round-trips; tamper detected; provider sees only ciphertext filename.

### Task 8.3 — Secure Deletion of Temp Files & Memory
**Files**: `packages/core/cryptavault/metadata/secure_delete.py`, `docs/secure_deletion.md`
**Action**:
- `secure_delete_file(path)`: overwrite zeros → random → zeros; fsync; unlink.
- Memory buffers: `ctypes.memset(0)` on `bytearray` after use.
- Maintain `~/.cryptavault/tmp/`; wipe on exit.
- Document impossibility on SSDs/journaling FS; advise FDE for guarantee.
**Verify**: Temp file overwritten (inspect pre-unlink); memory buffer zeroed (read post-wipe).
**Done**: Overwrite verified; memory wipe verified; limitation documented honestly.

### Task 8.4 — Metadata Encryption Toggle & Config
**Files**: `packages/core/cryptavault/metadata/options.py`
**Action**:
- Surface `metadata_encryption` flag per profile; orchestrator respects.
- Optional fields: file size encryption, timestamp randomization (to midnight) for MAXIMUM.
**Verify**: PERFORMANCE → plaintext manifest (warn); STANDARD+ → encrypted; MAXIMUM → timestamps randomized.
**Done**: Profile toggles respected; optional fields randomized when enabled.

## Phase Gate Criteria (Metadata Gate)
- [ ] Manifest schema round-trips with all metadata fields
- [ ] Encrypted manifest GCM tag detects tamper
- [ ] Supabase `key_manifests` stores hash only (no plaintext)
- [ ] Secure deletion: temp overwritten; memory wiped
- [ ] Profile toggles respected (PERFORMANCE off; MAXIMUM randomizes timestamps)

## Risk Notes
- R6 (secure deletion impossible) — address via honest documentation, not false claims.