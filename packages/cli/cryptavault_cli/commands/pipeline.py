"""Pipeline orchestration and secure shredding CLI commands."""

from pathlib import Path

from cryptavault.adaptive.profiles import get_profile
from cryptavault.crypto.kdf import Argon2id
from cryptavault.metadata.secure_delete import secure_delete_file
from cryptavault.pipeline.orchestrator import PipelineOrchestrator
from rich.console import Console
from rich.panel import Panel

console = Console()


def pipeline_encrypt_command(
    input_file: str,
    output_file: str | None = None,
    profile_name: str = "BALANCED",
    passphrase: str = "cryptavault-demo-passphrase",
) -> None:
    """Execute full multi-stage streaming pipeline (compression + chunked AEAD + Merkle + PQ signature)."""
    in_path = Path(input_file)
    if not in_path.exists() or in_path.is_dir():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        return

    out_path = Path(output_file or f"{input_file}.vault")
    profile = get_profile(profile_name)

    # Derive key via Argon2id
    salt = b"cryptavault:pipeline:salt:v1"
    key = Argon2id().derive(
        passphrase.encode("utf-8"),
        salt,
        length=32,
        time_cost=profile.kdf_time_cost,
        memory_cost=profile.kdf_memory_cost_kib,
        parallelism=profile.kdf_parallelism,
    )

    orchestrator = PipelineOrchestrator()

    with open(in_path, "rb") as in_f, open(out_path, "wb") as out_f:
        result = orchestrator.run_encryption(
            in_f,
            out_f,
            encryption_key=key,
            profile_or_name=profile,
            file_id=in_path.name,
        )

    console.print()
    console.print(
        Panel.fit(
            f"[bold green]✓ Pipeline Encryption Completed Successfully![/bold green]\n\n"
            f"Input File: [cyan]{in_path.resolve()}[/cyan] ({result.original_size_bytes} bytes)\n"
            f"Vault Artifact: [yellow]{out_path.resolve()}[/yellow]\n"
            f"Profile: [bold magenta]{result.profile_name}[/bold magenta]\n"
            f"Compression Applied: [green]{'YES (' + str(result.compression_algo) + ')' if result.compression_applied else 'SKIPPED'}[/green]\n"
            f"Chunks Processed: [cyan]{result.chunk_count}[/cyan]\n"
            f"BLAKE3 Merkle Root: [bold white]{result.merkle_root_hex}[/bold white]\n"
            f"Throughput: [green]{result.throughput_mb_s:.1f} MB/s[/green] ({result.duration_ms:.2f} ms)",
            border_style="green",
            title="[bold cyan]CryptaVault Pipeline[/bold cyan]",
        )
    )
    console.print()


def pipeline_decrypt_command(
    input_file: str,
    output_file: str | None = None,
    profile_name: str = "BALANCED",
    passphrase: str = "cryptavault-demo-passphrase",
) -> None:
    """Decrypt a chunked vault artifact with full tag and sequence verification."""
    in_path = Path(input_file)
    if not in_path.exists():
        console.print(f"[bold red]Error: Vault artifact '{input_file}' not found![/bold red]")
        return

    out_name = input_file[:-6] if input_file.endswith(".vault") else f"{input_file}.dec"
    out_path = Path(output_file or out_name)
    profile = get_profile(profile_name)

    salt = b"cryptavault:pipeline:salt:v1"
    key = Argon2id().derive(
        passphrase.encode("utf-8"),
        salt,
        length=32,
        time_cost=profile.kdf_time_cost,
        memory_cost=profile.kdf_memory_cost_kib,
        parallelism=profile.kdf_parallelism,
    )

    orchestrator = PipelineOrchestrator()

    try:
        with open(in_path, "rb") as in_f, open(out_path, "wb") as out_f:
            decrypted_bytes = orchestrator.run_decryption(
                in_f,
                out_f,
                encryption_key=key,
                profile_or_name=profile,
            )

        console.print()
        console.print("[bold green]✓ Pipeline Decryption Successful![/bold green]")
        console.print(
            f"  [cyan]Decrypted Output:[/cyan] {out_path.resolve()} ({decrypted_bytes} bytes)"
        )
        console.print("  [green]All chunks authenticated with fail-closed integrity tags.[/green]")
        console.print()
    except Exception as e:
        console.print(f"[bold red]Pipeline Decryption Failed:[/bold red] {e}")


def shred_command(file_path: str, passes: int = 3) -> None:
    """Securely overwrite and shred a file using DoD 5220.22-M multi-pass erasure."""
    p = Path(file_path)
    if not p.exists() or p.is_dir():
        console.print(f"[bold red]Error: File '{file_path}' not found![/bold red]")
        return

    file_size = p.stat().st_size
    secure_delete_file(p, passes=passes)

    console.print()
    console.print(
        Panel.fit(
            f"[bold red]✓ File Cryptographically Shredded & Unlinked[/bold red]\n\n"
            f"Target: [dim]{p.resolve()}[/dim] ({file_size} bytes)\n"
            f"Multi-Pass Method: [yellow]DoD 5220.22-M ({passes} Overwrite Passes: 0x00, 0xFF, CSPRNG)[/yellow]\n"
            f"Final Action: Truncated to 0 bytes and unlinked from filesystem.",
            border_style="red",
            title="[bold yellow]Secure Deletion[/bold yellow]",
        )
    )
    console.print()
