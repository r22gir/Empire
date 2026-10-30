// Public Empire Fine Fabrics store host.
//
// fabrics.empirebox.store serves the /fine-fabrics Next.js store.
// Operator screens and unrelated APIs 404 here. Catalog, cart,
// checkout, samples, and the fine-fabrics API stay reachable.
//
// Kept free of Next imports so node:test can exercise it directly.

export const FABRICS_PUBLIC_HOSTS: ReadonlySet<string> = new Set([
  "fabrics.empirebox.store",
  "test-fabrics.empirebox.store",
]);

export const FABRICS_STORE_INDEX = "/fine-fabrics";

const FABRICS_ALLOWLIST_EXACT: ReadonlySet<string> = new Set([
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
  "/merchant.xml",
  "/ff-placeholder-swatch.svg",
]);

const FABRICS_ALLOWLIST_PREFIXES = [
  "/fine-fabrics",
  "/_next/",
  "/api/v1/fine-fabrics",
];

const FABRICS_DENY_PREFIXES = [
  "/fine-fabrics/admin",
];

export type FabricsHostDecision =
  | { action: "pass" }
  | { action: "rewrite"; pathname: string }
  | { action: "next" }
  | { action: "not-found" };

export function normalizeFabricsHost(rawHost: string | null | undefined): string {
  return (rawHost || "").split(":")[0].trim().toLowerCase();
}

export function isFabricsHost(rawHost: string | null | undefined): boolean {
  return FABRICS_PUBLIC_HOSTS.has(normalizeFabricsHost(rawHost));
}

export function fabricsHostDecision(
  rawHost: string | null | undefined,
  _method: string,
  pathname: string,
): FabricsHostDecision {
  if (!isFabricsHost(rawHost)) return { action: "pass" };

  const path = pathname || "/";
  if (path.includes("..") || path.includes("\\") || path.includes("//")) {
    return { action: "not-found" };
  }
  if (path === "/") return { action: "rewrite", pathname: FABRICS_STORE_INDEX };
  if (path === "/sitemap.xml") return { action: "rewrite", pathname: "/fine-fabrics/sitemap.xml" };
  if (path === "/merchant.xml") return { action: "rewrite", pathname: "/fine-fabrics/merchant.xml" };
  if (FABRICS_DENY_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))) {
    return { action: "not-found" };
  }
  if (FABRICS_ALLOWLIST_EXACT.has(path)) return { action: "next" };
  if (FABRICS_ALLOWLIST_PREFIXES.some((prefix) => path === prefix || path.startsWith(prefix))) {
    return { action: "next" };
  }
  return { action: "not-found" };
}
