import { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  Check,
  Download,
  Eye,
  EyeOff,
  FileUp,
  Fingerprint,
  KeyRound,
  Lock,
  Moon,
  Save,
  ShieldCheck,
  Sun,
  Trash2,
} from 'lucide-react';
import { useVault } from '../lib/vault';
import { dbExportAll, dbImportAll } from '../lib/db';
import { b64ToBytes, sha256Hex } from '../lib/crypto';
import { PROFILES } from '../lib/profiles';
import {
  Badge,
  Card,
  Modal,
  PageHeader,
  Toggle,
  useToast,
} from '../components/ui';
import { downloadText } from '../lib/format';
import type { ProfileLevel } from '../lib/types';

export default function SettingsPage(): JSX.Element {
  const { settings, meta, updateSettings, changePassphrase, wipe, bumpRevision } = useVault();
  const { notify } = useToast();
  const [displayName, setDisplayName] = useState(settings.displayName);
  const [autoLock, setAutoLock] = useState(settings.autoLockMinutes);
  const [shareTtl, setShareTtl] = useState(settings.shareTtlHours);
  const [fingerprint, setFingerprint] = useState('');
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [rotateError, setRotateError] = useState<string | null>(null);
  const [importData, setImportData] = useState<Record<string, unknown[]> | null>(null);
  const [wipeOpen, setWipeOpen] = useState(false);
  const [backupName, setBackupName] = useState('');
  const importRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDisplayName(settings.displayName);
    setAutoLock(settings.autoLockMinutes);
    setShareTtl(settings.shareTtlHours);
  }, [settings.autoLockMinutes, settings.displayName, settings.shareTtlHours]);

  useEffect(() => {
    let cancelled = false;
    if (!meta) return;
    void sha256Hex(b64ToBytes(meta.saltB64)).then((digest) => {
      if (!cancelled) setFingerprint(digest);
    });
    return () => {
      cancelled = true;
    };
  }, [meta]);

  async function saveIdentity(): Promise<void> {
    await updateSettings({
      displayName: displayName.trim() || 'Local Vault',
      autoLockMinutes: Math.max(1, Math.min(240, autoLock)),
      shareTtlHours: Math.max(1, Math.min(720, shareTtl)),
    });
    notify('Settings saved.', 'success');
  }

  async function rotate(): Promise<void> {
    setRotateError(null);
    if (next !== confirm) {
      setRotateError('New passphrases do not match.');
      return;
    }
    setRotating(true);
    try {
      await changePassphrase(current, next);
      setCurrent('');
      setNext('');
      setConfirm('');
      notify('Passphrase rotated. All wrapped keys were re-encrypted.', 'success');
    } catch (err) {
      setRotateError(err instanceof Error ? err.message : 'Rotation failed.');
    } finally {
      setRotating(false);
    }
  }

  async function exportBackup(): Promise<void> {
    const data = await dbExportAll();
    const payload = {
      kind: 'cryptavault-encrypted-backup',
      version: 1,
      exportedAt: new Date().toISOString(),
      note: 'This backup contains ciphertext and wrapped keys only. The passphrase is required to use it.',
      data,
    };
    downloadText(
      JSON.stringify(payload, null, 2),
      backupName.trim()
        ? `${backupName.trim().replace(/[^a-zA-Z0-9-_]/g, '-')}.cvbackup.json`
        : `cryptavault-backup-${Date.now()}.cvbackup.json`,
      'application/json',
    );
    notify('Encrypted backup exported.', 'success');
  }

  async function readBackup(file: File): Promise<void> {
    try {
      const parsed = JSON.parse(await file.text()) as {
        kind?: string;
        version?: number;
        data?: Record<string, unknown[]>;
      };
      if (parsed.kind !== 'cryptavault-encrypted-backup' || !parsed.data) {
        throw new Error('Not a CryptaVault encrypted backup.');
      }
      setImportData(parsed.data);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Could not read backup.', 'error');
    }
  }

  async function restoreBackup(): Promise<void> {
    if (!importData) return;
    await dbImportAll(importData);
    bumpRevision();
    notify('Backup restored. Reloading vault…', 'success');
    setTimeout(() => window.location.reload(), 700);
  }

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Settings"
        title="Vault policy, identity, and recovery"
        description="Configure local policy, rotate the master passphrase, and export an encrypted backup. This page never sends data anywhere."
        action={
          <button className="btn-primary" onClick={() => void saveIdentity()}>
            <Save className="h-4 w-4" /> Save changes
          </button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
        <div className="space-y-4">
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Vault identity</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  The display label is local metadata and is not uploaded.
                </p>
              </div>
              <Fingerprint className="h-5 w-5 text-cyan-300" />
            </div>
            <div className="space-y-3">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Display name
                </span>
                <input
                  className="input"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Default profile
                  </span>
                  <select
                    className="input"
                    value={settings.defaultProfile}
                    onChange={(event) =>
                      void updateSettings({
                        defaultProfile: event.target.value as ProfileLevel,
                      })
                    }
                  >
                    {PROFILES.map((profile) => (
                      <option key={profile.level} value={profile.level}>
                        {profile.level.replace('_', '-')}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Theme
                  </span>
                  <div className="flex gap-2">
                    {(['dark', 'light'] as const).map((theme) => (
                      <button
                        key={theme}
                        className={`btn-secondary flex-1 justify-center ${
                          settings.theme === theme ? '!border-cyan-400/40 !text-cyan-200' : ''
                        }`}
                        onClick={() => void updateSettings({ theme })}
                      >
                        {theme === 'dark' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                        {theme}
                      </button>
                    ))}
                  </div>
                </label>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Auto-lock (minutes)
                  </span>
                  <input
                    type="number"
                    min={1}
                    max={240}
                    className="input"
                    value={autoLock}
                    onChange={(event) => setAutoLock(Number(event.target.value))}
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    Default share TTL (hours)
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
              </div>
              <Toggle
                label="Compress files by default"
                description="Auto-detection skips pre-compressed media. Turn off to never compress."
                checked={settings.compressByDefault}
                onChange={(nextValue) => void updateSettings({ compressByDefault: nextValue })}
              />
              <div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5">
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                  Vault salt fingerprint
                </div>
                <div className="mono mt-1 break-all text-[11px] text-cyan-300">
                  {fingerprint ? `${fingerprint.slice(0, 32)}…` : 'computing…'}
                </div>
                <div className="mt-1 text-[10px] text-slate-500">
                  SHA-256 of the 16-byte KDF salt. Use it to distinguish local vaults; it is not a
                  key.
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Encrypted backup</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  Export every store as ciphertext. Restore on this or another device.
                </p>
              </div>
              <Download className="h-5 w-5 text-cyan-300" />
            </div>
            <div className="space-y-3">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Backup file name (optional)
                </span>
                <input
                  className="input"
                  value={backupName}
                  onChange={(event) => setBackupName(event.target.value)}
                  placeholder="research-vault"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <button className="btn-secondary" onClick={() => void exportBackup()}>
                  <Download className="h-4 w-4" /> Export encrypted backup
                </button>
                <input
                  ref={importRef}
                  type="file"
                  accept=".json,application/json"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void readBackup(file);
                    event.target.value = '';
                  }}
                />
                <button className="btn-secondary" onClick={() => importRef.current?.click()}>
                  <FileUp className="h-4 w-4" /> Restore backup
                </button>
              </div>
              <div className="rounded-xl border border-amber-400/20 bg-amber-500/5 p-3 text-[11px] leading-relaxed text-amber-100/80">
                The backup is safe to store anywhere: it contains ciphertext, encrypted manifests,
                wrapped keys, and a verifier. It does not contain the passphrase. It does contain
                local share records, which never include capability keys.
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Rotate passphrase</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  Re-wraps every file and message key with a new master key.
                </p>
              </div>
              <KeyRound className="h-5 w-5 text-cyan-300" />
            </div>
            <div className="space-y-3">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Current passphrase
                </span>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showPasswords ? 'text' : 'password'}
                    value={current}
                    onChange={(event) => setCurrent(event.target.value)}
                    autoComplete="current-password"
                  />
                  <button
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-500"
                    onClick={() => setShowPasswords((value) => !value)}
                    aria-label="Toggle passphrase visibility"
                  >
                    {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  New passphrase
                </span>
                <input
                  className="input"
                  type={showPasswords ? 'text' : 'password'}
                  value={next}
                  onChange={(event) => setNext(event.target.value)}
                  autoComplete="new-password"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Confirm new passphrase
                </span>
                <input
                  className="input"
                  type={showPasswords ? 'text' : 'password'}
                  value={confirm}
                  onChange={(event) => setConfirm(event.target.value)}
                  autoComplete="new-password"
                />
              </label>
              {rotateError ? (
                <div className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  {rotateError}
                </div>
              ) : null}
              <button
                className="btn-primary w-full justify-center"
                onClick={() => void rotate()}
                disabled={rotating || !current || next.length < 10 || next !== confirm}
              >
                {rotating ? 'Rotating…' : 'Rotate passphrase'}
              </button>
              <div className="text-[11px] leading-relaxed text-slate-500">
                File payloads stay as ciphertext; only their wrapped keys and encrypted manifests
                are rewritten. Export a backup first if the vault is large.
              </div>
            </div>
          </Card>

          <Card>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Security posture</h2>
                <p className="mt-0.5 text-xs text-slate-400">Derived from the active profile.</p>
              </div>
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
            </div>
            <div className="space-y-2 text-[11px]">
              {[
                ['Profile', settings.defaultProfile.replace('_', '-')],
                ['Metadata encryption', settings.defaultProfile === 'PERFORMANCE' ? 'Off (profile)' : 'On'],
                ['Share capability', settings.sharingEnabled ? 'Enabled' : 'Disabled'],
                ['Messages', settings.messagingEnabled ? 'Enabled' : 'Disabled'],
                ['Experimental algorithms', settings.allowExperimental ? 'Policy allowed' : 'Blocked'],
                ['Auto-lock', `${settings.autoLockMinutes} minutes`],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-center justify-between gap-2 rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2"
                >
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-200">{value}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <Badge className="badge-emerald">IndexedDB only</Badge>
              <Badge className="badge-cyan">No telemetry</Badge>
              <Badge className="badge-purple">PBKDF2-SHA256</Badge>
            </div>
          </Card>

          <Card className="!border-rose-400/20">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Danger zone</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  Irreversibly delete this browser vault.
                </p>
              </div>
              <Lock className="h-5 w-5 text-rose-300" />
            </div>
            <button className="btn-danger w-full justify-center" onClick={() => setWipeOpen(true)}>
              <Trash2 className="h-4 w-4" /> Wipe local vault
            </button>
          </Card>
        </div>
      </div>

      <Modal
        open={Boolean(importData)}
        onClose={() => setImportData(null)}
        title="Restore encrypted backup?"
        subtitle="This replaces every store in the current browser vault with the backup contents."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setImportData(null)}>
              Cancel
            </button>
            <button className="btn-danger" onClick={() => void restoreBackup()}>
              <Check className="h-4 w-4" /> Replace & reload
            </button>
          </>
        }
      >
        <p className="text-sm leading-relaxed text-slate-300">
          You will need the passphrase that was active when the backup was created. The page will
          reload and lock automatically.
        </p>
      </Modal>

      <Modal
        open={wipeOpen}
        onClose={() => setWipeOpen(false)}
        title="Wipe the local vault?"
        subtitle="Every encrypted file, message, share record, and audit event is deleted."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setWipeOpen(false)}>
              Cancel
            </button>
            <button className="btn-danger" onClick={() => void wipe()}>
              <Trash2 className="h-4 w-4" /> Delete permanently
            </button>
          </>
        }
      >
        <p className="text-sm leading-relaxed text-slate-300">
          Export an encrypted backup first if you want to keep the ciphertext. This action cannot be
          undone.
        </p>
      </Modal>
    </div>
  );
}
