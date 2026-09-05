"""Automated unit and integration tests for CryptaVault CLI commands."""

from pathlib import Path

from cryptavault_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_version() -> None:
    """Verify cryptavault version output."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "CryptaVault CLI" in result.output
    assert "0.1.0" in result.output


def test_cli_status() -> None:
    """Verify cryptavault status displays zero-knowledge boundary and hardware info."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Zero-Knowledge Boundary" in result.output
    assert "ENFORCED" in result.output
    assert "AES-NI" in result.output


def test_cli_profiles() -> None:
    """Verify cryptavault profiles lists security tiers."""
    result = runner.invoke(app, ["profiles"])
    assert result.exit_code == 0
    assert "CryptaVault Adaptive Security Profiles" in result.output
    assert "BALANCED" in result.output
    assert "MAXIMUM" in result.output


def test_cli_benchmark() -> None:
    """Verify cryptavault benchmark executes successfully across all primitives."""
    result = runner.invoke(app, ["benchmark"])
    assert result.exit_code == 0
    assert "AES-256-GCM" in result.output
    assert "ChaCha20-Poly1305" in result.output
    assert "BLAKE3" in result.output
    assert "ML-KEM-768" in result.output
    assert "Argon2id" in result.output


def test_cli_encrypt_decrypt_roundtrip(tmp_path: Path) -> None:
    """Verify encrypt and decrypt round-trip with integrity tag verification."""
    secret_text = "Highly confidential data tested via CLI"
    test_file = tmp_path / "secret.txt"
    test_file.write_text(secret_text)

    enc_file = tmp_path / "secret.enc"
    dec_file = tmp_path / "secret.dec"

    # Encrypt
    enc_res = runner.invoke(
        app,
        [
            "encrypt",
            "--input",
            str(test_file),
            "--output",
            str(enc_file),
            "--profile",
            "BALANCED",
            "--passphrase",
            "test-passphrase-42",
        ],
    )
    assert enc_res.exit_code == 0
    assert enc_file.exists()

    # Decrypt
    dec_res = runner.invoke(
        app,
        [
            "decrypt",
            "--input",
            str(enc_file),
            "--output",
            str(dec_file),
            "--passphrase",
            "test-passphrase-42",
        ],
    )
    assert dec_res.exit_code == 0
    assert dec_file.exists()
    assert dec_file.read_text() == secret_text


def test_cli_tamper_detection(tmp_path: Path) -> None:
    """Verify that tampered ciphertext causes decryption failure (fail-closed)."""
    enc_file = tmp_path / "tampered.enc"

    runner.invoke(
        app,
        [
            "encrypt",
            "--text",
            "Authenticity test",
            "--output",
            str(enc_file),
            "--passphrase",
            "test-pass",
        ],
    )

    # Corrupt last byte (the tag)
    data = bytearray(enc_file.read_bytes())
    data[-1] ^= 0xFF
    enc_file.write_bytes(bytes(data))

    dec_res = runner.invoke(
        app,
        [
            "decrypt",
            "--input",
            str(enc_file),
            "--passphrase",
            "test-pass",
        ],
    )
    assert "Decryption failed" in dec_res.output


def test_cli_sign_and_verify(tmp_path: Path) -> None:
    """Verify post-quantum hybrid signing and verification via CLI."""
    doc = tmp_path / "document.txt"
    doc.write_text("Integrity validation content")

    sig = tmp_path / "document.sig"
    pub = tmp_path / "document.txt.pub"

    # Sign
    sign_res = runner.invoke(
        app,
        [
            "sign",
            str(doc),
            "--output-sig",
            str(sig),
        ],
    )
    assert sign_res.exit_code == 0
    assert sig.exists()
    assert pub.exists()

    # Verify valid
    vfy_res = runner.invoke(
        app,
        [
            "verify",
            str(doc),
            "--sig",
            str(sig),
            "--pubkey",
            str(pub),
        ],
    )
    assert vfy_res.exit_code == 0
    assert "SIGNATURE VALID" in vfy_res.output

    # Tamper file
    doc.write_text("Tampered content injected")
    vfy_tamper = runner.invoke(
        app,
        [
            "verify",
            str(doc),
            "--sig",
            str(sig),
            "--pubkey",
            str(pub),
        ],
    )
    assert vfy_tamper.exit_code == 0
    assert "SIGNATURE INVALID" in vfy_tamper.output


def test_cli_merkle(tmp_path: Path) -> None:
    """Verify Merkle tree audit and O(log n) proof verification."""
    (tmp_path / "file1.txt").write_text("File 1")
    (tmp_path / "file2.txt").write_text("File 2")
    (tmp_path / "file3.txt").write_text("File 3")

    res = runner.invoke(app, ["merkle", "--dir", str(tmp_path)])
    assert res.exit_code == 0
    assert "Merkle Tree Audit Summary" in res.output
    assert "SUCCESS" in res.output


def test_cli_keygen_and_inspect(tmp_path: Path) -> None:
    """Verify keygen creates keystore and BIP-39 recovery bundle."""
    ks_path = tmp_path / "test.keystore"
    res = runner.invoke(
        app,
        [
            "keygen",
            "--output",
            str(ks_path),
            "--passphrase",
            "KeystorePass123!",
        ],
    )
    assert res.exit_code == 0
    assert ks_path.exists()
    assert ks_path.with_suffix(".recovery.json").exists()

    # Test inspect
    inspect_res = runner.invoke(
        app,
        [
            "inspect-keystore",
            "--keystore",
            str(ks_path),
            "--passphrase",
            "KeystorePass123!",
        ],
    )
    assert inspect_res.exit_code == 0
    assert "Keystore Contents" in inspect_res.output
    assert "MASTER" in inspect_res.output
