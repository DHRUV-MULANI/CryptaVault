import rawCatalog from '../generated/catalog.json';
import type { ProfileLevel } from './types';

export interface CatalogAlgorithm {
  algorithm_id: string;
  family: string;
  wire_id: number;
  wire_id_hex: string;
  status: 'production' | 'experimental' | 'legacy' | 'forbidden';
  classical_bits: number | null;
  pq_nist_level: number | null;
  key_size_bytes: number | null;
  nonce_size_bytes: number | null;
  tag_size_bytes: number | null;
  quantum_resistant: boolean;
  hardware_accelerated: boolean;
  implemented: boolean;
  runtime_available: boolean;
  requires: string[];
  aliases: string[];
  replaced_by: string | null;
  description: string;
}

export interface Profile {
  level: ProfileLevel;
  name: string;
  description: string;
  slider_band: number[];
  symmetric_cipher: string;
  hash_algorithm: string;
  signature_algorithm: string;
  kem_algorithm: string;
  kdf_algorithm: string;
  kdf_memory_cost_kib: number;
  kdf_time_cost: number;
  kdf_parallelism: number;
  compression_algorithm: string;
  chunk_size_bytes: number;
  post_quantum_protected: boolean;
  metadata_encryption: boolean;
  audit_logging: boolean;
  forward_secrecy: boolean;
  multi_layer_encryption: boolean;
}

const catalogData = rawCatalog as unknown as {
  generated_by: string;
  families: string[];
  statuses: string[];
  algorithms: CatalogAlgorithm[];
  profiles: Profile[];
};

export const CATALOG: CatalogAlgorithm[] = catalogData.algorithms;
export const PROFILES: Profile[] = catalogData.profiles;
export const CATALOG_FAMILIES: string[] = catalogData.families;
export const CATALOG_STATUSES: string[] = catalogData.statuses;

export const DEFAULT_PROFILE: ProfileLevel = 'BALANCED';

export function getProfile(level: ProfileLevel | string): Profile {
  return PROFILES.find((profile) => profile.level === level) ?? PROFILES[2];
}

export const FAMILY_LABELS: Record<string, string> = {
  symmetric: 'Symmetric AEAD',
  hash: 'Hash',
  kdf: 'Key Derivation',
  kem: 'Key Encapsulation',
  signature: 'Signatures',
  pake: 'PAKE',
  sharing: 'Secret Sharing',
  rng: 'Randomness',
  quantum: 'Quantum / Experimental',
};

export const STATUS_STYLES: Record<string, string> = {
  production: 'badge-emerald',
  experimental: 'badge-purple',
  legacy: 'badge-cyan',
  forbidden: 'badge-rose',
};

export const FAMILY_COLORS: Record<string, string> = {
  symmetric: 'text-cyan-300',
  hash: 'text-emerald-300',
  kdf: 'text-sky-300',
  kem: 'text-purple-300',
  signature: 'text-fuchsia-300',
  pake: 'text-amber-300',
  sharing: 'text-orange-300',
  rng: 'text-teal-300',
  quantum: 'text-rose-300',
};

export function catalogStats(): {
  total: number;
  production: number;
  experimental: number;
  legacy: number;
  forbidden: number;
  runtimeMissing: number;
  families: number;
} {
  const count = (status: string) => CATALOG.filter((item) => item.status === status).length;
  return {
    total: CATALOG.length,
    production: count('production'),
    experimental: count('experimental'),
    legacy: count('legacy'),
    forbidden: count('forbidden'),
    runtimeMissing: CATALOG.filter((item) => item.implemented && item.requires.length > 0 && !item.runtime_available).length,
    families: new Set(CATALOG.map((item) => item.family)).size,
  };
}
