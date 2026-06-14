"""
R1D-FIX-2 — ApostApp checkout success/cancel URL hardening tests.

These tests verify the post-R1D-FIX-2 behavior of /api/v1/payments/checkout:

  T-01: ApostApp checkout with valid public success/cancel URLs
        (https://apostapp.empirebox.store/...) → accepted, 200, cs_live_ session
  T-02: ApostApp checkout with missing success_url (uses the default
        operator URL) → 400, blocked by operator-hostname check
  T-03: ApostApp checkout with missing cancel_url → 400, same
  T-04: ApostApp checkout with success_url = http://localhost:3005 → 400
  T-05: ApostApp checkout with success_url = https://studio.empirebox.store/x
        → 400, blocked by operator-hostname check
  T-06: ApostApp checkout with success_url = https://127.0.0.1:3005/x
        → 400, blocked by loopback check
  T-07: ApostApp checkout with success_url = http://apostapp.empirebox.store/x
        (non-https) → 400, blocked by https check
  T-08: ApostApp checkout with success_url = https://api.empirebox.store/x
        → 400, blocked by operator-hostname check
  T-09: ApostApp checkout with cancel_url = https://luxe.empirebox.store/x
        → 400, blocked by operator-hostname check
  T-10: ApostApp checkout with success_url = https://apostapp.empirebox.store
        with no trailing path (just host) → 200 (bare host is valid)
  T-11: ApostApp checkout with success_url = '' (empty string) → 400
  T-12: Non-apostille SaaS flow (tier=pro) — validator MUST NOT fire
        (Stripe will reject on price_id, but URL validation is bypassed)
  T-13: Non-apostille no flow set (empty request) — validator MUST NOT fire
        (backend will reject with 400 about missing tier, not URL)
  T-14: Public ApostApp config + packages regression (still working in
        live mode after the URL hardening code is loaded)

The tests run against the live backend (port 8000) for full HTTP-level
integration coverage. The post-R1D-FIX-2 code is the same code that
served the live smoke payment (PID 508161 at the time of writing).
"""
import os
import re
import requests

# ⚠️  LIVE-TEST GUARD (2026-06-14) ⚠️
# This file calls /api/v1/payments/checkout on the LIVE backend (full
# Cloudflare edge → cloudflared tunnel → backend stack) and creates
# `cs_live_*` Checkout Sessions on the LIVE Stripe account. The tests
# are now SKIPPED unless APOSTILLE_LIVE_TEST_TOKEN is set explicitly.
# See backend/tests/helpers/live_test_guard.py and
# HERMES-REPORT-GATE3-PAYMENT-INCIDENT-CLEANUP-AND-TEST-GUARDS-20260614.md.
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from helpers.live_test_guard import require_live_test_token  # noqa: E402

require_live_test_token(__file__)

import pytest

# Live backend (port 8000, not 3005). 127.0.0.1 because we're running
# on the same host as the backend; also test the public tunnel route
# via apostapp.empirebox.store.
LOCAL = "http://127.0.0.1:8000"
PUBLIC = "https://apostapp.empirebox.store"

# Pick the route that goes through the narrow-allowlist yml to the
# live backend. Use the PUBLIC host because that exercises the full
# stack: Cloudflare edge -> cloudflared tunnel -> backend validator.
URL = PUBLIC + "/api/v1/payments/checkout"

# Use the smoke order ID from R1D as a real, on-disk apostille order.
# (The order was marked paid=true and refunded; the JSON still exists.)
# Validator does not check whether the order exists — that's a separate
# Stripe-level check — so this is safe to use as a synthetic order id.
APOSTILLE_ORDER_ID = "116c9e4d"


def _post(payload):
    """Helper: POST to the checkout endpoint, return (status, body_dict)."""
    r = requests.post(URL, json=payload, timeout=15)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text[:500]}


# ── T-01: valid public URLs accepted ──────────────────────────────────

