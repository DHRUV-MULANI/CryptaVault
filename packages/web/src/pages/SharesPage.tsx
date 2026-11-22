import { useEffect, useMemo, useState } from 'react';
import { Copy, Link2, LockKeyhole, Plus, QrCode, RefreshCw, Share2, ShieldOff, KeyRound, Mail, RotateCcw } from 'lucide-react';
import { api, type ApiShare, type ApiFile } from '../lib/api';
import { useVault } from '../lib/vault';
import { bytesToB64Url, openJson, unwrapRawKey } from '../lib/crypto';
import type { FileMeta } from '../lib/types';
import { Badge, Card, EmptyState, Modal, PageHeader, Spinner, useToast } from '../components/ui';
import { formatDate, relativeTime } from '../lib/format';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') ?? '';

function makeShareLink(token: string, keyB64Url: string): string {
  const base = window.location.origin + window.location.pathname;
  return `${base}#/s/${token}?k=${keyB64Url}`;
}

export default function SharesPage(): JSX.Element {
  const { key, currentWorkspace } = useVault();
  const { notify } = useToast();
  const [shares, setShares] = useState<ApiShare[]>([]);
  const [received, setReceived] = useState<ApiShare[]>([]);
  const [files, setFiles] = useState<Array<{ api: ApiFile; meta: FileMeta }>>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'mine' | 'received'>('mine');
  const [createOpen, setCreateOpen] = useState(false);
  const [fileId, setFileId] = useState('');
  const [ttlHours, setTtlHours] = useState(24);
  const [maxUses, setMaxUses] = useState(3);
  const [password, setPassword] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [pin, setPin] = useState('');
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<{ link: string; pin?: string; token: string } | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [s, r, f] = await Promise.all([
        api.shares.list(),
        api.shares.received().catch(() => [] as ApiShare[]),
        currentWorkspace ? api.files.list(currentWorkspace.id) : Promise.resolve([]),
      ]);
      setShares(s);
      setReceived(r);
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
    if (pin.trim() && !/^\d{8}$/.test(pin.trim())) { notify('PIN must be exactly 8 digits', 'error'); return; }
    setBusy(true);
    try {
      const expiresAt = new Date(Date.now() + ttlHours * 3600_000).toISOString();
      const share = await api.shares.create({
        file_id: fileId,
        expires_at: expiresAt,
        max_uses: maxUses,
        password: password || null,
        recipient_email: recipientEmail.trim() || null,
        pin: pin.trim() || null,
      });
      const file = files.find((f) => f.api.id === fileId)?.api;
      let link = share.share_url;
      if (file) {
        const rawKey = await unwrapRawKey(key, { ivB64: file.wrapped_iv, ctB64: file.wrapped_key }, `filekey:${file.id}`);
        link = makeShareLink(share.token, bytesToB64Url(rawKey));
      }
      setCreated({ link, pin: share.pin, token: share.token });
      notify('Share created', 'success');
      setPassword(''); setRecipientEmail(''); setPin('');
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
        const share = await api.shares.create({ file_id: f.api.id, expires_at: expiresAt, max_uses: maxUses, password: password || null, recipient_email: recipientEmail.trim() || null, pin: pin.trim() || null });
        const rawKey = await unwrapRawKey(key, { ivB64: f.api.wrapped_iv, ctB64: f.api.wrapped_key }, `filekey:${f.api.id}`);
        links.push(`${f.meta.name}\n${makeShareLink(share.token, bytesToB64Url(rawKey))}\nPIN: ${share.pin ?? '(none)'}`);
      }
      setCreated({ link: links.join('\n\n'), token: '' });
      notify(`Created ${links.length} share(s)`, 'success');
      await load();
    } catch (err) { notify(err instanceof Error ? err.message : 'Share-all failed', 'error'); }
    finally { setBusy(false); }
  }

  async function revoke(token: string) {
    try { await api.shares.revoke(token); notify('Share revoked', 'success'); await load(); }
    catch (err) { notify(err instanceof Error ? err.message : 'Revoke failed', 'error'); }
  }

  async function changePin(s: ApiShare) {
    const next = prompt('Enter new 8-digit PIN (leave empty to auto-generate):', '');
    if (next === null) return;
    if (next.trim() && !/^\d{8}$/.test(next.trim())) { notify('PIN must be exactly 8 digits', 'error'); return; }
    try {
      const updated = await api.shares.updatePin(s.token, next.trim() || null);
      notify(`PIN updated: ${updated.pin ?? '(generated)'}`, 'success');
      if (updated.pin) alert(`New PIN for share ${s.token.slice(0, 8)}: ${updated.pin}`);
      await load();
    } catch (err) { notify(err instanceof Error ? err.message : 'PIN update failed', 'error'); }
  }

  async function regenerate(s: ApiShare) {
    if (!confirm('Regenerate share link? The old link will stop working.')) return;
    try {
      const updated = await api.shares.regenerate(s.token);
      const file = files.find((f) => f.api.id === updated.file_id)?.api;
      let link = updated.share_url;
      if (file && key) {
        const rawKey = await unwrapRawKey(key, { ivB64: file.wrapped_iv, ctB64: file.wrapped_key }, `filekey:${file.id}`);
        link = makeShareLink(updated.token, bytesToB64Url(rawKey));
      }
      setCreated({ link, pin: updated.pin, token: updated.token });
      setCreateOpen(true);
      notify('Link regenerated', 'success');
      await load();
    } catch (err) { notify(err instanceof Error ? err.message : 'Regenerate failed', 'error'); }
  }

  async function copy(text: string, label = 'Copied') {
    await navigator.clipboard.writeText(text);
    notify(label, 'success');
  }

  const active = useMemo(() => shares.filter((s) => !s.revoked && (!s.expires_at || new Date(s.expires_at).getTime() > Date.now()) && s.remaining_uses > 0).length, [shares]);
  const qrSrc = created?.token ? `${API_URL || ''}/api/shares/${created.token}/qr?key=${encodeURIComponent(created.link.split('k=')[1] ?? '')}` : null;

  return (
    <div className="animate-in">
      <PageHeader eyebrow="Secure shares" title="Server-enforced shares" description="Create share links with expiry, max uses, optional password, recipient email, and 8-digit PIN. Recipient email users can access without PIN when logged in; others need PIN. Links can be regenerated and copied/QR-shared."
        action={<><button className="btn-secondary" onClick={() => void load()}><RefreshCw className="h-4 w-4" /> Refresh</button><button className="btn-secondary" onClick={() => void shareAllFiles()} disabled={!files.length || busy}><Share2 className="h-4 w-4" /> Share all</button><button className="btn-primary" onClick={() => { setCreated(null); setCreateOpen(true); }} disabled={!files.length}><Plus className="h-4 w-4" /> Create share</button></>} />

      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        {[{ label: 'Active shares', value: active, hint: 'Not revoked/expired/exhausted' }, { label: 'My shares', value: shares.length, hint: 'Owned by you' }, { label: 'Received', value: received.length, hint: 'Shared to your email' }, { label: 'PIN protected', value: shares.filter((s) => s.pin_protected).length, hint: '8-digit access PIN' }].map((item) => (
          <Card key={item.label} className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{item.label}</div><div className="mt-1.5 text-2xl font-semibold text-white">{item.value}</div><div className="mt-1 text-[11px] text-slate-500">{item.hint}</div></Card>
        ))}
      </div>

      <div className="mb-4 flex gap-2">
        <button className={`btn-secondary !px-3 !py-1.5 !text-xs ${tab === 'mine' ? 'border-cyan-400/40 text-cyan-200' : ''}`} onClick={() => setTab('mine')}>My shares</button>
        <button className={`btn-secondary !px-3 !py-1.5 !text-xs ${tab === 'received' ? 'border-cyan-400/40 text-cyan-200' : ''}`} onClick={() => setTab('received')}>Shared with me</button>
      </div>

      {loading ? <div className="card py-12 text-center text-sm text-slate-400"><Spinner /> Loading shares…</div> : tab === 'received' ? (
        received.length === 0 ? <EmptyState icon={<Mail className="h-8 w-8" />} title="No shares received" description="When someone shares a file to your email, it appears here. You can open it without PIN when logged in." /> : (
          <Card className="!p-0 overflow-hidden"><div className="overflow-x-auto"><table className="data-table w-full text-left"><thead><tr className="border-b border-white/8 bg-white/[0.02]"><th className="px-4 py-3">Share</th><th className="px-4 py-3">File</th><th className="px-4 py-3">Expires</th><th className="px-4 py-3">Access</th><th className="px-4 py-3 text-right">Open</th></tr></thead><tbody>
            {received.map((s) => (
              <tr key={s.token} className="border-b border-white/5 last:border-0">
                <td className="px-4 py-3 text-xs text-slate-200">{s.token.slice(0, 12)}…<div className="text-[10px] text-slate-500">{relativeTime(s.created_at ?? '')}</div></td>
                <td className="px-4 py-3 text-slate-300">{s.file_id.slice(0, 8)} · v{s.version}</td>
                <td className="px-4 py-3 text-slate-400">{s.expires_at ? formatDate(s.expires_at) : 'Never'}</td>
                <td className="px-4 py-3"><Badge className="badge-emerald">Recipient (no PIN)</Badge></td>
                <td className="px-4 py-3 text-right"><a className="btn-secondary !px-2.5 !py-1.5 !text-xs" href={`#/s/${s.token}`}>Open</a></td>
              </tr>
            ))}
          </tbody></table></div></Card>
        )
      ) : shares.length === 0 ? (
        <EmptyState icon={<Link2 className="h-8 w-8" />} title="No shares yet" description="Create a server-enforced share from an encrypted workspace file." action={<button className="btn-primary" onClick={() => { setCreated(null); setCreateOpen(true); }} disabled={!files.length}><Plus className="h-4 w-4" /> Create share</button>} />
      ) : (
        <Card className="!p-0 overflow-hidden"><div className="overflow-x-auto"><table className="data-table w-full text-left"><thead><tr className="border-b border-white/8 bg-white/[0.02]"><th className="px-4 py-3">Share</th><th className="px-4 py-3">File/Recipient</th><th className="px-4 py-3">Expires</th><th className="px-4 py-3">Uses</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead><tbody>
          {shares.map((s) => {
            const expired = !!s.expires_at && new Date(s.expires_at).getTime() <= Date.now();
            const exhausted = s.remaining_uses <= 0;
            const status = s.revoked ? 'Revoked' : expired ? 'Expired' : exhausted ? 'Exhausted' : 'Active';
            const file = files.find((f) => f.api.id === s.file_id);
            return (
              <tr key={s.token} className="border-b border-white/5 last:border-0">
                <td className="px-4 py-3"><div className="flex items-center gap-2.5"><span className={`flex h-8 w-8 items-center justify-center rounded-lg ${s.password_protected ? 'bg-purple-500/10 text-purple-300' : 'bg-cyan-500/10 text-cyan-300'}`}>{s.password_protected ? <LockKeyhole className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}</span><div><div className="text-xs font-medium text-slate-200">{s.token.slice(0, 12)}…</div><div className="text-[10px] text-slate-500">{relativeTime(s.created_at ?? '')}</div></div></div></td>
                <td className="px-4 py-3 text-slate-300"><div>{file?.meta.name ?? s.file_id.slice(0, 8)}</div><div className="text-[10px] text-slate-500">{s.recipient_email ?? 'Anyone with link+PIN'} {s.pin_protected ? '· PIN' : ''}</div></td>
                <td className="px-4 py-3 text-slate-400">{s.expires_at ? formatDate(s.expires_at) : 'Never'}</td>
                <td className="px-4 py-3 text-slate-400">{s.uses}/{s.max_uses}</td>
                <td className="px-4 py-3"><Badge className={status === 'Active' ? 'badge-emerald' : status === 'Revoked' ? 'badge-rose' : 'badge-amber'}>{status}</Badge></td>
                <td className="px-4 py-3"><div className="flex justify-end gap-1">{status === 'Active' && <><button className="btn-ghost !p-2" title="Copy link" onClick={() => { const f = files.find((x) => x.api.id === s.file_id); if (f && key) { void unwrapRawKey(key, { ivB64: f.api.wrapped_iv, ctB64: f.api.wrapped_key }, `filekey:${f.api.id}`).then((rk) => copy(makeShareLink(s.token, bytesToB64Url(rk)), 'Link copied')); } else { void copy(s.share_url, 'Link copied'); } }}><Copy className="h-4 w-4" /></button><button className="btn-ghost !p-2" title="Change PIN" onClick={() => void changePin(s)}><KeyRound className="h-4 w-4" /></button><button className="btn-ghost !p-2" title="Regenerate link" onClick={() => void regenerate(s)}><RotateCcw className="h-4 w-4" /></button><button className="btn-ghost !p-2" title="Revoke" onClick={() => void revoke(s.token)}><ShieldOff className="h-4 w-4" /></button></>}</div></td>
              </tr>
            );
          })}
        </tbody></table></div></Card>
      )}

      <Modal open={createOpen} onClose={() => { setCreateOpen(false); setCreated(null); }} title="Create server share" subtitle="Server enforces expiry, max uses, password, revocation. Add recipient email and 8-digit PIN for controlled access. Key stays in URL fragment.">
        {created ? (
          <div className="space-y-3">
            <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-3 text-xs text-emerald-100">Share ready. Copy the link and PIN. The PIN is shown once; you can change it later.</div>
            {created.pin && <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/10 p-3"><div className="text-[11px] uppercase tracking-wider text-cyan-300">Access PIN</div><div className="mt-1 font-mono text-2xl font-semibold tracking-[0.2em] text-white">{created.pin}</div></div>}
            <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Share link (includes decryption key fragment)</span><textarea className="input min-h-[72px] text-xs" readOnly value={created.link} /></label>
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" onClick={() => void copy(created.link, 'Link copied')}><Copy className="h-4 w-4" /> Copy link</button>
              {created.pin && <button className="btn-secondary" onClick={() => void copy(created.pin!, 'PIN copied')}><KeyRound className="h-4 w-4" /> Copy PIN</button>}
              {qrSrc && <a className="btn-secondary" href={qrSrc} target="_blank" rel="noreferrer"><QrCode className="h-4 w-4" /> QR</a>}
              <button className="btn-secondary" onClick={() => { setCreateOpen(false); setCreated(null); }}>Done</button>
            </div>
            {qrSrc && <div className="flex justify-center rounded-xl border border-white/10 bg-white p-3"><img src={qrSrc} alt="Share QR" className="h-44 w-44" /></div>}
          </div>
        ) : (
          <form className="space-y-3" onSubmit={createShare}>
            <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">File</span><select className="input" value={fileId} onChange={(e) => setFileId(e.target.value)}>{files.map((f) => <option key={f.api.id} value={f.api.id}>{f.meta.name}</option>)}</select></label>
            <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Recipient email (optional)</span><input className="input" type="email" value={recipientEmail} onChange={(e) => setRecipientEmail(e.target.value)} placeholder="user@example.com — no PIN needed when logged in" /></label>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">TTL (hours)</span><input className="input" type="number" min={1} max={720} value={ttlHours} onChange={(e) => setTtlHours(Number(e.target.value))} /></label>
              <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Max uses</span><input className="input" type="number" min={1} max={1000} value={maxUses} onChange={(e) => setMaxUses(Number(e.target.value))} /></label>
              <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">8-digit PIN</span><input className="input font-mono" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 8))} placeholder="Auto" /></label>
            </div>
            <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Password (optional, server-verified)</span><input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Optional share password" /></label>
            <div className="text-[11px] text-slate-500">If PIN is empty, CryptaVault auto-generates an 8-digit PIN. Recipient email users skip PIN when logged in; others must enter PIN.</div>
            <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setCreateOpen(false)}>Cancel</button><button className="btn-primary" disabled={busy || !fileId}>{busy ? <Spinner /> : <Plus className="h-4 w-4" />} Create</button></div>
          </form>
        )}
      </Modal>
    </div>
  );
}
