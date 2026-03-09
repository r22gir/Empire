import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

const REPO_ROOT = path.resolve(process.cwd(), '..');
const HOME = process.env.HOME || '/home/rg';

function resolveDocPath(docPath: string): string {
  if (docPath.startsWith('~/')) return path.join(HOME, docPath.slice(2));
  if (docPath.startsWith('/')) return docPath;
  return path.join(REPO_ROOT, docPath);
}

const MIME_TYPES: Record<string, string> = {
  '.pdf': 'application/pdf',
  '.html': 'text/html',
  '.htm': 'text/html',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.doc': 'application/msword',
  '.odt': 'application/vnd.oasis.opendocument.text',
  '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  '.ppt': 'application/vnd.ms-powerpoint',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.mermaid': 'text/plain',
  '.mmd': 'text/plain',
  '.txt': 'text/plain',
  '.json': 'application/json',
  '.md': 'text/plain',
};

export async function GET(req: NextRequest) {
  const docPath = req.nextUrl.searchParams.get('path');
  if (!docPath) {
    return NextResponse.json({ error: 'Missing path parameter' }, { status: 400 });
  }

  const resolved = resolveDocPath(docPath);

  // Security: only allow from known directories
  const allowed = [
    REPO_ROOT,
    path.join(HOME, 'Empire'),
    path.join(HOME, 'Downloads'),
    path.join(HOME, 'Documents'),
    path.join(HOME, '.claude'),
  ];

  if (!allowed.some(dir => resolved.startsWith(dir))) {
    return NextResponse.json({ error: 'Access denied' }, { status: 403 });
  }

  if (!existsSync(resolved)) {
    return NextResponse.json({ error: 'File not found' }, { status: 404 });
  }

  try {
    const buffer = await readFile(resolved);
    const ext = path.extname(resolved).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    const filename = path.basename(resolved);

    return new NextResponse(buffer, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': contentType.startsWith('image/') || contentType === 'application/pdf' || contentType === 'text/html'
          ? `inline; filename="${filename}"`
          : `attachment; filename="${filename}"`,
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
