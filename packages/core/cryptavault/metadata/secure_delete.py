"""Secure Overwrite File Deletion and Memory Zeroing for CryptaVault.

Implements DoD 5220.22-M (3-pass overwrite) and in-place memory buffer erasure.

IMPORTANT PHYSICAL REALITY NOTE:
On modern Solid State Drives (SSDs) and flash media with wear-leveling controllers,
as well as copy-on-write (CoW) journaling filesystems (Btrfs, ZFS, APFS), software-level
block overwrites cannot guarantee physical magnetic/cell obliteration. Full-disk
encryption (FDE) and crypto-shredding (destroying the encryption key) remain the primary
zero-knowledge defense.
"""

from __future__ import annotations

import ctypes
import os
import secrets
from pathlib import Path


def secure_zero_memory(buffer: bytearray) -> None:
    """Zero out sensitive bytearray buffer memory in-place."""
    if not isinstance(buffer, bytearray):
        return

    length = len(buffer)
    if length == 0:
        return

    # In-place memory overwrite
    ctypes.memset((ctypes.c_char * length).from_buffer(buffer), 0, length)


def secure_delete_file(file_path: str | Path, passes: int = 3) -> None:
    """Overwrite file content with multi-pass patterns (DoD 5220.22-M) before unlinking."""
    path = Path(file_path)
    if not path.exists() or path.is_dir():
        return

    file_size = path.stat().st_size
    if file_size == 0:
        path.unlink(missing_ok=True)
        return

    chunk_size = 64 * 1024  # 64 KB write chunks

    with open(path, "r+b") as f:
        fd = f.fileno()

        # Pass 1: All zeros (0x00)
        f.seek(0)
        zero_chunk = b"\x00" * chunk_size
        bytes_left = file_size
        while bytes_left > 0:
            to_write = min(bytes_left, chunk_size)
            f.write(zero_chunk[:to_write])
            bytes_left -= to_write
        f.flush()
        os.fsync(fd)

        # Pass 2: All ones (0xFF)
        if passes >= 2:
            f.seek(0)
            ones_chunk = b"\xff" * chunk_size
            bytes_left = file_size
            while bytes_left > 0:
                to_write = min(bytes_left, chunk_size)
                f.write(ones_chunk[:to_write])
                bytes_left -= to_write
            f.flush()
            os.fsync(fd)

        # Pass 3: Random cryptographic bytes
        if passes >= 3:
            f.seek(0)
            bytes_left = file_size
            while bytes_left > 0:
                to_write = min(bytes_left, chunk_size)
                f.write(secrets.token_bytes(to_write))
                bytes_left -= to_write
            f.flush()
            os.fsync(fd)

        # Truncate to zero length
        f.truncate(0)
        f.flush()
        os.fsync(fd)

    # Finally unlink
    path.unlink(missing_ok=True)
