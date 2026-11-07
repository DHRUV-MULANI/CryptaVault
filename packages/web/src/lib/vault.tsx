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
import { recordAudit } from './audit';
import {
  KDF_ITERATIONS,
  VERIFIER_PLAINTEXT,
  deriveMasterKey,
  bytesToB64,
  importAesKey,
  openJson,
  randomBytes,
  seal,
  sealJson,
  unwrapRawKey,
  utf8,
  wrapRawKey,
  fromUtf8,
  open,
} from './crypto';
import {
  dbDelete,
  dbGet,
  dbGetAll,
  dbPut,
  deleteDatabase,
} from './db';
import { DEFAULT_PROFILE } from './profiles';
import type {
  FileMeta,
  FileRecord,
  MessageBody,
  MessageRecord,
  ProfileLevel,
  ThreadRecord,
  VaultMeta,
  VaultSettings,
} from './types';

export interface ThreadMeta {
  name: string;
  note?: string;
}

export const DEFAULT_SETTINGS: VaultSettings = {
  displayName: 'Local Vault',
  defaultProfile: DEFAULT_PROFILE,
  autoLockMinutes: 10,
  shareTtlHours: 24,
  allowExperimental: false,
  compressByDefault: true,
  theme: 'dark',
  messagingEnabled: true,
  sharingEnabled: true,
};

export type VaultStatus = 'loading' | 'empty' | 'locked' | 'unlocked';

interface VaultContextValue {
  status: VaultStatus;
  meta: VaultMeta | null;
  settings: VaultSettings;
  key: CryptoKey | null;
  revision: number;
  lastError: string | null;
  bumpRevision: () => void;
  createVault: (
    passphrase: string,
    displayName: string,
    defaultProfile: ProfileLevel,
  ) => Promise<void>;
  unlock: (passphrase: string) => Promise<void>;
  lock: () => void;
  updateSettings: (partial: Partial<VaultSettings>) => Promise<void>;
  changePassphrase: (current: string, next: string) => Promise<void>;
  wipe: () => Promise<void>;
}

const VaultContext = createContext<VaultContextValue | null>(null);

const VAULT_RECORD_KEY = 'vault';

function isVaultMeta(value: unknown): value is VaultMeta {
  if (!value || typeof value !== 'object') return false;
  const meta = value as Partial<VaultMeta>;
  return meta.version === 1 && typeof meta.saltB64 === 'string' && !!meta.verifier;
}

