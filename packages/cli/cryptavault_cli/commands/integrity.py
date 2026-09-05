"""Integrity, signatures, and Merkle tree commands for CryptaVault CLI."""

from pathlib import Path

from cryptavault.crypto.hash import Blake3
from cryptavault.crypto.hybrid import HybridSigPQ
from cryptavault.integrity.merkle import MerkleTree
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def sign_command(
    file_path: str,
    output_sig_path: str | None = None,
) -> None:
    """Sign a file using Post-Quantum Hybrid Signature (Ed25519 + Dilithium-3)."""
    p = Path(file_path)
    if not p.exists():
        console.print(f"[bold red]Error: File '{file_path}' not found![/bold red]")
        return

    data = p.read_bytes()

    sig_engine = HybridSigPQ()
    pubkey, privkey = sig_engine.keypair()

    signature_bytes = sig_engine.sign(privkey, data)

    sig_out = Path(output_sig_path or f"{file_path}.sig")
    sig_out.write_bytes(signature_bytes)

    pub_out = Path(f"{file_path}.pub")
    pub_out.write_bytes(pubkey)

    console.print()
    console.print(
        "[bold green]✓ File signed with Hybrid Post-Quantum Signature (Ed25519 + Dilithium3)![/bold green]"
    )
    console.print(f"  [cyan]Target File:[/cyan] {p.resolve()} ({len(data)} bytes)")
    console.print(
        f"  [cyan]Signature File:[/cyan] {sig_out.resolve()} ({len(signature_bytes)} bytes)"
    )
    console.print(f"  [cyan]Public Key File:[/cyan] {pub_out.resolve()} ({len(pubkey)} bytes)")
    console.print()


def verify_command(
    file_path: str,
    sig_path: str,
    pub_key_path: str,
) -> None:
    """Verify a file's integrity and authenticity against a Hybrid Post-Quantum signature."""
    fp = Path(file_path)
    sp = Path(sig_path)
    kp = Path(pub_key_path)

    if not fp.exists() or not sp.exists() or not kp.exists():
        console.print("[bold red]Error: One or more input files do not exist![/bold red]")
        return

    data = fp.read_bytes()
    sig_bytes = sp.read_bytes()
    pub_bytes = kp.read_bytes()

    sig_engine = HybridSigPQ()
    is_valid = sig_engine.verify(pub_bytes, data, sig_bytes)

    console.print()
    if is_valid:
        console.print(
            Panel.fit(
                f"[bold green]✓ SIGNATURE VALID — INTEGRITY VERIFIED[/bold green]\n\n"
                f"File: [cyan]{fp.name}[/cyan]\n"
                f"Dual Algorithms: [yellow]Ed25519 (Classical) + Dilithium3 (Post-Quantum NIST FIPS 204)[/yellow]\n"
                f"Status: EUF-CMA non-forgeable guarantee active.",
                title="[bold green]Cryptographic Verification[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[bold red]✗ SIGNATURE INVALID — FILE TAMPERED OR CORRUPTED[/bold red]\n\n"
                f"File: [cyan]{fp.name}[/cyan]\n"
                f"The cryptographic signature failed verification.",
                title="[bold red]Cryptographic Verification[/bold red]",
                border_style="red",
            )
        )
    console.print()


def merkle_command(dir_path: str = ".") -> None:
    """Compute cryptographic Merkle Tree root and audit proofs for files in a directory."""
    path = Path(dir_path).resolve()
    files = [f for f in sorted(path.iterdir()) if f.is_file() and not f.name.startswith(".")]

    if not files:
        console.print(f"[bold yellow]No files found in {path}[/bold yellow]")
        return

    leaves: list[bytes] = []
    file_map: list[tuple[str, str, int]] = []

    for f in files:
        try:
            data = f.read_bytes()
            leaf_hash = Blake3().digest(data)
            leaves.append(leaf_hash)
            file_map.append((f.name, leaf_hash.hex()[:16], len(data)))
        except Exception:  # noqa: BLE001, S112
            continue

    if not leaves:
        console.print("[bold red]No readable files to construct tree.[/bold red]")
        return

    tree = MerkleTree(leaves)
    root_hex = tree.root.hex()

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]Merkle Tree Audit Summary[/bold cyan]\n"
            f"Directory: [dim]{path}[/dim]\n"
            f"Leaf Count: [yellow]{len(leaves)}[/yellow] files\n"
            f"Cryptographic Root Hash: [bold green]{root_hex}[/bold green]",
            border_style="cyan",
        )
    )

    table = Table(
        title="Directory Merkle Leaf Hashes", show_header=True, header_style="bold magenta"
    )
    table.add_column("Index", style="yellow", width=8)
    table.add_column("File Name", style="cyan", width=28)
    table.add_column("Size (bytes)", style="dim", width=14)
    table.add_column("BLAKE3 Leaf Hash", style="white")

    for idx, (name, h, size) in enumerate(file_map[:15]):  # limit display to first 15
        table.add_row(str(idx), name, str(size), h + "...")

    if len(file_map) > 15:
        table.add_row("...", f"... and {len(file_map) - 15} more files", "...", "...")

    console.print(table)

    # Demonstrate O(log n) proof for leaf 0
    proof = tree.get_proof(0)
    is_proven = MerkleTree.verify_proof(leaves[0], proof, tree.root)

    console.print(
        f"[bold green]✓ Audit Proof for leaf 0 ({file_map[0][0]}):[/bold green] "
        f"[cyan]{len(proof)} steps[/cyan] (O(log n) verification: [bold green]{'SUCCESS' if is_proven else 'FAILED'}[/bold green])\n"
    )
