"""FTP Storage connector using standard library ftplib."""

from __future__ import annotations

import ftplib
import io
from datetime import UTC, datetime
from typing import BinaryIO
from urllib.parse import urlparse

from cryptavault.storage.base import StorageConnector, StorageFileInfo


class FtpStorage(StorageConnector):
    """File Transfer Protocol (FTP/FTPS) storage connector."""

    def __init__(
        self,
        host: str,
        port: int = 21,
        username: str = "anonymous",
        password: str = "anonymous@",
        base_dir: str = "",
        use_tls: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_dir = base_dir.strip("/")
        self.use_tls = use_tls
        self._ftp: ftplib.FTP | None = None

    @classmethod
    def from_uri(cls, uri: str) -> FtpStorage:
        """Create connector from URI: ftp://user:pass@host:port/path"""
        parsed = urlparse(uri)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 21,
            username=parsed.username or "anonymous",
            password=parsed.password or "anonymous@",
            base_dir=parsed.path.lstrip("/"),
        )

    @property
    def scheme(self) -> str:
        return "ftp"

    def authenticate(self) -> None:
        ftp_client: ftplib.FTP
        if self.use_tls:
            ftp_client = ftplib.FTP_TLS()
        else:
            ftp_client = ftplib.FTP()

        ftp_client.connect(host=self.host, port=self.port, timeout=10)
        ftp_client.login(user=self.username, passwd=self.password)
        ftp_client.set_pasv(True)
        if self.use_tls and isinstance(ftp_client, ftplib.FTP_TLS):
            ftp_client.prot_p()
        self._ftp = ftp_client

    def _get_ftp(self) -> ftplib.FTP:
        if self._ftp is None:
            self.authenticate()
        assert self._ftp is not None
        return self._ftp

    def _resolve(self, remote_path: str) -> str:
        clean = remote_path.lstrip("/").replace("ftp://", "")
        if self.base_dir:
            return f"/{self.base_dir}/{clean}"
        return f"/{clean}"

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        ftp = self._get_ftp()
        full_path = self._resolve(remote_path)
        ftp.storbinary(f"STOR {full_path}", stream)
        return f"ftp://{self.host}:{self.port}{full_path}"

    def download(self, remote_path: str) -> BinaryIO:
        ftp = self._get_ftp()
        full_path = self._resolve(remote_path)
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {full_path}", buf.write)
        buf.seek(0)
        return buf

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        ftp = self._get_ftp()
        full_path = (
            self._resolve(prefix) if prefix else (f"/{self.base_dir}" if self.base_dir else "/")
        )
        results: list[StorageFileInfo] = []
        lines: list[str] = []
        try:
            ftp.retrlines(f"NLST {full_path}", lines.append)
            for item in lines:
                name = item.rsplit("/", 1)[-1]
                size = 0
                try:
                    size = ftp.size(f"{full_path}/{name}".replace("//", "/")) or 0
                except Exception:
                    pass
                results.append(
                    StorageFileInfo(
                        path=f"{prefix}/{name}".strip("/"),
                        size_bytes=size,
                        modified_at=datetime.now(UTC),
                        is_dir=False,
                    )
                )
        except Exception:
            pass
        return results

    def delete(self, remote_path: str) -> bool:
        ftp = self._get_ftp()
        full_path = self._resolve(remote_path)
        try:
            ftp.delete(full_path)
            return True
        except Exception:
            return False

    def stat(self, remote_path: str) -> StorageFileInfo:
        ftp = self._get_ftp()
        full_path = self._resolve(remote_path)
        try:
            size = ftp.size(full_path)
            return StorageFileInfo(
                path=remote_path.lstrip("/"),
                size_bytes=size or 0,
                modified_at=datetime.now(UTC),
                is_dir=False,
            )
        except Exception as e:
            raise FileNotFoundError(f"FTP object not found: {remote_path}") from e

    def exists(self, remote_path: str) -> bool:
        try:
            self.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def move(self, src: str, dst: str) -> bool:
        ftp = self._get_ftp()
        ftp.rename(self._resolve(src), self._resolve(dst))
        return True

    def mkdir(self, path: str) -> None:
        ftp = self._get_ftp()
        ftp.mkd(self._resolve(path))

    def close(self) -> None:
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                self._ftp.close()
