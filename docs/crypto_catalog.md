# Crypto Catalog and Security Profiles

CryptaVault never hard-codes a primitive into a file format. Identity, metadata, lifecycle state, and stable wire IDs live in one catalog in `packages/core/cryptavault/crypto/catalog.py`. The adaptive engine, container header, API, CLI, and web portal all resolve algorithms through that catalog.

## Why the catalog exists

- **Crypto agility without data loss.** A file records the exact algorithms and wire IDs used to create it. Changing defaults later does not make old files unreadable.
- **Fail-closed lifecycle gates.** Forbidden algorithms cannot be selected. Legacy and experimental algorithms require explicit policy. Missing runtimes raise instead of silently falling back.
- **One source of truth.** The API exposes the catalog; the portal imports a generated snapshot; tests assert identity and wire-ID uniqueness.

## Catalog size

Generated snapshot: `packages/web/src/generated/catalog.json`

| Metric | Count |
|---|---:|
| Algorithms | 88 |
| Families | 9 |
| Production | 67 |
| Experimental | 14 |
| Legacy | 3 |
| Forbidden | 4 |
| Implemented in this repository | 26 |
| Missing runtime dependency | 6 |

Family distribution:

| Family | Count |
|---|---:|
| Signature | 25 |
| Hash | 17 |
| Symmetric AEAD | 16 |
| KEM | 15 |
| KDF | 7 |
| PAKE | 3 |
| RNG | 2 |
| Quantum / experimental | 2 |
| Secret sharing | 1 |

## Stable wire IDs

The high byte identifies the family. The low byte distinguishes algorithms inside the family. Wire IDs are permanent because they are persisted inside containers and manifests; an ID must never be reused for a different algorithm.

| Prefix | Family |
|---|---|
| `0x01` | Symmetric AEAD |
| `0x02` | Hash |
| `0x03` | KDF |
| `0x04` | KEM |
| `0x05` | Signature |
| `0x06` | PAKE |
| `0x07` | Secret sharing |
| `0x08` | RNG |
| `0x09` | Quantum / experimental |

Container headers store both the canonical algorithm ID and the wire ID and reject mismatches. During decryption the wire ID is resolved through the catalog, its family is checked, its algorithm ID must match the header, and runtime availability is required for primitives that will actually execute.

## Lifecycle status

| Status | Use |
|---|---|
| `production` | Permitted by default when runtime requirements are present |
| `experimental` | Requires explicit policy; never selected automatically by the static portal |
| `legacy` | Read/compatibility use; new writes require explicit permission |
| `forbidden` | Always rejected, including reads that would require the primitive |

Known forbidden entries include MD4, MD5, SIKE, and Rainbow. SHA-1 is marked legacy rather than forbidden so historical artifacts can be identified without treating it as a safe default.

## Six security profiles

Source: `packages/core/cryptavault/adaptive/profiles.py`

| Level | Name | Slider | AEAD | Hash | KEM | Signature | KDF memory / time | Chunk | PQ | Metadata encryption | Forward secrecy | Multi-layer |
|---|---|---|---:|---|---:|---|---:|---:|---|---|---|---|
| `PERFORMANCE` | Performance Optimized | 0–20 | aes-256-gcm | blake3 | x25519 | ed25519 | 32 MiB / 2 | 4 MiB | No | No | No | No |
| `STANDARD` | Standard Security | 20–40 | aes-256-gcm | sha256 | x25519 | ed25519 | 48 MiB / 3 | 4 MiB | No | Yes | No | No |
| `BALANCED` | Balanced (Default) | 40–60 | aes-256-gcm | sha256 | hybrid-kem-classical | ed25519 | 64 MiB / 3 | 4 MiB | Yes | Yes | No | No |
| `STRONG` | Strong Security | 60–80 | chacha20-poly1305 | blake3 | hybrid-kem-pq | hybrid-sig-pq | 64 MiB / 4 | 8 MiB | Yes | Yes | Yes | No |
| `PQ_STRONG` | Post-Quantum Strong | 80–90 | aes-256-gcm | sha3-512 | hybrid-kem-pq | hybrid-sig-pq | 96 MiB / 5 | 8 MiB | Yes | Yes | Yes | No |
| `MAXIMUM` | Maximum Post-Quantum | 90–100 | aes-256-gcm cascade | sha3-512 | hybrid-kem-pq | hybrid-sig-pq | 128 MiB / 5 | 16 MiB | Yes | Yes | Yes | Yes |

