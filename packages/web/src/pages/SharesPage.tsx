import { useRef, useState } from 'react';
import { Link } from 'wouter';
import {
  AlertTriangle,
  Clock,
  Download,
  FileUp,
  Link2,
  LockKeyhole,
  Share2,
  ShieldOff,
  Trash2,
} from 'lucide-react';
import { useFiles, useShares } from '../lib/hooks';
import { dbDelete, dbPut } from '../lib/db';
import { recordAudit } from '../lib/audit';
import { useVault } from '../lib/vault';
import {
  Badge,
  Card,
  EmptyState,
  Modal,
  PageHeader,
  useToast,
} from '../components/ui';
import { classNames, formatBytes, formatDate, relativeTime } from '../lib/format';
import type { ShareRecord } from '../lib/types';

export default function SharesPage(): JSX.Element {
  const { bumpRevision } = useVault();
  const { shares, loading } = useShares();
  const { files } = useFiles();
  const { notify } = useToast();
  const [revokeTarget, setRevokeTarget] = useState<ShareRecord | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ShareRecord | null>(null);
  const bundleInput = useRef<HTMLInputElement>(null);

  const fileNames = new Map(files.map((file) => [file.record.id, file.meta.name]));

  async function revoke(share: ShareRecord): Promise<void> {
    await dbPut<ShareRecord>('shares', { ...share, revoked: true });
    await recordAudit('share.revoked', share.id);
    bumpRevision();
    notify('Share record marked revoked. Existing copied links cannot be remotely invalidated.', 'info');
    setRevokeTarget(null);
  }

  async function remove(share: ShareRecord): Promise<void> {
    await dbDelete('shares', share.id);
    await recordAudit('share.deleted', share.id);
    bumpRevision();
    notify('Share record deleted.', 'success');
    setDeleteTarget(null);
  }

  async function importBundle(file: File): Promise<void> {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as { kind?: string };
      if (parsed.kind !== 'cryptavault-share-bundle') {
        throw new Error('Not a CryptaVault bundle.');
      }
      sessionStorage.setItem('cryptavault_open_bundle', text);
      window.location.hash = '#/share?bundle=1';
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Could not read bundle.', 'error');
    }
  }

  const active = shares.filter(
    (share) => !share.revoked && new Date(share.expiresAt).getTime() > Date.now(),
  ).length;

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Secure shares"
        title="Capability links and encrypted bundles"
        description="Share an encrypted copy without giving anyone access to your vault. Links and bundles are decrypted in the recipient's browser; the portal never sees a key."
        action={
          <>
            <input
              ref={bundleInput}
              type="file"
              accept=".json,.cvshare,application/json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void importBundle(file);
                event.target.value = '';
              }}
            />
            <button className="btn-secondary" onClick={() => bundleInput.current?.click()}>
              <FileUp className="h-4 w-4" /> Open a bundle
            </button>
            <Link href="/vault" className="btn-primary">
              <Share2 className="h-4 w-4" /> Share a file
            </Link>
          </>
        }
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        {[
          { label: 'Active records', value: active, hint: 'Not revoked or expired' },
          { label: 'Total records', value: shares.length, hint: 'Local bookkeeping only' },
          {
            label: 'Passphrase protected',
            value: shares.filter((share) => share.hasPassphrase).length,
            hint: 'Require a second secret',
          },
        ].map((item) => (
          <Card key={item.label} className="!p-4">
            <div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{item.label}</div>
            <div className="mt-1.5 text-2xl font-semibold text-white">{item.value}</div>
            <div className="mt-1 text-[11px] text-slate-500">{item.hint}</div>
          </Card>
        ))}
      </div>

      {loading ? (
        <div className="card py-12 text-center text-sm text-slate-400">Loading share records…</div>
      ) : shares.length === 0 ? (
        <EmptyState
          icon={<Share2 className="h-8 w-8" />}
          title="No shares yet"
          description="Create a share from the vault. For small files you can copy a self-contained link; for larger files download an encrypted bundle."
          action={
            <Link href="/vault" className="btn-primary">
              <Share2 className="h-4 w-4" /> Go to vault
            </Link>
          }
        />
      ) : (
        <div className="card overflow-hidden !p-0">
          <div className="overflow-x-auto scroll-thin">
            <table className="data-table w-full text-left">
              <thead>
                <tr className="border-b border-white/8 bg-white/[0.02]">
                  <th className="px-4 py-3">Share</th>
                  <th className="px-4 py-3">File</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Expires</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {shares.map((share) => {
                  const expired = new Date(share.expiresAt).getTime() <= Date.now();
                  const status = share.revoked ? 'Revoked' : expired ? 'Expired' : 'Active';
                  const name = fileNames.get(share.fileId);
                  return (
                    <tr key={share.id} className="border-b border-white/5 last:border-0">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <span
                            className={classNames(
                              'flex h-8 w-8 items-center justify-center rounded-lg',
                              share.hasPassphrase
                                ? 'bg-purple-500/10 text-purple-300'
                                : 'bg-cyan-500/10 text-cyan-300',
                            )}
                          >
                            {share.hasPassphrase ? (
                              <LockKeyhole className="h-4 w-4" />
                            ) : (
                              <Link2 className="h-4 w-4" />
                            )}
                          </span>
                          <div>
                            <div className="text-xs font-medium text-slate-200">
                              {share.label}
                            </div>
                            <div className="mono text-[10px] text-slate-500">
                              {share.id.slice(0, 12)}…
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="max-w-[200px] truncate text-slate-300">
                          {name ?? 'Encrypted file (removed)'}
                        </div>
                        <div className="text-[10px] text-slate-500">{formatBytes(share.bytes)}</div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge className={share.hasPassphrase ? 'badge-purple' : 'badge-cyan'}>
                          {share.mode}
                        </Badge>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-400">
                        {relativeTime(share.createdAt)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-400">
                        {formatDate(share.expiresAt)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={classNames(
                            'inline-flex items-center gap-1.5 text-xs',
                            status === 'Active'
                              ? 'text-emerald-300'
                              : status === 'Expired'
                                ? 'text-amber-300'
                                : 'text-rose-300',
                          )}
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-current" />
                          {status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {status === 'Active' ? (
                            <button
                              className="btn-ghost !p-2"
                              title="Revoke local record"
                              onClick={() => setRevokeTarget(share)}
                            >
                              <ShieldOff className="h-4 w-4" />
                            </button>
                          ) : null}
                          <button
                            className="btn-ghost !p-2 text-rose-300 hover:text-rose-200"
                            title="Delete record"
                            onClick={() => setDeleteTarget(share)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {[
          {
            icon: Clock,
            title: 'Expiry is advisory',
            body: 'A self-contained link cannot be remotely expired without a backend. Treat expiry as local governance metadata, not a cryptographic guarantee.',
          },
          {
            icon: LockKeyhole,
            title: 'Passphrase = second secret',
            body: 'Passphrase shares derive a separate PBKDF2 key. The link carries ciphertext only; the recipient needs both the link and the passphrase.',
          },
          {
            icon: Download,
            title: 'Bundle for larger files',
            body: 'URLs have practical size limits. Download a .cvshare.json bundle and send it through any channel; it remains ciphertext.',
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
        open={Boolean(revokeTarget)}
        onClose={() => setRevokeTarget(null)}
        title="Revoke this share record?"
        subtitle="This marks the local record revoked. It cannot invalidate a link or bundle that was already copied."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setRevokeTarget(null)}>
              Cancel
            </button>
            <button
              className="btn-danger"
              onClick={() => revokeTarget && void revoke(revokeTarget)}
            >
              <ShieldOff className="h-4 w-4" /> Mark revoked
            </button>
          </>
        }
      >
        <div className="flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-500/5 p-3 text-xs text-amber-100/80">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          Static deployments cannot remotely revoke a capability link. Delete the source file and
          rotate your passphrase if a link leaked.
        </div>
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Delete share record?"
        subtitle="Only the local bookkeeping entry is removed."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setDeleteTarget(null)}>
              Cancel
            </button>
            <button
              className="btn-danger"
              onClick={() => deleteTarget && void remove(deleteTarget)}
            >
              <Trash2 className="h-4 w-4" /> Delete record
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-300">The encrypted file in your vault is not deleted.</p>
      </Modal>
    </div>
  );
}
