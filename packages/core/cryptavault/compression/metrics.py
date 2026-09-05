"""Compression Metrics and Measurement for CryptaVault."""

from __future__ import annotations

import time
from dataclasses import dataclass

from cryptavault.compression.algorithms import get_compressor


@dataclass(frozen=True)
class CompressionMetrics:
    """Statistical measurement of compression performance."""

    algorithm: str
    original_size_bytes: int
    compressed_size_bytes: int
    ratio: float
    savings_percent: float
    duration_ms: float
    throughput_mb_s: float


def measure_compression(data: bytes, algorithm: str = "zstd") -> tuple[bytes, CompressionMetrics]:
    """Compress data and capture detailed performance telemetry."""
    compressor = get_compressor(algorithm)
    orig_len = len(data)

    t0 = time.perf_counter()
    compressed = compressor.compress(data)
    dur = time.perf_counter() - t0

    dur_ms = dur * 1000.0
    comp_len = len(compressed)
    ratio = comp_len / orig_len if orig_len > 0 else 1.0
    savings = (1.0 - ratio) * 100.0
    throughput = (orig_len / (1024 * 1024)) / dur if dur > 0 else 0.0

    metrics = CompressionMetrics(
        algorithm=algorithm,
        original_size_bytes=orig_len,
        compressed_size_bytes=comp_len,
        ratio=ratio,
        savings_percent=savings,
        duration_ms=dur_ms,
        throughput_mb_s=throughput,
    )
    return compressed, metrics
