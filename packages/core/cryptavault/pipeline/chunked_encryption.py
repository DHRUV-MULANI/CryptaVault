"""Chunked Streaming AEAD Encryption and Decryption for CryptaVault.

Handles arbitrary file sizes without loading entire files into memory.
Enforces fail-closed authentication per chunk, chunk ordering verification,
and tamper prevention via Authenticated Associated Data (AAD).
"""

from __future__ import annotations

import io
import struct
from collections.abc import Generator
from dataclasses import dataclass
from typing import BinaryIO

from cryptavault.adaptive.engine import AdaptiveEngine, PipelineConfig
from cryptavault.crypto.symmetric import InvalidTagError


class StreamingPipelineError(Exception):
    """Base exception for streaming pipeline errors."""


class ChunkOutOfOrderError(StreamingPipelineError):
    """Raised when chunk index sequence is broken or skipped."""


class ChunkTruncationError(StreamingPipelineError):
    """Raised when a chunk stream terminates prematurely without the final marker."""


@dataclass(frozen=True)
class EncryptedChunk:
    """Represents a single authenticated encrypted chunk."""

    index: int
    is_final: bool
    nonce: bytes
    ciphertext_and_tag: bytes

    def serialize(self) -> bytes:
        """Wire format: [8-byte index][1-byte is_final][12-byte nonce][4-byte len][ciphertext+tag]."""
        header = struct.pack(
            ">Q?12sI", self.index, self.is_final, self.nonce, len(self.ciphertext_and_tag)
        )
        return header + self.ciphertext_and_tag

    @classmethod
    def read_from_stream(cls, stream: BinaryIO) -> EncryptedChunk | None:
        """Read and parse next chunk from binary stream. Returns None on clean EOF."""
        header_bytes = stream.read(25)  # 8 + 1 + 12 + 4 = 25 bytes
        if not header_bytes:
            return None
        if len(header_bytes) < 25:
            raise ChunkTruncationError(
                f"Incomplete chunk header: read {len(header_bytes)} bytes, expected 25"
            )

        idx, is_final, nonce, payload_len = struct.unpack(">Q?12sI", header_bytes)
        payload = stream.read(payload_len)
        if len(payload) < payload_len:
            raise ChunkTruncationError(
                f"Incomplete chunk payload: read {len(payload)} bytes, expected {payload_len}"
            )

        return cls(index=idx, is_final=is_final, nonce=nonce, ciphertext_and_tag=payload)


class ChunkedEncryptor:
    """Streams and encrypts large data inputs in authenticated chunks."""

    def __init__(self, engine: AdaptiveEngine | None = None) -> None:
        self.engine = engine or AdaptiveEngine()

    def encrypt_stream(
        self,
        input_stream: BinaryIO,
        key: bytes,
        config: PipelineConfig,
        file_id: str = "default",
    ) -> Generator[EncryptedChunk, None, None]:
        """Read chunks from input_stream and yield encrypted chunks."""
        chunk_size = config.chunk_size_bytes
        idx = 0

        while True:
            chunk_data = input_stream.read(chunk_size)
            peek = input_stream.read(1)
            is_final = len(peek) == 0

            # If peek had a byte, seek back 1 position
            if not is_final:
                input_stream.seek(-1, io.SEEK_CUR)

            # Bind file_id, chunk_index, and is_final into AAD to prevent splicing/reordering
            aad = f"cryptavault:chunk:{file_id}:{idx}:{is_final}".encode()
            nonce, ciphertext = self.engine.encrypt_block(config, key, chunk_data, aad=aad)

            yield EncryptedChunk(
                index=idx,
                is_final=is_final,
                nonce=nonce,
                ciphertext_and_tag=ciphertext,
            )

            idx += 1
            if is_final:
                break


class ChunkedDecryptor:
    """Streams, decrypts, and authenticates chunks, writing plaintext to output_stream."""

    def __init__(self, engine: AdaptiveEngine | None = None) -> None:
        self.engine = engine or AdaptiveEngine()

    def decrypt_stream(
        self,
        encrypted_stream: BinaryIO,
        output_stream: BinaryIO,
        key: bytes,
        config: PipelineConfig,
        file_id: str = "default",
    ) -> int:
        """Decrypt all chunks from encrypted_stream into output_stream.

        Returns total decrypted bytes written.
        Raises ChunkOutOfOrderError or InvalidTagError on any corruption/tampering.
        """
        expected_idx = 0
        total_bytes = 0
        saw_final = False

        while True:
            chunk = EncryptedChunk.read_from_stream(encrypted_stream)
            if chunk is None:
                break

            if chunk.index != expected_idx:
                raise ChunkOutOfOrderError(
                    f"Chunk sequence anomaly: expected chunk {expected_idx}, got {chunk.index}"
                )

            aad = f"cryptavault:chunk:{file_id}:{chunk.index}:{chunk.is_final}".encode()
            try:
                plaintext_chunk = self.engine.decrypt_block(
                    config, key, chunk.nonce, chunk.ciphertext_and_tag, aad=aad
                )
            except InvalidTagError as exc:
                raise InvalidTagError(
                    f"Chunk {chunk.index} authentication tag failed verification. Stream tampered."
                ) from exc

            output_stream.write(plaintext_chunk)
            total_bytes += len(plaintext_chunk)

            if chunk.is_final:
                saw_final = True
                break

            expected_idx += 1

        if not saw_final:
            raise ChunkTruncationError(
                "Encrypted stream ended prematurely without final chunk marker"
            )

        return total_bytes
