# CryptaVault — Roadmap

## Timeline — 16 Weeks, 17 Phases

```
Week 1:    P0  Bootstrap ─────────────────────────────► [Setup Gate]
                         │
Weeks 2-3: P1  Classical Crypto ──────────────────────► [Crypto Gate]
                         │
Week 4:    P2  Post-Quantum ──────────────────────────► [PQ Gate]
                         │
Week 5:    P3  Signatures + Integrity ────────────────► [Integrity Gate]
                         │
Week 6:    P4  Key Management ────────────────────────► [KMS Gate]
                         │
Week 7:    P5  Adaptive Security Engine ─────────────► [Engine Gate]
                         │
Week 8:    P6  Compression ──────────────────────────► [Compression Gate]
                         │
Week 9:    P7  Streaming Pipeline ───────────────────► [Pipeline Gate]
                         │
Week 10:   P8  Metadata + Secure Deletion ────────────► [Metadata Gate]
                         │
Week 11:   P9  API + Auth Backend (Supabase) ────────► [API Gate]   ┐
                         │                                            │
Week 12:   P10 Storage Connectors ───────────────────► [Storage Gate]┤
                         │                                            │
Week 13:   P11 Secure Sharing ───────────────────────► [Sharing Gate]┘
                         │
Week 14:   P12 Web Client (WASM) ─┐
           P13 Admin Console ────┴──────────────────► [Clients Gate]
                         │
Week 15:   P14 Dashboard + Benchmark Lab ─┐
           P15 AI Assistant ─────────────┴──────────► [UI/AI Gate]
                         │
Week 16:   P16 Integration + Report ─────────────────► [RELEASE v1.0.0]
```

## Phase Dependency Graph

```
P0 ──┬─► P1 ──► P2 ──► P3 ──► P4 ──► P5 ──► P6 ──► P7 ──► P8 ──────────┐
     │                                                                  │
     ├─► P9  (API + Auth) ─────────────────────────────► P11 (Sharing)─┤
     │                                  ▲                               │
     └─► P10 (Storage) ─────────────────┼───────────────────────────────┤
                                        ▼                               │
                                        P12 (Web Client WASM) ─────────►│
                                        P13 (Admin SPA) ──────────────►│
                                        P14 (Dashboard + Bench) ─────►│
                                        P15 (AI) ────────────────────►│
                                                                       ▼
                                                                   P16 (Integration + Report)
```

**Critical path**: P0 → P1 → P2 → P3 → P4 → P5 → P7 → P8 → P12 → P16

## Parallelization Opportunities

- **P0.5 OAuth registrations** run during P0.1–P0.4 (start Week 1, approvals take days).
- **P9 (API) and P10 (Storage)** run in parallel (both start after P0; no interdependency).
- **P12 (Web WASM) and P13 (Admin SPA)** run in parallel (Week 14; different teams/files).
- **P14 (Dashboard) and P15 (AI)** run in parallel (Week 15).
- **P10.2–P10.4 (Local, SFTP, FTP)** independent of **P10.5–P10.7 (cloud)** — parallelizable.

## Milestone Gates

| # | Gate | Week | Criteria |
|---|------|------|----------|
| 1 | Setup | 1 | liboqs works, repo scaffolded, OAuth creds obtained, Supabase project provisioned |
| 2 | Crypto Core | 3 | Classical primitives pass all KATs |
| 3 | PQ Integrated | 4 | Kyber + Dilithium round-trip; hybrid KEM works |
| 4 | Integrity | 5 | Merkle + signatures verify tamper across 1000 leaves |
| 5 | KMS | 6 | Generate/rotate/backup/recover/destroy all work |
| 6 | Engine | 7 | 5 profiles resolve to correct configs |
| 7 | Compression | 8 | 4 algorithms stream + skip policy works |
| 8 | Pipeline | 9 | 1GB file E2E through orchestrator |
| 9 | Metadata | 10 | Encrypted manifest round-trips |
| 10 | API + Auth | 11 | Supabase Auth + FastAPI routes + RLS verified |
| 11 | Storage | 12 | 5 connectors round-trip 50MB |
| 12 | Sharing | 13 | QR + token + password + invitation shares work |
| 13 | Web Client | 14 | Browser crypto round-trips 100MB; keys stay in browser |
| 14 | Admin | 14 | Admin SPA CRUD + RBAC enforced |
| 15 | Dashboard + Bench | 15 | Live metrics + benchmark charts render |
| 16 | AI | 15 | Recommender + optional LLM work; no data leak |
| 17 | Release | 16 | Demo reproducible; report complete; tag v1.0.0 |

## Effort Distribution

| Category | Phases | % Effort |
|----------|--------|----------|
| Crypto Core (P1-P3) | 3 | 20% |
| Key Mgmt + Adaptive + Compression + Pipeline (P4-P7) | 4 | 25% |
| Backend (API + Storage + Sharing) (P9-P11) | 3 | 20% |
| Frontend (Web WASM + Admin + Dashboard) (P12-P14) | 3 | 20% |
| AI + Integration + Report (P15-P16) | 2 | 10% |
| Bootstrap (P0) | 1 | 5% |

## Deliverables per Phase

| Phase | Deliverable | Acceptance |
|-------|-------------|-----------|
| P0 | Repo, liboqs, deps, CI, OAuth, Supabase schema, plugin skeleton | All gates pass |
| P1 | Symmetric, asymmetric, hash, KDF modules | KATs + Hypothesis green |
| P2 | Kyber, Dilithium, hybrid KEM/sig | PQ KATs green |
| P3 | Signature layer, tamper detection, Merkle, integrity reports | 1000-leaf Merkle verified |
| P4 | KMS hierarchy, keystore, rotate, backup, import/export | Full lifecycle works |
| P5 | 5 profiles, adaptive engine, multi-layer, FS ratchet, audit, CLI | Slider resolution correct |
| P6 | File detect, policy, 4 algos, metrics, pipeline stage | Skip policy correct |
| P7 | Chunked, parallel, resume, queue, orchestrator | 1GB E2E < 200MB RAM |
| P8 | Metadata model, encrypted manifest, secure delete, toggles | Manifest round-trips; tamper detected |
| P9 | FastAPI app, Supabase auth, user/share/audit routes, rate limit | RLS enforced cross-user |
| P10 | Local, SFTP, FTP, GDrive, OneDrive, Dropbox, URI resolver | 5 connectors round-trip 50MB |
| P11 | Share packages, tokens, links, passwords, QR, invitations | All share modes work |
| P12 | WASM build, React scaffold, crypto wrappers, UI, widgets | 100MB browser round-trip |
| P13 | Admin SPA, users, audit, sessions, providers, flags, health | RBAC enforced; CRUD works |
| P14 | Benchmark suite, charts, SSE metrics, dashboard, security badge | Live metrics + charts render |
| P15 | Rule-based recommender, LLM provider, chat endpoint, KB fallback | No data leak enforced |
| P16 | E2E matrix, CLI polish, research notes, report, demo, tag v1.0.0 | Demo reproducible |

---

_End of ROADMAP.md_