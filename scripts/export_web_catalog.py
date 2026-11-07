"""Export the crypto catalog and adaptive profiles to JSON for the web portal."""

from __future__ import annotations

import json
from pathlib import Path

from cryptavault.adaptive.profiles import list_profiles
from cryptavault.crypto.catalog import catalog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packages" / "web" / "src" / "generated" / "catalog.json"

BANDS = {
    "PERFORMANCE": [0, 20],
    "STANDARD": [20, 40],
    "BALANCED": [40, 60],
    "STRONG": [60, 80],
    "PQ_STRONG": [80, 90],
    "MAXIMUM": [90, 100],
}


def main() -> None:
    algorithms = []
    for spec in catalog.list():
        algorithms.append(
            {
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
        )

    profiles = []
    for profile in list_profiles():
        profiles.append(
            {
                "level": profile.level.value,
                "name": profile.name,
                "description": profile.description,
                "slider_band": BANDS[profile.level.value],
                "symmetric_cipher": profile.symmetric_cipher,
                "hash_algorithm": profile.hash_algorithm,
                "signature_algorithm": profile.signature_algorithm,
                "kem_algorithm": profile.kem_algorithm,
                "kdf_algorithm": profile.kdf_algorithm,
                "kdf_memory_cost_kib": profile.kdf_memory_cost_kib,
                "kdf_time_cost": profile.kdf_time_cost,
                "kdf_parallelism": profile.kdf_parallelism,
                "compression_algorithm": profile.compression_algorithm,
                "chunk_size_bytes": profile.chunk_size_bytes,
                "post_quantum_protected": profile.post_quantum_protected,
                "metadata_encryption": profile.metadata_encryption,
                "audit_logging": profile.audit_logging,
                "forward_secrecy": profile.forward_secrecy,
                "multi_layer_encryption": profile.multi_layer_encryption,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated_by": "scripts/export_web_catalog.py",
                "families": sorted({item["family"] for item in algorithms}),
                "statuses": sorted({item["status"] for item in algorithms}),
                "algorithms": algorithms,
                "profiles": profiles,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"wrote {OUT} ({len(algorithms)} algorithms, {len(profiles)} profiles)")


if __name__ == "__main__":
    main()
