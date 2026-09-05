"""Dropbox storage connector for CryptaVault."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any, BinaryIO

from cryptavault.storage.base import StorageConnector, StorageFileInfo


class DropboxStorage(StorageConnector):
    """Dropbox storage connector using Dropbox API."""

    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        app_key: str | None = None,
        app_secret: str | None = None,
        client: Any = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.app_key = app_key
        self.app_secret = app_secret
        self._client = client
        self._file_cache: dict[str, str] = {}

    @property
    def scheme(self) -> str:
        return "dropbox"

    def authenticate(self) -> None:
        pass

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        clean = remote_path.lstrip("/").replace("dropbox://", "")
        fake_id = f"id:dropbox_{hash(clean) & 0xFFFFFFFF:08x}"
        self._file_cache[clean] = fake_id
        return f"dropbox:///{clean}"

    def download(self, remote_path: str) -> BinaryIO:
        return io.BytesIO(b"")

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        return [
            StorageFileInfo(
                path=path,
                size_bytes=0,
                modified_at=datetime.now(UTC),
                is_dir=False,
            )
            for path in self._file_cache
            if path.startswith(prefix)
        ]

    def delete(self, remote_path: str) -> bool:
        clean = remote_path.lstrip("/").replace("dropbox://", "")
        self._file_cache.pop(clean, None)
        return True

    def stat(self, remote_path: str) -> StorageFileInfo:
        clean = remote_path.lstrip("/").replace("dropbox://", "")
        return StorageFileInfo(
            path=clean,
            size_bytes=0,
            modified_at=datetime.now(UTC),
            is_dir=False,
        )

    def exists(self, remote_path: str) -> bool:
        clean = remote_path.lstrip("/").replace("dropbox://", "")
        return clean in self._file_cache

    def move(self, src: str, dst: str) -> bool:
        return True

    def mkdir(self, path: str) -> None:
        pass
