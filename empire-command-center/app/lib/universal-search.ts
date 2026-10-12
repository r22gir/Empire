/** Pure logic for Command Center / Max universal search.
 *  Safe to import from node:test (no React, no window).
 */

export type SearchActionKind = 'open' | 'call' | 'navigate' | 'draft_reply';

export type SearchAction = {
  kind: SearchActionKind;
  label: string;
  href?: string;
  phone?: string;
  mail_id?: string;
  source?: string;
};

export type SearchHit = {
  id: string;
  type: string;
  title: string;
  subtitle?: string;
  href: string;
  action: SearchAction;
  score?: number;
  extra?: { feature_id?: string; workroom_only?: boolean };
};

export type SearchGroup = {
  type: string;
  label: string;
  items: SearchHit[];
};

export type SearchResponse = {
  query: string;
  edition?: string;
  blocked?: boolean;
  ok?: boolean;
  groups: SearchGroup[];
  results: SearchHit[];
  top: SearchHit | null;
  timed_out?: string[];
  ms?: number;
};

export const GROUP_ORDER = [
  'screen', 'job', 'quote', 'invoice', 'person', 'file', 'organizer', 'mail', 'memory',
] as const;

export const GROUP_LABELS: Record<string, string> = {
  screen: 'Screens',
  job: 'Jobs',
  quote: 'Quotes',
  invoice: 'Invoices',
  person: 'People',
  file: 'Files',
  organizer: 'Organizer',
  mail: 'Pending email',
  memory: 'Memory',
};

export const WORKROOM_ONLY_SCREENS = new Set([
  'workroom', 'craft', 'construction', 'luxe', 'storefront',
  'schedule', 'final-docs', 'daily-summary',
  'business-profile', 'vendorops', 'contractor', 'lead', 'crm', 'pay',
  'pricing-studio', 'drawings', 'vision', 'recovery',
  'social', 'market', 'support', 'ship', 'archive', 'transcript',
  'platform', 'openclaw', 'max-continuity', 'hardware',
  'relist', 'llc', 'apost', 'assist', 'vetforge', 'petforge', 'dev',
  'jobs', 'invoices', 'invoice', 'quote', 'docs', 'product-docs', 'pricing',
]);

/** Screens the old Quick Switch omitted — must appear in the live palette. */
export const REQUIRED_SCREENS = [
  'improvements', 'tokens', 'family-help', 'organizer', 'minimax-usage', 'presentation-mode',
] as const;

export const DEBOUNCE_MS = 200;
export const MIN_QUERY_LEN = 1;

export function flattenGroups(groups: SearchGroup[] | undefined | null): SearchHit[] {
  if (!groups || !groups.length) return [];
  const order = new Map(GROUP_ORDER.map((t, i) => [t, i]));
  const sorted = [...groups].sort((a, b) => (order.get(a.type as typeof GROUP_ORDER[number]) ?? 99) - (order.get(b.type as typeof GROUP_ORDER[number]) ?? 99));
  const out: SearchHit[] = [];
  for (const g of sorted) {
    for (const item of g.items || []) out.push(item);
  }
  return out;
}

export function topResult(payload: Pick<SearchResponse, 'top' | 'results' | 'groups'> | null | undefined): SearchHit | null {
  if (!payload) return null;
  if (payload.top) return payload.top;
  if (payload.results && payload.results.length) return payload.results[0];
  const flat = flattenGroups(payload.groups);
  return flat[0] || null;
}

/** Enter opens the highlighted row, else the top result — jobs included. */
export function resultForEnter(flat: SearchHit[], focusIdx: number): SearchHit | null {
  if (!flat.length) return null;
  if (focusIdx >= 0 && focusIdx < flat.length) return flat[focusIdx];
  return flat[0];
}

export function isFamilyEditionId(id: string | undefined | null): boolean {
  const key = (id || '').toLowerCase().replace(/-/g, '_');
  return key === 'max_e' || key === 'maxe' || key === 'amp' || key === 'maxine' || key === 'unknown';
}

export function filterHitsForEdition(hits: SearchHit[], edition: string | undefined | null): SearchHit[] {
  const family = isFamilyEditionId(edition);
  const maxine = (edition || '').toLowerCase() === 'maxine';
  return hits.filter(h => {
    if (family) {
      if (h.type === 'job') return false;
      if (h.extra?.workroom_only) return false;
      const sid = String(h.extra?.feature_id || h.id.replace(/^screen:/, ''));
      if (h.type === 'screen' && WORKROOM_ONLY_SCREENS.has(sid)) return false;
    }
    if (maxine && /argos|campestre/i.test(`${h.title} ${h.subtitle || ''} ${h.href || ''}`)) return false;
    return true;
  });
}

export function parseSearchHref(href: string): { product?: string; screen?: string; section?: string; job?: string; quote?: string } {
  const out: { product?: string; screen?: string; section?: string; job?: string; quote?: string } = {};
  if (!href) return out;
  try {
    const q = href.startsWith('/?') || href.startsWith('?') ? href.replace(/^\//, '') : '';
    if (!q.startsWith('?')) return out;
    const p = new URLSearchParams(q.slice(1));
    for (const key of ['product', 'screen', 'section', 'job', 'quote'] as const) {
      const v = p.get(key);
      if (v) out[key] = v;
    }
  } catch { /* ignore */ }
  return out;
}

export function shouldFetch(query: string): boolean {
  return (query || '').trim().length >= MIN_QUERY_LEN;
}

export function groupHits(hits: SearchHit[]): SearchGroup[] {
  const buckets = new Map<string, SearchHit[]>();
  for (const h of hits) {
    const list = buckets.get(h.type) || [];
    list.push(h);
    buckets.set(h.type, list);
  }
  const groups: SearchGroup[] = [];
  for (const t of GROUP_ORDER) {
    const items = buckets.get(t);
    if (items && items.length) groups.push({ type: t, label: GROUP_LABELS[t] || t, items });
  }
  for (const [t, items] of buckets) {
    if (!(GROUP_ORDER as readonly string[]).includes(t) && items.length) {
      groups.push({ type: t, label: t, items });
    }
  }
  return groups;
}

export function actionHref(hit: SearchHit): string {
  if (hit.action?.kind === 'call' && hit.action.phone) return `tel:${hit.action.phone}`;
  return hit.action?.href || hit.href || '';
}

export function isDraftReply(hit: SearchHit): boolean {
  return hit.action?.kind === 'draft_reply';
}
