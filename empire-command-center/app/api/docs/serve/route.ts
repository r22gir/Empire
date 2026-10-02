import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import { empireRepoRoot } from '../repo-root';

const REPO_ROOT = empireRepoRoot();
const HOME = process.env.HOME || '/home/rg';

function resolveDocPath(docPath: string): string {
  if (docPath.startsWith('~/')) return path.join(HOME, docPath.slice(2));
  if (docPath.startsWith('/')) return docPath;
  return path.join(REPO_ROOT, docPath);
}

/** Registry paths say `data/...`; canonical files live in `backend/data/...`. */
function candidatePaths(docPath: string): string[] {
  const primary = resolveDocPath(docPath);
  const extra: string[] = [];
  if (!docPath.startsWith('/') && !docPath.startsWith('~/')) {
    if (docPath.startsWith('data/')) {
      extra.push(path.join(REPO_ROOT, 'backend', docPath));
    } else if (docPath.startsWith('backend/data/')) {
      extra.push(path.join(REPO_ROOT, docPath.slice('backend/'.length)));
    }
  }
  return [primary, ...extra];
}

function missingDocumentHtml(docPath: string): string {
  const safe = docPath.replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch] || ch
  ));
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Document unavailable</title>
<style>
  body { font-family: Georgia, "Times New Roman", serif; background: #f7f3ea; color: #20241f; margin: 0; padding: 48px 40px; }
  h1 { font-size: 22px; font-weight: 600; margin: 0; }
  .rule { height: 3px; width: 120px; background: #b8912f; margin: 16px 0; }
  p { max-width: 520px; line-height: 1.5; }
  code { font-family: ui-monospace, monospace; font-size: 12px; color: #7b7466; }
</style></head><body>
  <h1>Document not in this workspace</h1>
  <div class="rule"></div>
  <p>This Docs entry has no file here, so there is nothing to preview. No empty PDF was generated.</p>
  <p><code>${safe}</code></p>
</body></html>`;
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

function firstExisting(docPath: string): { resolved: string | null; denied: boolean } {
  const allowed = [
    REPO_ROOT,
    path.join(HOME, 'Empire'),
    path.join(HOME, 'Downloads'),
    path.join(HOME, 'Documents'),
    path.join(HOME, '.claude'),
  ];
  let denied = false;
  for (const resolved of candidatePaths(docPath)) {
    if (!allowed.some(dir => resolved.startsWith(dir))) {
      denied = true;
      continue;
    }
    if (existsSync(resolved)) return { resolved, denied: false };
  }
  return { resolved: null, denied };
}

export async function GET(req: NextRequest) {
  const docPath = req.nextUrl.searchParams.get('path');
  const probe = req.nextUrl.searchParams.get('probe') === '1';
  if (!docPath) {
    return NextResponse.json({ error: 'Missing path parameter' }, { status: 400 });
  }

  const found = firstExisting(docPath);
  if (probe) {
    return NextResponse.json({
      ok: !!found.resolved,
      message: found.resolved ? 'ready' : 'Document not in this workspace',
    });
  }

  if (!found.resolved && found.denied) {
    return new NextResponse(missingDocumentHtml(docPath), {
      status: 403,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }

  if (!found.resolved) {
    return new NextResponse(missingDocumentHtml(docPath), {
      status: 404,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }

  const resolved = found.resolved;

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
