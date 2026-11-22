import { MessageSquareLock, ShieldCheck } from 'lucide-react';
import { Card, PageHeader } from '../components/ui';

export default function MessagesPage(): JSX.Element {
  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Encrypted messages"
        title="Messaging (framework placeholder)"
        description="The dynamic framework currently focuses on authenticated workspaces, encrypted files, and server-enforced shares. End-to-end messaging relay is not wired into the live API yet."
      />
      <Card className="max-w-3xl">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-300"><MessageSquareLock className="h-5 w-5" /></span>
          <div>
            <h2 className="text-base font-semibold text-white">Not yet wired to dynamic backend</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              This page is intentionally no longer using local IndexedDB demo storage. To make messaging fully dynamic, the API needs message/thread routes, ciphertext storage, membership authorization, and delivery/sync semantics. The existing zero-knowledge model can be reused: per-message keys wrapped by user keys.
            </p>
            <div className="mt-4 rounded-xl border border-emerald-400/20 bg-emerald-500/5 px-3 py-2.5 text-xs text-emerald-100">
              <ShieldCheck className="mr-1.5 inline h-3.5 w-3.5" />
              No plaintext message data is stored by this placeholder.
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
