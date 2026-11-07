# Container Formats

CryptaVault has two independent container families:

| Format | Owner | Purpose |
|---|---|---|
| `CVV2` + `CVT1` | Python core pipeline | Crypto-agile, signed, Merkle-backed vault artifacts |
| `CVV1` | Python legacy reader | Compatibility with earlier artifacts |
| `CVW1` | Browser portal | JSON payload used by the static portal and share bundles |

They are not interchangeable. A browser `CVW1` container cannot be opened by `pipeline-decrypt`, and a core `CVV2` artifact is not imported by the portal today.

## Core container: `CVV2`

A core container is:

```text
CVV2 header-frame  ||  chunk 0  ||  chunk 1  || ... ||  CVT1 trailer-frame
```

### Header frame

```text
magic            4 bytes   ASCII "CVV2"
payload length   4 bytes   big-endian uint32
payload          N bytes   UTF-8 JSON object, keys sorted, compact separators
```

The JSON header contains:

| Field | Type | Meaning |
|---|---|---|
| `version` | integer | Must be `2` |
| `file_id` | string | Logical file identity, also bound into chunk AAD |
| `profile` | string | Profile level used at creation |
| `compression` | string or null | `zstd`, `brotli`, or other selected algorithm; null when skipped |
| `chunk_size_bytes` | integer | Positive chunk size |
| `multi_layer` | boolean | Whether cascade AEAD was used |
| `algorithms` | object | Required bindings for `symmetric`, `hash`, `signature`, `kem`, `kdf` |

Each algorithm binding is:

```json
{
  "family": "symmetric",
  "algorithm_id": "aes-256-gcm",
  "wire_id": 257
}
```

Validation rules:

- Header version must be exactly `2`.
- All five required families must be present.
- Wire IDs must be unique inside the header.
- Chunk size must be positive.
- Metadata frame must be non-empty and at most 1 MiB.
- JSON must parse to an object.

### Chunk records

Each chunk is:

```text
index             8 bytes   big-endian uint64
is_final          1 byte    boolean
nonce            12 bytes   AEAD nonce
payload length    4 bytes   big-endian uint32
ciphertext+tag    N bytes   AEAD ciphertext with authentication tag
```

Total chunk header: 25 bytes.

Associated data is:

```text
cryptavault:chunk:<file_id>:<chunk_index>:<is_final>
```

This binds each chunk to the file and its position. Decryption checks:

1. Chunk indices are contiguous and start at 0.
2. The AEAD tag verifies with the expected AAD.
3. The stream ends with a chunk marked final.
4. No chunk appears after the final marker.

Any failure aborts the operation. Plaintext from earlier chunks may already have been written to the output stream; callers that need all-or-nothing behavior should decrypt to a temporary buffer or file and only publish it after full verification.

### Trailer frame

```text
magic            4 bytes   ASCII "CVT1"
payload length   4 bytes   big-endian uint32
payload          N bytes   UTF-8 JSON object
```

Fields:

| Field | Type | Meaning |
|---|---|---|
| `chunk_count` | integer | Number of chunk records |
| `merkle_root_hex` | hex string | Root over per-chunk hashes |
| `signature_hex` | hex string | Optional signature over header digest and Merkle root |

A missing trailer, truncated frame, invalid hex, or mismatched chunk count is an integrity failure.

### Integrity and signature flow

Encryption:

1. Compress the payload if the policy says it is worthwhile.
2. Resolve the profile and pipeline configuration.
3. Write the header with exact algorithm bindings.
4. For each serialized chunk, hash it with the selected hash and collect leaves.
5. Build a Merkle tree over the chunk hashes.
6. Optionally sign `SIGNATURE_CONTEXT || hash(header_frame) || merkle_root`.
7. Write the trailer.

Decryption:

1. Parse the header and re-encode it deterministically.
2. Resolve and validate every binding through the catalog.
3. Decrypt chunks and hash each serialized chunk.
4. Read the trailer.
5. Compare chunk count and Merkle root with a constant-time comparison.
6. If a verification key was supplied, require and verify the signature.
7. Decompress after successful authentication.

`SIGNATURE_CONTEXT` is `cryptavault:container:v2:`.

### Legacy `CVV1`

`pipeline-decrypt` recognizes `CVV1` and routes through a legacy reader. It does not write new `CVV1` containers. New work always produces `CVV2`.

### Current memory behavior

The chunk encryptor and decryptor are incremental, but `PipelineOrchestrator.run_encryption` reads the entire input before compression, and `run_decryption` decrypts into an in-memory buffer before decompressing. The container format is streaming-friendly; the current orchestration layer is not yet bounded-memory. This is documented explicitly to avoid overstating the implementation.

## Browser portal container: `CVW1`

The static portal stores a JSON object:

| Field | Type | Meaning |
|---|---|---|
| `magic` | `"CVW1"` | Format discriminator |
| `v` | `1` | Version |
| `fileId` | string | File identity |
| `createdAt` | ISO string | Creation time |
| `profile` | string | One of the six profile levels |
| `compression` | `"none"` or `"gzip"` | Compression applied before chunking |
| `chunkSize` | integer | Chunk size in bytes |
| `chunks` | array | Chunk records |

Each chunk record:

| Field | Type | Meaning |
|---|---|---|
| `i` | integer | Chunk index |
| `f` | 0 or 1 | Final-chunk flag |
| `iv` | base64 | AES-GCM nonce |
| `ct` | base64 | Ciphertext and tag |

The portal binds associated data as `cryptavault:web:<fileId>:<index>:<final>`. It decrypts chunks in order, requires the final marker, and releases plaintext only after the full container opens successfully.

### Portal sealing layers

| Record | Key | AAD |
|---|---|---|
| Vault verifier | master key | `vault:verifier` |
| File manifest | master key | `filemeta:<fileId>` |
| File key | master key | `filekey:<fileId>` |
| File chunks | per-file key | `cryptavault:web:<fileId>:<index>:<final>` |
| Thread label | master key | `thread:<threadId>` |
| Message body | per-message key | `message:<messageId>` |
| Message key | master key | `messagekey:<messageId>` |
| Share payload | share key | `share:payload` |

All sealed records use the form `{ ivB64, ctB64 }`.

## Share bundle: `.cvshare.json`

A portal share bundle is JSON with a discriminator and the same payload shape used by link shares:

```json
{
  "kind": "cryptavault-share-bundle",
  "version": 1,
  "payload": { "...": "..." },
  "shareKeyB64": "..."
}
```

The bundle is for files whose self-contained URL would exceed the practical link size. The recipient opens it in the share viewer, which stores it temporarily in `sessionStorage` and decrypts in the tab.

If the share was passphrase-protected, the payload records `kdf: "pbkdf2"` plus a salt and iteration count, and the share key is wrapped with the passphrase-derived key. Otherwise the share key travels directly in the URL fragment or bundle.

## Compatibility rules

- Never reuse a wire ID for a different algorithm.
- Never reorder or rewrite header fields without a version bump.
- Never accept a chunk sequence with a gap, duplicate, or post-final record.
- Never decrypt with a profile name alone; the header is authoritative.
- Never trust an algorithm name without resolving it through the catalog.
- Never treat a static share revoke as revocation of an already-copied capability URL.
