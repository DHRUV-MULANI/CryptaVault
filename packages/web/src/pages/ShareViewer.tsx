import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, ArrowLeft, Check, Download, FileUp, LockKeyhole, ShieldCheck } from 'lucide-react';
import { api } from '../lib/api';
import { b64UrlToBytes, decryptContainer, decryptShare, parseShareBundle, readShareFromLocation, type ParsedShare } from '../lib/crypto';
import { downloadBlob, formatBytes } from '../lib/format';
import { Card, ProgressBar, Spinner } from '../components/ui';

const BUNDLE_KEY = 'cryptavault_open_bundle';

function getServerShareFromHash(): { token: string; keyB64Url: string | null } | null {
  const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash;
  const [path, query = ''] = hash.split('?');
  const m = path.match(/^\/s\/([^/]+)/);
  if (!m) return null;
  const params = new URLSearchParams(query);
  return { token: m[1], keyB64Url: params.get('k') };
}

export default function ShareViewer(): JSX.Element {
  const [parsed, setParsed] = useState<ParsedShare | null>(null);
  const [serverShare, setServerShare] = useState<{ token: string; keyB64Url: string | null } | null>(null);
  const [serverInfo, setServerInfo] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [passphrase, setPassphrase] = useState('');
  const [sharePassword, setSharePassword] = useState('');
  const [sharePin, setSharePin] = useState('');
  const [decrypting, setDecrypting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [done, setDone] = useState<{ name: string; size: number } | null>(null);
  const [importing, setImporting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fromLocation = readShareFromLocation();
    if (fromLocation) { setParsed(fromLocation); return; }
    const srv = getServerShareFromHash();
    if (srv) {
      setServerShare(srv);
      void api.shares.info(srv.token).then(setServerInfo).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load share'));
      return;
    }
    const stored = sessionStorage.getItem(BUNDLE_KEY);
    if (stored) {
      try { setParsed(parseShareBundle(stored)); } catch (err) { setError(err instanceof Error ? err.message : 'Could not read share bundle.'); }
    }
  }, []);

  const needsPassphrase = parsed?.payload.kdf === 'pbkdf2';
  const needsServerPassword = Boolean(serverInfo?.password_protected);
  const needsServerPin = Boolean(serverInfo?.pin_required);

  async function decryptLegacy() {
    if (!parsed) return;
    setDecrypting(true); setError(null); setProgress(0);
    try {
      const plaintext = await decryptShare(parsed, passphrase || undefined, setProgress);
      downloadBlob(plaintext, parsed.payload.name, parsed.payload.type || 'application/octet-stream');
      setDone({ name: parsed.payload.name, size: plaintext.length });
      sessionStorage.removeItem(BUNDLE_KEY);
    } catch (err) { setError(err instanceof Error ? err.message : 'Decryption failed.'); }
    finally { setDecrypting(false); }
  }

  async function decryptServerShare() {
    if (!serverShare) return;
    if (!serverShare.keyB64Url) { setError('This server share link is missing the key fragment (#k=...). Ask the sender for the full link.'); return; }
    setDecrypting(true); setError(null); setProgress(0);
    try {
      const bytes = await api.shares.download(
        serverShare.token,
        needsServerPassword ? sharePassword : undefined,
        needsServerPin ? sharePin : undefined,
      );
      const container = JSON.parse(new TextDecoder().decode(bytes));
      const rawKey = b64UrlToBytes(serverShare.keyB64Url);
      const plaintext = await decryptContainer(container, rawKey, setProgress);
      const name = String(serverInfo?.file_id ?? 'shared-file') + '.bin';
      // If container/meta had name we'd use it; server share info doesn't include decrypted name. Use generic.
      downloadBlob(plaintext, name, 'application/octet-stream');
      setDone({ name, size: plaintext.length });
    } catch (err) { setError(err instanceof Error ? err.message : 'Download/decrypt failed.'); }
    finally { setDecrypting(false); }
  }

  async function importBundle(file: File) {
    setImporting(true); setError(null);
    try {
      const text = await file.text();
      const next = parseShareBundle(text);
      sessionStorage.setItem(BUNDLE_KEY, text);
      setParsed(next); setServerShare(null); setServerInfo(null); setDone(null); setProgress(0);
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not read bundle.'); }
    finally { setImporting(false); }
  }

  const hasShare = Boolean(parsed || serverShare);

  return (
    <div className="mx-auto min-h-screen w-full max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <a href={import.meta.env.BASE_URL} className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950"><ShieldCheck className="h-5 w-5" /></span>
          <span><span className="block text-sm font-semibold text-white">CryptaVault</span><span className="block text-[10px] uppercase tracking-[0.2em] text-slate-500">Share viewer</span></span>
        </a>
        <a href={import.meta.env.BASE_URL} className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Portal</a>
      </div>

      <div className="card p-6 sm:p-8">
        <div className="mb-5">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-medium text-cyan-200"><LockKeyhole className="h-3.5 w-3.5" /> Zero-knowledge share</div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">{hasShare ? 'Decrypt shared file' : 'Open an encrypted share'}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">Decryption happens in this tab. Server shares use API access control + revocation, while the key stays in the URL fragment.</p>
        </div>

        {!hasShare ? (
          <div className="space-y-4">
            <input ref={inputRef} type="file" accept=".json,.cvshare,application/json" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void importBundle(f); e.target.value = ''; }} />
            <button className="flex w-full flex-col items-center justify-center rounded-2xl border border-dashed border-white/12 px-6 py-14 text-center transition-colors hover:border-cyan-400/40 hover:bg-cyan-500/5" onClick={() => inputRef.current?.click()}>
              {importing ? <Spinner label="Reading bundle…" /> : <><FileUp className="mb-3 h-9 w-9 text-cyan-300" /><span className="text-sm font-medium text-slate-200">Choose a .cvshare.json bundle</span><span className="mt-1 text-[11px] text-slate-500">Or open a server share link with #k= fragment.</span></>}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {serverShare && (
              <Card className="!p-4">
                <div className="text-sm font-medium text-white">Server share</div>
                <div className="mt-1 text-xs text-slate-400">Token: <span className="mono">{serverShare.token.slice(0, 16)}…</span></div>
                {serverInfo && <div className="mt-2 grid gap-2 sm:grid-cols-2 text-[11px] text-slate-400">
                  <div>Password: {serverInfo.password_protected ? 'required' : 'none'}</div>
                  <div>PIN: {serverInfo.pin_protected ? (serverInfo.pin_required ? 'required' : 'not required for you') : 'none'}</div>
                  <div>Remaining uses: {String(serverInfo.remaining_uses ?? '—')}</div>
                  <div>Ciphertext: {formatBytes(Number(serverInfo.ciphertext_size ?? 0))}</div>
                  {serverInfo.recipient_email ? <div className="sm:col-span-2">Recipient: {String(serverInfo.recipient_email)} {serverInfo.recipient_match ? '(you — PIN bypassed)' : ''}</div> : null}
                </div>}
                {!serverShare.keyB64Url && <div className="mt-2 text-xs text-amber-200">Missing key fragment. The full link must include `#...?...&k=...`.</div>}
                {needsServerPassword && <label className="mt-3 block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Share password</span><input className="input" type="password" value={sharePassword} onChange={(e) => setSharePassword(e.target.value)} /></label>}
                {needsServerPin && <label className="mt-3 block"><span className="mb-1.5 block text-xs font-medium text-slate-300">8-digit access PIN</span><input className="input font-mono tracking-widest" inputMode="numeric" maxLength={8} value={sharePin} onChange={(e) => setSharePin(e.target.value.replace(/\D/g, '').slice(0, 8))} placeholder="Enter 8-digit PIN" /></label>}
              </Card>
            )}

            {parsed && (
              <Card className="!p-4">
                <div className="text-sm font-medium text-white">{parsed.payload.name}</div>
                <div className="mt-1 text-xs text-slate-400">{formatBytes(parsed.payload.size)} · {parsed.payload.profile.replace('_', '-')}</div>
                {needsPassphrase && <label className="mt-3 block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Share passphrase</span><input className="input" type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} /></label>}
              </Card>
            )}

            {decrypting && <div className="space-y-2"><ProgressBar value={progress} /><div className="text-center text-[11px] text-slate-400">Decrypting {Math.round(progress * 100)}%</div></div>}
            {error && <div className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-200"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
            {done && <div className="flex items-start gap-2 rounded-xl border border-emerald-400/25 bg-emerald-500/10 px-3 py-2.5 text-xs text-emerald-100"><Check className="mt-0.5 h-4 w-4 shrink-0" />Downloaded and decrypted: {done.name} ({formatBytes(done.size)}).</div>}

            <div className="flex flex-wrap gap-2">
              {parsed && <button className="btn-primary" onClick={() => void decryptLegacy()} disabled={decrypting || (needsPassphrase && !passphrase)}>{decrypting ? <Spinner /> : <Download className="h-4 w-4" />} Decrypt & download</button>}
              {serverShare && <button className="btn-primary" onClick={() => void decryptServerShare()} disabled={decrypting || (needsServerPassword && !sharePassword) || (needsServerPin && sharePin.length !== 8)}>{decrypting ? <Spinner /> : <Download className="h-4 w-4" />} Download & decrypt</button>}
              <button className="btn-secondary" onClick={() => { sessionStorage.removeItem(BUNDLE_KEY); window.location.hash = '#/share'; window.location.reload(); }}>Open another</button>
            </div>
          </div>
        )}
      </div>

      <Card className="mt-4 !p-4"><div className="text-[11px] leading-relaxed text-slate-500"><span className="font-medium text-slate-300">Security note:</span> Server shares enforce revocation, expiry, and max uses on ciphertext download. The decryption key is carried in the URL fragment and is not sent to the API by this viewer.</div></Card>
    </div>
  );
}
