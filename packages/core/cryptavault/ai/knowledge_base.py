"""Cryptographic Knowledge Base for CryptaVault.

Provides authoritative, offline explanations of cryptographic primitives,
zero-knowledge storage models, and post-quantum transitions.
"""

from __future__ import annotations

from typing import Any

CONCEPTS: dict[str, dict[str, Any]] = {
    "aes-256-gcm": {
        "name": "AES-256-GCM",
        "category": "Symmetric AEAD",
        "description": "Advanced Encryption Standard in Galois/Counter Mode with 256-bit keys and 128-bit authentication tag.",
        "security_level": "256 bits classical / 128 bits post-quantum (Grover)",
        "hardware_acceleration": "Intel/AMD AES-NI & ARMv8 Cryptographic Extensions (>2,000 MB/s)",
        "when_to_use": "Standard default cipher for high-throughput bulk data encryption.",
        "nist_standard": "NIST SP 800-38D",
    },
    "chacha20-poly1305": {
        "name": "ChaCha20-Poly1305",
        "category": "Symmetric AEAD",
        "description": "Stream cipher combined with Poly1305 authenticator designed by Daniel J. Bernstein.",
        "security_level": "256 bits classical / 128 bits post-quantum",
        "hardware_acceleration": "Constant-time in software; immune to cache-timing side-channel attacks.",
        "when_to_use": "Systems without dedicated AES-NI hardware or when side-channel resistance is required.",
        "nist_standard": "RFC 8439",
    },
    "argon2id": {
        "name": "Argon2id",
        "category": "Key Derivation Function (KDF)",
        "description": "Memory-hard password hashing function winning the Password Hashing Competition.",
        "security_level": "Tunable memory cost (e.g. 64 MiB), time cost, and parallelism.",
        "hardware_acceleration": "Memory-bound; highly resistant to GPU/ASIC brute-force attacks.",
        "when_to_use": "Deriving master encryption keys from user passphrases and BIP-39 mnemonics.",
        "nist_standard": "RFC 9106",
    },
    "kyber-768": {
        "name": "ML-KEM-768 (Kyber-768)",
        "category": "Post-Quantum KEM",
        "description": "Module Learning with Errors (MLWE) lattice-based Key Encapsulation Mechanism.",
        "security_level": "NIST Security Category 3 (equivalent to AES-192).",
        "hardware_acceleration": "AVX2 NTT polynomial multiplication (~0.029 ms encapsulation).",
        "when_to_use": "Quantum-resistant key encapsulation guarding against 'Harvest Now, Decrypt Later'.",
        "nist_standard": "NIST FIPS 203",
    },
    "dilithium-3": {
        "name": "ML-DSA-65 (Dilithium-3)",
        "category": "Post-Quantum Digital Signature",
        "description": "Module-Lattice-Based Digital Signature Algorithm based on the hardness of lattice problems.",
        "security_level": "NIST Security Category 3 (equivalent to AES-192).",
        "hardware_acceleration": "Fast NTT polynomial arithmetic (~0.14 ms signature generation).",
        "when_to_use": "Digital authentication of manifests and audit logs resistant to Shor's algorithm.",
        "nist_standard": "NIST FIPS 204",
    },
    "hybrid-encryption": {
        "name": "Post-Quantum Hybrid Cryptography",
        "category": "Architecture",
        "description": "AND-composition of classical algorithms (X25519, Ed25519) with post-quantum lattice primitives (Kyber-768, Dilithium-3).",
        "security_level": "Preserves confidentiality as long as EITHER classical or lattice mathematics remains unbroken.",
        "when_to_use": "Long-term archive storage and maximum compliance transitions.",
        "nist_standard": "NIST SP 800-227 / RFC 9580",
    },
    "blake3": {
        "name": "BLAKE3 Cryptographic Hash",
        "category": "Hash Function",
        "description": "High-performance cryptographic tree hash based on Bao and BLAKE2.",
        "security_level": "128 bits collision resistance / 256 bits preimage resistance.",
        "hardware_acceleration": "Multi-threaded SIMD tree hashing (>3,400 MB/s).",
        "when_to_use": "Per-chunk hashing, Merkle tree construction, and deduplication.",
        "nist_standard": "BLAKE3 Specification (2020)",
    },
    "merkle-tree": {
        "name": "Merkle Tree Audit Proofs",
        "category": "Integrity",
        "description": "Binary hash tree enabling O(log n) cryptographic proofs of inclusion and tamper detection.",
        "security_level": "Collision-resistant root binding all file chunks or folder entries.",
        "when_to_use": "Verifying multi-chunk file integrity and folder synchronization audit logs.",
        "nist_standard": "RFC 6962",
    },
    "forward-secrecy": {
        "name": "Forward Secrecy Key Ratchet",
        "category": "Key Management",
        "description": "One-way key derivation ratchet generating ephemeral keys per file/chunk.",
        "security_level": "Compromise of the current key does not expose past ciphertext blocks.",
        "when_to_use": "Maximum security profile and long-lived cloud vault deployments.",
        "nist_standard": "Double Ratchet Algorithm (Signal / NIST SP 800-108)",
    },
    "zero-knowledge": {
        "name": "Zero-Knowledge Storage Boundary",
        "category": "Architecture",
        "description": "Enforces that plaintext data, filenames, and master keys NEVER leave the client boundary.",
        "security_level": "Untrusted server model: Cloud backends and databases only ever see ciphertext and hashes.",
        "when_to_use": "Mandatory across all CryptaVault storage targets.",
        "nist_standard": "Zero Trust Architecture (NIST SP 800-207)",
    },
    "dod-shredding": {
        "name": "DoD 5220.22-M Multi-Pass Shredding",
        "category": "Data Sanitization",
        "description": "Three-pass physical media sanitization: pass 1 writes 0x00, pass 2 writes 0xFF, pass 3 writes random bytes + fsync.",
        "security_level": "Prevents magnetic/flash remanence recovery on solid-state and spinning disks.",
        "when_to_use": "Cryptographic file deletion and local keystore destruction.",
        "nist_standard": "NIST SP 800-88 Rev 1",
    },
    "bip-39": {
        "name": "BIP-39 Mnemonic Seed Phrase",
        "category": "Key Management",
        "description": "24-word human-readable phrase encoding 256 bits of cryptographically secure entropy with checksum.",
        "security_level": "256 bits root key entropy.",
        "when_to_use": "Emergency paper backup and disaster key recovery.",
        "nist_standard": "Bitcoin Improvement Proposal 39",
    },
}


import re


def lookup_concept(concept_name: str) -> dict[str, Any] | None:
    """Case-insensitive lookup for a cryptographic concept."""
    raw = concept_name.lower().strip()
    for prefix in (
        "explain ",
        "what is ",
        "what are ",
        "tell me about ",
        "describe ",
        "how does ",
        "why use ",
    ):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :].strip()

    clean = raw.replace(" ", "-").replace("_", "-")
    for key, data in CONCEPTS.items():
        if key == clean or key in clean or clean in key:
            return data
        if clean in data["name"].lower() or data["name"].lower() in clean:
            return data

    tokens = [t for t in re.split(r"[\s\-_]+", raw) if len(t) > 2]
    for key, data in CONCEPTS.items():
        for token in tokens:
            if token in key or token in data["name"].lower():
                return data
    return None


def list_concepts() -> list[str]:
    """List all registered cryptographic concepts in the knowledge base."""
    return [c["name"] for c in CONCEPTS.values()]
