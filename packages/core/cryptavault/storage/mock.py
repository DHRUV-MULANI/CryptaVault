"""In-memory mock storage connector for zero-network testing and development."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import BinaryIO

from cryptavault.storage.base import StorageConnector, StorageFileInfo


class MockStorage(StorageConnector):
    """In-memory dictionary-backed storage connector."""

    def __init__(self, scheme: str = "mock") -> None:
        self._scheme = scheme
        self._data: dict[str, bytes] = {}
        self._metadata: dict[str, StorageFileInfo] = {}
        self._authenticated = True

    @property
    def scheme(self) -> str:
        return self._scheme

    def authenticate(self) -> None:
        self._authenticated = True

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        data = stream.read()
        self._data[remote_path] = data
        self._metadata[remote_path] = StorageFileInfo(
            path=remote_path,
            size_bytes=len(data),
            modified_at=datetime.now(UTC),
            is_dir=False,
        )
        return f"{self.scheme}://{remote_path}"

    def download(self, remote_path: str) -> BinaryIO:
        if remote_path not in self._data:
            raise FileNotFoundError(f"Mock storage path not found: {remote_path}")
        return io.BytesIO(self._data[remote_path])

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        return [info for path, info in self._metadata.items() if path.startswith(prefix)]

    def delete(self, remote_path: str) -> bool:
        if remote_path in self._data:
            del self._data[remote_path]
            self._metadata.pop(remote_path, None)
            return True
        return False

    def stat(self, remote_path: str) -> StorageFileInfo:
        if remote_path not in self._metadata:
            raise FileNotFoundError(f"Mock storage path not found: {remote_path}")
        return self._metadata[remote_path]

    def exists(self, remote_path: str) -> bool:
        return remote_path in self._data

    def move(self, src: str, dst: str) -> bool:
        if src not in self._data:
            raise FileNotFoundError(f"Source not found: {src}")
        self._data[dst] = self._data.pop(src)
        info = self._metadata.pop(src)
        info.path = dst
        info.modified_at = datetime.now(UTC)
        self._metadata[dst] = info
        return True

    def mkdir(self, path: str) -> None:
        # Directory is a no-op in key-value store
        pass
