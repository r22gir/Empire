"""Deny-by-default gate for the public Luxe hostnames.

Cloudflare tunnel ``empire-main`` sends ``luxe.empirebox.store/api/v1/*``
straight at this process (``localhost:8000``). That path never reaches the
Next.js intake allowlist, and the FastAPI routers for quotes, invoices,
payments, jobs, leads, and MAX do not require a session.

The gate keys off the hostname the client (or the tunnel) presented:
``Host``, ``X-Forwarded-Host``, or ``X-Original-Host``. Localhost, LAN, and
Tailscale addresses are not in that set, so EmpireDell cash-path curls to
``127.0.0.1:8000`` stay unchanged.

Keep this allowlist in sync with ``empire-command-center/middleware.ts``.
"""

from __future__ import annotations

import os
import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse

DENIAL_ERROR = "luxe_public_edge_denied"
RATE_LIMIT_ERROR = "luxe_public_edge_rate_limited"

DEFAULT_PUBLIC_LUXE_HOSTS = frozenset(
    {
        "luxe.empirebox.store",
        "test-luxe.empirebox.store",
    }
)

# Unauthenticated account takeover. Not a capture form.
_BLOCKED_EXACT = frozenset(
    {
        "/api/v1/intake/reset-password",
    }
)

# Operator intake CRM. Route-level JWT is not enough on a public hostname:
# these dumps stay on Tailscale / the Access-protected studio host.
_BLOCKED_PREFIXES = (
    "/api/v1/intake/admin",
    # Owner list of every submission, including photo analysis.
    "/api/v1/intake/owner",
)

# Anonymous capture posts. Route handlers add their own slowapi limits.
# /api/v1/leadforge/intake is the Workroom brief shared by LuxeForge
# (capture_channel=luxeforge) and LeadForge (capture_channel=leadforge).
# It writes one customer, one prospect, and one lead. It does not list them.
_PUBLIC_POST_EXACT = frozenset(
    {
        "/api/v1/intake/signup",
        "/api/v1/intake/login",
        "/api/v1/photos/upload",
        "/api/v1/leadforge/intake",
    }
)

_WORKROOM_INTAKE_PREFIX = "/api/v1/leadforge/intake/"

# Client portal paths. Intake JWT (or, for fabric rows and swatch bytes, the
# project id the portal just created) is enforced by the handler or is the
# existing capture design. These prefixes do not list quotes, invoices, or CRM.
_PUBLIC_ANY_METHOD_EXACT = frozenset(
    {
        "/intake",
        "/favicon.ico",
        "/robots.txt",
        "/api/v1/intake/me",
        "/api/v1/intake/projects",
    }
)

_PUBLIC_ANY_METHOD_PREFIXES = (
    "/intake/",
    "/_next/",
    "/intake_uploads/",
    "/api/v1/intake/projects/",
    "/api/v1/fabrics/intake-project/",
    "/api/v1/photos/serve/intake/",
)

# Owner action that lives under the fabric prefix. Not client capture.
_BLOCKED_SUFFIXES = (
    "/match",
)

# Paths the sunrise smoke found open on the public Luxe edge.
SENSITIVE_ANONYMOUS_PATHS = (
    ("GET", "/api/v1/quotes"),
    ("GET", "/api/v1/quotes-v2"),
    ("GET", "/api/v1/finance/invoices"),
    ("GET", "/api/v1/invoices"),
    ("GET", "/api/v1/finance/dashboard"),
    ("GET", "/api/v1/payments/history"),
    ("GET", "/api/v1/payments/overdue"),
    ("GET", "/api/v1/payments/subscriptions"),
    ("GET", "/api/v1/jobs/dashboard"),
    ("GET", "/api/v1/leads/leadforge/prospects/stats"),
    ("GET", "/api/v1/leads/pipeline"),
    ("GET", "/api/v1/leads/leadforge/providers"),
    ("GET", "/api/v1/leadforge/intake/1"),
    ("GET", "/api/v1/pricing/canonical/status"),
    ("GET", "/api/v1/pricing/labor-rates"),
    ("GET", "/api/v1/quotes/pricing-tables"),
    ("GET", "/api/v1/max/health"),
    ("GET", "/api/v1/crm/customers"),
    ("GET", "/api/v1/quote-requests"),
    ("GET", "/api/v1/portal/links"),
    ("POST", "/api/v1/quotes"),
    ("POST", "/api/v1/payments/checkout"),
    ("GET", "/api/v1/payments/webhook"),
    ("POST", "/api/v1/intake/reset-password"),
    ("GET", "/api/v1/intake/admin/projects"),
    ("GET", "/api/v1/intake/admin/users"),
    ("GET", "/api/v1/intake/owner/submissions"),
    ("GET", "/api/v1/fabrics"),
    ("GET", "/api/v1/photos/quote/example"),
    ("GET", "/docs"),
    ("GET", "/openapi.json"),
    ("GET", "/health"),
)

_RATE_LOCK = threading.Lock()
_RATE_BUCKETS: dict[str, list[float]] = {}
_WINDOW_SECONDS = 60.0


def public_luxe_hosts() -> frozenset[str]:
    """Defaults plus any extra names in ``LUXE_PUBLIC_EDGE_HOSTS``.

    The defaults cannot be removed via env. An empty or missing variable
    still locks ``luxe`` and ``test-luxe``.
    """
    hosts = set(DEFAULT_PUBLIC_LUXE_HOSTS)
    extra = os.getenv("LUXE_PUBLIC_EDGE_HOSTS", "")
    for item in extra.split(","):
        normalized = normalize_host(item)
        if normalized:
            hosts.add(normalized)
    return frozenset(hosts)


