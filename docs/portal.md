# CryptaVault Web Portal Guide

The web portal is a React + Vite client for the dynamic CryptaVault stack. It performs all file cryptography in the browser with Web Crypto, authenticates against the FastAPI API, and talks to Neon Postgres and S3-compatible storage only through the API.

The current deployment target is local:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Metadata: Neon Postgres
- Ciphertext: SeaweedFS S3 on `http://127.0.0.1:9000`

The GitHub Pages workflow can publish the SPA assets, but the dynamic portal needs a reachable API. GitHub Pages does not host FastAPI, Neon, or S3. See [demo.md](demo.md) for the full local runbook.

## Routes

| Route | Page | Purpose |
|---|---|---|
| `#/` | Dashboard | Live quota, workspace totals, storage mix, recent files, quick actions |
| `#/vault` | Vault | Upload, download, versions, trash, rename, shares |
| `#/shares` | Shares | Server shares, revocation, locally saved share links |
| `#/workspaces` | Workspaces | Create/select workspaces, members, roles, storage targets |
| `#/s/<token>` | Share viewer | Public server-share decryptor driven by `k`/`n`/`t`/`s`/`h` URL fragments |
| `#/catalog` | Catalog | Browse the 88 catalog algorithms and six profiles |
| `#/academy` | Academy | Zero-knowledge and adaptive-crypto explainer |
| `#/admin` | Admin | Admin-only users, quotas, roles, suspension, flags, storage health |
| `#/settings` | Settings | Account, default profile, auto-lock, shares, compression, theme |
| `#/status` | Status | API health/readiness, storage targets, browser crypto self-test |
| `#/messages` | Messages | Retained local IndexedDB messaging; not in the main navigation |

The dynamic app uses hash routing so static hosting can serve the SPA without rewrite rules.

## Authentication and key derivation

1. The user enters email and passphrase.
2. The client calls `/api/auth/prelogin` to retrieve the account's auth salt and iteration count.
3. The client derives:
   - an auth verifier with PBKDF2-SHA256
   - a 256-bit master key with PBKDF2-SHA256 using the separate vault salt
4. The auth verifier is sent to `/api/auth/login`; the master key never leaves the browser.
5. The master key decrypts the sealed vault check returned by the API to verify the passphrase.
6. The JWT is stored in `localStorage` under `cryptavault.session.token`.
7. The master key is held in memory only and cleared on lock, sign-out, or auto-lock.

Registration derives both values locally, creates a sealed vault check, and sends only the verifier, salts, check, profile, and display name. Neon stores no passphrase and no master key.

The demo seeds these accounts:

| Email | Password | Role |
|---|---|---|
| `admin@cryptavault.dev` | `CryptaVaultDemo!2026` | admin |
| `demo@cryptavault.dev` | `CryptaVaultDemo!2026` | user |
| `viewer@cryptavault.dev` | `CryptaVaultDemo!2026` | viewer |

## Vault workflow

### Encrypt and upload

1. Open **Vault** and choose a file, security profile, and compression mode.
2. The browser reads the file, optionally gzip-compresses it, and splits it into profile-sized chunks.
3. A fresh 256-bit file key is generated.
4. Each chunk is sealed with AES-256-GCM using AAD:

```text
cryptavault:web:v1:<fileId>:<chunkIndex>:<isFinal>
```

5. The `CVW1` container is serialized as JSON and uploaded as `ciphertext`.
6. The metadata manifest (name, MIME type, size, plaintext SHA-256, chunk count, profile, compression, creation time) is sealed with the master key under `filemeta:<fileId>`.
7. The raw file key is wrapped with the master key under `filekey:<fileId>`.
8. The API stores the encrypted manifest, wrapped key, ciphertext size, content tag, profile, and storage reference in Neon, and the ciphertext object in S3.

The API quota check uses ciphertext size. SeaweedFS receives no readable file name or plaintext.

### Download and verify

1. The browser downloads ciphertext from `/api/files/<fileId>/download`.
2. It unwraps the file key and decrypts the manifest.
3. It decrypts each authenticated chunk in order.
4. It decompresses gzip payloads when needed.
5. It verifies the plaintext SHA-256 against the sealed manifest.
6. Only then does it trigger the browser download.

A wrong key, modified chunk, bad AAD, unsupported container, or hash mismatch aborts before a file is released.

### Versioning, rename, and trash

- **New version** uploads the next immutable version, `current_version + 1`, with a fresh file key and new ciphertext object.
- **Versions** lists every version and marks the current one. Restore promotes an older version to current without deleting history.
- **Rename** re-seals only the current version's metadata manifest; payload ciphertext is unchanged.
- **Trash** sets the file's deleted timestamp. **Restore** clears it.
- **Permanent delete** removes every version and ciphertext object. The API rejects sharing a trashed file.

