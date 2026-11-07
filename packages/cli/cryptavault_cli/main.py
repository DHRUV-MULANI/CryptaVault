"""Typer CLI entrypoint for CryptaVault with deep help examples and interactive academy."""

import typer
from rich.console import Console

from cryptavault_cli.commands.ai import ai_app
from cryptavault_cli.commands.benchmark import run_benchmark
from cryptavault_cli.commands.crypto import decrypt_command, encrypt_command
from cryptavault_cli.commands.integrity import merkle_command, sign_command, verify_command
from cryptavault_cli.commands.keys import (
    inspect_keystore_command,
    keygen_command,
    recover_key_command,
)
from cryptavault_cli.commands.pipeline import (
    pipeline_decrypt_command,
    pipeline_encrypt_command,
    shred_command,
)
from cryptavault_cli.commands.profile import (
    profile_get_command,
    profile_list_command,
    profile_set_slider_command,
)
from cryptavault_cli.commands.profiles import profiles_command
from cryptavault_cli.commands.share import share_app
from cryptavault_cli.commands.status import status_command
from cryptavault_cli.commands.storage import storage_app
from cryptavault_cli.commands.teach import teach_app

app = typer.Typer(
    name="cryptavault",
    help="CryptaVault: Adaptive Hybrid Zero-Knowledge Cryptographic Storage CLI",
    epilog="""
Quickstart Examples:
  # Check hardware acceleration and post-quantum readiness:
  cryptavault status

  # Learn any cryptographic concept interactively:
  cryptavault teach zero-knowledge
  cryptavault teach pqc

  # Encrypt a file using the full streaming pipeline:
  cryptavault pipeline-encrypt confidential.pdf -o confidential.vault --profile MAXIMUM

  # Upload to Supabase Storage or Cloudflare R2:
  cryptavault storage upload confidential.vault supabase://vaults
  cryptavault storage upload confidential.vault r2://my-bucket

  # Create a timed share link with custom domain and QR code:
  cryptavault share create confidential.vault --domain https://vault.yourdomain.com --timed 3600 --qr
""",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

# Sub-apps
profile_app = typer.Typer(
    name="profile",
    help="Manage and configure adaptive security profiles (PERFORMANCE -> MAXIMUM).",
    epilog="""
Examples:
  cryptavault profile list
  cryptavault profile set --slider 75.0
  cryptavault profile get
""",
    no_args_is_help=True,
)
app.add_typer(profile_app, name="profile")
app.add_typer(storage_app, name="storage")
app.add_typer(share_app, name="share")
app.add_typer(ai_app, name="ai")
app.add_typer(teach_app, name="teach")


@profile_app.command("list")
def profile_list() -> None:
    """List all 6 security presets with slider ranges."""
    profile_list_command()


@profile_app.command("set")
def profile_set(
    slider: float = typer.Option(
        ..., "--slider", "-s", help="Slider percentage (0.0 to 100.0) mapping to security tier"
    ),
) -> None:
    """Set active profile by specifying slider percentage (0 to 100)."""
    profile_set_slider_command(slider)


@profile_app.command("get")
def profile_get() -> None:
    """Display current active security profile."""
    profile_get_command()


@app.command(name="version")
def version() -> None:
    """Display CryptaVault version and build info."""
    console.print(
        "[bold cyan]CryptaVault CLI[/bold cyan] version [green]1.0.0[/green] (Release v1.0.0 Production)"
    )


@app.command(
    name="status",
    epilog="""
Example:
  cryptavault status
""",
)
def status() -> None:
    """Display cryptographic hardware acceleration, liboqs status, and zero-knowledge bounds."""
    status_command()


@app.command(
    name="profiles",
    epilog="""
Example:
  cryptavault profiles
""",
)
def profiles() -> None:
    """List all adaptive cryptographic security profiles (PERFORMANCE through MAXIMUM)."""
    profiles_command()


@app.command(
    name="benchmark",
    epilog="""
Example:
  cryptavault benchmark
""",
)
def benchmark() -> None:
    """Execute live micro-benchmarks across AES-NI, ChaCha20, BLAKE3, Kyber-768, Dilithium-3, and Argon2id."""
    run_benchmark()


@app.command(
    name="keygen",
    epilog="""
Examples:
  cryptavault keygen -o vault.keystore -p "MySecurePassphrase123!"
  cryptavault keygen
""",
)
def keygen(
    output: str = typer.Option(
        "vault.keystore", "--output", "-o", help="Output path for encrypted keystore file"
    ),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Passphrase to encrypt keystore (prompted if omitted)"
    ),
) -> None:
    """Generate a new 256-bit Master Key with BIP-39 24-word recovery phrase and encrypted keystore."""
    keygen_command(output_keystore=output, passphrase=passphrase)


