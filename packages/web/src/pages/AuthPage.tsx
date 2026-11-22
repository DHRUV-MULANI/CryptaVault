import { useMemo, useState } from 'react';
import { AlertTriangle, Check, Eye, EyeOff, Fingerprint, KeyRound, LockKeyhole, LogIn, ShieldCheck, Sparkles } from 'lucide-react';
import { PROFILES } from '../lib/profiles';
import type { ProfileLevel } from '../lib/types';
import { passwordStrength } from '../lib/crypto';
import { useVault } from '../lib/vault';
import { Spinner } from '../components/ui';
import { classNames } from '../lib/format';

const FEATURES = [
  'AES-256-GCM client-side encryption with per-file keys',
  'PBKDF2-SHA256 master-key derivation (keys never leave this tab)',
  'Dynamic API + Neon metadata + S3-compatible ciphertext storage',
  'Server-enforced shares, roles, quotas, and workspace policies',
  '88-algorithm catalog and adaptive security profiles',
];

export default function AuthPage(): JSX.Element {
  const { status, user, login, register, unlock } = useVault();
  const locked = status === 'locked';
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState(user?.email ?? '');
  const [displayName, setDisplayName] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [confirm, setConfirm] = useState('');
  const [profile, setProfile] = useState<ProfileLevel>('BALANCED');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const creating = !locked && mode === 'register';
  const strength = useMemo(() => passwordStrength(passphrase), [passphrase]);
  const match = confirm.length > 0 && passphrase === confirm;
  const canSubmit = locked
    ? passphrase.length > 0 && !busy
    : creating
      ? email.includes('@') && passphrase.length >= 10 && match && !busy
      : email.includes('@') && passphrase.length > 0 && !busy;

  async function onSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (locked) {
        await unlock(passphrase);
      } else if (creating) {
        await register(email, passphrase, displayName, profile);
      } else {
        await login(email, passphrase);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden border-r border-white/8 px-10 py-12 lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-glow">
              <ShieldCheck className="h-6 w-6" />
            </span>
            <div>
              <div className="text-lg font-semibold tracking-tight text-white">CryptaVault</div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-500">Dynamic zero-knowledge framework</div>
            </div>
          </div>
          <h1 className="mt-12 max-w-xl text-4xl font-semibold leading-[1.1] tracking-tight text-white xl:text-5xl">
            Encrypt on the client. Coordinate on the server.
          </h1>
          <p className="mt-5 max-w-xl text-sm leading-relaxed text-slate-400">
            CryptaVault keeps plaintext and master keys in the browser/CLI. The API manages users, workspaces, roles, shares, quotas, and ciphertext objects only.
          </p>
          <ul className="mt-8 space-y-3">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-3 text-sm text-slate-300">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/12 text-emerald-300"><Check className="h-3 w-3" /></span>
                {feature}
              </li>
            ))}
          </ul>
        </div>
        <div className="relative grid grid-cols-3 gap-3">
          {[{ label: 'Algorithms', value: '88' }, { label: 'Profiles', value: '6' }, { label: 'Zero-knowledge', value: '100%' }].map((item) => (
            <div key={item.label} className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
              <div className="text-2xl font-semibold text-white">{item.value}</div>
              <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-slate-500">{item.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="card p-6 sm:p-7">
            <div className="mb-6">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-medium text-cyan-200">
                {locked ? <LockKeyhole className="h-3.5 w-3.5" /> : creating ? <Sparkles className="h-3.5 w-3.5" /> : <LogIn className="h-3.5 w-3.5" />}
                {locked ? 'Session locked' : creating ? 'Create account' : 'Sign in'}
              </div>
              <h2 className="text-xl font-semibold tracking-tight text-white">
                {locked ? 'Unlock your session' : creating ? 'Create your dynamic vault account' : 'Sign in to CryptaVault'}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                {locked
                  ? 'Your JWT session exists, but the master key is memory-only. Re-enter your passphrase to derive it locally.'
                  : creating
                    ? 'Your passphrase derives auth and vault keys locally. The server only receives verifiers, salts, and encrypted checks.'
                    : 'Sign in with your email and passphrase. The passphrase is used locally to derive keys.'}
              </p>
            </div>

            {!locked && (
              <div className="mb-4 grid grid-cols-2 gap-2 rounded-xl bg-white/[0.03] p-1">
                {(['login', 'register'] as const).map((m) => (
                  <button key={m} type="button" onClick={() => setMode(m)} className={classNames('rounded-lg px-3 py-2 text-sm', mode === m ? 'bg-cyan-500/15 text-cyan-100' : 'text-slate-400 hover:text-slate-200')}>
                    {m === 'login' ? 'Login' : 'Register'}
                  </button>
                ))}
              </div>
            )}

            <form className="space-y-4" onSubmit={onSubmit}>
              {!locked && (
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">Email</span>
                  <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" />
                </label>
              )}
              {locked && (
                <div className="rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3 text-xs text-slate-400">
                  Signed in as <span className="font-medium text-slate-200">{user?.email ?? 'user'}</span>
                </div>
              )}
              {creating && (
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">Display name</span>
                  <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Your name" autoComplete="name" />
                </label>
              )}
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">Passphrase</span>
                <div className="relative">
                  <input className="input pr-11" type={show ? 'text' : 'password'} value={passphrase} onChange={(e) => setPassphrase(e.target.value)} placeholder={creating ? 'At least 10 characters' : 'Enter passphrase'} autoComplete={creating ? 'new-password' : 'current-password'} autoFocus />
                  <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-slate-400 hover:text-slate-200" onClick={() => setShow((v) => !v)} aria-label={show ? 'Hide passphrase' : 'Show passphrase'}>
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {creating && passphrase ? (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex flex-1 gap-1">{[0,1,2,3,4].map((i) => <span key={i} className={classNames('h-1.5 flex-1 rounded-full', i < strength.score ? (strength.score <= 2 ? 'bg-amber-400' : strength.score === 3 ? 'bg-yellow-300' : 'bg-emerald-400') : 'bg-white/10')} />)}</div>
                    <span className={classNames('text-[11px] font-medium', strength.tone)}>{strength.label}</span>
                  </div>
                ) : null}
              </label>
              {creating && (
                <>
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-medium text-slate-300">Confirm passphrase</span>
                    <input className="input" type={show ? 'text' : 'password'} value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Repeat passphrase" autoComplete="new-password" />
                    {confirm && !match ? <span className="mt-1.5 block text-xs text-rose-300">Passphrases do not match.</span> : null}
                  </label>
                  <div>
                    <span className="mb-2 block text-xs font-medium text-slate-300">Default security profile</span>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {PROFILES.map((item) => (
                        <button key={item.level} type="button" onClick={() => setProfile(item.level)} className={classNames('rounded-xl border px-3 py-2.5 text-left transition-colors', profile === item.level ? 'border-cyan-400/40 bg-cyan-500/10' : 'border-white/8 bg-white/[0.02] hover:border-white/15')}>
                          <span className="text-xs font-semibold text-white">{item.level.replace('_', '-')}</span>
                          <span className="mt-0.5 block text-[10px] leading-snug text-slate-500">{item.slider_band[0]}–{item.slider_band[1]}%</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {error ? <div className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-200"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div> : null}

              <button type="submit" disabled={!canSubmit} className="btn-primary w-full justify-center disabled:cursor-not-allowed disabled:opacity-50">
                {busy ? <Spinner /> : locked ? <><KeyRound className="h-4 w-4" /> Unlock</> : creating ? <><Fingerprint className="h-4 w-4" /> Create account</> : <><LogIn className="h-4 w-4" /> Sign in</>}
              </button>
            </form>
          </div>
          <p className="mt-5 text-center text-[11px] leading-relaxed text-slate-500">
            Dynamic dev mode · API {import.meta.env.VITE_API_URL || 'same origin (/api proxy)'} · keys derived locally.
          </p>
        </div>
      </section>
    </div>
  );
}