def normalize_host(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return ""
    value = value.split(",")[0].strip()
    if value.startswith("["):
        # IPv6 literal, optional port: [2001:db8::1]:8000
        end = value.find("]")
        return value[: end + 1] if end != -1 else value
    if ":" in value:
        value = value.split(":", 1)[0]
    return value.rstrip(".")


def normalize_path(path: str) -> str:
    path = (path or "/").split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    while "//" in path:
        path = path.replace("//", "/")
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def request_hits_public_luxe_edge(request: Request) -> bool:
    hosts = public_luxe_hosts()
    candidates = [
        request.headers.get("host", ""),
        request.headers.get("x-forwarded-host", ""),
        request.headers.get("x-original-host", ""),
    ]
    for raw in candidates:
        # X-Forwarded-Host can be a chain. Every hop counts: a public name
        # anywhere in the chain means the request crossed that edge.
        for part in (raw or "").split(","):
            if normalize_host(part) in hosts:
                return True
    return False


def is_public_luxe_path_allowed(method: str, path: str) -> bool:
    """True when this method/path is the deliberate public intake surface."""
    method = (method or "GET").upper()
    path = normalize_path(path)
    if ".." in path or "\\" in path:
        return False
    if path in _BLOCKED_EXACT:
        return False
    for prefix in _BLOCKED_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return False
    if path.endswith(_BLOCKED_SUFFIXES) and path.startswith("/api/v1/fabrics/intake-project/"):
        return False

    if method == "OPTIONS":
        return _path_has_any_public_method(path)
    if method == "HEAD":
        method = "GET"

    if method == "POST" and (path in _PUBLIC_POST_EXACT or _is_workroom_quote_post(path)):
        return True
    if path in _PUBLIC_ANY_METHOD_EXACT:
        return True
    for prefix in _PUBLIC_ANY_METHOD_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _is_workroom_quote_post(path: str) -> bool:
    """POST /api/v1/leadforge/intake/{lead_id}/quote — one brief, one quote.

    GET of that lead stays closed. Integer ids are guessable, so a read
    would be a CRM dump. The quote post does not list quotes.
    """
    if not path.startswith(_WORKROOM_INTAKE_PREFIX) or not path.endswith("/quote"):
        return False
    lead_id = path[len(_WORKROOM_INTAKE_PREFIX) : -len("/quote")]
    return bool(lead_id) and lead_id.isdigit()


def _path_has_any_public_method(path: str) -> bool:
    if path in _PUBLIC_POST_EXACT or _is_workroom_quote_post(path):
        return True
    if path in _PUBLIC_ANY_METHOD_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_ANY_METHOD_PREFIXES)


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < 1:
        return default
    return value


def clear_public_edge_rate_buckets() -> None:
    with _RATE_LOCK:
        _RATE_BUCKETS.clear()


def _consume(key: str, limit: int, now: float) -> bool:
    with _RATE_LOCK:
        stamps = [stamp for stamp in _RATE_BUCKETS.get(key, []) if now - stamp < _WINDOW_SECONDS]
        if len(stamps) >= limit:
            _RATE_BUCKETS[key] = stamps
            return False
        stamps.append(now)
        _RATE_BUCKETS[key] = stamps
        return True


def consume_public_edge_rate_limit(client_ip: str, method: str, path: str, now: float | None = None) -> bool:
    """Return False when this public-edge client is over the per-minute cap."""
    moment = time.monotonic() if now is None else now
    ip = client_ip or "unknown"
    general = _positive_int_env("LUXE_PUBLIC_EDGE_RATE_PER_MINUTE", 60)
    if not _consume(ip, general, moment):
        return False
    if method.upper() == "POST" and normalize_path(path) == "/api/v1/photos/upload":
        upload_cap = _positive_int_env("LUXE_PUBLIC_EDGE_UPLOAD_PER_MINUTE", 10)
        if not _consume(f"{ip}|upload", upload_cap, moment):
            return False
    normalized = normalize_path(path)
    if method.upper() == "POST" and (
        normalized == "/api/v1/leadforge/intake" or _is_workroom_quote_post(normalized)
    ):
        intake_cap = _positive_int_env("LUXE_PUBLIC_EDGE_INTAKE_PER_MINUTE", 10)
        if not _consume(f"{ip}|workroom-intake", intake_cap, moment):
            return False
    return True


def client_ip(request: Request) -> str:
    cf = (request.headers.get("cf-connecting-ip") or "").split(",")[0].strip()
    if cf:
        return cf
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def luxe_public_edge_response(request: Request) -> JSONResponse | None:
    """401/429 when a public Luxe hostname asked for something other than intake.

    Returns None when the request should proceed (private host, or an
    allowlisted public capture path under the rate cap).
    """
    if not request_hits_public_luxe_edge(request):
        return None

    path = normalize_path(request.url.path)
    method = request.method.upper()
    headers = {
        "Cache-Control": "no-store",
        "X-Empire-Edge": "luxe-public-denied",
    }
    if not is_public_luxe_path_allowed(method, path):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required", "error": DENIAL_ERROR},
            headers=headers,
        )
    if not consume_public_edge_rate_limit(client_ip(request), method, path):
        headers["Retry-After"] = str(int(_WINDOW_SECONDS))
        headers["X-Empire-Edge"] = "luxe-public-rate-limited"
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded", "error": RATE_LIMIT_ERROR},
            headers=headers,
        )
    return None
