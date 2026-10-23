/** Last client/server error seen by this tab. Pedir ayuda attaches it to the ticket. */

let lastError = '';

export function recordClientError(error: unknown): string {
  const text = normalizeError(error);
  if (text) lastError = text.slice(0, 800);
  return lastError;
}

export function lastClientError(): string {
  return lastError;
}

export function currentHelpScreen(extra?: string): string {
  if (typeof window === 'undefined') return (extra || '').trim();
  const path = `${window.location.pathname || '/'}${window.location.hash || ''}`;
  const title = (document.title || '').trim();
  return [path, title, extra].filter(Boolean).join(' · ').slice(0, 500);
}

function normalizeError(error: unknown): string {
  if (!error) return '';
  if (typeof error === 'string') return error.trim();
  if (error instanceof Error) return (error.message || error.name || '').trim();
  try {
    return JSON.stringify(error).slice(0, 800);
  } catch {
    return String(error);
  }
}
