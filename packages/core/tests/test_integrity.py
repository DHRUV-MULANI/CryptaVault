"""Tests for CryptaVault Phase P3 (Signatures, Integrity, Merkle Trees, and Reports).

Tests:
- SignatureContext streaming across classical, PQ, and hybrid algorithms
- Tamper and corruption detection (VALID, TAMPERED, CORRUPTED, MISSING_KEY)
- Per-file streaming hashing
- Merkle tree scaling to 1000 leaves and audit proof verification
- Integrity report generation (ASCII table & JSON)
"""

import tempfile
from pathlib import Path

import pytest
from cryptavault.crypto.asymmetric import Ed25519Signer
from cryptavault.crypto.hash import Blake3
from cryptavault.integrity.file_hash import compute_file_hash
from cryptavault.integrity.merkle import MerkleTree
from cryptavault.integrity.report import FileManifestEntry, generate_report
from cryptavault.signatures.base import SignatureContext
from cryptavault.signatures.verify import VerificationStatus, verify_file

# ====================================================================
# 1. SignatureContext Streaming Tests
# ====================================================================


@pytest.mark.parametrize(
    "algorithm",
    ["ed25519", "ecdsa-p256", "dilithium3", "hybrid-sig-pq"],
)
def test_signature_context_roundtrip(algorithm: str) -> None:
    """Verify uniform streaming sign and verify across all supported schemes."""
    ctx = SignatureContext(algorithm=algorithm)
    _pub, _priv = ctx.generate_keys()

    data = b"CryptaVault zero-knowledge streaming payload" * 50
    sig = ctx.sign_bytes(data)

    assert ctx.verify_bytes(data, sig) is True
    assert ctx.verify_bytes(data + b"tampered", sig) is False


# ====================================================================
# 2. Tamper and Corruption Detection
# ====================================================================


def test_tamper_and_corruption_states() -> None:
    """Verify all 4 failure and success states: VALID, TAMPERED, CORRUPTED, MISSING_KEY."""
    signer = Ed25519Signer()
    pub, priv = signer.keypair()
    hasher = Blake3()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "secure_data.bin"
        original_content = b"Original uncorrupted financial record content"
        test_file.write_bytes(original_content)

        digest = hasher.digest(original_content)
        sig = signer.sign(priv, digest)
        expected_size = len(original_content)
        expected_hash = digest.hex()

        # 1. VALID
        res_valid = verify_file(
            file_path=test_file,
            signature=sig,
            public_key=pub,
            algorithm="ed25519",
            expected_hash=expected_hash,
            expected_size_bytes=expected_size,
        )
        assert res_valid.status == VerificationStatus.VALID

        # 2. TAMPERED (Single byte modified)
        tampered_content = b"Original Xncorrupted financial record content"
        test_file.write_bytes(tampered_content)
        res_tampered = verify_file(
            file_path=test_file,
            signature=sig,
            public_key=pub,
            algorithm="ed25519",
            expected_hash=expected_hash,
            expected_size_bytes=expected_size,
        )
        assert res_tampered.status == VerificationStatus.TAMPERED

        # 3. CORRUPTED (Truncated content)
        truncated_content = original_content[:15]
        test_file.write_bytes(truncated_content)
        res_corrupted = verify_file(
            file_path=test_file,
            signature=sig,
            public_key=pub,
            algorithm="ed25519",
            expected_hash=expected_hash,
            expected_size_bytes=expected_size,
        )
        assert res_corrupted.status == VerificationStatus.CORRUPTED

        # 4. MISSING_KEY
        test_file.write_bytes(original_content)
        res_missing = verify_file(
            file_path=test_file,
            signature=sig,
            public_key=None,
            algorithm="ed25519",
            expected_hash=expected_hash,
            expected_size_bytes=expected_size,
        )
        assert res_missing.status == VerificationStatus.MISSING_KEY


# ====================================================================
# 3. Per-File Streaming Hash
# ====================================================================


