"""Public cryptographic capability catalog and adaptive profile endpoints."""

from __future__ import annotations

from typing import Any

from cryptavault.adaptive.profiles import list_profiles
from cryptavault.crypto.catalog import AlgorithmSpec, catalog
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/api/crypto", tags=["crypto"])


def _spec_to_dict(spec: AlgorithmSpec) -> dict[str, Any]:
    """Serialize one catalog entry without leaking runtime internals."""
    return {
        "algorithm_id": spec.algorithm_id,
        "family": spec.family.value,
        "wire_id": spec.wire_id,
        "wire_id_hex": f"0x{spec.wire_id:04x}",
        "status": spec.status.value,
        "classical_bits": spec.classical_bits,
        "pq_nist_level": spec.pq_nist_level,
        "key_size_bytes": spec.key_size_bytes,
        "nonce_size_bytes": spec.nonce_size_bytes,
        "tag_size_bytes": spec.tag_size_bytes,
        "quantum_resistant": spec.quantum_resistant,
        "hardware_accelerated": spec.hardware_accelerated,
        "implemented": spec.implemented,
        "runtime_available": spec.is_runtime_available(),
        "requires": list(spec.requires),
        "aliases": sorted(spec.aliases),
        "replaced_by": spec.replaced_by,
        "description": spec.description,
    }


@router.get("/catalog")
def get_catalog(
    family: str | None = Query(default=None, description="Filter by crypto family"),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by lifecycle status"
    ),
    implemented_only: bool = Query(default=False, description="Only runtime-available entries"),
) -> dict[str, Any]:
    """Return the full crypto-agility catalog with metadata and wire identifiers."""
    try:
        specs = catalog.list(
            family=family,
            status=status_filter,
            implemented_only=implemented_only,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    families = sorted({spec.family.value for spec in catalog.list()})
    statuses = sorted({spec.status.value for spec in catalog.list()})
    return {
        "total": len(specs),
        "catalog_total": len(catalog.list()),
        "families": families,
        "statuses": statuses,
        "algorithms": [_spec_to_dict(spec) for spec in specs],
    }


@router.get("/catalog/{algorithm_id}")
def get_algorithm(algorithm_id: str) -> dict[str, Any]:
    """Return one algorithm by canonical id or alias."""
    spec = catalog.maybe_get(algorithm_id)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown algorithm '{algorithm_id}'.",
        )
    return _spec_to_dict(spec)


@router.get("/profiles")
def get_profiles() -> dict[str, Any]:
    """Return the six adaptive security profiles and their slider bands."""
    bands = [
        (0.0, 20.0, "PERFORMANCE"),
        (20.0, 40.0, "STANDARD"),
        (40.0, 60.0, "BALANCED"),
        (60.0, 80.0, "STRONG"),
        (80.0, 90.0, "PQ_STRONG"),
        (90.0, 100.0, "MAXIMUM"),
    ]
    band_map = {name: [low, high] for low, high, name in bands}
    profiles: list[dict[str, Any]] = []
    for profile in list_profiles():
        level = profile.level.value
        profiles.append(
            {
                "level": level,
                "name": profile.name,
                "description": profile.description,
                "slider_band": band_map.get(level, [0.0, 100.0]),
                "symmetric_cipher": profile.symmetric_cipher,
                "hash_algorithm": profile.hash_algorithm,
                "signature_algorithm": profile.signature_algorithm,
                "kem_algorithm": profile.kem_algorithm,
                "kdf": {
                    "algorithm": profile.kdf_algorithm,
                    "memory_cost_kib": profile.kdf_memory_cost_kib,
                    "time_cost": profile.kdf_time_cost,
                    "parallelism": profile.kdf_parallelism,
                },
                "compression_algorithm": profile.compression_algorithm,
                "chunk_size_bytes": profile.chunk_size_bytes,
                "post_quantum_protected": profile.post_quantum_protected,
                "metadata_encryption": profile.metadata_encryption,
                "audit_logging": profile.audit_logging,
                "forward_secrecy": profile.forward_secrecy,
                "multi_layer_encryption": profile.multi_layer_encryption,
            }
        )
    return {"total": len(profiles), "profiles": profiles}
