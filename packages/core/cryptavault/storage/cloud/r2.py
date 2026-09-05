"""Cloudflare R2 (S3-compatible) storage connector with zero egress fees and custom domain support.

Zero-Knowledge Invariant: Plaintext data and private encryption keys NEVER reach Cloudflare R2.
All payloads are chunked AEAD ciphertext envelopes (.vault) encrypted client-side.
"""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime
from typing import Any, BinaryIO
from urllib.parse import urlparse

from cryptavault.storage.base import StorageConnector, StorageFileInfo

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]
    ClientError = Exception  # type: ignore[assignment, misc]


class CloudflareR2Storage(StorageConnector):
    """Cloudflare R2 Object Storage connector via S3 API with custom domain and zero egress fees."""

    def __init__(
        self,
        bucket_name: str = "vaults",
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        custom_domain: str | None = None,
        endpoint_url: str | None = None,
        client: Any = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.account_id = account_id or os.getenv("CLOUDFLARE_R2_ACCOUNT_ID", "")
        self.access_key_id = access_key_id or os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
        self.secret_access_key = secret_access_key or os.getenv(
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY", ""
        )
        raw_domain = (
            custom_domain
            or os.getenv("CLOUDFLARE_R2_PUBLIC_DOMAIN")
            or os.getenv("CUSTOM_SHARE_DOMAIN")
            or ""
        )
        self.custom_domain: str = raw_domain.rstrip("/") if raw_domain else ""

        if endpoint_url:
            self.endpoint_url = endpoint_url
        elif self.account_id:
            self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
        else:
            self.endpoint_url = ""

        self._client = client

    @classmethod
    def from_uri(cls, uri: str) -> CloudflareR2Storage:
        """Parse r2://bucket_name/path or s3://bucket_name/path URI."""
        parsed = urlparse(uri)
        bucket = parsed.netloc or "vaults"
        return cls(bucket_name=bucket)

    @property
    def scheme(self) -> str:
        return "r2"

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        if boto3 is None:
            raise ImportError(
                "boto3 package is required for Cloudflare R2 storage. Install via `uv pip install boto3`."
            )

        if not self.endpoint_url or not self.access_key_id or not self.secret_access_key:
            raise ConnectionError(
                "Missing Cloudflare R2 credentials (CLOUDFLARE_R2_ACCOUNT_ID, ACCESS_KEY_ID, SECRET_ACCESS_KEY)."
            )

        self._client = boto3.client(
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name="auto",
            config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )
        return self._client

    def authenticate(self) -> None:
        client = self._get_client()
        try:
            client.head_bucket(Bucket=self.bucket_name)
        except Exception:
            # Attempt to create bucket if permitted
            try:
                client.create_bucket(Bucket=self.bucket_name)
            except Exception as exc:
                raise ConnectionError(
                    f"Failed to connect or create Cloudflare R2 bucket '{self.bucket_name}': {exc}"
                ) from exc

    def upload(self, stream: BinaryIO, remote_path: str, size: int | None = None) -> str:
        client = self._get_client()
        key = remote_path.lstrip("/")
        body = stream.read()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body,
            ContentType="application/octet-stream",
        )
        if self.custom_domain:
            return f"{self.custom_domain}/{key}"
        return f"r2://{self.bucket_name}/{key}"

    def download(self, remote_path: str) -> BinaryIO:
        client = self._get_client()
        key = remote_path.lstrip("/")
        try:
            response = client.get_object(Bucket=self.bucket_name, Key=key)
            return io.BytesIO(response["Body"].read())
        except Exception as exc:
            raise FileNotFoundError(f"File not found in R2: {remote_path}") from exc

    def list(self, prefix: str = "") -> list[StorageFileInfo]:
        client = self._get_client()
        clean_prefix = prefix.lstrip("/")
        try:
            res = client.list_objects_v2(Bucket=self.bucket_name, Prefix=clean_prefix)
            items: list[StorageFileInfo] = []
            for obj in res.get("Contents", []):
                items.append(
                    StorageFileInfo(
                        path=obj["Key"],
                        size_bytes=obj["Size"],
                        modified_at=obj.get("LastModified", datetime.now(UTC)),
                        is_dir=obj["Key"].endswith("/"),
                        etag=obj.get("ETag", "").strip('"'),
                    )
                )
            return items
        except Exception:
            return []

    def delete(self, remote_path: str) -> bool:
        client = self._get_client()
        key = remote_path.lstrip("/")
        try:
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def stat(self, remote_path: str) -> StorageFileInfo:
        client = self._get_client()
        key = remote_path.lstrip("/")
        try:
            head = client.head_object(Bucket=self.bucket_name, Key=key)
            return StorageFileInfo(
                path=key,
                size_bytes=head.get("ContentLength", 0),
                modified_at=head.get("LastModified", datetime.now(UTC)),
                is_dir=key.endswith("/"),
                etag=head.get("ETag", "").strip('"'),
            )
        except Exception as exc:
            raise FileNotFoundError(f"Object not found in R2: {remote_path}") from exc

    def exists(self, remote_path: str) -> bool:
        try:
            self.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def move(self, src: str, dst: str) -> bool:
        client = self._get_client()
        src_key = src.lstrip("/")
        dst_key = dst.lstrip("/")
        try:
            client.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": src_key},
                Key=dst_key,
            )
            client.delete_object(Bucket=self.bucket_name, Key=src_key)
            return True
        except Exception:
            return False

    def mkdir(self, path: str) -> None:
        """S3 is key-value based; ensure folder key exists with trailing slash."""
        client = self._get_client()
        clean = path.strip("/")
        if clean:
            folder_key = f"{clean}/"
            try:
                client.put_object(Bucket=self.bucket_name, Key=folder_key, Body=b"")
            except Exception:
                pass

    def get_public_url(self, remote_path: str) -> str:
        """Construct the custom domain public URL or R2 reference."""
        key = remote_path.lstrip("/")
        if self.custom_domain:
            return f"{self.custom_domain}/{key}"
        return f"r2://{self.bucket_name}/{key}"
