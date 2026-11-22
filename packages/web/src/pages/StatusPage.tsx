import { useEffect, useState } from 'react';
import { Check, CircleAlert, Cpu, Play, RefreshCw, X } from 'lucide-react';
import { api } from '../lib/api';
import { useVault } from '../lib/vault';
import { useFiles, useShares } from '../lib/hooks';
import { catalogStats, getProfile } from '../lib/profiles';
import { generateRawKey, importAesKey, open, randomBytes, seal, sha256Hex } from '../lib/crypto';
import { Badge, Card, PageHeader, useToast } from '../components/ui';
import { classNames, formatBytes } from '../lib/format';

interface CheckRow { label: string; detail: string; ok: boolean; }
interface SelfTest { ok: boolean; elapsedMs: number; ciphertextBytes: number; hash: string; }

export default function StatusPage(): JSX.Element {
  const { settings, user, vault } = useVault();
  const { files } = useFiles();
  const { shares } = useShares();
  const { notify } = useToast();
  const [checks, setChecks] = useState<CheckRow[]>([]);
  const [apiHealth, setApiHealth] = useState<Record<string, unknown> | null>(null);
  const [apiReady, setApiReady] = useState<Record<string, unknown> | null>(null);
  const [selfTest, setSelfTest] = useState<SelfTest | null>(null);
  const [testing, setTesting] = useState(false);
  const stats = catalogStats();
  const profile = getProfile(settings.defaultProfile);

  async function loadApi() {
    const [h, r] = await Promise.allSettled([api.system.health(), api.system.ready()]);
    setApiHealth(h.status === 'fulfilled' ? h.value : { status: 'error' });
    setApiReady(r.status === 'fulfilled' ? r.value : { status: 'error' });
  }

  useEffect(() => {
    setChecks([
      { label: 'Web Crypto API', detail: 'crypto.subtle required for AES-GCM/PBKDF2/SHA-256', ok: typeof globalThis.crypto?.subtle !== 'undefined' },
      { label: 'Secure context', detail: 'HTTPS or localhost required for WebCrypto', ok: window.isSecureContext },
      { label: 'IndexedDB', detail: 'Browser storage available (legacy/local features)', ok: typeof indexedDB !== 'undefined' },
      { label: 'CompressionStream', detail: 'Optional gzip compression before encryption', ok: typeof CompressionStream !== 'undefined' && typeof DecompressionStream !== 'undefined' },
      { label: 'Clipboard API', detail: 'Used for copying share links', ok: Boolean(navigator.clipboard) },
      { label: 'Network online', detail: 'Browser reports online state', ok: navigator.onLine },
    ]);
    void loadApi();
  }, []);

  async function runSelfTest() {
    setTesting(true);
    try {
      const start = performance.now();
      const payload = randomBytes(256 * 1024);
      const raw = generateRawKey();
      const aes = await importAesKey(raw, false);
      const sealed = await seal(aes, payload, 'diagnostics:self-test');
      const opened = await open(aes, sealed, 'diagnostics:self-test');
      const ok = opened.length === payload.length && opened.every((b, i) => b === payload[i]);
      const hash = await sha256Hex(opened);
      setSelfTest({ ok, elapsedMs: performance.now() - start, ciphertextBytes: Math.ceil((sealed.ctB64.length * 3) / 4), hash });
      notify(ok ? 'Self-test passed.' : 'Self-test failed.', ok ? 'success' : 'error');
    } catch (err) {
      setSelfTest({ ok: false, elapsedMs: 0, ciphertextBytes: 0, hash: '' });
      notify(err instanceof Error ? err.message : 'Self-test failed.', 'error');
    } finally { setTesting(false); }
  }

  const passed = checks.filter((c) => c.ok).length;
  const totalBytes = files.reduce((s, f) => s + (f.meta.size || 0), 0);

  return (
    <div className="animate-in">
      <PageHeader eyebrow="Diagnostics" title="Runtime and API diagnostics" description="Checks browser crypto capabilities, API reachability, and runs a local AES-GCM self-test. No plaintext is sent to the server." action={<><button className="btn-secondary" onClick={() => void loadApi()}><RefreshCw className="h-4 w-4" /> Refresh API</button><button className="btn-primary" onClick={() => void runSelfTest()} disabled={testing}><Play className="h-4 w-4" /> {testing ? 'Running…' : 'Run self-test'}</button></>} />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Environment checks</div><div className="mt-2 text-2xl font-semibold text-white">{passed}/{checks.length}</div><div className="mt-1 text-[11px] text-slate-500">{passed === checks.length ? 'All passed' : 'Review failures'}</div></Card>
        <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">API health</div><div className="mt-2 text-2xl font-semibold text-white">{String(apiHealth?.status ?? '—')}</div><div className="mt-1 text-[11px] text-slate-500">/health</div></Card>
        <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Encrypted files</div><div className="mt-2 text-2xl font-semibold text-white">{files.length}</div><div className="mt-1 text-[11px] text-slate-500">{formatBytes(totalBytes)} plaintext equivalent</div></Card>
        <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Shares</div><div className="mt-2 text-2xl font-semibold text-white">{shares.length}</div><div className="mt-1 text-[11px] text-slate-500">Owned by user</div></Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <h2 className="text-base font-semibold text-white">Browser environment</h2>
          <div className="mt-4 space-y-2">
            {checks.map((c) => (
              <div key={c.label} className="flex items-start gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5">
                <span className={classNames('mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg', c.ok ? 'bg-emerald-500/10 text-emerald-300' : 'bg-rose-500/10 text-rose-300')}>{c.ok ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}</span>
                <div className="min-w-0 flex-1"><div className="text-xs font-medium text-slate-200">{c.label}</div><div className="text-[10px] text-slate-500">{c.detail}</div></div>
                <Badge className={c.ok ? 'badge-emerald' : 'badge-rose'}>{c.ok ? 'pass' : 'fail'}</Badge>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <h2 className="text-base font-semibold text-white">API status</h2>
            <div className="mt-3 space-y-2 text-[11px]">
              {[['/health', JSON.stringify(apiHealth ?? {})], ['/ready', JSON.stringify(apiReady ?? {})], ['User', user?.email ?? '—'], ['Workspace role', 'see Workspaces']].map(([label, value]) => (
                <div key={label} className="rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2"><div className="text-slate-500">{label}</div><div className="mono mt-1 break-all text-slate-200">{value}</div></div>
              ))}
            </div>
          </Card>

          <Card>
            <h2 className="text-base font-semibold text-white">Crypto self-test</h2>
            <p className="mt-0.5 text-xs text-slate-400">Encrypts 256 KiB with fresh AES-256-GCM key, decrypts, verifies every byte.</p>
            {selfTest ? (
              <div className="mt-4 space-y-2">
                <div className={classNames('flex items-start gap-2 rounded-xl border px-3 py-2.5 text-xs', selfTest.ok ? 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100' : 'border-rose-400/25 bg-rose-500/10 text-rose-100')}>{selfTest.ok ? <Check className="mt-0.5 h-4 w-4 shrink-0" /> : <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />}{selfTest.ok ? `Round-trip verified in ${selfTest.elapsedMs.toFixed(1)} ms.` : 'Round-trip verification failed.'}</div>
                <div className="grid gap-2 sm:grid-cols-2"><div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2"><div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Ciphertext</div><div className="mono mt-1 text-xs text-slate-200">{formatBytes(selfTest.ciphertextBytes)}</div></div><div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2"><div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">SHA-256</div><div className="mono mt-1 truncate text-xs text-slate-200">{selfTest.hash.slice(0, 20)}…</div></div></div>
              </div>
            ) : <div className="mt-4 rounded-xl border border-dashed border-white/10 px-4 py-8 text-center"><Cpu className="mx-auto mb-2 h-7 w-7 text-slate-600" /><p className="text-xs text-slate-500">No self-test run in this session.</p></div>}
          </Card>
        </div>
      </div>

      <Card className="mt-4">
        <h2 className="text-base font-semibold text-white">Runtime / build</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-[11px]">
          {[['Build commit', (import.meta.env.VITE_COMMIT ?? 'dev').slice(0, 12)], ['Active profile', profile.level.replace('_', '-')], ['KDF', `${profile.kdf_algorithm} · ${Math.round(profile.kdf_memory_cost_kib / 1024)} MiB`], ['Chunk size', formatBytes(profile.chunk_size_bytes)], ['Vault iterations', vault?.kdf_iterations?.toLocaleString() ?? '—'], ['Catalog', `${stats.total} algorithms`]].map(([label, value]) => (
            <div key={label} className="flex items-center justify-between gap-2 rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2"><span className="text-slate-500">{label}</span><span className="mono truncate text-slate-200">{value}</span></div>
          ))}
        </div>
      </Card>
    </div>
  );
}
