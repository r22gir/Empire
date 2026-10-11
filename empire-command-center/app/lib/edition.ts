/** Studio / Workroom edition helpers. Family editions override in their own checkouts. */

export function editionFromEnv(): string {
  if (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_EMPIRE_EDITION) {
    return String(process.env.NEXT_PUBLIC_EMPIRE_EDITION).trim().toLowerCase();
  }
  return 'workroom';
}

export function isFamilyEdition(edition = editionFromEnv()): boolean {
  return edition === 'amp' || edition === 'maxine';
}
