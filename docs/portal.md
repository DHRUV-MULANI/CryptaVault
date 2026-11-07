# CryptaVault Web Portal Guide

The portal is a static React application deployed to GitHub Pages. It performs all cryptography in the browser with the Web Crypto API and stores ciphertext in IndexedDB. It does not require an account, a server, or a network connection after the assets load.

Live URL: https://dhruv-mulani.github.io/CryptaVault/

## Routes

The portal uses hash routing so it works on GitHub Pages without server rewrites.

| Route | Page | Purpose |
|---|---|---|
| `#/` | Dashboard | Vault summary, profile, storage, recent activity |
| `#/vault` | Vault | Upload, encrypt, download, rename, delete, and share files |
| `#/shares` | Shares | Inspect, revoke, or delete local share records; open bundles |
| `#/share` | Share viewer | Public decrypt screen for link and bundle shares |
| `#/messages` | Messages | Local encrypted conversations and notes |
| `#/catalog` | Catalog | Browse all 88 catalog algorithms and six profiles |
| `#/academy` | Academy | Implementation-aligned explainer and links |
| `#/admin` | Admin | Local policy flags, inventory, connector state, audit export, wipe |
| `#/settings` | Settings | Identity, policy, passphrase rotation, encrypted backup, wipe |
| `#/status` | Status | Browser capability checks, storage estimate, crypto self-test |

## First run

1. Open the portal over HTTPS or `localhost` so Web Crypto is available.
2. Choose **Create vault**.
3. Enter a passphrase of at least 10 characters. This passphrase is never stored.
4. Choose a default security profile. `BALANCED` is the default.
5. The portal derives a master key with PBKDF2-SHA256 (210,000 iterations, 16-byte salt), stores a sealed verifier, and unlocks the vault.

The vault record contains only the salt, iteration count, sealed verifier, and local settings. The passphrase itself is not persisted.

On later visits the portal detects the vault and asks for the passphrase. A 10-minute inactivity auto-lock is enabled by default; change it in **Settings**.

## Vault workflow

### Encrypt and store a file

1. Open **Vault → Encrypt a file**.
2. Select a file, a profile, and whether compression is automatic or off.
3. The browser reads the file, compresses it with gzip when useful, splits it into profile-sized chunks, and seals each chunk with AES-256-GCM.
4. A fresh per-file key is generated and wrapped with the master key.
5. The encrypted manifest (name, MIME type, size, hash, chunk count, profile, compression) is sealed separately with an AAD that binds it to the file ID.
6. The container JSON and encrypted manifest are written to IndexedDB.

Only ciphertext and wrapped keys are stored. The plaintext and raw file key exist only in memory during the operation.

### Download and delete

- **Download** unwraps the file key, decrypts each chunk, verifies the container magic/version and chunk order, decompresses if needed, then triggers a browser download.
- **Rename** rewrites only the encrypted manifest. The payload ciphertext is unchanged.
- **Delete** removes the container, wrapped key, and encrypted manifest from this browser.

## Secure shares

The portal creates two share forms:

| Mode | When used | What the recipient needs |
|---|---|---|
| Link | The generated URL is at most about 900 KB | The link, plus the passphrase if one was set |
| Bundle | The link would be too large | The downloaded `.cvshare.json` bundle, plus the passphrase if one was set |

A share contains an encrypted copy of the container and a sealed share key. The key travels in the URL fragment (never sent to a server) or inside the bundle. Optional passphrase protection derives an additional key with PBKDF2 and requires the recipient to type the passphrase.

Recipient flow:

1. Open the link, or go to `#/share` and choose the bundle.
2. Review the encrypted metadata shown by the viewer.
3. Enter the passphrase if required.
4. Decrypt. The file downloads directly from the tab.

Important limits in a static deployment:

- A share link is a **capability URL**. Anyone who has it, and the passphrase if set, can decrypt.
- **Revoke** marks the local bookkeeping record. It cannot invalidate a link or bundle that was already copied.
- **Expiry** is recorded and displayed but cannot be enforced without a server. The API can enforce expiry and one-time consumption when enabled.
- Deleting the local share record does not delete the encrypted file in the vault.

## Encrypted messages

Messages are local encrypted notes, not a network messenger in the static deployment.

