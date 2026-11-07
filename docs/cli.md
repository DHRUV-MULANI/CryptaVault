# CryptaVault CLI Reference

The `cryptavault` command is a Typer application in `packages/cli`. It performs key derivation, encryption, integrity checks, sharing coordination, storage operations, and offline education/advisory.

## Install

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e packages/core -e packages/cli
source .venv/bin/activate
cryptavault --help
```

Optional post-quantum support:

```bash
uv pip install --python .venv/bin/python -e 'packages/core[pq]'
# Native liboqs must be available to the dynamic loader.
```

If `uv run` reports workspace package-discovery errors, invoke the venv binary directly: `.venv/bin/cryptavault ...`.

## Global commands

### `cryptavault status`

Checks AES-NI, AVX2, post-quantum runtime availability, and states the zero-knowledge boundary. No file or key data is sent anywhere.

```bash
cryptavault status
```

### `cryptavault version`

Prints the CLI version.

### `cryptavault benchmark`

Runs live micro-benchmarks for AES, ChaCha20, BLAKE3, Argon2id, and post-quantum mechanisms when available.

```bash
cryptavault benchmark
```

### `cryptavault profiles`

Prints all six profiles with AEAD, KEM, signature, KDF, chunk size, and threat-model notes.

### `cryptavault profile list`

Prints the six presets and slider bands:

| Preset | Slider | Post-quantum |
|---|---|---|
| `PERFORMANCE` | 0–20 | No |
| `STANDARD` | 20–40 | No |
| `BALANCED` | 40–60 | Hybrid readiness |
| `STRONG` | 60–80 | Yes |
| `PQ_STRONG` | 80–90 | Yes |
| `MAXIMUM` | 90–100 | Yes |

### `cryptavault profile set --slider N`

Resolves a slider percentage to a profile and persists it as the active profile.

```bash
cryptavault profile set --slider 85   # PQ_STRONG
cryptavault profile set --slider 95   # MAXIMUM
cryptavault profile get
```

## Key management

### `cryptavault keygen`

Creates a 256-bit master key, prints a 24-word BIP-39 recovery phrase, and writes an encrypted keystore plus a recovery bundle.

```bash
cryptavault keygen --output vault.keystore --passphrase "correct horse battery staple"
```

Outputs:

- `vault.keystore` — encrypted keystore envelope.
- `vault.recovery.json` — recovery bundle for offline validation.

The recovery phrase is displayed once. Anyone with it can recover the key material. Store it offline.

### `cryptavault inspect-keystore`

Decrypts the keystore envelope with the passphrase and prints key IDs, tiers, algorithms, creation times, and SHA-256 fingerprints. It does not print raw key bytes.

```bash
cryptavault inspect-keystore --keystore vault.keystore --passphrase "correct horse battery staple"
```

### `cryptavault recover-key`

Validates a BIP-39 mnemonic and prints a fingerprint. With `--bundle`, it unwraps the recovery bundle to validate the master key.

```bash
cryptavault recover-key "word1 word2 ... word24"
```

## Authenticated encryption

### `cryptavault encrypt`

Encrypts a file or a text string with a passphrase-derived key.

```bash
cryptavault encrypt --input secrets.txt --output secrets.enc --profile BALANCED
cryptavault encrypt --text "database password" --output secret.enc --passphrase "LongPassphrase123!"
```

Options:

| Option | Meaning |
|---|---|
| `--input`, `-i` | Plaintext file |
| `--text`, `-t` | Plaintext string |
| `--output`, `-o` | Ciphertext envelope path |
| `--profile` | `PERFORMANCE`, `STANDARD`, `BALANCED`, `STRONG`, `PQ_STRONG`, `MAXIMUM` |
| `--passphrase`, `-p` | Passphrase for key derivation |

The default demo passphrase is not suitable for real data. Always set `--passphrase` or use the keystore pipeline.

### `cryptavault decrypt`

Authenticates and decrypts an envelope or file.

```bash
cryptavault decrypt --input secrets.enc --output secrets.txt --passphrase "LongPassphrase123!"
cryptavault decrypt --ciphertext "CV1:..." --passphrase "LongPassphrase123!"
```

Authentication failure aborts decryption.

## Full pipeline

### `cryptavault pipeline-encrypt`

Runs compression detection, chunked AEAD, Merkle hashing, and optional signing, then writes a `CVV2` container.

```bash
cryptavault pipeline-encrypt document.pdf --output document.vault --profile MAXIMUM
```

Options: `--output/-o`, `--profile`, `--passphrase/-p`.

The current orchestrator reads the whole input for compression before chunk encryption. It is not yet a bounded-memory streaming implementation.

### `cryptavault pipeline-decrypt`

Reads `CVV2`, validates header algorithm bindings, decrypts chunks, verifies the Merkle root and optional signature, and writes plaintext. Legacy `CVV1` containers are read through a compatibility path.

```bash
cryptavault pipeline-decrypt document.vault --output restored.pdf --profile MAXIMUM
```

The profile argument is accepted for compatibility; the container header is authoritative.

## Integrity and signatures

### `cryptavault sign`

Signs a file with the hybrid signature implementation (Ed25519 plus Dilithium-3 when liboqs is available). Writes `<file>.sig` and `<file>.pub` by default.

```bash
cryptavault sign release.tar.gz --output-sig release.sig
```

### `cryptavault verify`

Verifies a detached signature.

```bash
cryptavault verify release.tar.gz --sig release.sig --pubkey release.tar.gz.pub
```

### `cryptavault merkle`

Builds a BLAKE3 Merkle tree over a directory and prints the root and leaf hashes.

```bash
cryptavault merkle --dir ./data
```

## Sharing

The CLI share commands create a signed `SharePackage`, a timed capability link, and an optional ASCII QR code. They coordinate metadata; they do not encrypt the ciphertext file itself. Use `pipeline-encrypt` first.

### `cryptavault share create`

```bash
cryptavault share create document.vault --timed 3600 --max-uses 1 --qr
cryptavault share create document.vault --password "RecipientSecret123!" --domain https://vault.example.com
```

Options:

| Option | Default | Meaning |
|---|---|---|
| `--output`, `-o` | `share.json` | SharePackage output |
| `--timed`, `-t` | `3600` | Link lifetime in seconds |
| `--max-uses`, `-u` | `1` | Consumption limit |
| `--password`, `-p` | none | Password-wrap the share key |
| `--domain`, `-d` | `PUBLIC_SHARE_DOMAIN` or `https://cryptavault.local` | Base URL |
| `--qr` | on | Render an ASCII QR code |

