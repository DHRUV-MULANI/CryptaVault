import type { ReactNode } from 'react';
import { Link, useLocation } from 'wouter';
import {
  Activity,
  BookOpen,
  Boxes,
  FolderLock,
  Gauge,
  GraduationCap,
  LayoutDashboard,
  Lock,
  MessageSquareLock,
  Settings,
  Share2,
  ShieldCheck,
} from 'lucide-react';
import { useVault } from '../lib/vault';
import { getProfile } from '../lib/profiles';
import { classNames } from '../lib/format';

const NAV = [
  {
    group: 'Workspace',
    items: [
      { href: '/', label: 'Overview', icon: LayoutDashboard },
      { href: '/vault', label: 'Encrypted vault', icon: FolderLock },
      { href: '/shares', label: 'Secure shares', icon: Share2 },
      { href: '/messages', label: 'Messages', icon: MessageSquareLock },
    ],
  },
  {
    group: 'Intelligence',
    items: [
      { href: '/catalog', label: 'Crypto catalog', icon: Boxes },
      { href: '/academy', label: 'Academy', icon: GraduationCap },
    ],
  },
  {
    group: 'System',
    items: [
      { href: '/admin', label: 'Admin console', icon: Gauge },
      { href: '/settings', label: 'Settings', icon: Settings },
      { href: '/status', label: 'Diagnostics', icon: Activity },
    ],
  },
];

function Brand(): JSX.Element {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-glow">
        <ShieldCheck className="h-5 w-5" />
      </span>
      <span>
        <span className="block text-sm font-semibold tracking-tight text-white">CryptaVault</span>
        <span className="block text-[10px] uppercase tracking-[0.2em] text-slate-500">
          Zero-knowledge storage
        </span>
      </span>
    </Link>
  );
}

export default function Layout({ children }: { children: ReactNode }): JSX.Element {
  const [location] = useLocation();
  const { settings, meta, lock } = useVault();
  const profile = getProfile(settings.defaultProfile);
  const version = import.meta.env.VITE_COMMIT ?? 'dev';

  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-64 shrink-0 border-r border-white/8 bg-black/20 px-4 py-5 lg:flex lg:flex-col">
        <Brand />
        <div className="mt-6 flex items-center gap-2 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-300">
            <Lock className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <div className="truncate text-xs font-semibold text-white">
              {settings.displayName || 'Local vault'}
            </div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              Unlocked · {profile.level.replace('_', '-')}
            </div>
          </div>
        </div>

        <nav className="mt-6 flex-1 space-y-6 overflow-y-auto scroll-thin">
          {NAV.map((group) => (
            <div key={group.group}>
              <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">
                {group.group}
              </div>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const active =
                    item.href === '/' ? location === '/' : location.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={classNames(
                        'flex items-center gap-2.5 rounded-lg border px-2.5 py-2 text-sm transition-colors',
                        active
                          ? 'border-cyan-400/20 bg-cyan-500/10 text-cyan-100'
                          : 'border-transparent text-slate-400 hover:bg-white/5 hover:text-slate-100',
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="mt-4 space-y-3">
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
            <div className="flex items-center gap-2 text-[11px] text-slate-400">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" />
              Client-side encryption
            </div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-slate-500">
              Keys are derived in this tab and never uploaded. The vault is stored in IndexedDB.
            </p>
          </div>
          <button className="btn-secondary w-full justify-center !py-2 !text-xs" onClick={lock}>
            <Lock className="h-3.5 w-3.5" /> Lock vault
          </button>
          <div className="flex items-center justify-between px-1 text-[10px] text-slate-600">
            <span>v1.0.0 · {version.slice(0, 7)}</span>
            <a
              className="inline-flex items-center gap-1 hover:text-slate-400"
              href="https://github.com/DHRUV-MULANI/CryptaVault"
              target="_blank"
              rel="noreferrer"
            >
              <BookOpen className="h-3 w-3" /> Docs
            </a>
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 border-b border-white/8 bg-[#080b11]/85 backdrop-blur-xl lg:hidden">
          <div className="flex items-center justify-between px-4 py-3">
            <Brand />
            <div className="flex items-center gap-2">
              <span className="badge badge-emerald">{profile.level.replace('_', ' ')}</span>
              <button className="btn-ghost !p-2" onClick={lock} aria-label="Lock vault">
                <Lock className="h-4 w-4" />
              </button>
            </div>
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-2 scroll-thin">
            {NAV.flatMap((group) => group.items).map((item) => {
              const active = item.href === '/' ? location === '/' : location.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={classNames(
                    'flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs',
                    active ? 'bg-cyan-500/10 text-cyan-200' : 'text-slate-400',
                  )}
                >
                  <item.icon className="h-3.5 w-3.5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>

        <main className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
        <footer className="mx-auto flex w-full max-w-[1400px] flex-wrap items-center justify-between gap-2 px-4 pb-6 text-[11px] text-slate-600 sm:px-6 lg:px-8">
          <span>
            CryptaVault · zero-knowledge boundary enforced · vault created{' '}
            {meta ? new Date(meta.createdAt).toLocaleDateString() : '—'}
          </span>
          <span className="mono">AES-GCM · PBKDF2-SHA256 · IndexedDB</span>
        </footer>
      </div>
    </div>
  );
}
