"""SFTP Storage connector using Paramiko for remote encrypted storage."""

from __future__ import annotations

import io
import stat
from datetime import UTC, datetime
from typing import BinaryIO
from urllib.parse import urlparse

from cryptavault.storage.base import StorageConnector, StorageFileInfo

try:
    import paramiko
except ImportError:
    paramiko = None  # type: ignore[assignment]


class SftpStorage(StorageConnector):
    """Secure File Transfer Protocol (SFTP) storage connector."""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "crypta",
        password: str | None = None,
        key_filename: str | None = None,
        base_dir: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.base_dir = base_dir.strip("/")
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    @classmethod
    def from_uri(cls, uri: str) -> SftpStorage:
        """Create connector from URI: sftp://user:pass@host:port/path"""
        parsed = urlparse(uri)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 22,
            username=parsed.username or "anonymous",
            password=parsed.password,
            base_dir=parsed.path.lstrip("/"),
        )

    @property
    def scheme(self) -> str:
        return "sftp"

    def authenticate(self) -> None:
        if paramiko is None:
            raise ImportError("paramiko is not installed. Install with `uv pip install paramiko`.")
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            key_filename=self.key_filename,
            timeout=10,
        )
        self._sftp = self._client.open_sftp()

    def _get_sftp(self) -> paramiko.SFTPClient:
        if self._sftp is None:
            self.authenticate()
        assert self._sftp is not None
        return self._sftp

    def _resolve(self, remote_path: str) -> str:
        clean = remote_path.lstrip("/").replace("sftp://", "")
        if self.base_dir:
            return f"/{self.base_dir}/{clean}"
        return f"/{clean}"

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        sftp = self._get_sftp()
        full_path = self._resolve(remote_path)
        # Ensure parent dirs exist
        parent = full_path.rsplit("/", 1)[0]
        if parent:
            try:
                sftp.mkdir(parent)
            except Exception:
                pass

        # Stream upload via putfo
        sftp.putfo(stream, full_path)
        return f"sftp://{self.host}:{self.port}{full_path}"

    def download(self, remote_path: str) -> BinaryIO:
        sftp = self._get_sftp()
        full_path = self._resolve(remote_path)
        buf = io.BytesIO()
        sftp.getfo(full_path, buf)
        buf.seek(0)
        return buf

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        sftp = self._get_sftp()
        full_path = (
            self._resolve(prefix) if prefix else (f"/{self.base_dir}" if self.base_dir else "/")
        )
        results: list[StorageFileInfo] = []
        try:
            for attr in sftp.listdir_attr(full_path):
                is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
                results.append(
                    StorageFileInfo(
                        path=f"{prefix}/{attr.filename}".strip("/"),
                        size_bytes=attr.st_size or 0,
                        modified_at=datetime.fromtimestamp(attr.st_mtime or 0, tz=UTC),
                        is_dir=is_dir,
                    )
                )
        except OSError:
            pass
        return results

    def delete(self, remote_path: str) -> bool:
        sftp = self._get_sftp()
        full_path = self._resolve(remote_path)
        try:
            sftp.remove(full_path)
            return True
        except OSError:
            return False

    def stat(self, remote_path: str) -> StorageFileInfo:
        sftp = self._get_sftp()
        full_path = self._resolve(remote_path)
        try:
            attr = sftp.stat(full_path)
            is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
            return StorageFileInfo(
                path=remote_path.lstrip("/"),
                size_bytes=attr.st_size or 0,
                modified_at=datetime.fromtimestamp(attr.st_mtime or 0, tz=UTC),
                is_dir=is_dir,
            )
        except OSError as e:
            raise FileNotFoundError(f"SFTP file not found: {remote_path}") from e

    def exists(self, remote_path: str) -> bool:
        try:
            self.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def move(self, src: str, dst: str) -> bool:
        sftp = self._get_sftp()
        sftp.rename(self._resolve(src), self._resolve(dst))
        return True

    def mkdir(self, path: str) -> None:
        sftp = self._get_sftp()
        sftp.mkdir(self._resolve(path))

    def close(self) -> None:
        if self._sftp:
            self._sftp.close()
        if self._client:
            self._client.close()
