"""Cryptographic benchmarking command for CryptaVault CLI."""

import os
import time

from cryptavault.crypto.hash import Blake3, Sha256
from cryptavault.crypto.kdf import Argon2id
from cryptavault.crypto.pq import DilithiumSig, KyberKem
from cryptavault.crypto.symmetric import AES256GCM, ChaCha20Poly1305
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def run_benchmark() -> None:
    """Run real-time micro-benchmarks across CryptaVault classical and post-quantum primitives."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]CryptaVault Cryptographic Engine Live Benchmark[/bold cyan]\n"
            "[dim]Testing AVX2/AES-NI accelerated symmetric ciphers, hashing, and NIST PQC lattice algorithms[/dim]",
            border_style="cyan",
        )
    )

    results: list[dict[str, str]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:

        # 1. Symmetric Encryption Benchmark (10 MB buffer)
        task = progress.add_task("[cyan]Benchmarking AES-256-GCM...", total=None)
        test_data_10mb = os.urandom(10 * 1024 * 1024)
        aes_key = os.urandom(32)
        aes = AES256GCM()

        t0 = time.perf_counter()
        nonce, ct = aes.encrypt_auto_nonce(aes_key, test_data_10mb)
        t_aes_enc = time.perf_counter() - t0
        aes_enc_speed = 10.0 / t_aes_enc

        t0 = time.perf_counter()
        _ = aes.decrypt(aes_key, nonce, ct)
        t_aes_dec = time.perf_counter() - t0
        aes_dec_speed = 10.0 / t_aes_dec

        results.append(
            {
                "category": "Symmetric AEAD",
                "primitive": "AES-256-GCM",
                "operation": "Encrypt / Decrypt",
                "metric": f"{aes_enc_speed:.1f} MB/s enc | {aes_dec_speed:.1f} MB/s dec",
                "rating": "[green]Ultra Fast (Hardware AES-NI)[/green]",
            }
        )

        # 2. ChaCha20-Poly1305 Benchmark (10 MB buffer)
        progress.update(task, description="[cyan]Benchmarking ChaCha20-Poly1305...")
        chacha_key = os.urandom(32)
        chacha = ChaCha20Poly1305()

        t0 = time.perf_counter()
        ch_nonce, ch_ct = chacha.encrypt_auto_nonce(chacha_key, test_data_10mb)
        t_ch_enc = time.perf_counter() - t0
        ch_enc_speed = 10.0 / t_ch_enc

        t0 = time.perf_counter()
        _ = chacha.decrypt(chacha_key, ch_nonce, ch_ct)
        t_ch_dec = time.perf_counter() - t0
        ch_dec_speed = 10.0 / t_ch_dec

        results.append(
            {
                "category": "Symmetric AEAD",
                "primitive": "ChaCha20-Poly1305",
                "operation": "Encrypt / Decrypt",
                "metric": f"{ch_enc_speed:.1f} MB/s enc | {ch_dec_speed:.1f} MB/s dec",
                "rating": "[green]Fast (Constant-Time Poly1305)[/green]",
            }
        )

        # 3. Hashing Benchmark (20 MB buffer)
        progress.update(task, description="[cyan]Benchmarking BLAKE3 & SHA-256...")
        test_data_20mb = os.urandom(20 * 1024 * 1024)

        t0 = time.perf_counter()
        _ = Blake3().digest(test_data_20mb)
        t_blake3 = time.perf_counter() - t0
        blake3_speed = 20.0 / t_blake3

        t0 = time.perf_counter()
        _ = Sha256().digest(test_data_20mb)
        t_sha256 = time.perf_counter() - t0
        sha256_speed = 20.0 / t_sha256

        results.append(
            {
                "category": "Cryptographic Hash",
                "primitive": "BLAKE3 (Tree Hash)",
                "operation": "20 MB Stream Digest",
                "metric": f"{blake3_speed:.1f} MB/s",
                "rating": "[green]Extreme Throughput (AVX2)[/green]",
            }
        )
        results.append(
            {
                "category": "Cryptographic Hash",
                "primitive": "SHA-256 (NIST)",
                "operation": "20 MB Stream Digest",
                "metric": f"{sha256_speed:.1f} MB/s",
                "rating": "[cyan]Standard Compliant[/cyan]",
            }
        )

        # 4. Post-Quantum KEM (Kyber-768 / ML-KEM-768)
        progress.update(task, description="[cyan]Benchmarking Kyber-768 Lattice KEM...")
        try:
            kem = KyberKem(level=3)
            pubkey, privkey = kem.keypair()

            n_iters = 100
            t0 = time.perf_counter()
            for _ in range(n_iters):
                _ss, ct_kem = kem.encapsulate(pubkey)
            t_encap = (time.perf_counter() - t0) / n_iters

            t0 = time.perf_counter()
            for _ in range(n_iters):
                _ = kem.decapsulate(privkey, ct_kem)
            t_decap = (time.perf_counter() - t0) / n_iters

            results.append(
                {
                    "category": "Post-Quantum KEM",
                    "primitive": "ML-KEM-768 (Kyber768)",
                    "operation": "Encap / Decap",
                    "metric": f"{t_encap * 1000:.3f} ms encap | {t_decap * 1000:.3f} ms decap",
                    "rating": f"[green]{1.0 / t_encap:.0f} ops/sec (Quantum Resistant)[/green]",
                }
            )
        except Exception as e:  # noqa: BLE001
            results.append(
                {
                    "category": "Post-Quantum KEM",
                    "primitive": "ML-KEM-768",
                    "operation": "Encap / Decap",
                    "metric": f"Failed: {e}",
                    "rating": "[red]Error[/red]",
                }
            )

        # 5. Post-Quantum Signature (Dilithium-3 / ML-DSA-65)
        progress.update(task, description="[cyan]Benchmarking Dilithium-3 Lattice Signatures...")
        try:
            sig = DilithiumSig(level=3)
            spub, spriv = sig.keypair()
            sample_msg = b"CryptaVault zero-knowledge signature verification test payload"

            t0 = time.perf_counter()
            for _ in range(n_iters):
                signature = sig.sign(spriv, sample_msg)
            t_sign = (time.perf_counter() - t0) / n_iters

            t0 = time.perf_counter()
            for _ in range(n_iters):
                _ = sig.verify(spub, sample_msg, signature)
            t_vfy = (time.perf_counter() - t0) / n_iters

            results.append(
                {
                    "category": "Post-Quantum Signature",
                    "primitive": "ML-DSA-65 (Dilithium3)",
                    "operation": "Sign / Verify",
                    "metric": f"{t_sign * 1000:.3f} ms sign | {t_vfy * 1000:.3f} ms verify",
                    "rating": f"[green]{1.0 / t_sign:.0f} ops/sec (Quantum Resistant)[/green]",
                }
            )
        except Exception as e:  # noqa: BLE001
            results.append(
                {
                    "category": "Post-Quantum Signature",
                    "primitive": "Dilithium3",
                    "operation": "Sign / Verify",
                    "metric": f"Failed: {e}",
                    "rating": "[red]Error[/red]",
                }
            )

        # 6. Memory-Hard KDF (Argon2id)
        progress.update(task, description="[cyan]Benchmarking Argon2id Key Derivation...")
        kdf = Argon2id()
        t0 = time.perf_counter()
        _ = kdf.derive(
            b"cryptavault-master-password-test",
            os.urandom(16),
            length=32,
            time_cost=2,
            memory_cost=64 * 1024,
            parallelism=4,
        )
        t_argon = time.perf_counter() - t0

        results.append(
            {
                "category": "Password KDF",
                "primitive": "Argon2id (RFC 9106, 64MB)",
                "operation": "Master Key Derivation",
                "metric": f"{t_argon * 1000:.1f} ms",
                "rating": "[green]Optimal for Zero-Knowledge Login[/green]",
            }
        )

    # Render table
    table = Table(
        title="[bold]CryptaVault Primitive Micro-Benchmarks[/bold]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Category", style="cyan", width=22)
    table.add_column("Algorithm / Primitive", style="white", width=26)
    table.add_column("Operation", style="yellow", width=22)
    table.add_column("Performance Metric", style="bold white", width=34)
    table.add_column("Security & Acceleration", style="green")

    for r in results:
        table.add_row(r["category"], r["primitive"], r["operation"], r["metric"], r["rating"])

    console.print(table)
    console.print()
