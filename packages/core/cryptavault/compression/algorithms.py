"""Streaming & Block Compression Algorithms for CryptaVault.

Implements:
- Zstandard (Default, highest throughput and balanced ratio)
- Brotli (High density text/web assets)
- Gzip (Standards-compliant fallback)
- LZMA (Maximum compression ratio for cold storage)
"""

from __future__ import annotations

import gzip
import io
import lzma
from typing import Any, ClassVar

import brotli
import zstandard as zstd

from cryptavault.plugins.registry import CompressionAlgorithm, register_compression


class CompressionError(Exception):
    """Base exception for compression failures."""


class BaseCompressor(CompressionAlgorithm):
    """Base implementation for CryptaVault compression engines."""

    name: ClassVar[str] = "base"

    def compress(self, data: Any) -> Any:
        """Compress bytes or binary stream."""
        if hasattr(data, "read"):
            raw = data.read()
            out = self.compress_bytes(raw)
            return io.BytesIO(out)
        return self.compress_bytes(data)

    def decompress(self, data: Any) -> Any:
        """Decompress bytes or binary stream."""
        if hasattr(data, "read"):
            raw = data.read()
            out = self.decompress_bytes(raw)
            return io.BytesIO(out)
        return self.decompress_bytes(data)

    def compress_bytes(self, data: bytes) -> bytes:
        """Perform block compression."""
        raise NotImplementedError

    def decompress_bytes(self, data: bytes) -> bytes:
        """Perform block decompression."""
        raise NotImplementedError


@register_compression("zstd")
class ZstdCompressor(BaseCompressor):
    """Zstandard compression (RFC 8878)."""

    name: ClassVar[str] = "zstd"

    def __init__(self, level: int = 3) -> None:
        self.cctx = zstd.ZstdCompressor(level=level)
        self.dctx = zstd.ZstdDecompressor()

    def compress_bytes(self, data: bytes) -> bytes:
        """Compress data using Zstandard."""
        return bytes(self.cctx.compress(data))

    def decompress_bytes(self, data: bytes) -> bytes:
        """Decompress Zstandard data."""
        return bytes(self.dctx.decompress(data))


@register_compression("brotli")
class BrotliCompressor(BaseCompressor):
    """Brotli compression (RFC 7932)."""

    name: ClassVar[str] = "brotli"

    def __init__(self, quality: int = 6) -> None:
        self.quality = quality

    def compress_bytes(self, data: bytes) -> bytes:
        """Compress data using Brotli."""
        return bytes(brotli.compress(data, quality=self.quality))

    def decompress_bytes(self, data: bytes) -> bytes:
        """Decompress Brotli data."""
        return bytes(brotli.decompress(data))


@register_compression("gzip")
class GzipCompressor(BaseCompressor):
    """Gzip compression (RFC 1952)."""

    name: ClassVar[str] = "gzip"

    def __init__(self, compresslevel: int = 6) -> None:
        self.compresslevel = compresslevel

    def compress_bytes(self, data: bytes) -> bytes:
        """Compress data using Gzip."""
        return gzip.compress(data, compresslevel=self.compresslevel)

    def decompress_bytes(self, data: bytes) -> bytes:
        """Decompress Gzip data."""
        return gzip.decompress(data)


@register_compression("lzma")
class LzmaCompressor(BaseCompressor):
    """LZMA / XZ compression."""

    name: ClassVar[str] = "lzma"

    def __init__(self, preset: int = 6) -> None:
        self.preset = preset

    def compress_bytes(self, data: bytes) -> bytes:
        """Compress data using LZMA."""
        return lzma.compress(data, preset=self.preset)

    def decompress_bytes(self, data: bytes) -> bytes:
        """Decompress LZMA data."""
        return lzma.decompress(data)


_COMPRESSORS: dict[str, BaseCompressor] = {
    "zstd": ZstdCompressor(),
    "brotli": BrotliCompressor(),
    "gzip": GzipCompressor(),
    "lzma": LzmaCompressor(),
}


def get_compressor(name: str = "zstd") -> BaseCompressor:
    """Retrieve compressor instance by name."""
    norm = name.lower().strip()
    if norm not in _COMPRESSORS:
        raise ValueError(
            f"Unsupported compression algorithm '{name}'. Options: {list(_COMPRESSORS.keys())}"
        )
    return _COMPRESSORS[norm]


def compress(data: bytes, algorithm: str = "zstd") -> bytes:
    """One-shot helper to compress data."""
    return get_compressor(algorithm).compress_bytes(data)


def decompress(data: bytes, algorithm: str = "zstd") -> bytes:
    """One-shot helper to decompress data."""
    return get_compressor(algorithm).decompress_bytes(data)
