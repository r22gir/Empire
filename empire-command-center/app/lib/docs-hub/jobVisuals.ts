/** Turn a job's photos / drawings / mockups JSON into viewer-ready docs. Mock-safe. */
import type { DocEntry, DocGroup, DocType } from './types';

export type VisualKind = 'photo' | 'drawing' | 'mockup';

export interface VisualDoc {
  id: string;
  type: DocType;
  kind: 'pdf' | 'image';
  title: string;
  filename: string;
  src: string;
  source: string;
}

const IMG_RE = /\.(png|jpe?g|webp|gif)$/i;

export function normalizePhotoSrc(url: string): string {
  const src = String(url || '');
  const m = src.match(/^\/api\/v1\/photos\/(?!serve\/)([\w-]+)\/([\w-]+)\/([\w.-]+)$/);
  return m ? `/api/v1/photos/serve/${m[1]}/${m[2]}/${m[3]}` : src;
}

export function parseVisualList(value: unknown): unknown[] {
  if (value == null || value === '') return [];
  if (Array.isArray(value)) return value;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return value.trim() ? [value] : [];
    }
  }
  return [];
}

function itemUrl(item: unknown): { url: string; filename: string; title: string } | null {
  if (item == null) return null;
  if (typeof item === 'string') {
    const url = item.trim();
    if (!url) return null;
    const filename = url.split('?')[0].split('/').pop() || 'file';
    return { url, filename, title: filename };
  }
  if (typeof item !== 'object') return null;
  const rec = item as Record<string, unknown>;
  const url = String(rec.url || rec.src || rec.path || rec.serverUrl || '').trim();
  if (!url) return null;
  const filename = String(rec.filename || rec.original_name || rec.name || url.split('?')[0].split('/').pop() || 'file');
  const title = String(rec.title || rec.item_name || filename);
  return { url, filename, title };
}

export function visualsFromJob(job: Record<string, unknown> | null | undefined): VisualDoc[] {
  if (!job) return [];
  const out: VisualDoc[] = [];
  const fields: [string, VisualKind, DocType][] = [
    ['photos', 'photo', 'photo'],
    ['drawings', 'drawing', 'drawing'],
    ['mockups', 'mockup', 'drawing'],
  ];
  for (const [field, kind, type] of fields) {
    parseVisualList(job[field]).forEach((item, i) => {
      const parsed = itemUrl(item);
      if (!parsed) return;
      const src = normalizePhotoSrc(parsed.url);
      if (!src.startsWith('/') && !src.startsWith('http')) return;
      out.push({
        id: `job-${kind}-${i}-${parsed.filename}`,
        type,
        kind: IMG_RE.test(parsed.filename) || IMG_RE.test(src) ? 'image' : 'pdf',
        title: parsed.title,
        filename: parsed.filename,
        src,
        source: `job.${field}`,
      });
    });
  }
  return out;
}

export function visualToEntry(v: VisualDoc): DocEntry {
  return {
    id: v.id,
    type: v.type,
    kind: v.kind,
    title: v.title,
    filename: v.filename,
    version: 'original',
    versionRank: 1,
    isFinal: true,
    groupKey: `${v.type}|jobjson|${v.id}`,
    source: v.source,
    location: v.src,
    modified: '',
    src: v.src,
  };
}

export function visualsToGroups(visuals: VisualDoc[]): DocGroup[] {
  return visuals.map((v) => {
    const entry = visualToEntry(v);
    return { key: entry.groupKey, type: entry.type, title: entry.title, final: entry, older: [] };
  });
}

export function quotePdfSrc(quoteId: string): string {
  return `/api/v1/quotes-v2/${quoteId}/pdf`;
}

export function invoicePdfSrc(invoiceId: string): string {
  return `/api/v1/finance/invoices/${invoiceId}/pdf`;
}

export function docViewerTarget(doc: { url?: string | null; src?: string | null; filename?: string | null; title?: string | null; document_type?: string | null; quote_id?: string | null; id?: string | null }): { src?: string; id?: string; title: string; kind: 'pdf' | 'image' } {
  const raw = String(doc.src || doc.url || '');
  const src = raw ? normalizePhotoSrc(raw) : (doc.quote_id ? quotePdfSrc(String(doc.quote_id)) : '');
  const name = String(doc.title || doc.filename || 'Document');
  const kind: 'pdf' | 'image' = IMG_RE.test(name) || IMG_RE.test(src) || doc.document_type === 'photo' ? 'image' : 'pdf';
  return { src: src || undefined, title: name, kind };
}
