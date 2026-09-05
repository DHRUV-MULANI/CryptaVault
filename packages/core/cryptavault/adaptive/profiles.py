"""Security Profile Definitions for CryptaVault Adaptive Cryptographic Engine.

Defines the 4 core security profiles:
- PERFORMANCE: Maximizes throughput on constrained devices with classical high-speed primitives.
- BALANCED (Default): Optimal trade-off between modern security, compliance, and speed.
- HIGH: Heightened classical margin with early post-quantum defense.
- MAXIMUM: Post-quantum mandatory, maximum memory-hard KDF, and defense-in-depth.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SecurityLevel(str, Enum):
    """Enumeration of adaptive security tiers."""

    PERFORMANCE = "PERFORMANCE"
    BALANCED = "BALANCED"
    HIGH = "HIGH"
    MAXIMUM = "MAXIMUM"


class SecurityProfile(BaseModel):
    """Configuration specification for a cryptographic security profile."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Human-readable profile name")
    level: SecurityLevel = Field(..., description="Target security tier")
    description: str = Field(..., description="Profile rationale and intended threat model")
    symmetric_cipher: str = Field(..., description="AEAD symmetric cipher plugin identifier")
    hash_algorithm: str = Field(..., description="Cryptographic hash plugin identifier")
    signature_algorithm: str = Field(..., description="Digital signature plugin identifier")
    kem_algorithm: str = Field(..., description="Key encapsulation mechanism identifier")
    kdf_algorithm: str = Field(default="argon2id", description="Key derivation function identifier")
    kdf_memory_cost_kib: int = Field(default=65536, description="Argon2id memory cost in KiB")
    kdf_time_cost: int = Field(default=3, description="Argon2id iterations")
    kdf_parallelism: int = Field(default=4, description="Argon2id thread parallelism")
    compression_algorithm: str = Field(
        default="zstd", description="Compression algorithm identifier"
    )
    chunk_size_bytes: int = Field(
        default=4 * 1024 * 1024, description="Streaming pipeline chunk size"
    )
    post_quantum_protected: bool = Field(
        default=False, description="Whether PQ primitives are active"
    )


PROFILE_PERFORMANCE = SecurityProfile(
    name="Performance Optimized",
    level=SecurityLevel.PERFORMANCE,
    description="Engineered for high-throughput and mobile/battery-constrained environments.",
    symmetric_cipher="aes-256-gcm",
    hash_algorithm="blake3",
    signature_algorithm="ed25519",
    kem_algorithm="x25519",
    kdf_memory_cost_kib=32768,  # 32 MiB
    kdf_time_cost=2,
    kdf_parallelism=2,
    compression_algorithm="zstd",
    chunk_size_bytes=4 * 1024 * 1024,  # 4 MiB
    post_quantum_protected=False,
)

PROFILE_BALANCED = SecurityProfile(
    name="Balanced (Default)",
    level=SecurityLevel.BALANCED,
    description="Standard enterprise zero-knowledge baseline with hybrid post-quantum readiness.",
    symmetric_cipher="aes-256-gcm",
    hash_algorithm="sha256",
    signature_algorithm="ed25519",
    kem_algorithm="hybrid-kem-classical",
    kdf_memory_cost_kib=65536,  # 64 MiB
    kdf_time_cost=3,
    kdf_parallelism=4,
    compression_algorithm="zstd",
    chunk_size_bytes=4 * 1024 * 1024,  # 4 MiB
    post_quantum_protected=True,
)

PROFILE_HIGH = SecurityProfile(
    name="High Security",
    level=SecurityLevel.HIGH,
    description="Enhanced protection for sensitive personal and proprietary business data.",
    symmetric_cipher="chacha20-poly1305",
    hash_algorithm="blake3",
    signature_algorithm="ed25519",
    kem_algorithm="hybrid-kem-classical",
    kdf_memory_cost_kib=65536,  # 64 MiB
    kdf_time_cost=4,
    kdf_parallelism=4,
    compression_algorithm="zstd",
    chunk_size_bytes=8 * 1024 * 1024,  # 8 MiB
    post_quantum_protected=True,
)

PROFILE_MAXIMUM = SecurityProfile(
    name="Maximum Post-Quantum Security",
    level=SecurityLevel.MAXIMUM,
    description="State-sponsored threat model protection with NIST ML-KEM/ML-DSA and SHA3-512.",
    symmetric_cipher="aes-256-gcm",
    hash_algorithm="sha3-512",
    signature_algorithm="ed25519",
    kem_algorithm="hybrid-kem-classical",
    kdf_memory_cost_kib=131072,  # 128 MiB
    kdf_time_cost=5,
    kdf_parallelism=4,
    compression_algorithm="zstd",
    chunk_size_bytes=16 * 1024 * 1024,  # 16 MiB
    post_quantum_protected=True,
)

_PROFILES_BY_LEVEL: dict[SecurityLevel, SecurityProfile] = {
    SecurityLevel.PERFORMANCE: PROFILE_PERFORMANCE,
    SecurityLevel.BALANCED: PROFILE_BALANCED,
    SecurityLevel.HIGH: PROFILE_HIGH,
    SecurityLevel.MAXIMUM: PROFILE_MAXIMUM,
}


def get_profile(level_or_name: str | SecurityLevel) -> SecurityProfile:
    """Look up a security profile by level enum or string name."""
    if isinstance(level_or_name, SecurityLevel):
        return _PROFILES_BY_LEVEL[level_or_name]

    normalized = level_or_name.strip().upper()
    try:
        level = SecurityLevel(normalized)
        return _PROFILES_BY_LEVEL[level]
    except ValueError as exc:
        valid_options = [lvl.value for lvl in SecurityLevel]
        raise ValueError(
            f"Unknown security profile: '{level_or_name}'. Valid options: {valid_options}"
        ) from exc


def list_profiles() -> list[SecurityProfile]:
    """Return all available security profiles."""
    return list(_PROFILES_BY_LEVEL.values())


SECURITY_PROFILES: dict[str, SecurityProfile] = {
    lvl.value: prof for lvl, prof in _PROFILES_BY_LEVEL.items()
}
