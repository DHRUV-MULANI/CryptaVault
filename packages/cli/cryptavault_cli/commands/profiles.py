"""Security profiles command for CryptaVault CLI."""

from cryptavault.adaptive.profiles import SECURITY_PROFILES
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def profiles_command() -> None:
    """Display all adaptive cryptographic security profiles with specifications."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]CryptaVault Adaptive Security Profiles[/bold cyan]\n"
            "[dim]Dynamic crypto profiles selected based on hardware capabilities, network, and policy[/dim]",
            border_style="cyan",
        )
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Profile Level", style="bold yellow", width=14)
    table.add_column("Symmetric AEAD", style="cyan", width=18)
    table.add_column("KEM Algorithm", style="green", width=22)
    table.add_column("Signature", style="blue", width=14)
    table.add_column("KDF / Memory", style="white", width=18)
    table.add_column("Chunk Size", style="dim", width=12)
    table.add_column("Description & Threat Model", style="white")

    for name, profile in SECURITY_PROFILES.items():
        kdf_info = f"{profile.kdf_algorithm} ({profile.kdf_memory_cost_kib // 1024}MB, t={profile.kdf_time_cost})"
        chunk_info = (
            f"{profile.chunk_size_bytes // 1024} KB"
            if profile.chunk_size_bytes < 1048576
            else f"{profile.chunk_size_bytes // 1048576} MB"
        )

        table.add_row(
            name,
            profile.symmetric_cipher.upper(),
            profile.kem_algorithm,
            profile.signature_algorithm.upper(),
            kdf_info,
            chunk_info,
            profile.description,
        )

    console.print(table)
    console.print()
