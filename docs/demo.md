# CryptaVault Dynamic Stack — End-to-End Demo Runbook

This runbook starts and demonstrates the complete local stack:

- React + Vite web client on `http://localhost:3000`
- FastAPI API on `http://localhost:8000`
- Neon Postgres for auth, metadata, roles, shares, quotas, and policy
- SeaweedFS S3-compatible storage on `http://127.0.0.1:9000`
- Typer remote CLI sharing the same API and `CVW1` wire format

The zero-knowledge rule for the whole demo: plaintext, passphrases, master keys, and raw file keys stay in the browser or CLI process. Neon and SeaweedFS receive ciphertext, wrapped keys, encrypted manifests, and non-identifying records only.

---

## 1. Start the services

### Terminal 1 — SeaweedFS S3

The maintained local binary used for this project is `/tmp/opencode/seaweed/weed`:

```bash
cd /tmp/opencode/seaweed
./weed server \
  -dir=/tmp/opencode/seaweed/data \
  -ip=127.0.0.1 \
  -master.port=9333 \
  -volume.port=9340 \
  -filer.port=9341 \
  -s3 -s3.port=9000 \
  -s3.config=/tmp/opencode/seaweed/s3.json
```

Create the bucket once if it does not exist:

```bash
cd /tmp/opencode/seaweed
./weed shell
# inside the shell:
s3.bucket.create -name cryptavault
exit
```

`/tmp/opencode/seaweed/s3.json` defines access key `minioadmin`, secret key `minioadmin`, and full S3 actions for the local demo.

### Terminal 2 — FastAPI

From the repository root:

```bash
.venv/bin/uvicorn cryptavault_api.main:app --host 127.0.0.1 --port 8000
```

Check:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

Expected `/health`:

```json
{"status":"ok","version":"2.0.0","zero_knowledge_boundary":"ENFORCED","audit_logging":"DISABLED"}
```

Swagger: `http://127.0.0.1:8000/docs`

### Terminal 3 — Web client

```bash
npx -y pnpm --filter @cryptavault/web dev
```

Open `http://localhost:3000`.

The API URL defaults to `http://localhost:8000`. Override with `VITE_API_URL` if needed.

### Demo accounts

When the database has no users and `CRYPTAVAULT_SEED_DEMO=true` (default), startup seeds:

| Email | Password | Role |
|---|---|---|
| `admin@cryptavault.dev` | `CryptaVaultDemo!2026` | admin |
| `demo@cryptavault.dev` | `CryptaVaultDemo!2026` | user |
| `viewer@cryptavault.dev` | `CryptaVaultDemo!2026` | viewer |

The `demo` and `viewer` accounts are members of the `Final Year Team` workspace owned by `admin`.

---

## 2. Required environment

The API loads `.env` from the repository root. Minimum values:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
JWT_SECRET=replace-with-a-32-byte-or-longer-random-secret
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=cryptavault
PUBLIC_SHARE_DOMAIN=http://localhost:3000
CRYPTAVAULT_ENV=development
CRYPTAVAULT_SEED_DEMO=true
```

Cloud connector variables are optional. Google Drive, Dropbox, and OneDrive stay configuration-ready until OAuth applications and credentials are supplied.

---

## 3. Web demonstration path

### Step 1 — Sign in and inspect the dashboard

1. Open `http://localhost:3000`.
2. Sign in as `demo@cryptavault.dev` with `CryptaVaultDemo!2026`.
3. The dashboard loads live data from `/api/dashboard` and `/api/auth/me`.
4. Point out quota usage, workspace totals, storage mix, recent files, and the profile card.

The browser derived the auth verifier and master key locally. Only the verifier and sealed vault check were sent to the API.

### Step 2 — Encrypt and upload a file

1. Open **Vault**.
2. Choose a file, `BALANCED`, and automatic compression.
3. Upload.
4. Point out that the request contains:
   - `ciphertext` as an opaque `CVW1` JSON container
   - `encrypted_meta` and `meta_iv`
   - `wrapped_key` and `wrapped_iv`
   - the plaintext SHA-256 content tag
5. The API returns file/version metadata. Neon stores no readable file name; SeaweedFS stores no plaintext.

Download the file from the list and compare it with the original:

```bash
diff -s original.pdf downloaded.pdf
```

