"""Localhost / internal-token support health and dry-run.

Nightly checks can GET /api/v1/support/health for a yes/no.
Ticket APIs stay authenticated; this path never sends mail or WhatsApp.
"""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/support", tags=["support-health"])

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
INTERNAL_HEADER = "x-empire-internal-token"


def _peer_host(request: Request) -> str:
    """Raw peer only. X-Forwarded-For is ignored so this cannot be spoofed."""
    host = (request.client.host if request.client else "") or ""
    return host.strip().lower().strip("[]")


def request_is_loopback(request: Request) -> bool:
    host = _peer_host(request)
    if host in LOOPBACK_HOSTS:
        return True
    if host == "testclient" and (
        os.getenv("PYTEST_CURRENT_TEST") or os.getenv("EMPIRE_TEST_GUARD")
    ):
        return True
    return False


def _internal_token() -> str:
    return (
        (os.getenv("SUPPORT_DRYRUN_TOKEN") or "").strip()
        or (os.getenv("EMPIRE_INTERNAL_TOKEN") or "").strip()
    )


def token_authorized(request: Request) -> bool:
    expected = _internal_token()
    if not expected:
        return False
    offered = (request.headers.get(INTERNAL_HEADER) or "").strip()
    if not offered:
        return False
    return hmac.compare_digest(offered, expected)


def require_internal_or_localhost(request: Request) -> None:
    if request_is_loopback(request) or token_authorized(request):
        return
    raise HTTPException(
        status_code=403,
        detail="support dry-run is localhost or internal-token only",
    )


def _run_report() -> dict:
    from app.services.support_dryrun import run_support_dryrun

    report = run_support_dryrun()
    return report.to_dict()


@router.get("/health")
def support_health(request: Request):
    """Yes/no: is Empire support working? Isolated dry-run, no send."""
    require_internal_or_localhost(request)
    body = _run_report()
    return {
        "ok": body["ok"],
        "support_working": body["support_working"],
        "yes_no": body["yes_no"],
        "dry_run": True,
        "sent": False,
        "edition": body["edition"],
        "assistant": body["assistant"],
        "portable_to": body["portable_to"],
        "steps": body["steps"],
        "ticket_id": body.get("ticket_id"),
        "cleaned": body.get("cleaned"),
    }


@router.post("/dry-run")
@router.get("/dry-run")
def support_dry_run(request: Request):
    """Full isolated dry-run report, including the rendered Rafael notice."""
    require_internal_or_localhost(request)
    return _run_report()
