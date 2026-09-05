"""Typer CLI entrypoint for CryptaVault."""

import typer
from rich.console import Console

app = typer.Typer(
    name="cryptavault",
    help="CryptaVault: Adaptive Hybrid Zero-Knowledge Cryptographic Storage CLI",
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Show CryptaVault version."""
    console.print("[bold cyan]CryptaVault CLI[/bold cyan] version [green]0.1.0[/green]")


if __name__ == "__main__":
    app()
