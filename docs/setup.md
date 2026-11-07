# CryptaVault Development Environment Setup

This document covers local setup for the Python engine, CLI, API, and static web portal. For the complete command reference see [cli.md](cli.md); for portal usage see [portal.md](portal.md); for deployment see [deployment.md](deployment.md).

---

## 1. Prerequisites

- **Linux OS** (Tested on Arch Linux / Ryoku / Ubuntu 22.04+)
- **Python 3.11** (Managed via `uv` or system)
- **Node.js 20+** with `pnpm` (via `npx -y pnpm` or standalone `pnpm`)
- **C Toolchain**: `gcc` / `clang`, `make`, `openssl-dev`

---

## 2. Python Workspace Setup

1. **Virtual Environment Creation**:
   ```bash
   uv venv .venv --python 3.11
   ```

2. **Install Workspace Packages in Editable Mode**:
   ```bash
   uv pip install --python .venv/bin/python \
     -e packages/core \
     -e packages/api \
     -e packages/cli \
     pytest hypothesis ruff black mypy httpx cmake ninja
   ```

3. **Post-Quantum Cryptography (`liboqs`)**:
   `liboqs-python` bundles automated compilation using `cmake` and `ninja`. With `cmake` available in `.venv/bin`, running:
   ```bash
   uv pip install --python .venv/bin/python liboqs-python
   ```
   installs the Python bindings and may compile native `liboqs` when a matching shared library is not already present. Verify with `.venv/bin/python -c "import oqs; print(oqs.get_enabled_kem_mechanisms()[:3])"`.
   
   - **KEM Verified**: Kyber768 / ML-KEM-768 (32-byte shared secret, 1088-byte ciphertext)
   - **Signature Verified**: ML-DSA-65 / Dilithium3 (1952-byte public key, 3309-byte signature)
   - **KAT Baseline**: [pq_baseline.json](../packages/core/tests/kat/pq_baseline.json)

---

## 3. TypeScript & Web Workspace Setup

1. **Install Node dependencies**:
   ```bash
   npx -y pnpm install
   ```

2. **Run TypeScript typecheck across all web packages**:
   ```bash
   npx -y pnpm run typecheck
   ```

3. **Build the web portal and standalone admin scaffold**:
   ```bash
   npx -y pnpm run build
   ```

4. **Run the portal locally**:
   ```bash
   pnpm --filter @cryptavault/web dev
   ```
   Open the printed URL (usually `http://localhost:5173`). No API is required for the local vault, file encryption, share viewer, messages, catalog, or settings.

5. **Production Pages build**:
   ```bash
   VITE_BASE=/CryptaVault/ pnpm --filter @cryptavault/web build
   ```

---

## 4. Supabase Setup

1. Copy `.env.example` to `.env`:
   ```bash
   SUPABASE_URL="https://<your-project-id>.supabase.co"
   SUPABASE_KEY="<your-anon-key>"
   SUPABASE_ANON_KEY="<your-anon-key>"
   ```
2. Apply migrations in your Supabase SQL Editor:
   - Run [0001_init.sql](../supabase/migrations/0001_init.sql)
   - Run [0002_rls.sql](../supabase/migrations/0002_rls.sql)

---

## 5. Run the API

```bash
.venv/bin/uvicorn cryptavault_api.main:app --host 127.0.0.1 --port 8000 --reload
```

OpenAPI: `http://127.0.0.1:8000/docs`. The static portal does not require this service.

## 6. Containerized Development (`Dockerfile.dev`)

If you prefer building in a clean Docker container:
```bash
docker build -f Dockerfile.dev -t cryptavault:dev .
docker run -it -p 8000:8000 -p 3000:3000 -p 3001:3001 cryptavault:dev
```
