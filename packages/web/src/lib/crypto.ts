import type {
  Container,
  ContainerChunk,
  FileMeta,
  ProfileLevel,
  Sealed,
  SharePayload,
} from './types';

type Bytes = Uint8Array<ArrayBuffer>;

const encoder = new TextEncoder();
const decoder = new TextDecoder();
const KDF_ITERATIONS = 210_000;

export const VERIFIER_PLAINTEXT = 'cryptavault:verifier:v1';

export function utf8(value: string): Bytes {
  return new Uint8Array(encoder.encode(value));
}

export function fromUtf8(value: Bytes): string {
  return decoder.decode(value);
}

export function randomBytes(length: number): Bytes {
  return globalThis.crypto.getRandomValues(new Uint8Array(length));
}

export function bytesToB64(bytes: Bytes): string {
  let binary = '';
  const step = 0x8000;
  for (let i = 0; i < bytes.length; i += step) {
    binary += String.fromCharCode(...bytes.subarray(i, i + step));
  }
  return btoa(binary);
}

export function b64ToBytes(value: string): Bytes {
  const binary = atob(value);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    out[i] = binary.charCodeAt(i);
  }
  return out;
}

export function bytesToB64Url(bytes: Bytes): string {
  return bytesToB64(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

export function b64UrlToBytes(value: string): Bytes {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/');
  return b64ToBytes(padded + '='.repeat((4 - (padded.length % 4)) % 4));
}

export async function sha256Hex(bytes: Bytes): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function deriveMasterKey(
  passphrase: string,
  salt: Bytes,
  iterations = KDF_ITERATIONS,
): Promise<CryptoKey> {
  const material = await globalThis.crypto.subtle.importKey(
    'raw',
    utf8(passphrase),
    'PBKDF2',
    false,
    ['deriveKey'],
  );
  return globalThis.crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt,
      iterations,
      hash: 'SHA-256',
    },
    material,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

export async function importAesKey(raw: Bytes, extractable = false): Promise<CryptoKey> {
  return globalThis.crypto.subtle.importKey('raw', raw, 'AES-GCM', extractable, [
    'encrypt',
    'decrypt',
  ]);
}

export async function seal(
  key: CryptoKey,
  plaintext: Bytes,
  aad?: string,
): Promise<Sealed> {
  const iv = randomBytes(12);
  const algorithm: AesGcmParams = aad
    ? { name: 'AES-GCM', iv, additionalData: utf8(aad) }
    : { name: 'AES-GCM', iv };
  const ciphertext = await globalThis.crypto.subtle.encrypt(algorithm, key, plaintext);
  return { ivB64: bytesToB64(iv), ctB64: bytesToB64(new Uint8Array(ciphertext)) };
}

export async function open(
  key: CryptoKey,
  sealed: Sealed,
  aad?: string,
): Promise<Bytes> {
  const iv = b64ToBytes(sealed.ivB64);
  const algorithm: AesGcmParams = aad
    ? { name: 'AES-GCM', iv, additionalData: utf8(aad) }
    : { name: 'AES-GCM', iv };
  const plaintext = await globalThis.crypto.subtle.decrypt(
    algorithm,
    key,
    b64ToBytes(sealed.ctB64),
  );
  return new Uint8Array(plaintext);
}

export async function sealJson<T>(
  key: CryptoKey,
  value: T,
  aad?: string,
): Promise<Sealed> {
  return seal(key, utf8(JSON.stringify(value)), aad);
}

export async function openJson<T>(
  key: CryptoKey,
  sealed: Sealed,
  aad?: string,
): Promise<T> {
  return JSON.parse(fromUtf8(await open(key, sealed, aad))) as T;
}

export function generateRawKey(): Bytes {
  return randomBytes(32);
}

export async function wrapRawKey(
  masterKey: CryptoKey,
  raw: Bytes,
  aad: string,
): Promise<Sealed> {
  return seal(masterKey, raw, aad);
}

export async function unwrapRawKey(
  masterKey: CryptoKey,
  sealed: Sealed,
  aad: string,
): Promise<Bytes> {
  return open(masterKey, sealed, aad);
}

export function compressionSupported(): boolean {
  return (
    typeof CompressionStream !== 'undefined' && typeof DecompressionStream !== 'undefined'
  );
}

export async function compress(bytes: Bytes): Promise<Bytes> {
  if (!compressionSupported()) return bytes;
  const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream('gzip'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

export async function decompress(bytes: Bytes): Promise<Bytes> {
  if (!compressionSupported()) return bytes;
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

function shouldCompressFile(file: File): boolean {
  const type = file.type.toLowerCase();
  const name = file.name.toLowerCase();
  const preCompressed = [
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
    'video/',
    'audio/',
    'application/zip',
    'application/gzip',
    'application/x-7z',
    'application/pdf',
  ];
  if (preCompressed.some((prefix) => type.startsWith(prefix))) return false;
  if (/\.(jpg|jpeg|png|webp|gif|mp4|mkv|mp3|flac|ogg|zip|gz|xz|7z|pdf)$/.test(name)) {
    return false;
  }
  return (
    type.startsWith('text/') ||
    /\.(txt|md|json|csv|tsv|xml|html|css|js|ts|tsx|jsx|py|rs|go|java|sql|yaml|yml|log)$/.test(
      name,
    ) ||
    file.size < 512 * 1024
  );
}

export interface FileKeyMaterial {
  key: CryptoKey;
  raw: Bytes;
}

export async function createFileKey(): Promise<FileKeyMaterial> {
  const raw = generateRawKey();
  const key = await importAesKey(raw, true);
  return { key, raw };
}

export interface EncryptFileResult {
  container: Container;
  meta: FileMeta;
  rawKey: Bytes;
}

export async function encryptFile(
  file: File,
  profile: ProfileLevel,
  chunkSize: number,
  compressOverride: boolean | null,
  onProgress?: (fraction: number) => void,
): Promise<EncryptFileResult> {
  const fileId = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  const fileKey = await createFileKey();
  const original = new Uint8Array(await file.arrayBuffer());
  const hash = await sha256Hex(original);

  const useCompression = compressOverride ?? shouldCompressFile(file);
  const payload =
    useCompression && compressionSupported() ? await compress(original) : original;
  const compression: 'none' | 'gzip' =
    useCompression && compressionSupported() ? 'gzip' : 'none';

  const chunks: ContainerChunk[] = [];
  const total = Math.max(1, Math.ceil(payload.length / chunkSize));
  for (let index = 0; index < total; index += 1) {
    const start = index * chunkSize;
    const slice = payload.subarray(start, Math.min(start + chunkSize, payload.length));
    const isFinal = index === total - 1 ? 1 : 0;
    const aad = `cryptavault:web:v1:${fileId}:${index}:${isFinal}`;
    const sealed = await seal(fileKey.key, slice, aad);
    chunks.push({ i: index, f: isFinal, iv: sealed.ivB64, ct: sealed.ctB64 });
    onProgress?.((index + 1) / total);
  }

  const container: Container = {
    magic: 'CVW1',
    v: 1,
    fileId,
    createdAt,
    profile,
    compression,
    chunkSize,
    chunks,
  };

  return {
    container,
    rawKey: fileKey.raw,
    meta: {
      name: file.name,
      type: file.type || 'application/octet-stream',
      size: file.size,
      hash,
      chunkCount: chunks.length,
      compression,
      profile,
      createdAt,
    },
  };
}

export async function decryptContainer(
  container: Container,
  rawKey: Bytes,
  onProgress?: (fraction: number) => void,
): Promise<Bytes> {
  if (container.magic !== 'CVW1' || container.v !== 1) {
    throw new Error('Unsupported container format.');
  }
  const key = await importAesKey(rawKey, false);
  const parts: Bytes[] = [];
  const total = Math.max(1, container.chunks.length);
  for (let index = 0; index < container.chunks.length; index += 1) {
    const chunk = container.chunks[index];
    const aad = `cryptavault:web:v1:${container.fileId}:${chunk.i}:${chunk.f}`;
    parts.push(await open(key, { ivB64: chunk.iv, ctB64: chunk.ct }, aad));
    onProgress?.((index + 1) / total);
  }
  const joined = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
  let offset = 0;
  for (const part of parts) {
    joined.set(part, offset);
    offset += part.length;
  }
  return container.compression === 'gzip' ? decompress(joined) : joined;
}

export function containerToB64(container: Container): string {
  return bytesToB64(utf8(JSON.stringify(container)));
}

export function containerFromB64(value: string): Container {
  return JSON.parse(fromUtf8(b64ToBytes(value))) as Container;
}

export interface BuildShareOptions {
  meta: FileMeta;
  container: Container;
  rawKey: Bytes;
  passphrase?: string;
  iterations?: number;
}

export async function buildShare(options: BuildShareOptions): Promise<{
  payload: SharePayload;
  shareRawKey?: Bytes;
}> {
  const { meta, container, rawKey, passphrase } = options;
  let shareKey: CryptoKey;
  let shareRawKey: Bytes | undefined;
  let saltB64: string | undefined;
  let kdf: 'raw' | 'pbkdf2';

  if (passphrase && passphrase.length > 0) {
    const salt = randomBytes(16);
    saltB64 = bytesToB64(salt);
    kdf = 'pbkdf2';
    shareKey = await deriveMasterKey(passphrase, salt, options.iterations ?? KDF_ITERATIONS);
  } else {
    shareRawKey = generateRawKey();
    shareKey = await importAesKey(shareRawKey, false);
    kdf = 'raw';
  }

  const wrapped = await seal(shareKey, rawKey, 'sharekey:v1');
  const payload: SharePayload = {
    v: 1,
    name: meta.name,
    type: meta.type,
    size: meta.size,
    hash: meta.hash,
    profile: meta.profile,
    compression: meta.compression,
    chunkCount: meta.chunkCount,
    createdAt: meta.createdAt,
    containerB64: containerToB64(container),
    key: wrapped,
    kdf,
    saltB64,
    iterations: kdf === 'pbkdf2' ? (options.iterations ?? KDF_ITERATIONS) : undefined,
  };
  return { payload, shareRawKey };
}

export function sharePayloadToken(payload: SharePayload): string {
  return bytesToB64Url(utf8(JSON.stringify(payload)));
}

export function shareBaseUrl(): string {
  const base = import.meta.env.BASE_URL || '/';
  const origin = window.location.origin;
  const path = base.endsWith('/') ? base : `${base}/`;
  return `${origin}${path}#/share`;
}

export function buildShareLink(payload: SharePayload, shareRawKey?: Bytes): string {
  const token = sharePayloadToken(payload);
  const url = `${shareBaseUrl()}?d=${token}`;
  return shareRawKey ? `${url}&k=${bytesToB64Url(shareRawKey)}` : url;
}

export function buildShareBundle(payload: SharePayload, shareRawKey?: Bytes): string {
  return JSON.stringify(
    {
      v: 1,
      kind: 'cryptavault-share-bundle',
      payload,
      keyB64Url: shareRawKey ? bytesToB64Url(shareRawKey) : undefined,
    },
    null,
    2,
  );
}

export interface ParsedShare {
  payload: SharePayload;
  shareRawKey?: Bytes;
}

export function parseShareToken(token: string): SharePayload {
  return JSON.parse(fromUtf8(b64UrlToBytes(token))) as SharePayload;
}

export function parseShareBundle(text: string): ParsedShare {
  const parsed = JSON.parse(text) as {
    kind?: string;
    payload?: SharePayload;
    keyB64Url?: string;
  };
  if (parsed.kind !== 'cryptavault-share-bundle' || !parsed.payload) {
    throw new Error('This file is not a CryptaVault share bundle.');
  }
  return {
    payload: parsed.payload,
    shareRawKey: parsed.keyB64Url ? b64UrlToBytes(parsed.keyB64Url) : undefined,
  };
}

export function readShareFromLocation(): ParsedShare | null {
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash;
  const queryIndex = hash.indexOf('?');
  if (queryIndex < 0) return null;
  const params = new URLSearchParams(hash.slice(queryIndex + 1));
  const token = params.get('d');
  if (!token) return null;
  try {
    const payload = parseShareToken(token);
    const key = params.get('k');
    return {
      payload,
      shareRawKey: key ? b64UrlToBytes(key) : undefined,
    };
  } catch {
    return null;
  }
}

export async function decryptShare(
  parsed: ParsedShare,
  passphrase: string | undefined,
  onProgress?: (fraction: number) => void,
): Promise<Bytes> {
  const { payload } = parsed;
  let shareKey: CryptoKey;
  if (payload.kdf === 'pbkdf2') {
    if (!passphrase) throw new Error('This share requires a passphrase.');
    if (!payload.saltB64) throw new Error('Share is missing its KDF salt.');
    shareKey = await deriveMasterKey(
      passphrase,
      b64ToBytes(payload.saltB64),
      payload.iterations ?? KDF_ITERATIONS,
    );
  } else {
    if (!parsed.shareRawKey) throw new Error('This share link is missing its key.');
    shareKey = await importAesKey(parsed.shareRawKey, false);
  }

  const rawKey = await open(shareKey, payload.key, 'sharekey:v1');
  const container = containerFromB64(payload.containerB64);
  const plaintext = await decryptContainer(container, rawKey, onProgress);
  const hash = await sha256Hex(plaintext);
  if (hash !== payload.hash) {
    throw new Error('Integrity check failed: the decrypted file does not match its hash.');
  }
  return plaintext;
}

export function passwordStrength(value: string): {
  score: number;
  label: string;
  tone: string;
} {
  let score = 0;
  if (value.length >= 10) score += 1;
  if (value.length >= 16) score += 1;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value)) score += 1;
  if (score <= 1) return { score, label: 'Very weak', tone: 'text-rose-400' };
  if (score === 2) return { score, label: 'Weak', tone: 'text-amber-400' };
  if (score === 3) return { score, label: 'Fair', tone: 'text-yellow-300' };
  if (score === 4) return { score, label: 'Strong', tone: 'text-emerald-400' };
  return { score, label: 'Excellent', tone: 'text-cyan-300' };
}

export { KDF_ITERATIONS };
