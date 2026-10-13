/** Public BusinessOps self-serve signup is locked until launch. */

export type BusinessopsInfo = {
  public_signup_enabled?: boolean;
};

export function isPublicSignupEnabled(info?: BusinessopsInfo | null): boolean {
  return info?.public_signup_enabled === true;
}
