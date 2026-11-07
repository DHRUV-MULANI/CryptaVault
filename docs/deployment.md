# Deployment Guide

## Static web portal

The portal is built by Vite and deployed to GitHub Pages by `.github/workflows/pages.yml`.

### Automatic deployment

Every push to `main`:

1. Checks out the repository.
2. Installs pnpm 9.15.0 and Node 20.
3. Runs `pnpm install --no-frozen-lockfile`.
4. Builds `@cryptavault/web` with `VITE_BASE=/<repository-name>/`.
5. Uploads `packages/web/dist` as a Pages artifact.
6. Deploys through the official Pages actions.

Manual runs are available through `workflow_dispatch`.

### Enable Pages once

If the repository has never had Pages enabled:

```bash
gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow
```

Check the configuration:

```bash
gh api repos/<owner>/<repo>/pages
```

Expected URL for this repository:

```text
https://dhruv-mulani.github.io/CryptaVault/
```

### Build locally

```bash
pnpm install
VITE_BASE=/CryptaVault/ pnpm --filter @cryptavault/web build
```

Output: `packages/web/dist`

For a root-domain deployment, omit `VITE_BASE` or set `VITE_BASE=/`.

Preview the production build:

```bash
pnpm --filter @cryptavault/web preview
```

The portal uses hash routing, so no server-side rewrite is required.

### Custom domain

1. Add the domain in repository **Settings → Pages → Custom domain**.
2. Create the DNS records GitHub requires.
3. Keep `VITE_BASE=/` for a root domain, or `/subpath/` for a project path.
4. Update the API CORS configuration if the portal calls the API:

```bash
export CRYPTAVAULT_CORS_ORIGINS=https://vault.example.com
```

5. Re-run the Pages workflow.

### Pages troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 404 on asset URLs | Wrong Vite base | Set `VITE_BASE` to the repository path with a trailing slash |
| Blank page | JavaScript error or stale cache | Check the browser console and hard-refresh |
| Deploy job fails at configure-pages | Pages not enabled or permissions missing | Enable Pages with `build_type=workflow`; keep `pages: write` and `id-token: write` |
| Share link 404 | Hash route was converted to a path or base is wrong | Use the generated link unchanged |
| `pnpm install` prompt about purging modules | Non-interactive CI with an existing `node_modules` | Use `CI=1` locally; CI is already non-interactive |

## Local Python environment

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python \
  -e packages/core -e packages/api -e packages/cli \
  pytest hypothesis ruff black mypy httpx
source .venv/bin/activate
```

Post-quantum support:

```bash
uv pip install --python .venv/bin/python -e 'packages/core[pq]'
# Native liboqs must be installed and discoverable.
```

### Known workspace issue

The repository root is a uv workspace without a packaged root project. `uv run` and `uv sync` can fail with setuptools auto-discovery errors. Use the virtualenv binaries directly:

```bash
.venv/bin/python -m pytest
.venv/bin/cryptavault status
.venv/bin/uvicorn cryptavault_api.main:app
```

Or install editable packages explicitly as shown above.

## API deployment

The API is a standard ASGI application.

```bash
uvicorn cryptavault_api.main:app --host 0.0.0.0 --port 8000
```

For production, run behind a TLS-terminating reverse proxy and set:

| Variable | Required | Purpose |
|---|---|---|
| `SUPABASE_URL` | For auth and storage | Supabase project URL |
| `SUPABASE_KEY` / `SUPABASE_ANON_KEY` | For auth and storage | Client key |
| `SUPABASE_SERVICE_ROLE_KEY` | For privileged operations | Server key; keep secret |
| `PUBLIC_SHARE_DOMAIN` | Recommended | Base URL for share links |
| `CRYPTAVAULT_CORS_ORIGINS` | If portal is on another origin | Comma-separated origins |
| `REDIS_URL` | Optional | Shared rate-limit backend |

Never commit `.env` files or credentials. The repository's `.env` is a development placeholder; review it before any public deployment.

The current share, user, manifest, and audit stores may be in-memory depending on the route. Production requires durable database-backed stores and a shared rate limiter. The API is not a substitute for the client-side encryption boundary.

## Container and storage deployment

The core pipeline writes encrypted containers. Storage connectors accept ciphertext only.

```bash
cryptavault storage upload document.vault supabase://vaults
cryptavault storage upload document.vault r2://my-bucket
cryptavault storage upload document.vault local://./vault-data
```

Configure connector credentials through environment variables or the platform secret store. Grant the minimum permissions required to read and write the vault prefix.

## CI

`.github/workflows/ci.yml` runs:

- Python 3.11 and 3.12: ruff, black check, mypy, pytest.
- Node 20: pnpm install, typecheck, build.

`.github/workflows/pages.yml` runs on `main` only and deploys the web portal.

The Python CI installs liboqs through the environment used by the job. If PQ tests fail in CI with `OqsNotAvailableError`, install the native library or mark the PQ suite as environment-gated rather than weakening the assertion.

## Release checklist

1. `pytest` passes locally.
2. `ruff check .`, `black --check .`, and `mypy` pass.
3. `pnpm --filter @cryptavault/web typecheck` and `build` pass.
4. Catalog snapshot is regenerated if profiles or algorithms changed.
5. No secrets or `.env` changes are staged.
6. Documentation matches behavior.
7. Push to `main` and confirm the Pages deployment.
8. Open the live portal and run the Status self-test.
9. Create a small share, open it in a private window, and decrypt it.
10. Confirm the share viewer works without an account or API.