def test_t01_valid_public_urls_accepted():
    """ApostApp checkout with valid public success/cancel URLs -> 200."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "https://apostapp.empirebox.store/apostille/confirmation?order_id=116c9e4d",
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 200, f"expected 200, got {status}: {body}"
    assert body.get("checkout_url", "").startswith("https://checkout.stripe.com/c/pay/"), \
        f"expected Stripe checkout URL, got {body.get('checkout_url')}"
    assert body.get("session_id", "").startswith("cs_live_"), \
        f"expected cs_live_ session, got {body.get('session_id')}"
    assert body.get("apostille_order_id") == APOSTILLE_ORDER_ID
    assert body.get("amount_cents") == 50
    assert body.get("flow") == "apostille_one_time"


# ── T-02 / T-03: missing success/cancel URL ──────────────────────────

def test_t02_missing_success_url_rejected():
    """ApostApp checkout missing success_url (uses default operator URL) -> 400.

    Pydantic uses the field default when the field is absent from the
    JSON payload. The default points to studio.empirebox.store, so the
    operator-hostname check fires.
    """
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        # success_url omitted — Pydantic falls back to the operator default
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "operator hostname" in detail, f"expected operator-hostname error, got: {detail}"
    assert "studio.empirebox.store" in detail, f"expected studio.empirebox.store in error, got: {detail}"


def test_t03_missing_cancel_url_rejected():
    """ApostApp checkout missing cancel_url -> 400, same reason."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "https://apostapp.empirebox.store/apostille/confirmation?order_id=116c9e4d",
        # cancel_url omitted — Pydantic falls back to the operator default
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "operator hostname" in detail, f"expected operator-hostname error, got: {detail}"


def test_t11_empty_success_url_rejected():
    """ApostApp checkout with success_url='' -> 400, empty-string check."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "",
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "non-empty" in detail or "operator hostname" in detail, \
        f"expected empty-or-operator error, got: {detail}"


# ── T-04: localhost ───────────────────────────────────────────────────

def test_t04_localhost_rejected():
    """ApostApp checkout with success_url=http://localhost:3005 -> 400.

    Could be caught by either the https check (http://) or the loopback
    check (localhost). Either is correct behavior.
    """
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "http://localhost:3005",
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert ("loopback" in detail) or ("https" in detail), \
        f"expected loopback or https error, got: {detail}"


# ── T-05: operator hostname (studio) ──────────────────────────────────

def test_t05_studio_operator_url_rejected():
    """ApostApp checkout with success_url=https://studio.empirebox.store/x -> 400."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "https://studio.empirebox.store/payments/success",
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "operator hostname" in detail, f"expected operator-hostname error, got: {detail}"
    assert "studio.empirebox.store" in detail, f"expected studio in error, got: {detail}"


# ── T-06: loopback (127.0.0.1) ────────────────────────────────────────

def test_t06_loopback_127_rejected():
    """ApostApp checkout with success_url=https://127.0.0.1:3005/x -> 400."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "https://127.0.0.1:3005/x",
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "loopback" in detail, f"expected loopback error, got: {detail}"
    assert "127.0.0.1" in detail, f"expected 127.0.0.1 in error, got: {detail}"


# ── T-07: non-https ───────────────────────────────────────────────────

def test_t07_non_https_rejected():
    """ApostApp checkout with success_url=http://apostapp.empirebox.store/x -> 400."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "http://apostapp.empirebox.store/x",
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "https" in detail, f"expected https error, got: {detail}"


# ── T-08: another operator hostname (api) ─────────────────────────────

def test_t08_api_operator_url_rejected():
    """ApostApp checkout with success_url=https://api.empirebox.store/x -> 400."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "https://api.empirebox.store/x",
        "cancel_url": "https://apostapp.empirebox.store/apostille",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "operator hostname" in detail, f"expected operator-hostname error, got: {detail}"
    assert "api.empirebox.store" in detail, f"expected api.empirebox.store in error, got: {detail}"


# ── T-09: another operator hostname (luxe) on cancel_url ──────────────

def test_t09_luxe_operator_cancel_url_rejected():
    """ApostApp checkout with cancel_url=https://luxe.empirebox.store/x -> 400."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "https://apostapp.empirebox.store/apostille/confirmation?order_id=116c9e4d",
        "cancel_url": "https://luxe.empirebox.store/x",
    }
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "operator hostname" in detail, f"expected operator-hostname error, got: {detail}"
    assert "luxe.empirebox.store" in detail, f"expected luxe.empirebox.store in error, got: {detail}"


