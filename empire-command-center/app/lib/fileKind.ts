/**
 * Shared helpers for rendering LuxeForge intake uploads (photos, CAD,
 * 3D scans, docs, video, ...) as either an image preview or a file chip.
 *
 * Kept intentionally tiny — extension-based classification only, no
 * content sniffing (the backend already refuses to render anything but
 * a small raster-image allowlist inline; see
 * backend/app/services/uploads/safe_file_serve.py).
 */

const IMAGE_EXTENSIONS = new Set([
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'heic', 'heif',
]);

const CAD_EXTENSIONS = new Set(['dwg', 'dxf', 'skp', 'rvt', 'ifc', '3dm']);
const SCAN_3D_EXTENSIONS = new Set(['usdz', 'obj', 'ply', 'glb', 'gltf', 'fbx', 'stl', 'e57']);
const DOC_EXTENSIONS = new Set(['doc', 'docx', 'txt', 'rtf', 'pages']);
const SHEET_EXTENSIONS = new Set(['xls', 'xlsx', 'csv', 'numbers']);
const VIDEO_EXTENSIONS = new Set(['mp4', 'mov', 'avi', 'mkv', 'webm']);

export function fileExtension(name: string): string {
  const idx = name.lastIndexOf('.');
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : '';
}

export function isImageFile(name: string): boolean {
  return IMAGE_EXTENSIONS.has(fileExtension(name));
}

export type FileKind = 'image' | 'cad' | '3d-scan' | 'pdf' | 'doc' | 'sheet' | 'video' | 'archive' | 'file';

export function fileKind(name: string): FileKind {
  const ext = fileExtension(name);
  if (IMAGE_EXTENSIONS.has(ext)) return 'image';
  if (ext === 'pdf') return 'pdf';
  if (ext === 'zip' || ext === 'rar' || ext === '7z') return 'archive';
  if (CAD_EXTENSIONS.has(ext)) return 'cad';
  if (SCAN_3D_EXTENSIONS.has(ext)) return '3d-scan';
  if (DOC_EXTENSIONS.has(ext)) return 'doc';
  if (SHEET_EXTENSIONS.has(ext)) return 'sheet';
  if (VIDEO_EXTENSIONS.has(ext)) return 'video';
  return 'file';
}

export function fileKindLabel(name: string): string {
  switch (fileKind(name)) {
    case 'image': return 'Image';
    case 'pdf': return 'PDF';
    case 'archive': return 'Archive';
    case 'cad': return 'CAD';
    case '3d-scan': return '3D Scan';
    case 'doc': return 'Document';
    case 'sheet': return 'Spreadsheet';
    case 'video': return 'Video';
    default: return 'File';
  }
}

export function formatFileSize(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
