#!/usr/bin/env python3
"""Fail if anonymous clients can read sensitive Luxe API routes.

Prints status codes and the gate error field only. Response bodies are not
printed (they can contain customer names and amounts).

Examples:

    # App-level check against a local backend, pretending to be the public host
    # the Cloudflare tunnel presents:
    python3 backend/scripts/luxe_public_edge_smoke.py \\
        --base-url http://127.0.0.1:8000 \\
        --host luxe.empirebox.store

    # Same process, private cash path (must NOT be denied by this gate):
    python3 backend/scripts/luxe_public_edge_smoke.py \\
        --base-url http://127.0.0.1:8000 \\
        --expect-open

    # After deploy, from outside the tailnet:
    python3 backend/scripts/luxe_public_edge_smoke.py \\
        --base-url https://luxe.empirebox.store
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

SENSITIVE_PATHS = (
    "/api/v1/quotes?limit=1",
    "/api/v1/quotes-v2",
    "/api/v1/finance/invoices?limit=1",
    "/api/v1/invoices?limit=1",
    "/api/v1/finance/dashboard",
    "/api/v1/payments/history",
    "/api/v1/payments/overdue",
    "/api/v1/jobs/dashboard",
    "/api/v1/leads/leadforge/prospects/stats",
    "/api/v1/leadforge/intake/1",
    "/api/v1/pricing/canonical/status",
    "/api/v1/max/health",
    "/api/v1/crm/customers",
    "/api/v1/quote-requests",
    "/api/v1/portal/links",
    "/api/v1/intake/admin/projects",
    "/health",
)

PUBLIC_CAPTURE = (
    "/api/v1/intake/login",
    "/api/v1/leadforge/intake",
)
DENIAL_ERROR = "luxe_public_edge_denied"


def _fetch(url: str, host: str | None, method: str = "GET", body: bytes | None = None) -> tuple[int, str, str]:
    # A browser User-Agent. Cloudflare's bot check answers the default Python
    # agent with 403 before the origin sees the request, which hides whether
    # the API gate is actually closed.
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; EmpireLuxeEdgeSmoke/1.0)",
    }
    if host:
        headers["Host"] = host
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read(4096)
            return response.status, response.headers.get("content-type", ""), payload.decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        payload = exc.read(4096)
        return exc.code, exc.headers.get("content-type", ""), payload.decode("utf-8", "replace")


def _error_field(payload: str) -> str:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return ""
    if isinstance(data, dict):
        return str(data.get("error") or "")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Origin only, no path")
    parser.add_argument("--host", default="", help="Host header. Use luxe.empirebox.store against localhost:8000")
    parser.add_argument(
        "--expect-open",
        action="store_true",
        help="Private cash path: sensitive routes must NOT carry the public-edge denial",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    host = args.host.strip() or None
    failed = False

    for path in SENSITIVE_PATHS:
        status, ctype, payload = _fetch(f"{base}{path}", host)
        error = _error_field(payload)
        denied = status == 401 and error == DENIAL_ERROR
        print(f"{status} error={error or '-'} {path}")
        if args.expect_open:
            if denied:
                print(f"FAIL private path was denied: {path}", file=sys.stderr)
                failed = True
        elif not denied:
            print(f"FAIL anonymous sensitive path was not denied: {path} ctype={ctype.split(';')[0]}", file=sys.stderr)
            failed = True

    if not args.expect_open:
        for path in PUBLIC_CAPTURE:
            status, _ctype, payload = _fetch(
                f"{base}{path}",
                host,
                method="POST",
                body=b"{}",
            )
            error = _error_field(payload)
            print(f"{status} error={error or '-'} POST {path}")
            if status == 401 and error == DENIAL_ERROR:
                print(f"FAIL public capture was closed by the edge gate: POST {path}", file=sys.stderr)
                failed = True
        status, _ctype, payload = _fetch(
            f"{base}/api/v1/leadforge/intake/1/quote",
            host,
            method="POST",
            body=b"{}",
        )
        error = _error_field(payload)
        print(f"{status} error={error or '-'} POST /api/v1/leadforge/intake/1/quote")
        if status == 401 and error == DENIAL_ERROR:
            print("FAIL Workroom quote-from-brief was closed by the edge gate", file=sys.stderr)
            failed = True

    if failed:
        print("luxe public edge smoke: FAIL")
        return 1
    print("luxe public edge smoke: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
