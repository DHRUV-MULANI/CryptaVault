"""Unified Cryptographic Pipeline Orchestrator for CryptaVault.

Threads data through:
1. Intelligence & Skip-Compression Stage (Zstandard / Brotli)
2. Chunked AEAD Streaming Encryption (any catalogued AEAD or cascaded multi-layer)
3. Cryptographic Merkle Tree Integrity Tree (profile-selected hash)
4. Digital Signatures over the header digest and Merkle root (classical or PQ hybrid)

The container records the exact algorithms and wire identifiers used, so files
remain decryptable after defaults change and unknown primitives fail closed.
"""

from __future__ import annotations

import hmac
import io
import time
from dataclasses import dataclass
from typing import BinaryIO

from cryptavault.adaptive.engine import AdaptiveEngine, PipelineConfig
from cryptavault.adaptive.profiles import SecurityProfile, get_profile
from cryptavault.compression.algorithms import compress, decompress
from cryptavault.compression.policy import should_compress
from cryptavault.crypto.asymmetric import SignatureVerificationError
from cryptavault.crypto.catalog import CryptoFamily, catalog
from cryptavault.integrity.merkle import MerkleTree
from cryptavault.pipeline.chunked_encryption import (
    ChunkedDecryptor,
    ChunkedEncryptor,
    EncryptedChunk,
    StreamingPipelineError,
)
from cryptavault.pipeline.container import (
    CONTAINER_MAGIC,
    LEGACY_CONTAINER_MAGIC,
    AlgorithmBinding,
    ContainerHeader,
    ContainerIntegrityError,
    ContainerTrailer,
    encode_header,
    read_header_body,
    read_trailer,
    write_header,
    write_trailer,
)
from cryptavault.plugins.registry import hash_registry, signature_registry

SIGNATURE_CONTEXT = b"cryptavault:container:v2:"


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


def _binding(family: CryptoFamily, algorithm_id: str, require_runtime: bool) -> AlgorithmBinding:
    spec = (
        catalog.require_usable(algorithm_id, family)
        if require_runtime
        else catalog.get(algorithm_id)
    )
    if spec.family is not family:
        raise ContainerIntegrityError(
            f"Algorithm '{spec.algorithm_id}' is not a member of family '{family.value}'"
        )
    return AlgorithmBinding(
        family=family.value,
        algorithm_id=spec.algorithm_id,
        wire_id=spec.wire_id,
    )


def _validate_binding(
    family: CryptoFamily,
    binding: AlgorithmBinding,
    require_runtime: bool,
) -> str:
    spec = catalog.from_wire_id(binding.wire_id)
    if spec.family is not family:
        raise ContainerIntegrityError(
            f"Wire id 0x{binding.wire_id:04x} belongs to '{spec.family.value}', "
            f"not '{family.value}'"
        )
    if spec.algorithm_id != binding.algorithm_id:
        raise ContainerIntegrityError(
            f"Algorithm binding mismatch: header says '{binding.algorithm_id}', "
            f"wire id resolves to '{spec.algorithm_id}'"
        )
    if require_runtime:
        catalog.require_usable(spec.algorithm_id, family)
    return spec.algorithm_id


def _config_from_header(header: ContainerHeader, verification_required: bool) -> PipelineConfig:
    profile = get_profile(header.profile)
    symmetric_id = _validate_binding(
        CryptoFamily.SYMMETRIC, header.binding(CryptoFamily.SYMMETRIC.value), True
    )
    hash_id = _validate_binding(CryptoFamily.HASH, header.binding(CryptoFamily.HASH.value), True)
    signature_id = _validate_binding(
        CryptoFamily.SIGNATURE,
        header.binding(CryptoFamily.SIGNATURE.value),
        verification_required,
    )
    kem_id = _validate_binding(CryptoFamily.KEM, header.binding(CryptoFamily.KEM.value), False)
    _validate_binding(CryptoFamily.KDF, header.binding(CryptoFamily.KDF.value), False)

    return PipelineConfig(
        profile=profile,
        chunk_size_bytes=header.chunk_size_bytes,
        parallel_workers=profile.kdf_parallelism,
        symmetric_cipher=symmetric_id,
        hash_algorithm=hash_id,
        signature_algorithm=signature_id,
        kem_algorithm=kem_id,
        multi_layer=header.multi_layer,
        compression_enabled=True,
    )