@app.command(
    name="inspect-keystore",
    epilog="""
Example:
  cryptavault inspect-keystore -k vault.keystore -p "MySecurePassphrase123!"
""",
)
def inspect_keystore(
    keystore: str = typer.Option(
        "vault.keystore", "--keystore", "-k", help="Path to keystore file"
    ),
    passphrase: str = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Passphrase to decrypt keystore (prompted if omitted)",
    ),
) -> None:
    """Inspect encrypted keystore envelope metadata and key fingerprints."""
    inspect_keystore_command(keystore_path=keystore, passphrase=passphrase)


@app.command(
    name="recover-key",
    epilog="""
Example:
  cryptavault recover-key "shield matrix quantum cipher vault entropy lattice vector hybrid secure zero knowledge argon blake atomic dynamic crystal dilithium stream poly merkle audit proof verdict"
""",
)
def recover_key(
    mnemonic: str = typer.Argument(..., help="24-word BIP-39 recovery mnemonic phrase"),
) -> None:
    """Recover and reconstruct Master Key fingerprint from a BIP-39 mnemonic phrase."""
    recover_key_command(mnemonic_phrase=mnemonic)


@app.command(
    name="encrypt",
    epilog="""
Examples:
  # Encrypt a file with BALANCED profile:
  cryptavault encrypt -i secrets.txt -o secrets.enc --profile BALANCED

  # Encrypt string directly:
  cryptavault encrypt -t "My secret database password" -p "Passphrase123"
""",
)
def encrypt(
    input_file: str = typer.Option(None, "--input", "-i", help="Path of plaintext file to encrypt"),
    text: str = typer.Option(None, "--text", "-t", help="Raw string plaintext to encrypt"),
    output_file: str = typer.Option(
        None, "--output", "-o", help="Output file path for ciphertext envelope"
    ),
    profile: str = typer.Option(
        "BALANCED", "--profile", help="Security profile: PERFORMANCE, BALANCED, HIGH, MAXIMUM"
    ),
    passphrase: str = typer.Option(
        "cryptavault-demo-passphrase",
        "--passphrase",
        "-p",
        help="Passphrase for key derivation",
    ),
) -> None:
    """Encrypt a file or text string using adaptive authenticated encryption."""
    encrypt_command(
        input_path=input_file,
        text=text,
        output_path=output_file,
        profile_name=profile,
        passphrase=passphrase,
    )


@app.command(
    name="decrypt",
    epilog="""
Examples:
  cryptavault decrypt -i secrets.enc -o secrets_decrypted.txt -p "Passphrase123"
  cryptavault decrypt -c "CV1:BALANCED:..." -p "Passphrase123"
""",
)
def decrypt(
    input_file: str = typer.Option(None, "--input", "-i", help="Path of encrypted ciphertext file"),
    ciphertext: str = typer.Option(
        None, "--ciphertext", "-c", help="Base64 ciphertext envelope string"
    ),
    output_file: str = typer.Option(
        None, "--output", "-o", help="Output file path for decrypted plaintext"
    ),
    passphrase: str = typer.Option(
        "cryptavault-demo-passphrase",
        "--passphrase",
        "-p",
        help="Passphrase used for decryption",
    ),
) -> None:
    """Decrypt a file or base64 envelope with authentication tag verification."""
    decrypt_command(
        input_path=input_file,
        ciphertext_b64=ciphertext,
        output_path=output_file,
        passphrase=passphrase,
    )


