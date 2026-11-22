import { useEffect, useState } from 'react';
import { api, type ApiFile, type ApiShare } from './api';
import { openJson, unwrapRawKey } from './crypto';
import { useVault, type ThreadMeta } from './vault';
import type { AuditEvent, FileMeta, FileRecord, MessageBody, MessageRecord, ShareRecord, ThreadRecord } from './types';

export interface DecryptedFile {
  record: FileRecord & { api: ApiFile };
  meta: FileMeta & { ciphertextSize?: number; deletedAt?: string | null; versionCount?: number; currentVersion?: number };
}

function toFileMeta(apiFile: ApiFile, meta: FileMeta): DecryptedFile['meta'] {
  return {
    ...meta,
    ciphertextSize: apiFile.ciphertext_size,
    deletedAt: apiFile.deleted_at,
    versionCount: apiFile.version_count,
    currentVersion: apiFile.current_version,
  };
}

export function useFiles(): { files: DecryptedFile[]; loading: boolean } {
  const { key, revision, currentWorkspace } = useVault();
  const [files, setFiles] = useState<DecryptedFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!key || !currentWorkspace) {
      setFiles([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    void (async () => {
      try {
        const records = await api.files.list(currentWorkspace.id);
        const decrypted = await Promise.all(
          records.map(async (record) => {
            const rawKey = await unwrapRawKey(
              key,
              { ivB64: record.wrapped_iv, ctB64: record.wrapped_key },
              `filekey:${record.id}`,
            );
            void rawKey; // raw key not needed for listing
            const meta = await openJson<FileMeta>(
              key,
              { ivB64: record.meta_iv, ctB64: record.encrypted_meta },
              `filemeta:${record.id}`,
            );
            return {
              record: { id: record.id, createdAt: record.created_at ?? '', meta: { ivB64: record.meta_iv, ctB64: record.encrypted_meta }, key: { ivB64: record.wrapped_iv, ctB64: record.wrapped_key }, api: record } as DecryptedFile['record'],
              meta: toFileMeta(record, meta),
            };
          }),
        );
        if (!cancelled) {
          decrypted.sort((a, b) => (b.meta.createdAt || '').localeCompare(a.meta.createdAt || ''));
          setFiles(decrypted);
        }
      } catch {
        if (!cancelled) setFiles([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [key, revision, currentWorkspace]);

  return { files, loading };
}

export function useShares(): { shares: ShareRecord[]; loading: boolean } {
  const { revision, status } = useVault();
  const [shares, setShares] = useState<ShareRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (status !== 'unlocked' && status !== 'locked') {
      setShares([]);
      setLoading(false);
      return;
    }
    void (async () => {
      try {
        const records = await api.shares.list();
        if (cancelled) return;
        const mapped: ShareRecord[] = records.map((r: ApiShare) => ({
          id: r.token,
          fileId: r.file_id,
          createdAt: r.created_at ?? '',
          expiresAt: r.expires_at ?? '',
          revoked: r.revoked,
          mode: r.password_protected ? 'passphrase' : 'link',
          hasPassphrase: r.password_protected,
          bytes: 0,
          label: r.share_url,
        }));
        mapped.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
        setShares(mapped);
      } catch {
        if (!cancelled) setShares([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [revision, status]);

  return { shares, loading };
}

export function useAuditEvents(limit?: number): { events: AuditEvent[]; loading: boolean } {
  const { revision } = useVault();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    // Dynamic backend audit endpoint exists but may differ; keep local empty-safe for now.
    setEvents([]);
    setLoading(false);
  }, [limit, revision]);
  return { events, loading };
}

export interface DecryptedThread { record: ThreadRecord; meta: ThreadMeta; }

export function useThreads(): { threads: DecryptedThread[]; loading: boolean } {
  return { threads: [], loading: false };
}

export function useMessages(_threadId: string | null): { messages: MessageRecord[]; bodies: Record<string, MessageBody>; loading: boolean } {
  return { messages: [], bodies: {}, loading: false };
}
