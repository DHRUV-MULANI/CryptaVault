"""Cryptographic encryption and decryption commands for CryptaVault CLI."""

import base64
import os
from pathlib import Path

from cryptavault.adaptive.profiles import SECURITY_PROFILES
from cryptavault.crypto.kdf import Argon2id
from cryptavault.crypto.symmetric import AES256GCM, ChaCha20Poly1305
from rich.console import Console
from rich.panel import Panel

console = Console()


def encrypt_command(
    input_path: str | None = None,
    text: str | None = None,
    output_path: str | None = None,
    profile_name: str = "BALANCED",
    passphrase: str = "cryptavault-demo-passphrase",
) -> None:
    """Encrypt a file or text string using adaptive authenticated encryption."""
    if not input_path and not text:
        console.print(
            "[bold red]Error: Specify either an input file (--input) or raw text (--text)[/bold red]"
        )
        return

    profile_name_upper = profile_name.upper()
    profile = SECURITY_PROFILES.get(profile_name_upper)
    if not profile:
        console.print(
            f"[bold red]Unknown profile '{profile_name}'. Options: PERFORMANCE, BALANCED, HIGH, MAXIMUM[/bold red]"
        )
        return

    # Read plaintext
    if input_path:
        path = Path(input_path)
        if not path.exists():
            console.print(f"[bold red]Error: Input file '{input_path}' not found![/bold red]")
            return
        plaintext = path.read_bytes()
    else:
        plaintext = text.encode("utf-8")  # type: ignore

    # Derive key using Argon2id
    salt = os.urandom(16)
    kdf = Argon2id()
    derived_key = kdf.derive(
        passphrase.encode("utf-8"),
        salt,
        length=32,
        time_cost=profile.kdf_time_cost,
        memory_cost=profile.kdf_memory_cost_kib,
        parallelism=profile.kdf_parallelism,
    )

    # Encrypt according to profile
    aad = profile_name_upper.encode("utf-8")
    if profile.symmetric_cipher.lower() == "aes-256-gcm":
        cipher = AES256GCM()
        nonce, ciphertext = cipher.encrypt_auto_nonce(derived_key, plaintext, aad=aad)
    else:
        chacha_cipher = ChaCha20Poly1305()
        nonce, ciphertext = chacha_cipher.encrypt_auto_nonce(derived_key, plaintext, aad=aad)

    # Envelope: [1 byte profile len][profile name][16 bytes salt][12 bytes nonce][ciphertext+tag]
    env_profile_bytes = profile_name_upper.encode("utf-8")
    envelope = (
        len(env_profile_bytes).to_bytes(1, "big") + env_profile_bytes + salt + nonce + ciphertext
    )

    tag_hex = ciphertext[-16:].hex()

    if output_path:
        out_file = Path(output_path)
        out_file.write_bytes(envelope)
        console.print()
        console.print("[bold green]✓ File encrypted successfully![/bold green]")
        console.print(f"  [cyan]Profile:[/cyan] {profile_name_upper} ({profile.symmetric_cipher})")
        console.print(
            f"  [cyan]Ciphertext Output:[/cyan] {out_file.resolve()} ({len(envelope)} bytes)"
        )
        console.print(f"  [cyan]Auth Tag (hex):[/cyan] {tag_hex}")
        console.print()
    else:
        b64_cipher = base64.b64encode(envelope).decode("ascii")
        console.print()
        console.print(
            Panel.fit(
                f"[bold green]Encrypted Ciphertext Envelope (Base64):[/bold green]\n\n[yellow]{b64_cipher}[/yellow]\n\n"
                f"[dim]Cipher: {profile.symmetric_cipher} | Profile: {profile_name_upper} | Tag: {tag_hex}[/dim]",
                title="[bold cyan]CryptaVault Ciphertext[/bold cyan]",
                border_style="green",
            )
        )
        console.print()


def decrypt_command(
    input_path: str | None = None,
    ciphertext_b64: str | None = None,
    output_path: str | None = None,
    passphrase: str = "cryptavault-demo-passphrase",
) -> None:
    """Decrypt an encrypted file or base64 envelope with authentication tag verification."""
    if not input_path and not ciphertext_b64:
        console.print(
            "[bold red]Error: Specify either an input file (--input) or base64 ciphertext (--ciphertext)[/bold red]"
        )
        return

    if input_path:
        path = Path(input_path)
        if not path.exists():
            console.print(f"[bold red]Error: Input file '{input_path}' not found![/bold red]")
            return
        raw_envelope = path.read_bytes()
    else:
        raw_envelope = base64.b64decode(ciphertext_b64)  # type: ignore

    try:
        # Parse envelope
        prof_len = raw_envelope[0]
        offset = 1
        profile_name = raw_envelope[offset : offset + prof_len].decode("utf-8")
        offset += prof_len
        salt = raw_envelope[offset : offset + 16]
        offset += 16
        nonce = raw_envelope[offset : offset + 12]
        offset += 12
        ciphertext_and_tag = raw_envelope[offset:]

        profile = SECURITY_PROFILES[profile_name]

        kdf = Argon2id()
        derived_key = kdf.derive(
            passphrase.encode("utf-8"),
            salt,
            length=32,
            time_cost=profile.kdf_time_cost,
            memory_cost=profile.kdf_memory_cost_kib,
            parallelism=profile.kdf_parallelism,
        )
        aad = profile_name.encode("utf-8")

        if profile.symmetric_cipher.lower() == "aes-256-gcm":
            cipher = AES256GCM()
            plaintext = cipher.decrypt(derived_key, nonce, ciphertext_and_tag, aad=aad)
        else:
            chacha_cipher = ChaCha20Poly1305()
            plaintext = chacha_cipher.decrypt(derived_key, nonce, ciphertext_and_tag, aad=aad)

        if output_path:
            out_file = Path(output_path)
            out_file.write_bytes(plaintext)
            console.print(
                f"[bold green]✓ File decrypted successfully to:[/bold green] {out_file.resolve()}"
            )
        else:
            try:
                decoded_str = plaintext.decode("utf-8")
                console.print()
                console.print(
                    Panel.fit(
                        f"[bold white]{decoded_str}[/bold white]",
                        title="[bold green]✓ Decrypted Plaintext (AEAD Tag Authenticated)[/bold green]",
                        border_style="green",
                    )
                )
                console.print()
            except UnicodeDecodeError:
                console.print(
                    f"[bold green]✓ Decrypted binary payload ({len(plaintext)} bytes)[/bold green]"
                )

    except Exception as e:
        console.print(
            f"[bold red]Decryption failed (Corrupted or Tampered Ciphertext):[/bold red] {e}"
        )
