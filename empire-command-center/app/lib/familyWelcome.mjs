/** Family first-login welcome. Plain JS so Node 20 can import it in tests. */

import { isFamilyPublicPath, isFamilySurface } from './familyChrome.mjs';
import ampDeck from './welcome/amp.json' with { type: 'json' };
import maxineDeck from './welcome/maxine.json' with { type: 'json' };

export const WELCOME_REPLAY_EVENT = 'empire:family-welcome-replay';
export const WELCOME_QUERY = 'bienvenida';
export const WELCOME_HELP_LABEL = 'Ver bienvenida';
export const WELCOME_SKIP_LABEL = 'Saltar';
export const WELCOME_SKIP_ARIA = 'Saltar / Skip';
export const DEFAULT_INTERVAL_MS = 8000;
export const SLIDE_COUNT = 6;

const FAMILY = new Set(['amp', 'maxine']);

export function familyWelcomeEdition(edition) {
  const key = String(edition || '').trim().toLowerCase();
  if (key === 'maxine') return 'maxine';
  if (key === 'amp' || key === 'max-e' || key === 'max_e' || key === 'maxe') return 'amp';
  return '';
}

export function familyWelcomeAssistant(edition) {
  return familyWelcomeEdition(edition) === 'maxine' ? 'Maxine' : 'Max-e';
}

export function defaultWelcomeDeck(edition) {
  const kind = familyWelcomeEdition(edition) || 'amp';
  return kind === 'maxine' ? maxineDeck : ampDeck;
}

export function replayRequested(search) {
  const raw = String(search || '');
  const q = raw.startsWith('?') ? raw.slice(1) : raw;
  const params = new URLSearchParams(q);
  const value = (params.get(WELCOME_QUERY) || '').trim().toLowerCase();
  return value === '1' || value === 'true' || value === 'si' || value === 'sí';
}

export function shouldShowFamilyWelcome({
  edition = '',
  host = '',
  pathname = '/',
  seen = false,
  replay = false,
} = {}) {
  if (!isFamilySurface(edition, host)) return false;
  if (isFamilyPublicPath(pathname)) return false;
  if (replay) return true;
  return !seen;
}

export function autoAdvanceEnabled(prefersReducedMotion, playing = true) {
  return Boolean(playing) && !prefersReducedMotion;
}

export function nextSlideIndex(index, total) {
  const count = Math.max(1, Number(total) || 1);
  const current = Math.max(0, Number(index) || 0);
  return Math.min(count - 1, current + 1);
}

export function prevSlideIndex(index) {
  const current = Math.max(0, Number(index) || 0);
  return Math.max(0, current - 1);
}

export function isLastSlide(index, total) {
  const count = Math.max(1, Number(total) || 1);
  return Math.max(0, Number(index) || 0) >= count - 1;
}

export function sanitizeWelcomeImage(src) {
  const value = String(src || '').trim();
  if (!value) return '';
  if (!value.startsWith('/') || value.startsWith('//') || value.includes('..')) return '';
  if (value.includes('\\') || value.includes('\n') || value.includes('\r')) return '';
  return value;
}

export function requestFamilyWelcomeReplay() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(WELCOME_REPLAY_EVENT));
  try {
    const url = new URL(window.location.href);
    url.searchParams.set(WELCOME_QUERY, '1');
    window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
  } catch {
    // ignore
  }
}

export function clearWelcomeReplayQuery() {
  if (typeof window === 'undefined') return;
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.has(WELCOME_QUERY)) return;
    url.searchParams.delete(WELCOME_QUERY);
    const search = url.searchParams.toString();
    window.history.replaceState({}, '', `${url.pathname}${search ? `?${search}` : ''}${url.hash}`);
  } catch {
    // ignore
  }
}

export function welcomePayloadLooksPrivate(payload) {
  if (!payload || typeof payload !== 'object') return false;
  if ('users' in payload) return false;
  if (payload.email || payload.seen_by) return false;
  return Array.isArray(payload.slides);
}

export { FAMILY };
