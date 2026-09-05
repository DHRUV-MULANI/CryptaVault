"""Cryptographic Merkle Tree for Folder Integrity in CryptaVault.

Constructs binary Merkle trees where:
- Leaf nodes represent individual file BLAKE3 digests.
- Internal parent nodes are computed as SHA-256(left || right).
- Proof generation and verification run in O(log n) time and space.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Sequence
from typing import Any


class MerkleTreeError(Exception):
    """Base exception for Merkle tree errors."""


class MerkleTree:
    """Binary Merkle Tree supporting proof generation and verification."""

    def __init__(self, leaves: Sequence[bytes | str] | None = None) -> None:
        self.levels: list[list[bytes]] = []
        self._raw_leaves: list[bytes] = []
        if leaves:
            self.build(leaves)

    @property
    def root(self) -> bytes:
        """Return the binary root hash of the tree."""
        if not self.levels or not self.levels[-1]:
            return b""
        return self.levels[-1][0]

    @property
    def root_hex(self) -> str:
        """Return the hex-encoded root hash of the tree."""
        return self.root.hex()

    @property
    def leaf_count(self) -> int:
        return len(self._raw_leaves)

    def build(self, leaf_hashes: Sequence[bytes | str]) -> bytes:
        """Construct the Merkle tree from a sequence of leaf hashes.

        Accepts either raw bytes or hex strings.
        """
        if not leaf_hashes:
            self.levels = []
            self._raw_leaves = []
            return b""

        # Convert hex strings to bytes if necessary
        leaves_bytes: list[bytes] = [
            bytes.fromhex(h) if isinstance(h, str) else h for h in leaf_hashes
        ]
        self._raw_leaves = leaves_bytes[:]
        self.levels = [leaves_bytes]

        current_level = leaves_bytes
        while len(current_level) > 1:
            next_level: list[bytes] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd number of nodes, pair the last node with itself
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = hashlib.sha256(left + right).digest()
                next_level.append(parent)
            self.levels.append(next_level)
            current_level = next_level

        return self.root

    def get_proof(self, leaf_index: int) -> list[tuple[str, bytes]]:
        """Generate an audit proof for the leaf at leaf_index.

        Returns a list of (direction, sibling_hash) tuples where direction is 'L' or 'R'.
        'L': sibling is to the left of the current node.
        'R': sibling is to the right of the current node.
        """
        if not self.levels or leaf_index < 0 or leaf_index >= len(self._raw_leaves):
            raise IndexError(
                f"Leaf index {leaf_index} out of range (0..{len(self._raw_leaves) - 1})"
            )

        proof: list[tuple[str, bytes]] = []
        idx = leaf_index

        for level in self.levels[:-1]:
            is_right_child = idx % 2 == 1
            if is_right_child:
                sibling_idx = idx - 1
                direction = "L"
            else:
                sibling_idx = idx + 1 if idx + 1 < len(level) else idx
                direction = "R"

            sibling_hash = level[sibling_idx]
            proof.append((direction, sibling_hash))
            idx //= 2

        return proof

    @staticmethod
    def verify_proof(
        leaf: bytes | str,
        proof: list[tuple[str, bytes]],
        root: bytes | str,
    ) -> bool:
        """Verify that a given leaf belongs to the tree represented by root."""
        current = bytes.fromhex(leaf) if isinstance(leaf, str) else leaf
        expected_root = bytes.fromhex(root) if isinstance(root, str) else root

        for direction, sibling in proof:
            if direction == "L":
                current = hashlib.sha256(sibling + current).digest()
            elif direction == "R":
                current = hashlib.sha256(current + sibling).digest()
            else:
                return False

        return hmac.compare_digest(current, expected_root)

    def export_proof(self, leaf_index: int) -> dict[str, Any]:
        """Export serialized proof payload suitable for JSON transmission."""
        proof = self.get_proof(leaf_index)
        return {
            "leaf_index": leaf_index,
            "leaf_hash": self._raw_leaves[leaf_index].hex(),
            "root_hash": self.root_hex,
            "proof_steps": [{"direction": d, "sibling": s.hex()} for d, s in proof],
        }
