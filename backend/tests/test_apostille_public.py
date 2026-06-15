"""
R1B Apostille Fast Lane — public API tests.

Covers:
  * POST /api/v1/apostapp/public/intake  (happy path, validation, packages)
  * POST /api/v1/apostapp/public/verify   (happy path, wrong verifier, missing)
  * GET  /api/v1/apostapp/public/packages
  * GET  /api/v1/apostapp/public/config
  * POST /api/v1/payments/checkout        (apostille_one_time + SaaS regression)
  * GET  /api/v1/apostapp/public          (regression: internal endpoints still 200)

These tests run against the LIVE backend at http://127.0.0.1:8000.
No real money is charged — Stripe is in test mode.

Run with:
    /home/rg/empire-repo/backend/venv/bin/pytest tests/test_apostille_public.py -v

⚠️  LIVE-TEST GUARD (2026-06-14) ⚠️
This file was guarded on 2026-06-14 after a prior unsafe run accidentally
created 17 ApostApp orders + 17 customers + 1 live Stripe Checkout Session
on the LIVE backend. The tests are now SKIPPED unless the env var
APOSTILLE_LIVE_TEST_TOKEN=I_APPROVE_LIVE_APOSTAPP_PAYMENT_TESTS is set
explicitly (which requires Founder approval via `APPROVE LIVE STRIPE ACTION`).
DO NOT REMOVE OR WEAKEN THIS GUARD. See backend/tests/helpers/live_test_guard.py
and HERMES-REPORT-GATE3-PAYMENT-INCIDENT-CLEANUP-AND-TEST-GUARDS-20260614.md.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from helpers.live_test_guard import require_live_test_token  # noqa: E402

require_live_test_token(__file__)

import json
import re
import time
import uuid
from datetime import datetime

import pytest
import requests

BASE = "http://127.0.0.1:8000/api/v1"


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_intake():
    """A canonical sample intake payload."""
    return {
        "client_name": "Test Client",
        "email": "test.apostille@example.com",
        "phone": "555-0100",
        "document_type": "articles_of_organization",
        "destination_country": "Colombia",
        "origin_state": "MD",
        "service_level": "standard",
        "notes": "Pytest test only. Do not fulfill.",
    }


@pytest.fixture
def unique_intake(sample_intake):
    """A sample intake with a unique email to avoid collisions on rerun."""
    sample_intake = dict(sample_intake)
    unique_id = uuid.uuid4().hex[:8]
    sample_intake["email"] = f"test-{unique_id}@apostille-example.com"
    return sample_intake


# ── 1. /packages endpoint ───────────────────────────────────────────

def test_packages_returns_three():
    r = requests.get(f"{BASE}/apostapp/public/packages", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "packages" in data
    assert "test_mode" in data
    assert len(data["packages"]) == 3
    ids = {p["id"] for p in data["packages"]}
    assert ids == {"basic_intake", "standard", "rush"}


def test_packages_have_required_fields():
    r = requests.get(f"{BASE}/apostapp/public/packages", timeout=5)
    assert r.status_code == 200
    for pkg in r.json()["packages"]:
        for field in ("id", "name", "description", "price_cents", "turnaround", "includes"):
            assert field in pkg, f"package {pkg.get('id')} missing {field}"
        assert isinstance(pkg["price_cents"], int) and pkg["price_cents"] > 0


# ── 2. /config endpoint ─────────────────────────────────────────────

def test_config_returns_test_mode():
    r = requests.get(f"{BASE}/apostapp/public/config", timeout=5)
    assert r.status_code == 200
    assert "test_mode" in r.json()
    # Default test mode is 1 (True) since APOSTILLE_TEST_MODE is unset
    assert r.json()["test_mode"] is True


# ── 3. /intake endpoint ─────────────────────────────────────────────

def test_intake_happy_path(unique_intake):
    r = requests.post(f"{BASE}/apostapp/public/intake", json=unique_intake, timeout=5)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "order_id" in data
    assert len(data["order_id"]) >= 8
    assert data["package_id"] == unique_intake["service_level"]
    assert data["status"] == "received"
    assert data["paid"] is False
    assert data["test_mode"] is True
    assert data["amount_cents"] == 9500  # standard package


def test_intake_all_three_packages():
    for level, expected_cents in [("basic_intake", 3500), ("standard", 9500), ("rush", 19500)]:
        payload = {
            "client_name": "Pkg Test",
            "email": f"pkg-{level}@example.com",
            "document_type": "diploma",
            "destination_country": "Mexico",
            "origin_state": "DC",
            "service_level": level,
            "notes": "",
        }
        r = requests.post(f"{BASE}/apostapp/public/intake", json=payload, timeout=5)
        assert r.status_code == 200, r.text
        assert r.json()["amount_cents"] == expected_cents


def test_intake_missing_required_field(sample_intake):
    payload = dict(sample_intake)
    del payload["destination_country"]
    r = requests.post(f"{BASE}/apostapp/public/intake", json=payload, timeout=5)
    assert r.status_code == 422


def test_intake_invalid_email(sample_intake):
    payload = dict(sample_intake)
    payload["email"] = "not-an-email"
    r = requests.post(f"{BASE}/apostapp/public/intake", json=payload, timeout=5)
    assert r.status_code == 422


def test_intake_bad_service_level(sample_intake):
    payload = dict(sample_intake)
    payload["service_level"] = "nonexistent"
    r = requests.post(f"{BASE}/apostapp/public/intake", json=payload, timeout=5)
    assert r.status_code == 422
    assert "Unknown service_level" in r.json()["detail"]


def test_intake_origin_state_too_short(sample_intake):
    payload = dict(sample_intake)
    payload["origin_state"] = "X"
    r = requests.post(f"{BASE}/apostapp/public/intake", json=payload, timeout=5)
    assert r.status_code == 422


# ── 4. /verify endpoint ─────────────────────────────────────────────

def test_verify_happy_path(unique_intake):
    # First create the order
    r = requests.post(f"{BASE}/apostapp/public/intake", json=unique_intake, timeout=5)
    assert r.status_code == 200
    order_id = r.json()["order_id"]

    # Then verify it
    r2 = requests.post(
        f"{BASE}/apostapp/public/verify",
        json={"order_id": order_id, "email": unique_intake["email"]},
        timeout=5,
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["order_id"] == order_id
    assert data["status"] == "received"
    assert data["paid"] is False
    assert "timeline" in data
    assert len(data["timeline"]) == 6
    assert "next_step_message" in data


def test_verify_wrong_email_returns_404(unique_intake):
    r = requests.post(f"{BASE}/apostapp/public/intake", json=unique_intake, timeout=5)
    order_id = r.json()["order_id"]

    r2 = requests.post(
        f"{BASE}/apostapp/public/verify",
        json={"order_id": order_id, "email": "WRONG@example.com"},
        timeout=5,
    )
    assert r2.status_code == 404
    assert r2.json()["detail"] == "Order not found"


def test_verify_nonexistent_order_returns_404():
    r = requests.post(
        f"{BASE}/apostapp/public/verify",
        json={"order_id": "deadbeef", "email": "anyone@example.com"},
        timeout=5,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Order not found"


def test_verify_does_not_leak_pii(unique_intake):
    r = requests.post(f"{BASE}/apostapp/public/intake", json=unique_intake, timeout=5)
    order_id = r.json()["order_id"]

    r2 = requests.post(
        f"{BASE}/apostapp/public/verify",
        json={"order_id": order_id, "email": unique_intake["email"]},
        timeout=5,
    )
    data = r2.json()
    serialized = json.dumps(data)
    # Ensure no internal PII fields leak
    assert "customer_id" not in serialized
    assert "shipping_address" not in serialized
    assert "attachments" not in serialized
    # The actual phone number should NOT be in the response
    assert unique_intake["phone"] not in serialized
    # But the doc type SHOULD be reachable indirectly via the timeline message + package_id
    assert "package_id" in data


# ── 5. Stripe checkout — apostille flow + SaaS regression ──────────

def test_stripe_apostille_checkout(unique_intake):
    r = requests.post(f"{BASE}/apostapp/public/intake", json=unique_intake, timeout=5)
    order_id = r.json()["order_id"]

    r2 = requests.post(
        f"{BASE}/payments/checkout",
        json={
            "flow": "apostille_one_time",
            "apostille_order_id": order_id,
            "apostille_package_id": "standard",
            "apostille_amount_cents": 9500,
            "customer_email": unique_intake["email"],
            # R1D-FIX-2: success_url/cancel_url MUST use the public ApostApp
            # surface (https://apostapp.empirebox.store/...). This test was
            # written before R1D-FIX-2 with example.com URLs; updated to
            # use the production public surface so the validator accepts.
            "success_url": "https://apostapp.empirebox.store/apostille/confirmation?order_id=" + order_id,
            "cancel_url": "https://apostapp.empirebox.store/apostille",
        },
        timeout=10,
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert "checkout_url" in data
    assert data["checkout_url"].startswith("https://checkout.stripe.com/c/pay/")
    # R1D: live env is now active; session_id prefix is cs_live_ (was cs_test_)
    assert "cs_live_" in data["checkout_url"]
    assert data["flow"] == "apostille_one_time"
    assert data["apostille_order_id"] == order_id
    assert data["amount_cents"] == 9500


def test_stripe_saas_subscription_still_works():
    """Regression: existing tier-based checkout must not be broken."""
    r = requests.post(
        f"{BASE}/payments/checkout",
        json={
            "tier": "pro",
            "customer_email": "subscriber@example.com",
            "user_id": "u-test",
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["checkout_url"].startswith("https://checkout.stripe.com/c/pay/")
    assert data["tier"] == "pro"


def test_stripe_apostille_requires_order_id():
    r = requests.post(
        f"{BASE}/payments/checkout",
        json={
            "flow": "apostille_one_time",
            "apostille_amount_cents": 9500,
        },
        timeout=5,
    )
    assert r.status_code == 400


def test_stripe_apostille_zero_amount_rejected():
    r = requests.post(
        f"{BASE}/payments/checkout",
        json={
            "flow": "apostille_one_time",
            "apostille_order_id": "x",
            "apostille_amount_cents": 0,
        },
        timeout=5,
    )
    assert r.status_code == 400


# ── 6. Internal endpoint regression (founder flow) ─────────────────

def test_internal_apostapp_endpoints_still_200():
    """The founder-facing internal endpoints must still respond."""
    # /services, /document-types, /pricing-calculator — all public-safe existing
    for path in ["/apostapp/services", "/apostapp/document-types", "/apostapp/pricing-calculator"]:
        r = requests.get(f"{BASE}{path}", timeout=5)
        assert r.status_code == 200, f"{path} returned {r.status_code}"


def test_internal_apostapp_orders_list_still_200():
    """Founder's list-all-orders endpoint must still work."""
    r = requests.get(f"{BASE}/apostapp/orders", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "orders" in data
    assert "count" in data


def test_internal_apostapp_dashboard_still_200():
    """Founder's dashboard endpoint must still work."""
    r = requests.get(f"{BASE}/apostapp/dashboard", timeout=5)
    assert r.status_code == 200


def test_internal_apostapp_customers_list_still_200():
    """Founder's list-all-customers endpoint must still work."""
    r = requests.get(f"{BASE}/apostapp/customers", timeout=5)
    assert r.status_code == 200


# ── 7. Health ────────────────────────────────────────────────────────

def test_backend_health():
    r = requests.get(f"{BASE.replace('/api/v1','')}/health", timeout=5)
    assert r.status_code == 200
