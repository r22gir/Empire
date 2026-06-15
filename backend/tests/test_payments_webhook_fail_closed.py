"""
R1D-FIX — Stripe webhook fail-closed hardening tests.

These tests verify the post-R1D-FIX behavior of /api/v1/payments/webhook:

  T-01: Webhook with NO stripe-signature header AND valid JSON event body
        (an unsigned forgery) is REJECTED (4xx or 5xx).
  T-02: Webhook with garbage stripe-signature header is REJECTED.
  T-03: Webhook with valid-looking but wrong-signature header is REJECTED.
  T-04: Webhook with stripe-signature + valid payload is NOT accepted unless
        the signature is correct (the existing STRIPE_WEBHOOK_SECRET in .env
        is the test-mode secret, so we cannot easily forge a valid one from
        outside; this test verifies that 'looks plausible' is not enough).
  T-05: ApostApp order is NOT marked paid=true after a forged unsigned webhook.
  T-06: Stripe checkout creation in apostille_one_time mode still works
        (regression — R1B flow not broken by R1D-FIX code change).
  T-07: Config endpoint still reports test_mode=true (regression).
  T-08: Packages endpoint still returns 3 packages (regression).

Tests run against the LIVE backend at http://127.0.0.1:8000 — the same
convention as test_apostille_public.py. They do NOT require Stripe to be
in live mode. They DO require the backend to be running the R1D-FIX code
(which calls _require_webhook_secret() at the top of the webhook handler).

R1D-FIX behavior under test:
  * If STRIPE_WEBHOOK_SECRET is missing/empty → 503 fail-closed.
  * If STRIPE_WEBHOOK_SECRET is set (which is the case in dev .env) → 400
    on bad signature, 200 on valid signature.
  * In NO case does the webhook route fall back to parsing unsigned JSON.

Run with:
    /home/rg/empire-repo/backend/venv/bin/pytest tests/test_payments_webhook_fail_closed.py -v

⚠️  LIVE-TEST GUARD (2026-06-14) ⚠️
This file calls /api/v1/payments/webhook on the LIVE backend. While
the webhook handler is fail-closed (unsigned webhooks are rejected),
the tests POST forged webhook bodies to verify the rejection works.
These tests are now SKIPPED unless APOSTILLE_LIVE_TEST_TOKEN is set
explicitly. See backend/tests/helpers/live_test_guard.py and
HERMES-REPORT-GATE3-PAYMENT-INCIDENT-CLEANUP-AND-TEST-GUARDS-20260614.md.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from helpers.live_test_guard import require_live_test_token  # noqa: E402

require_live_test_token(__file__)

import json
import os
import time
import uuid
from pathlib import Path

import pytest
import requests

BASE = "http://127.0.0.1:8000/api/v1"
ORDERS_DIR = Path(os.path.expanduser("~/empire-repo/backend/data/apostapp/orders"))


# ── Helpers ──────────────────────────────────────────────────────────

def _forged_apostille_event(order_id: str, amount_cents: int = 9500) -> dict:
    """Construct a plausible-looking but UNSIGNED Stripe checkout.session.completed
    event for an apostille_one_time flow. This is the exact shape a malicious
    actor would send to /api/v1/payments/webhook to try to flip an order to paid."""
    return {
        "id": "evt_test_FORGED_" + uuid.uuid4().hex[:16],
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_FORGED_" + uuid.uuid4().hex[:16],
                "object": "checkout.session",
                "amount_total": amount_cents,
                "metadata": {
                    "apostille_order_id": order_id,
                    "apostille_package_id": "standard",
                    "flow": "apostille_one_time",
                },
            }
        },
    }


def _create_apostille_order_via_intake() -> str:
    """Create a real apostille order via the public intake endpoint so we have
    a real order_id to try to forge a 'paid' flag on."""
    payload = {
        "client_name": "R1DFIX Test",
        "email": f"r1dfix-{uuid.uuid4().hex[:8]}@example.com",
        "phone": "555-0199",
        "document_type": "articles_of_organization",
        "destination_country": "Colombia",
        "origin_state": "MD",
        "service_level": "standard",
        "notes": "R1D-FIX test only. Do not fulfill.",
    }
    r = requests.post(f"{BASE}/apostapp/public/intake", json=payload, timeout=10)
    assert r.status_code == 200, f"intake failed: {r.status_code} {r.text}"
    return r.json()["order_id"]


# ── T-01: Unsigned JSON webhook is REJECTED ──────────────────────────

def test_t01_unsigned_webhook_rejected():
    """A forged checkout.session.completed event with NO stripe-signature
    header must be REJECTED, not silently parsed and applied.

    Before R1D-FIX: if STRIPE_WEBHOOK_SECRET was set, the code went into
    stripe.Webhook.construct_event and would 400 on missing signature — so
    this case was actually rejected. This test pins the behavior so it
    can't regress to the unsigned-parse fallback."""
    order_id = _create_apostille_order_via_intake()
    forged = _forged_apostille_event(order_id)
    r = requests.post(
        f"{BASE}/payments/webhook",
        json=forged,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    # Expect 400 (invalid signature from construct_event) — NOT 200 ok.
    assert r.status_code == 400, (
        f"Unsigned webhook was accepted: status={r.status_code} body={r.text}. "
        f"This means the fail-closed fix is broken — an attacker could forge paid=true."
    )
    # And the order must NOT be marked paid.
    order_path = ORDERS_DIR / f"{order_id}.json"
    assert order_path.exists(), f"order file missing: {order_path}"
    order = json.loads(order_path.read_text())
    assert order.get("paid") is False, (
        f"Order {order_id} was marked paid=true after a forged unsigned webhook. "
        f"This is the exact bug R1D-FIX is supposed to prevent."
    )


# ── T-02: Garbage stripe-signature header is REJECTED ────────────────

def test_t02_garbage_signature_rejected():
    order_id = _create_apostille_order_via_intake()
    forged = _forged_apostille_event(order_id)
    r = requests.post(
        f"{BASE}/payments/webhook",
        json=forged,
        headers={
            "Content-Type": "application/json",
            "stripe-signature": "this_is_garbage_not_a_real_signature",
        },
        timeout=10,
    )
    assert r.status_code == 400, (
        f"Garbage-signature webhook was accepted: status={r.status_code} body={r.text}"
    )
    order_path = ORDERS_DIR / f"{order_id}.json"
    order = json.loads(order_path.read_text())
    assert order.get("paid") is False, f"Order {order_id} was paid=true after garbage-signature webhook"


# ── T-03: Wrong-but-plausible signature is REJECTED ──────────────────

def test_t03_wrong_signature_rejected():
    order_id = _create_apostille_order_via_intake()
    forged = _forged_apostille_event(order_id)
    # A signature that *looks* like a real Stripe v1 signature but is computed
    # with the wrong secret. Stripe's signature format is
    # "t=<timestamp>,v1=<sha256-hmac>" — we send a sha256 with a wrong key.
    wrong_sig = "t=1700000000,v1=" + "f" * 64  # 64 hex chars, wrong key
    r = requests.post(
        f"{BASE}/payments/webhook",
        json=forged,
        headers={
            "Content-Type": "application/json",
            "stripe-signature": wrong_sig,
        },
        timeout=10,
    )
    assert r.status_code == 400, (
        f"Wrong-signature webhook was accepted: status={r.status_code} body={r.text}"
    )
    order_path = ORDERS_DIR / f"{order_id}.json"
    order = json.loads(order_path.read_text())
    assert order.get("paid") is False, f"Order {order_id} was paid=true after wrong-signature webhook"


# ── T-04: HMAC of correct body with wrong key is REJECTED ────────────

def test_t04_hmac_with_wrong_key_rejected():
    """Forge a real-looking HMAC signature using a wrong secret key. This
    is what an attacker who guessed the algorithm (but not the key) would try."""
    import hmac
    import hashlib

    order_id = _create_apostille_order_via_intake()
    payload_dict = _forged_apostille_event(order_id)
    payload_bytes = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    timestamp = "1700000000"
    # Stripe signs "timestamp.payload" with the secret
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    wrong_key = b"whsec_attacker_does_not_know_the_real_secret"
    sig = hmac.new(wrong_key, signed_payload, hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={sig}"

    r = requests.post(
        f"{BASE}/payments/webhook",
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "stripe-signature": sig_header,
        },
        timeout=10,
    )
    assert r.status_code == 400, (
        f"HMAC-with-wrong-key webhook was accepted: status={r.status_code} body={r.text}"
    )
    order_path = ORDERS_DIR / f"{order_id}.json"
    order = json.loads(order_path.read_text())
    assert order.get("paid") is False, f"Order {order_id} was paid=true after wrong-key HMAC webhook"


# ── T-05: Webhook with valid STRIPE_WEBHOOK_SECRET is accepted ───────

def test_t05_valid_signed_webhook_accepted():
    """Sign a webhook payload with the REAL test-mode STRIPE_WEBHOOK_SECRET
    and verify it IS accepted (200). This is the positive control: proves
    the signature-verification path still works after R1D-FIX."""
    import hmac
    import hashlib

    # Read the test-mode webhook secret from .env. (No secret value is printed.)
    env_path = Path("/home/rg/empire-repo/backend/.env")
    if not env_path.exists():
        pytest.skip("backend .env not present; cannot compute real signed webhook")
    secret = None
    for line in env_path.read_text().splitlines():
        if line.startswith("STRIPE_WEBHOOK_SECRET="):
            secret = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
    if not secret:
        pytest.skip("STRIPE_WEBHOOK_SECRET not in .env")
    if secret == "" or secret == "0" or secret.lower() == "false":
        # If the secret is missing/empty, this is the fail-closed case
        # (covered by other tests). Skip the positive control.
        pytest.skip("STRIPE_WEBHOOK_SECRET is empty — fail-closed path active, no positive control possible")

    order_id = _create_apostille_order_via_intake()
    payload_dict = _forged_apostille_event(order_id)
    payload_bytes = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={sig}"

    r = requests.post(
        f"{BASE}/payments/webhook",
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "stripe-signature": sig_header,
        },
        timeout=10,
    )
    # Stripe SDK behavior: returns 200 on success
    assert r.status_code == 200, (
        f"Valid signed webhook was rejected: status={r.status_code} body={r.text}. "
        f"This means R1D-FIX broke the signature-verification path."
    )
    # And the order should be marked paid.
    order_path = ORDERS_DIR / f"{order_id}.json"
    order = json.loads(order_path.read_text())
    assert order.get("paid") is True, f"Order {order_id} should be paid after valid signed webhook"


