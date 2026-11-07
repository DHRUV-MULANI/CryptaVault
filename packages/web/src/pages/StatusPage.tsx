import { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Check,
  CircleAlert,
  Cpu,
  Database,
  Fingerprint,
  Gauge,
  HardDrive,
  KeyRound,
  LockKeyhole,
  Play,
  ShieldCheck,
  Wifi,
  X,
} from 'lucide-react';
import { useVault } from '../lib/vault';
import { CATALOG, catalogStats, getProfile } from '../lib/profiles';
import { useFiles, useShares } from '../lib/hooks';
import { recordAudit } from '../lib/audit';
import {
  generateRawKey,
  importAesKey,
  open,
  randomBytes,
  seal,
  sha256Hex,
} from '../lib/crypto';
import { Badge, Card, PageHeader, useToast } from '../components/ui';
import { classNames, formatBytes } from '../lib/format';

interface Check {
  label: string;
  detail: string;
  ok: boolean;
  icon: typeof Activity;
}

interface SelfTest {
  ok: boolean;
  elapsedMs: number;
  ciphertextBytes: number;
  hash: string;
}

export default function StatusPage(): JSX.Element {
  const { settings, meta, bumpRevision } = useVault();
  const { files } = useFiles();
  const { shares } = useShares();
  const { notify } = useToast();
  const [quota, setQuota] = useState<{ usage: number; quota: number } | null>(null);
  const [checks, setChecks] = useState<Check[]>([]);
  const [selfTest, setSelfTest] = useState<SelfTest | null>(null);
  const [testing, setTesting] = useState(false);
  const stats = catalogStats();
  const profile = getProfile(settings.defaultProfile);
  const commit = import.meta.env.VITE_COMMIT ?? 'dev';

  useEffect(() => {
    const result: Check[] = [
      {
        label: 'Web Crypto API',
        detail: 'crypto.subtle is required for AES-GCM, PBKDF2, SHA-256',
        ok: typeof globalThis.crypto?.subtle !== 'undefined',
        icon: KeyRound,
      },
      {
        label: 'Secure context',
        detail: 'Required for crypto.subtle; localhost and HTTPS qualify',
        ok: window.isSecureContext,
        icon: LockKeyhole,
      },
      {
        label: 'IndexedDB',
        detail: 'Persistent encrypted vault storage',
        ok: typeof indexedDB !== 'undefined',
        icon: Database,
      },
      {
        label: 'CompressionStream',
        detail: 'Optional gzip compression before encryption',
        ok:
          typeof CompressionStream !== 'undefined' &&
          typeof DecompressionStream !== 'undefined',
        icon: Gauge,
      },
      {
        label: 'BroadcastChannel',
        detail: 'Available for future multi-tab coordination',
        ok: typeof BroadcastChannel !== 'undefined',
        icon: Wifi,
      },
      {
        label: 'Clipboard API',
        detail: 'Used for copying share links and bundle JSON',
        ok: Boolean(navigator.clipboard),
        icon: Fingerprint,
      },
    ];
    setChecks(result);
    if (navigator.storage?.estimate) {
      void navigator.storage.estimate().then((estimate) => {
        setQuota({ usage: estimate.usage ?? 0, quota: estimate.quota ?? 0 });
      });
    }
  }, []);

  async function runSelfTest(): Promise<void> {
    setTesting(true);
    try {
      const start = performance.now();
      const payload = randomBytes(256 * 1024);
      const raw = generateRawKey();
      const key = await importAesKey(raw, false);
      const sealed = await seal(key, payload, 'diagnostics:self-test');
      const opened = await open(key, sealed, 'diagnostics:self-test');
      const ok =
        opened.length === payload.length &&
        opened.every((byte, index) => byte === payload[index]);
      const hash = await sha256Hex(opened);
      const elapsedMs = performance.now() - start;
      setSelfTest({
        ok,
        elapsedMs,
        ciphertextBytes: Math.ceil((sealed.ctB64.length * 3) / 4),
        hash,
      });
      await recordAudit('diagnostics.self_test', undefined, ok ? 'pass' : 'fail');
      bumpRevision();
      notify(ok ? 'Self-test passed.' : 'Self-test failed.', ok ? 'success' : 'error');
    } catch (err) {
      setSelfTest({ ok: false, elapsedMs: 0, ciphertextBytes: 0, hash: '' });
      notify(err instanceof Error ? err.message : 'Self-test failed.', 'error');
    } finally {
      setTesting(false);
    }
  }

  const missingRuntime = CATALOG.filter(
    (algorithm) => algorithm.implemented && algorithm.requires.length > 0 && !algorithm.runtime_available,
  );
  const totalBytes = files.reduce((sum, file) => sum + file.meta.size, 0);
  const passed = checks.filter((check) => check.ok).length;

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Diagnostics"
        title="Runtime, storage, and crypto self-test"
        description="Verify that this browser can actually perform the cryptographic operations the portal depends on, and inspect the deployment's local state without sending telemetry."
        action={
          <button className="btn-primary" onClick={() => void runSelfTest()} disabled={testing}>
            <Play className="h-4 w-4" />
            {testing ? 'Running…' : 'Run crypto self-test'}
          </button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: 'Environment checks',
            value: `${passed}/${checks.length}`,
            hint: passed === checks.length ? 'All checks passed' : 'Review failing checks',
            icon: ShieldCheck,
            tone: passed === checks.length ? 'text-emerald-300' : 'text-amber-300',
          },
          {
            label: 'Browser storage',
            value: quota ? formatBytes(quota.usage) : '—',
            hint: quota ? `of ${formatBytes(quota.quota)} quota` : 'estimate unavailable',
            icon: HardDrive,
            tone: 'text-cyan-300',
          },
          {
            label: 'Encrypted inventory',
            value: files.length,
            hint: `${formatBytes(totalBytes)} plaintext equivalent`,
            icon: Database,
            tone: 'text-purple-300',
          },
          {
            label: 'Share records',
            value: shares.length,
            hint: 'Local bookkeeping',
            icon: Fingerprint,
            tone: 'text-amber-300',
          },
        ].map((item) => (
          <Card key={item.label} className="!p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">
                  {item.label}
                </div>
                <div className="mt-2 text-2xl font-semibold text-white">{item.value}</div>
                <div className="mt-1 text-[11px] text-slate-500">{item.hint}</div>
              </div>
              <item.icon className={classNames('h-5 w-5', item.tone)} />
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <h2 className="text-base font-semibold text-white">Environment</h2>
          <p className="mt-0.5 text-xs text-slate-400">
            Capabilities detected in this browser session.
          </p>
          <div className="mt-4 space-y-2">
            {checks.map((check) => (
              <div
                key={check.label}
                className="flex items-start gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5"
              >
                <span
                  className={classNames(
                    'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg',
                    check.ok ? 'bg-emerald-500/10 text-emerald-300' : 'bg-rose-500/10 text-rose-300',
                  )}
                >
                  {check.ok ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-medium text-slate-200">{check.label}</div>
                  <div className="text-[10px] text-slate-500">{check.detail}</div>
                </div>
                <Badge className={check.ok ? 'badge-emerald' : 'badge-rose'}>
                  {check.ok ? 'pass' : 'fail'}
                </Badge>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <h2 className="text-base font-semibold text-white">Crypto self-test</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              Encrypts 256 KiB with a fresh AES-256-GCM key, decrypts it, and verifies every byte.
            </p>
            {selfTest ? (
              <div className="mt-4 space-y-2">
                <div
                  className={classNames(
                    'flex items-start gap-2 rounded-xl border px-3 py-2.5 text-xs',
                    selfTest.ok
                      ? 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100'
                      : 'border-rose-400/25 bg-rose-500/10 text-rose-100',
                  )}
                >
                  {selfTest.ok ? (
                    <Check className="mt-0.5 h-4 w-4 shrink-0" />
                  ) : (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  )}
                  {selfTest.ok
                    ? `Round-trip verified in ${selfTest.elapsedMs.toFixed(1)} ms.`
                    : 'Round-trip verification failed.'}
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2">
                    <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                      Ciphertext
                    </div>
                    <div className="mono mt-1 text-xs text-slate-200">
                      {formatBytes(selfTest.ciphertextBytes)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2">
                    <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                      SHA-256
                    </div>
                    <div className="mono mt-1 truncate text-xs text-slate-200">
                      {selfTest.hash ? `${selfTest.hash.slice(0, 20)}…` : '—'}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-white/10 px-4 py-8 text-center">
                <Cpu className="mx-auto mb-2 h-7 w-7 text-slate-600" />
                <p className="text-xs text-slate-500">No self-test has run in this session.</p>
              </div>
            )}
          </Card>

          <Card>
            <h2 className="text-base font-semibold text-white">Runtime and build</h2>
            <div className="mt-3 space-y-2 text-[11px]">
              {[
                ['Build commit', commit.slice(0, 12)],
                ['Base path', import.meta.env.BASE_URL],
                ['Active profile', profile.level.replace('_', '-')],
                ['KDF', `${profile.kdf_algorithm} · ${Math.round(profile.kdf_memory_cost_kib / 1024)} MiB`],
                ['Chunk size', formatBytes(profile.chunk_size_bytes)],
                ['Vault created', meta ? new Date(meta.createdAt).toLocaleString() : '—'],
                ['Online', navigator.onLine ? 'yes' : 'no'],
                ['Language', navigator.language],
                ['Platform', navigator.platform || 'unknown'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-center justify-between gap-2 rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2"
                >
                  <span className="text-slate-500">{label}</span>
                  <span className="mono truncate text-slate-200">{value}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <Card className="mt-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-white">Catalog runtime availability</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              {stats.total} algorithms · {stats.production} production · {stats.experimental}{' '}
              experimental · {stats.legacy} legacy · {stats.forbidden} forbidden
            </p>
          </div>
          <Badge className={missingRuntime.length ? 'badge-amber' : 'badge-emerald'}>
            {missingRuntime.length ? `${missingRuntime.length} need dependencies` : 'all runtimes ready'}
          </Badge>
        </div>
        {missingRuntime.length === 0 ? (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-500/5 px-3 py-2.5 text-xs text-emerald-100">
            <Check className="h-4 w-4" /> Every implemented catalog entry has its runtime
            dependency available.
          </div>
        ) : (
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {missingRuntime.slice(0, 12).map((algorithm) => (
              <div
                key={algorithm.algorithm_id}
                className="flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-500/5 px-3 py-2.5"
              >
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                <div className="min-w-0">
                  <div className="mono truncate text-[11px] text-amber-100">
                    {algorithm.algorithm_id}
                  </div>
                  <div className="text-[10px] text-amber-200/70">
                    requires {algorithm.requires.join(', ')}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="mt-4 rounded-xl border border-white/8 bg-white/[0.02] p-3 text-[11px] leading-relaxed text-slate-400">
          The browser portal does not use the Python catalog directly at runtime; it mirrors the
          same profiles and container ideas in WebCrypto. The catalog page and this diagnostic are
          generated from the Python catalog to keep the story consistent.
        </div>
      </Card>
    </div>
  );
}
