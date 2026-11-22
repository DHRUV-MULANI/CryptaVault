import { useEffect, useMemo, useState } from 'react';
import { Copy, Link2, LockKeyhole, Plus, RefreshCw, Share2, ShieldOff } from 'lucide-react';
import { api, type ApiShare, type ApiFile } from '../lib/api';
import { useVault } from '../lib/vault';
import { bytesToB64Url, openJson, unwrapRawKey } from '../lib/crypto';
import type { FileMeta } from '../lib/types';
import { Badge, Card, EmptyState, Modal, PageHeader, Spinner, useToast } from '../components/ui';
import { formatDate, relativeTime } from '../lib/format';

export default function SharesPage(): JSX.Element {
  const { key, currentWorkspace } = useVault();
  const { notify } = useToast();
  const [shares, setShares] = useState<ApiShare[]>([]);
  const [files, setFiles] = useState<Array<{ api: ApiFile; meta: FileMeta }>>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [fileId, setFileId] = useState('');
  const [ttlHours, setTtlHours] = useState(24);
  const [maxUses, setMaxUses] = useState(3);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [createdLink, setCreatedLink] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [s, f] = await Promise.all([api.shares.list(), currentWorkspace ? api.files.list(currentWorkspace.id) : Promise.resolve([])]);
      setShares(s);
      if (key) {
        const dec: Array<{ api: ApiFile; meta: FileMeta }> = [];
        for (const file of f.filter((x) => !x.deleted_at)) {
          try { dec.push({ api: file, meta: await openJson<FileMeta>(key, { ivB64: file.meta_iv, ctB64: file.encrypted_meta }, `filemeta:${file.id}`) }); } catch {}
        }
        setFiles(dec);
        if (!fileId && dec[0]) setFileId(dec[0].api.id);
      } else {
        setFiles([]);
      }
    } catch (err) { notify(err instanceof Error ? err.message : 'Failed to load shares', 'error'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [currentWorkspace?.id, key]);

  async function createShare(e: React.FormEvent) {
    e.preventDefault();
    if (!key || !fileId) return;
    setBusy(true);
    try {
      const expiresAt = new Date(Date.now() + ttlHours * 3600_000).toISOString();
      const share = await api.shares.create({ file_id: fileId, expires_at: expiresAt, max_uses: maxUses, password: password || null });
      const file = files.find((f) => f.api.id === fileId)?.api;
      if (file) {
        const rawKey = await unwrapRawKey(key, { ivB64: file.wrapped_iv, ctB64: file.wrapped_key }, `filekey:${file.id}`);
        const k = bytesToB64Url(rawKey);
        const base = window.location.origin + window.location.pathname;
        setCreatedLink(`${base}#/s/${share.token}?k=${k}`);
      } else {
        setCreatedLink(share.share_url);
      }
      notify('Share created', 'success');
      setPassword('');
      await load();
    } catch (err) { notify(err instanceof Error ? err.message : 'Create failed', 'error'); }
    finally { setBusy(false); }
  }

  async function shareAllFiles() {
    if (!key || files.length === 0) return;
    if (!confirm(`Create shares for all ${files.length} file(s) in this workspace?`)) return;
    setBusy(true);
    try {
      const expiresAt = new Date(Date.now() + ttlHours * 3600_000).toISOString();
      const links: string[] = [];
      for (const f of files) {
        const share = await api.shares.create({ file_id: f.api.id, expires_at: expiresAt, max_uses: maxUses, password: password || null });
        const rawKey = await unwrapRawKey(key, { ivB64: f.api.wrapped_iv, ctB64: f.api.wrapped_key }, `filekey:${f.api.id}`);
        const k = bytesToB64Url(rawKey);
        const base = window.location.origin + window.location.pathname;
        links.push(`${f.meta.name}: ${base}#/s/${share.token}?k=${k}`);
      }
      setCreatedLink(links.join('\n\n'));
      notify(`Created ${links.length} share(s)`, 'success');
      await load();
    } catch (err) { notify(err instanceof Error ? err.message : 'Share-all failed', 'error'); }
    finally { setBusy(false); }
  }

  async function revoke(token: string) {
    try { await api.shares.revoke(token); notify('Share revoked', 'success'); await load(); }
    catch (err) { notify(err instanceof Error ? err.message : 'Revoke failed', 'error'); }
  }

  const active = useMemo(() => shares.filter((s) => !s.revoked && (!s.expires_at || new Date(s.expires_at).getTime() > Date.now()) && s.remaining_uses > 0).length, [shares]);

  return (
    <div className="animate-in">
      <PageHeader eyebrow="Secure shares" title="Server-enforced shares" description="Shares are created through the API with expiry, max uses, optional password, and revocation. The share link includes client-side key material in the URL fragment so the server never sees decryption keys."
        action={<><button className="btn-secondary" onClick={() => void load()}><RefreshCw className="h-4 w-4" /> Refresh</button><button className="btn-secondary" onClick={() => void shareAllFiles()} disabled={!files.length || busy}><Share2 className="h-4 w-4" /> Share all</button><button className="btn-primary" onClick={() => setCreateOpen(true)} disabled={!files.length}><Plus className="h-4 w-4" /> Create share</button></>} />

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        {[{ label: 'Active shares', value: active, hint: 'Not revoked/expired/exhausted' }, { label: 'Total shares', value: shares.length, hint: 'Owned by current user' }, { label: 'Password protected', value: shares.filter((s) => s.password_protected).length, hint: 'Server-verified password' }].map((item) => (
          <Card key={item.label} className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{item.label}</div><div className="mt-1.5 text-2xl font-semibold text-white">{item.value}</div><div className="mt-1 text-[11px] text-slate-500">{item.hint}</div></Card>
        ))}
      </div>

      {loading ? <div className="card py-12 text-center text-sm text-slate-400"><Spinner /> Loading shares…</div> : shares.length === 0 ? (
        <EmptyState icon={<Link2 className="h-8 w-8" />} title="No shares yet" description="Create a server-enforced share from an encrypted workspace file." action={<button className="btn-primary" onClick={() => setCreateOpen(true)} disabled={!files.length}><Plus className="h-4 w-4" /> Create share</button>} />
      ) : (
        <Card className="!p-0 overflow-hidden"><div className="overflow-x-auto"><table className="data-table w-full text-left"><thead><tr className="border-b border-white/8 bg-white/[0.02]"><th className="px-4 py-3">Share</th><th className="px-4 py-3">File</th><th className="px-4 py-3">Expires</th><th className="px-4 py-3">Uses</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead><tbody>
          {shares.map((s) => {
            const expired = !!s.expires_at && new Date(s.expires_at).getTime() <= Date.now();
            const exhausted = s.remaining_uses <= 0;
            const status = s.revoked ? 'Revoked' : expired ? 'Expired' : exhausted ? 'Exhausted' : 'Active';
            const file = files.find((f) => f.api.id === s.file_id);
            return (
              <tr key={s.token} className="border-b border-white/5 last:border-0">
                <td className="px-4 py-3"><div className="flex items-center gap-2.5"><span className={`flex h-8 w-8 items-center justify-center rounded-lg ${s.password_protected ? 'bg-purple-500/10 text-purple-300' : 'bg-cyan-500/10 text-cyan-300'}`}>{s.password_protected ? <LockKeyhole className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}</span><div><div className="text-xs font-medium text-slate-200">{s.token.slice(0, 12)}…</div><div className="text-[10px] text-slate-500">{relativeTime(s.created_at ?? '')}</div></div></div></td>
                <td className="px-4 py-3 text-slate-300">{file?.meta.name ?? s.file_id.slice(0, 8)}</td>
                <td className="px-4 py-3 text-slate-400">{s.expires_at ? formatDate(s.expires_at) : 'Never'}</td>
                <td className="px-4 py-3 text-slate-400">{s.uses}/{s.max_uses}</td>
                <td className="px-4 py-3"><Badge className={status === 'Active' ? 'badge-emerald' : status === 'Revoked' ? 'badge-rose' : 'badge-amber'}>{status}</Badge></td>
                <td className="px-4 py-3"><div className="flex justify-end gap-1">{status === 'Active' && <button className="btn-ghost !p-2" title="Revoke" onClick={() => void revoke(s.token)}><ShieldOff className="h-4 w-4" /></button>}</div></td>
              </tr>
            );
          })}
        </tbody></table></div></Card>
      )}

      <Modal open={createOpen} onClose={() => { setCreateOpen(false); setCreatedLink(null); }} title="Create server share" subtitle="The server enforces expiry, max uses, password, and revocation. The key stays in the URL fragment.">
        {createdLink ? (
          <div className="space-y-3">
            <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-3 text-xs text-emerald-100">Share created. Copy this link - it contains the decryption key fragment.</div>
            <textarea className="input min-h-[96px] text-xs" readOnly value={createdLink} />
            <div className="flex gap-2">
              <button className="btn-primary" onClick={() => { void navigator.clipboard.writeText(createdLink); notify('Link copied', 'success'); }}><Copy className="h-4 w-4" /> Copy link</button>
              <button className="btn-secondary" onClick={() => { setCreateOpen(false); setCreatedLink(null); }}>Done</button>
            </div>
          </div>
        ) : (
          <form className="space-y-3" onSubmit={createShare}>
            <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">File</span><select className="input" value={fileId} onChange={(e) => setFileId(e.target.value)}>{files.map((f) => <option key={f.api.id} value={f.api.id}>{f.meta.name}</option>)}</select></label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">TTL (hours)</span><input className="input" type="number" min={1} max={720} value={ttlHours} onChange={(e) => setTtlHours(Number(e.target.value))} /></label>
              <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Max uses</span><input className="input" type="number" min={1} max={1000} value={maxUses} onChange={(e) => setMaxUses(Number(e.target.value))} /></label>
            </div>
            <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Password (optional, server-verified)</span><input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Optional share password" /></label>
            <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setCreateOpen(false)}>Cancel</button><button className="btn-primary" disabled={busy || !fileId}>{busy ? <Spinner /> : <Plus className="h-4 w-4" />} Create</button></div>
          </form>
        )}
      </Modal>
    </div>
  );
}
