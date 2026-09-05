"""Rule-based heuristic cryptographic advisor for CryptaVault.

Provides deterministic, offline, zero-network recommendations for encryption,
compression, and chunk sizing tailored to file characteristics and threat models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cryptavault.compression.detect import detect_file_type


@dataclass
class Recommendation:
    """Security and performance configuration recommendation."""

    encryption_algo: str
    compression_mode: str  # "zstd", "brotli", "none"
    chunk_size_bytes: int
    parallel_workers: int
    forward_secrecy: bool
    multi_layer: bool
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "encryption_algo": self.encryption_algo,
            "compression_mode": self.compression_mode,
            "chunk_size_bytes": self.chunk_size_bytes,
            "parallel_workers": self.parallel_workers,
            "forward_secrecy": self.forward_secrecy,
            "multi_layer": self.multi_layer,
            "rationale": self.rationale,
        }


class RuleBasedRecommender:
    """Evaluates file metadata and security profile to provide deterministic recommendations."""

    @staticmethod
    def advise(
        filename: str,
        size_bytes: int,
        profile_level: str = "BALANCED",
        header_sample: bytes = b"",
    ) -> Recommendation:
        """Generate tailored cryptographic and pipeline recommendations."""
        name_lower = filename.lower()
        if header_sample:
            file_type = detect_file_type(header_sample)
            is_already_compressed = file_type.is_pre_compressed
        else:
            is_already_compressed = any(
                name_lower.endswith(ext)
                for ext in (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".mp4",
                    ".mov",
                    ".zip",
                    ".gz",
                    ".tar.gz",
                    ".zst",
                    ".7z",
                    ".rar",
                )
            )
        is_highly_sensitive = any(
            kw in name_lower
            for kw in (
                "key",
                "wallet",
                "seed",
                "secret",
                "private",
                "credential",
                "password",
                "id_rsa",
            )
        )

        level_upper = profile_level.upper()

        # Rule 1: High Sensitivity / Credentials / Maximum Security
        if level_upper == "MAXIMUM" or is_highly_sensitive:
            comp = "none" if is_already_compressed else "zstd"
            return Recommendation(
                encryption_algo="aes-256-gcm+chacha20-poly1305",
                compression_mode=comp,
                chunk_size_bytes=(
                    16 * 1024 * 1024 if size_bytes > 50 * 1024 * 1024 else 4 * 1024 * 1024
                ),
                parallel_workers=4,
                forward_secrecy=True,
                multi_layer=True,
                rationale=(
                    "Highly sensitive asset or MAXIMUM profile detected: Enforcing dual-layer encryption "
                    "(AES-256-GCM + ChaCha20), forward-secrecy key ratchets, and tamper-evident audit logging."
                ),
            )

        # Rule 2: Massive Datasets & VM Images (>10 GB or .iso/.vmdk/.qcow2)
        if size_bytes > 10 * 1024 * 1024 * 1024 or any(
            name_lower.endswith(ext) for ext in (".iso", ".vmdk", ".qcow2", ".img")
        ):
            return Recommendation(
                encryption_algo="aes-256-gcm",
                compression_mode="none",  # Skip compression to maximize GB/s disk/network throughput
                chunk_size_bytes=16 * 1024 * 1024,
                parallel_workers=8,
                forward_secrecy=False,
                multi_layer=False,
                rationale=(
                    "Large-scale dataset (>10 GB / VM disk): Recommending hardware AES-NI acceleration with "
                    "16 MB chunks, 8 parallel workers, and skipping compression to achieve peak I/O throughput."
                ),
            )

        # Rule 3: Pre-compressed media (JPEG, MP4, PNG, ZIP, etc.)
        if is_already_compressed:
            algo = "chacha20-poly1305" if level_upper == "STRONG" else "aes-256-gcm"
            return Recommendation(
                encryption_algo=algo,
                compression_mode="none",
                chunk_size_bytes=4 * 1024 * 1024,
                parallel_workers=4,
                forward_secrecy=level_upper in ("STRONG", "MAXIMUM"),
                multi_layer=False,
                rationale=(
                    "Asset is already compressed or high-entropy media. "
                    "Skipping compression prevents CPU waste and ciphertext size inflation."
                ),
            )

        # Rule 4: Plaintext / Structured Code / Logs / CSV
        is_text_doc = any(
            name_lower.endswith(ext)
            for ext in (
                ".txt",
                ".log",
                ".json",
                ".csv",
                ".xml",
                ".sql",
                ".py",
                ".ts",
                ".md",
                ".html",
                ".yaml",
            )
        )
        if is_text_doc:
            algo = "chacha20-poly1305" if level_upper == "STRONG" else "aes-256-gcm"
            return Recommendation(
                encryption_algo=algo,
                compression_mode="zstd",
                chunk_size_bytes=4 * 1024 * 1024,
                parallel_workers=2,
                forward_secrecy=level_upper in ("STRONG", "MAXIMUM"),
                multi_layer=False,
                rationale=(
                    "Highly compressible text/structured document: Zstandard compression applied prior to AEAD "
                    "will yield up to 60–80% storage savings without noticeable latency penalty."
                ),
            )

        # Rule 5: Default General Workload
        algo = "chacha20-poly1305" if level_upper == "STRONG" else "aes-256-gcm"
        return Recommendation(
            encryption_algo=algo,
            compression_mode="zstd" if size_bytes < 100 * 1024 * 1024 else "none",
            chunk_size_bytes=4 * 1024 * 1024,
            parallel_workers=4,
            forward_secrecy=False,
            multi_layer=False,
            rationale="Standard workload: Balanced AES-256-GCM chunked AEAD with intelligent streaming.",
        )
