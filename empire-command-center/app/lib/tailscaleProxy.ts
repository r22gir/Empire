/** Trust Tailscale identity only when the TCP peer is the local serve proxy. */

export function normalizeSocketPeer(addr: string | undefined | null): string {
  let peer = String(addr || '').trim().toLowerCase();
  if (peer.startsWith('::ffff:')) peer = peer.slice('::ffff:'.length);
  return peer;
}

export function isLoopbackPeer(addr: string | undefined | null): boolean {
  const peer = normalizeSocketPeer(addr);
  return peer === '127.0.0.1' || peer === '::1';
}

type HeaderBag = Record<string, string | string[] | undefined>;

/** Stamp a Node request from its real socket. Client-supplied trust headers are dropped. */
export function stampIncomingMessage(req: { headers: HeaderBag; socket?: { remoteAddress?: string } }): void {
  const headers = req.headers;
  const peer = normalizeSocketPeer(req.socket?.remoteAddress);
  const login = headerValue(headers['tailscale-user-login']);
  delete headers['x-empire-socket-peer'];
  delete headers['x-empire-proxy-secret'];
  delete headers['x-empire-tailscale-verified'];
  headers['x-empire-socket-peer'] = peer;
  const secret = process.env.EMPIRE_PROXY_AUTH_SECRET || '';
  if (secret) headers['x-empire-proxy-secret'] = secret;
  if (!isLoopbackPeer(peer)) {
    for (const key of Object.keys(headers)) {
      if (key.toLowerCase().startsWith('tailscale-user-')) delete headers[key];
    }
    return;
  }
  if (login) headers['x-empire-tailscale-verified'] = '1';
}

function headerValue(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] || '';
  return value || '';
}

/** Middleware copy: drop Tailscale identity unless the socket stamp says loopback. */
export function applyTailscaleHeaderPolicy(headers: Headers): Headers {
  const next = new Headers(headers);
  const peer = next.get('x-empire-socket-peer') || '';
  if (!isLoopbackPeer(peer)) {
    for (const key of [...next.keys()]) {
      if (key.toLowerCase().startsWith('tailscale-user-')) next.delete(key);
    }
    next.delete('x-empire-tailscale-verified');
    return next;
  }
  if (next.get('tailscale-user-login')) next.set('x-empire-tailscale-verified', '1');
  else next.delete('x-empire-tailscale-verified');
  return next;
}
