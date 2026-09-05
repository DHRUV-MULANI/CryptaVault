"""CryptaVault Plugin Architecture & Component Registries.

Defines the Abstract Base Classes (ABCs) and typed registries enabling dynamic
extension of storage backends, cryptographic primitives, compression algorithms,
and AI policy providers.
"""

from __future__ import annotations

import importlib.metadata
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO, ClassVar, Generic, TypeVar

T = TypeVar("T")


class PluginError(Exception):
    """Base exception for plugin-related errors."""


class PluginRegistrationError(PluginError):
    """Raised when registering an invalid or duplicate plugin."""


class PluginNotFoundError(PluginError):
    """Raised when requesting an unregistered plugin name."""


# ====================================================================
# Data Transfer Models for Storage Plugins
# ====================================================================


@dataclass(frozen=True)
class RemoteFile:
    """Metadata representing a file or directory in a remote storage backend."""

    path: str
    size_bytes: int
    is_dir: bool = False
    modified_at: datetime | None = None


@dataclass(frozen=True)
class RemoteStat:
    """Status metadata for a remote resource."""

    path: str
    size_bytes: int
    is_dir: bool = False
    modified_at: datetime | None = None


# ====================================================================
# Abstract Base Classes (Plugin Interfaces)
# ====================================================================


class StorageConnector(ABC):
    """Interface for cloud and local storage backend connectors."""

    name: ClassVar[str]

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the storage provider."""
        ...

    @abstractmethod
    def upload(self, stream: BinaryIO, remote_path: str) -> None:
        """Upload a binary stream to the specified remote path."""
        ...

    @abstractmethod
    def download(self, remote_path: str) -> BinaryIO:
        """Download a remote resource as a binary stream."""
        ...

    @abstractmethod
    def list(self, prefix: str = "") -> list[RemoteFile]:
        """List files and folders matching the prefix."""
        ...

    @abstractmethod
    def delete(self, remote_path: str) -> None:
        """Delete a remote file or empty directory."""
        ...

    @abstractmethod
    def stat(self, remote_path: str) -> RemoteStat:
        """Fetch metadata for a remote path."""
        ...

    @abstractmethod
    def move(self, src: str, dst: str) -> None:
        """Move or rename a remote resource."""
        ...

    @abstractmethod
    def mkdir(self, path: str) -> None:
        """Create a remote directory."""
        ...


class CompressionAlgorithm(ABC):
    """Interface for stream and chunk compression algorithms."""

    name: ClassVar[str]

    @abstractmethod
    def compress(self, stream: BinaryIO) -> BinaryIO:
        """Compress a stream of bytes."""
        ...

    @abstractmethod
    def decompress(self, stream: BinaryIO) -> BinaryIO:
        """Decompress a stream of bytes."""
        ...


class EncryptionAlgorithm(ABC):
    """Interface for authenticated symmetric encryption primitives."""

    name: ClassVar[str]
    key_size_bytes: ClassVar[int]
    nonce_size_bytes: ClassVar[int]

    @abstractmethod
    def encrypt(self, key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
        """Encrypt plaintext with associated data producing ciphertext and tag."""
        ...

    @abstractmethod
    def decrypt(self, key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> bytes:
        """Decrypt ciphertext and authenticate tag against associated data."""
        ...


class StreamingHash(ABC):
    """Incremental hashing state for large streams."""

    @abstractmethod
    def update(self, data: bytes) -> None:
        """Feed additional bytes into the hash computation."""
        ...

    @abstractmethod
    def digest(self) -> bytes:
        """Return the raw binary digest."""
        ...

    @abstractmethod
    def hexdigest(self) -> str:
        """Return the hexadecimal digest string."""
        ...


class HashAlgorithm(ABC):
    """Interface for cryptographic hash algorithms."""

    name: ClassVar[str]

    @abstractmethod
    def digest(self, data: bytes, size: int | None = None) -> bytes:
        """Compute one-shot cryptographic hash."""
        ...

    @abstractmethod
    def streaming(self) -> StreamingHash:
        """Initialize an incremental streaming hash object."""
        ...


class SignatureAlgorithm(ABC):
    """Interface for digital signature schemes (classical & post-quantum)."""

    name: ClassVar[str]

    @abstractmethod
    def keypair(self) -> tuple[bytes, bytes]:
        """Generate (public_key, private_key) byte tuple."""
        ...

    @abstractmethod
    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign a message using the private key."""
        ...

    @abstractmethod
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify the signature against the message and public key."""
        ...


class KemAlgorithm(ABC):
    """Interface for Key Encapsulation Mechanisms (e.g. ML-KEM / Kyber)."""

    name: ClassVar[str]

    @abstractmethod
    def keypair(self) -> tuple[bytes, bytes]:
        """Generate (public_key, secret_key) byte tuple."""
        ...

    @abstractmethod
    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        """Encapsulate a shared secret, returning (shared_secret, ciphertext)."""
        ...

    @abstractmethod
    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate ciphertext to recover the shared secret."""
        ...


