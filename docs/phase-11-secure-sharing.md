# Phase P11 — Secure Sharing System (Week 13)

## Objective
Build the complete secure sharing system: encrypted share package format, one-time access tokens, time-limited links, password-protected shares, QR code generation, and invitation shares (public-key recipient via hybrid KEM).

## Prerequisites
- P2 (PQ Gate) — hybrid KEM for PQ-secure invitation shares.
- P9 (API Gate) — share token routes for server-side lifecycle.
- P10 (Storage Gate) — storage references for share package.

## Tasks

### Task 11.1 — Encrypted Share Package Format
**Files**: `packages/core/cryptavault/sharing/package.py`, `docs/share_format.md`
**Action**:
- `SharePackage`: `version`, `file_id`, `encrypted_key` (per-recipient), `ciphertext_ref`, `signature`, `merkle_root`, `manifest_fragment`.
- Serialize JSON or CBOR. Single-file shares inline ciphertext; large files reference storage (recipient needs access).
**Verify**: Round-trip; tamper ciphertext → verify fails; tamper signature → fails.
**Done**: Format stable; tamper detection; documented.

### Task 11.2 — One-Time Access Tokens
**Files**: `packages/core/cryptavault/sharing/token.py`
**Action**:
- Token = signed random 256-bit nonce + expiry + file_id + use_count; stored in Supabase `share_tokens`.
- HMAC with master key; verify signature before granting; increment use_count.
**Verify**: Valid → access; reuse → rejected; expired → rejected; tampered → rejected.
**Done**: One-time enforced; tamper/expiry handled.

### Task 11.3 — Time-Limited Links
**Files**: `packages/core/cryptavault/sharing/timed_link.py`
**Action**:
- Encode token + expiry in URL; signature prevents tampering.
- `verify_link(url) -> (valid, file_id, remaining_time)`.
**Verify**: Valid within window; expired → rejected; tampered expiry → rejected.
**Done**: Time-limited enforced; tamper-resistant.

### Task 11.4 — Password-Protected Sharing
**Files**: `packages/core/cryptavault/sharing/password.py`
**Action**:
- Sender: wrap share key with Argon2id-derived key from password; include salt + params.
- Recipient: enter password → Argon2id → unwrap → decrypt.
**Verify**: Correct password → decrypt; wrong → fail; empty allowed.
**Done**: Password protection enforced; Argon2id tuning documented.

### Task 11.5 — QR Code Share Generation
**Files**: `packages/core/cryptavault/sharing/qr.py`
**Action**:
- `qrcode` lib; encode URL (timed link) or compact package (small keys ≤2KB).
- Print ASCII to terminal or save PNG.
**Verify**: Generate → decode → match; size limits documented.
**Done**: QR round-trips; ASCII + PNG output.

### Task 11.6 — Invitation Share (Public-Key Recipient)
**Files**: `packages/core/cryptavault/sharing/invitation.py`
**Action**:
- Sender wraps share key with Hybrid KEM (X25519+Kyber for PQ-share).
- Package includes per-recipient wrapped key; multiple recipients supported.
**Verify**: Recipient with matching key → decrypt; wrong key → fail; multiple recipients each decrypt.
**Done**: Invitation enforced; multi-recipient works; PQ-hybrid for MAX profile.

## Phase Gate Criteria (Sharing Gate)
- [ ] Share package format round-trips with tamper detection
- [ ] One-time tokens enforce single-use + expiry
- [ ] Time-limited links verified server-side
- [ ] Password protection via Argon2id
- [ ] QR codes generated (ASCII + PNG)
- [ ] Invitation shares via hybrid KEM (multi-recipient)

## Open Questions
- CBOR vs JSON for package: prefer CBOR for compactness; JSON for human-debuggability. Implement both, default to CBOR.