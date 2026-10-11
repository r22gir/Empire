/**
 * Natural-language doc lookup for Max: GET /api/v1/docs-hub/resolve?q=show me Nehal's final estimate
 * Returns the best FINAL match with a viewer link (relative; same-origin, existing auth),
 * plus a few alternatives. Never returns file bytes or public links.
 */
import type { NextRequest } from 'next/server';
import { getIndex, haystack, parseQuery } from '../../../../lib/docs-hub/server';
import { viewerHref } from '../../../../lib/docs-hub/types';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const q = (req.nextUrl.searchParams.get('q') || '').trim();
  if (!q) return Response.json({ error: 'missing q' }, { status: 400 });
  const idx = await getIndex();
  const p = parseQuery(q);
  const scored = idx.docs
    .filter(d => d.type !== 'photo' || p.type === 'photo')
    // every name/word in the request must match (no unrelated near-misses)
    .filter(d => { const h = haystack(d); return p.terms.every(t => h.includes(t)); })
    .map(d => {
      const h = haystack(d);
      let s = 0;
      if (p.qn) s += (d.quoteNumber || '').toUpperCase() === p.qn ? 10 : -100;
      for (const t of p.terms) s += h.includes(t) ? ((d.client || '').toLowerCase().includes(t) ? 4 : 2) : -6;
      if (p.type) s += d.type === p.type ? 5 : -8;
      if (d.isFinal) s += 3;
      if (d.generated) s -= 1;
      if (d.jobFolder) s += 1; // curated job files beat system copies
      return { d, s };
    })
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s || (b.d.modified || '').localeCompare(a.d.modified || ''));
  const best = scored.find(x => x.d.isFinal)?.d || scored[0]?.d || null;
  const fmt = (d: any) => ({ id: d.id, title: d.title, type: d.type, version: d.version, isFinal: d.isFinal, client: d.client, designer: d.designer,
    quoteNumber: d.quoteNumber, modified: d.modified, location: d.location, viewer_url: viewerHref({ id: d.id }) });
  return Response.json({
    query: q, parsed: p, found: !!best, doc: best ? fmt(best) : null,
    alternatives: scored.filter(x => x.d !== best && x.d.isFinal).slice(0, 5).map(x => fmt(x.d)),
  }, { headers: { 'cache-control': 'no-store' } });
}
