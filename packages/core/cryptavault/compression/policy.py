"""Intelligent Skip-Compression Decision Policy for CryptaVault."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from cryptavault.adaptive.profiles import SecurityProfile
from cryptavault.compression.detect import FileCategory, detect_file_type


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of byte sequence (0.0 to 8.0 bits/byte)."""
    if not data:
        return 0.0

    length = len(data)
    counts = Counter(data)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def should_compress(
    data_or_path: bytes | str | Path,
    profile: SecurityProfile | None = None,
    sample_size_bytes: int = 64 * 1024,
) -> bool:
    """Determine whether a payload should be passed through the compression stage.

    Decisions:
    1. If content is an already-compressed media format (JPEG, MP4, ZIP, etc.) -> False.
    2. If content is plain text or source code -> True.
    3. If unknown binary, inspect Shannon entropy:
       - High entropy (> 7.5 bits/byte, typical of encrypted or random data) -> False.
       - Low/moderate entropy (<= 7.5 bits/byte) -> True.
    """
    info = detect_file_type(data_or_path)
    if info.is_pre_compressed:
        return False

    if info.category == FileCategory.TEXT:
        return True

    # Sample data for entropy evaluation
    if isinstance(data_or_path, (str, Path)):
        p = Path(data_or_path)
        if not p.exists() or p.is_dir():
            return False
        with open(p, "rb") as f:
            sample = f.read(sample_size_bytes)
    else:
        sample = data_or_path[:sample_size_bytes]

    if not sample:
        return False

    entropy = calculate_entropy(sample)
    # Entropy threshold: data with entropy >= 7.6 bits/byte yields negligible compression
    return entropy < 7.6
