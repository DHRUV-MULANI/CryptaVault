"""Crypto-agile container framing for CryptaVault.

A container is ``header + chunks + trailer``:

- Header: magic ``CVV2``, a length-prefixed JSON document describing the file and
  the exact algorithms (with stable wire identifiers) required to open it.
- Chunks: per-chunk AEAD records produced by :mod:`cryptavault.pipeline.chunked_encryption`.
- Trailer: magic ``CVT1``, a length-prefixed JSON document holding the chunk count,
  Merkle root, and optional signature over the header digest and Merkle root.

Because algorithm identity is persisted per file, old files remain decryptable
after defaults change, and unknown algorithms fail closed instead of silently
falling back to a weaker primitive.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import Any, BinaryIO

CONTAINER_MAGIC = b"CVV2"
LEGACY_CONTAINER_MAGIC = b"CVV1"
TRAILER_MAGIC = b"CVT1"

MAX_FRAME_BYTES = 1 * 1024 * 1024
REQUIRED_FAMILIES = ("symmetric", "hash", "signature", "kem", "kdf")


class ContainerError(Exception):
    """Base exception for container framing failures."""


class UnsupportedContainerVersionError(ContainerError):
    """Raised when a container uses an unknown or unsupported version."""


class ContainerIntegrityError(ContainerError):
    """Raised when container metadata is malformed or inconsistent."""


@dataclass(frozen=True)
class AlgorithmBinding:
    """Persisted identity of one algorithm used by a container."""

    family: str
    algorithm_id: str
    wire_id: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "algorithm_id": self.algorithm_id,
            "wire_id": self.wire_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlgorithmBinding:
        try:
            binding = cls(
                family=str(data["family"]),
                algorithm_id=str(data["algorithm_id"]),
                wire_id=int(data["wire_id"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ContainerIntegrityError(f"Malformed algorithm binding: {data!r}") from exc
        if not binding.algorithm_id or not 0 <= binding.wire_id <= 0xFFFF:
            raise ContainerIntegrityError(f"Invalid algorithm binding: {data!r}")
        return binding


@dataclass(frozen=True)
class ContainerHeader:
    """File metadata and algorithm bindings required to open a container."""

    file_id: str
    profile: str
    compression: str | None
    chunk_size_bytes: int
    multi_layer: bool
    algorithms: dict[str, AlgorithmBinding]
    version: int = 2

    def binding(self, family: str) -> AlgorithmBinding:
        """Return the binding for a family, failing closed when absent."""
        try:
            return self.algorithms[family]
        except KeyError as exc:
            raise ContainerIntegrityError(
                f"Container header is missing the '{family}' algorithm binding"
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "file_id": self.file_id,
            "profile": self.profile,
            "compression": self.compression,
            "chunk_size_bytes": self.chunk_size_bytes,
            "multi_layer": self.multi_layer,
            "algorithms": {name: binding.to_dict() for name, binding in self.algorithms.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContainerHeader:
        version = int(data.get("version", 0))
        if version != 2:
            raise UnsupportedContainerVersionError(
                f"Unsupported container header version: {version}"
            )
        raw_algorithms = data.get("algorithms")
        if not isinstance(raw_algorithms, dict):
            raise ContainerIntegrityError("Container header has no algorithm bindings")
        algorithms = {
            str(name): AlgorithmBinding.from_dict(binding)
            for name, binding in raw_algorithms.items()
        }
        for family in REQUIRED_FAMILIES:
            if family not in algorithms:
                raise ContainerIntegrityError(
                    f"Container header is missing the '{family}' algorithm binding"
                )
        wire_ids = [binding.wire_id for binding in algorithms.values()]
        if len(set(wire_ids)) != len(wire_ids):
            raise ContainerIntegrityError("Container header reuses an algorithm wire id")
        header = cls(
            file_id=str(data["file_id"]),
            profile=str(data["profile"]),
            compression=data.get("compression"),
            chunk_size_bytes=int(data["chunk_size_bytes"]),
            multi_layer=bool(data["multi_layer"]),
            algorithms=algorithms,
            version=version,
        )
        if header.chunk_size_bytes <= 0:
            raise ContainerIntegrityError("Container chunk size must be positive")
        return header


@dataclass(frozen=True)
class ContainerTrailer:
    """Integrity metadata written after the final chunk."""

    chunk_count: int
    merkle_root_hex: str
    signature_hex: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_count": self.chunk_count,
            "merkle_root_hex": self.merkle_root_hex,
            "signature_hex": self.signature_hex,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContainerTrailer:
        try:
            trailer = cls(
                chunk_count=int(data["chunk_count"]),
                merkle_root_hex=str(data["merkle_root_hex"]),
                signature_hex=str(data.get("signature_hex", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ContainerIntegrityError(f"Malformed container trailer: {data!r}") from exc
        if trailer.chunk_count < 0:
            raise ContainerIntegrityError("Container chunk count cannot be negative")
        try:
            bytes.fromhex(trailer.merkle_root_hex)
            if trailer.signature_hex:
                bytes.fromhex(trailer.signature_hex)
        except ValueError as exc:
            raise ContainerIntegrityError("Container trailer contains invalid hex") from exc
        return trailer


def _encode_json_frame(magic: bytes, payload: dict[str, Any]) -> bytes:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_FRAME_BYTES:
        raise ContainerError(f"Metadata frame exceeds {MAX_FRAME_BYTES} bytes")
    return magic + struct.pack(">I", len(encoded)) + encoded


def _read_json_frame(stream: BinaryIO, magic: bytes) -> dict[str, Any]:
    length_bytes = stream.read(4)
    if len(length_bytes) < 4:
        raise ContainerIntegrityError("Container metadata frame is truncated")
    (length,) = struct.unpack(">I", length_bytes)
    if length == 0 or length > MAX_FRAME_BYTES:
        raise ContainerIntegrityError(f"Invalid container metadata length: {length}")
    payload = stream.read(length)
    if len(payload) < length:
        raise ContainerIntegrityError("Container metadata frame is truncated")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContainerIntegrityError("Container metadata is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ContainerIntegrityError("Container metadata must be a JSON object")
    return data


def encode_header(header: ContainerHeader) -> bytes:
    """Serialize a header frame deterministically."""
    return _encode_json_frame(CONTAINER_MAGIC, header.to_dict())


def write_header(stream: BinaryIO, header: ContainerHeader) -> bytes:
    """Write a header frame and return the exact bytes written."""
    frame = encode_header(header)
    stream.write(frame)
    return frame


def read_header(stream: BinaryIO) -> ContainerHeader:
    """Read a ``CVV2`` header frame from the current stream position."""
    magic = stream.read(4)
    if magic != CONTAINER_MAGIC:
        raise UnsupportedContainerVersionError(
            f"Expected container magic {CONTAINER_MAGIC!r}, got {magic!r}"
        )
    return ContainerHeader.from_dict(_read_json_frame(stream, magic))


def read_header_body(stream: BinaryIO) -> ContainerHeader:
    """Read a header frame after the magic bytes have already been consumed."""
    return ContainerHeader.from_dict(_read_json_frame(stream, CONTAINER_MAGIC))


def encode_trailer(trailer: ContainerTrailer) -> bytes:
    """Serialize a trailer frame deterministically."""
    return _encode_json_frame(TRAILER_MAGIC, trailer.to_dict())


def write_trailer(stream: BinaryIO, trailer: ContainerTrailer) -> bytes:
    """Write a trailer frame and return the exact bytes written."""
    frame = encode_trailer(trailer)
    stream.write(frame)
    return frame


def read_trailer(stream: BinaryIO) -> ContainerTrailer:
    """Read a ``CVT1`` trailer frame from the current stream position."""
    magic = stream.read(4)
    if magic != TRAILER_MAGIC:
        raise ContainerIntegrityError(
            "Container is missing its integrity trailer; the file may be truncated or stripped"
        )
    return ContainerTrailer.from_dict(_read_json_frame(stream, magic))


__all__ = [
    "CONTAINER_MAGIC",
    "LEGACY_CONTAINER_MAGIC",
    "REQUIRED_FAMILIES",
    "TRAILER_MAGIC",
    "AlgorithmBinding",
    "ContainerError",
    "ContainerHeader",
    "ContainerIntegrityError",
    "ContainerTrailer",
    "UnsupportedContainerVersionError",
    "encode_header",
    "encode_trailer",
    "read_header",
    "read_header_body",
    "read_trailer",
    "write_header",
    "write_trailer",
]
