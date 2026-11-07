# @cryptavault/admin

Standalone React/Vite governance console scaffold for server-backed administration.

This package builds, but it is not the console deployed with the public portal. The GitHub Pages deployment ships the admin route inside `packages/web` (`#/admin`), which operates only on the local browser vault. Server governance, impersonation, global flags, and audit-chain endpoints live in `packages/api/cryptavault_api/routes/admin.py`.

## Develop

```bash
pnpm install
pnpm --filter @cryptavault/admin dev
```

## Build and typecheck

```bash
pnpm --filter @cryptavault/admin typecheck
pnpm --filter @cryptavault/admin build
```

See [docs/portal.md](../../docs/portal.md) and [docs/api.md](../../docs/api.md).
