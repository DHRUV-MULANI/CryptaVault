"""Interactive educational cryptographic teaching module for CryptaVault CLI."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()
teach_app = typer.Typer(
    name="teach",
    help="Interactive educational tutorials, concept explanations, and runnable examples",
    no_args_is_help=False,
)

TEACH_TOPICS = {
    "zero-knowledge": {
        "title": "Zero-Knowledge Storage Architecture",
        "summary": "Why the server, database, and cloud providers never see plaintext files or private keys.",
        "content": """
### What is Zero-Knowledge (ZK) Storage?
In standard cloud storage (like Google Drive or AWS S3 with server-side encryption), the cloud provider holds your encryption keys. If their servers are breached, or if an insider accesses the disks, your plaintext files can be read.

**In CryptaVault:**
1. **Client-Side Derivation**: Your master key is derived on your computer using memory-hard **Argon2id** from your passphrase.
2. **Local Pre-Compression**: Files are compressed with Zstandard before encryption to remove metadata leaks and reduce size.
3. **Local Encryption**: Ciphertext chunks are encrypted with **AES-256-GCM** or **ChaCha20-Poly1305** using random nonces and 128-bit authentication tags.
4. **Ciphertext Only Transport**: Only encrypted `.vault` containers reach **Supabase Storage** or **Cloudflare R2**.
5. **No Keys on Server**: The backend database only stores encrypted manifests and cryptographic integrity hashes.

### Try it yourself:
```bash
# Encrypt locally before any upload:
cryptavault pipeline-encrypt secret.pdf --output secret.vault --profile BALANCED

# Notice the server only ever receives 'secret.vault':
cryptavault storage upload --source secret.vault --backend supabase
```
""",
    },
    "pqc": {
        "title": "Post-Quantum Hybrid Cryptography (FIPS 203 & 204)",
        "summary": "How CryptaVault defends against 'Harvest Now, Decrypt Later' quantum attacks.",
        "content": """
### The Quantum Threat & Shor's Algorithm
Classical public-key cryptography (RSA, ECC, Diffie-Hellman) relies on mathematical problems like integer factorization and discrete logarithms. A sufficiently powerful quantum computer running **Shor's algorithm** will break these schemes in polynomial time.

Adversaries today are actively executing **Harvest Now, Decrypt Later (HNDL)**: capturing encrypted traffic and storing it until quantum machines are built.

### CryptaVault's Post-Quantum Defense:
- **ML-KEM-768 (Kyber-768)**: Standardized in **NIST FIPS 203**. Based on the hardness of Module Learning with Errors (MLWE) on lattice structures.
- **ML-DSA-65 (Dilithium-3)**: Standardized in **NIST FIPS 204**. Post-quantum lattice-based digital signatures.
- **Hybrid AND-Composition**: We combine classical X25519 with Kyber-768:
  `Shared Secret = HKDF( X25519_Secret || Kyber_Secret )`
  An attacker must break **BOTH** the elliptic curve problem **AND** the lattice problem to decrypt!

### Try it yourself:
```bash
# Check quantum primitives status:
cryptavault status

# Sign a file with Post-Quantum Hybrid signature:
cryptavault sign contract.pdf --output-sig contract.sig

# Run quantum micro-benchmarks:
cryptavault benchmark
```
""",
    },
    "adaptive": {
        "title": "5-Tier Adaptive Security Engine",
        "summary": "Balancing speed and security dynamically with a 0-100% slider.",
        "content": """
### Why Adaptive Security?
Different files have different threat models. A 10 GB video stream needs high-speed hardware acceleration, while sensitive private keys require maximum post-quantum forward secrecy.

### The 5 Profiles:
| Profile | Slider | Primary Cipher | Quantum Protection | Memory-Hard KDF |
|---|---|---|---|---|
| **PERFORMANCE** | 0-25% | AES-256-GCM (AES-NI >2500 MB/s) | Classical ECDH | Argon2id 16MB (t=1) |
| **STANDARD** | 25-50% | AES-256-GCM | Classical ECDH | Argon2id 32MB (t=2) |
| **BALANCED** | 50-75% | AES-256-GCM / ChaCha20 | Hybrid Kyber-768 | Argon2id 64MB (t=3) |
| **STRONG** | 75-90% | ChaCha20-Poly1305 (Side-channel safe) | Hybrid Kyber-768 | Argon2id 128MB (t=4) |
| **MAXIMUM** | 90-100% | AES-256 + ChaCha20 Cascaded | Mandatory Kyber + Dilithium | Argon2id 256MB (t=6) |

### Try it yourself:
```bash
# View all presets:
cryptavault profile list

# Set default slider to 85% (STRONG):
cryptavault profile set --slider 85.0

# Encrypt using MAXIMUM profile:
cryptavault encrypt --input confidential.db --output confidential.enc --profile MAXIMUM
```
""",
    },
    "streaming": {
        "title": "Chunked AEAD Streaming & BLAKE3 Merkle Trees",
        "summary": "Fail-closed streaming for files of arbitrary size with cryptographic tamper detection.",
        "content": """
### The Danger of In-Memory Encryption
Encrypting a 5 GB file in memory can crash low-spec devices or cause out-of-memory errors. Furthermore, naive chunking without authentication allows chunk-swapping or truncation attacks.

