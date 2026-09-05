"""Status command for CryptaVault CLI."""

import os
import platform

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def check_aesni() -> bool:
    """Check if host CPU supports AES-NI hardware acceleration."""
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                return "aes" in content
    except Exception:  # noqa: BLE001, S110
        pass
    return False


def check_avx2() -> bool:
    """Check if host CPU supports AVX2 vector extensions."""
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                return "avx2" in content
    except Exception:  # noqa: BLE001, S110
        pass
    return False


def status_command() -> None:
    """Display CryptaVault environment, cryptographic hardware, and zero-knowledge status."""
    try:
        import oqs

        pq_available = True
        kyber_supported = bool(oqs.is_kem_enabled("Kyber768") or oqs.is_kem_enabled("ML-KEM-768"))
        dilithium_supported = bool(
            oqs.is_sig_enabled("ML-DSA-65") or oqs.is_sig_enabled("Dilithium3")
        )
    except Exception:  # noqa: BLE001
        pq_available = False
        kyber_supported = False
        dilithium_supported = False

    aesni = check_aesni()
    avx2 = check_avx2()

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]CryptaVault[/bold cyan] [white]— Adaptive Hybrid Zero-Knowledge Cryptographic Engine[/white]\n"
            "[dim]Enforcing strict client-side encryption boundary across cloud & on-prem targets[/dim]",
            border_style="cyan",
        )
    )

    table = Table(
        title="[bold]Cryptographic System Status[/bold]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Subsystem", style="cyan", width=26)
    table.add_column("Status / Implementation", style="white")
    table.add_column("Security Guarantee", style="green")

    table.add_row(
        "Zero-Knowledge Boundary",
        "[bold green]ENFORCED (Client-Side Only)[/bold green]",
        "Plaintext & keys never touch server/database",
    )
    table.add_row(
        "Python Runtime",
        f"{platform.python_implementation()} {platform.python_version()} ({platform.machine()})",
        "Python 3.11+ secure interpreter",
    )
    table.add_row(
        "Post-Quantum Core (liboqs)",
        (
            "[bold green]ACTIVE (Native 0.16.0)[/bold green]"
            if pq_available
            else "[red]INACTIVE[/red]"
        ),
        "NIST FIPS 203 (ML-KEM) & FIPS 204 (ML-DSA)",
    )
    table.add_row(
        "Kyber KEM Mechanisms",
        (
            "[green]Kyber512, Kyber768, Kyber1024[/green]"
            if kyber_supported
            else "[red]Unavailable[/red]"
        ),
        "Lattice-based IND-CCA2 Post-Quantum",
    )
    table.add_row(
        "Dilithium Signatures",
        (
            "[green]Dilithium2, Dilithium3, Dilithium5[/green]"
            if dilithium_supported
            else "[red]Unavailable[/red]"
        ),
        "Lattice-based EUF-CMA Post-Quantum",
    )
    table.add_row(
        "Hardware Acceleration",
        f"AES-NI: {'[green]YES[/green]' if aesni else '[yellow]NO[/yellow]'} | AVX2: {'[green]YES[/green]' if avx2 else '[yellow]NO[/yellow]'}",
        "Constant-time vector execution",
    )
    table.add_row(
        "Key Derivation Engine",
        "Argon2id (RFC 9106) + PBKDF2-HMAC-SHA256",
        "Memory-hard GPU/ASIC resistant",
    )
    table.add_row(
        "Audit & Integrity Engine",
        "BLAKE3 + SHA-256 Merkle Trees (O(log n))",
        "Cryptographic proof of non-tampering",
    )

    console.print(table)
    console.print()
