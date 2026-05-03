export const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010/api/v1';
export const BACKEND_URL = API.replace(/\/api\/v1$/, '');
export const BACKEND_LABEL = process.env.NEXT_PUBLIC_BACKEND_LABEL || 'Backend 8010';
export const FRONTEND_LABEL = process.env.NEXT_PUBLIC_FRONTEND_LABEL || 'v10 Frontend 3010';

/** Backwards compat */
export const API_BASE = BACKEND_URL;

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