/** URLs Max chat may turn into clickable links / buttons. */
export function safeUrl(u: string): string {
  if (/^https?:\/\//i.test(u)) return u;
  if (/^\/api\/v1\/files\/found\?/i.test(u)) return u;
  if (/^\/docs\/view\?/i.test(u)) return u;
  return '';
}

export function markdownLinkCount(s: string): number {
  return (s.match(/\]\((?:https?:\/\/|\/api\/v1\/files\/found\?|\/docs\/view\?)/g) || []).length;
}
