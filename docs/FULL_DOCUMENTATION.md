# CryptaVault — Full Documentation

## 1. Overview

CryptaVault is a zero-knowledge, crypto-agile encrypted storage framework. Files are encrypted in the client (browser/CLI) before upload. The server stores ciphertext, encrypted metadata, wrapped keys, and access-control metadata — never plaintext or master keys.

## 2. Core Security Model

### Zero-Knowledge Boundary
- **Client knows**: passphrase, derived master key, plaintext, per-file keys, decrypted metadata.
- **Server knows**: ciphertext blobs, encrypted metadata envelopes, wrapped file keys, auth verifier, salts/KDF params, share tokens/policy, audit/access metadata.
- **Rule**: plaintext and user master keys never leave the client.

### Auth & Key Derivation
- Client derives `auth_key` and `master_key` from passphrase using PBKDF2-SHA256 (configurable iterations; default 210000 in web client).
- `auth_verifier = base64(raw auth_key bytes)` is sent to server for login/register.
- Server stores auth verifier/salt; it cannot derive the master key.
- `vault_check` is an AES-GCM encrypted verifier (`cryptavault:verifier:v1`) with AAD `vault:verifier`, used by client to confirm correct passphrase/unlock.

### File Encryption
- Each file gets a random per-file key.
- File is chunked and encrypted client-side (AES-GCM container format in web client).
- Metadata is encrypted with master key (AAD `filemeta:<file_id>`).
- Per-file key is wrapped with master key (AAD `filekey:<file_id>`).
- Server receives ciphertext + encrypted metadata + wrapped key.

## 3. Repository Layout

- `packages/core` - crypto engine, profiles, storage abstractions.
- `packages/api` - FastAPI backend, auth/workspaces/files/shares/admin routes.
- `packages/web` - React/Vite zero-knowledge web portal.
- `packages/mobile` - Flutter zero-knowledge client (Android/iOS/Linux/Web).
- `packages/cli` - Typer/Rich CLI.
- `packages/admin` - admin console package.
- `packages/wasm` - WASM bindings/experiments.
- `docs/` - architecture, phases, reports, guides.

## 4. Local Development

### Prerequisites
- Python 3.11 + `uv`
- Node 20+ + `pnpm` (or `npx pnpm`)
- Optional: Docker (for local Supabase), cloudflared (for tunnel)

### Setup
```bash
cd /home/boss/Documents/Collage/CryptaVault
uv venv .venv --python 3.11
uv pip install -e packages/core -e packages/api -e packages/cli
npx -y pnpm@9.15.0 install
```

### Run API
```bash
PYTHONPATH=packages/api:packages/core .venv/bin/uvicorn cryptavault_api.main:app --host 127.0.0.1 --port 8000
```

### Run Web
```bash
npx -y pnpm@9.15.0 --filter @cryptavault/web dev --host 0.0.0.0 --port 3000
```

Web dev server proxies `/api`, `/health`, `/ready` to `127.0.0.1:8000`.

## 5. Deployment / Internet Access

### Cloudflare Tunnel
- Install and run cloudflared as service.
- Configure tunnel public hostname to `http://localhost:3000`.
- Web proxies API same-origin, so one hostname is sufficient.

### Auto-start (systemd)
Services installed on this machine:
- `cryptavault-api.service`
- `cryptavault-web.service`
- `cloudflare-cryptavault.service` (Cloudflare tunnel; token at `/etc/cloudflared/token`, root-only)

Check:
```bash
systemctl status cryptavault-api cryptavault-web cloudflare-cryptavault --no-pager
```

## 6. Web App Features

### Landing & Auth
- Landing page: `#/`
- Auth: `#/auth` (register/login/unlock)

### Vault
- Upload encrypted files to current workspace.
- Select **encryption profile** per upload.
- Set optional **folder** metadata.
- Download decrypts locally and verifies hash.
- Trash = soft delete; Restore from trash; Permanent delete removes ciphertext and DB records.

### Sharing
- Create server-enforced share links with expiry, max uses, optional password, revocation, optional recipient email, and 8-digit PIN.
- PIN is auto-assigned if omitted; owner can change PIN or regenerate link. PIN is stored as server-side hash (access control), not a file encryption key.
- Recipient email: when that user is logged in, PIN is bypassed; other users must enter PIN.
- Share link includes decryption key and original file metadata (name, MIME, size, SHA-256) in the URL fragment (`#...k=...&n=...&t=...&s=...&h=...`) so the server receives none of it. QR code is generated client-side from the complete link.
- "Share all" can create shares for all files in current workspace.
- "Shared with me" tab lists shares addressed to the logged-in user's email.

### Workspaces
- Create/select workspaces.
- Files are scoped to workspace.

### Admin/Settings/Status
- Admin console for users/flags (role-gated).
- Settings for display/profile/theme/lock behavior.
- Diagnostics/status page.

## 7. Storage & Deletion

### Where files are stored
- **Ciphertext blobs**: configured storage target. Default local target: `data/storage/`.
- **Metadata/DB**: SQLite `data/cryptavault.db` by default (or configured DB). Contains users, workspaces, file records, encrypted metadata, wrapped keys, share policies.
- **Plaintext**: never stored server-side.

### When removed
- **Trash**: file record marked `deleted_at`; hidden from normal list; can be restored.
- **Permanent delete**: ciphertext deleted from storage target; file versions/shares/DB records removed.

