"""Comprehensive tests for CryptaVault KMS (Phase P4).

Tests:
- Key hierarchy and multi-tier wrapping/unwrapping
- Keystore encryption, persistence, wrong password rejection, and tamper detection
- Key lifecycle: generation, rotation, cascade re-wrapping, and zeroing destruction
- BIP-39 24-word mnemonic backup, restore, and validation
- Key import/export interop (PEM, hex, raw) and strength validation
"""

import os
import tempfile
from pathlib import Path

import pytest
from cryptavault.keys.backup import InvalidMnemonicError, KeyRecoveryManager
from cryptavault.keys.hierarchy import KeyDescriptor, KeyStatus, KeyTier, KeyTree
from cryptavault.keys.io import WeakKeyError, export_key, import_key
from cryptavault.keys.keystore import Keystore, KeystoreAuthError
from cryptavault.keys.operations import destroy_key, generate_key, rotate_key

# ====================================================================
# 1. Key Hierarchy & Wrapping Tests
# ====================================================================


def test_key_hierarchy_wrap_unwrap() -> None:
    """Ensure parent keys can wrap and unwrap children keys."""
    tree = KeyTree()
    master_key = os.urandom(32)

    # Add master descriptor
    master_desc = KeyDescriptor(
        id="master_root",
        tier=KeyTier.MASTER,
        algorithm="argon2id",
    )
    tree.add_key(master_desc)
    assert tree.find_root() == master_desc

    # Wrap a data key under master
    data_raw_key = os.urandom(32)
    data_desc = tree.wrap_raw_key(
        raw_key=data_raw_key,
        parent_raw_key=master_key,
        key_id="data_key_01",
        tier=KeyTier.DATA,
        parent_id="master_root",
    )

    assert data_desc.parent_id == "master_root"
    assert len(data_desc.wrapped_key) > 0

    # Unwrap data key
    unwrapped = tree.unwrap_key("data_key_01", master_key)
    assert unwrapped == data_raw_key


# ====================================================================
# 2. Encrypted Keystore Tests
# ====================================================================


def test_keystore_save_and_load_roundtrip() -> None:
    """Save encrypted keystore and load it back with the correct master password."""
    tree = KeyTree()
    master_key = os.urandom(32)
    data_key = os.urandom(32)

    tree.add_key(KeyDescriptor(id="root", tier=KeyTier.MASTER, algorithm="argon2id"))
    tree.wrap_raw_key(data_key, master_key, "data_01", parent_id="root")

    keystore = Keystore(time_cost=1, memory_cost=32768, parallelism=2)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        keystore.save_file(tree, "CorrectVaultPassword!#9", tmp.name)

        # Load with correct password
        loaded_tree = keystore.load_file("CorrectVaultPassword!#9", tmp.name)
        assert len(loaded_tree.list_keys()) == 2
        assert loaded_tree.unwrap_key("data_01", master_key) == data_key

        # Load with WRONG password must fail
        with pytest.raises(KeystoreAuthError):
            keystore.load_file("WrongPassword", tmp.name)

        # Tampered envelope must fail
        tampered_content = Path(tmp.name).read_text()
        tampered_content = tampered_content.replace('"version": 1', '"version": 1, "tamper": true')
        # Modify a byte in encrypted blob
        import json

        data = json.loads(Path(tmp.name).read_text())
        blob = bytearray(bytes.fromhex(data["encrypted_blob"]))
        blob[0] ^= 0x01
        data["encrypted_blob"] = blob.hex()
        Path(tmp.name).write_text(json.dumps(data))

        with pytest.raises(KeystoreAuthError):
            keystore.load_file("CorrectVaultPassword!#9", tmp.name)

    os.unlink(tmp.name)


# ====================================================================
# 3. Lifecycle Operations (Generate, Rotate, Destroy)
# ====================================================================


def test_key_generation_and_rotation() -> None:
    """Test key generation, rotation with cascade re-wrap, and destruction."""
    tree = KeyTree()
    master_key = os.urandom(32)
    tree.add_key(KeyDescriptor(id="master", tier=KeyTier.MASTER, algorithm="argon2id"))

    # Generate data key
    data_desc, data_raw = generate_key(
        tree=tree,
        tier=KeyTier.DATA,
        parent_raw_key=master_key,
        parent_id="master",
    )
    assert data_desc.status == KeyStatus.ACTIVE

    # Generate child share key wrapped by data key
    share_desc, share_raw = generate_key(
        tree=tree,
        tier=KeyTier.SHARE,
        parent_raw_key=data_raw,
        parent_id=data_desc.id,
    )

    # Rotate data key
    new_data_desc, new_data_raw = rotate_key(
        tree=tree,
        key_id=data_desc.id,
        parent_raw_key=master_key,
        old_raw_key=data_raw,
    )
    assert data_desc.status == KeyStatus.RETIRED
    assert new_data_desc.status == KeyStatus.ACTIVE
    assert new_data_desc.version == 2

    # Child should be unwrap-able with the NEW data key
    re_unwrapped_share = tree.unwrap_key(share_desc.id, new_data_raw)
    assert re_unwrapped_share == share_raw

    # Destroy key
    raw_buffer = bytearray(data_raw)
    destroy_key(tree, data_desc.id, raw_buffer=raw_buffer)
    assert data_desc.status == KeyStatus.DESTROYED
    assert data_desc.wrapped_key == ""
    assert all(b == 0 for b in raw_buffer)


# ====================================================================
# 4. BIP-39 Mnemonic Backup & Recovery
# ====================================================================


def test_bip39_recovery_roundtrip() -> None:
    """Export 24-word recovery bundle and recover master key."""
    mgr = KeyRecoveryManager()
    master_key = os.urandom(32)

    mnemonic_phrase, bundle = mgr.export_recovery_bundle(master_key)
    words = mnemonic_phrase.split()
    assert len(words) == 24
    assert bundle["word_count"] == 24

    # Verify offline
    assert mgr.verify_recovery_bundle(mnemonic_phrase, bundle) is True

    # Recover master key
    recovered = mgr.import_recovery_bundle(mnemonic_phrase, bundle)
    assert recovered == master_key

    # Invalid word should raise InvalidMnemonicError
    corrupted_words = words[:]
    corrupted_words[0] = "xyznotaword"
    with pytest.raises(InvalidMnemonicError):
        mgr.import_recovery_bundle(" ".join(corrupted_words), bundle)


# ====================================================================
# 5. Key Import / Export Interop & Weak Key Rejection
# ====================================================================


def test_key_import_export_raw_and_hex() -> None:
    """Test importing and exporting raw/hex keys."""
    raw_32 = os.urandom(32)
    exported_hex = export_key(raw_32, algorithm="aes-256-gcm", export_format="hex")
    assert exported_hex.decode("utf-8") == raw_32.hex()

    desc, imported_key = import_key(exported_hex, algorithm="aes-256-gcm")
    assert imported_key == raw_32
    assert desc.metadata["format"] == "hex"


def test_weak_key_rejected_on_import() -> None:
    """Importing symmetric keys with fewer than 256 bits must be rejected."""
    short_key = os.urandom(16)  # 128 bits is rejected for data keys
    with pytest.raises(WeakKeyError, match="minimum 256 bits"):
        import_key(short_key, algorithm="aes-256-gcm")