# ── T-10: bare-host URL is valid ──────────────────────────────────────

def test_t10_bare_host_url_accepted():
    """ApostApp checkout with success_url=https://apostapp.empirebox.store (no path) -> 200.

    Stripe accepts the URL as long as it's a valid URL. The host alone
    is fine; Stripe will redirect to whatever the URL resolves to.
    """
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": APOSTILLE_ORDER_ID,
        "apostille_amount_cents": 50,
        "success_url": "https://apostapp.empirebox.store",
        "cancel_url": "https://apostapp.empirebox.store",
    }
    status, body = _post(payload)
    assert status == 200, f"expected 200, got {status}: {body}"
    assert body.get("session_id", "").startswith("cs_live_")


# ── T-12: SaaS flow not affected ──────────────────────────────────────

def test_t12_saas_flow_unaffected_by_validator():
    """SaaS flow (tier=pro) — validator MUST NOT fire.

    Even though the live STRIPE_PRICE_PRO is a test-mode price id and
    Stripe will reject, the rejection must come from Stripe (price id
    not found), not from our URL validator. The fact that we get a 400
    with 'No such price' (and not 'operator hostname') proves the
    validator was bypassed.
    """
    payload = {
        "tier": "pro",
        "customer_email": "test@example.com",
        # No URLs — uses operator defaults, which are fine for SaaS
    }
    status, body = _post(payload)
    # Expect 400 from Stripe (price id not found in live mode), NOT
    # 400 from our URL validator. The error message tells us which.
    detail = body.get("detail", "") if isinstance(body, dict) else str(body)
    assert "operator hostname" not in detail, \
        f"validator fired for SaaS flow (should be bypassed): {detail}"
    assert "success_url" not in detail or "price" in detail.lower(), \
        f"unexpected error shape (should be Stripe price error): {detail}"


# ── T-13: empty SaaS request not affected ─────────────────────────────

def test_t13_empty_request_not_affected():
    """No flow, no tier, no URLs — validator MUST NOT fire; backend
    rejects with 'Either tier (SaaS) or flow=apostille_one_time required'.
    """
    payload = {}  # completely empty
    status, body = _post(payload)
    assert status == 400, f"expected 400, got {status}: {body}"
    detail = body.get("detail", "")
    assert "operator hostname" not in detail, \
        f"validator fired for empty request: {detail}"
    assert "tier" in detail or "flow" in detail, \
        f"expected tier/flow error, got: {detail}"


# ── T-14: public ApostApp surface still working in live mode ─────────

def test_t14_public_config_still_live():
    """/api/v1/apostapp/public/config still returns test_mode:false."""
    r = requests.get(PUBLIC + "/api/v1/apostapp/public/config", timeout=10)
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body.get("test_mode") is False, f"expected test_mode=false, got {body}"


def test_t15_public_packages_still_live():
    """/api/v1/apostapp/public/packages still returns 3 packages at live prices."""
    r = requests.get(PUBLIC + "/api/v1/apostapp/public/packages", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body.get("test_mode") is False
    assert body.get("currency") == "usd"
    pkgs = {p["id"]: p for p in body.get("packages", [])}
    assert "basic_intake" in pkgs
    assert "standard" in pkgs
    assert "rush" in pkgs
    assert pkgs["basic_intake"]["price_cents"] == 3500
    assert pkgs["standard"]["price_cents"] == 9500
    assert pkgs["rush"]["price_cents"] == 19500


def test_t16_smoke_order_still_paid_and_refund_marked():
    """The R1D smoke order is still on disk, paid=true, payment fields populated.

    This is a regression check that the URL hardening didn't accidentally
    mutate the order store.
    """
    import json
    order_path = "/home/rg/empire-repo/backend/data/apostapp/orders/116c9e4d.json"
    with open(order_path) as f:
        d = json.load(f)
    assert d.get("paid") is True
    assert (d.get("payment_session_id") or "").startswith("cs_live_")
    assert d.get("payment_amount_cents") == 50
    assert d.get("customer_name") == "R1D Live Smoke Test"
    assert d.get("documents", [{}])[0].get("doc_type") == "smoke_test_only"
