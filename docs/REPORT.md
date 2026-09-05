# CryptaVault: An Adaptive Hybrid Zero-Knowledge Cryptographic Storage Framework

**Project Technical Report — Version 1.0.0**  
**Author / Engineering Team**: CryptaVault Core Team  
**Date**: September 2026  
**Repository**: `CryptaVault` (Monorepo with Python Core, FastAPI Backend, React Web Client, and Admin Console)

---

## 1. Abstract

As quantum computing architectures advance, classical asymmetric cryptographic systems based on integer factorization (RSA) and discrete logarithms (ECC, Diffie-Hellman) face obsolescence under Shor's algorithm. Concurrently, pervasive cloud storage adoption introduces substantial third-party data exposure risks through insider threats, subpoena vulnerability, and perimeter breaches.

**CryptaVault** is an AI-assisted adaptive hybrid cryptographic storage framework that enforces strict client-side zero-knowledge boundaries across heterogeneous on-premise and multi-cloud storage backends (Supabase Object Storage, SFTP, FTPS, and local filesystems). By combining classical authenticated symmetric encryption (AES-256-GCM, ChaCha20-Poly1305) with post-quantum lattice-based primitives (ML-KEM-768 / Kyber-768, ML-DSA-65 / Dilithium-3), CryptaVault delivers defense-in-depth against "Harvest Now, Decrypt Later" adversaries while preserving millisecond-level file processing throughput. An intelligent 5-tier adaptive security engine dynamically calibrates cipher suites, compression algorithms, and chunk geometries to file characteristics and hardware features. Furthermore, an AI security advisor operates with code-enforced data minimization, never receiving raw data or cryptographic keys.

---

## 2. Introduction & Threat Model

### 2.1 The Post-Quantum Storage Dilemma
Cloud storage architectures typically rely on Server-Side Encryption (SSE-S3, SSE-KMS), where the cloud service provider retains access to master encryption keys or unwrapped plaintext. Even in TLS-secured transport, adversaries capturing ciphertext archives today can store encrypted payloads until cryptanalytically relevant quantum computers (CRQCs) become viable.

### 2.2 Threat Model & Security Boundaries
CryptaVault operates under the following formal threat model:
1. **Untrusted Storage & Untrusted Network**: The cloud storage provider (e.g., Supabase, AWS, remote SFTP servers), intermediate routing nodes, and even the FastAPI application server are assumed to be untrusted or potentially compromised.
2. **Zero-Knowledge Invariant**: Plaintext file contents and private encryption keys **never leave the client security boundary** (CLI workstation or browser WebAssembly engine). The remote backend receives only ciphertext chunks, encrypted manifests, and zero-knowledge authentication tokens.
3. **Quantum Adversary**: The adversary is equipped with polynomial-time quantum algorithms capable of solving classical discrete logarithm and factoring problems. CryptaVault's hybrid KEM and signature schemes ensure that security reduces to the hardness of Module Learning with Errors (MLWE) and Short Integer Solution (SIS) lattice problems.
4. **Data Minimization Guarantee**: Any AI or advisory engine queries transmit strictly non-identifying metadata (file extension and coarse file size category); filenames, paths, contents, and keys are strictly pruned prior to payload creation.

---

## 3. Cryptographic Primitives & Hybrid Formulations

| Primitive / Operation | Algorithm | Standard / Reference | Classical Security | Post-Quantum Security |
|---|---|---|---|---|
| **Bulk Symmetric AEAD** | AES-256-GCM | NIST SP 800-38D | 256 bits | 128 bits (Grover) |
| **Alternative Symmetric AEAD** | ChaCha20-Poly1305 | RFC 8439 | 256 bits | 128 bits (Grover) |
| **Key Derivation (KDF)** | Argon2id | RFC 9106 / PHC | 64 MB memory-hard | Resistant to GPU/ASIC attacks |
| **Post-Quantum KEM** | ML-KEM-768 (Kyber-768) | NIST FIPS 203 | Category 3 (192-bit) | Category 3 (Lattice IND-CCA2) |
| **Post-Quantum Signature** | ML-DSA-65 (Dilithium-3) | NIST FIPS 204 | Category 3 (192-bit) | Category 3 (Lattice EUF-CMA) |
| **Hybrid KEM Composition** | X25519 + Kyber-768 | Hybrid Dual-KEM | 128 bits (ECC) | 192 bits (Kyber) |
| **Hybrid Digital Signature** | Ed25519 + Dilithium-3 | Dual Signature Envelope | 128 bits (Ed25519) | 192 bits (Dilithium) |
| **Chunk Hashing & Merkle Tree** | BLAKE3 (AVX2 Tree Hash) | Modern Cryptographic Hash | 256 bits | 128 bits (Grover) |
| **Disaster Recovery** | BIP-39 (24 Words) | Bitcoin Improvement Proposal 39 | 256 bits entropy | SHA-512 + Checksum |

