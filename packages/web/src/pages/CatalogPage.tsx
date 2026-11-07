import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Binary,
  Boxes,
  Cpu,
  Fingerprint,
  Layers,
  Search,
  ShieldCheck,
} from 'lucide-react';
import {
  CATALOG,
  CATALOG_FAMILIES,
  CATALOG_STATUSES,
  FAMILY_COLORS,
  FAMILY_LABELS,
  PROFILES,
  STATUS_STYLES,
  catalogStats,
  type CatalogAlgorithm,
} from '../lib/profiles';
import { Badge, Card, Modal, PageHeader, StatCard } from '../components/ui';
import { classNames } from '../lib/format';

function statusClass(status: string): string {
  return STATUS_STYLES[status] ?? 'badge-cyan';
}

function securityLabel(algorithm: CatalogAlgorithm): string {
  const parts: string[] = [];
  if (algorithm.classical_bits) parts.push(`${algorithm.classical_bits}-bit classical`);
  if (algorithm.pq_nist_level) parts.push(`NIST PQ ${algorithm.pq_nist_level}`);
  return parts.join(' · ') || '—';
}

function sizeLabel(algorithm: CatalogAlgorithm): string {
  const parts: string[] = [];
  if (algorithm.key_size_bytes) parts.push(`key ${algorithm.key_size_bytes}B`);
  if (algorithm.nonce_size_bytes) parts.push(`nonce ${algorithm.nonce_size_bytes}B`);
  if (algorithm.tag_size_bytes) parts.push(`tag ${algorithm.tag_size_bytes}B`);
  return parts.join(' · ') || '—';
}

