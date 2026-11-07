import { useEffect, useState } from 'react';
import { dbGetAll } from './db';
import { importAesKey, openJson, unwrapRawKey } from './crypto';
import { useVault, type ThreadMeta } from './vault';
import type {
  AuditEvent,
  FileMeta,
  FileRecord,
  MessageBody,
  MessageRecord,
  ShareRecord,
  ThreadRecord,
} from './types';

export interface DecryptedFile {
  record: FileRecord;
  meta: FileMeta;
}

export function useFiles(): { files: DecryptedFile[]; loading: boolean } {
  const { key, revision } = useVault();
  const [files, setFiles] = useState<DecryptedFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!key) {
      setFiles([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    void (async () => {
      try {
        const records = await dbGetAll<FileRecord>('files');
        const decrypted = await Promise.all(
          records.map(async (record) => ({
            record,
            meta: await openJson<FileMeta>(key, record.meta, `filemeta:${record.id}`),
          })),
        );
        if (!cancelled) {
          decrypted.sort((a, b) => b.meta.createdAt.localeCompare(a.meta.createdAt));
          setFiles(decrypted);
        }
      } catch {
        if (!cancelled) setFiles([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [key, revision]);

  return { files, loading };
}

export function useShares(): { shares: ShareRecord[]; loading: boolean } {
  const { revision } = useVault();
  const [shares, setShares] = useState<ShareRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const records = await dbGetAll<ShareRecord>('shares');
        if (!cancelled) {
          records.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
          setShares(records);
        }
      } catch {
        if (!cancelled) setShares([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [revision]);

  return { shares, loading };
}

export function useAuditEvents(limit?: number): {
  events: AuditEvent[];
  loading: boolean;
} {
  const { revision } = useVault();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const records = await dbGetAll<AuditEvent>('audit');
        records.sort((a, b) => b.at.localeCompare(a.at));
        if (!cancelled) setEvents(limit ? records.slice(0, limit) : records);
      } catch {
        if (!cancelled) setEvents([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [limit, revision]);

  return { events, loading };
}

export interface DecryptedThread {
  record: ThreadRecord;
  meta: ThreadMeta;
}

export function useThreads(): { threads: DecryptedThread[]; loading: boolean } {
  const { key, revision } = useVault();
  const [threads, setThreads] = useState<DecryptedThread[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!key) {
      setThreads([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    void (async () => {
      try {
        const records = await dbGetAll<ThreadRecord>('threads');
        const decrypted = await Promise.all(
          records.map(async (record) => ({
            record,
            meta: await openJson<ThreadMeta>(key, record.meta, `thread:${record.id}`),
          })),
        );
        if (!cancelled) {
          decrypted.sort((a, b) => a.meta.name.localeCompare(b.meta.name));
          setThreads(decrypted);
        }
      } catch {
        if (!cancelled) setThreads([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [key, revision]);

  return { threads, loading };
}

export function useMessages(threadId: string | null): {
  messages: MessageRecord[];
  bodies: Record<string, MessageBody>;
  loading: boolean;
} {
  const { key, revision } = useVault();
  const [messages, setMessages] = useState<MessageRecord[]>([]);
  const [bodies, setBodies] = useState<Record<string, MessageBody>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!key || !threadId) {
      setMessages([]);
      setBodies({});
      return;
    }
    setLoading(true);
    void (async () => {
      try {
        const all = await dbGetAll<MessageRecord>('messages');
        const filtered = all
          .filter((message) => message.threadId === threadId)
          .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
        const decrypted: Record<string, MessageBody> = {};
        await Promise.all(
          filtered.map(async (message) => {
            const raw = await unwrapRawKey(key, message.key, `messagekey:${message.id}`);
            const messageKey = await importAesKey(raw);
            decrypted[message.id] = await openJson<MessageBody>(
              messageKey,
              message.body,
              `message:${message.id}`,
            );
          }),
        );
        if (!cancelled) {
          setMessages(filtered);
          setBodies(decrypted);
        }
      } catch {
        if (!cancelled) {
          setMessages([]);
          setBodies({});
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [key, revision, threadId]);

  return { messages, bodies, loading };
}