### CryptaVault's Streaming Pipeline:
1. **Magic-Byte Header Check**: Automatically skips compression on already-compressed files (ZIP, MP4, JPEG) to save CPU cycles.
2. **Chunked AEAD**: Splits data into streaming chunks (64KB to 4MB). Each chunk receives an incremental sequence number to prevent reordering.
3. **BLAKE3 Merkle Tree**: Leaf hashes are computed concurrently via AVX2 instructions to build an immutable cryptographic Merkle root.
4. **Fail-Closed Verification**: If an active attacker alters even 1 bit in transit, decryption immediately aborts with an authentication failure.

### Try it yourself:
```bash
# Process a large file through the streaming pipeline:
cryptavault pipeline-encrypt big_archive.tar --output big_archive.vault --profile BALANCED

# Decrypt and verify tamper protection:
cryptavault pipeline-decrypt big_archive.vault --output restored.tar

# Compute directory Merkle root:
cryptavault merkle --dir ./data
```
""",
    },
    "storage": {
        "title": "Multi-Backend Cloud Storage: Supabase vs Cloudflare R2",
        "summary": "Zero-knowledge storage targets, egress costs, and custom domain bindings.",
        "content": """
### Cloud Storage Options in CryptaVault
Because CryptaVault encrypts client-side, the remote storage provider only sees high-entropy ciphertext chunks.

### Comparing Providers:
| Provider | Protocol | Bandwidth Egress Fees | Custom Domains | Best For |
|---|---|---|---|---|
| **Cloudflare R2** | S3 API | **$0.00 / GB (Free Egress!)** | Native Custom Domain | Public sharing, large downloads, cost savings |
| **Supabase Storage** | REST / S3 | Included in free tier | Via proxy / domain | Integrated Auth + PostgreSQL metadata |
| **Remote SFTP** | SSH/SFTP | Your server bandwidth | Yes (own VPS) | Private enterprise servers |
| **Local Disk** | File I/O | N/A | N/A | Offline air-gapped storage |

### Why Cloudflare R2 is ideal:
Cloudflare R2 has **no egress fees**, meaning anyone downloading your shared files does not incur data transfer bills. You can bind your domain (e.g. `storage.yourdomain.com`) directly to your R2 bucket.

### Try it yourself:
```bash
# Upload to Supabase Storage:
cryptavault storage upload --source archive.vault --backend supabase --remote-path /vaults/archive.vault

# Upload to Cloudflare R2:
cryptavault storage upload --source archive.vault --backend r2 --remote-path /backups/archive.vault
```
""",
    },
    "sharing": {
        "title": "Zero-Knowledge Sharing & Custom Domain Links",
        "summary": "One-time access tokens, password wrapping, and QR codes with your custom domain.",
        "content": """
### How Zero-Knowledge Sharing Works
How do you share an encrypted file with a friend without giving the cloud provider the key?

1. **HMAC One-Time Tokens**: CryptaVault creates a single-use token that expires after N hours or after 1 download.
2. **Password Wrapping**: The file decryption key is encrypted with Argon2id using a password you tell your recipient out-of-band.
3. **Custom Domains**: Instead of sending an ugly localhost or generic URL, your share link uses your custom domain (e.g., `https://vault.yourdomain.com/share/{token}`).
4. **QR Codes**: Renders mobile-friendly ASCII QR codes in the terminal or PNG codes in the web UI for instant mobile scanning.

### Try it yourself:
```bash
# Create a 24-hour share link with QR code:
cryptavault share create --file-id "file-123" --expiry-hours 24 --qr

# Wrap a file key with a secret password:
cryptavault share wrap-password --file-key-hex "0123...cdef" --password "FriendSecretPassphrase"
```
""",
    },
}


@teach_app.callback(invoke_without_command=True)
def teach_main(
    ctx: typer.Context,
    topic: str = typer.Argument(
        None,
        help="Topic to learn: pqc, zero-knowledge, adaptive, streaming, storage, sharing (or omit to view index)",
    ),
) -> None:
    """Interactive educational guide and practical walkthrough of CryptaVault concepts."""
    if ctx.invoked_subcommand is not None:
        return

    if not topic:
        # Display topics catalog
        table = Table(title="🎓 CryptaVault Interactive Academy — Knowledge Topics")
        table.add_column("Topic Key", style="cyan bold")
        table.add_column("Concept Title", style="green")
        table.add_column("Summary", style="white")

        for key, data in TEACH_TOPICS.items():
            table.add_row(key, data["title"], data["summary"])

        console.print(table)
        console.print(
            "\n[bold yellow]Usage:[/bold yellow] [bold cyan]cryptavault teach <topic_key>[/bold cyan]"
        )
        console.print(
            "Example: [green]cryptavault teach zero-knowledge[/green]  or  [green]cryptavault teach pqc[/green]\n"
        )
        return

    key = topic.lower().strip()
    if key not in TEACH_TOPICS:
        console.print(f"[bold red]Unknown topic:[/bold red] '{topic}'.")
        console.print(f"Available topics: [cyan]{', '.join(TEACH_TOPICS.keys())}[/cyan]")
        return

    data = TEACH_TOPICS[key]
    console.print(
        Panel(
            f"[bold green]{data['title']}[/bold green]\n[italic]{data['summary']}[/italic]",
            border_style="cyan",
        )
    )
    console.print(Markdown(data["content"]))
