/**
 * Page renderer for the shared viewer (works on every phone; no PDF plugin needed).
 *   GET /api/v1/docs-hub/render?id=<docId>&info=1        -> { kind, pages, title }
 *   GET /api/v1/docs-hub/render?id=<docId>&page=3&w=1200 -> PNG of page 3
 *   (or ?src=<whitelisted backend pdf path> instead of id)
 * Uses poppler (pdfinfo / pdftoppm) on the Dell; renders are cached.
 */
import type { NextRequest } from 'next/server';
import { execFile } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';
import { CACHE_DIR, cachedSrc, resolveDocFile, sha } from '../../../../lib/docs-hub/server';

export const dynamic = 'force-dynamic';

const run = (cmd: string, args: string[]) => new Promise<string>((resolve, reject) =>
  execFile(cmd, args, { timeout: 30000, maxBuffer: 8 * 1024 * 1024 }, (e, out) => (e ? reject(e) : resolve(out))));

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  let abs: string | null = null;
  let title = '';
  let kind: 'pdf' | 'image' = 'pdf';
  const id = sp.get('id');
  const src = sp.get('src');
  if (id) {
    const r = await resolveDocFile(id);
    if (!r) return Response.json({ error: 'not found' }, { status: 404 });
    title = r.doc.title; kind = r.doc.kind;
    if (r.abs) abs = r.abs;
    else if (r.doc.src) { const c = await cachedSrc(r.doc.src); if ('error' in c) return Response.json({ error: c.error }, { status: c.status }); abs = c.abs; }
  } else if (src) {
    const c = await cachedSrc(src, sp.get('v'));
    if ('error' in c) return Response.json({ error: c.error }, { status: c.status });
    abs = c.abs; kind = /\.pdf$/i.test(abs) ? 'pdf' : 'image'; title = sp.get('title') || '';
  }
  if (!abs) return Response.json({ error: 'missing id or src' }, { status: 400 });
  let st;
  try { st = await fs.stat(abs); } catch { return Response.json({ error: 'file missing on disk' }, { status: 404 }); }

  if (sp.get('info') === '1') {
    if (kind === 'image') return Response.json({ kind, pages: 1, title });
    try {
      const out = await run('pdfinfo', [abs]);
      const pages = Number(out.match(/^Pages:\s+(\d+)/m)?.[1] || 1);
      const size = out.match(/^Page size:\s+([\d.]+) x ([\d.]+)/m);
      return Response.json({ kind, pages, title, ratio: size ? Number(size[2]) / Number(size[1]) : 1.294 }, { headers: { 'cache-control': 'no-store' } });
    } catch { return Response.json({ error: 'could not read PDF' }, { status: 422 }); }
  }
  if (kind === 'image') {
    const buf = await fs.readFile(abs);
    const ext = path.extname(abs).toLowerCase();
    return new Response(new Uint8Array(buf), { headers: { 'content-type': ext === '.png' ? 'image/png' : ext === '.webp' ? 'image/webp' : 'image/jpeg', 'cache-control': 'private, max-age=300' } });
  }
  const page = Math.max(1, Math.min(500, Number(sp.get('page') || 1) | 0));
  const w = [160, 320, 800, 1200, 1600, 2000].reduce((best, x) => (Math.abs(x - Number(sp.get('w') || 1200)) < Math.abs(best - Number(sp.get('w') || 1200)) ? x : best), 1200);
  await fs.mkdir(CACHE_DIR, { recursive: true });
  const key = sha(`${abs}|${st.mtimeMs}|${page}|${w}`);
  const outBase = path.join(CACHE_DIR, `r-${key}`);
  const png = `${outBase}.png`;
  try { await fs.access(png); } catch {
    try { await run('pdftoppm', ['-f', String(page), '-l', String(page), '-png', '-singlefile', '-scale-to-x', String(w), '-scale-to-y', '-1', abs, outBase]); }
    catch { return Response.json({ error: 'render failed' }, { status: 422 }); }
  }
  const buf = await fs.readFile(png);
  return new Response(new Uint8Array(buf), { headers: { 'content-type': 'image/png', 'cache-control': 'private, max-age=300' } });
}
