"""Per-File Integrity Hashing for CryptaVault.

Provides streaming cryptographic hashing for arbitrary files and binary streams
supporting BLAKE3, SHA-256, and SHA3-512 via the plugin registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from cryptavault.plugins.registry import hash_registry


def compute_file_hash(
    file_or_path: str | Path | BinaryIO,
    algorithm: str = "blake3",
    chunk_size: int = 1024 * 1024,
) -> str:
    """Compute the hex-encoded cryptographic digest of a file or stream.

    Streams content in memory-efficient chunks (default 1 MiB) to protect against OOM
    when processing multi-gigabyte files.
    """
    hasher_cls = hash_registry.get(algorithm)
    hasher_instance = hasher_cls()
    stream_hasher = hasher_instance.streaming()

    if isinstance(file_or_path, (str, Path)):
        path = Path(file_or_path)
        with path.open("rb") as f:
            while chunk := f.read(chunk_size):
                stream_hasher.update(chunk)
    else:
        while chunk := file_or_path.read(chunk_size):
            stream_hasher.update(chunk)

    return stream_hasher.hexdigest()
