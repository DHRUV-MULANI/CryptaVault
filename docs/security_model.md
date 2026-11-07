# Security Model

This document states what CryptaVault protects, what it does not protect, and where the static deployment trades server enforcement for client-only operation.

## Zero-knowledge boundary

The boundary is the client process:

- The Python CLI runs on the operator's machine.
- The browser portal runs in the user's tab.
- The FastAPI backend and every storage backend are outside the boundary.

Inside the boundary:

- Plaintext bytes.
- User passphrases.
- Derived master keys and per-file keys.
- Unwrapped share keys.
- Decrypted metadata and message bodies.

Outside the boundary, only the following may be stored or transmitted:

- Ciphertext and authentication tags.
- Encrypted manifests and encrypted message bodies.
- Wrapped keys.
- Non-identifying operational metadata such as timestamps, sizes, and opaque IDs required for coordination.

The browser portal does not call the API at all in the GitHub Pages deployment. The core CLI only sends ciphertext through storage connectors.

## Assets

| Asset | Protection |
|---|---|
| File contents | Per-file AEAD; per-file key wrapped by master key |
| File names, MIME types, hashes | Sealed manifest with AAD binding to file ID |
| Master key | Derived from passphrase; never persisted in plaintext |
| Vault verifier | Sealed known plaintext |
| Share contents | Self-contained ciphertext plus wrapped share key |
| Message bodies | Per-message AEAD; per-message key wrapped by master key |
| Keystore | Encrypted envelope plus BIP-39 recovery bundle |
| Audit events | Local IndexedDB record; API audit chain when enabled |

## Adversaries considered

### Storage or cloud provider

The provider sees ciphertext, container headers, encrypted manifests, wrapped keys, and any transport metadata. It cannot read file contents or file names without the client keys. A malicious provider can delete, replay, reorder, or withhold data; integrity checks detect modification and the client must handle unavailability.

### Network attacker

TLS protects transport to remote connectors and the API. A network attacker who captures ciphertext cannot decrypt it without the relevant key. A capability share URL contains the key in its fragment; anyone who obtains the full URL obtains the capability.

### Malicious or curious server operator

The API is designed to coordinate without receiving plaintext. Admin routes can manage users, flags, and audit records, but cannot derive user keys from stored material. A server operator can still observe request timing, sizes, account identity, and access patterns.

### Local device attacker

An attacker with code execution in the browser tab or CLI process can read keys and plaintext while the vault is unlocked. This model cannot defend against a compromised endpoint. Malicious browser extensions, injected scripts, or a compromised dependency are in scope for the attacker and out of scope for cryptographic protection.

### Offline attacker with stolen storage

An attacker with a copy of IndexedDB or an exported backup has ciphertext and wrapped keys. They must guess the passphrase. The browser uses PBKDF2-SHA256 with 210,000 iterations; the CLI uses Argon2id with profile-specific memory and time costs. A weak passphrase is the primary risk.

## Cryptographic choices

### Core engine

- Argon2id for passphrase-based key derivation with profile-specific memory, time, and parallelism.
- AES-256-GCM and ChaCha20-Poly1305 AEAD.
- Optional cascade AEAD for the `MAXIMUM` profile.
- BLAKE3, SHA-256, and SHA3-512 hashing.
- Merkle tree over serialized chunks.
- Ed25519 and hybrid post-quantum signature/KEM paths.
- Per-chunk AAD binding file ID, chunk index, and final marker.

### Browser portal

- PBKDF2-SHA256, 16-byte random salt, 210,000 iterations, AES-256-GCM derived key.
- Random 256-bit per-file key.
- AES-256-GCM per chunk with a 12-byte random IV and AAD binding file ID, index, and final marker.
- Optional gzip before encryption.
- Separate sealed manifest, wrapped key, thread, message, and share records.
- SHA-256 fingerprints for local diagnostics and share metadata.

PBKDF2 is used in the browser because Web Crypto exposes it universally. It is weaker against GPU/ASIC guessing than Argon2id. The portal therefore requires a passphrase of at least 10 characters, but this is a minimum, not a strength guarantee.

## What the server can see

When the API is enabled, the server may see:

- Account identity and session metadata.
- Encrypted manifests and ciphertext.
- File sizes, timestamps, and opaque identifiers.
- Share creation and consumption events.
- Audit events submitted by clients.
- Admin actions and feature flags.
- Request timing and rate-limit behavior.

The server must never see plaintext, passphrases, master keys, raw file keys, or decrypted share keys. Any change that violates this boundary is a security defect, not a feature trade-off.

## Sharing model

A share is a capability. The key is in the URL fragment or the bundle, so:

- Possession of the complete link or bundle is authorization.
- A passphrase adds a second factor for the share key.
- Revoking a local record does not revoke a copied link.
- Expiry is advisory in the static deployment and enforceable only with server coordination.
- One-time consumption is enforceable only with server state.

Recipients should treat share links like passwords.

## Local persistence

The portal stores encrypted records in IndexedDB. Practical consequences:

- Clearing site data destroys the local vault.
- Private browsing may disable or discard storage.
- A different browser or device has no access without an exported backup.
- An exported `.cvbackup.json` is still ciphertext; the passphrase is required.
- The display name and some policy fields are local configuration, not secrets.

## Static hosting

GitHub Pages serves immutable build assets over HTTPS. Risks and mitigations:

- **Supply chain.** The build depends on npm packages and GitHub Actions. Pin and review dependencies; the workflow uses standard official actions.
- **Injected script.** A compromised build or hosting account could exfiltrate keys from an unlocked tab. The project does not claim protection against a compromised origin.
- **Caching.** Old assets may remain in caches; cryptographic format changes must remain backward compatible or explicitly migrate.
- **No server headers.** The static deployment cannot enforce custom CSP, HSTS, or cookie policy beyond what GitHub Pages provides. A custom domain or reverse proxy can add headers.

## Post-quantum caveats

- liboqs must be installed natively. Without it, PQ operations fail closed.
- Hybrid constructions combine classical and post-quantum components. The security claim is no weaker than the stronger component under the stated composition, not a proof of a new primitive.
- Parameters and mechanism names can change across liboqs versions. Container headers persist the chosen algorithm identity so a later environment can detect unsupported primitives.

## Non-goals

- Protection against a compromised endpoint.
- Deniable encryption.
- Protection against traffic analysis by a network observer.
- Server-enforced access control in the static portal.
- Audited production readiness.
- Metadata hiding from the storage provider in the core pipeline. Container headers are authenticated but not confidential.

## Reporting

Do not include real secrets, private keys, or user data in a report. Provide a minimal reproduction, affected version/commit, and the security property that failed.