### `cryptavault share inspect`

Verifies the SharePackage signature and prints expiry and recipient information.

```bash
cryptavault share inspect share.json
```

### `cryptavault share qr`

Renders any URL or text as an ASCII QR code.

```bash
cryptavault share qr "https://example.com/share#token"
```

Server-enforced expiry and one-time consumption require the FastAPI sharing routes. A static link cannot be revoked after it is copied.

## Storage

`storage` resolves a connector from a URI and moves encrypted files only.

```bash
cryptavault storage upload document.vault local://./vault-data
cryptavault storage upload document.vault supabase://vaults
cryptavault storage upload document.vault r2://my-bucket
cryptavault storage list local://./vault-data
cryptavault storage download local://./vault-data/document.vault ./restored.vault
```

Supported URI families include local, Supabase, R2/S3-compatible, SFTP, FTPS, and cloud adapters. Each connector needs its own environment variables or credentials. Never put secrets in shell history or committed files.

## Education and advisory

### `cryptavault teach [topic]`

Prints an implementation-aligned tutorial. Run without a topic to list keys.

```bash
cryptavault teach
cryptavault teach zero-knowledge
cryptavault teach pqc
cryptavault teach adaptive
cryptavault teach streaming
cryptavault teach storage
cryptavault teach sharing
```

### `cryptavault ai advise <file>`

Runs a local rule-based recommendation over file name, size, and a 512-byte header sample. File contents are not uploaded.

```bash
cryptavault ai advise document.pdf --profile STRONG
```

### `cryptavault ai explain <concept>`

Looks up an offline knowledge-base entry.

```bash
cryptavault ai explain kyber
cryptavault ai explain argon2id
cryptavault ai explain merkle
```

### `cryptavault ai concepts`

Lists all offline concepts.

## Exit codes

Typer commands return `0` on success. Most failures print a Rich error and raise `Typer.Exit(code=1)`. Cryptographic verification failures must be treated as non-zero-equivalent and must not be ignored by scripts.

## Scripting notes

- Use `--passphrase` only in controlled environments; prefer interactive prompts or secret injection.
- Treat stdout as human-readable, not a stable machine format.
- Capture `pipeline-decrypt` failure and stop; never consume partially decrypted output.
- The keystore and recovery bundle are sensitive even though the keystore is encrypted. Protect file permissions.
- Use `.venv/bin/...` when packaging or automation requires a stable interpreter.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `OqsNotAvailableError` | Native liboqs missing | Install liboqs or skip PQ-dependent commands |
| `Incorrect passphrase` | Wrong key or corrupted envelope | Retry; no reset exists |
| `Invalid vault container` | Wrong file or unsupported magic | Confirm `CVV2`/`CVV1` input |
| `Merkle root mismatch` | Tampering, reordering, or truncation | Discard the container |
| `Container is not signed` on verify | Signature required but absent | Use the signed artifact or omit verification |
| `storage upload failed` | Missing connector credentials | Configure the connector or use `local://` |
| `SharePackage` signature invalid | Package modified | Regenerate the share |