class PipelineOrchestrator:
    """Coordinates end-to-end multi-stage cryptographic transformations."""

    MAGIC_HEADER = CONTAINER_MAGIC
    LEGACY_MAGIC_HEADER = LEGACY_CONTAINER_MAGIC

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
        """Run the full encryption pipeline, writing a CVV2 container."""
        t0 = time.perf_counter()
        profile = (
            profile_or_name
            if isinstance(profile_or_name, SecurityProfile)
            else get_profile(profile_or_name)
        )

        raw_data = input_stream.read()
        orig_size = len(raw_data)

        apply_comp = should_compress(raw_data, profile)
        comp_algo: str | None = None
        if apply_comp:
            comp_algo = profile.compression_algorithm
            payload_to_encrypt = compress(raw_data, comp_algo)
        else:
            payload_to_encrypt = raw_data

        config = self.engine.resolve(profile, file_size_bytes=len(payload_to_encrypt))
        symmetric_id = (
            "cascade-chacha20-aes256gcm" if config.multi_layer else config.symmetric_cipher
        )

        header = ContainerHeader(
            file_id=file_id,
            profile=profile.level.value,
            compression=comp_algo,
            chunk_size_bytes=config.chunk_size_bytes,
            multi_layer=config.multi_layer,
            algorithms={
                CryptoFamily.SYMMETRIC.value: _binding(CryptoFamily.SYMMETRIC, symmetric_id, True),
                CryptoFamily.HASH.value: _binding(CryptoFamily.HASH, config.hash_algorithm, True),
                CryptoFamily.KDF.value: _binding(CryptoFamily.KDF, profile.kdf_algorithm, False),
                CryptoFamily.SIGNATURE.value: _binding(
                    CryptoFamily.SIGNATURE,
                    config.signature_algorithm,
                    signing_key is not None,
                ),
                CryptoFamily.KEM.value: _binding(CryptoFamily.KEM, config.kem_algorithm, False),
            },
        )
        header_bytes = write_header(output_stream, header)

        hasher = hash_registry.get(config.hash_algorithm)()
        data_stream = io.BytesIO(payload_to_encrypt)
        chunk_leaves: list[bytes] = []
        chunk_count = 0

        for chunk in self.encryptor.encrypt_stream(
            data_stream, encryption_key, config, file_id=file_id
        ):
            serialized_chunk = chunk.serialize()
            output_stream.write(serialized_chunk)
            chunk_leaves.append(hasher.digest(serialized_chunk))
            chunk_count += 1

        tree = MerkleTree(chunk_leaves)
        merkle_root = tree.root

        sig_hex = ""
        if signing_key:
            signer = signature_registry.get(config.signature_algorithm)()
            message = SIGNATURE_CONTEXT + hasher.digest(header_bytes) + merkle_root
            sig_hex = signer.sign(signing_key, message).hex()

        write_trailer(
            output_stream,
            ContainerTrailer(
                chunk_count=chunk_count,
                merkle_root_hex=merkle_root.hex(),
                signature_hex=sig_hex,
            ),
        )

        dur = time.perf_counter() - t0
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
            duration_ms=dur * 1000.0,
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
        verification_key: bytes | None = None,
    ) -> int:
        """Decrypt a CVV1 or CVV2 container, verifying integrity and signature."""
        magic = encrypted_stream.read(4)
        if magic == LEGACY_CONTAINER_MAGIC:
            return self._run_decryption_v1(
                encrypted_stream,
                output_stream,
                encryption_key,
                profile_or_name,
                compression_algo,
                file_id,
            )
        if magic != CONTAINER_MAGIC:
            raise StreamingPipelineError(
                f"Invalid vault container: expected {CONTAINER_MAGIC!r} or "
                f"{LEGACY_CONTAINER_MAGIC!r}, got {magic!r}"
            )

        header = read_header_body(encrypted_stream)
        header_bytes = encode_header(header)
        if file_id is not None and file_id != header.file_id:
            raise ContainerIntegrityError(
                f"Caller file id '{file_id}' does not match container file id "
                f"'{header.file_id}'"
            )
        effective_file_id = header.file_id
        config = _config_from_header(header, verification_required=verification_key is not None)

        hasher = hash_registry.get(config.hash_algorithm)()
        chunk_leaves: list[bytes] = []

        def observe(chunk: EncryptedChunk) -> None:
            chunk_leaves.append(hasher.digest(chunk.serialize()))

        decrypted_buf = io.BytesIO()
        self.decryptor.decrypt_stream(
            encrypted_stream,
            decrypted_buf,
            encryption_key,
            config,
            file_id=effective_file_id,
            on_chunk=observe,
        )
        decrypted_bytes = decrypted_buf.getvalue()

        trailer = read_trailer(encrypted_stream)
        if trailer.chunk_count != len(chunk_leaves):
            raise ContainerIntegrityError(
                f"Container chunk count mismatch: trailer says {trailer.chunk_count}, "
                f"read {len(chunk_leaves)}"
            )

        tree = MerkleTree(chunk_leaves)
        expected_root = bytes.fromhex(trailer.merkle_root_hex)
        if not hmac.compare_digest(tree.root, expected_root):
            raise ContainerIntegrityError(
                "Merkle root mismatch: container chunks were modified or reordered"
            )

        if verification_key is not None:
            if not trailer.signature_hex:
                raise ContainerIntegrityError("Container is not signed")
            signer = signature_registry.get(config.signature_algorithm)()
            message = SIGNATURE_CONTEXT + hasher.digest(header_bytes) + tree.root
            if not signer.verify(verification_key, message, bytes.fromhex(trailer.signature_hex)):
                raise SignatureVerificationError("Container signature verification failed")

        if header.compression:
            final_data = decompress(decrypted_bytes, header.compression)
        else:
            final_data = decrypted_bytes

        output_stream.write(final_data)
        return len(final_data)

    def _run_decryption_v1(
        self,
        encrypted_stream: BinaryIO,
        output_stream: BinaryIO,
        encryption_key: bytes,
        profile_or_name: SecurityProfile | str,
        compression_algo: str | None,
        file_id: str | None,
    ) -> int:
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

        decrypted_buf = io.BytesIO()
        self.decryptor.decrypt_stream(
            encrypted_stream, decrypted_buf, encryption_key, config, file_id=effective_file_id
        )
        decrypted_bytes = decrypted_buf.getvalue()

        if effective_comp:
            final_data = decompress(decrypted_bytes, effective_comp)
        else:
            final_data = decrypted_bytes

        output_stream.write(final_data)
        return len(final_data)
