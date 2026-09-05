# Hybrid Digital Signatures (Ed25519 + Dilithium3)

## 1. Motivation & Integrity Threat Model
Digital signatures protect audit log integrity, key manifest authenticity, and zero-knowledge ownership proofs. If an adversary could forge signatures:
1. They could alter key manifests without client consent.
2. They could inject malicious encrypted shares or modify audit trails.

To guard against both classical forgery and quantum attacks (Shor's algorithm breaking discrete logarithms on Ed25519), CryptaVault implements **AND-Composition Hybrid Signatures**:
$$\text{Verify}_{Hybrid}(M, \Sigma) = \text{Verify}_{Ed25519}(M, \sigma_{Ed25519}) \land \text{Verify}_{Dilithium3}(M, \sigma_{Dilithium3})$$

---

## 2. Construction Protocol

### 2.1 Key Generation
$$\text{Gen}() \to (PK, SK)$$
- $PK = (PK_{Ed25519}, PK_{Dilithium3})$
- $SK = (SK_{Ed25519}, SK_{Dilithium3})$

### 2.2 Signing
$$\text{Sign}(SK, M) \to \Sigma$$
1. $\sigma_{Ed25519} \leftarrow \mathcal{S}_{Ed25519}.\text{Sign}(SK_{Ed25519}, M)$
2. $\sigma_{Dilithium3} \leftarrow \mathcal{S}_{Dilithium3}.\text{Sign}(SK_{Dilithium3}, M)$
3. $\Sigma = \text{WireEncode}(\sigma_{Ed25519}, \sigma_{Dilithium3})$

### 2.3 Verification
$$\text{Verify}(PK, M, \Sigma) \to \{0, 1\}$$
1. $(\sigma_{Ed25519}, \sigma_{Dilithium3}) \leftarrow \text{WireDecode}(\Sigma)$
2. $b_{classical} = \mathcal{S}_{Ed25519}.\text{Verify}(PK_{Ed25519}, M, \sigma_{Ed25519})$
3. If $b_{classical} \neq 1$, return $0$ (Fail-Closed).
4. $b_{pq} = \mathcal{S}_{Dilithium3}.\text{Verify}(PK_{Dilithium3}, M, \sigma_{Dilithium3})$
5. Return $b_{classical} \land b_{pq}$.

---

## 3. Security Properties (EUF-CMA)
Under the standard model:
- The composite signature achieves **Existential Unforgeability under Chosen Message Attacks (EUF-CMA)** as long as **either** Ed25519 or Dilithium3 remains EUF-CMA secure.
- For an adversary to forge a valid $\Sigma$, they must simultaneously forge $\sigma_{Ed25519}$ AND $\sigma_{Dilithium3}$ on the same message $M$.
- Breaking Ed25519 with a quantum computer does not permit forging $\sigma_{Dilithium3}$, preserving complete tamper-resistance.
