const IMAGE_EXT = new Set(['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp', 'heic', 'heif']);
const DOC_EXT = new Set(['pdf', 'txt', 'md', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'json']);
const CODE_EXT = new Set(['py', 'js', 'ts', 'tsx', 'jsx', 'html', 'css', 'sh', 'yaml', 'yml']);
const AUDIO_EXT = new Set(['m4a', 'mp3', 'wav', 'ogg', 'flac', 'wma', 'aac']);

export function chatFileBasename(filename: string): string {
  const trimmed = String(filename || '').trim();
  if (!trimmed) return '';
  const parts = trimmed.split(/[/\\]/);
  return parts[parts.length - 1] || trimmed;
}

export function chatFileExt(filename: string): string {
  const name = chatFileBasename(filename);
  const dot = name.lastIndexOf('.');
  return dot >= 0 ? name.slice(dot + 1).toLowerCase() : '';
}

export function chatFileCategory(filename: string): 'images' | 'documents' | 'code' | 'audio' | 'other' {
  const ext = chatFileExt(filename);
  if (DOC_EXT.has(ext)) return 'documents';
  if (CODE_EXT.has(ext)) return 'code';
  if (IMAGE_EXT.has(ext)) return 'images';
  if (AUDIO_EXT.has(ext)) return 'audio';
  return 'other';
}

export function isChatImageFilename(filename: string): boolean {
  return chatFileCategory(filename) === 'images';
}

/** Open-URL for a chat upload. Encodes spaces, parentheses and accents. */
export function fileViewUrl(filename: string, api: string = '/api/v1'): string {
  const name = chatFileBasename(filename);
  const category = chatFileCategory(name);
  return `${api}/files/view/${category}/${encodeURIComponent(name)}`;
}
