"""Classical Hybrid Key Encapsulation Mechanism (KEM) for CryptaVault.

Combines ephemeral X25519 Diffie-Hellman with HKDF-SHA256 key expansion
to guarantee forward secrecy and bind shared secret derivation to public key identities.
"""

from __future__ import annotations

from typing import ClassVar

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from cryptavault.plugins.registry import KemAlgorithm, register_kem


@register_kem("hybrid-kem-classical")
class HybridKemClassical(KemAlgorithm):
    """Ephemeral X25519 Diffie-Hellman with HKDF-SHA256 key derivation."""

    name: ClassVar[str] = "hybrid-kem-classical"
    CONTEXT_INFO: ClassVar[bytes] = b"cryptavault:classical-hybrid-kem:v1"

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate static recipient (public_bytes, private_bytes) 32-byte keys."""
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
        """Generate ephemeral X25519 keypair, perform ECDH, and derive symmetric key via HKDF.

        Returns (shared_secret, ephemeral_public_key).
        """
        peer_pub = x25519.X25519PublicKey.from_public_bytes(public_key)
        eph_priv = x25519.X25519PrivateKey.generate()
        eph_pub = eph_priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        raw_secret = eph_priv.exchange(peer_pub)

        # HKDF salt binds the ephemeral and recipient public keys to prevent cross-context replay
        salt = eph_pub + public_key
        shared_secret = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.CONTEXT_INFO,
        ).derive(raw_secret)

        return shared_secret, eph_pub

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """Derive identical shared secret from recipient's secret key and ephemeral public key."""
        recipient_priv = x25519.X25519PrivateKey.from_private_bytes(secret_key)
        recipient_pub = recipient_priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        peer_eph_pub = x25519.X25519PublicKey.from_public_bytes(ciphertext)
        raw_secret = recipient_priv.exchange(peer_eph_pub)

        salt = ciphertext + recipient_pub
        shared_secret = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.CONTEXT_INFO,
        ).derive(raw_secret)

        return shared_secret


# ====================================================================
# Post-Quantum Hybrid KEM (X25519 + Kyber768 / ML-KEM-768)
# ====================================================================


import struct

from cryptavault.crypto.asymmetric import Ed25519Signer, X25519Kem
from cryptavault.crypto.pq import Dilithium3, Kyber768
from cryptavault.plugins.registry import SignatureAlgorithm, register_signature


@register_kem("hybrid-kem-pq")
class HybridKemPQ(KemAlgorithm):
    """Post-Quantum Hybrid KEM combining classical X25519 and lattice-based Kyber768.

    Provides 'harvest now, decrypt later' security: confidentiality is preserved
    as long as EITHER the classical Diffie-Hellman or the lattice problem remains unbroken.
    """

    name: ClassVar[str] = "hybrid-kem-pq"
    CONTEXT_INFO: ClassVar[bytes] = b"cryptavault:hybrid-kem-pq:v1"

    def __init__(self) -> None:
        self.classical_kem = X25519Kem()
        self.pq_kem = Kyber768()

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate composite (public_key, private_key) containing both algorithms."""
        c_pub, c_priv = self.classical_kem.keypair()
        pq_pub, pq_priv = self.pq_kem.keypair()

        # Wire format: [2-byte c_pub_len] + [c_pub] + [pq_pub]
        pub = struct.pack(">H", len(c_pub)) + c_pub + pq_pub
        priv = struct.pack(">H", len(c_priv)) + c_priv + pq_priv
        return pub, priv

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        """Dual encapsulation against both public keys, combined via HKDF-SHA256."""
        c_pub_len = struct.unpack(">H", public_key[:2])[0]
        c_pub = public_key[2 : 2 + c_pub_len]
        pq_pub = public_key[2 + c_pub_len :]

        c_secret, c_ct = self.classical_kem.encapsulate(c_pub)
        pq_secret, pq_ct = self.pq_kem.encapsulate(pq_pub)

        # Combine shared secrets via HKDF
        ikm = c_secret + pq_secret
        salt = c_ct + pq_ct
        shared_secret = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.CONTEXT_INFO,
        ).derive(ikm)

        # Wire format: [2-byte c_ct_len] + [c_ct] + [pq_ct]
        ciphertext = struct.pack(">H", len(c_ct)) + c_ct + pq_ct
        return shared_secret, ciphertext

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """Dual decapsulation using recipient private keys, combined via HKDF-SHA256."""
        c_priv_len = struct.unpack(">H", secret_key[:2])[0]
        c_priv = secret_key[2 : 2 + c_priv_len]
        pq_priv = secret_key[2 + c_priv_len :]

        c_ct_len = struct.unpack(">H", ciphertext[:2])[0]
        c_ct = ciphertext[2 : 2 + c_ct_len]
        pq_ct = ciphertext[2 + c_ct_len :]

        c_secret = self.classical_kem.decapsulate(c_priv, c_ct)
        pq_secret = self.pq_kem.decapsulate(pq_priv, pq_ct)

        ikm = c_secret + pq_secret
        salt = c_ct + pq_ct
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=self.CONTEXT_INFO,
        ).derive(ikm)


# ====================================================================
# Post-Quantum Hybrid Signature (Ed25519 + Dilithium3 / ML-DSA-65)
# ====================================================================


@register_signature("hybrid-sig-pq")
class HybridSigPQ(SignatureAlgorithm):
    """Post-Quantum Hybrid Digital Signature combining Ed25519 and Dilithium3.

    Requires BOTH signatures to pass verification for the message to be accepted.
    Guarantees authenticity even if one of the underlying mathematical problems is broken.
    """

    name: ClassVar[str] = "hybrid-sig-pq"

    def __init__(self) -> None:
        self.classical_sig = Ed25519Signer()
        self.pq_sig = Dilithium3()

    def keypair(self) -> tuple[bytes, bytes]:
        """Generate composite (public_key, private_key) containing both signing keys."""
        c_pub, c_priv = self.classical_sig.keypair()
        pq_pub, pq_priv = self.pq_sig.keypair()

        pub = struct.pack(">H", len(c_pub)) + c_pub + pq_pub
        priv = struct.pack(">H", len(c_priv)) + c_priv + pq_priv
        return pub, priv

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Produce dual signature over the message."""
        c_priv_len = struct.unpack(">H", private_key[:2])[0]
        c_priv = private_key[2 : 2 + c_priv_len]
        pq_priv = private_key[2 + c_priv_len :]

        c_sig = self.classical_sig.sign(c_priv, message)
        pq_sig = self.pq_sig.sign(pq_priv, message)

        # Wire format: [2-byte c_sig_len] + [c_sig] + [pq_sig]
        return struct.pack(">H", len(c_sig)) + c_sig + pq_sig

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify that BOTH the classical and post-quantum signatures are valid."""
        try:
            c_pub_len = struct.unpack(">H", public_key[:2])[0]
            c_pub = public_key[2 : 2 + c_pub_len]
            pq_pub = public_key[2 + c_pub_len :]

            c_sig_len = struct.unpack(">H", signature[:2])[0]
            c_sig = signature[2 : 2 + c_sig_len]
            pq_sig = signature[2 + c_sig_len :]

            # Fail-closed: both must strictly succeed
            c_ok = self.classical_sig.verify(c_pub, message, c_sig)
            if not c_ok:
                return False

            return self.pq_sig.verify(pq_pub, message, pq_sig)
        except Exception:  # noqa: BLE001 - Fail-closed on any malformed signature
            return False
