"""Metadata Data Model and Schemas for CryptaVault."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class FileMetadata:
    """Detailed file metadata stored inside the zero-knowledge encrypted manifest."""

    file_id: str
    original_name: str
    original_size_bytes: int
    mime_type: str
    created_at: str
    modified_at: str
    chunk_count: int
    compression_algo: str | None
    encryption_algo: str
    key_id: str
    merkle_root_hex: str
    signature_hex: str
    extra_attributes: dict[str, Any]


@dataclass
class Manifest:
    """Top-level vault manifest grouping encrypted file records."""

    vault_id: str
    manifest_version: int = 1
    updated_at: str = ""
    files: dict[str, FileMetadata] | None = None

    def __post_init__(self) -> None:
        if self.files is None:
            self.files = {}
        if not self.updated_at:
            self.updated_at = datetime.now(UTC).isoformat()

    def add_file(self, metadata: FileMetadata) -> None:
        """Add or update file record in manifest."""
        assert self.files is not None
        self.files[metadata.file_id] = metadata
        self.updated_at = datetime.now(UTC).isoformat()

    def remove_file(self, file_id: str) -> None:
        """Remove file record from manifest."""
        assert self.files is not None
        if file_id in self.files:
            del self.files[file_id]
            self.updated_at = datetime.now(UTC).isoformat()

    def to_json(self) -> str:
        """Serialize manifest to JSON string."""
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, data: str) -> Manifest:
        """Deserialize manifest from JSON string."""
        raw = json.loads(data)
        files_dict = {}
        for fid, fmeta in raw.get("files", {}).items():
            files_dict[fid] = FileMetadata(**fmeta)
        return cls(
            vault_id=raw["vault_id"],
            manifest_version=raw.get("manifest_version", 1),
            updated_at=raw.get("updated_at", ""),
            files=files_dict,
        )
