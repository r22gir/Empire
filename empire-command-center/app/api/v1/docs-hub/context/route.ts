/** Job header data: GET /api/v1/docs-hub/context?quote=<id|EST-..>|job=<id|number>|invoice=<id|INV-..> */
import type { NextRequest } from 'next/server';
import { getIndex, jobContext } from '../../../../lib/docs-hub/server';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const idx = await getIndex(sp.get('refresh') === '1');
  const ctx = jobContext(idx, { quote: sp.get('quote'), job: sp.get('job'), invoice: sp.get('invoice') });
  if (!ctx) return Response.json({ found: false }, { headers: { 'cache-control': 'no-store' } });
  return Response.json({ found: true, ...ctx }, { headers: { 'cache-control': 'no-store' } });
}
