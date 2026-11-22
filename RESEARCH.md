# CryptaVault — Research Deliverables

## Number Theory & Cryptography Research Topics

Each topic below gets an **annotated reference implementation** under `research/notes/` plus a **1-2 page written note**. These support the final report's academic rigor (Task 16.3).

Each includes:
- **Annotated code**: minimal, readable implementation (NOT for production use — production uses library primitives)
- **Written note**: concept explanation, math derivation, security analysis, performance notes
- **Citations**: NIST FIPS, RFCs, academic papers, official specs

---

### Topic 1: Modular Arithmetic
**Annotated impl**: `research/notes/modular_arithmetic.py`
**Note**: `research/notes/modular_arithmetic.md`

- Operations mod n: addition, subtraction, multiplication, exponentiation.
- Modular inverses via Extended Euclidean Algorithm.
- Chinese Remainder Theorem (CRT) and its role in RSA decryption speedup.
- Euler's totient function φ(n), Fermat's little theorem.

### Topic 2: Prime Generation
**Annotated impl**: `research/notes/prime_generation.py`
**Note**: `research/notes/prime_generation.md`

- Sieve of Eratosthenes (small primes for reference).
- Miller-Rabin primality test with confidence bounds (error probability ≤ 2^-k).
- Safe primes (p = 2q+1) for Diffie-Hellman.
- Tuning loop iterations for production-grade confidence.

### Topic 3: Symmetric Cryptography Overview
**Note**: `research/notes/symmetric_overview.md` (conceptual, no impl)

- Block ciphers: AES structure (SubBytes/S-box, ShiftRows, MixColumns, AddRoundKey).
- Stream ciphers: ChaCha20 quarter-round, 20 rounds, key schedule.
- Modes of operation: ECB (insecure demo), CBC, CTR, GCM (AEAD construction).
- Why AEAD > manual encrypt-then-MAC.

### Topic 4: Asymmetric Cryptography — RSA
**Annotated impl**: `research/notes/rsa_math.py` (512-bit demo — illustration only)
**Note**: `research/notes/rsa_math.md`

- Key generation: p, q primes, n = pq, φ(n), e coprime to φ(n), d = e^-1 mod φ(n).
- Encryption: c = m^e mod n; Decryption: m = c^d mod n (via CRT for speedup).
- OAEP padding: why textbook RSA is insecure; OAEP construction.
- Attacks: timing, padding oracle, low-exponent; mitigations.

### Topic 5: Elliptic Curve Cryptography
**Annotated impl**: `research/notes/ecc_math.py`
**Note**: `research/notes/ecc_math.md`

- Curve arithmetic: point addition (geometric + algebraic), point doubling.
- Curve25519 (Montgomery curve): x-only DH, why Montgomery form.
- Ed25519 (Twisted Edwards curve): unified add/double, no special cases.
- Comparison with Weierstrass curves; why Curve25519 safe against timing attacks.

### Topic 6: Diffie-Hellman Key Exchange
**Annotated impl**: `research/notes/diffie_hellman.py`
**Note**: `research/notes/diffie_hellman.md`

- Classical DH (mod p): g^a mod p, g^b mod p, shared = g^(ab) mod p.
- ECDH on Curve25519.
- Man-in-the-middle vulnerability; how certificates / X25519 in TLS solve it.
- Authenticated DH (SIGMA / HMQV reference).

### Topic 7: Digital Signatures
**Note**: `research/notes/signatures_overview.md`
**Annotated impls**: `research/notes/rsa_pss.py`, `research/notes/ecdsa.py`, `research/notes/ed25519.py`

- RSA-PSS (probabilistic, salted); why PSS over PKCS#1 v1.5.
- ECDSA: per-signature k randomness → why deterministic ECDSA (RFC 6979) matters.
- Ed25519 (EdDSA, deterministic, Ed-key derivation).
- Dilithium (lattice-based Fiat-Shamir with aborts).
- Comparison table: signature size, verification time, security level.

### Topic 8: Hash Functions
**Annotated impl**: `research/notes/hash_constructions.py`
**Note**: `research/notes/hash_constructions.md`

- Merkle-Damgård construction (SHA-2): length extension attack, why HMAC mitigates.
- Sponge construction (SHA-3/Keccak): capacity, rate, absorb/squeeze.
- BLAKE3 tree mode: parallelizable, keyed hashing, XOF.
- Pre-image, second-preimage, collision resistance definitions.

### Topic 9: Merkle Trees
**Annotated impl**: `research/notes/merkle.py` (also used in Task 3.4)
**Note**: `research/notes/merkle.md`