### Profile behavior

The dynamic web/remote path uses the selected profile's chunk size and records its name, but uses the browser-portable subset:

- PBKDF2-SHA256 at the vault level
- AES-256-GCM chunk encryption
- gzip optional compression
- SHA-256 plaintext integrity hash

The full catalog, post-quantum KEMs/signatures, Merkle roots, and `CVV2` pipeline remain available in the Python core and offline CLI.

## Shares

The server enforces:

- expiry timestamp
- maximum download count
- revocation
- optional share passphrase
- workspace role permission to create/revoke

The browser creates a manifest:

```json
{
  "v": 1,
  "name": "...",
  "type": "application/pdf",
  "size": 12345,
  "hash": "...",
  "profile": "BALANCED",
  "compression": "gzip",
  "chunkCount": 2,
  "createdAt": "...",
  "key": { "ivB64": "...", "ctB64": "..." },
  "kdf": "raw"
}
```

The wrapped `key` contains the raw file key sealed with the share key under `sharekey:v1`.

- Capability shares use a random 256-bit share key; the link includes `k`.
- Passphrase shares derive the share key with PBKDF2 from the passphrase and salt; the link omits `k`.

The generated link has this form:

```text
https://cryptavault.dhruvmulani.com/#/s/<token>?k=<base64url-share-key>&n=<name>&t=<mime>&s=<size>&h=<sha256>
```

The server never receives `k`, `n`, `t`, `s`, or `h`: they live after `#` and are not sent in HTTP requests. The creating browser saves links under `cryptavault.share.link.{token}`. Another browser can still use a copied link; it just cannot reconstruct it from the server share list.

### Public viewer

The viewer parses the token, capability key, and optional original filename/MIME/size/hash from the URL fragment, fetches share policy from `/api/shares/<token>`, prompts for a password or 8-digit PIN when required, downloads ciphertext from `/api/shares/<token>/download`, decrypts, verifies the SHA-256 from `h` when present, and saves the file under its original name from `n`.

Legacy static links using `#/share?d=` remain supported: they carry a self-contained container manifest, and the viewer decrypts them entirely in the browser.

QR codes are generated client-side from the complete share link, including the key and metadata fragment. The key is never sent to `/api/shares/<token>/qr`.

## Workspaces and roles

| Role | Capabilities |
|---|---|
| `owner` | Full workspace control, deletion, member management |
| `admin` | Manage members and files except ownership transfer/deletion |
| `editor` | Upload, version, rename, trash, share |
| `viewer` | Read/download only |

The API enforces roles on every route. The web client switches the active workspace from the header and persists it in `localStorage`.

Workspace membership shares metadata and policy, not a common master key. A user can decrypt files they uploaded with their own master key. Decrypting another member's uploads requires the same master key, which the current design does not distribute.

## Dashboard and admin

The dashboard uses `/api/dashboard` and `/api/auth/me` for live data, then decrypts recent file manifests for display.

The admin page is available only to accounts with `role=admin`. It provides:

- total/active/suspended user counts
- aggregate storage and file counts
- role, quota, and suspension updates
- feature flags
- storage target health checks
- API health and readiness summaries

Feature flags are stored centrally and enforced by the API: sharing, versions, cloud connectors, and maintenance-mode writes.

## Settings

Settings updates:

- display name
- default security profile
- auto-lock minutes
- share TTL default
- compression preference
- theme

Passphrase rotation is intentionally disabled. Changing the dynamic vault passphrase requires re-wrapping every account's keys and is left as a documented migration item.

## Status

The status page shows:

- `/health` and `/ready`
- per-target storage health
- Web Crypto availability
- compression/decompression support
- AES-GCM round-trip self-test
- active profile and workspace summary

## Local storage keys

| Key | Purpose |
|---|---|
| `cryptavault.session.token` | JWT access token |
| `cryptavault.current.workspace` | Active workspace ID |
| `cryptavault.settings.<userId>` | Per-user UI preferences |
| `cryptavault.share.link.<token>` | Locally saved generated share link |

Clearing site data removes the JWT, workspace selection, settings, and saved links. Server metadata and ciphertext remain until deleted through the API.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | API base URL |
| `VITE_BASE` | `/` | Vite base path for static hosting |

## Limitations

- Dynamic accounts do not support passphrase rotation yet.
- Workspace members do not share a common vault key.
- Legacy static `#/share?d=` links cannot be opened by the dynamic viewer.
- Feature flags are enforced for sharing, versions, cloud connectors, and maintenance-mode writes. Maintenance mode still permits reads and administrator bypass.
- Cloud connectors are configuration-ready only.
- The server stores a plaintext SHA-256 content tag for integrity comparison; it is not a key or plaintext.
