import { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Boxes,
  Cloud,
  Database,
  Download,
  Gauge,
  HardDrive,
  KeyRound,
  LockKeyhole,
  Server,
  ShieldCheck,
  Terminal,
  Trash2,
} from 'lucide-react';
import { useVault } from '../lib/vault';
import { useAuditEvents, useFiles, useShares } from '../lib/hooks';
import { catalogStats, PROFILES } from '../lib/profiles';
import {
  Badge,
  Card,
  Modal,
  PageHeader,
  StatCard,
  Toggle,
  useToast,
} from '../components/ui';
import { formatBytes, formatDate, downloadText, relativeTime } from '../lib/format';
import { dbGetAll } from '../lib/db';
import type { MessageRecord } from '../lib/types';

export default function AdminPage(): JSX.Element {
  const { settings, meta, updateSettings, wipe } = useVault();
  const { files } = useFiles();
  const { shares } = useShares();
  const { events } = useAuditEvents(200);
  const { notify } = useToast();
  const [messageCount, setMessageCount] = useState(0);
  const [quota, setQuota] = useState<{ usage: number; quota: number } | null>(null);
  const [wipeOpen, setWipeOpen] = useState(false);
  const stats = catalogStats();

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const messages = await dbGetAll<MessageRecord>('messages');
      if (!cancelled) setMessageCount(messages.length);
      if (navigator.storage?.estimate) {
        const estimate = await navigator.storage.estimate();
        if (!cancelled) {
          setQuota({ usage: estimate.usage ?? 0, quota: estimate.quota ?? 0 });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const totalBytes = files.reduce((sum, file) => sum + file.meta.size, 0);
  const activeShares = shares.filter(
    (share) => !share.revoked && new Date(share.expiresAt).getTime() > Date.now(),
  ).length;

  function exportAudit(): void {
    const header = 'timestamp,action,target_id,detail\n';
    const rows = events
      .map((event) =>
        [
          event.at,
          event.action,
          event.targetId ?? '',
          (event.detail ?? '').replace(/,/g, ';'),
        ].join(','),
      )
      .join('\n');
    downloadText(header + rows, `cryptavault-audit-${Date.now()}.csv`, 'text/csv');
    notify('Audit log exported.', 'success');
  }

  const connectors = [
    {
      name: 'Browser IndexedDB',
      detail: 'Encrypted vault, manifests, messages, shares, audit',
      state: 'active',
      icon: Database,
    },
    {
      name: 'Local filesystem',
      detail: 'Available through the Python CLI and core engine',
      state: 'available',
      icon: HardDrive,
    },
    {
      name: 'Supabase / Postgres',
      detail: 'Configured by API environment variables; not used by static portal',
      state: 'config-required',
      icon: Server,
    },
    {
      name: 'Cloud / SFTP connectors',
      detail: 'Google Drive, OneDrive, Dropbox, R2, SFTP adapters in core',
      state: 'config-required',
      icon: Cloud,
    },
  ];

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Admin console"
        title="Local deployment control plane"
        description="Operational view of this browser vault: policy flags, encrypted inventory, connector state, catalog health, and the local audit log. Production governance lives in the authenticated API admin routes."
        action={
          <>
            <button className="btn-secondary" onClick={exportAudit} disabled={events.length === 0}>
              <Download className="h-4 w-4" /> Export audit CSV
            </button>
            <button className="btn-danger" onClick={() => setWipeOpen(true)}>
              <Trash2 className="h-4 w-4" /> Wipe vault
            </button>
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge className="badge-purple">Local admin demo</Badge>
        <Badge className="badge-emerald">Zero-knowledge</Badge>
        <Badge className="badge-cyan">Static deployment</Badge>
        <span className="text-[11px] text-slate-500">
          No central tenant data is available to this page by design.
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Encrypted inventory"
          value={files.length}
          hint={`${formatBytes(totalBytes)} plaintext equivalent`}
          icon={<Boxes className="h-5 w-5" />}
        />
        <StatCard
          label="Audit events"
          value={events.length}
          hint="Append-only local log"
          icon={<Activity className="h-5 w-5" />}
          accent="text-emerald-300"
        />
        <StatCard
          label="Active shares"
          value={activeShares}
          hint={`${shares.length} share records`}
          icon={<KeyRound className="h-5 w-5" />}
          accent="text-purple-300"
        />
        <StatCard
          label="Browser storage"
          value={quota ? formatBytes(quota.usage) : '—'}
          hint={quota ? `of ${formatBytes(quota.quota)} quota` : 'estimate unavailable'}
          icon={<Gauge className="h-5 w-5" />}
          accent="text-amber-300"
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Feature flags</h2>
              <p className="mt-0.5 text-xs text-slate-400">
                Persisted in the vault metadata. These are local policy controls.
              </p>
            </div>
            <LockKeyhole className="h-5 w-5 text-cyan-300" />
          </div>
          <div className="space-y-2">
            <Toggle
              label="Enable secure sharing"
              description="When off, the vault hides share actions."
              checked={settings.sharingEnabled}
              onChange={(next) => void updateSettings({ sharingEnabled: next })}
            />
            <Toggle
              label="Enable encrypted messages"
              description="When off, the messages workspace is disabled."
              checked={settings.messagingEnabled}
              onChange={(next) => void updateSettings({ messagingEnabled: next })}
            />
            <Toggle
              label="Allow experimental algorithms"
              description="Policy intent for non-production catalog entries. The static portal never selects them automatically."
              checked={settings.allowExperimental}
              onChange={(next) => void updateSettings({ allowExperimental: next })}
            />
          </div>
          <div className="mt-3 rounded-xl border border-white/8 bg-white/[0.02] p-3">
            <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
              Default profile
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="mono text-xs text-cyan-300">{settings.defaultProfile}</span>
              <span className="text-[11px] text-slate-500">
                {PROFILES.find((profile) => profile.level === settings.defaultProfile)?.name}
              </span>
            </div>
          </div>
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Connector matrix</h2>
              <p className="mt-0.5 text-xs text-slate-400">
                The static portal only uses browser storage.
              </p>
            </div>
            <Server className="h-5 w-5 text-cyan-300" />
          </div>
          <div className="space-y-2">
            {connectors.map((connector) => (
              <div
                key={connector.name}
                className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 text-slate-300">
                  <connector.icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-medium text-slate-200">{connector.name}</div>
                  <div className="text-[10px] text-slate-500">{connector.detail}</div>
                </div>
                <Badge
                  className={
                    connector.state === 'active'
                      ? 'badge-emerald'
                      : connector.state === 'available'
                        ? 'badge-cyan'
                        : 'badge-amber'
                  }
                >
                  {connector.state}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1.1fr]">
        <Card>
          <h2 className="text-base font-semibold text-white">Catalog health</h2>
          <p className="mt-0.5 text-xs text-slate-400">
            Lifecycle distribution across {stats.total} algorithms.
          </p>
          <div className="mt-4 space-y-3">
            {[
              ['Production', stats.production, 'bg-emerald-400'],
              ['Experimental', stats.experimental, 'bg-purple-400'],
              ['Legacy', stats.legacy, 'bg-cyan-400'],
              ['Forbidden', stats.forbidden, 'bg-rose-400'],
            ].map(([label, value, color]) => (
              <div key={String(label)}>
                <div className="mb-1 flex items-center justify-between text-[11px]">
                  <span className="text-slate-300">{label}</span>
                  <span className="text-slate-500">
                    {value} · {Math.round((Number(value) / stats.total) * 100)}%
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
                  <div
                    className={`h-full rounded-full ${color}`}
                    style={{ width: `${Math.max(2, (Number(value) / stats.total) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-500/5 p-3 text-[11px] text-amber-100/80">
            <div className="flex items-center gap-1.5 font-medium">
              <AlertTriangle className="h-3.5 w-3.5" /> {stats.runtimeMissing} entries need missing
              runtime dependencies
            </div>
            <p className="mt-1 leading-relaxed opacity-80">
              These are rejected by the catalog until the dependency is importable. The portal
              reports this rather than silently falling back.
            </p>
          </div>
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Local audit log</h2>
              <p className="mt-0.5 text-xs text-slate-400">
                No plaintext file names or message contents are recorded.
              </p>
            </div>
            <Activity className="h-5 w-5 text-cyan-300" />
          </div>
          {events.length === 0 ? (
            <p className="py-8 text-center text-xs text-slate-500">No audit events yet.</p>
          ) : (
            <div className="max-h-[330px] overflow-y-auto scroll-thin">
              <table className="data-table w-full text-left">
                <thead className="sticky top-0 bg-[#0b111d]">
                  <tr className="border-b border-white/8">
                    <th className="py-2 pr-3">Event</th>
                    <th className="py-2 pr-3">Target</th>
                    <th className="py-2">When</th>
                  </tr>
                </thead>
                <tbody>
                  {events.slice(0, 50).map((event) => (
                    <tr key={event.id} className="border-b border-white/5 last:border-0">
                      <td className="py-2 pr-3 text-xs text-slate-200">{event.action}</td>
                      <td className="mono py-2 pr-3 text-[10px] text-slate-500">
                        {event.targetId ? `${event.targetId.slice(0, 10)}…` : '—'}
                      </td>
                      <td className="whitespace-nowrap py-2 text-[10px] text-slate-500">
                        {relativeTime(event.at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Card>
          <KeyRound className="h-5 w-5 text-cyan-300" />
          <h3 className="mt-3 text-sm font-semibold text-white">Key hierarchy</h3>
          <pre className="code-block mt-2 !text-[10px]">{`passphrase
 └ PBKDF2-SHA256 × 210k
    └ master key (non-extractable)
       ├ wrap file keys
       ├ wrap message keys
       └ seal manifests`}</pre>
        </Card>
        <Card>
          <ShieldCheck className="h-5 w-5 text-cyan-300" />
          <h3 className="mt-3 text-sm font-semibold text-white">Vault identity</h3>
          <div className="mt-2 space-y-1.5 text-[11px]">
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Created</span>
              <span className="text-slate-300">
                {meta ? formatDate(meta.createdAt) : '—'}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">KDF rounds</span>
              <span className="text-slate-300">{meta?.iterations.toLocaleString() ?? '—'}</span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Auto-lock</span>
              <span className="text-slate-300">{settings.autoLockMinutes} min</span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Messages</span>
              <span className="text-slate-300">{messageCount}</span>
            </div>
          </div>
        </Card>
        <Card>
          <Terminal className="h-5 w-5 text-cyan-300" />
          <h3 className="mt-3 text-sm font-semibold text-white">Production admin</h3>
          <p className="mt-1.5 text-[11px] leading-relaxed text-slate-400">
            The FastAPI backend exposes authenticated routes for users, feature flags, quotas,
            impersonation, health, and audit. This static console cannot read central tenant data,
            by design.
          </p>
          <div className="mono mt-2 text-[10px] text-cyan-300">
            /api/admin/users · /api/admin/flags · /api/admin/health
          </div>
        </Card>
      </div>

      <Modal
        open={wipeOpen}
        onClose={() => setWipeOpen(false)}
        title="Wipe this local vault?"
        subtitle="Every encrypted file, message, thread, share record, and audit event is deleted from this browser."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setWipeOpen(false)}>
              Cancel
            </button>
            <button className="btn-danger" onClick={() => void wipe()}>
              <Trash2 className="h-4 w-4" /> Wipe everything
            </button>
          </>
        }
      >
        <p className="text-sm leading-relaxed text-slate-300">
          This cannot be undone. Export an encrypted backup from Settings first if you want to keep
          the ciphertext.
        </p>
      </Modal>
    </div>
  );
}
