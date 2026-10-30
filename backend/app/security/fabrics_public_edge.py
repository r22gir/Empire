"""Deny-by-default gate for fabrics.empirebox.store.

Cloudflare tunnels /api/v1/* to FastAPI the same way Luxe does. Only the
customer catalog, preview, samples, and test-mode checkout stay public.
Owner import, vendor flags, and photo uploads stay on studio / localhost.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

DENIAL_ERROR = "fabrics_public_edge_denied"

DEFAULT_PUBLIC_FABRICS_HOSTS = frozenset(
    {
        "fabrics.empirebox.store",
        "test-fabrics.empirebox.store",
    }
)

_PUBLIC_GET_EXACT = frozenset(
    {
        "/favicon.ico",
        "/robots.txt",
        "/api/v1/fine-fabrics/catalog",
        "/api/v1/fine-fabrics/categories",
        "/api/v1/fine-fabrics/health",
    }
)

_PUBLIC_GET_PREFIXES = (
    "/fine-fabrics",
    "/_next/",
    "/api/v1/fine-fabrics/products/",
    "/api/v1/fine-fabrics/photos/",
)

_PUBLIC_POST_EXACT = frozenset(
    {
        "/api/v1/fine-fabrics/checkout",
        "/api/v1/fine-fabrics/samples",
        "/api/v1/fine-fabrics/preview",
    }
)


def normalize_host(raw: str | None) -> str:
    return (raw or "").split(",")[0].strip().split(":")[0].lower().rstrip(".")


def request_host(request: Request) -> str:
    for header in ("x-forwarded-host", "x-original-host", "host"):
        value = request.headers.get(header)
        if value:
            return normalize_host(value)
    return ""


def is_public_fabrics_host(host: str | None) -> bool:
    return normalize_host(host) in DEFAULT_PUBLIC_FABRICS_HOSTS


def normalize_path(pathname: str) -> str:
    path = (pathname or "/").split("?")[0].split("#")[0] or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    while "//" in path:
        path = path.replace("//", "/")
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def is_public_fabrics_path_allowed(method: str, pathname: str) -> bool:
    path = normalize_path(pathname)
    verb = (method or "GET").upper()
    if ".." in path or "\\" in path:
        return False
    if verb == "OPTIONS":
        return (
            path in _PUBLIC_GET_EXACT
            or path in _PUBLIC_POST_EXACT
            or any(path.startswith(p) for p in _PUBLIC_GET_PREFIXES)
        )
    if verb == "HEAD":
        verb = "GET"
    if verb == "GET" and path in _PUBLIC_GET_EXACT:
        return True
    if verb == "GET" and any(path == p or path.startswith(p) for p in _PUBLIC_GET_PREFIXES):
        return True
    if verb == "POST" and path in _PUBLIC_POST_EXACT:
        return True
    return False


def fabrics_public_edge_response(request: Request) -> JSONResponse | None:
    host = request_host(request)
    if not is_public_fabrics_host(host):
        return None
    if is_public_fabrics_path_allowed(request.method, request.url.path):
        return None
    return JSONResponse(
        status_code=401,
        content={"detail": "Authentication required", "error": DENIAL_ERROR},
        headers={"Cache-Control": "no-store", "X-Empire-Edge": "fabrics-public-denied"},
    )
