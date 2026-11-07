# CryptaVault End-to-End Showcase Demo Guide

This document provides a reproducible demonstration across the **CLI**, the **zero-knowledge web portal**, and the optional **FastAPI backend**. The deployed portal uses native Web Crypto, not WASM.

---

## 1. Quick Service Startup

To showcase the entire distributed ecosystem, open three terminal tabs:

### Terminal 1: FastAPI Zero-Knowledge Backend (Port 8000)
```bash
.venv/bin/uvicorn cryptavault_api.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live SSE Telemetry**: [http://localhost:8000/api/metrics/stream](http://localhost:8000/api/metrics/stream)

### Terminal 2: Web Portal (Port 5173)
```bash
pnpm --filter @cryptavault/web dev
```
- **Portal URL**: the printed Vite URL, usually [http://localhost:5173](http://localhost:5173)

### Optional Terminal 3: Standalone Admin Scaffold (Port 3001)
```bash
pnpm --filter @cryptavault/admin dev -- --port 3001
```
- **Admin scaffold URL**: [http://localhost:3001](http://localhost:3001)
- The deployed admin experience is the in-portal `#/admin` route, which operates on the local browser vault.

---

## 2. Walkthrough Demonstration Steps

### Step 1: System Hardware & Zero-Knowledge Verification
Verify that CPU hardware acceleration (AES-NI, AVX2), post-quantum primitives (`liboqs`), and zero-knowledge bounds are active:
```bash
.venv/bin/cryptavault status
```

### Step 2: Key Generation & Disaster Recovery (BIP-39)
Generate a 256-bit Master Key protected with Argon2id and backed up via a 24-word BIP-39 mnemonic phrase:
```bash
.venv/bin/cryptavault keygen --output demo.keystore --passphrase "demo-passphrase-2026"
```
Inspect the keystore envelope metadata (showing public key fingerprints and zero plaintext exposure):
```bash
.venv/bin/cryptavault inspect-keystore --keystore demo.keystore --passphrase "demo-passphrase-2026"
```

### Step 3: Adaptive Streaming Pipeline Encryption
Create a test file and process it through the full streaming pipeline (Zstandard compression + chunked AEAD + BLAKE3 Merkle Tree + Dilithium-3 lattice signature):
```bash
echo "CryptaVault confidential demo data with high entropy and post-quantum security guarantees." > sample.txt
.venv/bin/cryptavault pipeline-encrypt sample.txt --output sample.vault --profile MAXIMUM --passphrase "demo-passphrase-2026"
```
Decrypt and verify the container header and chunk authentication tags:
```bash
.venv/bin/cryptavault pipeline-decrypt sample.vault --output sample_restored.txt --profile MAXIMUM --passphrase "demo-passphrase-2026"
diff -s sample.txt sample_restored.txt
```

### Step 4: Post-Quantum Signatures (NIST FIPS 204)
Sign the original artifact using Post-Quantum Hybrid Signatures (Ed25519 + Dilithium-3):
```bash
.venv/bin/cryptavault sign sample.txt --output-sig sample.sig
```

### Step 5: AI-Assisted Security Advisory
Demonstrate the code-enforced data-minimization advisory engine (only non-identifying file extension and size are evaluated; zero keys or plaintext are transmitted):
```bash
.venv/bin/cryptavault ai advise sample.txt
.venv/bin/cryptavault ai explain "ML-KEM-768"
.venv/bin/cryptavault ai explain "argon2id"
```

### Step 6: Live Benchmark Lab
Execute the cross-primitive micro-benchmark suite measuring throughput, latency, key sizes, and NIST security levels:
```bash
.venv/bin/cryptavault benchmark
```

### Step 7: Cryptographic Shredding (DoD 5220.22-M)
Permanently destroy the decrypted sample file using 3-pass overwrite sanitization:
```bash
.venv/bin/cryptavault shred sample_restored.txt --passes 3
```

---

## 3. Web Portal Showcase

1. Open the portal and create a local vault with a passphrase of at least 10 characters.
2. Upload a file from **Vault**. The browser compresses when useful, splits into chunks, encrypts each chunk with AES-256-GCM, seals the manifest, and stores ciphertext in IndexedDB.
3. Open **Catalog** to inspect all 88 algorithms, stable wire IDs, lifecycle gates, and the six profiles from `PERFORMANCE` through `PQ_STRONG` to `MAXIMUM`.
4. Create a share from the file row. Open the generated link in a private window; the share viewer decrypts without an account or API.
5. Use **Messages** for local encrypted notes, **Status** to run the browser crypto self-test, **Settings** to rotate the passphrase or export an encrypted backup, and **Admin** for local policy flags and audit export.
6. Open **Academy** for an implementation-aligned explanation of the zero-knowledge boundary, crypto agility, container framing, and deployment limits.

The static portal uses PBKDF2-SHA256 for the vault-level KDF, not Argon2id. The Python engine uses Argon2id. See [portal.md](portal.md) and [security_model.md](security_model.md).
