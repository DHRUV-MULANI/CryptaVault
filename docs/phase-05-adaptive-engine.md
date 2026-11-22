# Phase P5 — Adaptive Security Engine (Week 7)

## Objective
Build the adaptive security engine: 5 preset profiles mapping slider % to algorithm combinations, the adaptive engine that resolves profiles to concrete pipeline configs, multi-layer encryption (MAXIMUM), forward secrecy (ratcheted per-file keys), tamper-evident audit logging, and CLI persistence.

## Prerequisites
- P3 (Integrity Gate) — signatures + Merkle available.
- P4 (KMS Gate) — key hierarchy available for engine binding.

## Tasks

### Task 5.1 — Security Profile Definition
**Files**: `packages/core/cryptavault/adaptive/profiles.py`, `docs/profiles.md`
**Action**:
- `SecurityProfile` dataclass: all algorithm fields + flags (`metadata_encryption`, `audit_logging`, `forward_secrecy`).
- Presets: `PERFORMANCE` (0–20), `STANDARD` (20–50), `BALANCED` (35–65), `STRONG` (50–80), `MAXIMUM` (80–100). See ARCHITECTURE.md Profile table.
**Verify**: Each profile initializes; slider mapping correct; invalid % → ValueError.
**Done**: 5 profiles defined; slider→profile resolution works; documented.

### Task 5.2 — Adaptive Engine Core
**Files**: `packages/core/cryptavault/adaptive/engine.py`
**Action**:
- `AdaptiveEngine.resolve(profile, file_metadata) -> PipelineConfig`: maps profile to plugin instances via registry.
- Tunable knobs: `chunk_size` scales with file size (≥4MB for ≥1GB); `parallel_workers` scales with CPU.
**Verify**: Each profile → expected config; large file → larger chunks; CPU detection → correct workers.
**Done**: Valid `PipelineConfig` for all 5 profiles; chunk/worker scaling documented.

### Task 5.3 — Multi-Layer Encryption Mode
**Files**: `packages/core/cryptavault/adaptive/engine.py`
**Action**:
- For MAXIMUM profile: encrypt data twice — inner ChaCha20-Poly1305, outer AES-256-GCM.
- Each layer: independent keys (HKDF-derived with different `info` strings).
**Verify**: Round-trip; tamper outer → detected; tamper inner → detected; Hypothesis.
**Done**: Two-layer works; either tamper detected; overhead measured.

### Task 5.4 — Forward Secrecy (Ratcheted Per-File Keys)
**Files**: `packages/core/cryptavault/adaptive/forward_secrecy.py`, `research/notes/forward_secrecy.md`
**Action**:
- `RatchetKdf`: `next_key() -> file_key` (HKDF with counter salt); `current_state() -> snapshot`.
- Each file encrypted with own key; file key wrapped by current ratchet key, stored in manifest.
- Honest doc: true FS is a session property; ratchet approximates for at-rest. Cite Signal Double Ratchet.
**Verify**: Two files → different keys; ratchet advances; compromise old state → can't derive new.
**Done**: Per-file keys unique; ratchet advances; limitation documented honestly.

### Task 5.5 — Audit Logging
**Files**: `packages/core/cryptavault/adaptive/audit.py`
**Action**:
- `AuditLog.append(entry)`: each entry includes `prev_hash`, `entry_hash`, signed by master key.
- Fields: timestamp, operation, file_id, key_id, profile, outcome, signature.
- Sync to Supabase `audit_log` table (server stores but cannot forge — client verifies chain).
**Verify**: Append→verify chain; tamper entry → invalid; missing signature → flagged.
**Done**: Append-only log verified; tamper detection; export JSON for report.

### Task 5.6 — Profile Persistence & CLI Binding
**Files**: `packages/core/cryptavault/adaptive/store.py`, `packages/cli/cryptavault_cli/commands/profile.py`
**Action**:
- `cryptavault profile set --slider 75` → STRONG preset; saves to `~/.cryptavault/config.toml`.
- `cryptavault profile list` → table of presets with algorithm matrix.
- `cryptavault profile get` → current profile.
**Verify**: Set→get round-trip; invalid slider rejected; listing matches presets.
**Done**: CLI commands work; profile persisted.

## Phase Gate Criteria (Engine Gate)
- [ ] 5 profiles resolve to correct algorithm configs
- [ ] Adaptive engine produces valid `PipelineConfig`
- [ ] Multi-layer encryption (MAXIMUM) round-trips with tamper detection
- [ ] Forward-secrecy ratchet produces unique per-file keys
- [ ] Audit log chain verifies; tamper detected
- [ ] CLI profile commands work