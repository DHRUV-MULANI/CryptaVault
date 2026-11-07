import { useEffect, useState } from 'react';
import {
  KeyRound,
  LockKeyhole,
  MessageSquareLock,
  Plus,
  Send,
  ShieldCheck,
  Trash2,
  UserRound,
} from 'lucide-react';
import { useMessages, useThreads } from '../lib/hooks';
import { useVault } from '../lib/vault';
import { dbDelete, dbGetAll, dbPut } from '../lib/db';
import { recordAudit } from '../lib/audit';
import {
  generateRawKey,
  importAesKey,
  sealJson,
  wrapRawKey,
} from '../lib/crypto';
import {
  EmptyState,
  Modal,
  PageHeader,
  Spinner,
  useToast,
} from '../components/ui';
import { classNames, formatDate, relativeTime } from '../lib/format';
import type { MessageRecord } from '../lib/types';

export default function MessagesPage(): JSX.Element {
  const { key, settings, bumpRevision } = useVault();
  const { threads, loading: threadsLoading } = useThreads();
  const { notify } = useToast();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { messages, bodies, loading } = useMessages(selectedId);
  const [newOpen, setNewOpen] = useState(false);
  const [contactName, setContactName] = useState('');
  const [contactNote, setContactNote] = useState('');
  const [subject, setSubject] = useState('');
  const [bodyText, setBodyText] = useState('');
  const [sending, setSending] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    if (!selectedId && threads.length > 0) {
      setSelectedId(threads[0].record.id);
    }
    if (selectedId && !threads.some((thread) => thread.record.id === selectedId)) {
      setSelectedId(threads[0]?.record.id ?? null);
    }
  }, [selectedId, threads]);

  const selected = threads.find((thread) => thread.record.id === selectedId) ?? null;

  async function createThread(): Promise<void> {
    if (!key || !contactName.trim()) return;
    const id = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    await dbPut('threads', {
      id,
      createdAt,
      meta: await sealJson(
        key,
        { name: contactName.trim(), note: contactNote.trim() || undefined },
        `thread:${id}`,
      ),
    });
    await recordAudit('thread.created', id);
    bumpRevision();
    setSelectedId(id);
    setNewOpen(false);
    setContactName('');
    setContactNote('');
    notify('Encrypted conversation created.', 'success');
  }

  async function sendMessage(): Promise<void> {
    if (!key || !selectedId || !bodyText.trim()) return;
    setSending(true);
    try {
      const id = crypto.randomUUID();
      const createdAt = new Date().toISOString();
      const raw = generateRawKey();
      const messageKey = await importAesKey(raw, false);
      const record: MessageRecord = {
        id,
        threadId: selectedId,
        createdAt,
        direction: 'out',
        body: await sealJson(
          messageKey,
          { subject: subject.trim() || '(no subject)', body: bodyText.trim() },
          `message:${id}`,
        ),
        key: await wrapRawKey(key, raw, `messagekey:${id}`),
      };
      await dbPut('messages', record);
      await recordAudit('message.encrypted', id, `thread=${selectedId}`);
      bumpRevision();
      setSubject('');
      setBodyText('');
      notify('Message encrypted and stored locally.', 'success');
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Could not encrypt message.', 'error');
    } finally {
      setSending(false);
    }
  }

  async function deleteThread(): Promise<void> {
    if (!selectedId) return;
    const all = await dbGetAll<MessageRecord>('messages');
    await Promise.all(
      all
        .filter((message) => message.threadId === selectedId)
        .map((message) => dbDelete('messages', message.id)),
    );
    await dbDelete('threads', selectedId);
    await recordAudit('thread.deleted', selectedId);
    bumpRevision();
    setSelectedId(null);
    setDeleteOpen(false);
    notify('Conversation and its encrypted messages deleted.', 'success');
  }

  if (!settings.messagingEnabled) {
    return (
      <div className="animate-in">
        <PageHeader
          eyebrow="Encrypted messages"
          title="Messaging is disabled"
          description="An administrator flag has disabled the encrypted messaging workspace for this vault."
        />
        <EmptyState
          icon={<MessageSquareLock className="h-8 w-8" />}
          title="Encrypted messaging is turned off"
          description="Enable it in the Admin console or Settings to create encrypted conversations."
          action={
            <a href="#/admin" className="btn-primary">
              Open admin console
            </a>
          }
        />
      </div>
    );
  }

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Encrypted messages"
        title="Per-message keys, local ciphertext"
        description="Each message body is sealed with its own AES-256-GCM key and wrapped by your master key. This static deployment stores conversations locally; cross-device delivery uses the optional API relay."
        action={
          <button className="btn-primary" onClick={() => setNewOpen(true)}>
            <Plus className="h-4 w-4" /> New conversation
          </button>
        }
      />

      <div className="mb-3 flex items-center gap-2 rounded-xl border border-cyan-400/15 bg-cyan-500/5 px-3 py-2 text-[11px] text-cyan-100/80">
        <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
        Local encrypted messaging demo. On a static deployment, messages never leave this browser.
        The API package includes authenticated share and user routes for a real relay.
      </div>

      {threadsLoading ? (
        <div className="card py-16 text-center">
          <Spinner label="Unlocking conversation metadata…" />
        </div>
      ) : threads.length === 0 ? (
        <EmptyState
          icon={<MessageSquareLock className="h-8 w-8" />}
          title="No encrypted conversations"
          description="Create a conversation to store encrypted notes with a subject and body. Contact labels are encrypted with the same master key."
          action={
            <button className="btn-primary" onClick={() => setNewOpen(true)}>
              <Plus className="h-4 w-4" /> New conversation
            </button>
          }
        />
      ) : (
        <div className="grid min-h-[560px] gap-4 lg:grid-cols-[300px_1fr]">
          <div className="card !p-0">
            <div className="border-b border-white/8 px-4 py-3">
              <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Conversations
              </div>
            </div>
            <div className="max-h-[520px] overflow-y-auto p-2 scroll-thin">
              {threads.map((thread) => (
                <button
                  key={thread.record.id}
                  onClick={() => setSelectedId(thread.record.id)}
                  className={classNames(
                    'mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors',
                    selectedId === thread.record.id
                      ? 'bg-cyan-500/10 text-cyan-100'
                      : 'text-slate-300 hover:bg-white/5',
                  )}
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5 text-slate-300">
                    <UserRound className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{thread.meta.name}</span>
                    <span className="block truncate text-[10px] text-slate-500">
                      {thread.meta.note || 'Encrypted conversation'} ·{' '}
                      {relativeTime(thread.record.createdAt)}
                    </span>
                  </span>
                  <LockKeyhole className="h-3.5 w-3.5 text-emerald-300/70" />
                </button>
              ))}
            </div>
          </div>

          <div className="card flex min-h-[560px] flex-col !p-0">
            {selected ? (
              <>
                <div className="flex items-center justify-between gap-3 border-b border-white/8 px-4 py-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-white">
                      {selected.meta.name}
                    </div>
                    <div className="truncate text-[11px] text-slate-500">
                      {selected.meta.note || 'Contact label and note are encrypted'}
                    </div>
                  </div>
                  <button
                    className="btn-ghost !p-2 text-rose-300 hover:text-rose-200"
                    onClick={() => setDeleteOpen(true)}
                    title="Delete conversation"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <div className="flex-1 space-y-3 overflow-y-auto p-4 scroll-thin">
                  {loading ? (
                    <Spinner label="Decrypting messages…" />
                  ) : messages.length === 0 ? (
                    <div className="flex h-full flex-col items-center justify-center py-16 text-center">
                      <MessageSquareLock className="mb-3 h-8 w-8 text-slate-600" />
                      <p className="text-sm text-slate-400">No messages yet.</p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        Write the first encrypted note below.
                      </p>
                    </div>
                  ) : (
                    messages.map((message) => {
                      const decoded = bodies[message.id];
                      return (
                        <div
                          key={message.id}
                          className="rounded-xl border border-white/8 bg-white/[0.02] p-3.5"
                        >
                          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                            <div className="text-sm font-medium text-slate-100">
                              {decoded?.subject ?? 'Encrypted message'}
                            </div>
                            <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                              <KeyRound className="h-3 w-3 text-cyan-300/70" />
                              per-message key · {formatDate(message.createdAt)}
                            </div>
                          </div>
                          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
                            {decoded?.body ?? 'Decrypting…'}
                          </p>
                          <div className="mono mt-2 text-[9px] text-slate-600">
                            id {message.id.slice(0, 18)}… · {message.direction}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                <div className="border-t border-white/8 p-4">
                  <input
                    className="input mb-2"
                    placeholder="Subject"
                    value={subject}
                    onChange={(event) => setSubject(event.target.value)}
                  />
                  <textarea
                    className="input min-h-[84px] resize-y"
                    placeholder="Write an encrypted message body…"
                    value={bodyText}
                    onChange={(event) => setBodyText(event.target.value)}
                  />
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <span className="text-[10px] text-slate-500">
                      AES-256-GCM · fresh key per message
                    </span>
                    <button
                      className="btn-primary"
                      onClick={() => void sendMessage()}
                      disabled={sending || !bodyText.trim()}
                    >
                      {sending ? <Spinner /> : <Send className="h-4 w-4" />}
                      {sending ? 'Encrypting…' : 'Encrypt & send'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-1 items-center justify-center text-sm text-slate-500">
                Select a conversation.
              </div>
            )}
          </div>
        </div>
      )}

      <Modal
        open={newOpen}
        onClose={() => setNewOpen(false)}
        title="New encrypted conversation"
        subtitle="The contact label and note are encrypted before they are stored."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setNewOpen(false)}>
              Cancel
            </button>
            <button
              className="btn-primary"
              onClick={() => void createThread()}
              disabled={!contactName.trim()}
            >
              <Plus className="h-4 w-4" /> Create
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-300">Contact label</span>
            <input
              className="input"
              value={contactName}
              onChange={(event) => setContactName(event.target.value)}
              placeholder="e.g. Research partner"
              autoFocus
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-300">
              Note (optional)
            </span>
            <input
              className="input"
              value={contactNote}
              onChange={(event) => setContactNote(event.target.value)}
              placeholder="Context for this conversation"
            />
          </label>
          <div className="text-[11px] text-slate-500">
            This demo does not deliver messages to other devices. It demonstrates the
            client-side encryption and storage model used by the API relay.
          </div>
        </div>
      </Modal>

      <Modal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete this conversation?"
        subtitle="The encrypted messages and contact metadata will be removed from this browser."
        footer={
          <>
            <button className="btn-secondary" onClick={() => setDeleteOpen(false)}>
              Cancel
            </button>
            <button className="btn-danger" onClick={() => void deleteThread()}>
              <Trash2 className="h-4 w-4" /> Delete
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-300">
          {selected ? selected.meta.name : 'This conversation'} and all of its messages will be
          deleted.
        </p>
      </Modal>
    </div>
  );
}
