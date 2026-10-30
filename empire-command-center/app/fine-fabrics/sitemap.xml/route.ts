import { apiBase } from '../api';

export async function GET() {
  try {
    const res = await fetch(`${apiBase()}/fine-fabrics/sitemap.xml`, { cache: 'no-store' });
    if (res.ok) {
      return new Response(await res.text(), {
        headers: { 'Content-Type': 'application/xml; charset=utf-8' },
      });
    }
  } catch {
    // fall through to the index-only sitemap
  }
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://fabrics.empirebox.store/fine-fabrics</loc></url>
</urlset>
`;
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
