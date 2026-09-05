"""Unified Cryptographic Pipeline Orchestrator for CryptaVault.

Threads data through:
1. Intelligence & Skip-Compression Stage (Zstandard / Brotli)
2. Chunked AEAD Streaming Encryption (AES-256-GCM / ChaCha20-Poly1305 / Multi-Layer)
3. Cryptographic Merkle Tree Integrity Tree (BLAKE3)
4. Post-Quantum Hybrid Digital Signatures (Ed25519 + Dilithium-3)
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import BinaryIO

from cryptavault.adaptive.engine import AdaptiveEngine
from cryptavault.adaptive.profiles import SecurityProfile, get_profile
from cryptavault.compression.algorithms import compress, decompress
from cryptavault.compression.policy import should_compress
from cryptavault.crypto.hybrid import HybridSigPQ
from cryptavault.integrity.merkle import MerkleTree
from cryptavault.pipeline.chunked_encryption import (
    ChunkedDecryptor,
    ChunkedEncryptor,
    StreamingPipelineError,
)


@dataclass(frozen=True)
class PipelineResult:
    """Outcome and metadata from a pipeline execution."""

    file_id: str
    original_size_bytes: int
    processed_size_bytes: int
    compression_applied: bool
    compression_algo: str | None
    chunk_count: int
    merkle_root_hex: str
    signature_hex: str
    profile_name: str
    duration_ms: float
    throughput_mb_s: float


class PipelineOrchestrator:
    """Coordinates end-to-end multi-stage cryptographic transformations."""

    MAGIC_HEADER = b"CVV1"

    def __init__(self, engine: AdaptiveEngine | None = None) -> None:
        self.engine = engine or AdaptiveEngine()
        self.encryptor = ChunkedEncryptor(self.engine)
        self.decryptor = ChunkedDecryptor(self.engine)

    def run_encryption(
        self,
        input_stream: BinaryIO,
        output_stream: BinaryIO,
        encryption_key: bytes,
        profile_or_name: SecurityProfile | str = "BALANCED",
        signing_key: bytes | None = None,
        file_id: str = "doc-01",
    ) -> PipelineResult:
        """Run full encryption pipeline on input_stream, writing container and encrypted chunks to output_stream."""
        t0 = time.perf_counter()
        profile = (
            profile_or_name
            if isinstance(profile_or_name, SecurityProfile)
            else get_profile(profile_or_name)
        )

        # Read input payload
        raw_data = input_stream.read()
        orig_size = len(raw_data)

        # 1. Compression Stage
        apply_comp = should_compress(raw_data, profile)
        comp_algo: str | None = None
        if apply_comp:
            comp_algo = profile.compression_algorithm
            payload_to_encrypt = compress(raw_data, comp_algo)
        else:
            payload_to_encrypt = raw_data

        # 2. Adaptive Config Resolution
        config = self.engine.resolve(profile, file_size_bytes=len(payload_to_encrypt))

        # 3. Write Container Header: [4-byte MAGIC][1-byte file_id_len][file_id][1-byte comp_len][comp_algo]
        fid_bytes = file_id.encode("utf-8")
        comp_bytes = (comp_algo or "none").encode("utf-8")
        header = (
            self.MAGIC_HEADER
            + len(fid_bytes).to_bytes(1, "big")
            + fid_bytes
            + len(comp_bytes).to_bytes(1, "big")
            + comp_bytes
        )
        output_stream.write(header)

        # 4. Chunked AEAD Encryption
        data_stream = io.BytesIO(payload_to_encrypt)
        chunk_leaves: list[bytes] = []
        chunk_count = 0

        from cryptavault.crypto.hash import Blake3

        for chunk in self.encryptor.encrypt_stream(
            data_stream, encryption_key, config, file_id=file_id
        ):
            serialized_chunk = chunk.serialize()
            output_stream.write(serialized_chunk)
            chunk_leaves.append(Blake3().digest(serialized_chunk))
            chunk_count += 1

        # 5. Merkle Tree Integrity Stage
        tree = MerkleTree(chunk_leaves)
        merkle_root = tree.root

        # 6. Hybrid Signature Stage
        sig_hex = ""
        if signing_key:
            sig_engine = HybridSigPQ()
            sig_bytes = sig_engine.sign(signing_key, merkle_root)
            sig_hex = sig_bytes.hex()

        dur = time.perf_counter() - t0
        dur_ms = dur * 1000.0
        throughput = (orig_size / (1024 * 1024)) / dur if dur > 0 else 0.0

        return PipelineResult(
            file_id=file_id,
            original_size_bytes=orig_size,
            processed_size_bytes=output_stream.tell() if hasattr(output_stream, "tell") else 0,
            compression_applied=apply_comp,
            compression_algo=comp_algo,
            chunk_count=chunk_count,
            merkle_root_hex=merkle_root.hex(),
            signature_hex=sig_hex,
            profile_name=profile.level.value,
            duration_ms=dur_ms,
            throughput_mb_s=throughput,
        )

    def run_decryption(
        self,
        encrypted_stream: BinaryIO,
        output_stream: BinaryIO,
        encryption_key: bytes,
        profile_or_name: SecurityProfile | str = "BALANCED",
        compression_algo: str | None = None,
        file_id: str | None = None,
    ) -> int:
        """Run decryption and decompression pipeline reading container header automatically."""
        # Read Container Header
        magic = encrypted_stream.read(4)
        if magic != self.MAGIC_HEADER:
            raise StreamingPipelineError("Invalid vault container: missing CVV1 magic header")

        fid_len = int.from_bytes(encrypted_stream.read(1), "big")
        extracted_file_id = encrypted_stream.read(fid_len).decode("utf-8")

        comp_len = int.from_bytes(encrypted_stream.read(1), "big")
        extracted_comp = encrypted_stream.read(comp_len).decode("utf-8")

        effective_file_id = file_id or extracted_file_id
        effective_comp = compression_algo or (extracted_comp if extracted_comp != "none" else None)

        profile = (
            profile_or_name
            if isinstance(profile_or_name, SecurityProfile)
            else get_profile(profile_or_name)
        )
        config = self.engine.resolve(profile)

        # 1. Decrypt chunked stream
        decrypted_buf = io.BytesIO()
        self.decryptor.decrypt_stream(
            encrypted_stream, decrypted_buf, encryption_key, config, file_id=effective_file_id
        )
        decrypted_bytes = decrypted_buf.getvalue()

        # 2. Decompression Stage
        if effective_comp:
            final_data = decompress(decrypted_bytes, effective_comp)
        else:
            final_data = decrypted_bytes

        output_stream.write(final_data)
        return len(final_data)
