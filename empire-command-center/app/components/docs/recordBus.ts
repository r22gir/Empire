'use client';
/**
 * Click-and-go: open any quote / invoice / job in its document workspace from anywhere.
 * Inside the Command Center the host (CommandCenterApp) switches screens in place;
 * elsewhere (ring home, standalone pages) it falls back to a deep link.
 *   /?screen=quote&id=<quoteId>      quote document (WYSIWYG editor + PDF + docs)
 *   /?screen=invoice&id=<invoiceId>  invoice document
 */
export type RecordType = 'quote' | 'invoice' | 'invoice-edit' | 'job';
export interface RecordRef { type: RecordType; id: string; quoteId?: string | null }
export const OPEN_RECORD_EVENT = 'empire:open-record';

export function recordHref(r: RecordRef): string {
  if (r.type === 'quote') return `/?screen=quote&id=${encodeURIComponent(r.id)}`;
  if (r.type === 'invoice' || r.type === 'invoice-edit') return `/?screen=invoice&id=${encodeURIComponent(r.id)}`;
  if (r.type === 'job' && r.quoteId) return `/?screen=quote&id=${encodeURIComponent(r.quoteId)}`;
  return '/?screen=jobs';
}

export function openRecord(r: RecordRef) {
  if (typeof window === 'undefined' || !r.id) return;
  if ((window as any).__empireRecordHost) window.dispatchEvent(new CustomEvent(OPEN_RECORD_EVENT, { detail: r }));
  else window.location.href = recordHref(r);
}
