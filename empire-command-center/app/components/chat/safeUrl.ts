/** URLs Max chat may turn into clickable links / buttons. */
export function safeUrl(u: string): string {
  const t = (u || '').trim();
  if (!t) return '';
  if (/^(javascript|data|vbscript|file):/i.test(t)) return '';
  if (/^https?:\/\//i.test(t)) return t;
  if (/^\/api\/v1\/files\/found\?/i.test(t)) return t;
  if (/^\/docs\/view\?/i.test(t)) return t;
  return '';
}

export function markdownLinkCount(s: string): number {
  return (s.match(/\]\((?:https?:\/\/|\/api\/v1\/files\/found\?|\/docs\/view\?)/g) || []).length;
}
