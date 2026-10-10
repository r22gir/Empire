import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { familyHomeRedirect } from "./app/lib/familyChrome.mjs";
import { workroomHostDecision } from "./app/lib/workroomHost";

// Public Luxe hostnames. Keep this allowlist in sync with
// backend/app/security/luxe_public_edge.py. Cloudflare currently tunnels
// /api/v1/* straight to the backend, so the Python gate is the one that
// closes the hole. This middleware is the second lock for requests that
// do hit Next (pages, and /api/v1 if the tunnel rule is removed).
const LUXE_PUBLIC_HOSTS = new Set([
  "luxe.empirebox.store",
  "test-luxe.empirebox.store",
]);
const LUXE_BLOCKED_EXACT = new Set(["/api/v1/intake/reset-password"]);
const LUXE_BLOCKED_PREFIXES = ["/api/v1/intake/admin"];
const LUXE_PUBLIC_POST_EXACT = new Set([
  "/api/v1/intake/signup",
  "/api/v1/intake/login",
  "/api/v1/photos/upload",
  // Workroom designer brief (capture_channel luxeforge or leadforge). One
  // customer + one lead. Not the prospect/quote list.
  "/api/v1/leadforge/intake",
]);

function isWorkroomQuotePost(path: string): boolean {
  const prefix = "/api/v1/leadforge/intake/";
  if (!path.startsWith(prefix) || !path.endsWith("/quote")) return false;
  const leadId = path.slice(prefix.length, -"/quote".length);
  return leadId.length > 0 && /^[0-9]+$/.test(leadId);
}
const LUXE_PUBLIC_ANY_EXACT = new Set([
  "/intake",
  "/favicon.ico",
  "/robots.txt",
  "/api/v1/intake/me",
  "/api/v1/intake/projects",
]);
const LUXE_PUBLIC_ANY_PREFIXES = [
  "/intake/",
  "/_next/",
  "/intake_uploads/",
  "/api/v1/intake/projects/",
  "/api/v1/fabrics/intake-project/",
  "/api/v1/photos/serve/intake/",
];

function normalizeLuxePath(pathname: string): string {
  let path = pathname.split("?")[0].split("#")[0] || "/";
  if (!path.startsWith("/")) path = `/${path}`;
  while (path.includes("//")) path = path.split("//").join("/");
  if (path.length > 1 && path.endsWith("/")) path = path.slice(0, -1);
  return path;
}

function isLuxePathAllowed(method: string, pathname: string): boolean {
  const path = normalizeLuxePath(pathname);
  let verb = method.toUpperCase();
  if (path.includes("..") || path.includes("\\")) return false;
  if (LUXE_BLOCKED_EXACT.has(path)) return false;
  for (const prefix of LUXE_BLOCKED_PREFIXES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return false;
  }
  if (path.startsWith("/api/v1/fabrics/intake-project/") && path.endsWith("/match")) {
    return false;
  }
  if (verb === "OPTIONS") {
    if (LUXE_PUBLIC_POST_EXACT.has(path) || isWorkroomQuotePost(path) || LUXE_PUBLIC_ANY_EXACT.has(path)) return true;
    return LUXE_PUBLIC_ANY_PREFIXES.some((prefix) => path.startsWith(prefix));
  }
  if (verb === "HEAD") verb = "GET";
  if (verb === "POST" && (LUXE_PUBLIC_POST_EXACT.has(path) || isWorkroomQuotePost(path))) return true;
  if (LUXE_PUBLIC_ANY_EXACT.has(path)) return true;
  return LUXE_PUBLIC_ANY_PREFIXES.some((prefix) => path.startsWith(prefix));
}

// R1X-PUB-EMPIREBOX: Public apex landing hosts.
// The apex (and www) is a public, scrollable, SEO-renderable surface that
// serves the EmpireBox landing page. This block rewrites the apex root to
// /landing and 404s any path on the apex that is not in the landing-page
// allowlist. Operator screens (intake, services, etc.) are NOT reachable
// on the apex — they remain on the operator hostnames (studio, luxe, ...).
const PUBLIC_APEX_HOSTS = new Set(["empirebox.store", "www.empirebox.store"]);
const APEX_ALLOWLIST_EXACT = new Set(["/", "/landing", "/favicon.ico"]);
const APEX_ALLOWLIST_PREFIXES = ["/_next/", "/static/"];

