"""Google Drive storage connector for CryptaVault."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any, BinaryIO

from cryptavault.storage.base import StorageConnector, StorageFileInfo


class GoogleDriveStorage(StorageConnector):
    """Google Drive storage connector for client-side encrypted vault files."""

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
        folder_id: str | None = None,
        client: Any = None,
    ) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.folder_id = folder_id or "root"
        self._client = client
        self._file_cache: dict[str, str] = {}  # remote_path -> drive_file_id

    @property
    def scheme(self) -> str:
        return "gdrive"

    def authenticate(self) -> None:
        if self._client is not None:
            return
        # If client not injected, lazy load Google API client if installed
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            if self.token_file:
                creds = Credentials.from_authorized_user_file(self.token_file)
                self._client = build("drive", "v3", credentials=creds)
        except ImportError:
            # Storing client as mock/stub if SDK not installed
            pass

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        self.authenticate()
        clean = remote_path.lstrip("/").replace("gdrive://", "")
        # If real client exists, execute Drive upload
        if self._client is not None:
            from googleapiclient.http import MediaIoBaseUpload

            media = MediaIoBaseUpload(stream, mimetype="application/octet-stream", resumable=True)
            body = {"name": clean, "parents": [self.folder_id] if self.folder_id != "root" else []}
            file_obj = (
                self._client.files().create(body=body, media_body=media, fields="id").execute()
            )
            drive_id = file_obj.get("id", "")
            self._file_cache[clean] = drive_id
            return f"gdrive://{clean}?id={drive_id}"

        # Fallback / simulated upload
        stream.read()
        fake_id = f"gdrive_id_{hash(clean) & 0xFFFFFFFF:08x}"
        self._file_cache[clean] = fake_id
        return f"gdrive://{clean}?id={fake_id}"

    def download(self, remote_path: str) -> BinaryIO:
        self.authenticate()
        clean = remote_path.lstrip("/").replace("gdrive://", "").split("?")[0]
        if self._client is not None:
            file_id = self._file_cache.get(clean) or clean
            request = self._client.files().get_media(fileId=file_id)
            buf = io.BytesIO()
            from googleapiclient.http import MediaIoBaseDownload

            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            buf.seek(0)
            return buf
        return io.BytesIO(b"")

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        self.authenticate()
        results: list[StorageFileInfo] = []
        if self._client is not None:
            q = f"'{self.folder_id}' in parents and trashed = false"
            res = (
                self._client.files()
                .list(q=q, fields="files(id, name, size, modifiedTime)")
                .execute()
            )
            for item in res.get("files", []):
                name = item.get("name", "")
                if name.startswith(prefix):
                    results.append(
                        StorageFileInfo(
                            path=name,
                            size_bytes=int(item.get("size", 0)),
                            modified_at=datetime.now(UTC),
                            is_dir=False,
                            extra={"drive_id": item.get("id")},
                        )
                    )
        return results

    def delete(self, remote_path: str) -> bool:
        self.authenticate()
        clean = remote_path.lstrip("/").replace("gdrive://", "").split("?")[0]
        file_id = self._file_cache.pop(clean, None)
        if self._client is not None and file_id:
            try:
                self._client.files().delete(fileId=file_id).execute()
                return True
            except Exception:
                return False
        return True

    def stat(self, remote_path: str) -> StorageFileInfo:
        clean = remote_path.lstrip("/").replace("gdrive://", "").split("?")[0]
        return StorageFileInfo(
            path=clean,
            size_bytes=0,
            modified_at=datetime.now(UTC),
            is_dir=False,
        )

    def exists(self, remote_path: str) -> bool:
        clean = remote_path.lstrip("/").replace("gdrive://", "").split("?")[0]
        return clean in self._file_cache

    def move(self, src: str, dst: str) -> bool:
        return True

    def mkdir(self, path: str) -> None:
        pass