class KdfAlgorithm(ABC):
    """Interface for Key Derivation Functions (Argon2id, HKDF)."""

    name: ClassVar[str]

    @abstractmethod
    def derive(self, password: bytes, salt: bytes, length: int, **params: Any) -> bytes:
        """Derive a key of requested length from password and salt."""
        ...


class AiProvider(ABC):
    """Interface for AI security policy recommendations and assistance."""

    name: ClassVar[str]

    @abstractmethod
    def recommend(self, file_metadata: dict[str, Any]) -> dict[str, Any]:
        """Recommend adaptive security profile parameters based on metadata."""
        ...

    @abstractmethod
    def explain(self, concept: str) -> str:
        """Provide zero-knowledge explanation of cryptographic concepts."""
        ...


# ====================================================================
# Typed Registry Container
# ====================================================================


class PluginRegistry(Generic[T]):
    """Thread-safe typed registry for a specific plugin contract."""

    def __init__(self, contract_name: str, expected_base: type[Any]) -> None:
        self.contract_name = contract_name
        self.expected_base = expected_base
        self._plugins: dict[str, type[T]] = {}

    def register(self, name: str, cls: type[T]) -> type[T]:
        """Register a plugin class under a unique normalized name."""
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise PluginRegistrationError("Plugin name cannot be empty")
        if not issubclass(cls, self.expected_base):
            raise PluginRegistrationError(
                f"Class {cls.__name__} does not implement {self.expected_base.__name__}"
            )
        if normalized_name in self._plugins:
            raise PluginRegistrationError(
                f"Plugin '{normalized_name}' is already registered in {self.contract_name}"
            )
        self._plugins[normalized_name] = cls
        return cls

    def get(self, name: str) -> type[T]:
        """Retrieve a registered plugin class by name."""
        normalized_name = name.strip().lower()
        if normalized_name not in self._plugins:
            raise PluginNotFoundError(
                f"No plugin named '{normalized_name}' found in {self.contract_name} registry. "
                f"Available: {list(self._plugins.keys())}"
            )
        return self._plugins[normalized_name]

    def list_available(self) -> list[str]:
        """Return list of registered plugin identifiers."""
        return sorted(self._plugins.keys())

    def clear(self) -> None:
        """Clear registered plugins (primarily for unit tests)."""
        self._plugins.clear()


# ====================================================================
# Global Plugin Registries
# ====================================================================