## 8. CLI

Install:
```bash
uv pip install -e packages/core -e packages/cli
cryptavault --help
```

Or direct from GitHub (after push):
```bash
uv tool install --from git+https://github.com/DHRUV-MULANI/CryptaVault.git#subdirectory=packages/cli --with git+https://github.com/DHRUV-MULANI/CryptaVault.git#subdirectory=packages/core cryptavault-cli
```

## 9. Testing

```bash
# Web
npx -y pnpm@9.15.0 --filter @cryptavault/web run typecheck
npx -y pnpm@9.15.0 --filter @cryptavault/web run build

# Python
PYTHONPATH=packages/api:packages/core .venv/bin/pytest packages/core/tests -q
PYTHONPATH=packages/api:packages/core .venv/bin/pytest packages/api/tests -q

# Flutter (mobile/desktop/web)
cd packages/mobile
flutter analyze
flutter test
flutter build apk --release
flutter build web --release
flutter build linux --release
```

`packages/mobile/test/api_interop_test.dart` runs against the live API at `http://127.0.0.1:8000` when it is available and exits cleanly otherwise. It exercises registration, login/unlock, encrypted upload/download with hash verification, share PIN/recipient bypass/PIN change/regeneration/revocation, and trash/restore/permanent delete using the exact client code paths.

Known env limitations: PQ tests require liboqs; some API/CLI tests may need isolated DB fixtures. Web builds need `CHROME_EXECUTABLE` (Chrome/Chromium) and Linux builds need `ninja`.

## 10. Security Notes

- Do not commit `.env`, secrets, tokens, or local DB/storage.
- Rotate any tokens/passwords accidentally exposed in chat/logs.
- Use HTTPS in production (Cloudflare tunnel/reverse proxy).
- Rate limits, backups, monitoring, and secret rotation should be configured before public production use.

## 11. Troubleshooting

- **404 after login on unknown route**: check the hash URL; only defined routes are supported.
- **Upload fails**: verify storage target config points to writable path and is default/enabled.
- **Public domain not resolving locally**: check DNS; local Tailscale DNS may override resolution. Test with `curl --resolve ...`.
- **Auth/register WebCrypto error**: ensure auth key derivation is extractable for verifier export (fixed in web client).
## 12. Flutter mobile/desktop app

The Flutter client in `packages/mobile` targets Android, iOS, Linux, and Web from one Dart codebase. It is a full client, not a wrapper: crypto runs on the device using `cryptography` (PBKDF2-HMAC-SHA256, AES-256-GCM), and the API only ever receives ciphertext, wrapped keys, and sealed metadata.

### Environment

Flutter is installed at `~/.local/share/rd-flutter` (Flutter 3.47.5 / Dart 3.13.4). It is permanently exported in:

- `~/.config/fish/conf.d/flutter.fish`
- `~/.bashrc` and `~/.profile`

So `flutter` and `dart` work in new shells. For web builds set `CHROME_EXECUTABLE=/usr/bin/google-chrome-stable`; for Linux builds `ninja` must be installed.

### Features

- **Auth**: register/login with client-derived `auth_verifier`, vault check (`cryptavault:verifier:v1` under AAD `vault:verifier`), lock/unlock, sign out.
- **Vault**: list decrypted metadata, upload with encryption profile + folder, download/decrypt with SHA-256 verification, trash/restore/permanent delete, folder filter/search.
- **Shares**: create with recipient email, 8-digit PIN (auto-assigned), password, expiry, max uses; copy link with `#k=` key and original-name metadata, locally generated QR code, native share sheet, change PIN, regenerate (invalidates old token), revoke, "Shared with me" inbox.
- **Share viewer**: paste a full share link, parse token/key/name fragment, PIN/password prompt, recipient-email bypass, download and decrypt locally, verify hash, and save under the original filename.
- **Workspaces**: list/select/create workspaces in Settings.
- **Status**: dashboard counters, storage mix, system health, feature flags, and admin user controls (suspend/role) when signed in as admin.
- **Zero-knowledge**: master key lives only in memory; JWT in `flutter_secure_storage`. The server URL defaults to `https://cryptavault.dhruvmulani.com` and can be changed in Settings.
- **Android networking**: the release manifest permits cleartext traffic so a local/LAN API URL works during development. Use the HTTPS public URL (or an HTTPS reverse proxy) on untrusted networks; plaintext files and keys are never sent either way.

### Layout

```
packages/mobile/lib/
├── main.dart, app.dart               # bootstrap and themed MaterialApp
├── models/types.dart                 # API/container models
├── services/crypto_service.dart      # CVW1 container + PBKDF2/AES-GCM helpers
├── services/api_service.dart         # FastAPI client (auth/files/shares/admin)
├── services/storage_service.dart     # secure token store + in-memory test store
├── state/vault_provider.dart         # auth/master-key/workspace state
└── screens/                          # auth, vault, shares, share viewer, status, settings
```

### Verification

```
flutter analyze          # no issues
flutter test             # 9 tests passed (4 crypto + 5 live-API interop)
flutter build apk --release
flutter build web --release
flutter build linux --release
```

Artifacts: `build/app/outputs/flutter-apk/app-release.apk`, `build/web/`, `build/linux/x64/release/bundle/cryptavault_mobile`.
