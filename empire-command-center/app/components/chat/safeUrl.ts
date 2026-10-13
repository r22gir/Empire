/** Allow only same-origin app deep links and https URLs in Max chat. */

const APP_PATH = /^\/(?:\?[\w.&=%/-]*|ayuda|archivo|classic|quote\/[\w-]+|presentation\/[\w-]+)?$/i;

export function isAppDeepLink(href: string): boolean {
  const t = (href || "").trim();
  if (t === "/" || t.startsWith("/?")) return true;
  return APP_PATH.test(t);
}

export function safeUrl(href: string): string | null {
  const t = (href || "").trim();
  if (!t) return null;
  const lower = t.toLowerCase();
  if (lower.startsWith("javascript:") || lower.startsWith("data:") || lower.startsWith("vbscript:")) {
    return null;
  }
  if (t.startsWith("https://") || t.startsWith("http://localhost") || t.startsWith("http://127.0.0.1")) {
    return t;
  }
  if (isAppDeepLink(t)) return t;
  return null;
}
