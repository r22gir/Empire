import { isFamilyEdition, isFamilyHost } from './familyChrome.mjs';

export const FAMILY_LOGIN_PATH = '/login';

export function shouldGateFamilyShell(edition: string = '', host: string = ''): boolean {
  return isFamilyEdition(edition) || isFamilyHost(host);
}

/** True when /api/v1/amp/me (or whoami) says the visitor is not signed in. */
export function familyAuthFailedStatus(status: number): boolean {
  return status === 401 || status === 403;
}
