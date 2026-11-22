import { useEffect, useState } from 'react';
import { AlertTriangle, Fingerprint, KeyRound, LogOut, Moon, Save, ShieldCheck, Sun } from 'lucide-react';
import { useVault } from '../lib/vault';
import { PROFILES } from '../lib/profiles';
import { Badge, Card, PageHeader, useToast } from '../components/ui';
import type { ProfileLevel } from '../lib/types';

export default function SettingsPage(): JSX.Element {
  const { settings, user, vault, updateSettings, lock, logout } = useVault();
  const { notify } = useToast();
  const [displayName, setDisplayName] = useState(settings.displayName);
  const [autoLock, setAutoLock] = useState(settings.autoLockMinutes);
  const [shareTtl, setShareTtl] = useState(settings.shareTtlHours);

  useEffect(() => {
    setDisplayName(settings.displayName);
    setAutoLock(settings.autoLockMinutes);
    setShareTtl(settings.shareTtlHours);
  }, [settings.displayName, settings.autoLockMinutes, settings.shareTtlHours]);

  async function save() {
    await updateSettings({
      displayName: displayName.trim() || settings.displayName,
      autoLockMinutes: Math.max(1, Math.min(240, autoLock)),
      shareTtlHours: Math.max(1, Math.min(720, shareTtl)),
    });
    notify('Settings saved.', 'success');
  }

  return (
    <div className="animate-in">
      <PageHeader eyebrow="Settings" title="Account and session settings" description="Dynamic account settings are stored through the API where supported. Master keys remain memory-only in this tab." action={<button className="btn-primary" onClick={() => void save()}><Save className="h-4 w-4" /> Save</button>} />

      <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
        <div className="space-y-4">
          <Card>
            <div className="mb-4 flex items-center justify-between"><div><h2 className="text-base font-semibold text-white">Identity</h2><p className="mt-0.5 text-xs text-slate-400">Display name and default profile are synced to the API.</p></div><Fingerprint className="h-5 w-5 text-cyan-300" /></div>
            <div className="space-y-3">
              <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Display name</span><input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} /></label>
              <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Email</span><input className="input" value={user?.email ?? ''} disabled /></label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Default profile</span><select className="input" value={settings.defaultProfile} onChange={(e) => void updateSettings({ defaultProfile: e.target.value as ProfileLevel })}>{PROFILES.map((p) => <option key={p.level} value={p.level}>{p.level.replace('_', '-')}</option>)}</select></label>
                <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Theme</span><div className="flex gap-2">{(['dark', 'light'] as const).map((t) => <button key={t} className={`btn-secondary flex-1 justify-center ${settings.theme === t ? '!border-cyan-400/40 !text-cyan-200' : ''}`} onClick={() => void updateSettings({ theme: t })}>{t === 'dark' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}{t}</button>)}</div></label>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Auto-lock (minutes)</span><input type="number" min={1} max={240} className="input" value={autoLock} onChange={(e) => setAutoLock(Number(e.target.value))} /></label>
                <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Default share TTL (hours)</span><input type="number" min={1} max={720} className="input" value={shareTtl} onChange={(e) => setShareTtl(Number(e.target.value))} /></label>
              </div>
            </div>
          </Card>

          <Card>
            <div className="mb-3 flex items-center justify-between"><div><h2 className="text-base font-semibold text-white">Passphrase rotation</h2><p className="mt-0.5 text-xs text-slate-400">Not yet wired for dynamic accounts.</p></div><KeyRound className="h-5 w-5 text-cyan-300" /></div>
            <div className="flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-500/5 p-3 text-xs text-amber-100/80">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              Dynamic passphrase rotation requires re-wrapping server-stored wrapped keys and updating auth/vault verifiers atomically. This is a planned framework feature; it is intentionally disabled here instead of pretending to work.
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <div className="mb-3 flex items-center justify-between"><div><h2 className="text-base font-semibold text-white">Session & vault</h2><p className="mt-0.5 text-xs text-slate-400">Local session controls.</p></div><ShieldCheck className="h-5 w-5 text-emerald-300" /></div>
            <div className="space-y-2 text-[11px]">
              {[['User ID', user?.id ?? '—'], ['Role', user?.role ?? '—'], ['KDF iterations', vault?.kdf_iterations?.toLocaleString() ?? '—'], ['Vault salt', vault?.salt_b64 ? `${vault.salt_b64.slice(0, 16)}…` : '—'], ['Quota', `${((user?.used_bytes ?? 0) / 1024 / 1024).toFixed(2)} / ${((user?.quota_bytes ?? 0) / 1024 / 1024).toFixed(2)} MiB`]].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-2 rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2"><span className="text-slate-500">{label}</span><span className="mono truncate text-slate-200">{value}</span></div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5"><Badge className="badge-emerald">API-backed</Badge><Badge className="badge-cyan">Zero-knowledge</Badge><Badge className="badge-purple">PBKDF2-SHA256</Badge></div>
          </Card>

          <Card className="!border-rose-400/20">
            <div className="mb-3"><h2 className="text-base font-semibold text-white">Session actions</h2><p className="mt-0.5 text-xs text-slate-400">Lock clears the in-memory master key. Logout clears the JWT session.</p></div>
            <div className="grid gap-2 sm:grid-cols-2">
              <button className="btn-secondary justify-center" onClick={lock}><KeyRound className="h-4 w-4" /> Lock</button>
              <button className="btn-danger justify-center" onClick={() => void logout()}><LogOut className="h-4 w-4" /> Logout</button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
