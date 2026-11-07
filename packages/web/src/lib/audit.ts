import { dbPut } from './db';
import type { AuditEvent } from './types';

export async function recordAudit(
  action: string,
  targetId?: string,
  detail?: string,
): Promise<AuditEvent> {
  const event: AuditEvent = {
    id: crypto.randomUUID(),
    at: new Date().toISOString(),
    action,
    targetId,
    detail,
  };
  await dbPut('audit', event);
  return event;
}
