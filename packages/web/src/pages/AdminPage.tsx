import { useEffect, useState } from 'react';
import { Activity, RefreshCw, ShieldCheck, Users } from 'lucide-react';
import { api, type ApiUser } from '../lib/api';
import { useVault } from '../lib/vault';
import { Badge, Card, PageHeader, Spinner, useToast } from '../components/ui';
import { formatBytes } from '../lib/format';

export default function AdminPage(): JSX.Element {
  const { user } = useVault();
  const { notify } = useToast();
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [adminDash, setAdminDash] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const isAdmin = user?.role === 'admin';

  async function load() {
    if (!isAdmin) { setLoading(false); return; }
    setLoading(true);
    try {
      const [u, f, h, d] = await Promise.all([api.admin.users(), api.admin.flags(), api.admin.health(), api.dashboard.admin()]);
      setUsers(u); setFlags(f); setHealth(h); setAdminDash(d);
    } catch (err) { notify(err instanceof Error ? err.message : 'Admin load failed', 'error'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [isAdmin]);

  async function toggleFlag(key: string) {
    try {
      const next = !flags[key];
      await api.admin.setFlag(key, next);
      setFlags((prev) => ({ ...prev, [key]: next }));
      notify(`Flag ${key} ${next ? 'enabled' : 'disabled'}`, 'success');
    } catch (err) { notify(err instanceof Error ? err.message : 'Flag update failed', 'error'); }
  }

  async function setSuspended(u: ApiUser, suspended: boolean) {
    try {
      const res = await api.admin.updateUser(u.id, { suspended });
      setUsers((prev) => prev.map((x) => x.id === u.id ? res.user : x));
      notify(`User ${suspended ? 'suspended' : 'activated'}`, 'success');
    } catch (err) { notify(err instanceof Error ? err.message : 'Update failed', 'error'); }
  }

  if (!isAdmin) {
    return <div className="animate-in"><PageHeader eyebrow="Admin console" title="Admin access required" description="This page uses dynamic admin APIs and requires an admin account." /><Card><p className="text-sm text-slate-400">Signed in as {user?.email ?? 'unknown'} with role {user?.role ?? 'unknown'}.</p></Card></div>;
  }

  return (
    <div className="animate-in">
      <PageHeader eyebrow="Admin console" title="Dynamic admin control plane" description="Live admin data from the API: users, feature flags, and system health. No central plaintext data is exposed." action={<button className="btn-secondary" onClick={() => void load()}><RefreshCw className="h-4 w-4" /> Refresh</button>} />

      {loading ? <div className="card py-12 text-center text-slate-400"><Spinner /> Loading admin data…</div> : (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Users</div><div className="mt-2 text-2xl font-semibold text-white">{String(adminDash?.users_total ?? users.length)}</div><div className="mt-1 text-[11px] text-slate-500">{String(adminDash?.users_active ?? '—')} active</div></Card>
            <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Files</div><div className="mt-2 text-2xl font-semibold text-white">{String(adminDash?.files_total ?? '—')}</div><div className="mt-1 text-[11px] text-slate-500">{formatBytes(Number(adminDash?.bytes_total ?? 0))}</div></Card>
            <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Shares</div><div className="mt-2 text-2xl font-semibold text-white">{String(adminDash?.shares_total ?? '—')}</div><div className="mt-1 text-[11px] text-slate-500">Total share records</div></Card>
            <Card className="!p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">System</div><div className="mt-2 text-2xl font-semibold text-white">{String(health?.status ?? '—')}</div><div className="mt-1 text-[11px] text-slate-500">DB: {String(health?.database ?? '—')}</div></Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
            <Card>
              <div className="mb-3 flex items-center justify-between"><h2 className="text-base font-semibold text-white">Users</h2><Badge className="badge-cyan"><Users className="mr-1 h-3 w-3" /> {users.length}</Badge></div>
              <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b border-white/8 text-left text-[11px] uppercase tracking-wider text-slate-500"><th className="px-2 py-2">User</th><th className="px-2 py-2">Role</th><th className="px-2 py-2">Used</th><th className="px-2 py-2">Status</th><th className="px-2 py-2">Action</th></tr></thead><tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-white/5"><td className="px-2 py-2"><div className="text-slate-100">{u.display_name || u.email}</div><div className="text-[11px] text-slate-500">{u.email}</div></td><td className="px-2 py-2 text-slate-300">{u.role}</td><td className="px-2 py-2 text-slate-400">{formatBytes(u.used_bytes)}</td><td className="px-2 py-2"><Badge className={u.suspended ? 'badge-rose' : 'badge-emerald'}>{u.suspended ? 'suspended' : 'active'}</Badge></td><td className="px-2 py-2">{u.id !== user?.id && <button className="btn-secondary !px-2 !py-1 !text-xs" onClick={() => void setSuspended(u, !u.suspended)}>{u.suspended ? 'Activate' : 'Suspend'}</button>}</td></tr>
                ))}
              </tbody></table></div>
            </Card>

            <div className="space-y-4">
              <Card>
                <div className="mb-3 flex items-center justify-between"><h2 className="text-base font-semibold text-white">Feature flags</h2><ShieldCheck className="h-5 w-5 text-cyan-300" /></div>
                <div className="space-y-2">
                  {Object.entries(flags).map(([k, v]) => (
                    <button key={k} onClick={() => void toggleFlag(k)} className="flex w-full items-center justify-between rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5 text-left hover:border-white/15">
                      <span className="text-sm text-slate-200">{k}</span><Badge className={v ? 'badge-emerald' : 'badge-rose'}>{v ? 'enabled' : 'disabled'}</Badge>
                    </button>
                  ))}
                  {Object.keys(flags).length === 0 && <p className="text-xs text-slate-500">No flags returned.</p>}
                </div>
              </Card>

              <Card>
                <div className="mb-3 flex items-center justify-between"><h2 className="text-base font-semibold text-white">System health</h2><Activity className="h-5 w-5 text-cyan-300" /></div>
                <pre className="code-block !text-[10px] overflow-auto max-h-64">{JSON.stringify(health, null, 2)}</pre>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
