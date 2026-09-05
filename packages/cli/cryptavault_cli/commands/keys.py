"""Key management commands for CryptaVault CLI."""

import json
import os
import uuid
from pathlib import Path

from cryptavault.keys.backup import KeyRecoveryManager
from cryptavault.keys.hierarchy import KeyDescriptor, KeyTier, KeyTree
from cryptavault.keys.keystore import Keystore
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()


def keygen_command(
    output_keystore: str = "vault.keystore",
    passphrase: str | None = None,
    interactive: bool = True,
) -> None:
    """Generate a new Master Key, display BIP-39 recovery phrase, and store in encrypted envelope."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]CryptaVault Zero-Knowledge Master Key Generator[/bold cyan]\n"
            "[dim]Derives a 256-bit cryptographically secure root key with BIP-39 mnemonic phrase backup[/dim]",
            border_style="cyan",
        )
    )

    # 1. Generate 32-byte Master Key & BIP-39 Recovery Bundle
    master_key_bytes = os.urandom(32)
    recovery_mgr = KeyRecoveryManager()
    mnemonic, bundle = recovery_mgr.export_recovery_bundle(master_key_bytes)

    # 2. Display Mnemonic securely
    words = mnemonic.split()
    mnemonic_table = Table(
        title="[bold red]BIP-39 24-Word Master Recovery Phrase[/bold red]", show_header=False
    )
    for i in range(0, len(words), 4):
        chunk = [
            f"[bold yellow]{idx+1:02d}.[/bold yellow] [white]{w}[/white]"
            for idx, w in enumerate(words[i : i + 4], start=i)
        ]
        mnemonic_table.add_row(*chunk)

    console.print(mnemonic_table)
    console.print(
        "[bold red]WARNING:[/bold red] Write this phrase down on paper! It is the [italic]ONLY[/italic] way to recover your data if you lose your password.\n"
        "[dim]CryptaVault operates with zero knowledge: no server or administrator can reset your keys.[/dim]\n"
    )

    # 3. Prompt for passphrase if not supplied
    if not passphrase:
        if interactive:
            passphrase = Prompt.ask(
                "[bold green]Enter a passphrase to protect your local keystore[/bold green]",
                password=True,
            )
            pass_confirm = Prompt.ask("[bold green]Confirm passphrase[/bold green]", password=True)
            if passphrase != pass_confirm:
                console.print("[bold red]Error: Passphrases do not match![/bold red]")
                return
        else:
            passphrase = "default-development-passphrase"

    # 4. Save to encrypted keystore file using KeyTree
    tree = KeyTree()
    key_id = f"mk-{uuid.uuid4().hex[:8]}"
    master_desc = KeyDescriptor(
        id=key_id,
        tier=KeyTier.MASTER,
        algorithm="aes-256-gcm",
        parent_id=None,
        wrapped_key=master_key_bytes.hex(),
        metadata={"purpose": "Root Master Encryption Key", "recovery_bundle": bundle},
    )
    tree.add_key(master_desc)

    out_path = Path(output_keystore).resolve()
    keystore = Keystore()
    keystore.save_file(tree, passphrase, str(out_path))

    # Save recovery bundle json alongside for emergency offline recovery
    bundle_path = out_path.with_suffix(".recovery.json")
    bundle_path.write_text(json.dumps(bundle, indent=2))

    console.print(f"[bold green]✓ Keystore saved securely to:[/bold green] [cyan]{out_path}[/cyan]")
    console.print(f"[bold green]✓ Master Key ID:[/bold green] [yellow]{key_id}[/yellow]")
    console.print(
        f"[bold green]✓ Emergency Recovery Bundle saved to:[/bold green] [cyan]{bundle_path}[/cyan]"
    )
    console.print()


def inspect_keystore_command(
    keystore_path: str = "vault.keystore",
    passphrase: str | None = None,
) -> None:
    """Inspect encrypted keystore envelope without exposing secret keys."""
    path = Path(keystore_path)
    if not path.exists():
        console.print(f"[bold red]Error: Keystore file '{keystore_path}' not found![/bold red]")
        return

    if not passphrase:
        passphrase = Prompt.ask("[bold green]Enter keystore passphrase[/bold green]", password=True)
    try:
        ks = Keystore()
        tree = ks.load_file(passphrase, str(path))
        table = Table(
            title=f"[bold]Keystore Contents ({path.name})[/bold]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Key ID", style="cyan", width=20)
        table.add_column("Tier", style="yellow", width=14)
        table.add_column("Algorithm", style="green", width=16)
        table.add_column("Created At", style="dim", width=24)
        table.add_column("Fingerprint (SHA-256)", style="white")

        from cryptavault.crypto.hash import Sha256

        sha = Sha256()
        for desc in tree.list_keys():
            raw = bytes.fromhex(desc.wrapped_key)
            fp = sha.digest(raw)[:16].hex()
            table.add_row(desc.id, desc.tier.value, desc.algorithm, str(desc.created_at), fp)

        console.print()
        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"[bold red]Failed to decrypt keystore:[/bold red] {e}")


def recover_key_command(
    mnemonic_phrase: str,
    bundle_file: str | None = None,
) -> None:
    """Validate and derive master key from BIP-39 recovery phrase and bundle."""
    recovery_mgr = KeyRecoveryManager()
    try:
        if bundle_file:
            bf = Path(bundle_file)
            if not bf.exists():
                console.print(f"[bold red]Bundle file '{bundle_file}' not found![/bold red]")
                return
            bundle = json.loads(bf.read_text())
            master_key = recovery_mgr.import_recovery_bundle(mnemonic_phrase, bundle)
            from cryptavault.crypto.hash import Sha256

            fp = Sha256().digest(master_key)[:16].hex()
            console.print()
            console.print(
                "[bold green]✓ Successfully unwrapped Master Key from recovery bundle![/bold green]"
            )
            console.print(f"[bold cyan]Master Key Fingerprint:[/bold cyan] [yellow]{fp}[/yellow]")
            console.print("[dim]Zero-Knowledge recovery validated successfully.[/dim]\n")
        else:
            if not recovery_mgr.mnemo.check(mnemonic_phrase.strip()):
                console.print(
                    "[bold red]Invalid BIP-39 mnemonic phrase (checksum failed)[/bold red]"
                )
                return
            seed = recovery_mgr.mnemo.to_seed(mnemonic_phrase.strip())
            from cryptavault.crypto.hash import Sha256

            fp = Sha256().digest(seed)[:16].hex()
            console.print()
            console.print("[bold green]✓ BIP-39 Recovery phrase valid![/bold green]")
            console.print(f"[bold cyan]Seed Fingerprint:[/bold cyan] [yellow]{fp}[/yellow]")
            console.print("[dim]Key phrase validated offline without server involvement.[/dim]\n")
    except Exception as e:
        console.print(f"[bold red]Recovery failed:[/bold red] {e}")
