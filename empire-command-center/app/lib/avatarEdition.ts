/**
 * Simli / TalkingHead edition for the current Command Center checkout.
 *
 * Empire (this tree) is Max / workroom. Family checkouts override EDITION
 * (amp -> Max-e, maxine -> Maxine). Family editions must never fall back
 * to Max's workroom face, even if a URL or iframe omits edition=.
 *
 * This module is importable from Node tests (no Next / edition.ts import).
 * Callers pass EDITION.avatarEdition || EDITION.id as the profile.
 */
export type AvatarEdition = 'workroom' | 'max_e' | 'maxine';

export type EditionHint = {
  id?: string;
  avatarEdition?: string;
};

const FAMILY: ReadonlySet<AvatarEdition> = new Set(['max_e', 'maxine']);

export function normalizeAvatarEdition(raw?: string | null): AvatarEdition | null {
  const key = String(raw || '').trim().toLowerCase().replace(/-/g, '_');
  if (key === 'amp' || key === 'maxe' || key === 'max_e') return 'max_e';
  if (key === 'maxine') return 'maxine';
  if (key === 'workroom' || key === 'empire' || key === 'max') return 'workroom';
  return null;
}

function profileEdition(profile?: string | EditionHint | null): AvatarEdition {
  if (profile && typeof profile === 'object') {
    return profileEdition(profile.avatarEdition || profile.id);
  }
  const fromArg = normalizeAvatarEdition(profile);
  if (fromArg) return fromArg;
  return 'workroom';
}

/**
 * Resolve the face edition for an iframe / Simli session.
 * `hint` is an explicit edition or product (workroom, amp, maxine).
 * A family profile never returns workroom, even if hint is missing or "workroom".
 */
export function resolveAvatarEdition(
  hint?: string | null,
  profile?: string | EditionHint | null,
): AvatarEdition {
  const fromProfile = profileEdition(profile);
  const fromHint = normalizeAvatarEdition(hint);
  if (FAMILY.has(fromProfile)) return fromProfile;
  if (fromHint && FAMILY.has(fromHint)) return fromHint;
  if (fromHint === 'workroom') return 'workroom';
  return fromProfile;
}

export function isFamilyAvatarEdition(edition?: string | null): boolean {
  const key = normalizeAvatarEdition(edition);
  return !!key && FAMILY.has(key);
}

export function avatarFrameSrc(
  hint?: string | null,
  extras?: Record<string, string>,
  profile?: string | EditionHint | null,
): string {
  const edition = resolveAvatarEdition(hint, profile);
  const q = new URLSearchParams({ edition, ...(extras || {}) });
  return `/avatar.html?${q.toString()}`;
}

/** Read edition from the current URL (?edition= or ?product=amp). */
export function editionFromLocation(search?: string): string | null {
  if (typeof search !== 'string') {
    if (typeof window === 'undefined') return null;
    search = window.location.search;
  }
  const params = new URLSearchParams(search);
  return params.get('edition') || params.get('product');
}