### Step 3 — Add an immutable version and restore

1. Upload the same logical file again using **New version**.
2. Open **Versions** and show `v1`, `v2`, and the current marker.
3. Restore `v1` and download again. The ciphertext object for each version remains separate.
4. Move the file to **Trash**, restore it, then permanently delete a disposable copy and show the version list disappear.

### Step 4 — Create and open a server-enforced share

1. Choose **Share** on a file.
2. Set expiry and maximum downloads.
3. Optionally set a share passphrase.
4. Copy the generated link. It has this shape:

```text
http://localhost:3000/#/s/<token>?m=<encrypted-manifest>&k=<raw-share-key>
```

5. Open the link in a private window.

The public viewer:

- fetches `/api/shares/<token>` for policy and availability
- posts to `/api/shares/<token>/download` for ciphertext
- unwraps the raw file key from the manifest
- decrypts the `CVW1` container and verifies SHA-256

If a passphrase was used, the link omits `k` and the viewer asks for the passphrase.

6. Download once and show the use counter/remaining uses.
7. Revoke the share in **Shares** and reload the public link. The API now returns HTTP 410.

The generated link exists only in the creating browser's local storage key `cryptavault.share.link.{token}`; the server never receives decryptable URL material.

### Step 5 — Workspaces and roles

1. Open **Workspaces**.
2. Show `Personal vault` and `Final Year Team`.
3. Add `viewer@cryptavault.dev` to a workspace as `viewer` or change an existing member role.
4. Sign in as `viewer@cryptavault.dev` and show that viewer/editor restrictions are enforced by the API.
5. Create a workspace with a different storage target and switch the active workspace.

### Step 6 — Admin and status

1. Sign in as `admin@cryptavault.dev`.
2. Open **Admin**:
   - user count, active/suspended counts, total storage
   - role, quota, and suspension updates
   - feature flags
   - storage target health tests
   - `/health` and `/ready` summaries
3. Open **Status** and point out:
   - API health/readiness
   - storage target health
   - browser capability checks
   - AES-GCM self-test
   - active profile summary

### Step 7 — Reference pages

- **Catalog** lists the 88-algorithm catalog and six profiles.
- **Academy** explains the zero-knowledge boundary and adaptive design.
- **Settings** updates display name, default profile, auto-lock, share TTL, compression, and theme. Passphrase rotation is intentionally disabled because dynamic account migration is not implemented yet.

---

## 4. CLI demonstration path

Use a separate session file so the demo does not disturb a developer session:

```bash
export CRYPTAVAULT_SESSION=/tmp/cryptavault-demo-session.json
```

### Login and workspace

```bash
.venv/bin/cryptavault remote auth login \
  --email demo@cryptavault.dev \
  --passphrase 'CryptaVaultDemo!2026'

.venv/bin/cryptavault remote auth whoami
.venv/bin/cryptavault remote workspace list
```

The session file contains the JWT and vault bootstrap, never the passphrase or master key.

### Upload, list, and download

```bash
printf 'CryptaVault dynamic CLI demo %s\n' "$(date -Is)" > /tmp/cv-demo.txt

.venv/bin/cryptavault remote files upload /tmp/cv-demo.txt \
  --profile BALANCED \
  --passphrase 'CryptaVaultDemo!2026'

.venv/bin/cryptavault remote files list --passphrase 'CryptaVaultDemo!2026'
```

Copy the printed file ID, then:

```bash
export FILE_ID='<printed-file-id>'

.venv/bin/cryptavault remote files download "$FILE_ID" \
  --output /tmp/cv-demo-roundtrip.txt \
  --passphrase 'CryptaVaultDemo!2026'

cmp /tmp/cv-demo.txt /tmp/cv-demo-roundtrip.txt
```

### Version, restore, and trash

```bash
printf 'second version\n' >> /tmp/cv-demo.txt

.venv/bin/cryptavault remote files upload /tmp/cv-demo.txt \
  --version-of "$FILE_ID" \
  --passphrase 'CryptaVaultDemo!2026'

.venv/bin/cryptavault remote files versions "$FILE_ID"

.venv/bin/cryptavault remote files download "$FILE_ID" --version 1 \
  --output /tmp/cv-demo-v1.txt \
  --passphrase 'CryptaVaultDemo!2026'

.venv/bin/cryptavault remote files restore "$FILE_ID" 1
.venv/bin/cryptavault remote files trash "$FILE_ID"
.venv/bin/cryptavault remote files list --trash --passphrase 'CryptaVaultDemo!2026'
.venv/bin/cryptavault remote files untrash "$FILE_ID"
```