export function VaultProvider({ children }: { children: ReactNode }): JSX.Element {
  const [status, setStatus] = useState<VaultStatus>('loading');
  const [meta, setMeta] = useState<VaultMeta | null>(null);
  const [key, setKey] = useState<CryptoKey | null>(null);
  const [revision, setRevision] = useState(0);
  const [lastError, setLastError] = useState<string | null>(null);
  const lastActivity = useRef(Date.now());

  const bumpRevision = useCallback(() => setRevision((value) => value + 1), []);

  const touch = useCallback(() => {
    lastActivity.current = Date.now();
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const record = await dbGet<{ key: string; value: unknown }>('vault', VAULT_RECORD_KEY);
        if (cancelled) return;
        if (record && isVaultMeta(record.value)) {
          setMeta(record.value);
          setStatus('locked');
        } else {
          setStatus('empty');
        }
      } catch {
        if (!cancelled) {
          setStatus('empty');
          setLastError('Browser storage is unavailable. The portal cannot persist a vault.');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const settings = meta?.settings ?? DEFAULT_SETTINGS;

  useEffect(() => {
    document.documentElement.classList.toggle('light', settings.theme === 'light');
  }, [settings.theme]);

  const persistMeta = useCallback(async (next: VaultMeta) => {
    await dbPut('vault', { key: VAULT_RECORD_KEY, value: next });
    setMeta(next);
  }, []);

  const createVault = useCallback(
    async (passphrase: string, displayName: string, defaultProfile: ProfileLevel) => {
      setLastError(null);
      if (passphrase.length < 10) {
        throw new Error('Use a passphrase of at least 10 characters.');
      }
      const existing = await dbGet('vault', VAULT_RECORD_KEY);
      if (existing) throw new Error('A vault already exists in this browser.');

      const salt = randomBytes(16);
      const masterKey = await deriveMasterKey(passphrase, salt, KDF_ITERATIONS);
      const verifier = await seal(masterKey, utf8(VERIFIER_PLAINTEXT), 'vault:verifier');
      const now = new Date().toISOString();
      const next: VaultMeta = {
        version: 1,
        saltB64: bytesToB64(salt),
        iterations: KDF_ITERATIONS,
        verifier,
        settings: {
          ...DEFAULT_SETTINGS,
          displayName: displayName.trim() || DEFAULT_SETTINGS.displayName,
          defaultProfile,
        },
        createdAt: now,
        updatedAt: now,
      };
      await persistMeta(next);
      setKey(masterKey);
      setStatus('unlocked');
      lastActivity.current = Date.now();
      await recordAudit('vault.created', undefined, `profile=${defaultProfile}`);
      bumpRevision();
    },
    [bumpRevision, persistMeta],
  );

  const unlock = useCallback(
    async (passphrase: string) => {
      setLastError(null);
      const record = await dbGet<{ key: string; value: VaultMeta }>('vault', VAULT_RECORD_KEY);
      if (!record || !isVaultMeta(record.value)) {
        setStatus('empty');
        throw new Error('No vault exists in this browser.');
      }
      const salt = Uint8Array.from(atob(record.value.saltB64), (char) => char.charCodeAt(0));
      const masterKey = await deriveMasterKey(
        passphrase,
        salt,
        record.value.iterations ?? KDF_ITERATIONS,
      );
      try {
        const verifier = await open(masterKey, record.value.verifier, 'vault:verifier');
        if (fromUtf8(verifier) !== VERIFIER_PLAINTEXT) throw new Error('bad verifier');
      } catch {
        throw new Error('Incorrect passphrase.');
      }
      setKey(masterKey);
      setMeta(record.value);
      setStatus('unlocked');
      lastActivity.current = Date.now();
      await recordAudit('vault.unlocked');
      bumpRevision();
    },
    [bumpRevision],
  );

  const lock = useCallback(() => {
    setKey(null);
    setStatus((current) => (current === 'unlocked' ? 'locked' : current));
    void recordAudit('vault.locked');
  }, []);

  const updateSettings = useCallback(
    async (partial: Partial<VaultSettings>) => {
      if (!meta) return;
      const next: VaultMeta = {
        ...meta,
        settings: { ...meta.settings, ...partial },
        updatedAt: new Date().toISOString(),
      };
      await persistMeta(next);
      await recordAudit('settings.updated', undefined, Object.keys(partial).join(','));
      bumpRevision();
    },
    [bumpRevision, meta, persistMeta],
  );

  const changePassphrase = useCallback(
    async (current: string, next: string) => {
      if (!meta || !key) throw new Error('Unlock the vault first.');
      if (next.length < 10) throw new Error('Use a passphrase of at least 10 characters.');
      const currentSalt = Uint8Array.from(atob(meta.saltB64), (char) => char.charCodeAt(0));
      const currentKey = await deriveMasterKey(
        current,
        currentSalt,
        meta.iterations ?? KDF_ITERATIONS,
      );
      try {
        await open(currentKey, meta.verifier, 'vault:verifier');
      } catch {
        throw new Error('Current passphrase is incorrect.');
      }

      const salt = randomBytes(16);
      const nextKey = await deriveMasterKey(next, salt, KDF_ITERATIONS);
      const verifier = await seal(nextKey, utf8(VERIFIER_PLAINTEXT), 'vault:verifier');

      const files = await dbGetAll<FileRecord>('files');
      for (const file of files) {
        const raw = await unwrapRawKey(key, file.key, `filekey:${file.id}`);
        const fileMeta = await openJson<FileMeta>(key, file.meta, `filemeta:${file.id}`);
        await dbPut('files', {
          ...file,
          key: await wrapRawKey(nextKey, raw, `filekey:${file.id}`),
          meta: await sealJson(nextKey, fileMeta, `filemeta:${file.id}`),
        });
      }

      const threads = await dbGetAll<ThreadRecord>('threads');
      for (const thread of threads) {
        const threadMeta = await openJson<ThreadMeta>(key, thread.meta, `thread:${thread.id}`);
        await dbPut('threads', {
          ...thread,
          meta: await sealJson(nextKey, threadMeta, `thread:${thread.id}`),
        });
      }

      const messages = await dbGetAll<MessageRecord>('messages');
      for (const message of messages) {
        const raw = await unwrapRawKey(key, message.key, `messagekey:${message.id}`);
        await dbPut('messages', {
          ...message,
          key: await wrapRawKey(nextKey, raw, `messagekey:${message.id}`),
        });
      }

      const nextMeta: VaultMeta = {
        ...meta,
        saltB64: bytesToB64(salt),
        iterations: KDF_ITERATIONS,
        verifier,
        updatedAt: new Date().toISOString(),
      };
      await persistMeta(nextMeta);
      setKey(nextKey);
      await recordAudit('vault.passphrase_changed');
      bumpRevision();
    },
    [bumpRevision, key, meta, persistMeta],
  );

  const wipe = useCallback(async () => {
    await deleteDatabase();
    setKey(null);
    setMeta(null);
    setStatus('empty');
    window.location.reload();
  }, []);

  useEffect(() => {
    if (status !== 'unlocked') return;
    const mark = () => touch();
    window.addEventListener('pointerdown', mark);
    window.addEventListener('keydown', mark);
    window.addEventListener('touchstart', mark);
    const interval = window.setInterval(() => {
      const limit = Math.max(1, settings.autoLockMinutes) * 60_000;
      if (Date.now() - lastActivity.current > limit) {
        lock();
      }
    }, 15_000);
    return () => {
      window.removeEventListener('pointerdown', mark);
      window.removeEventListener('keydown', mark);
      window.removeEventListener('touchstart', mark);
      window.clearInterval(interval);
    };
  }, [lock, settings.autoLockMinutes, status, touch]);

  useEffect(() => {
    if (status !== 'unlocked') return;
    const onHidden = () => {
      if (document.visibilityState === 'hidden') touch();
    };
    document.addEventListener('visibilitychange', onHidden);
    return () => document.removeEventListener('visibilitychange', onHidden);
  }, [status, touch]);

  const value = useMemo<VaultContextValue>(
    () => ({
      status,
      meta,
      settings,
      key,
      revision,
      lastError,
      bumpRevision,
      createVault,
      unlock,
      lock,
      updateSettings,
      changePassphrase,
      wipe,
    }),
    [
      status,
      meta,
      settings,
      key,
      revision,
      lastError,
      bumpRevision,
      createVault,
      unlock,
      lock,
      updateSettings,
      changePassphrase,
      wipe,
    ],
  );

  return <VaultContext.Provider value={value}>{children}</VaultContext.Provider>;
}

export function useVault(): VaultContextValue {
  const context = useContext(VaultContext);
  if (!context) throw new Error('useVault must be used inside VaultProvider.');
  return context;
}

export async function loadFileMeta(
  key: CryptoKey,
  file: FileRecord,
): Promise<{ meta: FileMeta; rawKey: Uint8Array<ArrayBuffer> }> {
  const rawKey = await unwrapRawKey(key, file.key, `filekey:${file.id}`);
  const meta = await openJson<FileMeta>(key, file.meta, `filemeta:${file.id}`);
  return { meta, rawKey };
}

export async function readMessage(
  key: CryptoKey,
  message: MessageRecord,
): Promise<MessageBody> {
  const raw = await unwrapRawKey(key, message.key, `messagekey:${message.id}`);
  const messageKey = await importAesKey(raw);
  return openJson<MessageBody>(messageKey, message.body, `message:${message.id}`);
}

export async function deleteFileCascade(id: string): Promise<void> {
  await dbDelete('files', id);
  await dbDelete('blobs', id);
}
