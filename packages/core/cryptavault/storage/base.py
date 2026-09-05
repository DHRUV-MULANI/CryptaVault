"""StorageConnector abstract base class for CryptaVault multi-backend storage.

All storage backends (Local, Supabase, SFTP, FTP, Cloud) implement this interface.
Zero-Knowledge Invariant: Connectors handle strictly encrypted ciphertext streams.
Plaintext data is never passed to storage drivers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO


@dataclass
class StorageFileInfo:
    """Metadata describing a remote storage object."""

    path: str
    size_bytes: int
    modified_at: datetime
    is_dir: bool = False
    etag: str | None = None
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at.isoformat(),
            "is_dir": self.is_dir,
            "etag": self.etag,
            "extra": self.extra or {},
        }


class StorageConnector(ABC):
    """Abstract interface defining required storage operations."""

    @property
    @abstractmethod
    def scheme(self) -> str:
        """URI scheme supported by this connector (e.g., 'local', 'supabase', 'sftp')."""
        ...

    @abstractmethod
    def authenticate(self) -> None:
        """Validate credentials and test connection to the storage provider."""
        ...

    @abstractmethod
    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        """Stream an encrypted payload to the remote path.

        Returns:
            The canonical path or URI of the uploaded object.
        """
        ...

    @abstractmethod
    def download(self, remote_path: str) -> BinaryIO:
        """Stream an encrypted payload from the remote path.

        Returns:
            A file-like readable stream of raw bytes.
        """
        ...

    @abstractmethod
    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        """List files matching the given path prefix."""
        ...

    @abstractmethod
    def delete(self, remote_path: str) -> bool:
        """Delete an object at remote_path. Returns True if deleted."""
        ...

    @abstractmethod
    def stat(self, remote_path: str) -> StorageFileInfo:
        """Retrieve metadata for the object at remote_path.

        Raises FileNotFoundError if the object does not exist.
        """
        ...

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """Check whether remote_path exists."""
        ...

    @abstractmethod
    def move(self, src: str, dst: str) -> bool:
        """Atomically rename or move an object from src to dst."""
        ...

    @abstractmethod
    def mkdir(self, path: str) -> None:
        """Ensure the given directory path exists."""
        ...
