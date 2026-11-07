"""Cryptographic Algorithm Catalog for CryptaVault.

The catalog is the single source of truth for algorithm identity, capability
metadata, lifecycle status, and stable wire identifiers. The adaptive engine and
the container format resolve algorithms through this catalog instead of hard-coding
primitive names, which is what makes the platform crypto-agile.

Wire identifiers are permanent. An identifier must never be reused for a different
algorithm, because it is persisted inside encrypted containers.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cryptavault.plugins.registry import (
    encryption_registry,
    hash_registry,
    kdf_registry,
    kem_registry,
    signature_registry,
)


class CatalogError(Exception):
    """Base exception for catalog failures."""


class UnknownAlgorithmError(CatalogError):
    """Raised when an algorithm identifier is not present in the catalog."""


class AlgorithmRejectedError(CatalogError):
    """Raised when an algorithm is known but not permitted for use."""


class AlgorithmUnavailableError(CatalogError):
    """Raised when an algorithm is catalogued but not usable in this environment."""


class CryptoFamily(str, Enum):
    """Algorithm families exposed by the platform."""

    SYMMETRIC = "symmetric"
    HASH = "hash"
    KDF = "kdf"
    KEM = "kem"
    SIGNATURE = "signature"
    PAKE = "pake"
    SECRET_SHARING = "secret-sharing"
    RNG = "rng"
    QUANTUM = "quantum"


class AlgorithmStatus(str, Enum):
    """Lifecycle status controlling whether an algorithm may be used."""

    PRODUCTION = "production"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"
    FORBIDDEN = "forbidden"


class WirePrefix:
    """Stable high-byte ranges for algorithm wire identifiers."""

    SYMMETRIC = 0x01
    HASH = 0x02
    KDF = 0x03
    KEM = 0x04
    SIGNATURE = 0x05
    PAKE = 0x06
    SECRET_SHARING = 0x07
    RNG = 0x08
    QUANTUM = 0x09


@dataclass(frozen=True)
class AlgorithmSpec:
    """Capability and lifecycle metadata for a single algorithm."""

    algorithm_id: str
    family: CryptoFamily
    wire_id: int
    status: AlgorithmStatus = AlgorithmStatus.PRODUCTION
    classical_bits: int | None = None
    pq_nist_level: int | None = None
    key_size_bytes: int | None = None
    nonce_size_bytes: int | None = None
    tag_size_bytes: int | None = None
    quantum_resistant: bool = False
    hardware_accelerated: bool = False
    implemented: bool = True
    requires: tuple[str, ...] = ()
    aliases: frozenset[str] = field(default_factory=frozenset)
    replaced_by: str | None = None
    description: str = ""

    def missing_requirements(self) -> tuple[str, ...]:
        """Return required Python distributions that are not importable."""
        missing: list[str] = []
        for requirement in self.requires:
            try:
                if importlib.util.find_spec(requirement) is None:
                    missing.append(requirement)
            except (ImportError, ValueError):
                missing.append(requirement)
        return tuple(missing)

    def is_runtime_available(self) -> bool:
        """Return whether the algorithm can run in the current environment."""
        return self.implemented and not self.missing_requirements()


class CryptoCatalog:
    """Registry of algorithm metadata with alias and wire-id resolution."""

    def __init__(self) -> None:
        self._specs: dict[str, AlgorithmSpec] = {}
        self._aliases: dict[str, str] = {}
        self._by_wire: dict[int, str] = {}

    def register(self, spec: AlgorithmSpec) -> AlgorithmSpec:
        """Register one algorithm spec, rejecting identity collisions."""
        algorithm_id = spec.algorithm_id.strip().lower()
        if not algorithm_id:
            raise CatalogError("Algorithm identifier cannot be empty")
        if algorithm_id in self._specs:
            raise CatalogError(f"Algorithm '{algorithm_id}' is already registered")
        if spec.wire_id in self._by_wire:
            raise CatalogError(
                f"Wire id 0x{spec.wire_id:04x} is already assigned to "
                f"'{self._by_wire[spec.wire_id]}'"
            )
        for alias in spec.aliases:
            normalized = alias.strip().lower()
            if normalized in self._aliases or normalized in self._specs:
                raise CatalogError(f"Alias '{normalized}' is already registered")
            self._aliases[normalized] = algorithm_id
        self._specs[algorithm_id] = spec
        self._by_wire[spec.wire_id] = algorithm_id
        return spec

    def resolve_id(self, algorithm_id_or_alias: str) -> str:
        """Resolve an identifier or alias to the canonical algorithm id."""
        normalized = algorithm_id_or_alias.strip().lower()
        if normalized in self._specs:
            return normalized
        if normalized in self._aliases:
            return self._aliases[normalized]
        raise UnknownAlgorithmError(
            f"Unknown algorithm '{algorithm_id_or_alias}'. "
            f"Known families: {sorted({s.family.value for s in self._specs.values()})}"
        )

    def get(self, algorithm_id_or_alias: str) -> AlgorithmSpec:
        """Return the spec for an identifier or alias."""
        return self._specs[self.resolve_id(algorithm_id_or_alias)]

    def maybe_get(self, algorithm_id_or_alias: str) -> AlgorithmSpec | None:
        """Return the spec when known, otherwise ``None``."""
        try:
            return self.get(algorithm_id_or_alias)
        except UnknownAlgorithmError:
            return None

    def from_wire_id(self, wire_id: int) -> AlgorithmSpec:
        """Resolve a persisted wire identifier back to its spec."""
        algorithm_id = self._by_wire.get(wire_id)
        if algorithm_id is None:
            raise UnknownAlgorithmError(f"Unknown algorithm wire id 0x{wire_id:04x}")
        return self._specs[algorithm_id]

    def list(
        self,
        family: CryptoFamily | str | None = None,
        status: AlgorithmStatus | str | None = None,
        implemented_only: bool = False,
    ) -> list[AlgorithmSpec]:
        """List specs, optionally filtered by family, status, and availability."""
        family_value = CryptoFamily(family) if isinstance(family, str) else family
        status_value = AlgorithmStatus(status) if isinstance(status, str) else status
        specs = sorted(self._specs.values(), key=lambda spec: (spec.family.value, spec.wire_id))
        if family_value is not None:
            specs = [spec for spec in specs if spec.family == family_value]
        if status_value is not None:
            specs = [spec for spec in specs if spec.status == status_value]
        if implemented_only:
            specs = [spec for spec in specs if spec.is_runtime_available()]
        return specs

    def require_usable(
        self,
        algorithm_id_or_alias: str,
        family: CryptoFamily | str | None = None,
        allow_experimental: bool = False,
        allow_legacy: bool = False,
    ) -> AlgorithmSpec:
        """Return a spec only if it is permitted and runnable.

        This is the enforcement point that prevents silent downgrade to a
        forbidden or unavailable primitive.
        """
        spec = self.get(algorithm_id_or_alias)
        if family is not None:
            expected = CryptoFamily(family) if isinstance(family, str) else family
            if spec.family != expected:
                raise AlgorithmRejectedError(
                    f"Algorithm '{spec.algorithm_id}' belongs to family "
                    f"'{spec.family.value}', expected '{expected.value}'"
                )

        if spec.status is AlgorithmStatus.FORBIDDEN:
            raise AlgorithmRejectedError(
                f"Algorithm '{spec.algorithm_id}' is forbidden and cannot be used"
            )
        if spec.status is AlgorithmStatus.EXPERIMENTAL and not allow_experimental:
            raise AlgorithmRejectedError(
                f"Algorithm '{spec.algorithm_id}' is experimental; opt-in is required"
            )
        if spec.status is AlgorithmStatus.LEGACY and not allow_legacy:
            raise AlgorithmRejectedError(
                f"Algorithm '{spec.algorithm_id}' is legacy; opt-in is required and "
                f"replacement is '{spec.replaced_by}'"
            )

        if not spec.implemented:
            raise AlgorithmUnavailableError(
                f"Algorithm '{spec.algorithm_id}' is catalogued but not implemented"
            )
        missing = spec.missing_requirements()
        if missing:
            raise AlgorithmUnavailableError(
                f"Algorithm '{spec.algorithm_id}' requires missing distributions: "
                f"{', '.join(missing)}"
            )

        registry = _family_registry(spec.family)
        if registry is not None and spec.algorithm_id not in registry.list_available():
            raise AlgorithmUnavailableError(
                f"Algorithm '{spec.algorithm_id}' is catalogued but not registered"
            )
        return spec

    def is_usable(self, algorithm_id_or_alias: str, **kwargs: object) -> bool:
        """Return whether ``require_usable`` would succeed."""
        try:
            self.require_usable(algorithm_id_or_alias, **kwargs)  # type: ignore[arg-type]
            return True
        except CatalogError:
            return False

    def wire_id(self, algorithm_id_or_alias: str) -> int:
        """Return the stable wire identifier for an algorithm."""
        return self.get(algorithm_id_or_alias).wire_id

    @property
    def specs(self) -> Iterable[AlgorithmSpec]:
        """Iterate over all registered specs."""
        return tuple(self._specs.values())


def _family_registry(family: CryptoFamily) -> Any:
    return {
        CryptoFamily.SYMMETRIC: encryption_registry,
        CryptoFamily.HASH: hash_registry,
        CryptoFamily.KDF: kdf_registry,
        CryptoFamily.KEM: kem_registry,
        CryptoFamily.SIGNATURE: signature_registry,
    }.get(family)


def _spec(
    algorithm_id: str,
    family: CryptoFamily,
    wire_id: int,
    **kwargs: Any,
) -> AlgorithmSpec:
    return AlgorithmSpec(algorithm_id=algorithm_id, family=family, wire_id=wire_id, **kwargs)


def _build_default_catalog() -> CryptoCatalog:
    catalog = CryptoCatalog()

    symmetric = CryptoFamily.SYMMETRIC
    symmetric_specs = [
        _spec(
            "aes-128-gcm",
            symmetric,
            0x0101,
            key_size_bytes=16,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=128,
            hardware_accelerated=True,
            aliases=frozenset({"aes128gcm", "aes-gcm-128"}),
        ),
        _spec(
            "aes-192-gcm",
            symmetric,
            0x0102,
            key_size_bytes=24,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=192,
            hardware_accelerated=True,
            aliases=frozenset({"aes192gcm", "aes-gcm-192"}),
        ),
        _spec(
            "aes-256-gcm",
            symmetric,
            0x0103,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=256,
            hardware_accelerated=True,
            aliases=frozenset({"aes256gcm", "aes-gcm"}),
        ),
        _spec(
            "aes-128-ccm",
            symmetric,
            0x0104,
            key_size_bytes=16,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=128,
            hardware_accelerated=True,
        ),
        _spec(
            "aes-256-ccm",
            symmetric,
            0x0105,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=256,
            hardware_accelerated=True,
        ),
        _spec(
            "aes-256-gcm-siv",
            symmetric,
            0x0106,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=256,
            hardware_accelerated=True,
            aliases=frozenset({"aes-gcm-siv", "gcmsiv"}),
        ),
        _spec(
            "aes-256-ocb3",
            symmetric,
            0x0107,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=256,
            hardware_accelerated=True,
        ),
        _spec(
            "chacha20-poly1305",
            symmetric,
            0x0108,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=256,
            aliases=frozenset({"chacha20poly1305", "chacha20"}),
        ),
        _spec(
            "xchacha20-poly1305",
            symmetric,
            0x0109,
            key_size_bytes=32,
            nonce_size_bytes=24,
            tag_size_bytes=16,
            classical_bits=256,
            implemented=False,
            description="24-byte nonce variant; requires a library exposing XChaCha20",
        ),
        _spec(
            "ascon-128a",
            symmetric,
            0x010A,
            key_size_bytes=16,
            nonce_size_bytes=16,
            tag_size_bytes=16,
            classical_bits=128,
            implemented=False,
        ),
        _spec(
            "camellia-256-gcm",
            symmetric,
            0x010B,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=256,
            implemented=False,
        ),
        _spec(
            "aria-256-gcm",
            symmetric,
            0x010C,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=256,
            implemented=False,
        ),
        _spec(
            "sm4-gcm",
            symmetric,
            0x010D,
            key_size_bytes=16,
            nonce_size_bytes=12,
            tag_size_bytes=16,
            classical_bits=128,
            implemented=False,
        ),
        _spec(
            "aes-256-siv",
            symmetric,
            0x010E,
            key_size_bytes=64,
            nonce_size_bytes=None,
            tag_size_bytes=16,
            classical_bits=256,
            implemented=False,
            description="Deterministic, nonce-less AEAD; needs a dedicated interface",
        ),
        _spec(
            "cascade-chacha20-aes256gcm",
            symmetric,
            0x010F,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=32,
            classical_bits=256,
            implemented=True,
            aliases=frozenset({"multi-layer", "cascade"}),
            description="Inner ChaCha20-Poly1305 layered under AES-256-GCM",
        ),
        _spec(
            "cascade-aes256gcm-chacha20",
            symmetric,
            0x0110,
            key_size_bytes=32,
            nonce_size_bytes=12,
            tag_size_bytes=32,
            classical_bits=256,
            implemented=False,
            description="Reserved reverse cascade order",
        ),
    ]

    hash_family = CryptoFamily.HASH
    hash_specs = [
        _spec(
            "sha256",
            hash_family,
            0x0201,
            classical_bits=256,
            aliases=frozenset({"sha-256", "sha2-256"}),
        ),
        _spec("sha3-512", hash_family, 0x0202, classical_bits=512, aliases=frozenset({"sha3_512"})),
        _spec("blake3", hash_family, 0x0203, classical_bits=256),
        _spec("sha3-256", hash_family, 0x0204, classical_bits=256, implemented=False),
        _spec("sha512", hash_family, 0x0205, classical_bits=512, implemented=False),
        _spec("blake2b", hash_family, 0x0206, classical_bits=256, implemented=False),
        _spec("blake2s", hash_family, 0x0207, classical_bits=256, implemented=False),
        _spec("shake128", hash_family, 0x0208, classical_bits=128, implemented=False),
        _spec("shake256", hash_family, 0x0209, classical_bits=256, implemented=False),
        _spec("kmac256", hash_family, 0x020A, classical_bits=256, implemented=False),
        _spec(
            "hmac-sha256",
            hash_family,
            0x020B,
            classical_bits=256,
            implemented=False,
            aliases=frozenset({"hmac"}),
        ),
        _spec("sm3", hash_family, 0x020C, classical_bits=256, implemented=False),
        _spec("streebog-512", hash_family, 0x020D, classical_bits=512, implemented=False),
        _spec("whirlpool", hash_family, 0x020E, classical_bits=512, implemented=False),
        _spec(
            "sha1",
            hash_family,
            0x020F,
            classical_bits=160,
            status=AlgorithmStatus.LEGACY,
            implemented=False,
            replaced_by="sha256",
            description="Verification only; never for new data",
        ),
        _spec(
            "md5",
            hash_family,
            0x0210,
            classical_bits=128,
            status=AlgorithmStatus.FORBIDDEN,
            implemented=False,
            replaced_by="sha256",
        ),
        _spec(
            "md4",
            hash_family,
            0x0211,
            classical_bits=128,
            status=AlgorithmStatus.FORBIDDEN,
            implemented=False,
            replaced_by="sha256",
        ),
    ]

    kdf = CryptoFamily.KDF
    kdf_specs = [
        _spec("argon2id", kdf, 0x0301, classical_bits=256, aliases=frozenset({"argon2"})),
        _spec("pbkdf2-sha256", kdf, 0x0302, classical_bits=256, aliases=frozenset({"pbkdf2"})),
        _spec("hkdf-sha256", kdf, 0x0303, classical_bits=256, aliases=frozenset({"hkdf"})),
        _spec("scrypt", kdf, 0x0304, classical_bits=256, implemented=False),
        _spec(
            "bcrypt",
            kdf,
            0x0305,
            classical_bits=192,
            implemented=False,
            status=AlgorithmStatus.LEGACY,
            replaced_by="argon2id",
        ),
        _spec("yescrypt", kdf, 0x0306, classical_bits=256, implemented=False),
        _spec("balloon", kdf, 0x0307, classical_bits=256, implemented=False),
    ]

    kem = CryptoFamily.KEM
    kem_specs = [
        _spec(
            "x25519",
            kem,
            0x0401,
            classical_bits=128,
            key_size_bytes=32,
            aliases=frozenset({"curve25519"}),
        ),
        _spec("x448", kem, 0x0402, classical_bits=224, key_size_bytes=56, implemented=False),
        _spec("ecdh-p256", kem, 0x0403, classical_bits=128, implemented=False),
        _spec(
            "ml-kem-512",
            kem,
            0x0404,
            pq_nist_level=1,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
            aliases=frozenset({"kyber512", "kyber-512", "mlkem512"}),
        ),
        _spec(
            "ml-kem-768",
            kem,
            0x0405,
            pq_nist_level=3,
            quantum_resistant=True,
            requires=("oqs",),
            aliases=frozenset({"kyber768", "kyber", "mlkem768"}),
        ),
        _spec(
            "ml-kem-1024",
            kem,
            0x0406,
            pq_nist_level=5,
            quantum_resistant=True,
            requires=("oqs",),
            aliases=frozenset({"kyber1024", "mlkem1024"}),
        ),
        _spec(
            "frodokem-976",
            kem,
            0x0407,
            pq_nist_level=3,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
        ),
        _spec(
            "ntru-hps-2048-509",
            kem,
            0x0408,
            pq_nist_level=1,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
        ),
        _spec(
            "classic-mceliece-348864",
            kem,
            0x0409,
            pq_nist_level=1,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
        ),
        _spec(
            "hqc-256",
            kem,
            0x040A,
            pq_nist_level=5,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
        ),
        _spec(
            "bike-l1",
            kem,
            0x040B,
            pq_nist_level=1,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "saber",
            kem,
            0x040C,
            pq_nist_level=3,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "hybrid-kem-classical",
            kem,
            0x040D,
            classical_bits=128,
            quantum_resistant=False,
            aliases=frozenset({"x25519-hkdf"}),
        ),
        _spec(
            "hybrid-kem-pq",
            kem,
            0x040E,
            classical_bits=128,
            pq_nist_level=3,
            quantum_resistant=True,
            requires=("oqs",),
        ),
        _spec(
            "sike-p434",
            kem,
            0x040F,
            pq_nist_level=1,
            quantum_resistant=True,
            status=AlgorithmStatus.FORBIDDEN,
            implemented=False,
            description="Broken isogeny scheme; never use",
        ),
    ]

    signature = CryptoFamily.SIGNATURE
    signature_specs = [
        _spec("ed25519", signature, 0x0501, classical_bits=128, aliases=frozenset({"ed-25519"})),
        _spec("ed448", signature, 0x0502, classical_bits=224, implemented=False),
        _spec(
            "ecdsa-p256",
            signature,
            0x0503,
            classical_bits=128,
            aliases=frozenset({"p-256", "secp256r1"}),
        ),
        _spec(
            "ecdsa-p384",
            signature,
            0x0504,
            classical_bits=192,
            implemented=False,
            aliases=frozenset({"p-384", "secp384r1"}),
        ),
        _spec(
            "ecdsa-p521",
            signature,
            0x0505,
            classical_bits=256,
            implemented=False,
            aliases=frozenset({"p-521", "secp521r1"}),
        ),
        _spec("rsa-pss-3072", signature, 0x0506, classical_bits=128, implemented=False),
        _spec(
            "rsa-pss-4096",
            signature,
            0x0507,
            classical_bits=152,
            implemented=False,
            aliases=frozenset({"rsa-4096", "rsa"}),
        ),
        _spec("secp256k1", signature, 0x0508, classical_bits=128, implemented=False),
        _spec(
            "ml-dsa-44",
            signature,
            0x0509,
            pq_nist_level=2,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
            aliases=frozenset({"dilithium2", "dilithium-2"}),
        ),
        _spec(
            "ml-dsa-65",
            signature,
            0x050A,
            pq_nist_level=3,
            quantum_resistant=True,
            requires=("oqs",),
            aliases=frozenset({"dilithium3", "dilithium"}),
        ),
        _spec(
            "ml-dsa-87",
            signature,
            0x050B,
            pq_nist_level=5,
            quantum_resistant=True,
            requires=("oqs",),
            aliases=frozenset({"dilithium5"}),
        ),
        _spec(
            "slh-dsa-sha2-128s",
            signature,
            0x050C,
            pq_nist_level=1,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
        ),
        _spec(
            "slh-dsa-shake-256s",
            signature,
            0x050D,
            pq_nist_level=5,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
        ),
        _spec(
            "falcon-512",
            signature,
            0x050E,
            pq_nist_level=1,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
            aliases=frozenset({"fn-dsa-512"}),
        ),
        _spec(
            "fn-dsa-512",
            signature,
            0x050F,
            pq_nist_level=1,
            quantum_resistant=True,
            requires=("oqs",),
            implemented=False,
        ),
        _spec(
            "lms",
            signature,
            0x0510,
            pq_nist_level=1,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "xmss",
            signature,
            0x0511,
            pq_nist_level=1,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "hybrid-sig-pq",
            signature,
            0x0512,
            classical_bits=128,
            pq_nist_level=3,
            quantum_resistant=True,
            requires=("oqs",),
            aliases=frozenset({"ed25519-dilithium3"}),
        ),
        _spec(
            "rainbow",
            signature,
            0x0513,
            pq_nist_level=1,
            quantum_resistant=True,
            status=AlgorithmStatus.FORBIDDEN,
            implemented=False,
            description="Broken multivariate scheme; never use",
        ),
        _spec(
            "mayo-1",
            signature,
            0x0514,
            pq_nist_level=1,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "cross-128",
            signature,
            0x0515,
            pq_nist_level=1,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "uov",
            signature,
            0x0516,
            pq_nist_level=1,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "sqisign",
            signature,
            0x0517,
            pq_nist_level=1,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "bls12-381",
            signature,
            0x0518,
            classical_bits=128,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "ed25519-blake3",
            signature,
            0x0519,
            classical_bits=128,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
    ]

    pake = CryptoFamily.PAKE
    pake_specs = [
        _spec("spake2", pake, 0x0601, classical_bits=128, implemented=False),
        _spec(
            "opaque",
            pake,
            0x0602,
            classical_bits=128,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "srp-6a",
            pake,
            0x0603,
            classical_bits=128,
            implemented=False,
            status=AlgorithmStatus.LEGACY,
            replaced_by="opaque",
        ),
    ]

    sharing = CryptoFamily.SECRET_SHARING
    sharing_specs = [
        _spec(
            "shamir-secret-sharing",
            sharing,
            0x0701,
            classical_bits=256,
            implemented=False,
            aliases=frozenset({"shamir", "sss"}),
        ),
    ]

    rng = CryptoFamily.RNG
    rng_specs = [
        _spec(
            "os-csprng",
            rng,
            0x0801,
            classical_bits=256,
            description="Operating-system cryptographic random source",
        ),
        _spec(
            "qrng",
            rng,
            0x0802,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
    ]

    quantum = CryptoFamily.QUANTUM
    quantum_specs = [
        _spec(
            "qkd-bb84",
            quantum,
            0x0901,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
        _spec(
            "qkd-e91",
            quantum,
            0x0902,
            quantum_resistant=True,
            implemented=False,
            status=AlgorithmStatus.EXPERIMENTAL,
        ),
    ]

    for spec in (
        symmetric_specs
        + hash_specs
        + kdf_specs
        + kem_specs
        + signature_specs
        + pake_specs
        + sharing_specs
        + rng_specs
        + quantum_specs
    ):
        catalog.register(spec)

    return catalog


catalog = _build_default_catalog()


__all__ = [
    "AlgorithmRejectedError",
    "AlgorithmSpec",
    "AlgorithmStatus",
    "AlgorithmUnavailableError",
    "CatalogError",
    "CryptoCatalog",
    "CryptoFamily",
    "UnknownAlgorithmError",
    "WirePrefix",
    "catalog",
]
