# Plugin Development Guide

CryptaVault uses a typed registry and Abstract Base Class (ABC) plugin architecture to allow extensions (new storage connectors, post-quantum KEMs, signature schemes, compression algorithms, and AI providers) without modifying core library code.

---

## 1. Available Plugin Registries

| Registry | Base Class | Decorator | Purpose |
| :--- | :--- | :--- | :--- |
| `storage_registry` | `StorageConnector` | `@register_storage("name")` | Cloud & on-prem storage targets (GDrive, OneDrive, S3, SFTP) |
| `compression_registry` | `CompressionAlgorithm` | `@register_compression("name")` | Chunk and stream compressors (Zstandard, Brotli, LZMA) |
| `encryption_registry` | `EncryptionAlgorithm` | `@register_encryption("name")` | AEAD ciphers (AES-256-GCM, ChaCha20-Poly1305) |
| `hash_registry` | `HashAlgorithm` | `@register_hash("name")` | Hashes and MACs (BLAKE3, SHA-384, KMAC) |
| `signature_registry` | `SignatureAlgorithm` | `@register_signature("name")` | Digital signatures (Ed25519, ECDSA, ML-DSA/Dilithium) |
| `kem_registry` | `KemAlgorithm` | `@register_kem("name")` | Key encapsulation (ML-KEM/Kyber768, Classic McEliece) |
| `kdf_registry` | `KdfAlgorithm` | `@register_kdf("name")` | Password & key derivation (Argon2id, HKDF) |
| `ai_registry` | `AiProvider` | `@register_ai("name")` | AI policy and recommendation engines |

---

## 2. Implementing a Plugin

To create a new plugin, subclass the relevant interface and register it:

```python
from io import BytesIO
from typing import BinaryIO
from cryptavault.plugins.registry import StorageConnector, register_storage, RemoteFile, RemoteStat

@register_storage("my_custom_store")
class MyCustomStorage(StorageConnector):
    name = "my_custom_store"

    def authenticate(self) -> None:
        # Initialize client authentication
        ...

    def upload(self, stream: BinaryIO, remote_path: str) -> None:
        # Stream ciphertext chunk to storage target
        ...

    def download(self, remote_path: str) -> BinaryIO:
        # Fetch ciphertext chunk
        ...

    def list(self, prefix: str = "") -> list[RemoteFile]:
        ...

    def delete(self, remote_path: str) -> None:
        ...

    def stat(self, remote_path: str) -> RemoteStat:
        ...

    def move(self, src: str, dst: str) -> None:
        ...

    def mkdir(self, path: str) -> None:
        ...
```

---

## 3. External Package Discovery via Entry Points

Third-party packages can register plugins automatically by declaring entry points in their `pyproject.toml`:

```toml
[project.entry-points."cryptavault.plugins"]
my_custom_store = "my_package.plugins:MyCustomStorage"
```

When CryptaVault boots, calling `discover_plugins()` dynamically loads all registered entry-point plugins without requiring explicit core imports.
