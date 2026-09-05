"""One-Time Access Tokens with HMAC authentication and lifecycle enforcement."""

from __future__ import annotations

import base64
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256


@dataclass
class ShareToken:
    """Represents a signed access token authorizing limited access to a shared file."""

    token_id: str
    file_id: str
    nonce_hex: str
    created_at_iso: str
    expires_at_iso: str | None
    max_uses: int
    current_uses: int
    signature_b64: str

    def is_expired(self) -> bool:
        if not self.expires_at_iso:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at_iso)
            return datetime.now(UTC) > exp
        except Exception:
            return True

    def is_exhausted(self) -> bool:
        return self.current_uses >= self.max_uses

    def is_valid(self, master_key: bytes) -> bool:
        """Validate token HMAC signature, expiry, and use count."""
        if self.is_expired() or self.is_exhausted():
            return False
        expected_sig = ShareTokenManager.compute_signature(
            master_key,
            token_id=self.token_id,
            file_id=self.file_id,
            nonce_hex=self.nonce_hex,
            expires_at_iso=self.expires_at_iso,
            max_uses=self.max_uses,
        )
        return hmac.compare_digest(self.signature_b64, expected_sig)


class ShareTokenManager:
    """Manages creation, verification, and consumption of cryptographic share tokens."""

    @staticmethod
    def compute_signature(
        secret_key: bytes,
        token_id: str,
        file_id: str,
        nonce_hex: str,
        expires_at_iso: str | None,
        max_uses: int,
    ) -> str:
        msg = f"{token_id}:{file_id}:{nonce_hex}:{expires_at_iso or ''}:{max_uses}".encode()
        sig = hmac.new(secret_key, msg, sha256).digest()
        return base64.urlsafe_b64encode(sig).decode().rstrip("=")

    @classmethod
    def create_token(
        cls,
        secret_key: bytes,
        file_id: str,
        expires_at_iso: str | None = None,
        max_uses: int = 1,
    ) -> ShareToken:
        token_id = secrets.token_urlsafe(16)
        nonce_hex = secrets.token_hex(16)
        created_at = datetime.now(UTC).isoformat()
        signature = cls.compute_signature(
            secret_key,
            token_id=token_id,
            file_id=file_id,
            nonce_hex=nonce_hex,
            expires_at_iso=expires_at_iso,
            max_uses=max_uses,
        )
        return ShareToken(
            token_id=token_id,
            file_id=file_id,
            nonce_hex=nonce_hex,
            created_at_iso=created_at,
            expires_at_iso=expires_at_iso,
            max_uses=max_uses,
            current_uses=0,
            signature_b64=signature,
        )

    @classmethod
    def consume_token(cls, token: ShareToken, secret_key: bytes) -> bool:
        """Verify token and increment its usage count."""
        if not token.is_valid(secret_key):
            return False
        token.current_uses += 1
        return True
