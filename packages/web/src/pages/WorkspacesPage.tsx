import { useEffect, useState } from 'react';
import { Building2, Plus, RefreshCw, Shield, UserPlus, Users } from 'lucide-react';
import { api, type ApiMember, type ApiWorkspace } from '../lib/api';
import { useVault } from '../lib/vault';
import { Badge, Card, PageHeader, Spinner, useToast } from '../components/ui';
import { formatBytes } from '../lib/format';

const ROLES = ['viewer', 'editor', 'admin'];

export default function WorkspacesPage(): JSX.Element {
  const { currentWorkspace, selectWorkspace, refresh, user, bumpRevision } = useVault();
  const { notify } = useToast();
  const [workspaces, setWorkspaces] = useState<ApiWorkspace[]>([]);
  const [members, setMembers] = useState<ApiMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('');
  const [memberEmail, setMemberEmail] = useState('');
  const [memberRole, setMemberRole] = useState('viewer');

  async function load() {
    setLoading(true);
    try {
      const ws = await api.workspaces.list();
      setWorkspaces(ws);
      const active = ws.find((w) => w.id === currentWorkspace?.id) ?? ws[0];
      if (active) {
        if (active.id !== currentWorkspace?.id) selectWorkspace(active.id);
        setMembers(await api.workspaces.members(active.id));
      } else {
        setMembers([]);
      }
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to load workspaces', 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [currentWorkspace?.id]);

  async function createWorkspace(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const ws = await api.workspaces.create({ name: name.trim() });
      notify(`Workspace "${ws.name}" created`, 'success');
      setName('');
      await refresh();
      selectWorkspace(ws.id);
      await load();
      bumpRevision();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Create failed', 'error');
    } finally {
      setBusy(false);
    }
  }

  async function addMember(e: React.FormEvent) {
    e.preventDefault();
    if (!currentWorkspace || !memberEmail.trim()) return;
    setBusy(true);
    try {
      await api.workspaces.addMember(currentWorkspace.id, { email: memberEmail.trim(), role: memberRole });
      notify('Member added/updated', 'success');
      setMemberEmail('');
      setMembers(await api.workspaces.members(currentWorkspace.id));
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Member update failed', 'error');
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(userId: string, role: string) {
    if (!currentWorkspace) return;
    try {
      await api.workspaces.updateMember(currentWorkspace.id, userId, { role });
      setMembers(await api.workspaces.members(currentWorkspace.id));
      notify('Role updated', 'success');
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Role update failed', 'error');
    }
  }

  async function removeMember(userId: string) {
    if (!currentWorkspace) return;
    try {
      await api.workspaces.removeMember(currentWorkspace.id, userId);
      setMembers(await api.workspaces.members(currentWorkspace.id));
      notify('Member removed', 'success');
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Remove failed', 'error');
    }
  }

  const canManage = ['owner', 'admin'].includes(currentWorkspace?.role ?? '');

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Workspaces"
        title="Dynamic workspaces"
        description="Workspaces are API-backed collaboration boundaries. Roles, quotas, and storage targets are enforced by the server; file contents remain client-encrypted."
        action={<button className="btn-secondary" onClick={() => void load()}><RefreshCw className="h-4 w-4" /> Refresh</button>}
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Your workspaces</h2>
            <Badge className="badge-cyan">{workspaces.length}</Badge>
          </div>
          {loading ? <div className="py-8 text-center text-slate-400"><Spinner /> Loading…</div> : (
            <div className="space-y-2">
              {workspaces.map((ws) => {
                const active = ws.id === currentWorkspace?.id;
                return (
                  <button key={ws.id} onClick={() => { selectWorkspace(ws.id); bumpRevision(); }} className={`w-full rounded-xl border px-4 py-3 text-left transition-colors ${active ? 'border-cyan-400/30 bg-cyan-500/10' : 'border-white/8 bg-white/[0.02] hover:border-white/15'}`}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-cyan-300" />
                          <span className="truncate text-sm font-medium text-white">{ws.name}</span>
                        </div>
                        <div className="mt-1 text-[11px] text-slate-500">{ws.file_count} files · {formatBytes(ws.total_bytes)} · role {ws.role}</div>
                      </div>
                      {active ? <Badge className="badge-emerald">Active</Badge> : null}
                    </div>
                  </button>
                );
              })}
              {workspaces.length === 0 && <p className="text-sm text-slate-500">No workspaces found.</p>}
            </div>
          )}

          <form onSubmit={createWorkspace} className="mt-4 border-t border-white/8 pt-4">
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Create workspace</label>
            <div className="flex gap-2">
              <input className="input flex-1" value={name} onChange={(e) => setName(e.target.value)} placeholder="Workspace name" />
              <button className="btn-primary" disabled={busy || !name.trim()}><Plus className="h-4 w-4" /> Create</button>
            </div>
          </form>
        </Card>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Members</h2>
              <p className="text-xs text-slate-400">{currentWorkspace?.name ?? 'Select a workspace'}</p>
            </div>
            <Badge className="badge-purple"><Users className="mr-1 h-3 w-3" /> {members.length}</Badge>
          </div>

          <div className="space-y-2">
            {members.map((m) => (
              <div key={m.user_id} className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm text-slate-100">{m.display_name || m.email}</div>
                  <div className="truncate text-[11px] text-slate-500">{m.email}</div>
                </div>
                {canManage && m.role !== 'owner' && m.user_id !== user?.id ? (
                  <div className="flex items-center gap-2">
                    <select className="input !w-auto !py-1.5 !text-xs" value={m.role} onChange={(e) => void changeRole(m.user_id, e.target.value)}>
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                    <button className="btn-ghost !px-2 !py-1.5 text-xs text-rose-300" onClick={() => void removeMember(m.user_id)}>Remove</button>
                  </div>
                ) : (
                  <Badge className={m.role === 'owner' ? 'badge-amber' : 'badge-cyan'}><Shield className="mr-1 h-3 w-3" /> {m.role}</Badge>
                )}
              </div>
            ))}
            {!loading && members.length === 0 && <p className="text-sm text-slate-500">No members loaded.</p>}
          </div>

          {canManage && currentWorkspace && (
            <form onSubmit={addMember} className="mt-4 border-t border-white/8 pt-4">
              <label className="mb-1.5 block text-xs font-medium text-slate-300">Add/update member by email</label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <input className="input flex-1" type="email" value={memberEmail} onChange={(e) => setMemberEmail(e.target.value)} placeholder="member@example.com" />
                <select className="input sm:w-32" value={memberRole} onChange={(e) => setMemberRole(e.target.value)}>
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <button className="btn-primary" disabled={busy || !memberEmail.trim()}><UserPlus className="h-4 w-4" /> Add</button>
              </div>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}