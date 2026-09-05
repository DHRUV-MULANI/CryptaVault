"""CLI commands for AI-assisted cryptographic advisory and concept explanation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from cryptavault.ai.knowledge_base import list_concepts, lookup_concept
from cryptavault.ai.rules import RuleBasedRecommender
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

ai_app = typer.Typer(
    name="ai",
    help="AI-assisted cryptographic advisory and educational assistant.",
    no_args_is_help=True,
)
console = Console()


@ai_app.command("advise")
def ai_advise(
    file_path: Annotated[
        Path,
        typer.Argument(
            help="File to evaluate for cryptographic and compression recommendations", exists=True
        ),
    ],
    profile: Annotated[
        str,
        typer.Option(
            "--profile", "-p", help="Security profile tier (PERFORMANCE, BALANCED, STRONG, MAXIMUM)"
        ),
    ] = "BALANCED",
) -> None:
    """Analyze file characteristics and recommend optimal ciphers, chunk size, and compression."""
    try:
        size = file_path.stat().st_size
        header = b""
        with open(file_path, "rb") as f:
            header = f.read(512)

        rec = RuleBasedRecommender.advise(
            filename=file_path.name,
            size_bytes=size,
            profile_level=profile,
            header_sample=header,
        )

        table = Table(title=f"AI Cryptographic Advisory: {file_path.name}", border_style="cyan")
        table.add_column("Parameter", style="bold white")
        table.add_column("Recommended Setting", style="cyan")

        table.add_row("Encryption Cipher", rec.encryption_algo)
        table.add_row("Compression Mode", rec.compression_mode.upper())
        table.add_row("Streaming Chunk Size", f"{rec.chunk_size_bytes // (1024 * 1024)} MB")
        table.add_row("Parallel Thread Workers", str(rec.parallel_workers))
        table.add_row("Forward Secrecy Ratchet", "ACTIVE" if rec.forward_secrecy else "DISABLED")
        table.add_row("Multi-Layer AEAD", "ACTIVE" if rec.multi_layer else "DISABLED")

        console.print(table)
        console.print(
            Panel(
                f"[italic green]{rec.rationale}[/italic green]",
                title="Engineering Rationale",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[bold red]Advisory analysis failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@ai_app.command("explain")
def ai_explain(
    concept: Annotated[
        str,
        typer.Argument(
            help="Cryptographic concept to explain (e.g. 'kyber', 'argon2id', 'merkle')"
        ),
    ],
) -> None:
    """Look up educational explanations of cryptographic concepts in the offline knowledge base."""
    data = lookup_concept(concept)
    if not data:
        console.print(f"[bold red]Concept not found:[/bold red] '{concept}'")
        console.print(f"Available concepts: [dim]{', '.join(list_concepts())}[/dim]")
        raise typer.Exit(code=1)

    table = Table(title=f"CryptaVault Knowledge Base: {data['name']}", border_style="green")
    table.add_column("Property", style="bold white")
    table.add_column("Details", style="cyan")

    table.add_row("Category", data.get("category", "-"))
    table.add_row("Description", data.get("description", "-"))
    table.add_row("Security Level", data.get("security_level", "-"))
    table.add_row("When to Use", data.get("when_to_use", "-"))
    table.add_row("Standard", data.get("nist_standard", "-"))
    if "hardware_acceleration" in data:
        table.add_row("Hardware Acceleration", data["hardware_acceleration"])

    console.print(table)


@ai_app.command("concepts")
def ai_list_concepts() -> None:
    """List all registered cryptographic concepts in the knowledge base."""
    concepts = list_concepts()
    console.print(
        f"[bold cyan]Registered Cryptographic Concepts ({len(concepts)} total):[/bold cyan]"
    )
    for c in concepts:
        console.print(f"  • [green]{c}[/green]")
