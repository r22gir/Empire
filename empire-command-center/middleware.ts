import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const LUXE_PUBLIC_HOST = "luxe.empirebox.store";
const LUXE_PUBLIC_REDIRECT_PATHS = new Set(["/", "/luxe", "/luxe/", "/luxeforge", "/luxeforge/"]);

export function middleware(request: NextRequest) {
  const host = (request.headers.get("host") || "").split(":")[0].toLowerCase();
  if (host !== LUXE_PUBLIC_HOST) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  if (!LUXE_PUBLIC_REDIRECT_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = "/intake";
  return NextResponse.redirect(url);
}