# ── T-06: Regression — checkout still works ──────────────────────────

def test_t06_apostille_checkout_still_works():
    """R1D-FIX must not break the R1B apostille_one_time checkout flow."""
    payload = {
        "flow": "apostille_one_time",
        "apostille_order_id": "r1dfix-regression-" + uuid.uuid4().hex[:8],
        "apostille_package_id": "standard",
        "apostille_amount_cents": 50,  # smallest sensible amount; test mode
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
    }
    r = requests.post(f"{BASE}/payments/checkout", json=payload, timeout=15)
    assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("checkout_url", "").startswith("https://checkout.stripe.com/"), (
        f"unexpected checkout_url: {data.get('checkout_url')}"
    )
    assert data.get("session_id", "").startswith("cs_test_"), (
        f"expected test-mode session_id, got: {data.get('session_id')}"
    )
    assert data.get("flow") == "apostille_one_time"
    assert data.get("amount_cents") == 50


# ── T-07: Regression — config still says test_mode ──────────────────

def test_t07_config_test_mode():
    r = requests.get(f"{BASE}/apostapp/public/config", timeout=5)
    assert r.status_code == 200
    assert r.json() == {"test_mode": True}, (
        f"config endpoint changed: {r.json()} (R1D-FIX should not have touched this)"
    )


# ── T-08: Regression — packages endpoint still works ────────────────

def test_t08_packages_endpoint():
    r = requests.get(f"{BASE}/apostapp/public/packages", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d.get("test_mode") is True
    assert d.get("currency") == "usd"
    assert len(d.get("packages", [])) == 3
    pkg_ids = {p["id"] for p in d["packages"]}
    assert pkg_ids == {"basic_intake", "standard", "rush"}
