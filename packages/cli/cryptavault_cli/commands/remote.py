"""Authenticated remote API commands for the dynamic CryptaVault stack.

The remote commands mirror the web client: local accounts derive an auth verifier
and a master key in the CLI process, encrypted metadata and CVW1 containers are
created client-side, and the API only ever receives ciphertext plus wrapped keys.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import mimetypes
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs

import httpx
import typer
from cryptavault.adaptive.profiles import get_profile
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from rich.console import Console
from rich.table import Table

console = Console()

DEFAULT_API = os.getenv("CRYPTAVAULT_API_URL", "http://localhost:8000").rstrip("/")
SESSION_PATH = Path(
    os.getenv(
        "CRYPTAVAULT_SESSION",
        str(Path.home() / ".config" / "cryptavault" / "session.json"),
    )
)
KDF_ITERATIONS = 210_000
VERIFIER = b"cryptavault:verifier:v1"

remote_app = typer.Typer(
    name="remote",
    help="Authenticated API commands: login, workspaces, encrypted files, and shares.",
    no_args_is_help=True,
)
auth_app = typer.Typer(
    name="auth", help="Login, register, inspect, and clear the API session.", no_args_is_help=True
)
workspace_app = typer.Typer(
    name="workspace", help="List, create, select, and share workspaces.", no_args_is_help=True
)
files_app = typer.Typer(
    name="files",
    help="Encrypt/upload, download, version, trash, and share files.",
    no_args_is_help=True,
)
shares_app = typer.Typer(
    name="shares", help="List, revoke, and decrypt server-enforced shares.", no_args_is_help=True
)

remote_app.add_typer(auth_app, name="auth")
remote_app.add_typer(workspace_app, name="workspace")
remote_app.add_typer(files_app, name="files")
remote_app.add_typer(shares_app, name="shares")


# ---------------------------------------------------------------------------
# Session and HTTP helpers
# ---------------------------------------------------------------------------


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64d(value: str) -> bytes:
    return base64.b64decode(value)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64urld(value: str) -> bytes:
    padded = value.replace("-", "+").replace("_", "/")
    return base64.b64decode(padded + "=" * ((4 - len(padded) % 4) % 4))


def _seal(key: bytes, plaintext: bytes, aad: str) -> dict[str, str]:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad.encode("utf-8"))
    return {"ivB64": _b64(nonce), "ctB64": _b64(ciphertext)}


def _open(key: bytes, sealed: dict[str, str], aad: str) -> bytes:
    return AESGCM(key).decrypt(
        _b64d(sealed["ivB64"]),
        _b64d(sealed["ctB64"]),
        aad.encode("utf-8"),
    )


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))


def _load_session(required: bool = True) -> dict[str, Any]:
    if not SESSION_PATH.exists():
        if required:
            console.print("[red]No API session. Run:[/red] cryptavault remote auth login")
            raise typer.Exit(1)
        return {}
    try:
        return cast(dict[str, Any], json.loads(SESSION_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]Could not read session:[/red] {exc}")
        raise typer.Exit(1) from exc


def _save_session(session: dict[str, Any]) -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(session, indent=2), encoding="utf-8")
    try:
        SESSION_PATH.chmod(0o600)
    except OSError:
        pass


def _clear_session() -> None:
    try:
        SESSION_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return response.text or response.reason_phrase
    detail = payload.get("detail") if isinstance(payload, dict) else payload
    if isinstance(detail, list):
        return "; ".join(
            str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail
        )
    return str(detail)


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    public: bool = False,
    **kwargs: Any,
) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    if not public:
        if not token:
            session = _load_session()
            token = session.get("access_token")
        if not token:
            console.print("[red]Session has no token. Run:[/red] cryptavault remote auth login")
            raise typer.Exit(1)
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.request(
            method,
            f"{DEFAULT_API}{path}",
            headers=headers,
            timeout=120.0,
            **kwargs,
        )
    except httpx.HTTPError as exc:
        console.print(f"[red]API request failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    if response.status_code == 401 and not public:
        console.print(
            "[red]Session expired or unauthorized.[/red] Run: cryptavault remote auth login"
        )
        raise typer.Exit(1)
    if response.status_code >= 400:
        console.print(f"[red]API {response.status_code}:[/red] {_detail(response)}")
        raise typer.Exit(1)
    return response


def _prompt_passphrase(passphrase: str | None, label: str = "Master passphrase") -> str:
    if passphrase:
        return passphrase
    return str(typer.prompt(label, hide_input=True))


def _master_key(passphrase: str | None = None) -> tuple[bytes, dict[str, Any]]:
    session = _load_session()
    vault = session.get("vault") or {}
    if not vault.get("salt_b64") or not vault.get("check"):
        console.print(
            "[red]Session is missing vault bootstrap. Run:[/red] cryptavault remote auth login"
        )
        raise typer.Exit(1)
    secret = _prompt_passphrase(passphrase)
    key = _derive(
        secret, _b64d(vault["salt_b64"]), int(vault.get("kdf_iterations", KDF_ITERATIONS))
    )
    try:
        opened = _open(key, vault["check"], "vault:verifier")
    except InvalidTag:
        console.print("[red]Incorrect passphrase.[/red]")
        raise typer.Exit(1) from None
    if opened != VERIFIER:
        console.print("[red]Vault verifier mismatch.[/red]")
        raise typer.Exit(1)
    return key, session


def _workspace_id(workspace: str | None, session: dict[str, Any]) -> str:
    if workspace:
        return workspace
    current = session.get("current_workspace_id")
    if current:
        return str(current)
    workspaces = session.get("workspaces") or []
    if workspaces:
        return str(workspaces[0]["id"])
    console.print(
        "[red]No workspace available. Create one with:[/red] cryptavault remote workspace create NAME"
    )
    raise typer.Exit(1)


def _find_workspace(identifier: str, session: dict[str, Any]) -> dict[str, Any]:
    workspaces = session.get("workspaces") or []
    for item in workspaces:
        if identifier in {item.get("id"), item.get("name")}:
            return cast(dict[str, Any], item)
    response = _request("GET", "/api/workspaces")
    remote_items: list[dict[str, Any]] = response.json()
    for item in remote_items:
        if identifier in {item.get("id"), item.get("name")}:
            return item
    console.print(f"[red]Workspace not found:[/red] {identifier}")
    raise typer.Exit(1)


def _refresh_session(session: dict[str, Any]) -> dict[str, Any]:
    response = _request("GET", "/api/auth/me", token=session.get("access_token"))
    payload = response.json()
    session.update(
        {
            "user": payload["user"],
            "vault": payload["vault"],
            "workspaces": payload["workspaces"],
        }
    )
    if not session.get("current_workspace_id") and payload["workspaces"]:
        session["current_workspace_id"] = payload["workspaces"][0]["id"]
    _save_session(session)
    return session


# ---------------------------------------------------------------------------
# CVW1 client-side encryption (web-compatible)
# ---------------------------------------------------------------------------


_PRECOMPRESSED = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/zip",
    "application/gzip",
    "application/x-7z-compressed",
    "application/pdf",
}
_PRECOMPRESSED_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp4",
    ".mkv",
    ".mp3",
    ".flac",
    ".ogg",
    ".zip",
    ".gz",
    ".xz",
    ".7z",
    ".pdf",
}


def _should_compress(path: Path, content_type: str) -> bool:
    if content_type in _PRECOMPRESSED:
        return False
    if path.suffix.lower() in _PRECOMPRESSED_EXT:
        return False
    return path.stat().st_size < 512 * 1024 or (content_type.startswith("text/"))


def _encrypt_file(
    path: Path,
    master_key: bytes,
    profile: str,
    compress: str,
    file_id: str | None = None,
) -> tuple[bytes, dict[str, Any], bytes]:
    spec = get_profile(profile)
    level = spec.level.value
    data = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    use_compression = {
        "on": True,
        "off": False,
        "auto": _should_compress(path, content_type),
    }[compress]
    payload = gzip.compress(data) if use_compression else data
    compression = "gzip" if use_compression else "none"
    file_uuid = file_id or str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    raw_key = secrets.token_bytes(32)
    cipher = AESGCM(raw_key)
    chunks: list[dict[str, Any]] = []
    chunk_size = spec.chunk_size_bytes
    total = max(1, (len(payload) + chunk_size - 1) // chunk_size)
    for index in range(total):
        start = index * chunk_size
        chunk = payload[start : start + chunk_size]
        final = 1 if index == total - 1 else 0
        nonce = secrets.token_bytes(12)
        aad = f"cryptavault:web:v1:{file_uuid}:{index}:{final}"
        ciphertext = cipher.encrypt(nonce, chunk, aad.encode("utf-8"))
        chunks.append(
            {
                "i": index,
                "f": final,
                "iv": _b64(nonce),
                "ct": _b64(ciphertext),
            }
        )
    container = {
        "magic": "CVW1",
        "v": 1,
        "fileId": file_uuid,
        "createdAt": created_at,
        "profile": level,
        "compression": compression,
        "chunkSize": chunk_size,
        "chunks": chunks,
    }
    meta = {
        "name": path.name,
        "type": content_type,
        "size": len(data),
        "hash": hashlib.sha256(data).hexdigest(),
        "chunkCount": len(chunks),
        "compression": compression,
        "profile": level,
        "createdAt": created_at,
    }
    return (
        json.dumps(container, separators=(",", ":")).encode("utf-8"),
        meta,
        raw_key,
    )


def _decrypt_container(
    container: dict[str, Any],
    raw_key: bytes,
) -> tuple[bytes, str, dict[str, Any]]:
    if container.get("magic") != "CVW1" or int(container.get("v", 0)) != 1:
        raise ValueError("Unsupported container format.")
    cipher = AESGCM(raw_key)
    parts: list[bytes] = []
    for chunk in container.get("chunks", []):
        aad = f"cryptavault:web:v1:{container['fileId']}:{chunk['i']}:{chunk['f']}"
        parts.append(cipher.decrypt(_b64d(chunk["iv"]), _b64d(chunk["ct"]), aad.encode("utf-8")))
    joined = b"".join(parts)
    compression = str(container.get("compression") or "none")
    data = gzip.decompress(joined) if compression == "gzip" else joined
    return data, compression, container


def _record_file_id(record: dict[str, Any]) -> str:
    return str(record.get("file_id") or record["id"])


def _file_meta(master_key: bytes, record: dict[str, Any]) -> dict[str, Any]:
    sealed = {"ivB64": record["meta_iv"], "ctB64": record["encrypted_meta"]}
    return cast(
        dict[str, Any],
        json.loads(
            _open(master_key, sealed, f"filemeta:{_record_file_id(record)}").decode("utf-8")
        ),
    )


def _file_key(master_key: bytes, record: dict[str, Any]) -> bytes:
    sealed = {"ivB64": record["wrapped_iv"], "ctB64": record["wrapped_key"]}
    return _open(master_key, sealed, f"filekey:{_record_file_id(record)}")


def _decrypt_record(
    master_key: bytes, record: dict[str, Any], ciphertext: bytes
) -> tuple[bytes, dict[str, Any]]:
    meta = _file_meta(master_key, record)
    raw_key = _file_key(master_key, record)
    container = json.loads(ciphertext.decode("utf-8"))
    data, _compression, _container = _decrypt_container(container, raw_key)
    digest = hashlib.sha256(data).hexdigest()
    if digest != meta.get("hash"):
        raise ValueError("Integrity check failed: plaintext SHA-256 does not match the manifest.")
    return data, meta


def _build_manifest(
    meta: dict[str, Any], raw_key: bytes, passphrase: str | None
) -> tuple[dict[str, Any], bytes | None]:
    if passphrase:
        salt = secrets.token_bytes(16)
        share_key = _derive(passphrase, salt, KDF_ITERATIONS)
        share_raw = None
        kdf = "pbkdf2"
    else:
        share_raw = secrets.token_bytes(32)
        share_key = share_raw
        salt = b""
        kdf = "raw"
    wrapped = _seal(share_key, raw_key, "sharekey:v1")
    manifest = {
        "v": 1,
        "name": meta["name"],
        "type": meta["type"],
        "size": meta["size"],
        "hash": meta["hash"],
        "profile": meta["profile"],
        "compression": meta["compression"],
        "chunkCount": meta["chunkCount"],
        "createdAt": meta["createdAt"],
        "key": wrapped,
        "kdf": kdf,
    }
    if kdf == "pbkdf2":
        manifest["saltB64"] = _b64(salt)
        manifest["iterations"] = KDF_ITERATIONS
    return manifest, share_raw


def _share_link(share_url: str, manifest: dict[str, Any], share_raw: bytes | None) -> str:
    encoded = _b64url(json.dumps(manifest, separators=(",", ":")).encode("utf-8"))
    link = f"{share_url}?m={encoded}"
    if share_raw:
        link += f"&k={_b64url(share_raw)}"
    return link


def _parse_share_link(link: str) -> tuple[str, dict[str, Any], bytes | None]:
    if "#" not in link:
        raise ValueError("Share link must contain a #/s/TOKEN fragment.")
    fragment = link.split("#", 1)[1]
    path, _, query = fragment.partition("?")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2 or parts[0] != "s":
        raise ValueError("Share link is not a CryptaVault /s/ link.")
    token = parts[1]
    params = parse_qs(query)
    if "m" not in params:
        raise ValueError("Share link is missing the encrypted manifest (m).")
    manifest = json.loads(_b64urld(params["m"][0]).decode("utf-8"))
    key = _b64urld(params["k"][0]) if "k" in params else None
    return token, manifest, key


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@auth_app.command("login")
def login(
    email: str = typer.Option(..., "--email", "-e", prompt=True),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Master passphrase (prompted if omitted)"
    ),
) -> None:
    """Authenticate against the API and store the JWT session (never the master key)."""
    secret = _prompt_passphrase(passphrase)
    pre = _request("POST", "/api/auth/prelogin", public=True, json={"email": email}).json()
    if not pre.get("exists"):
        console.print(
            "[red]No account exists for that email. Register in the web app or CLI.[/red]"
        )
        raise typer.Exit(1)
    verifier = _derive(
        secret, _b64d(pre["auth_salt_b64"]), int(pre.get("kdf_iterations", KDF_ITERATIONS))
    )
    envelope = _request(
        "POST",
        "/api/auth/login",
        public=True,
        json={"email": email, "auth_verifier": _b64(verifier)},
    ).json()
    vault = envelope["vault"]
    key = _derive(
        secret, _b64d(vault["salt_b64"]), int(vault.get("kdf_iterations", KDF_ITERATIONS))
    )
    try:
        opened = _open(key, vault["check"], "vault:verifier")
    except InvalidTag:
        console.print(
            "[red]Login succeeded but the master passphrase could not unlock the vault.[/red]"
        )
        raise typer.Exit(1) from None
    if opened != VERIFIER:
        console.print("[red]Vault verifier mismatch.[/red]")
        raise typer.Exit(1)
    workspaces = envelope.get("workspaces") or []
    session = {
        "access_token": envelope["access_token"],
        "email": envelope["user"]["email"],
        "user": envelope["user"],
        "vault": vault,
        "workspaces": workspaces,
        "current_workspace_id": workspaces[0]["id"] if workspaces else None,
        "api_url": DEFAULT_API,
    }
    _save_session(session)
    console.print(
        f"[green]Signed in as[/green] {session['email']} · {len(workspaces)} workspace(s)"
    )
    if workspaces:
        console.print(f"Active workspace: [cyan]{workspaces[0]['name']}[/cyan]")


@auth_app.command("register")
def register(
    email: str = typer.Option(..., "--email", "-e", prompt=True),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Master passphrase (prompted if omitted)"
    ),
    display_name: str = typer.Option("", "--display-name", help="Display name"),
    profile: str = typer.Option("BALANCED", "--profile", help="Default security profile"),
) -> None:
    """Create an account and store the JWT session; the master key stays in this process."""
    secret = _prompt_passphrase(passphrase)
    if len(secret) < 10:
        console.print("[red]Use a passphrase of at least 10 characters.[/red]")
        raise typer.Exit(1)
    auth_salt = secrets.token_bytes(16)
    vault_salt = secrets.token_bytes(16)
    verifier = _derive(secret, auth_salt, KDF_ITERATIONS)
    master = _derive(secret, vault_salt, KDF_ITERATIONS)
    check = _seal(master, VERIFIER, "vault:verifier")
    envelope = _request(
        "POST",
        "/api/auth/register",
        public=True,
        json={
            "email": email,
            "display_name": display_name.strip() or "CryptaVault user",
            "auth_salt_b64": _b64(auth_salt),
            "auth_verifier": _b64(verifier),
            "vault_salt_b64": _b64(vault_salt),
            "vault_check": check,
            "kdf_iterations": KDF_ITERATIONS,
        },
    ).json()
    workspaces = envelope.get("workspaces") or []
    _save_session(
        {
            "access_token": envelope["access_token"],
            "email": envelope["user"]["email"],
            "user": envelope["user"],
            "vault": envelope["vault"],
            "workspaces": workspaces,
            "current_workspace_id": workspaces[0]["id"] if workspaces else None,
            "api_url": DEFAULT_API,
        }
    )
    console.print(f"[green]Account created:[/green] {email}")
    if workspaces:
        console.print(f"Active workspace: [cyan]{workspaces[0]['name']}[/cyan]")


@auth_app.command("whoami")
def whoami() -> None:
    """Show the current session, account, and workspace."""
    session = _refresh_session(_load_session())
    user = session["user"]
    console.print(f"[cyan]{user['display_name'] or user['email']}[/cyan] · {user['email']}")
    console.print(
        f"role={user['role']} · quota={user['quota_bytes']} bytes · used={user['used_bytes']} bytes"
    )
    for workspace in session.get("workspaces") or []:
        marker = "*" if workspace["id"] == session.get("current_workspace_id") else " "
        console.print(f" {marker} {workspace['name']} ({workspace['role']}) · {workspace['id']}")


@auth_app.command("logout")
def logout() -> None:
    """Call the API logout endpoint and remove the local session file."""
    session = _load_session(required=False)
    if session.get("access_token"):
        try:
            _request("POST", "/api/auth/logout", token=session["access_token"])
        except typer.Exit:
            pass
    _clear_session()
    console.print("[green]Signed out.[/green]")


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------


@workspace_app.command("list")
def workspace_list() -> None:
    """List every workspace visible to the account."""
    session = _refresh_session(_load_session())
    table = Table(title="Workspaces")
    table.add_column("Active", style="cyan")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Files", justify="right")
    table.add_column("Bytes", justify="right")
    table.add_column("ID", style="dim")
    for workspace in session.get("workspaces") or []:
        table.add_row(
            "*" if workspace["id"] == session.get("current_workspace_id") else "",
            workspace["name"],
            workspace["role"],
            str(workspace["file_count"]),
            str(workspace["total_bytes"]),
            workspace["id"],
        )
    console.print(table)


@workspace_app.command("create")
def workspace_create(
    name: str = typer.Argument(..., help="Workspace name"),
    profile: str = typer.Option("BALANCED", "--profile", help="Default security profile"),
    storage_target: str = typer.Option(None, "--storage-target", help="Storage target name"),
) -> None:
    """Create a workspace and make it the CLI's active workspace."""
    session = _load_session()
    payload = _request(
        "POST",
        "/api/workspaces",
        token=session["access_token"],
        json={
            "name": name,
            "default_profile": profile,
            "storage_target": storage_target,
        },
    ).json()
    _refresh_session(session)
    session["current_workspace_id"] = payload["id"]
    _save_session(session)
    console.print(f"[green]Workspace created:[/green] {payload['name']} · {payload['id']}")


