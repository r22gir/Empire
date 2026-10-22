/**
 * Split /jobs/{id}/related into auto-linked vs review-only docs.
 * Shared-client quotes must never look like they belong to this job.
 */
export type RelatedQuote = {
  id?: string;
  quote_number?: string;
  job_id?: string | null;
  customer_id?: string | null;
  review?: boolean;
  match_by?: string;
};

export type RelatedPayload = {
  quotes?: RelatedQuote[];
  invoices?: RelatedQuote[];
  possibly_related?: {
    quotes?: RelatedQuote[];
    invoices?: RelatedQuote[];
  };
  clients?: { name?: string; role?: string; customer_id?: string }[];
};

export function autoRelatedQuotes(related: RelatedPayload | null | undefined): RelatedQuote[] {
  return [...(related?.quotes || [])].filter((q) => !q.review);
}

export function reviewRelatedQuotes(related: RelatedPayload | null | undefined): RelatedQuote[] {
  const fromBucket = related?.possibly_related?.quotes || [];
  if (fromBucket.length) return fromBucket;
  return [...(related?.quotes || [])].filter((q) => q.review);
}

export function autoRelatedInvoices(related: RelatedPayload | null | undefined): RelatedQuote[] {
  return [...(related?.invoices || [])].filter((q) => !q.review);
}

export function reviewRelatedInvoices(related: RelatedPayload | null | undefined): RelatedQuote[] {
  const fromBucket = related?.possibly_related?.invoices || [];
  if (fromBucket.length) return fromBucket;
  return [...(related?.invoices || [])].filter((q) => q.review);
}

export function isSharedClientReviewQuote(q: RelatedQuote, jobId: string): boolean {
  if (q.job_id && String(q.job_id) === String(jobId)) return false;
  return Boolean(q.review || q.match_by === 'customer_id_shared');
}
