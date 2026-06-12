import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const LUXE_PUBLIC_HOST = "luxe.empirebox.store";
const LUXE_PUBLIC_REDIRECT_PATHS = new Set(["/", "/luxe", "/luxe/", "/luxeforge", "/luxeforge/"]);

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

  // --- Existing LUXE block (untouched) ---
  if (host !== LUXE_PUBLIC_HOST) {
    // fall through to FORGE block
  } else if (!LUXE_PUBLIC_REDIRECT_PATHS.has(pathname)) {
    return NextResponse.next();
  } else {
    const url = request.nextUrl.clone();
    url.pathname = "/intake";
    return NextResponse.redirect(url);
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
