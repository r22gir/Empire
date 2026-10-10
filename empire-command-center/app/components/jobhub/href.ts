// One URL for the job hub everywhere (search, Workroom rail, dashboard items, job header).
export function jobHubHref(t: { job?: string | null; quote?: string | null }): string {
  const p = new URLSearchParams({ product: 'workroom', section: 'jobhub' });
  if (t.job) p.set('job', t.job); else if (t.quote) p.set('quote', t.quote);
  return `/?${p}`;
}