Slider resolution is half-open from 0 through 90 and closed at 100:

```text
0 ≤ p < 20    → PERFORMANCE
20 ≤ p < 40   → STANDARD
40 ≤ p < 60   → BALANCED
60 ≤ p < 80   → STRONG
80 ≤ p < 90   → PQ_STRONG
90 ≤ p ≤ 100  → MAXIMUM
```

Values outside `[0, 100]` raise `ValueError`.

### Profile behavior in the core pipeline

- `PERFORMANCE` disables metadata encryption by profile policy and uses a lighter KDF.
- `BALANCED` is post-quantum ready through a hybrid classical KEM selection but does not enable all PQ signature paths.
- `STRONG` switches to ChaCha20-Poly1305 for side-channel resilience and enables forward-secrecy ratcheting.
- `PQ_STRONG` mandates post-quantum hybrid primitives and uses SHA3-512.
- `MAXIMUM` adds multi-layer AEAD through the cascade implementation and uses the largest KDF memory and chunk size.

Post-quantum execution depends on the native `liboqs` library. When it is absent, PQ operations fail closed with `OqsNotAvailableError`; they do not downgrade.

### Browser portal profile mapping

The static portal mirrors the profile names, descriptions, slider bands, and chunk sizes. Its vault-level KDF is PBKDF2-SHA256 with 210,000 iterations because Web Crypto supports PBKDF2 in all target browsers. Per-file payloads use AES-256-GCM and optional gzip. The portal does not run liboqs, so the catalog's post-quantum entries are informational there.

## API

The catalog is exposed by `packages/api/cryptavault_api/routes/crypto.py`.

### `GET /api/crypto/catalog`

Query parameters:

| Parameter | Type | Meaning |
|---|---|---|
| `family` | string | Filter by family: `symmetric`, `hash`, `kdf`, `kem`, `signature`, `pake`, `secret-sharing`, `rng`, `quantum` |
| `status` | string | Filter by `production`, `experimental`, `legacy`, `forbidden` |
| `implemented_only` | boolean | Only algorithms that are implemented and have present runtime requirements |

Response contains the families, statuses, and algorithm records with IDs, wire IDs, size metadata, PQ level, hardware acceleration, implementation state, runtime availability, requirements, aliases, replacement guidance, and description.

```bash
curl 'http://127.0.0.1:8000/api/crypto/catalog?family=symmetric&implemented_only=true'
```

### `GET /api/crypto/catalog/{algorithm_id}`

Resolves a canonical ID or alias. Returns `404` for unknown IDs.

```bash
curl http://127.0.0.1:8000/api/crypto/catalog/aes-256-gcm
```

### `GET /api/crypto/profiles`

Returns the six profiles with full configuration and slider bands.

```bash
curl http://127.0.0.1:8000/api/crypto/profiles
```

## Regenerating the web snapshot

```bash
PYTHONPATH=packages/core:packages/api:packages/cli \
  .venv/bin/python scripts/export_web_catalog.py
```

The script writes `packages/web/src/generated/catalog.json`, which is imported by `packages/web/src/lib/profiles.ts`. Regenerate it whenever the Python catalog or profiles change.

## Adding an algorithm

1. Register an `AlgorithmSpec` with a permanent, unique wire ID in the correct high-byte range.
2. Add aliases and lifecycle status.
3. Implement the primitive and register it in the matching plugin registry.
4. Declare runtime requirements so the catalog can report environment availability.
5. Add tests for identity collisions, wire-ID round trips, forbidden rejection, alias resolution, and runtime gating.
6. Regenerate the web snapshot.
7. Update this document and the API response expectations if the public shape changes.

## Invariants

- Wire IDs are unique and never reused.
- Canonical IDs and aliases are case-insensitive and collision-checked.
- A container header must contain bindings for symmetric, hash, signature, KEM, and KDF families.
- A binding's family, ID, and wire ID must agree during decryption.
- Unknown or forbidden algorithms fail closed.
- Production defaults never silently select experimental, legacy, or forbidden primitives.
