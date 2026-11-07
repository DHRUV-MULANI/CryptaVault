# @cryptavault/web

Static zero-knowledge portal for CryptaVault. React 18, Vite 6, Tailwind 3, and the Web Crypto API. All encryption and decryption happen in the browser; records are stored in IndexedDB.

Live deployment: https://dhruv-mulani.github.io/CryptaVault/

## Develop

```bash
pnpm install
pnpm --filter @cryptavault/web dev
```

## Build

```bash
VITE_BASE=/CryptaVault/ pnpm --filter @cryptavault/web build
```

Output: `dist/`

## Typecheck

```bash
pnpm --filter @cryptavault/web typecheck
```

## Structure

- `src/lib/crypto.ts` — WebCrypto primitives, chunked `CVW1` containers, sharing.
- `src/lib/db.ts` — IndexedDB stores.
- `src/lib/vault.tsx` — vault lifecycle, settings, passphrase rotation, auto-lock.
- `src/lib/hooks.ts` — reactive file, share, audit, thread, and message queries.
- `src/pages/` — dashboard, vault, shares, share viewer, messages, catalog, academy, admin, settings, status.
- `src/generated/catalog.json` — catalog snapshot generated from the Python catalog.

Full user and security documentation: [docs/portal.md](../../docs/portal.md), [docs/security_model.md](../../docs/security_model.md).
