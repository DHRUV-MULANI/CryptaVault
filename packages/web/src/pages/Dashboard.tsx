import { useEffect, useMemo, useState } from 'react';
import { Link } from 'wouter';
import {
  Activity,
  ArrowRight,
  Boxes,
  Clock,
  FolderLock,
  KeyRound,
  Layers,
  Lock,
  MessageSquareLock,
  Share2,
  ShieldCheck,
  Sparkles,
  Upload,
} from 'lucide-react';
import { useVault } from '../lib/vault';
import { useAuditEvents, useFiles, useShares } from '../lib/hooks';
import { getProfile } from '../lib/profiles';
import { dbGetAll } from '../lib/db';
import type { MessageRecord, ThreadRecord } from '../lib/types';
import { formatBytes, relativeTime } from '../lib/format';
import { Badge, Card, PageHeader, StatCard } from '../components/ui';
import FileIcon from '../components/FileIcon';

export default function Dashboard(): JSX.Element {
  const { settings, meta, revision } = useVault();
  const { files } = useFiles();
  const { shares } = useShares();
  const { events } = useAuditEvents(6);
  const [messageCount, setMessageCount] = useState(0);
  const [threadCount, setThreadCount] = useState(0);
  const profile = getProfile(settings.defaultProfile);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [messages, threads] = await Promise.all([
        dbGetAll<MessageRecord>('messages'),
        dbGetAll<ThreadRecord>('threads'),
      ]);
      if (!cancelled) {
        setMessageCount(messages.length);
        setThreadCount(threads.length);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [revision]);

  const totalBytes = useMemo(
    () => files.reduce((sum, file) => sum + file.meta.size, 0),
    [files],
  );
  const activeShares = shares.filter(
    (share) => !share.revoked && new Date(share.expiresAt).getTime() > Date.now(),
  ).length;

  const categories = useMemo(() => {
    const buckets: Record<string, number> = {};
    for (const file of files) {
      const type = file.meta.type.split('/')[0] || 'other';
      buckets[type] = (buckets[type] ?? 0) + file.meta.size;
    }
    return Object.entries(buckets).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [files]);

  const maxCategory = Math.max(1, ...categories.map(([, bytes]) => bytes));

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Overview"
        title={`Welcome back, ${settings.displayName || 'operator'}`}
        description="Your zero-knowledge vault at a glance. Everything below is decrypted locally in this tab; the stored records remain ciphertext."
        action={
          <>
            <Link href="/vault" className="btn-primary">
              <Upload className="h-4 w-4" /> Encrypt a file
            </Link>
            <Link href="/shares" className="btn-secondary">
              <Share2 className="h-4 w-4" /> Create share
            </Link>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Encrypted files"
          value={files.length}
          hint={`${formatBytes(totalBytes)} plaintext protected`}
          icon={<FolderLock className="h-5 w-5" />}
        />
        <StatCard
          label="Active shares"
          value={activeShares}
          hint={`${shares.length} total share records`}
          icon={<Share2 className="h-5 w-5" />}
          accent="text-purple-300"
        />
        <StatCard
          label="Encrypted messages"
          value={messageCount}
          hint={`${threadCount} conversation${threadCount === 1 ? '' : 's'}`}
          icon={<MessageSquareLock className="h-5 w-5" />}
          accent="text-emerald-300"
        />
        <StatCard
          label="Audit events"
          value={events.length ? 'Tracked' : '0'}
          hint="Local append-only activity log"
          icon={<Activity className="h-5 w-5" />}
          accent="text-amber-300"
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <div className="space-y-4">
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Active security profile</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  Slider band {profile.slider_band[0]}–{profile.slider_band[1]}% · {profile.name}
                </p>
              </div>
              <Badge
                className={
                  profile.post_quantum_protected ? 'badge-purple' : 'badge-cyan'
                }
              >
                {profile.post_quantum_protected ? 'Post-quantum' : 'Classical'}
              </Badge>
            </div>
            <div className="mb-4 h-2 overflow-hidden rounded-full bg-white/8">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500"
                style={{ width: `${profile.slider_band[1]}%` }}
              />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                ['Symmetric AEAD', profile.symmetric_cipher],
                ['Hash', profile.hash_algorithm],
                ['Signature', profile.signature_algorithm],
                ['KEM', profile.kem_algorithm],
                [
                  'KDF',
                  `${profile.kdf_algorithm} · ${Math.round(
                    profile.kdf_memory_cost_kib / 1024,
                  )} MiB · t=${profile.kdf_time_cost}`,
                ],
                ['Chunk size', formatBytes(profile.chunk_size_bytes)],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5"
                >
                  <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                    {label}
                  </div>
                  <div className="mono mt-1 truncate text-xs text-slate-200">{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {profile.metadata_encryption ? (
                <Badge className="badge-emerald">Metadata encrypted</Badge>
              ) : (
                <Badge className="badge-cyan">Metadata plaintext</Badge>
              )}
              {profile.forward_secrecy ? <Badge className="badge-emerald">Forward secrecy</Badge> : null}
              {profile.multi_layer_encryption ? (
                <Badge className="badge-purple">Dual-layer AEAD</Badge>
              ) : null}
              <Link
                href="/catalog"
                className="inline-flex items-center gap-1 text-[11px] text-cyan-300 hover:underline"
              >
                Browse catalog <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </Card>

          <Card>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold text-white">Recent encrypted files</h2>
              <Link href="/vault" className="text-xs text-cyan-300 hover:underline">
                Open vault
              </Link>
            </div>
            {files.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 px-4 py-10 text-center">
                <FolderLock className="mx-auto mb-3 h-8 w-8 text-slate-600" />
                <p className="text-sm text-slate-400">
                  No files yet. Encrypt your first file to populate the vault.
                </p>
                <Link href="/vault" className="btn-primary mt-4 inline-flex">
                  <Upload className="h-4 w-4" /> Encrypt a file
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {files.slice(0, 5).map(({ record, meta: fileMeta }) => (
                  <div
                    key={record.id}
                    className="flex items-center gap-3 rounded-xl border border-white/6 bg-white/[0.02] px-3 py-2.5"
                  >
                    <FileIcon name={fileMeta.name} type={fileMeta.type} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-slate-100">
                        {fileMeta.name}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {formatBytes(fileMeta.size)} · {fileMeta.profile.replace('_', '-')} ·{' '}
                        {relativeTime(fileMeta.createdAt)}
                      </div>
                    </div>
                    <span className="mono hidden text-[10px] text-slate-600 sm:block">
                      {fileMeta.hash.slice(0, 10)}…
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <h2 className="mb-1 text-base font-semibold text-white">Quick actions</h2>
            <p className="mb-4 text-xs text-slate-400">
              Common workspace workflows, all performed client-side.
            </p>
            <div className="space-y-2">
              {[
                { href: '/vault', icon: Upload, title: 'Encrypt & upload', detail: 'Chunked AES-256-GCM' },
                { href: '/shares', icon: Share2, title: 'Create capability link', detail: 'Optional passphrase' },
                { href: '/messages', icon: MessageSquareLock, title: 'Write encrypted message', detail: 'Per-message keys' },
                { href: '/settings', icon: KeyRound, title: 'Backup & rotate keys', detail: 'Change passphrase' },
              ].map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="flex items-center gap-3 rounded-xl border border-white/6 bg-white/[0.02] px-3 py-2.5 transition-colors hover:border-cyan-400/25 hover:bg-cyan-500/5"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 text-cyan-300">
                    <action.icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-slate-100">{action.title}</span>
                    <span className="block text-[11px] text-slate-500">{action.detail}</span>
                  </span>
                  <ArrowRight className="h-4 w-4 text-slate-600" />
                </Link>
              ))}
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-base font-semibold text-white">Encrypted storage mix</h2>
            {categories.length === 0 ? (
              <p className="text-xs text-slate-500">No encrypted payloads yet.</p>
            ) : (
              <div className="space-y-3">
                {categories.map(([category, bytes]) => (
                  <div key={category}>
                    <div className="mb-1 flex items-center justify-between text-[11px]">
                      <span className="capitalize text-slate-300">{category}</span>
                      <span className="text-slate-500">{formatBytes(bytes)}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-blue-500"
                        style={{ width: `${Math.max(4, (bytes / maxCategory) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 text-base font-semibold text-white">Recent activity</h2>
            {events.length === 0 ? (
              <p className="text-xs text-slate-500">No audit events recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {events.map((event) => (
                  <div key={event.id} className="flex items-start gap-2.5">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-slate-200">{event.action}</div>
                      <div className="text-[10px] text-slate-500">
                        {relativeTime(event.at)}
                        {event.detail ? ` · ${event.detail}` : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {[
          {
            icon: Lock,
            title: 'Zero-knowledge boundary',
            body: 'Plaintext and private keys never leave this tab. IndexedDB holds only AES-GCM ciphertext and wrapped keys.',
          },
          {
            icon: Layers,
            title: 'Crypto agility',
            body: '88 catalogued algorithms with stable wire IDs, lifecycle status, and runtime availability checks.',
          },
          {
            icon: Sparkles,
            title: 'Adaptive profiles',
            body: 'Six profiles span performance-first classical crypto through post-quantum, forward-secret maximum mode.',
          },
        ].map((item) => (
          <div key={item.title} className="card p-4">
            <item.icon className="h-5 w-5 text-cyan-300" />
            <h3 className="mt-3 text-sm font-semibold text-white">{item.title}</h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{item.body}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-white/8 bg-white/[0.02] px-4 py-3 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" /> Vault created{' '}
          {meta ? new Date(meta.createdAt).toLocaleString() : '—'}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5" /> Auto-lock after {settings.autoLockMinutes} minutes
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Boxes className="h-3.5 w-3.5" /> Default{' '}
          {settings.defaultProfile.replace('_', '-')}
        </span>
      </div>
    </div>
  );
}