storage_registry = PluginRegistry[StorageConnector]("StorageConnector", StorageConnector)
compression_registry = PluginRegistry[CompressionAlgorithm](
    "CompressionAlgorithm", CompressionAlgorithm
)
encryption_registry = PluginRegistry[EncryptionAlgorithm](
    "EncryptionAlgorithm", EncryptionAlgorithm
)
hash_registry = PluginRegistry[HashAlgorithm]("HashAlgorithm", HashAlgorithm)
signature_registry = PluginRegistry[SignatureAlgorithm]("SignatureAlgorithm", SignatureAlgorithm)
kem_registry = PluginRegistry[KemAlgorithm]("KemAlgorithm", KemAlgorithm)
kdf_registry = PluginRegistry[KdfAlgorithm]("KdfAlgorithm", KdfAlgorithm)
ai_registry = PluginRegistry[AiProvider]("AiProvider", AiProvider)


# ====================================================================
# Registration Decorators
# ====================================================================


def register_storage(name: str) -> Callable[[type[StorageConnector]], type[StorageConnector]]:
    """Decorator to register a StorageConnector plugin."""

    def decorator(cls: type[StorageConnector]) -> type[StorageConnector]:
        return storage_registry.register(name, cls)

    return decorator


def register_compression(
    name: str,
) -> Callable[[type[CompressionAlgorithm]], type[CompressionAlgorithm]]:
    """Decorator to register a CompressionAlgorithm plugin."""

    def decorator(cls: type[CompressionAlgorithm]) -> type[CompressionAlgorithm]:
        return compression_registry.register(name, cls)

    return decorator


def register_encryption(
    name: str,
) -> Callable[[type[EncryptionAlgorithm]], type[EncryptionAlgorithm]]:
    """Decorator to register an EncryptionAlgorithm plugin."""

    def decorator(cls: type[EncryptionAlgorithm]) -> type[EncryptionAlgorithm]:
        return encryption_registry.register(name, cls)

    return decorator


def register_hash(name: str) -> Callable[[type[HashAlgorithm]], type[HashAlgorithm]]:
    """Decorator to register a HashAlgorithm plugin."""

    def decorator(cls: type[HashAlgorithm]) -> type[HashAlgorithm]:
        return hash_registry.register(name, cls)

    return decorator


def register_signature(name: str) -> Callable[[type[SignatureAlgorithm]], type[SignatureAlgorithm]]:
    """Decorator to register a SignatureAlgorithm plugin."""

    def decorator(cls: type[SignatureAlgorithm]) -> type[SignatureAlgorithm]:
        return signature_registry.register(name, cls)

    return decorator


def register_kem(name: str) -> Callable[[type[KemAlgorithm]], type[KemAlgorithm]]:
    """Decorator to register a KemAlgorithm plugin."""

    def decorator(cls: type[KemAlgorithm]) -> type[KemAlgorithm]:
        return kem_registry.register(name, cls)

    return decorator


def register_kdf(name: str) -> Callable[[type[KdfAlgorithm]], type[KdfAlgorithm]]:
    """Decorator to register a KdfAlgorithm plugin."""

    def decorator(cls: type[KdfAlgorithm]) -> type[KdfAlgorithm]:
        return kdf_registry.register(name, cls)

    return decorator


def register_ai(name: str) -> Callable[[type[AiProvider]], type[AiProvider]]:
    """Decorator to register an AiProvider plugin."""

    def decorator(cls: type[AiProvider]) -> type[AiProvider]:
        return ai_registry.register(name, cls)

    return decorator


import logging

logger = logging.getLogger(__name__)


def discover_plugins(group_name: str = "cryptavault.plugins") -> int:
    """Discover and load external plugins declared via entry points."""
    loaded = 0
    try:
        entry_points = importlib.metadata.entry_points()
        group: Any = getattr(
            entry_points, "select", lambda **kwargs: entry_points.get(group_name, [])
        )(group=group_name)
        for ep in group:
            try:
                ep.load()
                loaded += 1
            except (ImportError, AttributeError, TypeError, KeyError) as err:
                logger.debug("Failed to load plugin entry point %s: %s", ep.name, err)
    except (
        importlib.metadata.PackageNotFoundError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    ) as err:
        logger.debug("Error querying entry points for %s: %s", group_name, err)
    return loaded
