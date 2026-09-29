// Public Empire Workroom showroom host (Style B, quiet luxury).
//
// workroom.empirebox.store serves one static page from
// public/workroom-showroom/. It is a read-only marketing surface:
// GET/HEAD only, "/" is rewritten to the showroom index, the showroom
// asset folder is allowed, and every other path 404s. Operator screens
// (/workroom, /intake, /max, ...) and /api/* are never reachable here.
//
// Kept free of Next imports so node:test can exercise it directly.

export const WORKROOM_PUBLIC_HOSTS: ReadonlySet<string> = new Set([
  "workroom.empirebox.store",
]);

export const WORKROOM_SHOWROOM_PREFIX = "/workroom-showroom/";
export const WORKROOM_SHOWROOM_INDEX = "/workroom-showroom/index.html";

const WORKROOM_ALLOWLIST_EXACT: ReadonlySet<string> = new Set([
  "/favicon.ico",
]);

export type WorkroomHostDecision =
  | { action: "pass" }
  | { action: "method-not-allowed" }
  | { action: "rewrite"; pathname: string }
  | { action: "next" }
  | { action: "not-found" };

export function normalizeHost(rawHost: string | null | undefined): string {
  return (rawHost || "").split(":")[0].trim().toLowerCase();
}

export function isWorkroomHost(rawHost: string | null | undefined): boolean {
  return WORKROOM_PUBLIC_HOSTS.has(normalizeHost(rawHost));
}

export function workroomHostDecision(
  rawHost: string | null | undefined,
  method: string,
  pathname: string,
): WorkroomHostDecision {
  if (!isWorkroomHost(rawHost)) return { action: "pass" };

  const verb = (method || "").toUpperCase();
  if (verb !== "GET" && verb !== "HEAD") return { action: "method-not-allowed" };

  const path = pathname || "/";
  if (path === "/") return { action: "rewrite", pathname: WORKROOM_SHOWROOM_INDEX };
  if (path.includes("..") || path.includes("\\") || path.includes("//")) {
    return { action: "not-found" };
  }
  if (WORKROOM_ALLOWLIST_EXACT.has(path)) return { action: "next" };
  if (path.startsWith(WORKROOM_SHOWROOM_PREFIX)) return { action: "next" };
  return { action: "not-found" };
}
