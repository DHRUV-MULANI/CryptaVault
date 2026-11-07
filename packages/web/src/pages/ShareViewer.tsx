import { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Download,
  FileUp,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
} from 'lucide-react';
import {
  decryptShare,
  parseShareBundle,
  readShareFromLocation,
  type ParsedShare,
} from '../lib/crypto';
import {
  downloadBlob,
  formatBytes,
  formatDate,
} from '../lib/format';
import { Card, ProgressBar, Spinner } from '../components/ui';
import FileIcon from '../components/FileIcon';

const BUNDLE_KEY = 'cryptavault_open_bundle';

export default function ShareViewer(): JSX.Element {
  const [parsed, setParsed] = useState<ParsedShare | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [passphrase, setPassphrase] = useState('');
  const [decrypting, setDecrypting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [done, setDone] = useState<{ name: string; size: number } | null>(null);
  const [importing, setImporting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fromLocation = readShareFromLocation();
    if (fromLocation) {
      setParsed(fromLocation);
      return;
    }
    const stored = sessionStorage.getItem(BUNDLE_KEY);
    if (stored) {
      try {
        setParsed(parseShareBundle(stored));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not read the share bundle.');
      }
    }
  }, []);

  const needsPassphrase = parsed?.payload.kdf === 'pbkdf2';

  async function decrypt(): Promise<void> {
    if (!parsed) return;
    setDecrypting(true);
    setError(null);
    setProgress(0);
    try {
      const plaintext = await decryptShare(parsed, passphrase || undefined, setProgress);
      downloadBlob(
        plaintext,
        parsed.payload.name,
        parsed.payload.type || 'application/octet-stream',
      );
      setDone({ name: parsed.payload.name, size: plaintext.length });
      sessionStorage.removeItem(BUNDLE_KEY);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Decryption failed. The link may be corrupt or the passphrase may be wrong.',
      );
    } finally {
      setDecrypting(false);
    }
  }

  async function importBundle(file: File): Promise<void> {
    setImporting(true);
    setError(null);
    try {
      const text = await file.text();
      const next = parseShareBundle(text);
      sessionStorage.setItem(BUNDLE_KEY, text);
      setParsed(next);
      setDone(null);
      setProgress(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read bundle.');
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="mx-auto min-h-screen w-full max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <a href={import.meta.env.BASE_URL} className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-sm font-semibold text-white">CryptaVault</span>
            <span className="block text-[10px] uppercase tracking-[0.2em] text-slate-500">
              Share viewer
            </span>
          </span>
        </a>
        <a href={import.meta.env.BASE_URL} className="btn-ghost">
          <ArrowLeft className="h-4 w-4" /> Portal
        </a>
      </div>

      <div className="card p-6 sm:p-8">
        <div className="mb-5">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-medium text-cyan-200">
            <LockKeyhole className="h-3.5 w-3.5" /> Zero-knowledge share
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">
            {parsed ? 'Decrypt this shared file' : 'Open an encrypted share'}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
            Decryption happens in this tab. Nothing is uploaded, no account is required, and the
            key stays in the URL fragment or in the bundle you opened.
          </p>
        </div>

        {!parsed ? (
          <div className="space-y-4">
            <input
              ref={inputRef}
              type="file"
              accept=".json,.cvshare,application/json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void importBundle(file);
                event.target.value = '';
              }}
            />
            <button
              className="flex w-full flex-col items-center justify-center rounded-2xl border border-dashed border-white/12 px-6 py-14 text-center transition-colors hover:border-cyan-400/40 hover:bg-cyan-500/5"
              onClick={() => inputRef.current?.click()}
            >
              {importing ? (
                <Spinner label="Reading bundle…" />
              ) : (
                <>
                  <FileUp className="mb-3 h-9 w-9 text-cyan-300" />
                  <span className="text-sm font-medium text-slate-200">
                    Choose a .cvshare.json bundle
                  </span>
                  <span className="mt-1 text-[11px] text-slate-500">
                    You can also open a self-contained share link directly.
                  </span>
                </>
              )}
            </button>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ['1', 'Open the link or bundle', 'The ciphertext is read locally.'],
                ['2', 'Unlock with the share secret', 'A passphrase, or the key in the link.'],
                ['3', 'Download and verify', 'SHA-256 integrity is checked before download.'],
              ].map(([step, title, body]) => (
                <div key={step} className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
                  <div className="mono text-xs text-cyan-300">0{step}</div>
                  <div className="mt-1 text-xs font-medium text-slate-200">{title}</div>
                  <div className="mt-1 text-[11px] text-slate-500">{body}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-[1.25fr_1fr]">
            <div className="space-y-4">
              <div className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.02] p-4">
                <FileIcon name={parsed.payload.name} type={parsed.payload.type} size="lg" />
                <div className="min-w-0">
                  <div className="truncate text-base font-semibold text-white">
                    {parsed.payload.name}
                  </div>
                  <div className="mt-1 text-xs text-slate-400">
                    {formatBytes(parsed.payload.size)} · {parsed.payload.profile.replace('_', '-')} ·{' '}
                    {parsed.payload.chunkCount} chunks
                  </div>
                  <div className="mt-1 text-[10px] text-slate-500">
                    Created {formatDate(parsed.payload.createdAt)} ·{' '}
                    {parsed.payload.compression === 'gzip' ? 'gzip compressed' : 'no compression'}
                  </div>
                </div>
              </div>

              {needsPassphrase ? (
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Share passphrase
                  </span>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input
                      className="input pl-9"
                      type="password"
                      value={passphrase}
                      onChange={(event) => setPassphrase(event.target.value)}
                      placeholder="Enter the passphrase from the sender"
                      autoComplete="off"
                      autoFocus
                    />
                  </div>
                </label>
              ) : (
                <div className="flex items-start gap-2 rounded-xl border border-cyan-400/20 bg-cyan-500/5 p-3 text-[11px] leading-relaxed text-cyan-100">
                  <KeyRound className="mt-0.5 h-4 w-4 shrink-0" />
                  This link contains its capability key. Anyone who has the full link can decrypt
                  this shared copy.
                </div>
              )}

              {decrypting ? (
                <div className="space-y-2">
                  <ProgressBar value={progress} />
                  <div className="text-center text-[11px] text-slate-400">
                    Decrypting chunk {Math.round(progress * 100)}%
                  </div>
                </div>
              ) : null}

              {error ? (
                <div className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  {error}
                </div>
              ) : null}

              {done ? (
                <div className="flex items-start gap-2 rounded-xl border border-emerald-400/25 bg-emerald-500/10 px-3 py-2.5 text-xs text-emerald-100">
                  <Check className="mt-0.5 h-4 w-4 shrink-0" />
                  Integrity verified and downloaded: {done.name} ({formatBytes(done.size)}).
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <button
                  className="btn-primary"
                  onClick={() => void decrypt()}
                  disabled={decrypting || (needsPassphrase && passphrase.length === 0)}
                >
                  {decrypting ? <Spinner /> : <Download className="h-4 w-4" />}
                  {decrypting ? 'Decrypting…' : 'Decrypt & download'}
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    sessionStorage.removeItem(BUNDLE_KEY);
                    window.location.href = `${import.meta.env.BASE_URL}#/share`;
                    window.location.reload();
                  }}
                >
                  Open another
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
              <div className="mb-2 text-xs font-semibold text-slate-200">What this viewer can see</div>
              <ul className="space-y-2 text-[11px] leading-relaxed text-slate-400">
                <li>File name, size, hash, and profile from the encrypted share manifest.</li>
                <li>The AES-GCM chunk ciphertext and its wrapped per-file key.</li>
                <li>No plaintext leaves this tab; the download is created with a blob URL.</li>
                <li>Integrity is verified against the SHA-256 digest before the file is saved.</li>
              </ul>
              <div className="mt-4 border-t border-white/8 pt-3">
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                  Container magic
                </div>
                <div className="mono mt-1 text-xs text-cyan-300">CVW1 · chunked AEAD</div>
              </div>
              <div className="mt-3">
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                  KDF mode
                </div>
                <div className="mono mt-1 text-xs text-slate-300">
                  {parsed.payload.kdf === 'pbkdf2'
                    ? `PBKDF2-SHA256 · ${(parsed.payload.iterations ?? 210000).toLocaleString()} iterations`
                    : 'Raw capability key (link fragment)'}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-white/8 pt-4 text-[11px] text-slate-500">
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" /> Client-side decryption
          </span>
          <span>Static deployment · no telemetry</span>
        </div>
      </div>

      <Card className="mt-4 !p-4">
        <div className="text-[11px] leading-relaxed text-slate-500">
          <span className="font-medium text-slate-300">Security note:</span> expiry and revocation
          are not cryptographically enforceable for self-contained shares without a server. Treat
          the link or bundle as the capability: delete the source, rotate the passphrase, or stop
          distributing it if it leaks.
        </div>
      </Card>
    </div>
  );
}