### Create and decrypt a share

```bash
.venv/bin/cryptavault remote files share "$FILE_ID" \
  --ttl 24 \
  --max-uses 5 \
  --passphrase 'CryptaVaultDemo!2026'
```

Copy the printed link and decrypt it anonymously:

```bash
.venv/bin/cryptavault remote shares decrypt '<printed-link>' \
  --output /tmp/cv-demo-share.txt

cmp /tmp/cv-demo.txt /tmp/cv-demo-share.txt
```

For a passphrase-protected share:

```bash
.venv/bin/cryptavault remote files share "$FILE_ID" \
  --ttl 24 --max-uses 5 --password 'share-secret' \
  --passphrase 'CryptaVaultDemo!2026'

.venv/bin/cryptavault remote shares decrypt '<printed-link>' \
  --password 'share-secret' \
  --output /tmp/cv-demo-share-pass.txt
```

### Revoke

```bash
.venv/bin/cryptavault remote shares list
.venv/bin/cryptavault remote shares revoke '<share-token>'
```

Open the revoked URL again to show HTTP 410.

---

## 5. Zero-knowledge evidence

### Neon stores no plaintext

The database stores:

- user email, display name, role, quota, status
- auth salt + verifier, vault salt + sealed check
- workspace names and membership roles
- encrypted metadata blobs and wrapped file keys
- ciphertext size, hash tag, profile, storage key
- share policy: token, expiry, max uses, password hash, revoked flag

It does not store file names, plaintext hashes that reveal content, master keys, raw file keys, or share capability keys. The content tag is SHA-256 of plaintext and is used by the client for integrity verification.

### SeaweedFS stores no plaintext

Inspect the bucket/object layout and show that objects are `CVW1` JSON with base64 ciphertext chunks, not original files.

### API refuses unauthenticated access

```bash
curl -i http://127.0.0.1:8000/api/workspaces
```

Expect HTTP 401.

### Share policy is server-enforced

1. Create a share with `max_uses=1`.
2. Download once.
3. Download again. The API returns HTTP 410.
4. Revoke another share and show HTTP 410 on reload.

---

## 6. Automated verification

```bash
# Backend/core/CLI
.venv/bin/pytest -q --hypothesis-seed=0
.venv/bin/ruff check .
.venv/bin/mypy packages/core/cryptavault packages/api/cryptavault_api packages/cli/cryptavault_cli

# Web
npx -y pnpm --filter @cryptavault/web run typecheck
npx -y pnpm --filter @cryptavault/web run build
```

Expected: 165 Python tests pass, ruff/mypy clean, web typecheck/build pass.

---

## 7. Cleanup

```bash
unset CRYPTAVAULT_SESSION
rm -f /tmp/cryptavault-demo-session.json /tmp/cv-demo*.txt /tmp/cv-demo-share*.txt /tmp/cv-demo-v1.txt
```

Stop the API and SeaweedFS with `Ctrl+C` in their terminals.

Do not commit `.env`, session files, share links, or `/tmp/neon-create.json`.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `Database initialization failed` | Check `DATABASE_URL`; Neon must be reachable from this machine. |
| `/ready` reports storage down | Confirm SeaweedFS is on port 9000 and the `cryptavault` bucket exists. |
| Login says incorrect passphrase | Use the seeded password exactly; demo accounts use `.dev`, not `.local`. |
| Share link opens but cannot decrypt | The link must include `?m=`; legacy `#/share?d=` links are not supported by the dynamic viewer. |
| `410 Gone` on a share | The share expired, reached its use limit, was revoked, or its file was deleted. |
| `413` on upload | The account quota was exceeded. Raise it in Admin or use another account. |
| `409 Next version must be N` | Another upload already created that version; refresh and retry. |
| CLI says session expired | Run `cryptavault remote auth login` again. |
| `OqsNotAvailableError` | Install native `liboqs` only if demonstrating the post-quantum core path. The dynamic `CVW1` path does not require it. |
