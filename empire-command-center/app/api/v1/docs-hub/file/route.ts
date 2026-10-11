/**
 * Stream an indexed doc: GET /api/v1/docs-hub/file?id=<docId>[&download=1]
 * or a whitelisted backend source: ?src=/api/v1/quotes-v2/<id>/pdf
 * Inline by default (preview/print); download only when asked.
 * Only files present in the index (inside the allowed roots) are served.
 */
import type { NextRequest } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { cachedSrc, resolveDocFile } from '../../../../lib/docs-hub/server';

export const dynamic = 'force-dynamic';

const MIME: Record<string, string> = { '.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif' };

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const download = sp.get('download') === '1';
  let abs: string | null = null;
  let name = 'document.pdf';
  const id = sp.get('id');
  const src = sp.get('src');
  if (id) {
    const r = await resolveDocFile(id);
    if (!r) return Response.json({ error: 'not found' }, { status: 404 });
    name = r.doc.filename;
    if (r.abs) abs = r.abs;
    else if (r.doc.src) { const c = await cachedSrc(r.doc.src); if ('error' in c) return Response.json({ error: c.error }, { status: c.status }); abs = c.abs; }
  } else if (src) {
    const c = await cachedSrc(src, sp.get('v'));
    if ('error' in c) return Response.json({ error: c.error }, { status: c.status });
    abs = c.abs;
    name = sp.get('name') || path.basename(src.replace(/\/pdf$/, '.pdf'));
  }
  if (!abs) return Response.json({ error: 'missing id or src' }, { status: 400 });
  let buf: Buffer;
  try { buf = await fs.readFile(abs); } catch { return Response.json({ error: 'file missing on disk' }, { status: 404 }); }
  const type = MIME[path.extname(abs).toLowerCase()] || 'application/octet-stream';
  const safe = name.replace(/[^\w.\- ]+/g, '_');
  return new Response(new Uint8Array(buf), {
    headers: { 'content-type': type, 'content-disposition': `${download ? 'attachment' : 'inline'}; filename="${safe}"`, 'cache-control': 'private, no-store', 'x-content-type-options': 'nosniff' },
  });
}
