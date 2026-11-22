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
- `cloudflared.service`

Check:
```bash
systemctl status cryptavault-api cryptavault-web cloudflared --no-pager
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
- Create server-enforced share links with expiry, max uses, optional password, revocation.
- Share link includes decryption key in URL fragment (`#...k=...`) so server does not receive key.
- "Share all" can create shares for all files in current workspace.

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
```

Known env limitations: PQ tests require liboqs; some API/CLI tests may need isolated DB fixtures.

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