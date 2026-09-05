# CryptaVault CLI Reference

CryptaVault provides a high-performance command-line interface built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/). All cryptographic operations, key derivations, and chunk encryptions happen locally on the client machine before any ciphertext touches remote storage targets.

---

## Global Options

```bash
cryptavault --help
```

---

## Command Overview

| Command | Category | Description |
|---|---|---|
| `cryptavault status` | Diagnostics | Display CPU hardware acceleration (AES-NI, AVX2), `liboqs` status, and Zero-Knowledge bounds. |
| `cryptavault version` | Info | Print production release version and build details. |
| `cryptavault profiles` | Profiles | Display all 5 adaptive security tiers with primitive compositions. |
| `cryptavault profile list` | Profiles | List security presets and slider value mappings (0.0 to 100.0%). |
| `cryptavault profile set` | Profiles | Change active default profile by percentage slider. |
| `cryptavault profile get` | Profiles | View currently active security profile. |
| `cryptavault benchmark` | Performance | Execute live micro-benchmarks across AES-NI, ChaCha20, BLAKE3, Kyber-768, Dilithium-3, and Argon2id. |
| `cryptavault keygen` | Key Management | Generate a 256-bit Master Key with a BIP-39 24-word recovery phrase and encrypted keystore. |
| `cryptavault inspect-keystore` | Key Management | Inspect encrypted keystore envelope metadata and public key fingerprints. |
| `cryptavault recover-key` | Key Management | Reconstruct Master Key from a 24-word BIP-39 recovery phrase. |
| `cryptavault encrypt` | Core Crypto | Encrypt a file or string using adaptive authenticated encryption (AES-256-GCM / ChaCha20-Poly1305). |
| `cryptavault decrypt` | Core Crypto | Decrypt an encrypted envelope with authenticated tag verification. |
| `cryptavault pipeline-encrypt` | Streaming Pipeline | Full pipeline: entropy compression (zstd), chunked AEAD, Merkle tree root, and Dilithium-3 signature into a `.vault` container. |
| `cryptavault pipeline-decrypt` | Streaming Pipeline | Streaming decompression and fail-closed chunk tag verification. |
| `cryptavault shred` | Secure Deletion | Permanently sanitize a file using DoD 5220.22-M 3-pass overwrite before unlinking. |
| `cryptavault sign` | PQ Signatures | Sign a file using Post-Quantum Hybrid Signatures (Ed25519 + Dilithium-3 / FIPS 204). |
| `cryptavault verify` | PQ Signatures | Verify integrity and authenticity against a post-quantum hybrid signature. |
| `cryptavault merkle` | Integrity | Compute BLAKE3 Merkle Tree root hash and audit proof for all files in a directory. |
| `cryptavault storage ...` | Multi-Backend | Sync, upload, download, and list across Local, Supabase, SFTP, FTP, and Cloud targets. |
| `cryptavault share ...` | Zero-Knowledge Sharing | Generate HMAC one-time access links, timed share links, wrapped passphrases, and QR codes. |
| `cryptavault ai advise` | AI Advisory | Analyze file metadata (extension, size) and recommend optimal compression & crypto profiles with code-enforced data minimization. |
| `cryptavault ai explain` | AI Advisory | Query the offline cryptographic knowledge base for primitive specifications and NIST standards. |
| `cryptavault ai concepts` | AI Advisory | List all available cryptographic concepts in the curated knowledge base. |

---

## Detailed Command Examples

### 1. Hardware Status & Diagnostics
```bash
cryptavault status
```
Outputs CPU capabilities (`AES-NI`, `AVX2`), native `liboqs` bindings, and zero-knowledge storage verification guarantees.

### 2. Key Generation & Disaster Recovery
```bash
# Generate a new master key and BIP-39 mnemonic
cryptavault keygen --output vault.keystore --passphrase "my-secure-passphrase"

# Inspect keystore fingerprints without exposing keys
cryptavault inspect-keystore --keystore vault.keystore --passphrase "my-secure-passphrase"

# Recover key from BIP-39 seed phrase
cryptavault recover-key "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
```

### 3. File & Streaming Encryption
```bash
# Encrypt with BALANCED profile (AES-256-GCM + Argon2id)
cryptavault encrypt --input document.pdf --output document.pdf.enc --profile BALANCED

# Decrypt
cryptavault decrypt --input document.pdf.enc --output document.pdf

# Full streaming pipeline with Zstandard compression and chunked AEAD
cryptavault pipeline-encrypt large_dataset.csv --output dataset.vault --profile MAXIMUM
cryptavault pipeline-decrypt dataset.vault --output dataset_restored.csv --profile MAXIMUM
```

### 4. Post-Quantum Signatures & Directory Integrity
```bash
# Generate dual classical + lattice signature (FIPS 204)
cryptavault sign release.tar.gz --output-sig release.sig

# Verify signature
cryptavault verify release.tar.gz --sig release.sig --pubkey release.pub

# Compute directory Merkle Tree root with BLAKE3
cryptavault merkle --dir ./data
```

### 5. Multi-Backend Cloud Storage
```bash
# Upload to Supabase Storage bucket (zero-knowledge ciphertext only)
cryptavault storage upload --source document.vault --backend supabase --remote-path /vaults/doc1.vault

# Upload to SFTP server
cryptavault storage upload --source backup.vault --backend sftp --remote-path /backups/backup.vault
```

### 6. Zero-Knowledge Sharing & QR Codes
```bash
# Create a 24-hour timed share link with QR code
cryptavault share create --file-id "file-uuid-123" --expiry-hours 24 --qr

# Wrap a symmetric file key for a recipient with a shared password
cryptavault share wrap-password --file-key-hex "0123...cdef" --password "one-time-secret"
```

### 7. AI Security Advisory
```bash
# Get intelligent recommendations with code-level data minimization
cryptavault ai advise financial_records.xlsx

# Query cryptographic concept
cryptavault ai explain "ML-KEM-768"
cryptavault ai explain "argon2id"
```
