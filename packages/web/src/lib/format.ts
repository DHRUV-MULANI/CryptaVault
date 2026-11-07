export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${value >= 10 || exponent === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[exponent]}`;
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function relativeTime(value: string): string {
  const date = new Date(value).getTime();
  if (Number.isNaN(date)) return value;
  const delta = Date.now() - date;
  const future = delta < 0;
  const seconds = Math.round(Math.abs(delta) / 1000);
  if (seconds < 60) return future ? 'in a moment' : 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return future ? `in ${minutes}m` : `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return future ? `in ${days}d` : `${days}d ago`;
  return formatDate(value);
}

export function truncate(value: string, max = 46): string {
  if (value.length <= max) return value;
  return `${value.slice(0, Math.max(0, max - 1))}…`;
}

export function shortHash(value: string, length = 12): string {
  return value.length <= length ? value : `${value.slice(0, length)}…`;
}

export function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}

export function downloadBlob(data: BlobPart, filename: string, type = 'application/octet-stream'): void {
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function downloadText(text: string, filename: string, type = 'text/plain'): void {
  downloadBlob(text, filename, type);
}

export async function copyText(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = value;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      const ok = document.execCommand('copy');
      textarea.remove();
      return ok;
    } catch {
      return false;
    }
  }
}

export function fileIconKind(name: string, type: string): string {
  const lower = `${name} ${type}`.toLowerCase();
  if (lower.includes('image') || /\.(png|jpg|jpeg|gif|webp|svg)$/.test(name)) return 'image';
  if (lower.includes('video') || /\.(mp4|mkv|mov|webm)$/.test(name)) return 'video';
  if (lower.includes('audio') || /\.(mp3|wav|flac|ogg)$/.test(name)) return 'audio';
  if (lower.includes('pdf') || /\.pdf$/.test(name)) return 'pdf';
  if (lower.includes('zip') || /\.(zip|gz|xz|7z|rar)$/.test(name)) return 'archive';
  if (/\.(ts|tsx|js|jsx|py|rs|go|java|sql|css|html|json|yaml|yml)$/.test(name)) return 'code';
  if (/\.(txt|md|log|csv)$/.test(name)) return 'text';
  return 'file';
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60) || 'vault';
}
