# CryptaVault

**AI-Assisted Adaptive Hybrid Cryptographic Storage Framework**

A zero-knowledge cryptographic framework that sits between users and storage providers, enforcing client-side encryption with adaptive (speed/security slider) classical + post-quantum hybrid cryptography.

## Status
🚧 **Planning Complete — Awaiting Phase P0 (Bootstrap) execution**

See [PLAN.md](PLAN.md) for the 74-task, 17-phase, 16-week master plan.

## Documents

| Document | Purpose |
|----------|---------|
| [PLAN.md](PLAN.md) | Master execution plan (74 tasks, 17 phases) |
| [ROADMAP.md](ROADMAP.md) | Timeline + dependency graph + milestone gates |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module map, data flow, DB schema, API surface, plugin contracts |
| [SRS.md](SRS.md) | Software Requirements Specification (formal) |
| [RISKS.md](RISKS.md) | Risks, assumptions, mitigations, deferred scope |
| [RESEARCH.md](RESEARCH.md) | Number theory + crypto research deliverables |
| [docs/](docs/) | Per-phase specs (17 files) |

## Quickstart (once Phase P0 completes)

```bash
# Backend (Python)
pip install -e packages/core packages/api packages/cli
cryptavault init

# Web client (Vite + React + WASM)
pnpm install
pnpm --filter cryptavault-web dev

# Admin console
pnpm --filter cryptavault-admin dev
```

## Stack
- **Language**: Python 3.11+ (crypto core + API + CLI) · TypeScript (web + admin)
- **Database / BaaS**: Supabase (PostgreSQL + Auth + RLS)
- **Interface**: REST API (FastAPI) + React Web Client (WASM crypto) + React Admin SPA (shadcn/ui) + Python CLI (Typer)
- **Post-Quantum**: liboqs (Kyber + Dilithium)
- **AI**: Rule-based heuristic + optional cloud LLM (OpenAI/Anthropic)

## License
MIT