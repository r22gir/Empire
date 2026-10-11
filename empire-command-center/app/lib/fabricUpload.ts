/** Same cap as intake photo and scan uploads (INTAKE_MAX_UPLOAD_MB, default 200). */
export const FABRIC_MAX_BYTES = 200 * 1024 * 1024;

const IMAGE_EXTENSIONS = new Set([
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'heic', 'heif',
]);

function extension(name: string): string {
  const idx = name.lastIndexOf('.');
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : '';
}

export function isFabricImage(file: { name: string; type?: string }): boolean {
  if ((file.type || '').toLowerCase().startsWith('image/')) return true;
  return IMAGE_EXTENSIONS.has(extension(file.name || ''));
}

/** Images, including HEIC, use the intake photos route. Everything else uses scans. */
export function fabricUploadKind(file: { name: string; type?: string }): 'photos' | 'scans' {
  return isFabricImage(file) ? 'photos' : 'scans';
}

export function fabricTooLarge(file: { size: number }): boolean {
  return file.size > FABRIC_MAX_BYTES;
}
