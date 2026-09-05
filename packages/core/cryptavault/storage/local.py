"""Local filesystem storage connector with atomic writes and directory containment."""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from cryptavault.storage.base import StorageConnector, StorageFileInfo


class LocalStorage(StorageConnector):
    """Local filesystem storage connector enforcing directory isolation and atomic writes."""

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    @property
    def scheme(self) -> str:
        return "local"

    def authenticate(self) -> None:
        if not self.root_path.exists() or not os.access(self.root_path, os.W_OK):
            raise PermissionError(f"Cannot write to storage root: {self.root_path}")

    def _resolve(self, remote_path: str) -> Path:
        # Strip leading slash/scheme
        clean_path = remote_path.lstrip("/").replace("local://", "")
        target = (self.root_path / clean_path).resolve()
        # Prevent directory traversal attacks
        if not str(target).startswith(str(self.root_path)):
            raise ValueError(f"Path traversal detected: {remote_path}")
        return target

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        target = self._resolve(remote_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: stream to temp file in target directory, flush, fsync, then rename
        tmp_fd, tmp_path_str = tempfile.mkstemp(dir=target.parent, prefix=".upload_tmp_")
        tmp_path = Path(tmp_path_str)
        try:
            with open(tmp_fd, "wb") as f_out:
                shutil.copyfileobj(stream, f_out, length=64 * 1024)
                f_out.flush()
                os.fsync(f_out.fileno())
            tmp_path.replace(target)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

        return f"local://{remote_path.lstrip('/')}"

    def download(self, remote_path: str) -> BinaryIO:
        target = self._resolve(remote_path)
        if not target.exists() or target.is_dir():
            raise FileNotFoundError(f"Object not found: {remote_path}")
        return open(target, "rb")

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        results: list[StorageFileInfo] = []
        search_root = self._resolve(prefix) if prefix else self.root_path

        if not search_root.exists():
            return results

        if search_root.is_file():
            stat = search_root.stat()
            rel = str(search_root.relative_to(self.root_path))
            return [
                StorageFileInfo(
                    path=rel,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                    is_dir=False,
                )
            ]

        for entry in search_root.rglob("*"):
            if entry.name.startswith(".upload_tmp_"):
                continue
            stat = entry.stat()
            rel = str(entry.relative_to(self.root_path))
            results.append(
                StorageFileInfo(
                    path=rel,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                    is_dir=entry.is_dir(),
                )
            )
        return results

    def delete(self, remote_path: str) -> bool:
        target = self._resolve(remote_path)
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return True
        return False

    def stat(self, remote_path: str) -> StorageFileInfo:
        target = self._resolve(remote_path)
        if not target.exists():
            raise FileNotFoundError(f"Object not found: {remote_path}")
        s = target.stat()
        return StorageFileInfo(
            path=remote_path.lstrip("/"),
            size_bytes=s.st_size,
            modified_at=datetime.fromtimestamp(s.st_mtime, tz=UTC),
            is_dir=target.is_dir(),
        )

    def exists(self, remote_path: str) -> bool:
        return self._resolve(remote_path).exists()

    def move(self, src: str, dst: str) -> bool:
        src_target = self._resolve(src)
        dst_target = self._resolve(dst)
        if not src_target.exists():
            raise FileNotFoundError(f"Source not found: {src}")
        dst_target.parent.mkdir(parents=True, exist_ok=True)
        src_target.replace(dst_target)
        return True

    def mkdir(self, path: str) -> None:
        target = self._resolve(path)
        target.mkdir(parents=True, exist_ok=True)