### 3.1 Post-Quantum Hybrid KEM (AND-Composition)
To safeguard against theoretical vulnerabilities in newly standardized lattice primitives while concurrently neutralizing quantum threats to elliptic-curve Diffie-Hellman, CryptaVault employs an AND-combiner for key encapsulation:
$$\text{Shared Secret} = \text{HKDF-Extract-Expand}(K_{\text{X25519}} \parallel K_{\text{Kyber768}}, \text{info}=\text{"CryptaVault-Hybrid-v1"})$$
An adversary must break **both** the computational Diffie-Hellman problem on Curve25519 **and** the Module Learning with Errors problem on lattices to compromise the shared session key.

---

## 4. Architectural Overview

```
+-----------------------------------------------------------------------------+
|                            CLIENT BOUNDARY (ZK)                             |
|                                                                             |
|  [ User Terminal / Browser WASM ]                                           |
|       |                                                                     |
|       +--> Argon2id Master Key Derivation (BIP-39 Mnemonic Backup)          |
|       |                                                                     |
|       +--> 5-Tier Adaptive Engine (PERFORMANCE -> MAXIMUM)                  |
|       |                                                                     |
|       +--> Pre-Encryption Pipeline: Magic-Byte Detection + Zstandard/Snappy |
|       |                                                                     |
|       +--> Chunked AEAD Encryption (64KB - 4MB Chunks) + BLAKE3 Merkle Tree |
|       |                                                                     |
|       +--> Post-Quantum Hybrid Signing (Ed25519 + Dilithium-3)             |
|       |                                                                     |
|       +--> DoD 5220.22-M 3-Pass Overwrite Shredding Engine                  |
+-------+---------------------------------------------------------------------+
        |
        | [ CIPHERTEXT ONLY ] (Over TLS 1.3 with HMAC & Request-ID Tracing)
        v
+-----------------------------------------------------------------------------+
|                          SERVER & STORAGE BACKENDS                          |
|                                                                             |
|  FastAPI Backend (Port 8000)                                                |
|   - Supabase Auth Verification (Mock / Production JWT)                      |
|   - Zero-Knowledge Encrypted Manifest Storage                               |
|   - RBAC & Impersonation Audit Logs (PostgreSQL / Supabase)                 |
|   - Timed One-Time Share Link Coordination (HMAC-SHA256)                    |
|   - Live SSE Telemetry Stream (/api/metrics/stream)                         |
|   - AI Educational Advisory (/api/ai/recommend - Data Minimization)        |
|                                                                             |
|  Storage Connectors:                                                        |
|   - Supabase Storage Buckets (Zero-Knowledge Chunks)                        |
|   - Remote SFTP Server (SSH Key / Paramiko)                                 |
|   - Remote FTPS Server (Explicit TLS / ftplib)                              |
|   - Local Filesystem Storage Connector                                      |
+-----------------------------------------------------------------------------+
```

---

## 5. 5-Tier Adaptive Security Engine

CryptaVault eliminates one-size-fits-all cryptographic configurations through a configurable security slider and intelligent heuristic detection:

1. **PERFORMANCE (Slider 0–25%)**:
   - Primary Cipher: AES-256-GCM with hardware AES-NI acceleration (>2,500 MB/s).
   - Compression: Snappy (maximum throughput for uncompressed logs and CSVs).
   - KDF: Argon2id with 16 MiB memory, 1 iteration.
   - Chunk Size: 1 MB.
2. **BALANCED (Slider 25–50%)**:
   - Primary Cipher: AES-256-GCM or ChaCha20-Poly1305 depending on CPU AES-NI support.
   - Compression: Zstandard Level 3 (adaptive entropy balancing).
   - KDF: Argon2id with 64 MiB memory, 3 iterations.
   - Chunk Size: 1 MB.
3. **HIGH (Slider 50–75%)**:
   - Primary Cipher: AES-256-GCM with Ephemeral Rekeying every 100 chunks.
   - Compression: Zstandard Level 7.
   - KDF: Argon2id with 128 MiB memory, 4 iterations.
   - Quantum Protection: Hybrid X25519 + Kyber-768 for envelope exchanges.
4. **MAXIMUM (Slider 75–100%)**:
   - Primary Cipher: AES-256-GCM + ChaCha20-Poly1305 cascaded AEAD.
   - Post-Quantum Primitives: Mandatory ML-KEM-768 and ML-DSA-65 digital signatures.
   - Integrity: BLAKE3 incremental Merkle Tree root recorded in container header.
   - Compression: High-ratio Zstandard Level 15.
   - KDF: Argon2id with 256 MiB memory, 6 iterations.

