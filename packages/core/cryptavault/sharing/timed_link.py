"""Time-Limited Share Link generator and tamper-evident verifier."""

from __future__ import annotations

import base64
import hmac
import time
from hashlib import sha256
from typing import NamedTuple
from urllib.parse import parse_qs, urlencode, urlparse


class LinkValidationResult(NamedTuple):
    is_valid: bool
    file_id: str | None
    remaining_seconds: int
    error: str | None


class TimedShareLink:
    """Generates and verifies cryptographic time-limited share URLs."""

    @staticmethod
    def generate_link(
        base_url: str,
        secret_key: bytes,
        file_id: str,
        validity_seconds: int = 3600,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """Create a signed URL that expires after validity_seconds."""
        expires_at_epoch = int(time.time()) + validity_seconds
        params: dict[str, str] = {
            "fid": file_id,
            "exp": str(expires_at_epoch),
        }
        if extra_params:
            params.update(extra_params)

        # Compute tamper-evident HMAC over query parameters
        msg = f"{file_id}:{expires_at_epoch}".encode()
        sig = hmac.new(secret_key, msg, sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        params["sig"] = sig_b64

        query_str = urlencode(params)
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}{query_str}"

    @staticmethod
    def verify_link(url: str, secret_key: bytes) -> LinkValidationResult:
        """Verify URL signature and check whether the link has expired."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        fid = params.get("fid", [None])[0]
        exp_str = params.get("exp", [None])[0]
        sig_b64 = params.get("sig", [None])[0]

        if not fid or not exp_str or not sig_b64:
            return LinkValidationResult(
                False, None, 0, "Missing required link parameters (fid, exp, sig)"
            )

        try:
            exp_epoch = int(exp_str)
        except ValueError:
            return LinkValidationResult(False, None, 0, "Invalid expiration timestamp")

        # Verify HMAC signature
        msg = f"{fid}:{exp_epoch}".encode()
        expected_sig = hmac.new(secret_key, msg, sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        if not hmac.compare_digest(sig_b64, expected_b64):
            return LinkValidationResult(
                False, None, 0, "Signature verification failed — URL has been tampered with"
            )

        current_epoch = int(time.time())
        remaining = exp_epoch - current_epoch
        if remaining <= 0:
            return LinkValidationResult(False, fid, 0, "Link has expired")

        return LinkValidationResult(True, fid, remaining, None)
