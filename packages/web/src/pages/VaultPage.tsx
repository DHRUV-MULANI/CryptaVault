import { useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Download,
  FileUp,
  FolderLock,
  Pencil,
  Search,
  Share2,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import type { DecryptedFile } from '../lib/hooks';
import { useFiles } from '../lib/hooks';
import { useVault, loadFileMeta, deleteFileCascade } from '../lib/vault';
import { dbGet, dbPut } from '../lib/db';
import { recordAudit } from '../lib/audit';
import {
  buildShare,
  buildShareBundle,
  buildShareLink,
  decryptContainer,
  encryptFile,
  sealJson,
  wrapRawKey,
} from '../lib/crypto';
import { getProfile, PROFILES } from '../lib/profiles';
import type {
  Container,
  FileMeta,
  ProfileLevel,
  StoredBlob,
} from '../lib/types';
import {
  Badge,
  CopyButton,
  EmptyState,
  Modal,
  PageHeader,
  ProgressBar,
  Spinner,
  useToast,
} from '../components/ui';
import FileIcon from '../components/FileIcon';
import { classNames, downloadBlob, downloadText, formatBytes, relativeTime } from '../lib/format';

const MAX_FILE_BYTES = 250 * 1024 * 1024;

export default function VaultPage(): JSX.Element {
  const { key, settings, bumpRevision } = useVault();
  const { files, loading } = useFiles();
  const { notify } = useToast();
  const [search, setSearch] = useState('');
  const [profileFilter, setProfileFilter] = useState<string>('ALL');
  const [sort, setSort] = useState<'newest' | 'oldest' | 'name' | 'size'>('newest');

  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProfile, setUploadProfile] = useState<ProfileLevel>(settings.defaultProfile);
  const [compressMode, setCompressMode] = useState<'auto' | 'on' | 'off'>(
    settings.compressByDefault ? 'auto' : 'off',
  );
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const [shareTarget, setShareTarget] = useState<DecryptedFile | null>(null);
  const [shareTtl, setShareTtl] = useState(settings.shareTtlHours);
  const [sharePassphrase, setSharePassphrase] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<{
    link: string;
    bundle: string;
    filename: string;
    mode: string;
  } | null>(null);

  const [renameTarget, setRenameTarget] = useState<DecryptedFile | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<DecryptedFile | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    const list = files.filter((file) => {
      if (profileFilter !== 'ALL' && file.meta.profile !== profileFilter) return false;
      if (!term) return true;
      return (
        file.meta.name.toLowerCase().includes(term) ||
        file.meta.type.toLowerCase().includes(term)
      );
    });
    return [...list].sort((a, b) => {
      if (sort === 'name') return a.meta.name.localeCompare(b.meta.name);
      if (sort === 'size') return b.meta.size - a.meta.size;
      if (sort === 'oldest') return a.meta.createdAt.localeCompare(b.meta.createdAt);
      return b.meta.createdAt.localeCompare(a.meta.createdAt);
    });
  }, [files, profileFilter, search, sort]);

  function chooseFile(file: File | null): void {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      notify(`File is larger than ${formatBytes(MAX_FILE_BYTES)}; choose a smaller file.`, 'error');
      return;
    }
    setUploadFile(file);
    setUploadError(null);
    setUploadOpen(true);
  }

  async function doUpload(): Promise<void> {
    if (!key || !uploadFile) return;
    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);
    try {
      const profile = getProfile(uploadProfile);
      const compressOverride =
        compressMode === 'auto' ? null : compressMode === 'on';
      const result = await encryptFile(
        uploadFile,
        uploadProfile,
        profile.chunk_size_bytes,
        compressOverride,
        setUploadProgress,
      );
      const id = result.container.fileId;
      await dbPut('files', {
        id,
        createdAt: result.meta.createdAt,
        meta: await sealJson(key, result.meta, `filemeta:${id}`),
        key: await wrapRawKey(key, result.rawKey, `filekey:${id}`),
      });
      await dbPut('blobs', { id, container: JSON.stringify(result.container) });
      await recordAudit(
        'file.encrypted',
        id,
        `profile=${uploadProfile};bytes=${result.meta.size};chunks=${result.meta.chunkCount}`,
      );
      bumpRevision();
      notify(`${result.meta.name} encrypted and stored.`, 'success');
      setUploadOpen(false);
      setUploadFile(null);
      setUploadProgress(0);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Encryption failed.');
    } finally {
      setUploading(false);
    }
  }

  async function downloadFile(target: DecryptedFile): Promise<void> {
    if (!key) return;
    setDownloadingId(target.record.id);
    try {
      const blob = await dbGet<StoredBlob>('blobs', target.record.id);
      if (!blob) throw new Error('Encrypted payload is missing.');
      const container = JSON.parse(blob.container) as Container;
      const { rawKey } = await loadFileMeta(key, target.record);
      const plaintext = await decryptContainer(container, rawKey);
      downloadBlob(
        plaintext,
        target.meta.name,
        target.meta.type || 'application/octet-stream',
      );
      await recordAudit('file.decrypted', target.record.id);
      bumpRevision();
      notify(`${target.meta.name} decrypted locally.`, 'success');
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Decryption failed.', 'error');
    } finally {
      setDownloadingId(null);
    }
  }

  function openShare(target: DecryptedFile): void {
    if (!settings.sharingEnabled) {
      notify('Secure sharing is disabled by policy. Enable it in the Admin console.', 'error');
      return;
    }
    setShareTarget(target);
    setGenerated(null);
    setShareTtl(settings.shareTtlHours);
    setSharePassphrase('');
  }

  async function generateShare(): Promise<void> {
    if (!key || !shareTarget) return;
    setGenerating(true);
    try {
      const blob = await dbGet<StoredBlob>('blobs', shareTarget.record.id);
      if (!blob) throw new Error('Encrypted payload is missing.');
      const container = JSON.parse(blob.container) as Container;
      const { rawKey } = await loadFileMeta(key, shareTarget.record);
      const { payload, shareRawKey } = await buildShare({
        meta: shareTarget.meta,
        container,
        rawKey,
        passphrase: sharePassphrase || undefined,
      });
      const link = buildShareLink(payload, shareRawKey);
      const bundle = buildShareBundle(payload, shareRawKey);
      const tooLarge = link.length > 900_000;
      const mode = sharePassphrase
        ? 'passphrase'
        : tooLarge
          ? 'bundle'
          : 'link';
      const id = crypto.randomUUID();
      const now = new Date();
      const expiresAt = new Date(now.getTime() + Math.max(1, shareTtl) * 3_600_000);
      await dbPut('shares', {
        id,
        fileId: shareTarget.record.id,
        createdAt: now.toISOString(),
        expiresAt: expiresAt.toISOString(),
        revoked: false,
        mode,
        hasPassphrase: Boolean(sharePassphrase),
        bytes: shareTarget.meta.size,
        label: sharePassphrase ? 'Passphrase-protected share' : 'Capability-link share',
      });
      await recordAudit('share.created', id, `mode=${mode};file=${shareTarget.record.id}`);
      bumpRevision();
      setGenerated({
        link: tooLarge ? '' : link,
        bundle,
        filename: `${shareTarget.meta.name.replace(/\.[^.]+$/, '') || 'cryptavault'}.cvshare.json`,
        mode,
      });
      notify(
        tooLarge
          ? 'Share is too large for a URL. Download the encrypted bundle instead.'
          : 'Share capability created.',
        tooLarge ? 'info' : 'success',
      );
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Could not create share.', 'error');
    } finally {
      setGenerating(false);
    }
  }

  async function doRename(): Promise<void> {
    if (!key || !renameTarget || !renameValue.trim()) return;
    setBusy(true);
    try {
      const nextMeta: FileMeta = { ...renameTarget.meta, name: renameValue.trim() };
      await dbPut('files', {
        ...renameTarget.record,
        meta: await sealJson(key, nextMeta, `filemeta:${renameTarget.record.id}`),
      });
      await recordAudit('file.renamed', renameTarget.record.id);
      bumpRevision();
      notify('File renamed.', 'success');
      setRenameTarget(null);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Rename failed.', 'error');
    } finally {
      setBusy(false);
    }
  }

  async function doDelete(): Promise<void> {
    if (!deleteTarget) return;
    setBusy(true);
    try {
      await deleteFileCascade(deleteTarget.record.id);
      await recordAudit('file.deleted', deleteTarget.record.id);
      bumpRevision();
      notify('Encrypted file and payload deleted.', 'success');
      setDeleteTarget(null);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Delete failed.', 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Encrypted vault"
        title="Files, encrypted before storage"
        description="Each file gets a fresh AES-256-GCM key, is chunked with authenticated boundaries, and is wrapped by your master key. Names, hashes, and manifests are encrypted too."
        action={
          <>
            <button className="btn-secondary" onClick={() => inputRef.current?.click()}>
              <FileUp className="h-4 w-4" /> Choose file
            </button>
            <button className="btn-primary" onClick={() => setUploadOpen(true)}>
              <Upload className="h-4 w-4" /> Upload
            </button>
          </>
        }
      />

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
      />

      <div
        className={classNames(
          'mb-4 flex flex-col items-center justify-center rounded-2xl border border-dashed px-6 py-7 text-center transition-colors',
          dragActive
            ? 'border-cyan-400/60 bg-cyan-500/10'
            : 'border-white/12 bg-white/[0.015]',
        )}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          chooseFile(event.dataTransfer.files?.[0] ?? null);
        }}
      >
        <FolderLock className="mb-2 h-7 w-7 text-cyan-300" />
        <p className="text-sm font-medium text-slate-200">
          Drop a file here, or{' '}
          <button
            className="text-cyan-300 underline-offset-2 hover:underline"
            onClick={() => inputRef.current?.click()}
          >
            browse your device
          </button>
        </p>
        <p className="mt-1 text-[11px] text-slate-500">
          Client-side chunked encryption · max {formatBytes(MAX_FILE_BYTES)} per file in this demo
        </p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9"
            placeholder="Search encrypted files by name or type"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <select
          className="input w-auto"
          value={profileFilter}
          onChange={(event) => setProfileFilter(event.target.value)}
        >
          <option value="ALL">All profiles</option>
          {PROFILES.map((profile) => (
            <option key={profile.level} value={profile.level}>
              {profile.level.replace('_', '-')}
            </option>
          ))}
        </select>
        <select
          className="input w-auto"
          value={sort}
          onChange={(event) => setSort(event.target.value as typeof sort)}
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="name">Name</option>
          <option value="size">Largest</option>
        </select>
      </div>

      {loading ? (
        <div className="card flex items-center justify-center py-16">
          <Spinner label="Decrypting file manifests…" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<FolderLock className="h-8 w-8" />}
          title={files.length === 0 ? 'Your vault is empty' : 'No files match this filter'}
          description={
            files.length === 0
              ? 'Encrypt a file to create its per-file key, chunked ciphertext, and encrypted manifest.'
              : 'Try a different search term or security profile filter.'
          }
          action={
            files.length === 0 ? (
              <button className="btn-primary" onClick={() => inputRef.current?.click()}>
                <Upload className="h-4 w-4" /> Encrypt a file
              </button>
            ) : null
          }
        />
      ) : (
        <div className="card overflow-hidden !p-0">
          <div className="overflow-x-auto scroll-thin">
            <table className="data-table w-full text-left">
              <thead>
                <tr className="border-b border-white/8 bg-white/[0.02]">
                  <th className="px-4 py-3">File</th>
                  <th className="px-4 py-3">Size</th>
                  <th className="px-4 py-3">Profile</th>
                  <th className="px-4 py-3">Chunks</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(({ record, meta: fileMeta }) => (
                  <tr key={record.id} className="border-b border-white/5 last:border-0">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <FileIcon name={fileMeta.name} type={fileMeta.type} size="sm" />
                        <div className="min-w-0">
                          <div className="max-w-[260px] truncate font-medium text-slate-100">
                            {fileMeta.name}
                          </div>
                          <div className="mono text-[10px] text-slate-500">
                            {fileMeta.hash.slice(0, 16)}…
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-300">
                      {formatBytes(fileMeta.size)}
                      <span className="ml-1 text-[10px] text-slate-500">
                        {fileMeta.compression === 'gzip' ? '· gzip' : ''}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        className={
                          getProfile(fileMeta.profile).post_quantum_protected
                            ? 'badge-purple'
                            : 'badge-cyan'
                        }
                      >
                        {fileMeta.profile.replace('_', '-')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-400">{fileMeta.chunkCount}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-400">
                      {relativeTime(fileMeta.createdAt)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          className="btn-ghost !p-2"
                          title="Decrypt and download"
                          onClick={() => void downloadFile({ record, meta: fileMeta })}
                          disabled={downloadingId === record.id}
                        >
                          {downloadingId === record.id ? (
                            <Spinner />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                        </button>
                        <button
                          className="btn-ghost !p-2 disabled:opacity-40"
                          title={
                            settings.sharingEnabled
                              ? 'Create share'
                              : 'Sharing disabled by policy'
                          }
                          onClick={() => openShare({ record, meta: fileMeta })}
                          disabled={!settings.sharingEnabled}
                        >
                          <Share2 className="h-4 w-4" />
                        </button>
                        <button
                          className="btn-ghost !p-2"
                          title="Rename"
                          onClick={() => {
                            setRenameTarget({ record, meta: fileMeta });
                            setRenameValue(fileMeta.name);
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          className="btn-ghost !p-2 text-rose-300 hover:text-rose-200"
                          title="Delete"
                          onClick={() => setDeleteTarget({ record, meta: fileMeta })}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Modal
        open={uploadOpen}
        onClose={() => {
          if (!uploading) {
            setUploadOpen(false);
            setUploadError(null);
          }
        }}
        title="Encrypt a file"
        subtitle="The file is read in this tab, compressed when useful, chunked, and sealed with a fresh key."
        footer={
          <>
            <button
              className="btn-secondary"
              onClick={() => setUploadOpen(false)}
              disabled={uploading}
            >
              Cancel
            </button>
            <button
              className="btn-primary"
              onClick={() => void doUpload()}
              disabled={!uploadFile || uploading}
            >
              {uploading ? <Spinner /> : <ShieldCheck className="h-4 w-4" />}
              {uploading ? 'Encrypting…' : 'Encrypt & store'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          {uploadFile ? (
            <div className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.02] p-3">
              <FileIcon name={uploadFile.name} type={uploadFile.type} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-slate-100">{uploadFile.name}</div>
                <div className="text-[11px] text-slate-500">
                  {formatBytes(uploadFile.size)} · {uploadFile.type || 'unknown type'}
                </div>
              </div>
              {!uploading ? (
                <button
                  className="btn-ghost !p-2"
                  onClick={() => setUploadFile(null)}
                  aria-label="Remove selected file"
                >
                  <X className="h-4 w-4" />
                </button>
              ) : null}
            </div>
          ) : (
            <button
              className="flex w-full flex-col items-center justify-center rounded-xl border border-dashed border-white/12 px-4 py-8 text-center hover:border-cyan-400/40"
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="mb-2 h-6 w-6 text-slate-400" />
              <span className="text-sm text-slate-300">Select a file</span>
            </button>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-slate-300">
                Security profile
              </span>
              <select
                className="input"
                value={uploadProfile}
                onChange={(event) => setUploadProfile(event.target.value as ProfileLevel)}
                disabled={uploading}
              >
                {PROFILES.map((profile) => (
                  <option key={profile.level} value={profile.level}>
                    {profile.level.replace('_', '-')} · {profile.symmetric_cipher}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-slate-300">Compression</span>
              <select
                className="input"
                value={compressMode}
                onChange={(event) => setCompressMode(event.target.value as typeof compressMode)}
                disabled={uploading}
              >
                <option value="auto">Auto (skip pre-compressed)</option>
                <option value="on">Always gzip</option>
                <option value="off">Never compress</option>
              </select>
            </label>
          </div>

          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3 text-[11px] leading-relaxed text-slate-400">
            <div className="mb-1 font-medium text-slate-200">Pipeline</div>
            {getProfile(uploadProfile).symmetric_cipher} · {getProfile(uploadProfile).chunk_size_bytes / (1024 * 1024)} MiB chunks · per-file key wrapped with PBKDF2-derived master key. The manifest (name, type, size, hash) is encrypted separately.
          </div>

          {uploading ? (
            <div className="space-y-2">
              <ProgressBar value={uploadProgress} />
              <div className="text-center text-[11px] text-slate-400">
                Encrypting chunk {Math.round(uploadProgress * 100)}%
              </div>
            </div>
          ) : null}

          {uploadError ? (
            <div className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {uploadError}
            </div>
          ) : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(shareTarget)}
        onClose={() => {
          if (!generating) {
            setShareTarget(null);
            setGenerated(null);
          }
        }}
        title="Create a zero-knowledge share"
        subtitle="The recipient decrypts in their browser. The payload is encrypted with a share key that only the link or bundle carries."
        wide
        footer={
          <>
            <button
              className="btn-secondary"
              onClick={() => {
                setShareTarget(null);
                setGenerated(null);
              }}
              disabled={generating}
            >
              Close
            </button>
            {!generated ? (
              <button className="btn-primary" onClick={() => void generateShare()} disabled={generating}>
                {generating ? <Spinner /> : <Share2 className="h-4 w-4" />}
                {generating ? 'Sealing…' : 'Generate share'}
              </button>
            ) : null}
          </>
        }
      >
        {shareTarget ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.02] p-3">
              <FileIcon name={shareTarget.meta.name} type={shareTarget.meta.type} />
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-100">
                  {shareTarget.meta.name}
                </div>
                <div className="text-[11px] text-slate-500">
                  {formatBytes(shareTarget.meta.size)} · {shareTarget.meta.profile.replace('_', '-')}
                </div>
              </div>
            </div>

            {!generated ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Expires after (hours)
                  </span>
                  <input
                    type="number"
                    min={1}
                    max={720}
                    className="input"
                    value={shareTtl}
                    onChange={(event) => setShareTtl(Number(event.target.value))}
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Passphrase (optional)
                  </span>
                  <input
                    className="input"
                    value={sharePassphrase}
                    onChange={(event) => setSharePassphrase(event.target.value)}
                    placeholder="Recommended for sensitive files"
                    autoComplete="new-password"
                  />
                </label>
                <div className="sm:col-span-2 rounded-xl border border-amber-400/20 bg-amber-500/5 p-3 text-[11px] leading-relaxed text-amber-100/80">
                  A capability link contains the decryption key in its URL fragment. Anyone with
                  the link can decrypt the shared copy. Add a passphrase to require a second
                  secret. Share records in this portal are local bookkeeping; revocation cannot
                  invalidate a link that was already copied.
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div
                  className={classNames(
                    'rounded-xl border p-3 text-xs',
                    generated.mode === 'bundle'
                      ? 'border-amber-400/25 bg-amber-500/5 text-amber-100'
                      : 'border-emerald-400/25 bg-emerald-500/5 text-emerald-100',
                  )}
                >
                  {generated.mode === 'bundle'
                    ? 'This share exceeds a practical URL size. Download the encrypted bundle and send it through your normal channel.'
                    : 'Share generated. The link is self-contained and decrypts entirely in the recipient browser.'}
                </div>

                {generated.link ? (
                  <div>
                    <div className="mb-1.5 text-xs font-medium text-slate-300">Share link</div>
                    <div className="flex items-start gap-2">
                      <textarea
                        readOnly
                        className="input mono !text-[10px]"
                        rows={4}
                        value={generated.link}
                      />
                      <CopyButton value={generated.link} />
                    </div>
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  <button
                    className="btn-secondary"
                    onClick={() =>
                      downloadText(generated.bundle, generated.filename, 'application/json')
                    }
                  >
                    <Download className="h-4 w-4" /> Download encrypted bundle
                  </button>
                  <CopyButton value={generated.bundle} label="Copy bundle JSON" />
                </div>
                <p className="text-[11px] text-slate-500">
                  Recipients open the link in this portal or import the bundle from the share
                  screen. The bundle is already ciphertext; it still carries the capability key
                  when no passphrase was used.
                </p>
              </div>
            )}
          </div>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(renameTarget)}
        onClose={() => setRenameTarget(null)}
        title="Rename encrypted file"
        subtitle="Only the encrypted manifest is rewritten. The payload ciphertext is unchanged."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setRenameTarget(null)}>
              Cancel
            </button>
            <button className="btn-primary" onClick={() => void doRename()} disabled={busy}>
              Save name
            </button>
          </>
        }
      >
        <input
          className="input"
          value={renameValue}
          onChange={(event) => setRenameValue(event.target.value)}
          autoFocus
        />
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Delete encrypted file?"
        subtitle="This removes the ciphertext payload, wrapped file key, and encrypted manifest from this browser."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setDeleteTarget(null)}>
              Cancel
            </button>
            <button className="btn-danger" onClick={() => void doDelete()} disabled={busy}>
              <Trash2 className="h-4 w-4" /> Delete file
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-300">
          {deleteTarget ? deleteTarget.meta.name : ''} will no longer be downloadable. Existing
          share links you already distributed are unaffected.
        </p>
      </Modal>
    </div>
  );
}
