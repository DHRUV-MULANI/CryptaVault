"""Profile configuration CLI command for CryptaVault."""

from cryptavault.adaptive.profiles import SECURITY_PROFILES, resolve_slider
from cryptavault.adaptive.store import ProfileStore
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def profile_list_command() -> None:
    """Display all 6 adaptive security presets with slider ranges."""
    table = Table(
        title="CryptaVault Adaptive Security Presets", show_header=True, header_style="bold magenta"
    )
    table.add_column("Preset Level", style="bold yellow", width=14)
    table.add_column("Slider Range", style="cyan", width=14)
    table.add_column("Symmetric AEAD", style="green", width=18)
    table.add_column("Quantum Resistant", style="white", width=18)
    table.add_column("Chunk Size", style="dim", width=12)
    table.add_column("Description", style="white")

    ranges = {
        "PERFORMANCE": "0% – 20%",
        "STANDARD": "20% – 40%",
        "BALANCED": "40% – 60%",
        "STRONG": "60% – 80%",
        "PQ_STRONG": "80% – 90%",
        "MAXIMUM": "90% – 100%",
    }

    for name, p in SECURITY_PROFILES.items():
        pq_str = "YES (NIST PQC)" if p.post_quantum_protected else "NO (Classical)"
        table.add_row(
            name,
            ranges.get(name, ""),
            p.symmetric_cipher.upper(),
            pq_str,
            f"{p.chunk_size_bytes // (1024 * 1024)} MB",
            p.description,
        )

    console.print()
    console.print(table)
    console.print()


def profile_set_slider_command(slider_pct: float) -> None:
    """Set active profile by specifying slider percentage (0 to 100)."""
    try:
        profile = resolve_slider(slider_pct)
        store = ProfileStore()
        store.set_active_profile(profile.level.value)
        console.print()
        console.print(
            Panel.fit(
                f"[bold green]✓ Active Security Profile Updated[/bold green]\n"
                f"Slider: [cyan]{slider_pct:.1f}%[/cyan] → Profile: [bold yellow]{profile.level.value}[/bold yellow] ({profile.name})\n"
                f"Cipher: [white]{profile.symmetric_cipher.upper()}[/white] | Chunk: [white]{profile.chunk_size_bytes // (1024*1024)} MB[/white]\n"
                f"Post-Quantum Defense: [green]{'ACTIVE' if profile.post_quantum_protected else 'DISABLED'}[/green]",
                border_style="green",
            )
        )
        console.print()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


def profile_get_command() -> None:
    """Show current active profile."""
    store = ProfileStore()
    active = store.get_active_profile()
    console.print()
    console.print(
        f"Current Active Profile: [bold yellow]{active.level.value}[/bold yellow] ({active.name})"
    )
    console.print(f"[dim]{active.description}[/dim]\n")
