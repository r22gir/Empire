import { apiBase } from '../api';

export async function GET() {
  try {
    const res = await fetch(`${apiBase()}/fine-fabrics/merchant.xml`, { cache: 'no-store' });
    if (res.ok) {
      return new Response(await res.text(), {
        headers: { 'Content-Type': 'application/xml; charset=utf-8' },
      });
    }
  } catch {
    // fall through
  }
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>Empire Fine Fabrics</title>
    <link>https://fabrics.empirebox.store</link>
    <description>Cloth for drapery, upholstery, and outdoor work. Shipping is never free.</description>
  </channel>
</rss>
`;
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
