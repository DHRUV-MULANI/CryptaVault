export type ProfileLevel =
  | 'PERFORMANCE'
  | 'STANDARD'
  | 'BALANCED'
  | 'STRONG'
  | 'PQ_STRONG'
  | 'MAXIMUM';

export interface Sealed {
  ivB64: string;
  ctB64: string;
}

export interface VaultSettings {
  displayName: string;
  defaultProfile: ProfileLevel;
  autoLockMinutes: number;
  shareTtlHours: number;
  allowExperimental: boolean;
  compressByDefault: boolean;
  theme: 'dark' | 'light';
  messagingEnabled: boolean;
  sharingEnabled: boolean;
}

export interface VaultMeta {
  version: 1;
  saltB64: string;
  iterations: number;
  verifier: Sealed;
  settings: VaultSettings;
  createdAt: string;
  updatedAt: string;
}

export interface FileMeta {
  name: string;
  type: string;
  size: number;
  hash: string;
  chunkCount: number;
  compression: 'none' | 'gzip';
  profile: ProfileLevel;
  createdAt: string;
}

export interface FileRecord {
  id: string;
  createdAt: string;
  meta: Sealed;
  key: Sealed;
}

export interface StoredBlob {
  id: string;
  container: string;
}

export interface ShareRecord {
  id: string;
  fileId: string;
  createdAt: string;
  expiresAt: string;
  revoked: boolean;
  mode: 'link' | 'passphrase' | 'bundle';
  hasPassphrase: boolean;
  bytes: number;
  label: string;
}

export interface ThreadRecord {
  id: string;
  createdAt: string;
  meta: Sealed;
}

export interface MessageRecord {
  id: string;
  threadId: string;
  createdAt: string;
  direction: 'out' | 'in';
  body: Sealed;
  key: Sealed;
}

export interface MessageBody {
  subject: string;
  body: string;
}

export interface AuditEvent {
  id: string;
  at: string;
  action: string;
  targetId?: string;
  detail?: string;
}

export interface ContainerChunk {
  i: number;
  f: number;
  iv: string;
  ct: string;
}

export interface Container {
  magic: 'CVW1';
  v: 1;
  fileId: string;
  createdAt: string;
  profile: ProfileLevel;
  compression: 'none' | 'gzip';
  chunkSize: number;
  chunks: ContainerChunk[];
}

export interface SharePayload {
  v: 1;
  name: string;
  type: string;
  size: number;
  hash: string;
  profile: ProfileLevel;
  compression: 'none' | 'gzip';
  chunkCount: number;
  createdAt: string;
  containerB64: string;
  key: Sealed;
  kdf: 'raw' | 'pbkdf2';
  saltB64?: string;
  iterations?: number;
}
