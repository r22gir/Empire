export const HELP_MAX_FILES = 5;
export const HELP_MAX_FILE_BYTES = 8 * 1024 * 1024;
export const HELP_MAX_VOICE_BYTES = 12 * 1024 * 1024;

const HELP_FILE_EXT = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.txt', '.md',
  '.csv', '.doc', '.docx', '.xls', '.xlsx',
]);
const HELP_FILE_MIME = new Set([
  'image/png', 'image/jpeg', 'image/gif', 'image/webp',
  'application/pdf', 'text/plain', 'text/markdown', 'text/csv',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]);
const HELP_MIME_ALIAS: Record<string, string> = {
  'image/jpg': 'image/jpeg',
  'image/pjpeg': 'image/jpeg',
  'image/x-png': 'image/png',
  'application/x-pdf': 'application/pdf',
  'application/acrobat': 'application/pdf',
};
const HELP_UNKNOWN_MIME = new Set([
  '',
  'application/octet-stream',
  'binary/octet-stream',
  'application/download',
]);
const HELP_HTML_EXT = new Set(['.html', '.htm', '.shtml', '.xhtml', '.svg', '.xml', '.js', '.mjs']);
const HELP_EXT_MIME: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.pdf': 'application/pdf',
  '.txt': 'text/plain',
  '.md': 'text/markdown',
  '.csv': 'text/csv',
  '.doc': 'application/msword',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.xls': 'application/vnd.ms-excel',
  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
};

export const HELP_FILE_ACCEPT =
  'image/png,image/jpeg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.md,.csv,.doc,.docx,.xls,.xlsx,application/pdf';

function helpExt(name: string): string {
  const base = (name || '').split(/[/\\]/).pop() || '';
  const dot = base.lastIndexOf('.');
  return dot >= 0 ? base.slice(dot).toLowerCase() : '';
}

export function inferHelpMime(filename: string, contentType?: string | null): string {
  const raw = String(contentType || '').split(';')[0].trim().toLowerCase();
  const aliased = HELP_MIME_ALIAS[raw] || raw;
  if (!HELP_UNKNOWN_MIME.has(aliased)) return aliased;
  return HELP_EXT_MIME[helpExt(filename)] || '';
}

export function formatHelpBytes(n: number): string {
  if (!Number.isFinite(n) || n < 1024) return `${Math.max(0, Math.round(n || 0))} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function validateHelpFile(file: { name: string; type?: string; size: number }): { ok: true } | { ok: false; reason: string } {
  if (!file || !file.size) return { ok: false, reason: 'archivo vacío' };
  if (file.size > HELP_MAX_FILE_BYTES) {
    return { ok: false, reason: `supera ${formatHelpBytes(HELP_MAX_FILE_BYTES)}` };
  }
  const ext = helpExt(file.name);
  const mime = inferHelpMime(file.name, file.type);
  if (HELP_HTML_EXT.has(ext) || mime === 'text/html' || mime === 'image/svg+xml') {
    return { ok: false, reason: 'tipo de archivo no permitido' };
  }
  if (!HELP_FILE_EXT.has(ext) || !HELP_FILE_MIME.has(mime)) {
    return { ok: false, reason: 'tipo de archivo no permitido' };
  }
  return { ok: true };
}
