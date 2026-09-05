"""CryptaVault: AI-Assisted Adaptive Hybrid Cryptographic Storage Framework."""

# Ensure standard built-in crypto plugins are registered upon importing cryptavault
import cryptavault.crypto.asymmetric as _asymmetric  # noqa: F401
import cryptavault.crypto.hash as _hash  # noqa: F401
import cryptavault.crypto.hybrid as _hybrid  # noqa: F401
import cryptavault.crypto.kdf as _kdf  # noqa: F401
import cryptavault.crypto.pq as _pq  # noqa: F401
import cryptavault.crypto.symmetric as _symmetric  # noqa: F401

__version__ = "0.1.0"