- A conversation label is sealed with the master key.
- Each message body is sealed with its own AES-256-GCM key, and that key is wrapped with the master key.
- Deleting a conversation removes its messages and metadata from IndexedDB.
- Cross-device delivery requires the authenticated API relay; it is not part of the GitHub Pages deployment.
- Administrators can disable the workspace with the `messagingEnabled` policy flag.

## Catalog

The Catalog page reads `packages/web/src/generated/catalog.json`, generated from the Python catalog by `scripts/export_web_catalog.py`.

It shows:

- 88 algorithms across 9 families: symmetric, hash, KDF, KEM, signature, PAKE, secret sharing, RNG, quantum/experimental.
- Stable wire IDs in hex.
- Lifecycle status: `production`, `experimental`, `legacy`, or `forbidden`.
- Classical bits, NIST post-quantum level, key/nonce/tag sizes.
- Whether the algorithm is implemented and whether its runtime dependency is available.
- The six security profiles and their slider bands.

Filters and search are client-side only. The static portal never selects experimental or forbidden algorithms automatically.

## Admin console

The static admin page is a local control plane, not a multi-tenant governance service.

It provides:

- Local policy flags: sharing, messaging, experimental-algorithm intent.
- Encrypted inventory counts and storage estimate.
- Connector status: IndexedDB active; filesystem, Supabase, and cloud/SFTP marked as available or configuration-required.
- Catalog health: production/experimental/legacy/forbidden counts and missing runtime dependencies.
- Audit log view and CSV export.
- Vault wipe.

Production governance, user impersonation, global feature flags, and server-side audit chains live in the FastAPI admin routes. See [api.md](api.md).

## Settings and recovery

**Settings** supports:

- Display name, default profile, theme, auto-lock duration, share TTL, compression default.
- Passphrase rotation. The master key is re-derived and all wrapped keys and sealed records are re-encrypted with the new key.
- Encrypted backup export as `.cvbackup.json`. The export contains ciphertext and wrapped keys only.
- Backup restore. This replaces every store in the current browser vault.
- Vault wipe. This deletes the vault and all records in this browser.

Backups are only useful with the passphrase that protects the wrapped keys. Store the passphrase separately from the backup. A backup restored into another browser recreates the vault and records but does not merge with an existing vault; the restore action replaces local stores.

## Status and self-test

The Status page checks:

- `crypto.subtle` availability.
- IndexedDB availability.
- Compression stream support.
- Secure context.
- Storage quota estimate.
- Catalog runtime dependencies.
- A live self-test that generates a key, seals 256 KiB, opens it, compares every byte, and hashes the result.

No telemetry is sent.

## Data model

IndexedDB database: `cryptavault-portal`

| Store | Contents |
|---|---|
| `vault` | Salt, iterations, sealed verifier, local settings |
| `files` | File ID, timestamps, sealed manifest, sealed file key |
| `blobs` | Encrypted container JSON |
| `shares` | Local share bookkeeping: mode, expiry, revocation, size, label |
| `threads` | Conversation ID, timestamps, sealed contact metadata |
| `messages` | Message ID, thread ID, direction, sealed body, sealed message key |
| `audit` | Local event log: action, target, detail, timestamp |

Everything except non-secret bookkeeping fields is ciphertext or a wrapper.

## Browser support

The portal needs:

- Web Crypto (`crypto.subtle`) with AES-GCM, PBKDF2, and SHA-256.
- IndexedDB.
- A secure context (HTTPS or localhost).
- `CompressionStream` for gzip. If unavailable, compression falls back to none for that operation.

## Local development

```bash
pnpm install
pnpm --filter @cryptavault/web dev
```

Production build:

```bash
VITE_BASE=/CryptaVault/ pnpm --filter @cryptavault/web build
```

The build output is `packages/web/dist`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| “Browser storage is unavailable” | Private mode, disabled IndexedDB, or storage pressure | Use a normal window and allow site data |
| Wrong passphrase | PBKDF2 derives a different key | Retry; there is no server-side reset |
| Share link opens but cannot decrypt | Truncated link, wrong passphrase, or tampered payload | Request a fresh link or bundle |
| Bundle does not open | Wrong file type or modified JSON | Use the original `.cvshare.json` file |
| File missing after browser cleanup | Site data was cleared | Restore an exported `.cvbackup.json` |
| Compression unavailable | Browser lacks `CompressionStream` | The operation stores uncompressed ciphertext |
| Post-quantum item marked unavailable | Runtime dependency not present | This affects the Python engine, not the static portal |