@app.command(
    name="pipeline-encrypt",
    epilog="""
Examples:
  # High-speed processing for large videos/archives:
  cryptavault pipeline-encrypt dataset.csv -o dataset.vault --profile PERFORMANCE

  # Maximum post-quantum lattice security + high Zstd compression:
  cryptavault pipeline-encrypt medical_records.pdf -o medical.vault --profile MAXIMUM
""",
)
def pipeline_encrypt(
    input_file: str = typer.Argument(
        ..., help="Path of file to process through streaming pipeline"
    ),
    output_file: str = typer.Option(None, "--output", "-o", help="Output path for .vault artifact"),
    profile: str = typer.Option("BALANCED", "--profile", help="Security profile tier"),
    passphrase: str = typer.Option(
        "cryptavault-demo-passphrase", "--passphrase", "-p", help="Passphrase"
    ),
) -> None:
    """Process a file through the full streaming pipeline (compression + chunked AEAD + Merkle + PQC sig)."""
    pipeline_encrypt_command(
        input_file=input_file,
        output_file=output_file,
        profile_name=profile,
        passphrase=passphrase,
    )


@app.command(
    name="pipeline-decrypt",
    epilog="""
Example:
  cryptavault pipeline-decrypt dataset.vault -o dataset_restored.csv --profile MAXIMUM
""",
)
def pipeline_decrypt(
    vault_file: str = typer.Argument(..., help="Path to encrypted .vault artifact"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output path for decrypted file"),
    profile: str = typer.Option("BALANCED", "--profile", help="Security profile tier"),
    passphrase: str = typer.Option(
        "cryptavault-demo-passphrase", "--passphrase", "-p", help="Passphrase"
    ),
) -> None:
    """Decrypt a chunked vault artifact with streaming fail-closed tag verification."""
    pipeline_decrypt_command(
        input_file=vault_file,
        output_file=output_file,
        profile_name=profile,
        passphrase=passphrase,
    )


@app.command(
    name="shred",
    epilog="""
Example:
  cryptavault shred obsolete_database.db --passes 3
""",
)
def shred(
    file_path: str = typer.Argument(..., help="Path of file to cryptographically shred"),
    passes: int = typer.Option(
        3, "--passes", help="Number of overwrite passes (default 3, DoD 5220.22-M)"
    ),
) -> None:
    """Permanently destroy a file using DoD 5220.22-M multi-pass overwrite before unlinking."""
    shred_command(file_path=file_path, passes=passes)


@app.command(
    name="sign",
    epilog="""
Example:
  cryptavault sign release.tar.gz --output-sig release.sig
""",
)
def sign(
    file_path: str = typer.Argument(..., help="Path of file to sign"),
    output_sig: str = typer.Option(None, "--output-sig", help="Output path for binary signature"),
) -> None:
    """Sign a file using Post-Quantum Hybrid Signature (Ed25519 + Dilithium-3)."""
    sign_command(file_path=file_path, output_sig_path=output_sig)


@app.command(
    name="verify",
    epilog="""
Example:
  cryptavault verify release.tar.gz --sig release.sig --pubkey release.pub
""",
)
def verify(
    file_path: str = typer.Argument(..., help="Path of file to verify"),
    sig_path: str = typer.Option(..., "--sig", "-s", help="Path to signature file"),
    pub_key: str = typer.Option(..., "--pubkey", "-k", help="Path to public key file"),
) -> None:
    """Verify file integrity and authenticity against Post-Quantum Hybrid signature."""
    verify_command(file_path=file_path, sig_path=sig_path, pub_key_path=pub_key)


@app.command(
    name="merkle",
    epilog="""
Example:
  cryptavault merkle --dir ./data
""",
)
def merkle(
    dir_path: str = typer.Option(
        ".", "--dir", "-d", help="Directory path to compute Merkle Tree for"
    ),
) -> None:
    """Compute BLAKE3 Merkle Tree root hash and audit proof for all files in a directory."""
    merkle_command(dir_path=dir_path)


if __name__ == "__main__":
    app()