def test_compute_file_hash_streaming() -> None:
    """Verify compute_file_hash on temporary files across algorithms."""
    with tempfile.NamedTemporaryFile() as tmp:
        data = b"Testing streaming file hash in 1MB chunks" * 2000
        tmp.write(data)
        tmp.flush()

        h_blake3 = compute_file_hash(tmp.name, algorithm="blake3")
        h_sha256 = compute_file_hash(tmp.name, algorithm="sha256")
        h_sha3 = compute_file_hash(tmp.name, algorithm="sha3-512")

        assert len(h_blake3) == 64
        assert len(h_sha256) == 64
        assert len(h_sha3) == 128
        assert h_blake3 != h_sha256


# ====================================================================
# 4. Merkle Tree Scaling to 1000 Leaves
# ====================================================================


def test_merkle_tree_1000_leaves_and_proofs() -> None:
    """Build Merkle tree with 1,000 leaves and verify inclusion proofs."""
    hasher = Blake3()
    leaf_hashes = [hasher.digest(f"leaf_data_block_{i}".encode()).hex() for i in range(1000)]

    tree = MerkleTree(leaf_hashes)
    assert tree.leaf_count == 1000
    assert len(tree.root) == 32

    # Verify proofs for first, middle, and last leaf
    for idx in [0, 1, 499, 500, 999]:
        proof = tree.get_proof(idx)
        leaf = leaf_hashes[idx]
        assert MerkleTree.verify_proof(leaf, proof, tree.root) is True

        # Tampered leaf must fail verification
        tampered_leaf = bytes.fromhex(leaf)[:-1] + b"\xff"
        assert MerkleTree.verify_proof(tampered_leaf, proof, tree.root) is False

        # Export proof dictionary and verify
        exported = tree.export_proof(idx)
        assert exported["leaf_index"] == idx
        assert exported["root_hash"] == tree.root_hex


# ====================================================================
# 5. Integrity Report Generator
# ====================================================================


def test_integrity_report_generator() -> None:
    """Test comprehensive report generation on a multi-file folder."""
    signer = Ed25519Signer()
    pub, priv = signer.keypair()
    hasher = Blake3()

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        f1 = base / "doc1.txt"
        f2 = base / "doc2.txt"

        f1.write_text("Hello CryptaVault")
        f2.write_text("Sensitive Data")

        d1 = hasher.digest(f1.read_bytes())
        d2 = hasher.digest(f2.read_bytes())

        s1 = signer.sign(priv, d1)
        s2 = signer.sign(priv, d2)

        manifest = [
            FileManifestEntry(
                rel_path="doc1.txt",
                expected_hash=d1.hex(),
                size_bytes=len(f1.read_bytes()),
                signature=s1,
                public_key=pub,
            ),
            FileManifestEntry(
                rel_path="doc2.txt",
                expected_hash=d2.hex(),
                size_bytes=len(f2.read_bytes()),
                signature=s2,
                public_key=pub,
            ),
        ]

        # Clean report
        rep = generate_report(base, manifest)
        assert rep.is_fully_valid is True
        assert rep.total_files == 2
        assert rep.valid_files == 2
        assert rep.merkle_root is not None

        # Verify exports
        json_output = rep.to_json()
        assert "doc1.txt" in json_output
        table_output = rep.to_table()
        assert "PASS" in table_output

        # Now tamper doc2.txt (same size: 14 bytes)
        f2.write_text("Sensitive Date")  # 14 bytes, hash differs
        rep_tampered = generate_report(base, manifest)
        assert rep_tampered.is_fully_valid is False
        assert rep_tampered.tampered_files == 1
        assert rep_tampered.valid_files == 1

        # Now corrupt doc2.txt (truncated size: 9 bytes)
        f2.write_text("Sensitive")
        rep_corrupted = generate_report(base, manifest)
        assert rep_corrupted.corrupted_files == 1
