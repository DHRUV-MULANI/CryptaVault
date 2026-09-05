"""Asymmetric Cryptography Primitives for CryptaVault.

Implements classical asymmetric cryptography:
- X25519 Diffie-Hellman Key Encapsulation (RFC 7748)
- Ed25519 Digital Signatures (RFC 8032)
- ECDSA Digital Signatures over NIST P-256 and P-384
- RSA-4096 with OAEP Encryption and PSS Signatures
- Uniform KeyPair container supporting PKCS#8 password-encrypted PEM serialization
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa, x25519

from cryptavault.plugins.registry import (
    KemAlgorithm,
    SignatureAlgorithm,
    register_kem,
    register_signature,
)


class AsymmetricCryptoError(Exception):
    """Base exception for asymmetric cryptographic failures."""


class KeyFormatError(AsymmetricCryptoError):
    """Raised when serialized key material is malformed or unsupported."""


class SignatureVerificationError(AsymmetricCryptoError):
    """Raised when signature verification fails."""


# ====================================================================
# Uniform KeyPair Container
# ====================================================================


@dataclass(frozen=True)
class KeyPair:
    """Uniform container for asymmetric key pairs."""

    algorithm: str
    public_bytes: bytes
    private_bytes: bytes

    def to_pem(self, password: bytes | None = None) -> tuple[bytes, bytes]:
        """Serialize key pair to PEM format.

        If password is provided, private key is encrypted with PKCS#8 BestAvailableEncryption.
        """
        enc: serialization.KeySerializationEncryption
        if password is not None:
            enc = serialization.BestAvailableEncryption(password)
        else:
            enc = serialization.NoEncryption()

        priv_obj: Any
        pub_obj: Any

        # Depending on algorithm, load native object to export standard PEM
        if self.algorithm == "x25519":
            priv_obj = x25519.X25519PrivateKey.from_private_bytes(self.private_bytes)
            pub_obj = priv_obj.public_key()
        elif self.algorithm == "ed25519":
            priv_obj = ed25519.Ed25519PrivateKey.from_private_bytes(self.private_bytes)
            pub_obj = priv_obj.public_key()
        elif self.algorithm in ("ecdsa-p256", "ecdsa-p384") or self.algorithm == "rsa-4096":
            priv_obj = serialization.load_der_private_key(self.private_bytes, password=None)
            pub_obj = priv_obj.public_key()
        else:
            raise KeyFormatError(f"Unsupported algorithm for PEM export: {self.algorithm}")

        priv_pem = priv_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=enc,
        )
        pub_pem = pub_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pub_pem, priv_pem


# ====================================================================
# X25519 Diffie-Hellman Key Encapsulation Mechanism
# ====================================================================


@register_kem("x25519")
class X25519Kem(KemAlgorithm):
    """X25519 ephemeral key encapsulation mechanism."""

    name: ClassVar[str] = "x25519"

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate static or ephemeral (public_bytes, private_bytes) 32-byte keys."""
        priv = x25519.X25519PrivateKey.generate()
        pub = priv.public_key()
        pub_raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        priv_raw = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pub_raw, priv_raw

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        """Generate ephemeral keypair and compute shared secret against peer public key.

        Returns (shared_secret, ephemeral_public_key).
        """
        peer_pub = x25519.X25519PublicKey.from_public_bytes(public_key)
        ephemeral_priv = x25519.X25519PrivateKey.generate()
        ephemeral_pub = ephemeral_priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        shared_secret = ephemeral_priv.exchange(peer_pub)
        return shared_secret, ephemeral_pub

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """Derive the shared secret from recipient's secret key and peer's ephemeral public key."""
        recipient_priv = x25519.X25519PrivateKey.from_private_bytes(secret_key)
        peer_pub = x25519.X25519PublicKey.from_public_bytes(ciphertext)
        return recipient_priv.exchange(peer_pub)


# ====================================================================
# Ed25519 High-Speed Digital Signatures
# ====================================================================


@register_signature("ed25519")
class Ed25519Signer(SignatureAlgorithm):
    """Ed25519 high-speed constant-time signature scheme."""

    name: ClassVar[str] = "ed25519"

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate Ed25519 (public_bytes, private_bytes) 32-byte keys."""
        priv = ed25519.Ed25519PrivateKey.generate()
        pub = priv.public_key()
        pub_raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        priv_raw = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pub_raw, priv_raw

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign message using raw 32-byte private key."""
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
        return priv.sign(message)

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify signature using raw 32-byte public key."""
        pub = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
        try:
            pub.verify(signature, message)
            return True
        except InvalidSignature:
            return False


# ====================================================================
# ECDSA Digital Signatures (NIST P-256 / P-384)
# ====================================================================


@register_signature("ecdsa-p256")
class ECDSAP256Signer(SignatureAlgorithm):
    """ECDSA signature scheme over NIST curve SECP256R1 (P-256) with SHA-256."""

    name: ClassVar[str] = "ecdsa-p256"

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate (public_der, private_der) keys."""
        priv = ec.generate_private_key(ec.SECP256R1())
        pub = priv.public_key()
        pub_der = pub.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        priv_der = priv.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pub_der, priv_der

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign message using DER-encoded private key."""
        priv = serialization.load_der_private_key(private_key, password=None)
        if not isinstance(priv, ec.EllipticCurvePrivateKey):
            raise KeyFormatError("Invalid ECDSA private key format")
        return priv.sign(message, ec.ECDSA(hashes.SHA256()))

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify signature using DER-encoded public key."""
        pub = serialization.load_der_public_key(public_key)
        if not isinstance(pub, ec.EllipticCurvePublicKey):
            return False
        try:
            pub.verify(signature, message, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False


# ====================================================================
# RSA-4096 (OAEP Encryption + PSS Signatures)
# ====================================================================


class RSA4096:
    """RSA-4096 supporting OAEP encryption/decryption and PSS signatures."""

    @staticmethod
    def generate_keypair() -> tuple[bytes, bytes]:
        """Generate 4096-bit RSA keypair, returning (public_der, private_der)."""
        priv = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        pub = priv.public_key()
        pub_der = pub.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        priv_der = priv.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pub_der, priv_der

    @staticmethod
    def encrypt_oaep(public_key: bytes, plaintext: bytes, label: bytes | None = None) -> bytes:
        """Encrypt plaintext using RSA-OAEP with SHA-256 and MGF1."""
        pub = serialization.load_der_public_key(public_key)
        if not isinstance(pub, rsa.RSAPublicKey):
            raise KeyFormatError("Invalid RSA public key")
        return pub.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=label,
            ),
        )

    @staticmethod
    def decrypt_oaep(private_key: bytes, ciphertext: bytes, label: bytes | None = None) -> bytes:
        """Decrypt ciphertext using RSA-OAEP with SHA-256 and MGF1."""
        priv = serialization.load_der_private_key(private_key, password=None)
        if not isinstance(priv, rsa.RSAPrivateKey):
            raise KeyFormatError("Invalid RSA private key")
        return priv.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=label,
            ),
        )

    @staticmethod
    def sign_pss(private_key: bytes, message: bytes) -> bytes:
        """Sign message using RSA-PSS with SHA-256 and MGF1."""
        priv = serialization.load_der_private_key(private_key, password=None)
        if not isinstance(priv, rsa.RSAPrivateKey):
            raise KeyFormatError("Invalid RSA private key")
        return priv.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

    @staticmethod
    def verify_pss(public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify RSA-PSS signature."""
        pub = serialization.load_der_public_key(public_key)
        if not isinstance(pub, rsa.RSAPublicKey):
            return False
        try:
            pub.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False
