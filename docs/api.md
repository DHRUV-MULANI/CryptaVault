# API Reference

The FastAPI backend coordinates authentication, encrypted manifests, encrypted storage, shares, audit records, admin governance, metrics, and AI advisory. It never receives plaintext or user keys.

Base URL in development: `http://127.0.0.1:8000`

Interactive schema: `/docs`, `/redoc`, and `/openapi.json`.

## Run

```bash
uv pip install --python .venv/bin/python -e packages/core -e packages/api
.venv/bin/uvicorn cryptavault_api.main:app --host 127.0.0.1 --port 8000 --reload
```

The static portal does not require this service. Start it only when you need server-coordinated features.

## Authentication

Protected routes expect a Supabase JWT:

```http
Authorization: Bearer <access_token>
```

For local tests, the dependency accepts a mock token of the form `mock-user-token-<id>`. An ID containing `admin` receives the admin role. Never enable mock tokens in a real deployment.

| Environment variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` or `SUPABASE_ANON_KEY` | Client key |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side key for privileged operations |
| `PUBLIC_SHARE_DOMAIN` / `CUSTOM_SHARE_DOMAIN` | Base URL used in share links |
| `CRYPTAVAULT_CORS_ORIGINS` | Comma-separated extra allowed origins |
| `REDIS_URL` | Optional rate-limit backend |

Default CORS origins include localhost ports 3000/3001 and `https://dhruv-mulani.github.io`. Add a custom portal origin with `CRYPTAVAULT_CORS_ORIGINS`.

## Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Liveness, version, zero-knowledge boundary marker |
| GET | `/ready` | No | Readiness and Supabase configuration presence |

```bash
curl http://127.0.0.1:8000/health
```

## Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/session` | No | Store a Supabase access token in an HTTP-only `cv_session` cookie |
| GET | `/api/auth/me` | Bearer | Current user id, email, role, metadata |
| POST | `/api/auth/logout` | No | Delete the session cookie |

The portal does not use these routes in its static deployment.

## Users and encrypted manifests

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/users/me` | Bearer | Profile, quota, used bytes, default profile |
| PATCH | `/api/users/me` | Bearer | Update display name and default profile |
| GET | `/api/users/me/manifest` | Bearer | Retrieve the latest encrypted manifest |
| PUT | `/api/users/me/manifest` | Bearer | Store an encrypted manifest |

Manifest upload body:

```json
{
  "manifest_version": 1,
  "ciphertext_b64": "...",
  "nonce_b64": "...",
  "hash_blake3_hex": "...",
  "file_count": 12
}
```

The server stores the ciphertext envelope, nonce, hash, and count. It cannot read file names, directories, or keys. Manifests are isolated per user ID.

## Crypto catalog and profiles

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/crypto/catalog` | No | List algorithms; filters `family`, `status`, `implemented_only` |
| GET | `/api/crypto/catalog/{algorithm_id}` | No | Resolve an ID or alias |
| GET | `/api/crypto/profiles` | No | List six profiles and full configuration |

```bash
curl 'http://127.0.0.1:8000/api/crypto/catalog?family=signature&status=production'
curl http://127.0.0.1:8000/api/crypto/catalog/ml-kem-768
curl http://127.0.0.1:8000/api/crypto/profiles
```

Invalid filters return `422`; unknown IDs return `404`. See [crypto_catalog.md](crypto_catalog.md).

## Shares

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/shares` | Bearer | Create a signed share token |
| GET | `/api/shares` | Bearer | List the caller's shares |
| GET | `/api/shares/{token_id}` | No | Public token metadata |
| POST | `/api/shares/{token_id}/consume` | No | Consume one use |
| DELETE | `/api/shares/{token_id}` | Bearer | Revoke the caller's share |
| GET | `/api/shares/{token_id}/qr` | No | PNG QR code for the share URL |

Create body:

```json
{
  "file_id": "file-123",
  "filename": "report.pdf",
  "ciphertext_ref": "supabase://vaults/report.pdf.vault",
  "expires_at_iso": "2026-11-08T12:00:00Z",
  "max_uses": 1,
  "password_protected": false,
  "share_package_json": null,
  "custom_domain": "https://vault.example.com"
}
```

The current implementation keeps share records in process memory. Production use requires a database-backed store. The API can enforce expiry and use counts; the static portal cannot.

## Encrypted storage

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/storage/upload` | Bearer | Upload an encrypted file |
| GET | `/api/storage/files` | Bearer | List the caller's encrypted files |
| GET | `/api/storage/download/{file_id}` | Bearer | Download encrypted bytes and metadata |

Uploads are multipart. The service stores ciphertext and opaque metadata only. Connector credentials belong in environment variables or the deployment secret store.

## Audit

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/audit` | Bearer | Append an audit entry |
| GET | `/api/audit` | Bearer | List the caller's audit entries |
| POST | `/api/audit/verify` | Bearer | Verify the caller's audit chain |
| GET | `/api/audit/admin/all` | Admin | List all audit entries |

Audit entries are hash-chained. The chain detects modification, but it does not make a malicious server honest; use an external anchor or export for stronger guarantees.

## Admin

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/admin/users` | Admin | List users |
| PATCH | `/api/admin/users/{user_id}` | Admin | Update account status |
| POST | `/api/admin/impersonate/{user_id}` | Admin | Issue an impersonation audit event and scoped token |
| GET | `/api/admin/flags` | Admin | Read runtime feature flags |
| PUT | `/api/admin/flags/{flag_name}` | Admin | Set a feature flag |
| GET | `/api/admin/health` | Admin | Admin health summary |

Admin routes require the `admin` role from Supabase metadata or a mock admin token. Impersonation must be audited and must never expose user plaintext or keys.

## Metrics

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/metrics/benchmark` | No | Latest benchmark records |
| GET | `/api/metrics/security-badge?profile=BALANCED` | No | Profile security label and parameters |
| GET | `/api/metrics/stream` | No | Server-Sent Events telemetry stream |

The security badge recognizes all six profiles, including `PQ_STRONG`. Unknown profile names return a safe default or validation error according to the route implementation.

## AI advisory

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/ai/recommend` | No | Rule-based recommendation from file metadata |
| POST | `/api/ai/chat` | No | Offline assistant response |
| GET | `/api/ai/concepts` | No | List knowledge-base concepts |

The advisory layer is rule-based and offline. It is not an external LLM call. Do not send file contents, plaintext, keys, or secrets to any advisory endpoint.

## Rate limits and middleware

- 120 requests per minute per client by default.
- 30 authentication requests per minute.
- CORS allows configured origins with credentials.
- The limiter is in-memory unless Redis is configured.

## Error behavior

| Status | Meaning |
|---|---|
| 400 | Invalid request or operation |
| 401 | Missing, malformed, or expired bearer token |
| 403 | Authenticated but not authorized |
| 404 | Resource or algorithm not found |
| 422 | Request validation failed |
| 500 | Configuration or server failure |

Cryptographic verification failures are surfaced as client-visible errors and must not be retried as if they were transient.

## Zero-knowledge checklist for API changes

Any new endpoint must answer:

1. Does it receive plaintext, a passphrase, a master key, or a raw file key? If yes, reject the design.
2. Does it log request bodies that could contain ciphertext-adjacent secrets? If yes, redact.
3. Does it cross-user isolate by authenticated subject rather than client-supplied IDs?
4. Does it preserve the exact ciphertext byte-for-byte?
5. Does it fail closed on malformed envelopes, hashes, or signatures?
