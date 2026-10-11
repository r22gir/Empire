/**
 * Final Docs hub index: GET /api/v1/docs-hub
 *   ?q=  free text (client, job/quote number, doc type words)
 *   ?type=estimate|presentation|invoice|drawing|photo|other
 *   ?client= ?quote=<id|EST-..> ?job=<id|number|folder> ?final=1 ?group=1 ?refresh=1
 *   ?id=<docId>  -> one doc + its versions + job context
 * Same auth perimeter as the rest of /api/v1 (served by this Next server).
 */
import type { NextRequest } from 'next/server';
import { docsForQuote, getIndex, groupDocs, jobContext, searchDocs } from '../../../lib/docs-hub/server';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const idx = await getIndex(sp.get('refresh') === '1');
  const id = sp.get('id');
  if (id) {
    const doc = idx.docs.find(d => d.id === id);
    if (!doc) return Response.json({ error: 'not found' }, { status: 404 });
    const versions = idx.docs.filter(d => d.groupKey === doc.groupKey).sort((a, b) => (b.modified || '').localeCompare(a.modified || ''));
    const context = jobContext(idx, { quote: doc.quoteId || doc.quoteNumber, invoice: doc.invoiceId });
    return Response.json({ doc, versions, context }, { headers: { 'cache-control': 'no-store' } });
  }
  const quote = sp.get('quote');
  let docs = quote ? docsForQuote(idx, quote).docs : idx.docs;
  docs = searchDocs(docs, {
    q: sp.get('q') || undefined, type: sp.get('type'), client: sp.get('client'), job: sp.get('job'),
    finalOnly: sp.get('final') === '1',
  });
  const facets = {
    types: docs.reduce((m: Record<string, number>, d) => { m[d.type] = (m[d.type] || 0) + 1; return m; }, {}),
    clients: [...new Set(idx.docs.filter(d => d.isFinal && d.client).map(d => d.client as string))].sort(),
  };
  const body: any = { builtAt: idx.builtAt, tookMs: idx.tookMs, total: docs.length, roots: idx.roots, facets, dbError: idx.dbError || undefined };
  if (sp.get('group') === '1') body.groups = groupDocs(docs);
  else body.docs = docs.sort((a, b) => (b.modified || '').localeCompare(a.modified || '')).slice(0, Number(sp.get('limit') || 500));
  if (quote) body.context = jobContext(idx, { quote });
  return Response.json(body, { headers: { 'cache-control': 'no-store' } });
}