function isApexPathAllowed(pathname: string): boolean {
  if (APEX_ALLOWLIST_EXACT.has(pathname)) return true;
  for (const prefix of APEX_ALLOWLIST_PREFIXES) {
    if (pathname.startsWith(prefix)) return true;
  }
  return false;
}

export function middleware(request: NextRequest) {
  const host = (request.headers.get("host") || "").split(":")[0].toLowerCase();
  const { pathname } = request.nextUrl;

  const home = familyHomeRedirect(
    process.env.NEXT_PUBLIC_EMPIRE_EDITION || "",
    pathname,
    Boolean(request.cookies.get("amp_session")?.value),
    host,
  );
  if (home) {
    const url = request.nextUrl.clone();
    url.pathname = home;
    return NextResponse.redirect(url);
  }

  // --- R1X-PUB-EMPIREBOX: public apex host block ---
  if (PUBLIC_APEX_HOSTS.has(host)) {
    // Apex is read-only public: allowlist GET/HEAD only.
    const method = request.method.toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      return new NextResponse("Method Not Allowed", { status: 405 });
    }

    // Rewrite "/" → "/landing" so the middleware serves the landing route
    // when a customer hits the bare apex domain. (Internal rewrite — the
    // browser URL stays https://empirebox.store/.)
    if (pathname === "/") {
      const url = request.nextUrl.clone();
      url.pathname = "/landing";
      return NextResponse.rewrite(url);
    }

    // Anything else on the apex must be in the landing-page allowlist.
    if (!isApexPathAllowed(pathname)) {
      return new NextResponse("Not Found", {
        status: 404,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    return NextResponse.next();
  }

  // --- WORKROOM showroom host: public Style B landing (read-only) ---
  // workroom.empirebox.store serves the static Empire Workroom showroom
  // from public/workroom-showroom/. "/" rewrites to its index.html; only
  // the showroom folder and favicon are reachable; everything else 404s.
  // The apex and Luxe rules above/below are unchanged. See
  // app/lib/workroomHost.ts (+ workroomHost.test.ts).
  const workroom = workroomHostDecision(host, request.method, pathname);
  if (workroom.action === "method-not-allowed") {
    return new NextResponse("Method Not Allowed", {
      status: 405,
      headers: { Allow: "GET, HEAD" },
    });
  }
  if (workroom.action === "rewrite") {
    const url = request.nextUrl.clone();
    url.pathname = workroom.pathname;
    return NextResponse.rewrite(url);
  }
  if (workroom.action === "not-found") {
    return new NextResponse("Not Found", {
      status: 404,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  if (workroom.action === "next") {
    return NextResponse.next();
  }

  // --- LUXE bucket: HARD-SCOPED to intake ---
  // Anonymous clients may open the intake pages and the narrow capture API.
  // Quotes, invoices, CRM, payments, jobs, leads, and MAX are 401 here.
  // Page URLs outside the allowlist redirect to /intake.
  if (LUXE_PUBLIC_HOSTS.has(host)) {
    if (!isLuxePathAllowed(request.method, pathname)) {
      const isApi =
        pathname.startsWith("/api/") ||
        pathname === "/docs" ||
        pathname === "/redoc" ||
        pathname === "/openapi.json" ||
        pathname === "/health";
      if (isApi) {
        return NextResponse.json(
          { detail: "Authentication required", error: "luxe_public_edge_denied" },
          {
            status: 401,
            headers: {
              "Cache-Control": "no-store",
              "X-Empire-Edge": "luxe-public-denied",
            },
          },
        );
      }
      const url = request.nextUrl.clone();
      url.pathname = "/intake";
      url.search = "";
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  // --- FORGE block: operator platform infrastructure surface ---
  // forge.empirebox.store is a Cloudflare Access-protected operator host.
  // It must NEVER serve a public marketing surface. The apex "/" must land
  // on the PlatformForge screen (app/platform/page.tsx) instead of the
  // default Owner/Dashboard. Any other path on forge passes through
  // (e.g. /workroom, /max) so founder nav still works.
  if (host === "forge.empirebox.store" && pathname === "/") {
    const url = request.nextUrl.clone();
    url.pathname = "/platform";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}
