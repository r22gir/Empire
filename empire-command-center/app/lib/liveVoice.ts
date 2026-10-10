/** Live-voice WebSocket URL and chrome. Same-origin on public hosts. */

export function isLocalHost(host: string): boolean {
  const h = String(host || '').split(':')[0].toLowerCase();
  return h === 'localhost' || h === '127.0.0.1' || h === '0.0.0.0' || h === '::1';
}

export function isFamilyEditionKey(edition?: string): boolean {
  const key = String(edition || '').trim().toLowerCase();
  return key === 'amp' || key === 'maxine';
}

/**
 * Browser <-> /api/v1/avatar/live.
 *
 * On amp.empirebox.store / maxine / studio the socket stays on this origin so
 * the AMP ``amp_session`` cookie (or Cloudflare Access on Workroom) is sent.
 * NEXT_PUBLIC_API_URL must not pull the browser onto studio from AMP.
 * Localhost still uses the API base so the socket hits the backend port,
 * not the Next.js rewrite (which does not upgrade WebSockets).
 */
export function liveVoiceUrl(
  location: { protocol?: string; host?: string },
  apiBase?: string,
): string {
  const host = String(location.host || '');
  const proto = location.protocol === 'http:' ? 'ws:' : 'wss:';
  if (host && !isLocalHost(host)) {
    return `${proto}//${host}/api/v1/avatar/live`;
  }
  const base = String(apiBase || '').replace(/\/$/, '');
  if (base.startsWith('https://')) return `${base.replace(/^https:/, 'wss:')}/avatar/live`;
  if (base.startsWith('http://')) return `${base.replace(/^http:/, 'ws:')}/avatar/live`;
  return `${proto}//${host || '127.0.0.1:8000'}/api/v1/avatar/live`;
}

export function liveVoiceConnectError(edition?: string): string {
  if (isFamilyEditionKey(edition)) {
    return 'Error de conexión. ¿Iniciaste sesión en esta página?';
  }
  return 'Connection error (are you signed in to studio.empirebox.store?)';
}

export function liveVoiceTitle(edition?: string, assistantName?: string): string {
  if (isFamilyEditionKey(edition)) {
    const name = (assistantName || '').trim() || (edition === 'maxine' ? 'Maxine' : 'Max-e');
    return `${name} · Voz en vivo`;
  }
  return 'Max · Live voice';
}
