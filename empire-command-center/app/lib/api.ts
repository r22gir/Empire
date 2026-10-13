function resolveApiBase(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  }
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  }
  // Same-origin /api/v1 for any non-localhost host (studio.empirebox.store,
  // forge.empirebox.store, LAN IPs, etc.). The Next.js server proxies
  // /api/v1/* -> http://127.0.0.1:8000/api/v1/* via next.config rewrites.
  // This keeps the request inside the same host so Cloudflare Access
  // (which is host-scoped) carries the CF_Authorization cookie end-to-end
  // and the browser's fetch() can complete. Cross-host fetches to
  // api.empirebox.store return 302 to the Access login page, which
  // fetch() cannot follow with credentials, so every status card would
  // read "unknown" / "offline" instead of the real values.
  return `${window.location.origin}/api/v1`;
}

export const API = resolveApiBase();

export const API_BASE = API.replace(/\/api\/v1\/?$/, '');

/** Append cache-bust param to any URL to defeat browser/CDN caching */
function bustCache(url: string): string {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}_v=${Date.now()}`;
}

export async function apiFetch<T = any>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(bustCache(`${API}${path}`), {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...opts?.headers },
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

const RELIST_TOKEN_KEY = 'relist_token';

export function getRelistToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(RELIST_TOKEN_KEY);
}

export function setRelistToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(RELIST_TOKEN_KEY, token);
}

export async function relistFetch<T = any>(path: string, opts?: RequestInit): Promise<T> {
  const token = getRelistToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(bustCache(`${API}${path}`), {
    ...opts,
    headers: { ...headers, ...opts?.headers },
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export async function obtainFounderToken(pin: string): Promise<{ access_token: string; user: any }> {
  const res = await fetch(`${API}/auth/founder-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  });
  if (!res.ok) throw new Error(`Founder token failed: ${res.status}`);
  return res.json();
}

export type SellablePackageId =
  | 'pkg_starter'
  | 'pkg_growth'
  | 'pkg_empire'
  | 'pkg_apostille_only';

export async function businessopsInfo(): Promise<{ public_signup_enabled?: boolean }> {
  const res = await fetch(`${API}/businessops/info`, { cache: 'no-store' });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `BusinessOps info failed (${res.status})`);
  }
  return body;
}

export async function businessopsSignup(payload: {
  email: string;
  password: string;
  display_name: string;
  business_name: string;
  package_id: SellablePackageId;
}) {
  const res = await fetch(`${API}/businessops/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `Signup failed (${res.status})`);
  }
  return body;
}

export async function businessopsCheckout(payload: {
  business_id: string;
  package_id: SellablePackageId;
  tenant_id?: string;
  customer_email?: string;
  success_url?: string;
  cancel_url?: string;
  interval?: 'month' | 'year';
}) {
  const res = await fetch(`${API}/businessops/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (res.status === 503) {
    throw new Error('Stripe TEST checkout is not configured yet.');
  }
  if (!res.ok) {
    throw new Error(body.detail || `Checkout failed (${res.status})`);
  }
  return body as { checkout_url: string; session_id: string; test_mode: boolean };
}

export function apiStream(path: string, body: any): ReadableStream<string> {
  return new ReadableStream({
    async start(controller) {
      const res = await fetch(bustCache(`${API}${path}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        cache: 'no-store',
      });
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) { controller.close(); return; }
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            controller.enqueue(line.slice(6));
          }
        }
      }
      controller.close();
    },
  });
}
