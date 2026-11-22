import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { api, getStoredWorkspaceId, getToken, setStoredWorkspaceId, setToken, type ApiMe, type ApiUser, type ApiVault, type ApiWorkspace } from './api';
import {
  KDF_ITERATIONS,
  VERIFIER_PLAINTEXT,
  b64ToBytes,
  bytesToB64,
  deriveMasterKey,
  fromUtf8,
  open,
  randomBytes,
  seal,
  utf8,
} from './crypto';
import type { ProfileLevel, VaultSettings } from './types';

export interface ThreadMeta {
  name: string;
  note?: string;
}

export const DEFAULT_SETTINGS: VaultSettings = {
  displayName: 'CryptaVault User',
  defaultProfile: 'BALANCED',
  autoLockMinutes: 10,
  shareTtlHours: 24,
  allowExperimental: false,
  compressByDefault: true,
  theme: 'dark',
  messagingEnabled: true,
  sharingEnabled: true,
};

export type VaultStatus = 'loading' | 'anonymous' | 'locked' | 'unlocked';

interface VaultContextValue {
  status: VaultStatus;
  user: ApiUser | null;
  vault: ApiVault | null;
  workspaces: ApiWorkspace[];
  currentWorkspace: ApiWorkspace | null;
  settings: VaultSettings;
  key: CryptoKey | null;
  revision: number;
  lastError: string | null;
  bumpRevision: () => void;
  register: (email: string, passphrase: string, displayName: string, defaultProfile: ProfileLevel) => Promise<void>;
  login: (email: string, passphrase: string) => Promise<void>;
  unlock: (passphrase: string) => Promise<void>;
  lock: () => void;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  selectWorkspace: (id: string) => void;
  updateSettings: (partial: Partial<VaultSettings>) => Promise<void>;
  // Compatibility aliases for older pages while migration is in progress
  meta: { createdAt: string; settings: VaultSettings; iterations?: number; saltB64?: string } | null;
  createVault: (passphrase: string, displayName: string, defaultProfile: ProfileLevel) => Promise<void>;
  changePassphrase: (_current: string, _next: string) => Promise<void>;
  wipe: () => Promise<void>;
}

const VaultContext = createContext<VaultContextValue | null>(null);

function settingsFromUser(user: ApiUser | null, prev: VaultSettings): VaultSettings {
  if (!user) return prev;
  return {
    ...prev,
    displayName: user.display_name || prev.displayName,
    defaultProfile: (user.default_profile as ProfileLevel) || prev.defaultProfile,
  };
}

function pickWorkspace(workspaces: ApiWorkspace[], preferredId: string | null): ApiWorkspace | null {
  if (workspaces.length === 0) return null;
  if (preferredId) {
    const found = workspaces.find((w) => w.id === preferredId);
    if (found) return found;
  }
  return workspaces[0] ?? null;
}

