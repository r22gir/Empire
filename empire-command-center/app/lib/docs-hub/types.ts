/** Shared (client + server) types for the Final Docs hub. */
export type DocType = 'estimate' | 'presentation' | 'invoice' | 'drawing' | 'photo' | 'other';

export const DOC_TYPES: { id: DocType; label: string; plural: string }[] = [
  { id: 'estimate', label: 'Estimate', plural: 'Estimates' },
  { id: 'presentation', label: 'Presentation', plural: 'Presentations' },
  { id: 'invoice', label: 'Invoice', plural: 'Invoices' },
  { id: 'drawing', label: 'Drawing', plural: 'Drawings' },
  { id: 'photo', label: 'Photo', plural: 'Photos' },
  { id: 'other', label: 'Other', plural: 'Other files' },
];

export interface DocEntry {
  id: string;                 // stable id (hash of path or src)
  type: DocType;
  kind: 'pdf' | 'image';
  title: string;
  filename: string;
  version: string;            // "v18", "rev M", "system PDF", "original", "generated"
  versionRank: number;
  isFinal: boolean;           // latest (or explicitly "final") in its group
  finalReason?: 'explicit' | 'latest' | 'single';
  groupKey: string;
  source: string;             // "jobs folder", "quote PDFs", "invoice PDFs", ...
  location: string;           // where it lives on the Dell (display only)
  modified: string;           // ISO
  size?: number;
  generated?: boolean;        // rendered on demand from a backend endpoint
  src?: string;               // backend path for generated / url-backed docs
  quoteNumber?: string | null;
  quoteId?: string | null;
  jobId?: string | null;
  jobNumber?: string | null;
  jobFolder?: string | null;  // ~/jobs/<slug>
  invoiceId?: string | null;
  invoiceNumber?: string | null;
  client?: string | null;     // end client (e.g. "Nehal Elrefai")
  designer?: string | null;   // billing customer (e.g. "Dahlia Design")
  project?: string | null;
  businessUnit?: string | null;
}

export interface DocGroup {
  key: string;
  type: DocType;
  title: string;
  final: DocEntry;
  older: DocEntry[];
}

export interface JobContext {
  quoteId?: string | null;
  quoteNumber?: string | null;
  jobId?: string | null;
  jobNumber?: string | null;
  client?: string | null;
  designer?: string | null;
  project?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  status?: string | null;
  total?: number | null;
  depositRequired?: number | null;
  depositPaid?: number | null;
  depositOwed?: number | null;
  balanceDue?: number | null;
  installDate?: string | null;
  nextStep?: string | null;
  invoices?: { id: string; number: string; status: string; total: number; paid: number; balance: number }[];
}

export const DOCS_API = '/api/v1/docs-hub';

export function viewerHref(d: { id?: string; src?: string; title?: string }): string {
  if (d.id) return `/docs/view?id=${encodeURIComponent(d.id)}`;
  const p = new URLSearchParams();
  if (d.src) p.set('src', d.src);
  if (d.title) p.set('title', d.title);
  return `/docs/view?${p.toString()}`;
}