- Construction; leaf/intermediate hash functions.
- Inclusion proofs: O(log n) size, O(log n) verification time.
- Tamper detection at any level; proof of non-inclusion.
- Applications: Git, Bitcoin, CryptaVault folder integrity.

### Topic 10: Authenticated Encryption (AEAD)
**Note**: `research/notes/aead.md`

- GCM: counter mode + GHASH (polynomial MAC over GF(2^128)).
- ChaCha20-Poly1305: ChaCha stream + Poly1305 MAC (integer mod p).
- Why AEAD > encrypt-then-MAC glued manually (nonce reuse, ordering, AAD binding).
- Misuse resistance: SIV mode (nonce-misuse-resistant) — reference.

### Topic 11: Post-Quantum Cryptography
**Note**: `research/notes/post_quantum.md`

- Shor's algorithm threat: breaks RSA/ECDH at scale; why lattice-based resists.
- Lattice-based crypto overview: Learning With Errors (LWE), Module-LWE.
- Kyber KEM (FIPS 203): key generation, encapsulation, decapsulation.
- Dilithium signatures (FIPS 204): Fiat-Shamir with aborts.
- NIST PQC standardization: Levels 1/3/5 vs AES-128/192/256 equivalence.
- Why hybrid classical + PQ (transition security: protects against "harvest now, decrypt later" during the migration).

### Topic 12: Key Management
**Note**: `research/notes/key_management.md`

- Hierarchical key derivation: HKDF (extract-then-expand), why salt + info.
- Ratchets: Signal Double Ratchet (DH ratchet + symmetric ratchet); per-message keys.
- Key wrapping: RFC 3394 AES-KW or AES-GCM wrap.
- Key rotation policies; why forward secrecy requires active rotation.
- Threshold key sharing (Shamir's Secret Sharing, future work).

### Topic 13: Compression
**Annotated impl**: `research/notes/compression_overview.py`
**Note**: `research/notes/compression_overview.md`

- Entropy coding: Huffman, arithmetic coding.
- LZ77: sliding window dictionary coding.
- LZMA: larger window + range coding.
- Brotli: LZ77 + context modeling + static dictionary.
- zstd: modern, fast, tunable levels.
- When compression hurts (already-compressed, small files, CPU-bound workloads).

### Topic 14: Secure Software Architecture
**Note**: `research/notes/secure_architecture.md`

- Zero-knowledge architecture: client-side encryption, server only stores ciphertext.
- Threat model: honest-but-curious storage provider; malicious network; compromised server.
- Access control boundaries: master key in keystore, never exported, best-effort memory wipe.
- Least privilege: storage connectors see only ciphertext; API sees only encrypted manifests.

### Topic 15: Secure File Sharing
**Note**: `research/notes/secure_sharing.md`

- Hybrid KEM for multi-recipient shares: one ciphertext + N recipient-wrapped keys.
- Key wrapping per recipient (X25519+Kyber for PQ-secure shares).
- One-time vs time-limited vs password-protected shares; security tradeoffs.
- QR codes for offline / air-gapped sharing (compact key material only).

### Topic 16: Forward Secrecy
**Note**: `research/notes/forward_secrecy.md`

- Session FS (TLS 1.3 ephemeral ECDHE): new DH per session; compromise doesn't reveal past sessions.
- At-rest FS approximation: ratcheted per-file keys; each file uses its own key; ratchet advances.
- Honest limitation: ratchet compromise reveals future keys (not past), but true FS requires session property.
- Signal Double Ratchet as reference design.

---

## Citation Standards

All notes cite sources:

- **NIST FIPS 203** (Kyber KEM standard)
- **NIST FIPS 204** (Dilithium signature standard)
- **NIST FIPS 202** (SHA-3 / Keccak)
- **RFC 5869** (HKDF)
- **RFC 8439** (ChaCha20-Poly1305)
- **RFC 7748** (Curve25519 / Curve448)
- **RFC 8032** (EdDSA — Ed25519/Ed448)
- **RFC 3394** (AES Key Wrap)
- **Signal Double Ratchet paper** (Perrin, Marlinsbury)
- **BLAKE3 spec** (Orr, Aumentado, Hopwood)
- **Original Diffie-Hellman 1976** ("New Directions in Cryptography")
- **liboqs documentation** (open-quantum-safe/liboqs GitHub)
- **Wycheproof test vectors** (Google,揭露 crypto API misuse)
- **Original papers** per algorithm (e.g., Rivest-Shamir-Adleman 1978, Miller-Rabin 1980)

---

_End of RESEARCH.md_