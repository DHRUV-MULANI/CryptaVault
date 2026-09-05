"""Resume Checkpointing for Interrupted Operations in CryptaVault."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from cryptavault.crypto.hash import Blake3


@dataclass
class OperationCheckpoint:
    """State of an ongoing or interrupted chunked pipeline operation."""

    file_id: str
    file_path: str
    file_size_bytes: int
    chunk_size_bytes: int
    completed_chunks: dict[int, str]  # chunk_index -> chunk_hash (BLAKE3 hex)
    is_complete: bool = False

    def mark_chunk(self, chunk_index: int, chunk_ciphertext: bytes) -> None:
        """Record a successfully processed chunk."""
        h = Blake3().digest(chunk_ciphertext).hex()
        self.completed_chunks[chunk_index] = h

    def verify_chunk(self, chunk_index: int, chunk_ciphertext: bytes) -> bool:
        """Verify whether an existing chunk matches its recorded hash."""
        if chunk_index not in self.completed_chunks:
            return False
        h = Blake3().digest(chunk_ciphertext).hex()
        return self.completed_chunks[chunk_index] == h

    def save(self, checkpoint_path: str | Path) -> None:
        """Save checkpoint to disk as JSON."""
        p = Path(checkpoint_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Convert integer keys to str for JSON serialization
        data = asdict(self)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, checkpoint_path: str | Path) -> OperationCheckpoint | None:
        """Load checkpoint from disk. Returns None if file does not exist."""
        p = Path(checkpoint_path)
        if not p.exists():
            return None
        raw = json.loads(p.read_text(encoding="utf-8"))
        # Re-convert str keys to int
        raw["completed_chunks"] = {int(k): v for k, v in raw.get("completed_chunks", {}).items()}
        return cls(**raw)
