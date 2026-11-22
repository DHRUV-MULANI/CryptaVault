import { useEffect, useMemo, useRef, useState } from 'react';
import { Download, FileUp, RefreshCw, Share2, Trash2, Undo2, Upload } from 'lucide-react';
import { Link } from 'wouter';
import { api, type ApiFile } from '../lib/api';
import { decryptContainer, encryptFile, openJson, sha256Hex, unwrapRawKey } from '../lib/crypto';
import { getProfile, PROFILES } from '../lib/profiles';
import type { FileMeta } from '../lib/types';
import { useVault } from '../lib/vault';
import { Badge, Card, PageHeader, Spinner, useToast } from '../components/ui';
import { formatBytes, formatDate } from '../lib/format';

interface Row { api: ApiFile; meta: FileMeta; }

export default function VaultPage(): JSX.Element {
  const { key, currentWorkspace, settings, bumpRevision } = useVault();
  const { notify } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [showDeleted, setShowDeleted] = useState(false);
  const [uploadFolder, setUploadFolder] = useState('');
  const [uploadProfile, setUploadProfile] = useState(settings.defaultProfile);
  const [folderFilter, setFolderFilter] = useState('');

  const profile = getProfile(uploadProfile);

  async function load() {
    if (!key || !currentWorkspace) { setRows([]); setLoading(false); return; }
    setLoading(true);
    try {
      const files = await api.files.list(currentWorkspace.id);
      const filtered = showDeleted ? files : files.filter((f) => !f.deleted_at);
      const decrypted: Row[] = [];
      for (const f of filtered) {
        try {
          const meta = await openJson<FileMeta>(key, { ivB64: f.meta_iv, ctB64: f.encrypted_meta }, `filemeta:${f.id}`);
          decrypted.push({ api: f, meta });
        } catch {
          // skip undecryptable rows (e.g. different master key)
        }
      }
      decrypted.sort((a, b) => (b.meta.createdAt || '').localeCompare(a.meta.createdAt || ''));
      setRows(decrypted);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to load files', 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [key, currentWorkspace?.id, showDeleted]);

  async function onUpload(files: FileList | null) {
    if (!files || !files.length || !key || !currentWorkspace) return;
    setBusy('Uploading…');
    try {
      for (const file of Array.from(files)) {
        setBusy(`Encrypting ${file.name}…`);
        const enc = await encryptFile(file, uploadProfile, profile.chunk_size_bytes, settings.compressByDefault ? null : false);
        enc.meta.folder = uploadFolder.trim() || undefined;
        enc.meta.profile = uploadProfile;
        // seal meta and wrap key with master key
        const { sealJson, wrapRawKey, utf8 } = await import('../lib/crypto');
        const sealedMeta = await sealJson(key, enc.meta, `filemeta:${enc.container.fileId}`);
        const wrappedKey = await wrapRawKey(key, enc.rawKey, `filekey:${enc.container.fileId}`);
        const form = new FormData();
        form.append('file_id', enc.container.fileId);
        form.append('version', '1');
        form.append('encrypted_meta', sealedMeta.ctB64);
        form.append('meta_iv', sealedMeta.ivB64);
        form.append('wrapped_key', wrappedKey.ctB64);
        form.append('wrapped_iv', wrappedKey.ivB64);
        form.append('content_tag', enc.meta.hash);
        form.append('profile', uploadProfile);
        form.append('ciphertext', new Blob([utf8(JSON.stringify(enc.container))], { type: 'application/octet-stream' }), `${enc.container.fileId}.cv`);
        setBusy(`Uploading ${file.name}…`);
        await api.files.upload(currentWorkspace.id, form);
      }
      notify('Upload complete', 'success');
      bumpRevision();
      await load();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Upload failed', 'error');
    } finally {
      setBusy(null);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  async function onDownload(row: Row) {
    if (!key) return;
    setBusy(`Downloading ${row.meta.name}…`);
    try {
      const bytes = await api.files.download(row.api.id);
      const container = JSON.parse(new TextDecoder().decode(bytes));
      const rawKey = await unwrapRawKey(key, { ivB64: row.api.wrapped_iv, ctB64: row.api.wrapped_key }, `filekey:${row.api.id}`);
      const plain = await decryptContainer(container, rawKey);
      const hash = await sha256Hex(plain);
      if (hash !== row.meta.hash) throw new Error('Integrity check failed.');
      const blob = new Blob([plain], { type: row.meta.type || 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = row.meta.name;
      a.click();
      URL.revokeObjectURL(url);
      notify('Download decrypted and verified', 'success');
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Download failed', 'error');
    } finally {
      setBusy(null);
    }
  }

  async function onTrash(row: Row) {
    setBusy('Moving to trash…');
    try { await api.files.trash(row.api.id); notify('Moved to trash', 'success'); await load(); }
    catch (err) { notify(err instanceof Error ? err.message : 'Trash failed', 'error'); }
    finally { setBusy(null); }
  }

  async function onUntrash(row: Row) {
    setBusy('Restoring…');
    try { await api.files.untrash(row.api.id); notify('Restored', 'success'); await load(); }
    catch (err) { notify(err instanceof Error ? err.message : 'Restore failed', 'error'); }
    finally { setBusy(null); }
  }

  async function onPermanentDelete(row: Row) {
    if (!confirm(`Permanently delete "${row.meta.name}"?`)) return;
    setBusy('Deleting…');
    try { await api.files.permanentDelete(row.api.id); notify('Permanently deleted', 'success'); await load(); }
    catch (err) { notify(err instanceof Error ? err.message : 'Delete failed', 'error'); }
    finally { setBusy(null); }
  }

  const visibleRows = useMemo(() => folderFilter.trim() ? rows.filter((r) => (r.meta.folder || '').toLowerCase().includes(folderFilter.toLowerCase().trim())) : rows, [rows, folderFilter]);
  const total = useMemo(() => visibleRows.reduce((s, r) => s + (r.meta.size || 0), 0), [visibleRows]);

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Encrypted vault"
        title="Workspace files"
        description="Files are encrypted in this browser, uploaded as ciphertext to the API/S3, and decrypted locally on download."
        action={
          <>
            <button className="btn-secondary" onClick={() => void load()}><RefreshCw className="h-4 w-4" /> Refresh</button>
            <button className="btn-primary" onClick={() => inputRef.current?.click()} disabled={!currentWorkspace || !!busy}><Upload className="h-4 w-4" /> Upload</button>
            <input ref={inputRef} type="file" multiple className="hidden" onChange={(e) => void onUpload(e.target.files)} />
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-slate-400">
        <Badge className="badge-cyan">{currentWorkspace?.name ?? 'No workspace'}</Badge>
        <span>{visibleRows.length} files</span>
        <span>{formatBytes(total)}</span>
        <label className="ml-auto inline-flex items-center gap-2">
          <input type="checkbox" checked={showDeleted} onChange={(e) => setShowDeleted(e.target.checked)} />
          Show trashed
        </label>
      </div>

      <Card className="mb-4 !p-4">
        <div className="grid gap-3 md:grid-cols-3">
          <label className="block text-xs text-slate-400">Upload folder (optional)
            <input className="input mt-1" value={uploadFolder} onChange={(e) => setUploadFolder(e.target.value)} placeholder="e.g. finance/reports" />
          </label>
          <label className="block text-xs text-slate-400">Encryption profile
            <select className="input mt-1" value={uploadProfile} onChange={(e) => setUploadProfile(e.target.value as any)}>
              {PROFILES.map((p) => <option key={p.level} value={p.level}>{p.level} — {p.name}</option>)}
            </select>
          </label>
          <div className="text-xs text-slate-400">
            <div>Key wrapping</div>
            <div className="mt-1 rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-[11px] text-slate-300">Per-file random key, wrapped by your master key (AES-GCM). Master key never leaves this browser.</div>
          </div>
        </div>
        <div className="mt-3">
          <label className="block text-xs text-slate-400">Filter by folder
            <input className="input mt-1" value={folderFilter} onChange={(e) => setFolderFilter(e.target.value)} placeholder="type folder name..." />
          </label>
        </div>
      </Card>

      {busy && <div className="mb-4 rounded-xl border border-cyan-400/20 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-100"><Spinner /> {busy}</div>}

      <Card>
        {loading ? (
          <div className="py-10 text-center text-slate-400"><Spinner /> Loading files…</div>
        ) : visibleRows.length === 0 ? (
          <div className="py-12 text-center">
            <FileUp className="mx-auto mb-3 h-8 w-8 text-slate-600" />
            <p className="text-sm text-slate-400">No files in this workspace yet.</p>
            <button className="btn-primary mt-4" onClick={() => inputRef.current?.click()} disabled={!currentWorkspace}><Upload className="h-4 w-4" /> Encrypt & upload</button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/8 text-left text-[11px] uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2">Name</th><th className="px-3 py-2">Size</th><th className="px-3 py-2">Profile</th><th className="px-3 py-2">Version</th><th className="px-3 py-2">Created</th><th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => (
                  <tr key={row.api.id} className="border-b border-white/5 align-middle">
                    <td className="px-3 py-3">
                      <div className="font-medium text-slate-100">{row.meta.name}</div>
                      <div className="text-[11px] text-slate-500">{row.meta.folder ? `${row.meta.folder} · ` : ''}{row.meta.type} · {row.meta.hash.slice(0, 12)}…</div>
                      {row.api.deleted_at ? <Badge className="badge-amber mt-1">trashed</Badge> : null}
                    </td>
                    <td className="px-3 py-3 text-slate-300">{formatBytes(row.meta.size)}</td>
                    <td className="px-3 py-3"><Badge className="badge-cyan">{row.meta.profile}</Badge></td>
                    <td className="px-3 py-3 text-slate-300">v{row.api.current_version}</td>
                    <td className="px-3 py-3 text-slate-400">{formatDate(row.meta.createdAt)}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button className="btn-secondary !px-2.5 !py-1.5 !text-xs" onClick={() => void onDownload(row)} disabled={!!busy}><Download className="h-3.5 w-3.5" /> Get</button>
                        {!row.api.deleted_at && <Link href="/shares" className="btn-secondary !px-2.5 !py-1.5 !text-xs"><Share2 className="h-3.5 w-3.5" /> Share</Link>}
                        {!row.api.deleted_at ? (
                          <button className="btn-secondary !px-2.5 !py-1.5 !text-xs" onClick={() => void onTrash(row)} disabled={!!busy}><Trash2 className="h-3.5 w-3.5" /> Trash</button>
                        ) : (
                          <>
                            <button className="btn-secondary !px-2.5 !py-1.5 !text-xs" onClick={() => void onUntrash(row)} disabled={!!busy}><Undo2 className="h-3.5 w-3.5" /> Restore</button>
                            <button className="btn-danger !px-2.5 !py-1.5 !text-xs" onClick={() => void onPermanentDelete(row)} disabled={!!busy}><Trash2 className="h-3.5 w-3.5" /> Delete</button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}