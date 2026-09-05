"""Storage URI auto-detection and connector registry for CryptaVault."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from cryptavault.storage.base import StorageConnector
from cryptavault.storage.cloud.dropbox import DropboxStorage
from cryptavault.storage.cloud.gdrive import GoogleDriveStorage
from cryptavault.storage.cloud.onedrive import OneDriveStorage
from cryptavault.storage.ftp import FtpStorage
from cryptavault.storage.local import LocalStorage
from cryptavault.storage.mock import MockStorage
from cryptavault.storage.sftp import SftpStorage
from cryptavault.storage.supabase import SupabaseStorage


def resolve_storage(uri_or_path: str) -> StorageConnector:
    """Auto-detects and instantiates the appropriate StorageConnector for a URI or local path.

    Supported URI patterns:
    - local:///path/to/storage or /path/to/storage or ./storage
    - mock://test-bucket
    - supabase://bucket_name
    - sftp://user:pass@host:port/path
    - ftp://user:pass@host:port/path
    - gdrive://folder_id
    - onedrive://folder_path
    - dropbox://folder_path
    """
    if "://" not in uri_or_path:
        # Plain filesystem path defaults to LocalStorage
        return LocalStorage(Path(uri_or_path))

    parsed = urlparse(uri_or_path)
    scheme = parsed.scheme.lower()

    if scheme in ("local", "file"):
        path = parsed.path
        # On windows or relative path handling
        if not path and parsed.netloc:
            path = parsed.netloc
        return LocalStorage(Path(path or "."))

    if scheme == "mock":
        return MockStorage(scheme="mock")

    if scheme == "supabase":
        bucket = parsed.netloc or (
            parsed.path.strip("/").split("/")[0] if parsed.path else "vaults"
        )
        return SupabaseStorage(bucket_name=bucket)

    if scheme == "sftp":
        return SftpStorage.from_uri(uri_or_path)

    if scheme in ("ftp", "ftps"):
        use_tls = scheme == "ftps"
        connector = FtpStorage.from_uri(uri_or_path)
        connector.use_tls = use_tls
        return connector

    if scheme in ("gdrive", "googledrive"):
        folder = parsed.netloc or parsed.path.strip("/")
        return GoogleDriveStorage(folder_id=folder or "root")

    if scheme == "onedrive":
        folder = parsed.netloc or parsed.path.strip("/")
        return OneDriveStorage(root_folder=folder or "CryptaVault")

    if scheme == "dropbox":
        return DropboxStorage()

    raise ValueError(f"Unsupported storage URI scheme: '{scheme}' (URI: {uri_or_path})")
