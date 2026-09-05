"""CLI commands for multi-backend storage operations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from cryptavault.storage.registry import resolve_storage
from rich.console import Console
from rich.table import Table

storage_app = typer.Typer(
    name="storage",
    help="Multi-backend storage operations (Local, Supabase, Cloudflare R2, SFTP, FTP, Cloud).",
    epilog="""
Examples:
  # Upload encrypted file to Supabase Storage:
  cryptavault storage upload backup.vault supabase://vaults

  # Upload encrypted file to Cloudflare R2 (zero egress fees):
  cryptavault storage upload backup.vault r2://my-bucket

  # List files stored in Supabase:
  cryptavault storage list supabase://vaults

  # Download from Cloudflare R2:
  cryptavault storage download r2://my-bucket/backup.vault ./restored.vault
""",
    no_args_is_help=True,
)
console = Console()


@storage_app.command("upload")
def storage_upload(
    file_path: Annotated[
        Path,
        typer.Argument(help="Local file to upload", exists=True, readable=True),
    ],
    target_uri: Annotated[
        str,
        typer.Argument(help="Storage URI or directory (e.g., local://vaults, supabase://vaults)"),
    ],
) -> None:
    """Upload an encrypted vault payload to a storage connector."""
    try:
        connector = resolve_storage(target_uri)
        connector.authenticate()

        filename = file_path.name
        remote_path = filename

        with open(file_path, "rb") as f:
            size = file_path.stat().st_size
            res_uri = connector.upload(f, remote_path, size=size)

        console.print("[bold green]✓ Upload successful![/bold green]")
        console.print(f"Target: [cyan]{res_uri}[/cyan]")
        console.print(f"Bytes transferred: [bold]{size:,}[/bold] bytes")
    except Exception as e:
        console.print(f"[bold red]Storage upload failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@storage_app.command("download")
def storage_download(
    remote_uri: Annotated[str, typer.Argument(help="Storage URI to download from")],
    output_path: Annotated[Path, typer.Argument(help="Destination local file path")],
) -> None:
    """Download an object from a storage connector."""
    try:
        connector = resolve_storage(remote_uri)
        connector.authenticate()

        # Extract filename from URI
        remote_path = remote_uri.split("://", 1)[-1]
        stream = connector.download(remote_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f_out:
            data = stream.read()
            f_out.write(data)

        console.print("[bold green]✓ Download successful![/bold green]")
        console.print(f"Saved to: [cyan]{output_path}[/cyan] ({len(data):,} bytes)")
    except Exception as e:
        console.print(f"[bold red]Storage download failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@storage_app.command("list")
def storage_list(
    storage_uri: Annotated[
        str,
        typer.Argument(help="Storage URI to list (e.g. local://./vault_store, supabase://vaults)"),
    ],
) -> None:
    """List objects in the target storage connector."""
    try:
        connector = resolve_storage(storage_uri)
        connector.authenticate()
        objects = connector.list()

        table = Table(title=f"Objects in {storage_uri}", border_style="cyan")
        table.add_column("Path", style="bold white")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Modified (UTC)", style="dim")
        table.add_column("Type", style="yellow")

        for obj in objects:
            type_str = "DIR" if obj.is_dir else "FILE"
            size_str = "-" if obj.is_dir else f"{obj.size_bytes:,} B"
            table.add_row(
                obj.path, size_str, obj.modified_at.strftime("%Y-%m-%d %H:%M:%S"), type_str
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Storage list failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e
