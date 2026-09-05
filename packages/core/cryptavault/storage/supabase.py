"""Supabase Storage connector for cloud-backed zero-knowledge ciphertext vaults.

Stores encrypted chunks and manifests in Supabase Storage buckets (e.g. 'vaults').
Zero-Knowledge Invariant: The Supabase bucket only ever receives encrypted ciphertext.
"""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime
from typing import Any, BinaryIO

from cryptavault.storage.base import StorageConnector, StorageFileInfo

try:
    from supabase import Client, create_client
except ImportError:
    create_client = None  # type: ignore[assignment]
    Client = None  # type: ignore[assignment, misc]


class SupabaseStorage(StorageConnector):
    """Storage connector interfacing with Supabase Object Storage."""

    def __init__(
        self,
        bucket_name: str = "vaults",
        url: str | None = None,
        key: str | None = None,
        client: Any = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.url = url or os.getenv("SUPABASE_URL", "")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

        if client is not None:
            self._client = client
        elif create_client is not None and self.url and self.key:
            self._client = create_client(self.url, self.key)
        else:
            self._client = None

    @property
    def scheme(self) -> str:
        return "supabase"

    def authenticate(self) -> None:
        if self._client is None:
            if not self.url or not self.key:
                raise ConnectionError("Missing SUPABASE_URL or SUPABASE_KEY credentials.")
            if create_client is None:
                raise ImportError(
                    "supabase package is not installed. Install with `uv pip install supabase`."
                )
            self._client = create_client(self.url, self.key)

        # Probe bucket availability
        try:
            self._client.storage.get_bucket(self.bucket_name)
        except Exception:
            # If bucket does not exist, try creating it as a private bucket
            try:
                self._client.storage.create_bucket(self.bucket_name, options={"public": False})
            except Exception:
                # If cannot create or already exists, proceed
                pass

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        clean_path = remote_path.lstrip("/").replace("supabase://", "")
        if self._client is None:
            self.authenticate()

        data = stream.read()
        self._client.storage.from_(self.bucket_name).upload(
            path=clean_path,
            file=data,
            file_options={"upsert": "true", "content-type": "application/octet-stream"},
        )
        return f"supabase://{self.bucket_name}/{clean_path}"

    def download(self, remote_path: str) -> BinaryIO:
        clean_path = (
            remote_path.lstrip("/")
            .replace(f"supabase://{self.bucket_name}/", "")
            .replace("supabase://", "")
        )
        if self._client is None:
            self.authenticate()

        res_bytes = self._client.storage.from_(self.bucket_name).download(clean_path)
        return io.BytesIO(res_bytes)

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        clean_prefix = prefix.lstrip("/").replace("supabase://", "")
        if self._client is None:
            self.authenticate()

        objects = self._client.storage.from_(self.bucket_name).list(clean_prefix)
        results: list[StorageFileInfo] = []
        for obj in objects:
            name = obj.get("name", "")
            meta = obj.get("metadata", {})
            size = meta.get("size", 0) if meta else 0
            created_at_str = obj.get("created_at") or datetime.now(UTC).isoformat()
            try:
                dt = datetime.fromisoformat(created_at_str)
            except Exception:
                dt = datetime.now(UTC)

            full_path = f"{clean_prefix}/{name}".lstrip("/")
            results.append(
                StorageFileInfo(
                    path=full_path,
                    size_bytes=size,
                    modified_at=dt,
                    is_dir=obj.get("id") is None and not meta,
                    etag=meta.get("eTag") if meta else None,
                )
            )
        return results

    def delete(self, remote_path: str) -> bool:
        clean_path = (
            remote_path.lstrip("/")
            .replace(f"supabase://{self.bucket_name}/", "")
            .replace("supabase://", "")
        )
        if self._client is None:
            self.authenticate()

        self._client.storage.from_(self.bucket_name).remove([clean_path])
        return True

    def stat(self, remote_path: str) -> StorageFileInfo:
        clean_path = (
            remote_path.lstrip("/")
            .replace(f"supabase://{self.bucket_name}/", "")
            .replace("supabase://", "")
        )
        dir_path, _, filename = clean_path.rpartition("/")
        files = self.list(dir_path)
        for f in files:
            if f.path == clean_path or f.path.endswith(filename):
                return f
        raise FileNotFoundError(f"Supabase storage object not found: {remote_path}")

    def exists(self, remote_path: str) -> bool:
        try:
            self.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def move(self, src: str, dst: str) -> bool:
        clean_src = (
            src.lstrip("/")
            .replace(f"supabase://{self.bucket_name}/", "")
            .replace("supabase://", "")
        )
        clean_dst = (
            dst.lstrip("/")
            .replace(f"supabase://{self.bucket_name}/", "")
            .replace("supabase://", "")
        )
        if self._client is None:
            self.authenticate()
        self._client.storage.from_(self.bucket_name).move(clean_src, clean_dst)
        return True

    def mkdir(self, path: str) -> None:
        pass
