# Phase P4 — Key Management System (Week 6)

## Objective
Build a hierarchical key management system (KMS) with master → data → share keys, encrypted keystore, full lifecycle (generate/rotate/version/destroy), backup/recovery (mnemonic), and interop import/export.

## Prerequisites
- P3 (Integrity Gate) passed — signing + hashing primitives available.
- P1 (Crypto Gate) — Argon2id, AES-256-GCM, HKDF available for keystore encryption.

## Tasks

### Task 4.1 — Key Hierarchy & Data Structures
**Files**: `packages/core/cryptavault/keys/hierarchy.py`
**Action**:
- Define `KeyTier`: `MASTER`, `DATA`, `SHARE`, `SESSION` (ephemeral).
- Define `KeyDescriptor` dataclass: `id`, `tier`, `algorithm`, `created_at`, `version`, `parent_id`, `wrapped_key`.
- Master key derived from user password via Argon2id **client-side**; data keys random or HKDF-derived and wrapped.
- `KeyTree`: `add_key`, `get_key(id)`, `rotate_key(id)`, `find_root()`.
**Verify**: Tree round-trips; parent-child enforced; rotating parent re-wraps children.
**Done**: Hierarchy enforced; rotation cascades; JSON serialization (wrapped keys only) works.

### Task 4.2 — Encrypted Keystore
**Files**: `packages/core/cryptavault/keys/keystore.py`
**Action**:
- `Keystore.save(tree, master_password)` / `load(master_password)`.
- JSON envelope: `{version, salt, argon2_params, encrypted_blob}`; blob = AES-256-GCM(tree_json, key=Argon2id(password, salt)).
- Browser variant: encrypted keystore stored in `localStorage`/`IndexedDB`; decrypted in memory only on unlock.
**Verify**: Save→load round-trip; wrong password → fail; tamper → GCM tag failure.
**Done**: Keystore round-trips; wrong password rejected; tamper detected.

### Task 4.3 — Key Generation, Rotation & Versioning
**Files**: `packages/core/cryptavault/keys/operations.py`
**Action**:
- `generate_key(tier, algorithm) -> KeyDescriptor`: random/derived; new id + version.
- `rotate_key(id) -> new_descriptor`: new key, re-wrap children; old = `RETIRED` (decrypts old, not new encrypts).
- `version_key(id)`: increment version, keep history.
- `destroy_key(id)`: remove + cryptographic erase (memory overwrite + `DESTROYED` mark).
**Verify**: Generate→rotate → new key encrypts new files; old files decrypt with retired key; destroy → unrecoverable.
**Done**: Rotation seamless; backward compat for decryption; destroy irreversible.

### Task 4.4 — Key Backup & Recovery
**Files**: `packages/core/cryptavault/keys/backup.py`
**Action**:
- `export_recovery_bundle(master_password) -> bundle`: recovery key (random 256-bit) wraps master; 24-word mnemonic via `mnemonic` lib.
- `import_recovery_bundle(mnemonic, bundle) -> KeyTree`: re-derive recovery key; unwrap master.
- `verify_recovery_bundle(mnemonic, bundle) -> bool` for offline verification.
**Verify**: Export→import round-trip; wrong mnemonic → fail; partial mnemonic → fail.
**Done**: Mnemonic round-trips; wrong words rejected; procedure in `docs/key_recovery.md`.

### Task 4.5 — Key Import/Export (Interop)
**Files**: `packages/core/cryptavault/keys/io.py`
**Action**:
- `export_key(id, format='pem', password=None) -> bytes`: PKCS#8 PEM for asymmetric; raw bytes for symmetric (warn).
- `import_key(data, format, password=None, tier) -> KeyDescriptor`.
- Validate key strength on import (reject <256-bit symmetric, <2048-bit RSA).
**Verify**: PEM round-trip; import rejects weak keys; invalid format → clear error.
**Done**: Standard PEM interop works; weak keys rejected; format auto-detected.

## Phase Gate Criteria (KMS Gate)
- [ ] Hierarchy enforced; rotation cascades to children
- [ ] Keystore round-trips; wrong password + tamper rejected
- [ ] Full lifecycle (generate/rotate/version/destroy) works
- [ ] Mnemonic backup/recovery round-trips; wrong words rejected
- [ ] PEM import/export works; weak keys rejected

## Open Questions
- Browser keystore storage location: `localStorage` vs `IndexedDB` — pick based on size; design supports both.