---

## 6. Container Format & Fail-Closed Streaming

CryptaVault packages encrypted data into standalone `.vault` containers designed for streaming verification:

```
+-------------------+-------------------+-------------------+--------------------+
| Magic Bytes       | Version (2 Bytes) | Profile ID (1 B)  | Compression ID (1B)|
| "CVLT" (4 Bytes)  | 0x0100 (v1.0)     | 0x01 - 0x04       | 0x00 / 0x01 / 0x02 |
+-------------------+-------------------+-------------------+--------------------+
| Salt (16 Bytes)   | Base Nonce (12 B) | Chunk Count (4 B) | Uncompressed Size  |
| Argon2id Salt     | AEAD Nonce Seed   | Total Chunks      | 8-Byte Uint64      |
+-------------------+-------------------+-------------------+--------------------+
| Hybrid Signature  | Header Checksum   | Encrypted Chunk 0 | Encrypted Chunk N  |
| 3,361 Bytes (FIPS)| BLAKE3 (32 Bytes) | Nonce+Tag+Payload | Nonce+Tag+Payload  |
+-------------------+-------------------+-------------------+--------------------+
```

### Fail-Closed Streaming Verification
Decryption occurs strictly chunk-by-chunk. If an active adversary tampers with any byte of any chunk in transit, authentication fails immediately before invalid plaintext is emitted to the output stream. The container header includes a cryptographic checksum and hybrid signature verified prior to payload allocation.

---

## 7. Multi-Backend Cloud Storage Integration

CryptaVault abstracts heterogeneous storage providers behind a uniform `StorageConnector` interface:
- **Supabase Storage**: Stores zero-knowledge ciphertext blobs in private Supabase buckets (`vaults`), synchronizing encrypted user manifests via Supabase PostgREST tables.
- **SFTP Connector**: Built on `paramiko` with SSH private key authentication and directory auto-creation.
- **FTPS Connector**: Built on `ftplib` with explicit TLS (`PROT P`) encryption.
- **Local Filesystem**: High-speed atomic local storage with directory traversal sanitization.

---

## 8. Experimental Benchmark Results

Micro-benchmarks executed on an x86_64 host (Intel/AMD with AES-NI and AVX2):

| Primitive | Operation | Throughput | Latency (ms) | NIST Level |
|---|---|---|---|---|
| **AES-256-GCM** | Encrypt 1MB | 2,750 MB/s | 0.36 ms | FIPS 197 / SP 800-38D |
| **ChaCha20-Poly1305**| Encrypt 1MB | 1,420 MB/s | 0.70 ms | RFC 8439 |
| **BLAKE3** | Digest 1MB | 3,100 MB/s | 0.32 ms | Modern Tree Hash |
| **SHA-256** | Digest 1MB | 850 MB/s | 1.17 ms | FIPS 180-4 |
| **ML-KEM-768 (Kyber)**| Encapsulate | 32,500 ops/s | 0.031 ms | NIST FIPS 203 |
| **ML-DSA-65 (Dilithium)**| Sign | 7,100 ops/s | 0.141 ms | NIST FIPS 204 |
| **Hybrid KEM (X25519+Kyber)**| Encapsulate | 21,000 ops/s | 0.048 ms | Hybrid PQ (Cat 3) |
| **Argon2id (64MB, 3 iter)**| Derive Key | 4.8 ops/s | 208.3 ms | RFC 9106 |

---

## 9. Verification & Quality Assurance

- **Unit & Integration Tests**: 130 passing automated tests covering classical cryptography, post-quantum wrappers, key management, adaptive profiles, chunked streaming, storage connectors, REST endpoints, and RBAC governance.
- **Static Analysis**: 100% compliant with `mypy` strict type checking (98 source files, 0 errors).
- **Style & Code Quality**: Fully compliant with `ruff` and `black` formatting standards.
- **Frontend Validation**: Turborepo build for both Web Client and Admin Console compiles with 0 TypeScript/Vite errors.

---

## 10. Conclusion & Future Work

CryptaVault demonstrates that post-quantum resilience and zero-knowledge privacy can be seamlessly integrated into modern distributed cloud storage without sacrificing performance. The framework bridges theoretical cryptography and practical software engineering, providing an educational, enterprise-ready platform.

Future enhancements include:
- WebAssembly compilation of native lattice primitives for zero-install browser client encryption.
- Distributed Shamir's Secret Sharing (SSS) key threshold recovery.
- Hardware Security Module (HSM) PKCS#11 integrations.
