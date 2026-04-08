export const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');

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
