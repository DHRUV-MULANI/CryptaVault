# CryptaVault End-to-End Showcase Demo Guide

This document provides a step-by-step, 100% reproducible demonstration of the CryptaVault system across the **CLI**, the **FastAPI Zero-Knowledge Backend**, the **Web Client (React + WASM)**, and the **Admin Governance Console**.

---

## 1. Quick Service Startup

To showcase the entire distributed ecosystem, open three terminal tabs:

### Terminal 1: FastAPI Zero-Knowledge Backend (Port 8000)
```bash
cd /home/devil/Projects/Collage_project/CryptaVault
.venv/bin/uvicorn cryptavault_api.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live SSE Telemetry**: [http://localhost:8000/api/metrics/stream](http://localhost:8000/api/metrics/stream)

### Terminal 2: Web Client Application (Port 3000)
```bash
cd /home/devil/Projects/Collage_project/CryptaVault/packages/web
npm run dev -- --port 3000
```
- **Web App URL**: [http://localhost:3000](http://localhost:3000)

### Terminal 3: Admin Governance Console (Port 3001)
```bash
cd /home/devil/Projects/Collage_project/CryptaVault/packages/admin
npm run dev -- --port 3001
```
- **Admin Console URL**: [http://localhost:3001](http://localhost:3001)

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

## 3. Web & Admin Showcase Highlights

1. **Web Client (`packages/web`)**:
   - Client-side master key derivation using Argon2id.
   - Live drag-and-drop file encryption with visual chunk progress bar.
   - Interactive 5-tier adaptive security slider (PERFORMANCE to MAXIMUM).
   - Real-time cryptographic security badge displaying classical & post-quantum bits.
   - QR code rendering for one-time timed share links.
   - Educational AI cryptographic assistant drawer.

2. **Admin Console (`packages/admin`)**:
   - RBAC-enforced tenant management with safe admin impersonation and audit trail.
   - Live telemetry dashboard powered by Server-Sent Events (`/api/metrics/stream`).
   - Dynamic runtime feature flag switches (Enable Post-Quantum, Mandatory 2FA, Strict ZK).
   - Cryptographic tamper log inspector.