export function VaultProvider({ children }: { children: ReactNode }): JSX.Element {
  const [status, setStatus] = useState<VaultStatus>('loading');
  const [user, setUser] = useState<ApiUser | null>(null);
  const [vault, setVault] = useState<ApiVault | null>(null);
  const [workspaces, setWorkspaces] = useState<ApiWorkspace[]>([]);
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(getStoredWorkspaceId());
  const [key, setKey] = useState<CryptoKey | null>(null);
  const [settings, setSettings] = useState<VaultSettings>(DEFAULT_SETTINGS);
  const [revision, setRevision] = useState(0);
  const [lastError, setLastError] = useState<string | null>(null);
  const lastActivity = useRef(Date.now());

  const bumpRevision = useCallback(() => setRevision((v) => v + 1), []);
  const touch = useCallback(() => {
    lastActivity.current = Date.now();
  }, []);

  const applySession = useCallback((me: ApiMe | { user: ApiUser; vault: ApiVault; workspaces: ApiWorkspace[] }) => {
    setUser(me.user);
    setVault(me.vault);
    setWorkspaces(me.workspaces);
    setSettings((prev) => settingsFromUser(me.user, prev));
    setCurrentWorkspaceId((prev) => {
      const picked = pickWorkspace(me.workspaces, prev ?? getStoredWorkspaceId());
      setStoredWorkspaceId(picked?.id ?? null);
      return picked?.id ?? null;
    });
  }, []);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setVault(null);
      setWorkspaces([]);
      setKey(null);
      setStatus('anonymous');
      return;
    }
    try {
      const me = await api.auth.me();
      applySession(me);
      setStatus((prev) => (prev === 'unlocked' && key ? 'unlocked' : 'locked'));
    } catch {
      setToken(null);
      setUser(null);
      setVault(null);
      setWorkspaces([]);
      setKey(null);
      setStatus('anonymous');
    }
  }, [applySession, key]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const token = getToken();
      if (!token) {
        if (!cancelled) setStatus('anonymous');
        return;
      }
      try {
        const me = await api.auth.me();
        if (cancelled) return;
        applySession(me);
        setStatus('locked');
      } catch {
        if (cancelled) return;
        setToken(null);
        setStatus('anonymous');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applySession]);

  useEffect(() => {
    document.documentElement.classList.toggle('light', settings.theme === 'light');
  }, [settings.theme]);

  const deriveAndVerify = useCallback(async (passphrase: string, v: ApiVault): Promise<CryptoKey> => {
    const salt = b64ToBytes(v.salt_b64);
    const masterKey = await deriveMasterKey(passphrase, salt, v.kdf_iterations ?? KDF_ITERATIONS);
    const plain = await open(masterKey, v.check, 'vault:verifier');
    if (fromUtf8(plain) !== VERIFIER_PLAINTEXT) {
      throw new Error('Vault check failed.');
    }
    return masterKey;
  }, []);

  const login = useCallback(async (email: string, passphrase: string) => {
    setLastError(null);
    const normalized = email.toLowerCase().trim();
    const pre = await api.auth.prelogin(normalized);
    const authSalt = b64ToBytes(pre.auth_salt_b64);
    const iterations = pre.kdf_iterations ?? KDF_ITERATIONS;
    const authKey = await deriveMasterKey(passphrase, authSalt, iterations, true);
    const authRaw = new Uint8Array(await crypto.subtle.exportKey('raw', authKey));
    const authVerifier = bytesToB64(authRaw);
    const session = await api.auth.login({ email: normalized, auth_verifier: authVerifier });
    setToken(session.access_token);
    applySession(session);
    const masterKey = await deriveAndVerify(passphrase, session.vault);
    setKey(masterKey);
    setStatus('unlocked');
    lastActivity.current = Date.now();
    bumpRevision();
  }, [applySession, bumpRevision, deriveAndVerify]);

  const register = useCallback(async (email: string, passphrase: string, displayName: string, defaultProfile: ProfileLevel) => {
    setLastError(null);
    if (passphrase.length < 10) throw new Error('Use a passphrase of at least 10 characters.');
    const normalized = email.toLowerCase().trim();
    const iterations = KDF_ITERATIONS;
    const authSalt = randomBytes(16);
    const vaultSalt = randomBytes(16);
    const authKey = await deriveMasterKey(passphrase, authSalt, iterations, true);
    const masterKey = await deriveMasterKey(passphrase, vaultSalt, iterations);
    const authRaw = new Uint8Array(await crypto.subtle.exportKey('raw', authKey));
    const authVerifier = bytesToB64(authRaw);
    const vaultCheck = await seal(masterKey, utf8(VERIFIER_PLAINTEXT), 'vault:verifier');
    const session = await api.auth.register({
      email: normalized,
      display_name: displayName.trim() || normalized.split('@')[0] || 'User',
      auth_salt_b64: bytesToB64(authSalt),
      auth_verifier: authVerifier,
      vault_salt_b64: bytesToB64(vaultSalt),
      vault_check: vaultCheck,
      kdf_iterations: iterations,
    });
    setToken(session.access_token);
    applySession(session);
    setKey(masterKey);
    setStatus('unlocked');
    lastActivity.current = Date.now();
    // best-effort profile update
    try {
      await api.auth.updateMe({ default_profile: defaultProfile });
      await refresh();
      setKey(masterKey);
      setStatus('unlocked');
    } catch {
      // ignore
    }
    bumpRevision();
  }, [applySession, bumpRevision, refresh]);

  const unlock = useCallback(async (passphrase: string) => {
    setLastError(null);
    if (!vault) throw new Error('No session vault metadata. Please sign in again.');
    const masterKey = await deriveAndVerify(passphrase, vault);
    setKey(masterKey);
    setStatus('unlocked');
    lastActivity.current = Date.now();
    bumpRevision();
  }, [bumpRevision, deriveAndVerify, vault]);

  const lock = useCallback(() => {
    setKey(null);
    setStatus((s) => (s === 'unlocked' ? 'locked' : s));
  }, []);

  const logout = useCallback(async () => {
    try { await api.auth.logout(); } catch { /* ignore */ }
    setToken(null);
    setStoredWorkspaceId(null);
    setKey(null);
    setUser(null);
    setVault(null);
    setWorkspaces([]);
    setCurrentWorkspaceId(null);
    setStatus('anonymous');
  }, []);

  const selectWorkspace = useCallback((id: string) => {
    setCurrentWorkspaceId(id);
    setStoredWorkspaceId(id);
    bumpRevision();
  }, [bumpRevision]);

  const updateSettings = useCallback(async (partial: Partial<VaultSettings>) => {
    setSettings((prev) => ({ ...prev, ...partial }));
    const payload: { display_name?: string; default_profile?: string } = {};
    if (partial.displayName !== undefined) payload.display_name = partial.displayName;
    if (partial.defaultProfile !== undefined) payload.default_profile = partial.defaultProfile;
    if (Object.keys(payload).length > 0) {
      try {
        const me = await api.auth.updateMe(payload);
        applySession(me);
        if (key) setStatus('unlocked');
      } catch {
        // local-only settings still applied
      }
    }
    bumpRevision();
  }, [applySession, bumpRevision, key]);

  useEffect(() => {
    if (status !== 'unlocked') return;
    const mark = () => touch();
    window.addEventListener('pointerdown', mark);
    window.addEventListener('keydown', mark);
    window.addEventListener('touchstart', mark);
    const interval = window.setInterval(() => {
      const limit = Math.max(1, settings.autoLockMinutes) * 60_000;
      if (Date.now() - lastActivity.current > limit) lock();
    }, 15_000);
    return () => {
      window.removeEventListener('pointerdown', mark);
      window.removeEventListener('keydown', mark);
      window.removeEventListener('touchstart', mark);
      window.clearInterval(interval);
    };
  }, [lock, settings.autoLockMinutes, status, touch]);

  const currentWorkspace = useMemo(
    () => pickWorkspace(workspaces, currentWorkspaceId),
    [workspaces, currentWorkspaceId],
  );

  const value = useMemo<VaultContextValue>(() => ({
    status,
    user,
    vault,
    workspaces,
    currentWorkspace,
    settings,
    key,
    revision,
    lastError,
    bumpRevision,
    register,
    login,
    unlock,
    lock,
    logout,
    refresh,
    selectWorkspace,
    updateSettings,
    meta: user ? { createdAt: user.created_at ?? new Date().toISOString(), settings, iterations: vault?.kdf_iterations, saltB64: vault?.salt_b64 } : null,
    createVault: async (passphrase: string, displayName: string, defaultProfile: ProfileLevel) => {
      const email = user?.email;
      if (!email) throw new Error('Email is required for registration.');
      await register(email, passphrase, displayName, defaultProfile);
    },
    changePassphrase: async () => {
      throw new Error('Passphrase rotation is not implemented yet for dynamic accounts.');
    },
    wipe: async () => {
      await logout();
    },
  }), [status, user, vault, workspaces, currentWorkspace, settings, key, revision, lastError, bumpRevision, register, login, unlock, lock, logout, refresh, selectWorkspace, updateSettings]);

  return <VaultContext.Provider value={value}>{children}</VaultContext.Provider>;
}

export function useVault(): VaultContextValue {
  const ctx = useContext(VaultContext);
  if (!ctx) throw new Error('useVault must be used inside VaultProvider.');
  return ctx;
}

// Compatibility stubs for pages still being migrated from local IndexedDB model.
export async function loadFileMeta(_key: CryptoKey, _file: unknown): Promise<{ meta: any; rawKey: Uint8Array<ArrayBuffer> }> {
  throw new Error('Local file meta loading is not used in dynamic mode.');
}
export async function deleteFileCascade(_id: string): Promise<void> {
  throw new Error('Local file cascade delete is not used in dynamic mode.');
}