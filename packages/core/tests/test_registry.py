"""Unit tests for CryptaVault plugin registry and ABC contracts."""

from typing import BinaryIO

import pytest
from cryptavault.plugins.registry import (
    CompressionAlgorithm,
    EncryptionAlgorithm,
    PluginNotFoundError,
    PluginRegistrationError,
    PluginRegistry,
    StorageConnector,
    compression_registry,
    discover_plugins,
    register_compression,
)


class DummyStorage(StorageConnector):
    name = "dummy_storage"

    def authenticate(self) -> None:
        pass

    def upload(self, stream: BinaryIO, remote_path: str) -> None:
        pass

    def download(self, remote_path: str) -> BinaryIO:
        raise NotImplementedError

    def list(self, prefix: str = ""):
        return []

    def delete(self, remote_path: str) -> None:
        pass

    def stat(self, remote_path: str):
        raise NotImplementedError

    def move(self, src: str, dst: str) -> None:
        pass

    def mkdir(self, path: str) -> None:
        pass


class DummyCompression(CompressionAlgorithm):
    name = "dummy_zstd"

    def compress(self, stream: BinaryIO) -> BinaryIO:
        return stream

    def decompress(self, stream: BinaryIO) -> BinaryIO:
        return stream


class DummyEncryption(EncryptionAlgorithm):
    name = "dummy_aes"
    key_size_bytes = 32
    nonce_size_bytes = 12

    def encrypt(self, key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
        return plaintext

    def decrypt(self, key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> bytes:
        return ciphertext


def test_registry_registration_and_retrieval() -> None:
    """Ensure valid plugins can be registered and retrieved."""
    test_reg = PluginRegistry[StorageConnector]("TestStorage", StorageConnector)
    test_reg.register("mock_storage", DummyStorage)

    assert "mock_storage" in test_reg.list_available()
    retrieved = test_reg.get("mock_storage")
    assert retrieved is DummyStorage
    assert issubclass(retrieved, StorageConnector)


def test_registry_case_insensitivity() -> None:
    """Ensure plugin names are normalized case-insensitively."""
    test_reg = PluginRegistry[StorageConnector]("TestStorage", StorageConnector)
    test_reg.register("FastStorage", DummyStorage)

    assert test_reg.get("faststorage") is DummyStorage
    assert test_reg.get("FASTSTORAGE") is DummyStorage


def test_registry_duplicate_registration_raises() -> None:
    """Ensure registering a duplicate name raises PluginRegistrationError."""
    test_reg = PluginRegistry[StorageConnector]("TestStorage", StorageConnector)
    test_reg.register("storage_a", DummyStorage)

    with pytest.raises(PluginRegistrationError, match="already registered"):
        test_reg.register("storage_a", DummyStorage)


def test_registry_invalid_subclass_raises() -> None:
    """Ensure registering a class that does not implement the contract raises an error."""
    test_reg = PluginRegistry[StorageConnector]("TestStorage", StorageConnector)

    class NotAStorage:
        pass

    with pytest.raises(PluginRegistrationError, match="does not implement"):
        test_reg.register("invalid", NotAStorage)  # type: ignore[arg-type]


def test_registry_not_found_raises() -> None:
    """Ensure looking up an unregistered plugin raises PluginNotFoundError."""
    test_reg = PluginRegistry[StorageConnector]("TestStorage", StorageConnector)
    with pytest.raises(PluginNotFoundError, match="No plugin named 'unknown'"):
        test_reg.get("unknown")


def test_decorators() -> None:
    """Ensure decorator syntax properly registers into global registries."""
    try:

        @register_compression("dummy_test_comp")
        class DecoratedComp(DummyCompression):
            pass

        assert compression_registry.get("dummy_test_comp") is DecoratedComp
    finally:
        if "dummy_test_comp" in compression_registry.list_available():
            del compression_registry._plugins["dummy_test_comp"]


def test_discover_plugins_smoke() -> None:
    """Smoke test entry-point discovery function."""
    count = discover_plugins("cryptavault.plugins")
    assert isinstance(count, int)
