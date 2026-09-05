"""Security Profile Definitions for CryptaVault Adaptive Cryptographic Engine.

Defines the 5 core adaptive security profiles:
- PERFORMANCE (0–20% slider): Maximizes throughput on constrained devices with classical high-speed primitives.
- STANDARD (20–40% slider): Lightweight cloud storage with standard NIST compliance.
- BALANCED (40–60% slider, Default): Optimal trade-off between modern security, compliance, and speed.
- STRONG (60–80% slider): Heightened classical margin with mandatory post-quantum hybrid defense.
- MAXIMUM (80–100% slider): Post-quantum mandatory, dual-layer AEAD, maximum memory-hard KDF, and forward secrecy.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SecurityLevel(str, Enum):
    """Enumeration of adaptive security tiers."""

    PERFORMANCE = "PERFORMANCE"
    STANDARD = "STANDARD"
    BALANCED = "BALANCED"
    STRONG = "STRONG"
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
    metadata_encryption: bool = Field(
        default=True, description="Whether file manifests and metadata are encrypted"
    )
    audit_logging: bool = Field(
        default=True, description="Whether tamper-evident signed audit trails are generated"
    )
    forward_secrecy: bool = Field(
        default=False, description="Whether ratcheted per-file keys are used"
    )
    multi_layer_encryption: bool = Field(
        default=False, description="Whether dual-layer AEAD encryption is applied"
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
    metadata_encryption=False,
    audit_logging=True,
    forward_secrecy=False,
    multi_layer_encryption=False,
)

PROFILE_STANDARD = SecurityProfile(
    name="Standard Security",
    level=SecurityLevel.STANDARD,
    description="Cost-effective enterprise storage baseline with NIST compliance.",
    symmetric_cipher="aes-256-gcm",
    hash_algorithm="sha256",
    signature_algorithm="ed25519",
    kem_algorithm="x25519",
    kdf_memory_cost_kib=49152,  # 48 MiB
    kdf_time_cost=3,
    kdf_parallelism=4,
    compression_algorithm="zstd",
    chunk_size_bytes=4 * 1024 * 1024,  # 4 MiB
    post_quantum_protected=False,
    metadata_encryption=True,
    audit_logging=True,
    forward_secrecy=False,
    multi_layer_encryption=False,
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
    metadata_encryption=True,
    audit_logging=True,
    forward_secrecy=False,
    multi_layer_encryption=False,
)

PROFILE_STRONG = SecurityProfile(
    name="Strong Security",
    level=SecurityLevel.STRONG,
    description="Enhanced side-channel defense with ChaCha20-Poly1305 and dual post-quantum signatures.",
    symmetric_cipher="chacha20-poly1305",
    hash_algorithm="blake3",
    signature_algorithm="hybrid-sig-pq",
    kem_algorithm="hybrid-kem-pq",
    kdf_memory_cost_kib=65536,  # 64 MiB
    kdf_time_cost=4,
    kdf_parallelism=4,
    compression_algorithm="zstd",
    chunk_size_bytes=8 * 1024 * 1024,  # 8 MiB
    post_quantum_protected=True,
    metadata_encryption=True,
    audit_logging=True,
    forward_secrecy=True,
    multi_layer_encryption=False,
)

PROFILE_MAXIMUM = SecurityProfile(
    name="Maximum Post-Quantum Security",
    level=SecurityLevel.MAXIMUM,
    description="State-sponsored threat model protection with dual-layer AEAD, NIST ML-KEM/ML-DSA, and SHA3-512.",
    symmetric_cipher="aes-256-gcm",
    hash_algorithm="sha3-512",
    signature_algorithm="hybrid-sig-pq",
    kem_algorithm="hybrid-kem-pq",
    kdf_memory_cost_kib=131072,  # 128 MiB
    kdf_time_cost=5,
    kdf_parallelism=4,
    compression_algorithm="zstd",
    chunk_size_bytes=16 * 1024 * 1024,  # 16 MiB
    post_quantum_protected=True,
    metadata_encryption=True,
    audit_logging=True,
    forward_secrecy=True,
    multi_layer_encryption=True,
)

_PROFILES_BY_LEVEL: dict[SecurityLevel, SecurityProfile] = {
    SecurityLevel.PERFORMANCE: PROFILE_PERFORMANCE,
    SecurityLevel.STANDARD: PROFILE_STANDARD,
    SecurityLevel.BALANCED: PROFILE_BALANCED,
    SecurityLevel.STRONG: PROFILE_STRONG,
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


def resolve_slider(percentage: float) -> SecurityProfile:
    """Resolve a slider percentage (0.0 to 100.0) to a concrete SecurityProfile.

    Ranges:
    - 0 <= pct < 20: PERFORMANCE
    - 20 <= pct < 40: STANDARD
    - 40 <= pct < 60: BALANCED
    - 60 <= pct < 80: STRONG
    - 80 <= pct <= 100: MAXIMUM
    """
    if percentage < 0.0 or percentage > 100.0:
        raise ValueError(f"Slider percentage must be between 0 and 100, got {percentage}")

    if percentage < 20.0:
        return PROFILE_PERFORMANCE
    if percentage < 40.0:
        return PROFILE_STANDARD
    if percentage < 60.0:
        return PROFILE_BALANCED
    if percentage < 80.0:
        return PROFILE_STRONG
    return PROFILE_MAXIMUM


SECURITY_PROFILES: dict[str, SecurityProfile] = {
    lvl.value: prof for lvl, prof in _PROFILES_BY_LEVEL.items()
}
