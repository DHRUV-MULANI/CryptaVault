import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Check,
  Eye,
  EyeOff,
  Fingerprint,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { PROFILES } from '../lib/profiles';
import type { ProfileLevel } from '../lib/types';
import { passwordStrength } from '../lib/crypto';
import { useVault } from '../lib/vault';
import { Modal, Spinner, useToast } from '../components/ui';
import { classNames } from '../lib/format';

const FEATURES = [
  'AES-256-GCM chunked encryption with per-file keys',
  'PBKDF2-SHA256 (210,000 iterations) master-key derivation',
  'Persistent encrypted vault in this browser (IndexedDB)',
  'Self-contained capability links with optional passphrases',
  'Real crypto-agility catalog with 88 algorithms across 9 families',
];

export default function AuthPage(): JSX.Element {
  const { status, createVault, unlock, wipe, meta } = useVault();
  const { notify } = useToast();
  const creating = status === 'empty';
  const [displayName, setDisplayName] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [confirm, setConfirm] = useState('');
  const [profile, setProfile] = useState<ProfileLevel>('BALANCED');
  const [accepted, setAccepted] = useState(false);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmWipe, setConfirmWipe] = useState(false);

  const strength = useMemo(() => passwordStrength(passphrase), [passphrase]);
  const match = confirm.length > 0 && passphrase === confirm;
  const canSubmit = creating
    ? passphrase.length >= 10 && match && accepted && !busy
    : passphrase.length > 0 && !busy;

  async function onSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (creating) {
        await createVault(passphrase, displayName, profile);
        notify('Vault created. Your keys stay in this browser.', 'success');
      } else {
        await unlock(passphrase);
        notify('Vault unlocked.', 'success');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden border-r border-white/8 px-10 py-12 lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-10 bottom-0 h-80 w-80 rounded-full bg-purple-500/10 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-glow">
              <ShieldCheck className="h-6 w-6" />
            </span>
            <div>
              <div className="text-lg font-semibold tracking-tight text-white">CryptaVault</div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-500">
                Zero-knowledge storage
              </div>
            </div>
          </div>
          <h1 className="mt-12 max-w-xl text-4xl font-semibold leading-[1.1] tracking-tight text-white xl:text-5xl">
            Your files are encrypted before they leave this tab.
          </h1>
          <p className="mt-5 max-w-xl text-sm leading-relaxed text-slate-400">
            CryptaVault is an adaptive, crypto-agile storage portal. The browser derives your
            master key, wraps every file key, and stores only ciphertext. No account, backend, or
            telemetry is required for this local deployment.
          </p>
          <ul className="mt-8 space-y-3">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-3 text-sm text-slate-300">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/12 text-emerald-300">
                  <Check className="h-3 w-3" />
                </span>
                {feature}
              </li>
            ))}
          </ul>
        </div>
        <div className="relative grid grid-cols-3 gap-3">
          {[
            { label: 'Algorithms', value: '88' },
            { label: 'Profiles', value: '6' },
            { label: 'Client-side', value: '100%' },
          ].map((item) => (
            <div key={item.label} className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
              <div className="text-2xl font-semibold text-white">{item.value}</div>
              <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-slate-500">
                {item.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <div>
              <div className="text-base font-semibold text-white">CryptaVault</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Zero-knowledge storage
              </div>
            </div>
          </div>

          <div className="card p-6 sm:p-7">
            <div className="mb-6">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-medium text-cyan-200">
                {creating ? <Sparkles className="h-3.5 w-3.5" /> : <LockKeyhole className="h-3.5 w-3.5" />}
                {creating ? 'Create your local vault' : 'Vault locked'}
              </div>
              <h2 className="text-xl font-semibold tracking-tight text-white">
                {creating ? 'Set a master passphrase' : 'Unlock with your passphrase'}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                {creating
                  ? 'This passphrase derives the key that protects every file. It is never stored or transmitted. There is no recovery if you forget it.'
                  : 'Your encrypted vault is stored in this browser. The passphrase is required to derive the unwrapping key.'}
              </p>
            </div>

            <form className="space-y-4" onSubmit={onSubmit}>
              {creating ? (
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Vault display name
                  </span>
                  <input
                    className="input"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="e.g. Research archive"
                    autoComplete="off"
                  />
                </label>
              ) : null}

              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Master passphrase
                </span>
                <div className="relative">
                  <input
                    className="input pr-11"
                    type={show ? 'text' : 'password'}
                    value={passphrase}
                    onChange={(event) => setPassphrase(event.target.value)}
                    placeholder={creating ? 'At least 10 characters' : 'Enter passphrase'}
                    autoComplete={creating ? 'new-password' : 'current-password'}
                    autoFocus
                  />
                  <button
                    type="button"
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-slate-400 hover:text-slate-200"
                    onClick={() => setShow((value) => !value)}
                    aria-label={show ? 'Hide passphrase' : 'Show passphrase'}
                  >
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {creating && passphrase ? (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex flex-1 gap-1">
                      {[0, 1, 2, 3, 4].map((index) => (
                        <span
                          key={index}
                          className={classNames(
                            'h-1.5 flex-1 rounded-full',
                            index < strength.score
                              ? strength.score <= 2
                                ? 'bg-amber-400'
                                : strength.score === 3
                                  ? 'bg-yellow-300'
                                  : 'bg-emerald-400'
                              : 'bg-white/10',
                          )}
                        />
                      ))}
                    </div>
                    <span className={classNames('text-[11px] font-medium', strength.tone)}>
                      {strength.label}
                    </span>
                  </div>
                ) : null}
              </label>

              {creating ? (
                <>
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-medium text-slate-300">
                      Confirm passphrase
                    </span>
                    <input
                      className="input"
                      type={show ? 'text' : 'password'}
                      value={confirm}
                      onChange={(event) => setConfirm(event.target.value)}
                      placeholder="Repeat passphrase"
                      autoComplete="new-password"
                    />
                    {confirm && !match ? (
                      <span className="mt-1.5 block text-xs text-rose-300">
                        Passphrases do not match.
                      </span>
                    ) : null}
                  </label>

                  <div>
                    <span className="mb-2 block text-xs font-medium text-slate-300">
                      Default security profile
                    </span>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {PROFILES.map((item) => (
                        <button
                          key={item.level}
                          type="button"
                          onClick={() => setProfile(item.level)}
                          className={classNames(
                            'rounded-xl border px-3 py-2.5 text-left transition-colors',
                            profile === item.level
                              ? 'border-cyan-400/40 bg-cyan-500/10'
                              : 'border-white/8 bg-white/[0.02] hover:border-white/15',
                          )}
                        >
                          <span className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-white">
                              {item.level.replace('_', '-')}
                            </span>
                            {item.post_quantum_protected ? (
                              <span className="text-[9px] font-semibold uppercase tracking-wider text-purple-300">
                                PQ
                              </span>
                            ) : null}
                          </span>
                          <span className="mt-0.5 block text-[10px] leading-snug text-slate-500">
                            {item.slider_band[0]}–{item.slider_band[1]}%
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-amber-400/20 bg-amber-500/5 p-3">
                    <input
                      type="checkbox"
                      checked={accepted}
                      onChange={(event) => setAccepted(event.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-cyan-400"
                    />
                    <span className="text-xs leading-relaxed text-amber-100/80">
                      I understand this deployment stores the encrypted vault in this browser. If I
                      clear site data or forget the passphrase, the files cannot be recovered.
                    </span>
                  </label>
                </>
              ) : (
                <div className="rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3 text-xs text-slate-400">
                  {meta ? (
                    <>
                      Vault <span className="font-medium text-slate-200">{meta.settings.displayName}</span>{' '}
                      · created {new Date(meta.createdAt).toLocaleDateString()} · PBKDF2-
                      {meta.iterations.toLocaleString()} rounds
                    </>
                  ) : (
                    'Local encrypted vault'
                  )}
                </div>
              )}

              {error ? (
                <div className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={!canSubmit}
                className="btn-primary w-full justify-center disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? (
                  <Spinner />
                ) : creating ? (
                  <>
                    <Fingerprint className="h-4 w-4" /> Create encrypted vault
                  </>
                ) : (
                  <>
                    <KeyRound className="h-4 w-4" /> Unlock vault
                  </>
                )}
              </button>
            </form>

            {!creating ? (
              <button
                className="mt-4 inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-rose-300"
                onClick={() => setConfirmWipe(true)}
              >
                <Trash2 className="h-3.5 w-3.5" /> Delete this local vault
              </button>
            ) : null}
          </div>

          <p className="mt-5 text-center text-[11px] leading-relaxed text-slate-500">
            Static deployment · no account or server required. See the{' '}
            <a
              className="text-cyan-300 hover:underline"
              href="https://github.com/DHRUV-MULANI/CryptaVault#readme"
              target="_blank"
              rel="noreferrer"
            >
              README
            </a>{' '}
            for security boundaries and production deployment.
          </p>
        </div>
      </section>

      <Modal
        open={confirmWipe}
        onClose={() => setConfirmWipe(false)}
        title="Delete this local vault?"
        subtitle="This removes every encrypted file, message, share record, and the vault metadata from this browser."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setConfirmWipe(false)}>
              Cancel
            </button>
            <button className="btn-danger" onClick={() => void wipe()}>
              <Trash2 className="h-4 w-4" /> Delete permanently
            </button>
          </>
        }
      >
        <p className="text-sm leading-relaxed text-slate-300">
          This action cannot be undone. Exported encrypted backups are not affected.
        </p>
      </Modal>
    </div>
  );
}