export default function CatalogPage(): JSX.Element {
  const [search, setSearch] = useState('');
  const [family, setFamily] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [selected, setSelected] = useState<CatalogAlgorithm | null>(null);
  const stats = catalogStats();

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return CATALOG.filter((algorithm) => {
      if (family !== 'ALL' && algorithm.family !== family) return false;
      if (status !== 'ALL' && algorithm.status !== status) return false;
      if (!term) return true;
      return (
        algorithm.algorithm_id.includes(term) ||
        algorithm.family.includes(term) ||
        algorithm.description.toLowerCase().includes(term) ||
        algorithm.aliases.some((alias) => alias.includes(term))
      );
    });
  }, [family, search, status]);

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Crypto agility"
        title="Every algorithm, wire ID, and lifecycle gate"
        description="The catalog is the single source of truth for what the engine may use. Stable wire IDs are persisted in manifests so old data remains decryptable while new data can move to stronger primitives."
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Catalogued algorithms"
          value={stats.total}
          hint={`${stats.families} cryptographic families`}
          icon={<Boxes className="h-5 w-5" />}
        />
        <StatCard
          label="Production"
          value={stats.production}
          hint="Allowed by default"
          icon={<ShieldCheck className="h-5 w-5" />}
          accent="text-emerald-300"
        />
        <StatCard
          label="Experimental / legacy"
          value={stats.experimental + stats.legacy}
          hint="Gated behind policy flags"
          icon={<Layers className="h-5 w-5" />}
          accent="text-purple-300"
        />
        <StatCard
          label="Runtime missing deps"
          value={stats.runtimeMissing}
          hint="e.g. liboqs for PQ"
          icon={<Cpu className="h-5 w-5" />}
          accent="text-amber-300"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9"
            placeholder="Search by id, family, alias, or description"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <select className="input w-auto" value={family} onChange={(event) => setFamily(event.target.value)}>
          <option value="ALL">All families</option>
          {CATALOG_FAMILIES.map((name) => (
            <option key={name} value={name}>
              {FAMILY_LABELS[name] ?? name}
            </option>
          ))}
        </select>
        <select className="input w-auto" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="ALL">All statuses</option>
          {CATALOG_STATUSES.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 card overflow-hidden !p-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/8 px-4 py-2.5">
          <div className="text-[11px] text-slate-500">
            Showing <span className="font-semibold text-slate-300">{filtered.length}</span> of{' '}
            {CATALOG.length} algorithms
          </div>
          <div className="flex flex-wrap gap-1.5">
            {CATALOG_STATUSES.map((name) => (
              <span key={name} className={classNames('badge !text-[9px]', statusClass(name))}>
                {name}
              </span>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto scroll-thin">
          <table className="data-table w-full min-w-[920px] text-left">
            <thead>
              <tr className="border-b border-white/8 bg-white/[0.02]">
                <th className="px-4 py-3">Algorithm</th>
                <th className="px-4 py-3">Family</th>
                <th className="px-4 py-3">Wire ID</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Security</th>
                <th className="px-4 py-3">Sizes</th>
                <th className="px-4 py-3">Runtime</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((algorithm) => (
                <tr
                  key={algorithm.algorithm_id}
                  className="cursor-pointer border-b border-white/5 transition-colors last:border-0 hover:bg-white/[0.03]"
                  onClick={() => setSelected(algorithm)}
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="mono text-xs font-medium text-slate-100">
                        {algorithm.algorithm_id}
                      </span>
                      {algorithm.quantum_resistant ? (
                        <span className="rounded bg-purple-500/15 px-1 py-0.5 text-[8px] font-semibold uppercase tracking-wider text-purple-300">
                          PQ
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-0.5 max-w-[320px] truncate text-[10px] text-slate-500">
                      {algorithm.description}
                    </div>
                  </td>
                  <td className={classNames('px-4 py-2.5 text-xs', FAMILY_COLORS[algorithm.family])}>
                    {FAMILY_LABELS[algorithm.family] ?? algorithm.family}
                  </td>
                  <td className="mono px-4 py-2.5 text-[11px] text-slate-400">
                    {algorithm.wire_id_hex}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={classNames('badge !text-[9px]', statusClass(algorithm.status))}>
                      {algorithm.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-[11px] text-slate-400">
                    {securityLabel(algorithm)}
                  </td>
                  <td className="mono px-4 py-2.5 text-[10px] text-slate-500">
                    {sizeLabel(algorithm)}
                  </td>
                  <td className="px-4 py-2.5">
                    {!algorithm.implemented ? (
                      <span className="text-[11px] text-slate-500">Not implemented</span>
                    ) : algorithm.runtime_available ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-current" /> available
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] text-amber-300">
                        <AlertTriangle className="h-3 w-3" /> needs {algorithm.requires.join(', ')}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Card className="mt-4">
        <h2 className="text-base font-semibold text-white">Profile matrix</h2>
        <p className="mt-1 text-xs text-slate-400">
          Profiles bind a family-level policy to concrete algorithms. The six bands are stable and
          map to the adaptive slider.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {PROFILES.map((profile) => (
            <div
              key={profile.level}
              className="rounded-xl border border-white/8 bg-white/[0.02] p-3.5"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-semibold text-white">
                  {profile.level.replace('_', '-')}
                </div>
                <Badge className={profile.post_quantum_protected ? 'badge-purple' : 'badge-cyan'}>
                  {profile.slider_band[0]}–{profile.slider_band[1]}%
                </Badge>
              </div>
              <div className="mt-2 space-y-1 text-[10px] text-slate-400">
                <div className="mono truncate">AEAD {profile.symmetric_cipher}</div>
                <div className="mono truncate">HASH {profile.hash_algorithm}</div>
                <div className="mono truncate">KEM {profile.kem_algorithm}</div>
                <div className="mono truncate">
                  KDF {profile.kdf_algorithm} · {Math.round(profile.kdf_memory_cost_kib / 1024)} MiB
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {profile.forward_secrecy ? (
                  <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-emerald-300">
                    FS
                  </span>
                ) : null}
                {profile.multi_layer_encryption ? (
                  <span className="rounded bg-purple-500/10 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-purple-300">
                    dual-layer
                  </span>
                ) : null}
                {profile.metadata_encryption ? (
                  <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-cyan-300">
                    metadata
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {[
          {
            icon: Fingerprint,
            title: 'Stable wire IDs',
            body: 'Every algorithm has a 16-bit family-prefixed wire ID persisted with data. The catalog resolves IDs back to specs without guessing.',
          },
          {
            icon: Binary,
            title: 'Lifecycle gates',
            body: 'Production is default. Experimental requires an explicit flag, legacy requires opt-in, and forbidden entries can never be selected.',
          },
          {
            icon: ShieldCheck,
            title: 'Fail closed',
            body: 'Missing runtimes and family mismatches raise errors before encryption. No silent downgrade to a different primitive.',
          },
        ].map((item) => (
          <Card key={item.title}>
            <item.icon className="h-5 w-5 text-cyan-300" />
            <h3 className="mt-3 text-sm font-semibold text-white">{item.title}</h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{item.body}</p>
          </Card>
        ))}
      </div>

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected?.algorithm_id ?? ''}
        subtitle={selected ? FAMILY_LABELS[selected.family] ?? selected.family : undefined}
        wide
      >
        {selected ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <span className={classNames('badge', statusClass(selected.status))}>
                {selected.status}
              </span>
              <span className="badge badge-cyan">{selected.wire_id_hex}</span>
              {selected.quantum_resistant ? <span className="badge badge-purple">PQ</span> : null}
              {selected.hardware_accelerated ? (
                <span className="badge badge-emerald">Hardware accelerated</span>
              ) : null}
              {selected.implemented ? (
                selected.runtime_available ? (
                  <span className="badge badge-emerald">Runtime available</span>
                ) : (
                  <span className="badge badge-amber">Needs {selected.requires.join(', ')}</span>
                )
              ) : (
                <span className="badge badge-cyan">Not implemented</span>
              )}
            </div>

            <p className="text-sm leading-relaxed text-slate-300">{selected.description}</p>

            <div className="grid gap-2 sm:grid-cols-2">
              {[
                ['Family', FAMILY_LABELS[selected.family] ?? selected.family],
                ['Wire ID', `${selected.wire_id_hex} (${selected.wire_id})`],
                ['Classical security', selected.classical_bits ? `${selected.classical_bits} bits` : '—'],
                ['PQ NIST level', selected.pq_nist_level ? String(selected.pq_nist_level) : '—'],
                ['Key size', selected.key_size_bytes ? `${selected.key_size_bytes} bytes` : '—'],
                ['Nonce size', selected.nonce_size_bytes ? `${selected.nonce_size_bytes} bytes` : '—'],
                ['Tag size', selected.tag_size_bytes ? `${selected.tag_size_bytes} bytes` : '—'],
                ['Replaced by', selected.replaced_by ?? '—'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5"
                >
                  <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                    {label}
                  </div>
                  <div className="mono mt-1 text-xs text-slate-200">{value}</div>
                </div>
              ))}
            </div>

            {selected.aliases.length > 0 ? (
              <div>
                <div className="mb-1.5 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                  Aliases
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {selected.aliases.map((alias) => (
                    <span key={alias} className="mono-tag">
                      {alias}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            {selected.requires.length > 0 ? (
              <div
                className={classNames(
                  'rounded-xl border p-3 text-xs',
                  selected.runtime_available
                    ? 'border-emerald-400/20 bg-emerald-500/5 text-emerald-100'
                    : 'border-amber-400/20 bg-amber-500/5 text-amber-100',
                )}
              >
                <div className="mb-1 font-medium">Runtime requirements</div>
                <div className="mono text-[11px]">{selected.requires.join(', ')}</div>
                <div className="mt-1 text-[11px] opacity-80">
                  {selected.runtime_available
                    ? 'All requirements are importable in this environment.'
                    : 'The catalog will reject this algorithm until the dependency is installed.'}
                </div>
              </div>
            ) : null}

            {selected.status === 'forbidden' ? (
              <div className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/10 p-3 text-xs text-rose-100">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                Forbidden algorithms are catalogued for migration awareness only. The engine must
                reject them even if a manifest requests one.
              </div>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
