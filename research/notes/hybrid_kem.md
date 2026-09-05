# Hybrid Key Encapsulation Mechanism (X25519 + Kyber768)

## 1. Threat Model: "Harvest Now, Decrypt Later" (HNDL)
Adversaries currently intercept and store encrypted data transmissions from classical public-key infrastructures. When cryptanalytically relevant quantum computers (CRQCs) become operational, stored classical ciphertexts (RSA, ECDH) can be retroactively decrypted using Shor's algorithm.

CryptaVault mitigates this via **Hybrid Cryptographic Key Encapsulation**, combining:
1. **Classical Asymmetric Hardness**: Elliptic Curve Diffie-Hellman on Curve25519 (X25519), resisting classical adversaries.
2. **Post-Quantum Hardness**: Module Learning With Errors (MLWE) via NIST FIPS 203 (ML-KEM-768 / CRYSTALS-Kyber), resisting both classical and quantum attacks.

---

## 2. Construction & Composition Protocol

Let $\mathcal{K}_{ECDH}$ be the classical X25519 KEM and $\mathcal{K}_{PQ}$ be the post-quantum ML-KEM-768 scheme.

### 2.1 Key Generation
$$\text{Gen}() \to (PK, SK)$$
- $PK = (PK_{ECDH}, PK_{PQ})$
- $SK = (SK_{ECDH}, SK_{PQ})$

### 2.2 Dual Encapsulation
$$\text{Encap}(PK) \to (K_{shared}, CT)$$
1. $(K_{ECDH}, CT_{ECDH}) \leftarrow \mathcal{K}_{ECDH}.\text{Encap}(PK_{ECDH})$
2. $(K_{PQ}, CT_{PQ}) \leftarrow \mathcal{K}_{PQ}.\text{Encap}(PK_{PQ})$
3. $IKM = K_{ECDH} \mathbin{\Vert} K_{PQ}$
4. $Salt = CT_{ECDH} \mathbin{\Vert} CT_{PQ}$
5. $K_{shared} = \text{HKDF-Extract-and-Expand}(Salt, IKM, \text{"cryptavault:hybrid-kem-pq:v1"}, 32)$
6. $CT = (CT_{ECDH}, CT_{PQ})$

### 2.3 Dual Decapsulation
$$\text{Decap}(SK, CT) \to K_{shared}$$
1. $K_{ECDH} \leftarrow \mathcal{K}_{ECDH}.\text{Decap}(SK_{ECDH}, CT_{ECDH})$
2. $K_{PQ} \leftarrow \mathcal{K}_{PQ}.\text{Decap}(SK_{PQ}, CT_{PQ})$
3. $IKM = K_{ECDH} \mathbin{\Vert} K_{PQ}$
4. $Salt = CT_{ECDH} \mathbin{\Vert} CT_{PQ}$
5. $K_{shared} = \text{HKDF-Extract-and-Expand}(Salt, IKM, \text{"cryptavault:hybrid-kem-pq:v1"}, 32)$

---

## 3. Security Analysis (IND-CCA2 Combiner)
By the Giacon et al. (2018) and Bindel et al. (2019) KEM combiner theorems, concatenating shared secrets into a dual-PRF extract-and-expand KDF (such as HKDF-SHA256) yields an **IND-CCA2 secure hybrid KEM** as long as **at least one** of the constituent KEMs remains IND-CCA2 secure.

- If a quantum computer breaks discrete logarithms on Curve25519, Kyber768 preserves IND-CCA2 confidentiality.
- If an unexpected structural attack weakens lattice-based MLWE, X25519 preserves 128-bit classical security.
- The ciphertext binding salt ($CT_{ECDH} \mathbin{\Vert} CT_{PQ}$) prevents cross-protocol substitution and replay attacks.
