/**
 * GET /api/v1/quote-verification?id=<quoteId>
 * Reads the last saved verification (written by the backend's POST /quotes/verify/{id})
 * and answers 200 either way, so opening a never-verified quote doesn't log a 404.
 * Running a verification still goes to the backend unchanged.
 */
import type { NextRequest } from 'next/server';
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';

export const dynamic = 'force-dynamic';

// Same directory the live backend reads (EMPIRE_DATA_DIR=~/empire-data -> quotes/).
const DIRS = [path.join(process.env.EMPIRE_DATA_HOME || path.join(os.homedir(), 'empire-data'), 'quotes')];

export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get('id') || '';
  if (!/^[\w-]{3,40}$/.test(id)) return Response.json({ exists: false, error: 'bad id' }, { status: 400 });
  for (const dir of DIRS) {
    try {
      const raw = await fs.readFile(path.join(dir, `${id}_verification.json`), 'utf8');
      return Response.json({ exists: true, result: JSON.parse(raw) }, { headers: { 'cache-control': 'no-store' } });
    } catch { /* try next */ }
  }
  return Response.json({ exists: false }, { headers: { 'cache-control': 'no-store' } });
}
