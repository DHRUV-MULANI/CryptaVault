"""Integrity Report Generator for CryptaVault.

Generates structured health and verification reports across folders, manifests,
and Merkle trees, rendering both formatted ASCII/Rich tables and machine-readable JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptavault.integrity.merkle import MerkleTree
from cryptavault.signatures.verify import VerificationResult, VerificationStatus, verify_file


@dataclass(frozen=True)
class FileManifestEntry:
    """Expected file metadata stored in an encrypted manifest."""

    rel_path: str
    expected_hash: str
    size_bytes: int
    signature: bytes | None = None
    public_key: bytes | None = None
    algorithm: str = "ed25519"


@dataclass
class IntegrityReport:
    """Complete folder integrity audit report."""

    target_path: str
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    total_files: int = 0
    valid_files: int = 0
    tampered_files: int = 0
    corrupted_files: int = 0
    missing_key_files: int = 0
    merkle_root: str | None = None
    file_results: list[VerificationResult] = field(default_factory=list)

    @property
    def is_fully_valid(self) -> bool:
        return self.valid_files == self.total_files and self.total_files > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "target_path": self.target_path,
            "generated_at": self.generated_at,
            "summary": {
                "total_files": self.total_files,
                "valid_files": self.valid_files,
                "tampered_files": self.tampered_files,
                "corrupted_files": self.corrupted_files,
                "missing_key_files": self.missing_key_files,
                "is_fully_valid": self.is_fully_valid,
                "merkle_root": self.merkle_root,
            },
            "results": [
                {
                    "file_path": r.file_path,
                    "status": r.status.value,
                    "message": r.message,
                    "actual_size_bytes": r.actual_size_bytes,
                    "expected_size_bytes": r.expected_size_bytes,
                    "actual_hash": r.actual_hash,
                    "expected_hash": r.expected_hash,
                    "diagnostics": r.diagnostics,
                }
                for r in self.file_results
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Export report as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_table(self) -> str:
        """Render clean ASCII summary table."""
        lines = [
            "=" * 78,
            f"  CryptaVault Integrity Audit Report: {self.target_path}",
            f"  Timestamp: {self.generated_at}",
            f"  Status: {'✔ PASS (All Files Valid)' if self.is_fully_valid else '✖ INTEGRITY BREACH DETECTED'}",
            f"  Summary: {self.valid_files}/{self.total_files} Valid | {self.tampered_files} Tampered | {self.corrupted_files} Corrupted",
        ]
        if self.merkle_root:
            lines.append(f"  Merkle Tree Root: {self.merkle_root}")
        lines.append("-" * 78)
        lines.append(f"{'Status':<12} {'Size':<10} {'File Path'}")
        lines.append("-" * 78)

        for r in self.file_results:
            status_tag = f"[{r.status.value}]"
            size_str = f"{r.actual_size_bytes} B"
            lines.append(f"{status_tag:<12} {size_str:<10} {r.file_path}")
            if not r.is_valid:
                lines.append(f"   ↳ Error: {r.message}")

        lines.append("=" * 78)
        return "\n".join(lines)


def generate_report(
    folder_path: str | Path,
    manifest: list[FileManifestEntry],
) -> IntegrityReport:
    """Generate comprehensive integrity report verifying files against manifest entries."""
    root = Path(folder_path)
    report = IntegrityReport(target_path=str(root))

    leaf_hashes: list[str] = []

    for entry in manifest:
        file_full_path = root / entry.rel_path
        res = verify_file(
            file_path=file_full_path,
            signature=entry.signature,
            public_key=entry.public_key,
            algorithm=entry.algorithm,
            expected_hash=entry.expected_hash,
            expected_size_bytes=entry.size_bytes,
        )
        report.file_results.append(res)
        report.total_files += 1

        if res.status == VerificationStatus.VALID:
            report.valid_files += 1
            if res.actual_hash:
                leaf_hashes.append(res.actual_hash)
        elif res.status == VerificationStatus.TAMPERED:
            report.tampered_files += 1
        elif res.status == VerificationStatus.CORRUPTED:
            report.corrupted_files += 1
        elif res.status == VerificationStatus.MISSING_KEY:
            report.missing_key_files += 1

    # Compute folder Merkle root if valid files exist
    if leaf_hashes:
        tree = MerkleTree(leaf_hashes)
        report.merkle_root = tree.root_hex

    return report
