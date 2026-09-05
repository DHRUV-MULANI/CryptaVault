"""Smoke imports test verifying all runtime dependencies are present and importable."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "cryptography",
        "cryptography.hazmat.primitives.ciphers.aead",
        "argon2",
        "blake3",
        "zstandard",
        "lzma",
        "brotli",
        "paramiko",
        "qrcode",
        "typer",
        "rich",
        "pydantic",
        "httpx",
        "mnemonic",
        "fastapi",
        "supabase",
        "gotrue",
        "psycopg2",
        "cryptavault",
        "cryptavault_api",
        "cryptavault_cli",
    ],
)
def test_smoke_import(module_name: str) -> None:
    """Ensure critical runtime and framework modules can be imported without error."""
    mod = importlib.import_module(module_name)
    assert mod is not None