@workspace_app.command("use")
def workspace_use(identifier: str = typer.Argument(..., help="Workspace name or ID")) -> None:
    """Set the active workspace for subsequent CLI commands."""
    session = _load_session()
    workspace = _find_workspace(identifier, session)
    session["current_workspace_id"] = workspace["id"]
    _save_session(session)
    console.print(f"[green]Active workspace:[/green] {workspace['name']} · {workspace['id']}")


@workspace_app.command("members")
def workspace_members(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace name or ID"),
) -> None:
    """List workspace members and roles."""
    session = _load_session()
    workspace_id = _workspace_id(workspace, session)
    members = _request(
        "GET", f"/api/workspaces/{workspace_id}/members", token=session["access_token"]
    ).json()
    table = Table(title=f"Members · {workspace_id}")
    table.add_column("Name")
    table.add_column("Email")
    table.add_column("Role")
    table.add_column("Joined")
    for member in members:
        table.add_row(
            member["display_name"] or "—",
            member["email"],
            member["role"],
            member.get("joined_at") or "—",
        )
    console.print(table)


@workspace_app.command("add-member")
def workspace_add_member(
    email: str = typer.Argument(..., help="Registered account email"),
    role: str = typer.Option("viewer", "--role", help="viewer, editor, or admin"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace name or ID"),
) -> None:
    """Add a registered user to a workspace."""
    session = _load_session()
    workspace_id = _workspace_id(workspace, session)
    _request(
        "POST",
        f"/api/workspaces/{workspace_id}/members",
        token=session["access_token"],
        json={"email": email, "role": role},
    )
    console.print(f"[green]Added[/green] {email} as {role}.")


@workspace_app.command("remove-member")
def workspace_remove_member(
    user_id: str = typer.Argument(..., help="User ID"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace name or ID"),
) -> None:
    """Remove a non-owner member from a workspace."""
    session = _load_session()
    workspace_id = _workspace_id(workspace, session)
    _request(
        "DELETE", f"/api/workspaces/{workspace_id}/members/{user_id}", token=session["access_token"]
    )
    console.print("[green]Member removed.[/green]")


@workspace_app.command("delete")
def workspace_delete(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace name or ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Permanently delete a workspace owned by this account."""
    session = _load_session()
    workspace_id = _workspace_id(workspace, session)
    if not yes:
        typer.confirm("Delete the workspace and every encrypted file in it?", abort=True)
    _request("DELETE", f"/api/workspaces/{workspace_id}", token=session["access_token"])
    _refresh_session(session)
    if session.get("current_workspace_id") == workspace_id:
        session["current_workspace_id"] = (
            session["workspaces"][0]["id"] if session.get("workspaces") else None
        )
        _save_session(session)
    console.print("[green]Workspace deleted.[/green]")


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@files_app.command("list")
def files_list(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace name or ID"),
    trash: bool = typer.Option(False, "--trash", help="List trashed files"),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Master passphrase (prompted if omitted)"
    ),
) -> None:
    """List active or trashed encrypted files."""
    session = _load_session()
    workspace_id = _workspace_id(workspace, session)
    path = (
        f"/api/workspaces/{workspace_id}/trash"
        if trash
        else f"/api/workspaces/{workspace_id}/files"
    )
    records = _request("GET", path, token=session["access_token"]).json()
    master = _master_key(passphrase)[0]
    table = Table(title="Trash" if trash else "Encrypted files")
    table.add_column("Name")
    table.add_column("Size", justify="right")
    table.add_column("Profile")
    table.add_column("Version", justify="right")
    table.add_column("Storage")
    table.add_column("Updated")
    table.add_column("ID", style="dim")
    for record in records:
        try:
            meta = _file_meta(master, record)
            name = meta.get("name", record["id"])
            size = str(meta.get("size", record["ciphertext_size"]))
        except Exception:
            name = f"Encrypted file {record['id'][:8]}"
            size = str(record["ciphertext_size"])
        table.add_row(
            name,
            size,
            record.get("profile", "—"),
            f"v{record['current_version']} / {record['version_count']}",
            record.get("storage_target", "—"),
            record.get("updated_at") or "—",
            record["id"],
        )
    console.print(table)


@files_app.command("upload")
def files_upload(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace name or ID"),
    profile: str = typer.Option("BALANCED", "--profile", help="Security profile"),
    compress: str = typer.Option("auto", "--compress", help="auto, on, or off"),
    version_of: str = typer.Option(
        None, "--version-of", help="Existing file ID to add a version to"
    ),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Master passphrase (prompted if omitted)"
    ),
) -> None:
    """Encrypt a file client-side and upload ciphertext + wrapped keys."""
    session = _load_session()
    workspace_id = _workspace_id(workspace, session)
    master = _master_key(passphrase)[0]
    compress = compress.lower()
    if compress not in {"auto", "on", "off"}:
        console.print("[red]--compress must be auto, on, or off.[/red]")
        raise typer.Exit(1)
    file_id: str | None = None
    version = 1
    if version_of:
        records = _request(
            "GET", f"/api/workspaces/{workspace_id}/files", token=session["access_token"]
        ).json()
        record = next((item for item in records if item["id"] == version_of), None)
        if record is None:
            console.print(f"[red]File not found in workspace:[/red] {version_of}")
            raise typer.Exit(1)
        file_id = record["id"]
        version = int(record["current_version"]) + 1
    ciphertext, meta, raw_key = _encrypt_file(path, master, profile, compress, file_id)
    file_id = file_id or json.loads(ciphertext.decode("utf-8"))["fileId"]
    meta_sealed = _seal(
        master, json.dumps(meta, separators=(",", ":")).encode("utf-8"), f"filemeta:{file_id}"
    )
    key_sealed = _seal(master, raw_key, f"filekey:{file_id}")
    data = {
        "file_id": file_id,
        "version": str(version),
        "encrypted_meta": meta_sealed["ctB64"],
        "meta_iv": meta_sealed["ivB64"],
        "wrapped_key": key_sealed["ctB64"],
        "wrapped_iv": key_sealed["ivB64"],
        "content_tag": meta["hash"],
        "profile": meta["profile"],
    }
    response = _request(
        "POST",
        f"/api/workspaces/{workspace_id}/files/upload",
        token=session["access_token"],
        data=data,
        files={"ciphertext": (f"{file_id}.v{version}.cv", ciphertext, "application/octet-stream")},
    ).json()
    console.print(
        f"[green]Uploaded[/green] {meta['name']} · v{version} · "
        f"{len(ciphertext)} ciphertext bytes · file {response['id']}"
    )


def _download_record(
    record: dict[str, Any],
    version: int | None = None,
    passphrase: str | None = None,
) -> tuple[bytes, dict[str, Any]]:
    session = _load_session()
    master = _master_key(passphrase)[0]
    if version is not None:
        versions = _request(
            "GET", f"/api/files/{record['id']}/versions", token=session["access_token"]
        ).json()
        selected = next((item for item in versions if int(item["version"]) == version), None)
        if selected is None:
            console.print(f"[red]Version {version} not found.[/red]")
            raise typer.Exit(1)
        record = selected
    file_id = _record_file_id(record)
    ciphertext = _request(
        "GET",
        f"/api/files/{file_id}/download" + (f"?version={version}" if version is not None else ""),
        token=session["access_token"],
    ).content
    try:
        return _decrypt_record(master, record, ciphertext)
    except (ValueError, InvalidTag, KeyError) as exc:
        console.print(f"[red]Decryption failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@files_app.command("download")
def files_download(
    file_id: str = typer.Argument(..., help="File ID"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path"),
    version: int = typer.Option(None, "--version", help="Version number (default: current)"),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Master passphrase (prompted if omitted)"
    ),
) -> None:
    """Download ciphertext and decrypt/verify it locally."""
    session = _load_session()
    record = _request("GET", f"/api/files/{file_id}", token=session["access_token"]).json()
    data, meta = _download_record(record, version, passphrase)
    target = output or Path(meta["name"])
    target.write_bytes(data)
    console.print(f"[green]Decrypted[/green] {meta['name']} → {target} · {len(data)} bytes")


@files_app.command("versions")
def files_versions(file_id: str = typer.Argument(..., help="File ID")) -> None:
    """List every immutable version of a file."""
    session = _load_session()
    versions = _request(
        "GET", f"/api/files/{file_id}/versions", token=session["access_token"]
    ).json()
    table = Table(title=f"Versions · {file_id}")
    table.add_column("Version", justify="right")
    table.add_column("Current")
    table.add_column("Ciphertext bytes", justify="right")
    table.add_column("Profile")
    table.add_column("Storage")
    table.add_column("Created")
    for item in versions:
        table.add_row(
            str(item["version"]),
            "yes" if item["is_current"] else "",
            str(item["ciphertext_size"]),
            item.get("profile", "—"),
            item.get("storage_target", "—"),
            item.get("created_at") or "—",
        )
    console.print(table)


@files_app.command("restore")
def files_restore(
    file_id: str = typer.Argument(..., help="File ID"),
    version: int = typer.Argument(..., help="Version number"),
) -> None:
    """Make an older version current again."""
    session = _load_session()
    _request("POST", f"/api/files/{file_id}/restore/{version}", token=session["access_token"])
    console.print(f"[green]Restored[/green] {file_id} to v{version}.")


@files_app.command("trash")
def files_trash(file_id: str = typer.Argument(..., help="File ID")) -> None:
    """Move a file to the recycle bin."""
    session = _load_session()
    _request("DELETE", f"/api/files/{file_id}", token=session["access_token"])
    console.print("[green]Moved to trash.[/green]")


@files_app.command("untrash")
def files_untrash(file_id: str = typer.Argument(..., help="File ID")) -> None:
    """Restore a file from the recycle bin."""
    session = _load_session()
    _request("POST", f"/api/files/{file_id}/untrash", token=session["access_token"])
    console.print("[green]Restored from trash.[/green]")


@files_app.command("delete")
def files_delete(
    file_id: str = typer.Argument(..., help="File ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Permanently delete every version and ciphertext object."""
    session = _load_session()
    if not yes:
        typer.confirm("Permanently delete every version of this file?", abort=True)
    _request("DELETE", f"/api/files/{file_id}/permanent", token=session["access_token"])
    console.print("[green]File permanently deleted.[/green]")


@files_app.command("rename")
def files_rename(
    file_id: str = typer.Argument(..., help="File ID"),
    name: str = typer.Argument(..., help="New display name"),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Master passphrase (prompted if omitted)"
    ),
) -> None:
    """Rename a file by re-sealing its metadata manifest."""
    session = _load_session()
    master = _master_key(passphrase)[0]
    record = _request("GET", f"/api/files/{file_id}", token=session["access_token"]).json()
    meta = _file_meta(master, record)
    meta["name"] = name
    sealed = _seal(
        master, json.dumps(meta, separators=(",", ":")).encode("utf-8"), f"filemeta:{file_id}"
    )
    _request(
        "PATCH",
        f"/api/files/{file_id}",
        token=session["access_token"],
        json={"encrypted_meta": sealed["ctB64"], "meta_iv": sealed["ivB64"]},
    )
    console.print(f"[green]Renamed[/green] {file_id} → {name}")


@files_app.command("share")
def files_share(
    file_id: str = typer.Argument(..., help="File ID"),
    ttl_hours: int = typer.Option(24, "--ttl", help="Expiry in hours"),
    max_uses: int = typer.Option(5, "--max-uses", help="Download limit"),
    password: str = typer.Option(
        None, "--password", help="Share passphrase; omitted for link capability"
    ),
    version: int = typer.Option(None, "--version", help="Version to share (default: current)"),
    passphrase: str = typer.Option(
        None, "--passphrase", "-p", help="Master passphrase (prompted if omitted)"
    ),
) -> None:
    """Create a server-enforced share and print a web-compatible manifest link."""
    session = _load_session()
    master = _master_key(passphrase)[0]
    record = _request("GET", f"/api/files/{file_id}", token=session["access_token"]).json()
    if version is not None:
        versions = _request(
            "GET", f"/api/files/{file_id}/versions", token=session["access_token"]
        ).json()
        selected = next((item for item in versions if int(item["version"]) == version), None)
        if selected is None:
            console.print("[red]Version not found.[/red]")
            raise typer.Exit(1)
        record = selected
    meta = _file_meta(master, record)
    raw_key = _file_key(master, record)
    manifest, share_raw = _build_manifest(meta, raw_key, password)
    expires = datetime.now(UTC) + timedelta(hours=max(1, ttl_hours))
    share = _request(
        "POST",
        "/api/shares",
        token=session["access_token"],
        json={
            "file_id": file_id,
            "version": record.get("version", record["current_version"]),
            "expires_at": expires.isoformat(),
            "max_uses": max(1, max_uses),
            **({"password": password} if password else {}),
        },
    ).json()
    link = _share_link(share["share_url"], manifest, share_raw)
    console.print(f"[green]Share created:[/green] {share['token']}")
    console.print(f"Expires: {expires.isoformat()} · downloads: {max_uses}")
    console.print("[bold]Share link:[/bold]")
    console.print(link, soft_wrap=True)


# ---------------------------------------------------------------------------
# Shares
# ---------------------------------------------------------------------------


@shares_app.command("list")
def shares_list() -> None:
    """List server shares owned by this account."""
    session = _load_session()
    shares = _request("GET", "/api/shares", token=session["access_token"]).json()
    table = Table(title="Shares")
    table.add_column("Token", style="dim")
    table.add_column("File")
    table.add_column("Version", justify="right")
    table.add_column("Uses", justify="right")
    table.add_column("Expires")
    table.add_column("Password")
    table.add_column("Revoked")
    for item in shares:
        table.add_row(
            item["token"][:16] + "…",
            item["file_id"],
            str(item["version"]),
            f"{item['uses']}/{item['max_uses']}",
            item.get("expires_at") or "never",
            "yes" if item["password_protected"] else "no",
            "yes" if item["revoked"] else "no",
        )
    console.print(table)


@shares_app.command("revoke")
def shares_revoke(token: str = typer.Argument(..., help="Share token")) -> None:
    """Revoke a share so the API rejects future downloads."""
    session = _load_session()
    _request("DELETE", f"/api/shares/{token}", token=session["access_token"])
    console.print("[green]Share revoked.[/green]")


@shares_app.command("decrypt")
def shares_decrypt(
    link: str = typer.Argument(..., help="Full #/s/TOKEN?m=... share link"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path"),
    password: str = typer.Option(None, "--password", help="Share passphrase if required"),
) -> None:
    """Download a share anonymously, decrypt the manifest, and verify SHA-256."""
    try:
        token, manifest, share_raw = _parse_share_link(link)
    except ValueError as exc:
        console.print(f"[red]Invalid link:[/red] {exc}")
        raise typer.Exit(1) from exc
    if manifest.get("kdf") == "pbkdf2" and not password:
        password = typer.prompt("Share passphrase", hide_input=True)
    if manifest.get("kdf") == "raw" and not share_raw:
        console.print("[red]This link is missing its capability key.[/red]")
        raise typer.Exit(1)
    response = _request(
        "POST",
        f"/api/shares/{token}/download",
        public=True,
        json={"password": password or None},
    )
    if manifest["kdf"] == "pbkdf2":
        share_key = _derive(
            password or "",
            _b64d(manifest["saltB64"]),
            int(manifest.get("iterations", KDF_ITERATIONS)),
        )
    else:
        share_key = share_raw  # type: ignore[assignment]
    try:
        raw_key = AESGCM(share_key).decrypt(
            _b64d(manifest["key"]["ivB64"]),
            _b64d(manifest["key"]["ctB64"]),
            b"sharekey:v1",
        )
        container = json.loads(response.content.decode("utf-8"))
        data, _compression, _container = _decrypt_container(container, raw_key)
    except (InvalidTag, ValueError, KeyError) as exc:
        console.print(f"[red]Share decryption failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    digest = hashlib.sha256(data).hexdigest()
    if digest != manifest.get("hash"):
        console.print("[red]Integrity check failed: plaintext hash does not match manifest.[/red]")
        raise typer.Exit(1)
    target = output or Path(manifest["name"])
    target.write_bytes(data)
    console.print(f"[green]Decrypted[/green] {manifest['name']} → {target} · {len(data)} bytes")
