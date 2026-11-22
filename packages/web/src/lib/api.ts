const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '';

export const TOKEN_KEY = 'cryptavault.session.token';
export const WORKSPACE_KEY = 'cryptavault.current.workspace';

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getStoredWorkspaceId(): string | null {
  return localStorage.getItem(WORKSPACE_KEY);
}

export function setStoredWorkspaceId(id: string | null): void {
  if (id) localStorage.setItem(WORKSPACE_KEY, id);
  else localStorage.removeItem(WORKSPACE_KEY);
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function messageFromBody(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    const detail = record.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            const msg = (item as { msg?: unknown }).msg;
            return typeof msg === 'string' ? msg : JSON.stringify(item);
          }
          return String(item);
        })
        .join('; ');
    }
    if (typeof record.message === 'string') return record.message;
  }
  if (typeof body === 'string' && body.trim()) return body;
  return fallback;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      messageFromBody(body, `Request failed (${response.status})`),
      body,
    );
  }
  return body as T;
}

export interface ApiUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  suspended: boolean;
  quota_bytes: number;
  used_bytes: number;
  default_profile: string;
  created_at: string | null;
}

export interface ApiVault {
  salt_b64: string;
  check: { ivB64: string; ctB64: string };
  kdf_iterations: number;
}

export interface ApiWorkspace {
  id: string;
  name: string;
  owner_id: string;
  role: string;
  default_profile: string;
  storage_target: string | null;
  file_count: number;
  total_bytes: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ApiSession {
  access_token: string;
  token_type: string;
  user: ApiUser;
  vault: ApiVault;
  workspaces: ApiWorkspace[];
}

export interface ApiMe {
  user: ApiUser;
  vault: ApiVault;
  workspaces: ApiWorkspace[];
}

export interface ApiMember {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  joined_at: string | null;
}

export interface ApiFileVersion {
  id: string;
  file_id: string;
  version: number;
  encrypted_meta: string;
  meta_iv: string;
  wrapped_key: string;
  wrapped_iv: string;
  ciphertext_size: number;
  content_tag: string;
  profile: string;
  storage_target: string | null;
  storage_key: string;
  created_by: string | null;
  created_at: string | null;
}

export interface ApiFile {
  id: string;
  workspace_id: string;
  owner_id: string;
  current_version: number;
  version_count: number;
  deleted_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  encrypted_meta: string;
  meta_iv: string;
  wrapped_key: string;
  wrapped_iv: string;
  ciphertext_size: number;
  content_tag: string;
  profile: string;
  storage_target: string | null;
  storage_key: string;
}

export interface ApiShare {
  token: string;
  file_id: string;
  version: number;
  share_url: string;
  recipient_email: string | null;
  created_at: string | null;
  expires_at: string | null;
  max_uses: number;
  uses: number;
  remaining_uses: number;
  password_protected: boolean;
  pin_protected: boolean;
  revoked: boolean;
  pin?: string;
  owner_id?: string;
  ciphertext_size?: number;
  profile?: string;
}

export const api = {
  auth: {
    prelogin: (email: string) =>
      apiFetch<{ exists: boolean; auth_salt_b64: string; kdf_iterations: number }>(
        '/api/auth/prelogin',
        { method: 'POST', body: JSON.stringify({ email }) },
      ),
    register: (payload: {
      email: string;
      display_name: string;
      auth_salt_b64: string;
      auth_verifier: string;
      vault_salt_b64: string;
      vault_check: { ivB64: string; ctB64: string };
      kdf_iterations: number;
    }) => apiFetch<ApiSession>('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
    login: (payload: { email: string; auth_verifier: string }) =>
      apiFetch<ApiSession>('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
    me: () => apiFetch<ApiMe>('/api/auth/me'),
    updateMe: (payload: { display_name?: string; default_profile?: string }) =>
      apiFetch<ApiMe>('/api/auth/me', { method: 'PATCH', body: JSON.stringify(payload) }),
    logout: () => apiFetch<{ status: string }>('/api/auth/logout', { method: 'POST' }),
  },
  workspaces: {
    list: () => apiFetch<ApiWorkspace[]>('/api/workspaces'),
    create: (payload: { name: string; default_profile?: string; storage_target?: string | null }) =>
      apiFetch<ApiWorkspace>('/api/workspaces', { method: 'POST', body: JSON.stringify(payload) }),
    get: (id: string) => apiFetch<ApiWorkspace>(`/api/workspaces/${id}`),
    update: (id: string, payload: { name?: string; default_profile?: string; storage_target?: string | null }) =>
      apiFetch<ApiWorkspace>(`/api/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    remove: (id: string) => apiFetch<{ status: string; workspace_id: string }>(`/api/workspaces/${id}`, { method: 'DELETE' }),
    members: (id: string) => apiFetch<ApiMember[]>(`/api/workspaces/${id}/members`),
    addMember: (id: string, payload: { email: string; role: string }) =>
      apiFetch<{ status: string; user_id: string; role: string }>(`/api/workspaces/${id}/members`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    updateMember: (id: string, userId: string, payload: { role: string }) =>
      apiFetch<{ status: string; user_id: string; role: string }>(
        `/api/workspaces/${id}/members/${userId}`,
        { method: 'PATCH', body: JSON.stringify(payload) },
      ),
    removeMember: (id: string, userId: string) =>
      apiFetch<{ status: string; user_id: string }>(`/api/workspaces/${id}/members/${userId}`, {
        method: 'DELETE',
      }),
  },
  files: {
    list: (workspaceId: string) => apiFetch<ApiFile[]>(`/api/workspaces/${workspaceId}/files`),
    upload: async (workspaceId: string, form: FormData) => {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/files/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: form,
      });
      const body = await parseBody(response);
      if (!response.ok) throw new ApiError(response.status, messageFromBody(body, 'Upload failed'), body);
      return body as ApiFile;
    },
    download: async (fileId: string, version?: number) => {
      const token = getToken();
      const qs = version ? `?version=${version}` : '';
      const response = await fetch(`${API_URL}/api/files/${fileId}/download${qs}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) {
        const body = await parseBody(response);
        throw new ApiError(response.status, messageFromBody(body, 'Download failed'), body);
      }
      return new Uint8Array(await response.arrayBuffer());
    },
    versions: (fileId: string) => apiFetch<ApiFileVersion[]>(`/api/files/${fileId}/versions`),
    rename: (fileId: string, payload: { encrypted_meta: string; meta_iv: string }) =>
      apiFetch<ApiFile>(`/api/files/${fileId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    trash: (fileId: string) => apiFetch<{ status: string }>(`/api/files/${fileId}`, { method: 'DELETE' }),
    untrash: (fileId: string) => apiFetch<{ status: string }>(`/api/files/${fileId}/untrash`, { method: 'POST' }),
    restoreVersion: (fileId: string, version: number) =>
      apiFetch<ApiFile>(`/api/files/${fileId}/restore/${version}`, { method: 'POST' }),
    permanentDelete: (fileId: string) =>
      apiFetch<{ status: string }>(`/api/files/${fileId}/permanent`, { method: 'DELETE' }),
  },
  shares: {
    list: () => apiFetch<ApiShare[]>('/api/shares'),
    received: () => apiFetch<ApiShare[]>('/api/shares/received'),
    create: (payload: { file_id: string; version?: number; expires_at?: string | null; max_uses: number; password?: string | null; recipient_email?: string | null; pin?: string | null }) =>
      apiFetch<ApiShare>('/api/shares', { method: 'POST', body: JSON.stringify(payload) }),
    info: (token: string) => apiFetch<Record<string, unknown>>(`/api/shares/${token}`),
    download: async (token: string, password?: string, pin?: string) => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      const t = getToken();
      if (t) headers.Authorization = `Bearer ${t}`;
      const response = await fetch(`${API_URL}/api/shares/${token}/download`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...(password ? { password } : {}), ...(pin ? { pin } : {}) }),
      });
      if (!response.ok) {
        const body = await parseBody(response);
        throw new ApiError(response.status, messageFromBody(body, 'Share download failed'), body);
      }
      return new Uint8Array(await response.arrayBuffer());
    },
    updatePin: (token: string, pin?: string | null) =>
      apiFetch<ApiShare>(`/api/shares/${token}/pin`, { method: 'PATCH', body: JSON.stringify({ pin: pin ?? null }) }),
    regenerate: (token: string) =>
      apiFetch<ApiShare>(`/api/shares/${token}/regenerate`, { method: 'POST' }),
    revoke: (token: string) => apiFetch<{ status: string }>(`/api/shares/${token}`, { method: 'DELETE' }),
  },
  dashboard: {
    me: () => apiFetch<Record<string, unknown>>('/api/dashboard'),
    admin: () => apiFetch<Record<string, unknown>>('/api/dashboard/admin'),
  },
  admin: {
    users: () => apiFetch<ApiUser[]>('/api/admin/users'),
    updateUser: (id: string, payload: Record<string, unknown>) =>
      apiFetch<{ status: string; user: ApiUser }>(`/api/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    flags: () => apiFetch<Record<string, boolean>>('/api/admin/flags'),
    setFlag: (key: string, enabled: boolean) =>
      apiFetch<Record<string, unknown>>(`/api/admin/flags/${encodeURIComponent(key)}`, { method: 'PUT', body: JSON.stringify({ enabled }) }),
    health: () => apiFetch<Record<string, unknown>>('/api/admin/health'),
  },
  storage: {
    targets: () => apiFetch<Array<Record<string, unknown>>>('/api/storage/targets'),
  },
  system: {
    health: () => apiFetch<Record<string, unknown>>('/health'),
    ready: () => apiFetch<Record<string, unknown>>('/ready'),
  },
};
