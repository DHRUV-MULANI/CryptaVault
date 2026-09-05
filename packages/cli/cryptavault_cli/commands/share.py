"""CLI commands for secure cryptographic sharing and QR code generation."""

from __future__ import annotations

import base64
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from cryptavault.crypto.asymmetric import Ed25519Signer
from cryptavault.sharing.package import RecipientKeyEnvelope, SharePackage
from cryptavault.sharing.password import PasswordKeyProtector
from cryptavault.sharing.qr import generate_qr_ascii
from cryptavault.sharing.timed_link import TimedShareLink
from rich.console import Console
from rich.table import Table

share_app = typer.Typer(
    name="share",
    help="Cryptographic sharing operations (timed links, passwords, QR codes, invitations).",
    epilog="""
Examples:
  # Create a 24-hour timed share link with QR code:
  cryptavault share create confidential.vault --timed 86400 --qr

  # Create a share link using your custom Cloudflare or university domain:
  cryptavault share create backup.vault --domain https://vault.yourdomain.com --timed 3600

  # Password-protect the shared file encryption key:
  cryptavault share create dataset.vault --password "RecipientSecret123!" --qr
""",
    no_args_is_help=True,
)
console = Console()


@share_app.command("create")
def share_create(
    file_path: Annotated[
        Path,
        typer.Argument(help="Ciphertext file to share", exists=True, readable=True),
    ],
    output_package: Annotated[
        Path,
        typer.Option("--output", "-o", help="Path to write the SharePackage JSON file"),
    ] = Path("share.json"),
    expires_seconds: Annotated[
        int,
        typer.Option("--timed", "-t", help="Validity duration in seconds (e.g. 3600 for 1 hour)"),
    ] = 3600,
    max_uses: Annotated[
        int,
        typer.Option("--max-uses", "-u", help="Maximum times link can be consumed (1 = one-time)"),
    ] = 1,
    password: Annotated[
        str | None,
        typer.Option("--password", "-p", help="Optional password protecting the share key"),
    ] = None,
    domain: Annotated[
        str | None,
        typer.Option(
            "--domain",
            "-d",
            help="Custom domain or Cloudflare base URL (e.g. https://vault.yourdomain.com)",
        ),
    ] = None,
    show_qr: Annotated[
        bool,
        typer.Option("--qr", help="Render ASCII QR code in terminal"),
    ] = True,
) -> None:
    """Generate a signed cryptographic SharePackage with timed link and QR code."""
    try:
        # Generate author signing key for authentication
        signer = Ed25519Signer()

        # Ephemeral file key for sharing
        file_key = os.urandom(32)
        recipients: list[RecipientKeyEnvelope] = []

        if password:
            wrapped = PasswordKeyProtector.wrap_key(file_key, password)
            recipients.append(
                RecipientKeyEnvelope(
                    recipient_id="password-protected",
                    kem_scheme="argon2id-password",
                    wrapped_key_b64=wrapped["wrapped_ciphertext_b64"],
                    extra_params={
                        "salt_b64": wrapped["salt_b64"],
                        "nonce_b64": wrapped["nonce_b64"],
                    },
                )
            )
        else:
            recipients.append(
                RecipientKeyEnvelope(
                    recipient_id="public-bearer",
                    kem_scheme="bearer-token",
                    wrapped_key_b64=base64.b64encode(file_key).decode("utf-8"),
                )
            )

        now = datetime.now(UTC)
        exp = now + timedelta(seconds=expires_seconds)
        exp_iso = exp.isoformat()

        pkg = SharePackage(
            version="1.0",
            file_id=file_path.stem,
            filename=file_path.name,
            file_size_bytes=file_path.stat().st_size,
            ciphertext_ref=f"local://{file_path.resolve()}",
            created_at=now.isoformat(),
            expires_at=exp_iso,
            max_uses=max_uses,
            recipients=recipients,
        )
        signer = Ed25519Signer()
        pub, priv = signer.keypair()
        pkg.sign(priv, pub)

        # Save package
        output_package.write_text(pkg.to_json())

        # Generate signed timed link with custom domain support
        base_domain = (
            domain or os.getenv("PUBLIC_SHARE_DOMAIN") or "https://cryptavault.local"
        ).rstrip("/")
        base_url = f"{base_domain}/share"
        link = TimedShareLink.generate_link(
            base_url=base_url,
            secret_key=file_key,
            file_id=pkg.file_id,
            validity_seconds=expires_seconds,
        )

        console.print("[bold green]✓ Cryptographic SharePackage created![/bold green]")
        console.print(f"File: [cyan]{file_path.name}[/cyan] ({pkg.file_size_bytes:,} bytes)")
        console.print(f"Expires in: [yellow]{expires_seconds // 60} minutes[/yellow] ({exp_iso})")
        console.print(f"Usage limit: [yellow]{max_uses} access(es)[/yellow]")
        console.print(f"Package saved to: [cyan]{output_package}[/cyan]")
        console.print(f"Signed link: [bold underline blue]{link}[/bold underline blue]")

        if show_qr:
            console.print("\n[bold cyan]Scan QR Code to access share:[/bold cyan]")
            qr_text = generate_qr_ascii(link)
            console.print(qr_text)

    except Exception as e:
        console.print(f"[bold red]Share creation failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@share_app.command("inspect")
def share_inspect(
    package_file: Annotated[
        Path,
        typer.Argument(help="Path to share package JSON file", exists=True, readable=True),
    ],
) -> None:
    """Inspect and verify the cryptographic signature of a SharePackage."""
    try:
        pkg = SharePackage.from_json(package_file.read_text())
        is_sig_valid = pkg.verify_signature()
        is_expired = pkg.is_expired()

        status_text = (
            "[bold green]VALID[/bold green]"
            if is_sig_valid
            else "[bold red]SIGNATURE INVALID[/bold red]"
        )
        expiry_text = (
            "[bold red]EXPIRED[/bold red]" if is_expired else "[bold green]ACTIVE[/bold green]"
        )

        table = Table(title=f"SharePackage: {package_file.name}", border_style="cyan")
        table.add_column("Property", style="bold white")
        table.add_column("Value", style="cyan")

        table.add_row("File ID", pkg.file_id)
        table.add_row("Filename", pkg.filename or "(unnamed)")
        table.add_row("File Size", f"{pkg.file_size_bytes:,} bytes")
        table.add_row("Ciphertext Ref", pkg.ciphertext_ref)
        table.add_row("Signature Integrity", status_text)
        table.add_row("Expiry Status", expiry_text)
        table.add_row("Expires At", str(pkg.expires_at))
        table.add_row("Max Uses", str(pkg.max_uses or "Unlimited"))
        table.add_row("Recipients Count", str(len(pkg.recipients)))

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Inspect failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@share_app.command("qr")
def share_qr(
    data: Annotated[str, typer.Argument(help="URL or text data to encode as QR code")],
) -> None:
    """Render an ASCII QR code in the terminal."""
    try:
        qr_ascii = generate_qr_ascii(data)
        console.print(qr_ascii)
    except Exception as e:
        console.print(f"[bold red]QR generation failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e
