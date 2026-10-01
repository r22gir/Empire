/**
 * This instance's API prefix.
 *
 * Workroom leaves NEXT_PUBLIC_API_URL unset and uses http://localhost:8000/api/v1.
 * The AMP edition sets NEXT_PUBLIC_API_URL (and EMPIRE_API_BASE for the
 * Next.js rewrite) to its own process.
 */
export const EMPIRE_API_V1_DEFAULT = 'http://localhost:8000/api/v1';

export function empireApiV1(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL || EMPIRE_API_V1_DEFAULT).trim();
  return raw.replace(/\/$/, '');
}
