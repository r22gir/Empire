/**
 * Same-origin proxy for the LeadForge list endpoint.
 *
 * FastAPI serves the list at `/api/v1/leads/` (trailing slash). Through the
 * generic `/api/v1/:path*` rewrite the browser's `/api/v1/leads` reaches the
 * backend without the slash, FastAPI answers 307 with an absolute
 * `http://127.0.0.1:8000/...` Location, and the browser (on the Tailscale /
 * Cloudflare host) cannot follow it. Asking for `/api/v1/leads/` instead gets
 * 308-stripped by Next before the rewrite runs. This handler takes the exact
 * `/api/v1/leads` path (filesystem routes win over afterFiles rewrites) and
 * forwards server-side to the slash route, so no redirect reaches the browser.
 * Sub-paths (`/api/v1/leads/<id>`, `/api/v1/leads/leadforge/...`) still go
 * through the normal rewrite. Backend code (main.py) is untouched.
 */
import type { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

const UPSTREAM = process.env.NEXT_PUBLIC_BACKEND_UPSTREAM || 'http://127.0.0.1:8000';

async function forward(req: NextRequest): Promise<Response> {
  const target = `${UPSTREAM}/api/v1/leads/${req.nextUrl.search}`;
  const headers: Record<string, string> = { accept: req.headers.get('accept') || 'application/json' };
  const ct = req.headers.get('content-type');
  if (ct) headers['content-type'] = ct;
  const init: RequestInit = { method: req.method, headers, cache: 'no-store', redirect: 'manual' };
  if (req.method !== 'GET' && req.method !== 'HEAD') init.body = await req.text();
  try {
    const res = await fetch(target, init);
    return new Response(res.body, {
      status: res.status,
      headers: { 'content-type': res.headers.get('content-type') || 'application/json', 'cache-control': 'no-store' },
    });
  } catch (e) {
    return Response.json({ detail: `LeadForge upstream unreachable: ${(e as Error).message}` }, { status: 502 });
  }
}

export const GET = forward;
export const POST = forward;
