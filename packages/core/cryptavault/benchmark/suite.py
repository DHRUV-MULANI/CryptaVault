"""Comparative Benchmark Suite for CryptaVault.

Evaluates throughput, latency, key sizes, memory, and NIST security levels
across classical, post-quantum, and hybrid primitives.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

from cryptavault.crypto.asymmetric import Ed25519Signer
from cryptavault.crypto.hash import Blake3, Sha256
from cryptavault.crypto.hybrid import HybridKemPQ
from cryptavault.crypto.kdf import Argon2id
from cryptavault.crypto.pq import Kyber768
from cryptavault.crypto.symmetric import AES256GCM, ChaCha20Poly1305


@dataclass
class BenchmarkResult:
    """Individual cryptographic benchmark measurement."""

    algorithm: str
    category: str  # "Symmetric AEAD", "Hash", "KEM", "Signature", "KDF", "Hybrid"
    operation: str
    throughput_mb_s: float
    latency_ms: float
    key_size_bytes: int
    tag_or_sig_bytes: int
    classical_bits: int
    pq_bits: int
    nist_level: str


class BenchmarkSuite:
    """Orchestrates comprehensive cross-primitive micro-benchmarks."""

    def __init__(self) -> None:
        self.results: list[BenchmarkResult] = []

    def run_all(
        self, payload_size_bytes: int = 1024 * 1024, iterations: int = 5
    ) -> list[BenchmarkResult]:
        """Execute benchmarks across all primitives."""
        self.results = []
        data = os.urandom(payload_size_bytes)
        key32 = os.urandom(32)
        nonce12 = os.urandom(12)

        # 1. AES-256-GCM
        aes = AES256GCM()
        t0 = time.perf_counter()
        for _ in range(iterations):
            _ = aes.encrypt(key32, nonce12, data)
        elapsed = time.perf_counter() - t0
        mb = (payload_size_bytes * iterations) / (1024 * 1024)
        throughput = mb / elapsed if elapsed > 0 else 0
        self.results.append(
            BenchmarkResult(
                algorithm="AES-256-GCM (Hardware AES-NI)",
                category="Symmetric AEAD",
                operation="encrypt",
                throughput_mb_s=round(throughput, 1),
                latency_ms=round((elapsed / iterations) * 1000, 3),
                key_size_bytes=32,
                tag_or_sig_bytes=16,
                classical_bits=256,
                pq_bits=128,  # Grover
                nist_level="FIPS 197 / NIST SP 800-38D",
            )
        )

        # 2. ChaCha20-Poly1305
        chacha = ChaCha20Poly1305()
        t0 = time.perf_counter()
        for _ in range(iterations):
            _ = chacha.encrypt(key32, nonce12, data)
        elapsed = time.perf_counter() - t0
        throughput = mb / elapsed if elapsed > 0 else 0
        self.results.append(
            BenchmarkResult(
                algorithm="ChaCha20-Poly1305 (Constant-Time)",
                category="Symmetric AEAD",
                operation="encrypt",
                throughput_mb_s=round(throughput, 1),
                latency_ms=round((elapsed / iterations) * 1000, 3),
                key_size_bytes=32,
                tag_or_sig_bytes=16,
                classical_bits=256,
                pq_bits=128,
                nist_level="RFC 8439",
            )
        )

        # 3. BLAKE3
        b3 = Blake3()
        t0 = time.perf_counter()
        for _ in range(iterations):
            _ = b3.digest(data)
        elapsed = time.perf_counter() - t0
        throughput = mb / elapsed if elapsed > 0 else 0
        self.results.append(
            BenchmarkResult(
                algorithm="BLAKE3 (Tree Hash AVX2)",
                category="Hash",
                operation="digest",
                throughput_mb_s=round(throughput, 1),
                latency_ms=round((elapsed / iterations) * 1000, 3),
                key_size_bytes=0,
                tag_or_sig_bytes=32,
                classical_bits=256,
                pq_bits=128,
                nist_level="Modern Tree Hash",
            )
        )

        # 4. SHA-256
        sha = Sha256()
        t0 = time.perf_counter()
        for _ in range(iterations):
            _ = sha.digest(data)
        elapsed = time.perf_counter() - t0
        throughput = mb / elapsed if elapsed > 0 else 0
        self.results.append(
            BenchmarkResult(
                algorithm="SHA-256 (NIST Standard)",
                category="Hash",
                operation="digest",
                throughput_mb_s=round(throughput, 1),
                latency_ms=round((elapsed / iterations) * 1000, 3),
                key_size_bytes=0,
                tag_or_sig_bytes=32,
                classical_bits=256,
                pq_bits=128,
                nist_level="FIPS 180-4",
            )
        )

        # 5. Kyber-768 (ML-KEM-768)
        kyber = Kyber768()
        pub_k, _priv_k = kyber.keypair()
        t0 = time.perf_counter()
        for _ in range(iterations * 10):
            _ss, ct_k = kyber.encapsulate(pub_k)
        elapsed = time.perf_counter() - t0
        ops_per_sec = (iterations * 10) / elapsed if elapsed > 0 else 0
        self.results.append(
            BenchmarkResult(
                algorithm="ML-KEM-768 (Kyber-768)",
                category="KEM",
                operation="encapsulate",
                throughput_mb_s=round(ops_per_sec, 0),  # ops/sec for asymmetric
                latency_ms=round((elapsed / (iterations * 10)) * 1000, 3),
                key_size_bytes=len(pub_k),
                tag_or_sig_bytes=len(ct_k),
                classical_bits=192,
                pq_bits=192,
                nist_level="NIST FIPS 203 (Category 3)",
            )
        )

        # 6. Ed25519 Signatures
        ed = Ed25519Signer()
        _pub_ed, priv_ed = ed.keypair()
        t0 = time.perf_counter()
        for _ in range(iterations * 10):
            _ = ed.sign(priv_ed, b"Benchmark message")
        elapsed = time.perf_counter() - t0
        self.results.append(
            BenchmarkResult(
                algorithm="Ed25519",
                category="Signature",
                operation="sign",
                throughput_mb_s=round((iterations * 10) / elapsed if elapsed > 0 else 0, 0),
                latency_ms=round((elapsed / (iterations * 10)) * 1000, 3),
                key_size_bytes=32,
                tag_or_sig_bytes=64,
                classical_bits=128,
                pq_bits=0,  # Vulnerable to Shor's algorithm
                nist_level="RFC 8032",
            )
        )

        # 7. Post-Quantum Hybrid KEM (X25519 + Kyber768)
        hkem = HybridKemPQ()
        pub_h, _priv_h = hkem.keypair()
        t0 = time.perf_counter()
        for _ in range(iterations * 5):
            _ss_h, ct_h = hkem.encapsulate(pub_h)
        elapsed = time.perf_counter() - t0
        self.results.append(
            BenchmarkResult(
                algorithm="Hybrid KEM (X25519 + Kyber768)",
                category="Hybrid",
                operation="encapsulate",
                throughput_mb_s=round((iterations * 5) / elapsed if elapsed > 0 else 0, 0),
                latency_ms=round((elapsed / (iterations * 5)) * 1000, 3),
                key_size_bytes=len(pub_h),
                tag_or_sig_bytes=len(ct_h),
                classical_bits=128,
                pq_bits=192,
                nist_level="Hybrid FIPS 203 + RFC 7748",
            )
        )

        # 8. Argon2id KDF
        argon = Argon2id()
        t0 = time.perf_counter()
        argon.derive(
            b"testpass", os.urandom(16), length=32, time_cost=1, memory_cost=16384, parallelism=2
        )
        elapsed = time.perf_counter() - t0
        self.results.append(
            BenchmarkResult(
                algorithm="Argon2id (Memory-Hard KDF)",
                category="KDF",
                operation="derive",
                throughput_mb_s=round(1.0 / elapsed if elapsed > 0 else 0, 1),
                latency_ms=round(elapsed * 1000, 2),
                key_size_bytes=32,
                tag_or_sig_bytes=32,
                classical_bits=256,
                pq_bits=128,
                nist_level="RFC 9106 / Password Hashing Competition Winner",
            )
        )

        return self.results

    def to_dict(self) -> list[dict[str, Any]]:
        return [asdict(r) for r in self.results]

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_csv(self) -> str:
        output = io.StringIO()
        if not self.results:
            return ""
        writer = csv.DictWriter(output, fieldnames=list(asdict(self.results[0]).keys()))
        writer.writeheader()
        for r in self.results:
            writer.writerow(asdict(r))
        return output.getvalue()
