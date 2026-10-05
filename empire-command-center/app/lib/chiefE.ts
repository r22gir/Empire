// Chief e = Rafael's Grok Bot assistant (separate from Max). Max links to it with
// the markdown link [Ask Chief e](chief-e:ask); the studio turns that into this URL.
// Set NEXT_PUBLIC_CHIEF_E_URL at build time to the exact Grok Bot address.
export const CHIEF_E_URL = (process.env.NEXT_PUBLIC_CHIEF_E_URL || 'https://grok.com/').trim();

/** Grok Bot URL, optionally pre-filled with a question (q= is ignored where unsupported). */
export function chiefEHref(question?: string): string {
  const q = (question || '').trim();
  if (!q) return CHIEF_E_URL;
  const sep = CHIEF_E_URL.includes('?') ? '&' : '?';
  return `${CHIEF_E_URL}${sep}q=${encodeURIComponent(q.slice(0, 1500))}`;
}
