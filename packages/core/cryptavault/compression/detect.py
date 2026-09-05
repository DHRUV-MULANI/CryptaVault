"""Magic Byte File Type Detection for CryptaVault.

Detects file types and identifies whether content is already compressed
or encrypted to prevent wasted CPU cycles on double-compression.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class FileCategory(str, Enum):
    """Broad category of detected content."""

    ARCHIVE = "ARCHIVE"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"
    EXECUTABLE = "EXECUTABLE"
    TEXT = "TEXT"
    BINARY_UNKNOWN = "BINARY_UNKNOWN"


# Table of magic byte signatures: (prefix_bytes, mime_type, category, is_pre_compressed)
MAGIC_SIGNATURES: list[tuple[bytes, str, FileCategory, bool]] = [
    # Archives & Compressed formats
    (b"\x1f\x8b", "application/gzip", FileCategory.ARCHIVE, True),
    (b"\x28\xb5\x2f\xfd", "application/zstd", FileCategory.ARCHIVE, True),
    (b"BZh", "application/x-bzip2", FileCategory.ARCHIVE, True),
    (b"\xfd7zXZ\x00", "application/x-xz", FileCategory.ARCHIVE, True),
    (b"7z\xbc\xaf'\x1c", "application/x-7z-compressed", FileCategory.ARCHIVE, True),
    (b"Rar!\x1a\x07", "application/vnd.rar", FileCategory.ARCHIVE, True),
    (b"PK\x03\x04", "application/zip", FileCategory.ARCHIVE, True),
    (b"PK\x05\x06", "application/zip", FileCategory.ARCHIVE, True),
    (b"PK\x07\x08", "application/zip", FileCategory.ARCHIVE, True),
    # Images (Pre-compressed)
    (b"\xff\xd8\xff", "image/jpeg", FileCategory.IMAGE, True),
    (b"\x89PNG\r\n\x1a\n", "image/png", FileCategory.IMAGE, True),
    (b"GIF87a", "image/gif", FileCategory.IMAGE, True),
    (b"GIF89a", "image/gif", FileCategory.IMAGE, True),
    # Videos & Audio (Pre-compressed)
    (b"\x00\x00\x00\x18ftypmp42", "video/mp4", FileCategory.VIDEO, True),
    (b"\x00\x00\x00\x1cftypisom", "video/mp4", FileCategory.VIDEO, True),
    (b"\x00\x00\x00\x20ftypisom", "video/mp4", FileCategory.VIDEO, True),
    (b"\x1aE\xdf\xa3", "video/x-matroska", FileCategory.VIDEO, True),
    (b"ID3", "audio/mpeg", FileCategory.AUDIO, True),
    (b"\xff\xfb", "audio/mpeg", FileCategory.AUDIO, True),
    (b"fLaC", "audio/flac", FileCategory.AUDIO, True),
    (b"OggS", "audio/ogg", FileCategory.AUDIO, True),
    # Documents
    (b"%PDF", "application/pdf", FileCategory.DOCUMENT, True),  # PDFs have internal zlib streams
    # Databases & Executables (Compressible)
    (b"SQLite format 3\x00", "application/vnd.sqlite3", FileCategory.DOCUMENT, False),
    (b"\x7fELF", "application/x-executable", FileCategory.EXECUTABLE, False),
    (b"MZ", "application/x-dosexec", FileCategory.EXECUTABLE, False),
    (b"\xca\xfe\xba\xbe", "application/x-mach-binary", FileCategory.EXECUTABLE, False),
]


class FileTypeInfo:
    """Detection result for a file or memory buffer."""

    def __init__(
        self,
        mime_type: str,
        category: FileCategory,
        is_pre_compressed: bool,
    ) -> None:
        self.mime_type = mime_type
        self.category = category
        self.is_pre_compressed = is_pre_compressed

    def __repr__(self) -> str:
        return (
            f"FileTypeInfo(mime='{self.mime_type}', category={self.category.value}, "
            f"pre_compressed={self.is_pre_compressed})"
        )


def detect_file_type(data_or_path: bytes | str | Path) -> FileTypeInfo:
    """Inspect magic bytes to detect file type and compression eligibility."""
    if isinstance(data_or_path, (str, Path)):
        p = Path(data_or_path)
        if not p.exists() or p.is_dir():
            return FileTypeInfo("application/octet-stream", FileCategory.BINARY_UNKNOWN, False)
        with open(p, "rb") as f:
            header = f.read(512)
    else:
        header = data_or_path[:512]

    # Check magic signatures
    for sig, mime, cat, pre_comp in MAGIC_SIGNATURES:
        if header.startswith(sig):
            return FileTypeInfo(mime, cat, pre_comp)

    # Check for RIFF WEBP / WAV
    if header.startswith(b"RIFF") and len(header) >= 12:
        tag = header[8:12]
        if tag == b"WEBP":
            return FileTypeInfo("image/webp", FileCategory.IMAGE, True)
        if tag == b"WAVE":
            return FileTypeInfo("audio/wav", FileCategory.AUDIO, False)

    # Check if plain UTF-8 text
    try:
        header.decode("utf-8")
        return FileTypeInfo("text/plain", FileCategory.TEXT, False)
    except UnicodeDecodeError:
        pass

    return FileTypeInfo("application/octet-stream", FileCategory.BINARY_UNKNOWN, False)
