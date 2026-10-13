"""
BusinessOps Phase 2 — self-serve signup, tenant isolation, Stripe TEST checkout.

Uses a tmp SQLite file (never the live empire.db). Stripe is mocked.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    from app.db import database
    import app.services.business.signup as signup_mod
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "biz_signup_test.db"))
    monkeypatch.setenv("BUSINESSOPS_PUBLIC_SIGNUP_ENABLED", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy_businessops")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_dummy")
    monkeypatch.setattr(signup_mod, "_hash_password", lambda password: "test-hash:" + password)
    from app.main import app
    return TestClient(app)


def _signup(client, *, email="owner@alpha.test", package_id="pkg_starter", name="Alpha Co", headers=None):
    return client.post(
        "/api/v1/businessops/signup",
        json={
            "email": email,
            "password": "password12",
            "display_name": "Ada Owner",
            "business_name": name,
            "package_id": package_id,
        },
        headers=headers or {},
    )


class _FakeSession:
    id = "cs_test_bizops"
    url = "https://checkout.stripe.com/c/pay/cs_test_bizops"


class _FakeStripe:
    last_params = None

    class checkout:
        class Session:
            @staticmethod
            def create(**kwargs):
                _FakeStripe.last_params = kwargs
                return _FakeSession()

    class Webhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            return json.loads(payload)


def test_public_signup_disabled_by_default(client, monkeypatch):
    """Anonymous POST must 404 and must not write a tenant when the flag is off."""
    monkeypatch.delenv("BUSINESSOPS_PUBLIC_SIGNUP_ENABLED", raising=False)
    r = _signup(client, email="locked@public.test", name="Should Not Land")
    assert r.status_code == 404
    assert r.json()["detail"] == "Not found"
    listed = client.get("/api/v1/businessops/businesses")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
    assert listed.json()["items"] == []


def test_public_signup_disabled_explicit_false(client, monkeypatch):
    monkeypatch.setenv("BUSINESSOPS_PUBLIC_SIGNUP_ENABLED", "false")
    r = _signup(client)
    assert r.status_code == 404


def test_wrong_founder_pin_is_404_when_public_disabled(client, monkeypatch):
    monkeypatch.setenv("BUSINESSOPS_PUBLIC_SIGNUP_ENABLED", "0")
    monkeypatch.setenv("FOUNDER_PIN", "correct-founder-pin")
    r = _signup(client, headers={"X-Founder-Pin": "wrong-pin"})
    assert r.status_code == 404
    listed = client.get("/api/v1/businessops/businesses")
    assert listed.json()["total"] == 0


def test_founder_can_signup_when_public_disabled(client, monkeypatch):
    monkeypatch.setenv("BUSINESSOPS_PUBLIC_SIGNUP_ENABLED", "false")
    monkeypatch.setenv("FOUNDER_PIN", "correct-founder-pin")
    r = _signup(
        client,
        email="founder-internal@tmp.test",
        name="Internal Prospect",
        headers={"X-Founder-Pin": "correct-founder-pin"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["business"]["display_name"] == "Internal Prospect"
    assert body["next_step"] == "checkout"


def test_info_reports_public_signup_flag(client, monkeypatch):
    monkeypatch.delenv("BUSINESSOPS_PUBLIC_SIGNUP_ENABLED", raising=False)
    off = client.get("/api/v1/businessops/info")
    assert off.status_code == 200
    assert off.json()["public_signup_enabled"] is False
    monkeypatch.setenv("BUSINESSOPS_PUBLIC_SIGNUP_ENABLED", "true")
    on = client.get("/api/v1/businessops/info")
    assert on.json()["public_signup_enabled"] is True


def test_signup_creates_business_tenant_and_pending_subscription(client):
    r = _signup(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["next_step"] == "checkout"
    assert body["business"]["status"] == "prospect"
    assert body["tenant"]["id"].startswith("ten_")
    assert body["subscription"]["status"] == "pending"
    assert body["subscription"]["package_id"] == "pkg_starter"
    assert body["user"]["role"] == "owner"
    assert body["access_token"]

    tenant_id = body["tenant"]["id"]
    biz_id = body["business"]["id"]
    scoped = client.get(f"/api/v1/businessops/businesses?tenant_id={tenant_id}")
    assert scoped.status_code == 200
    items = scoped.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == biz_id

    tenants = client.get("/api/v1/businessops/tenants")
    assert any(t["id"] == tenant_id for t in tenants.json()["items"])


@pytest.mark.parametrize("package_id", ["pkg_founder", "pkg_custom"])
def test_signup_refuses_unsold_packages(client, package_id):
    r = _signup(client, package_id=package_id)
    assert r.status_code == 400
    assert "not" in r.json()["detail"].lower() or "Founder" in r.json()["detail"] or "Custom" in r.json()["detail"]


def test_tenant_isolation_hides_other_business(client):
    a = _signup(client, email="a@alpha.test", name="Alpha LLC").json()
    b = _signup(client, email="b@beta.test", name="Beta LLC", package_id="pkg_growth").json()

    headers = {"X-Empire-Tenant-Id": a["tenant"]["id"]}
    leak = client.get(f"/api/v1/businessops/businesses/{b['business']['id']}", headers=headers)
    assert leak.status_code == 404

    own = client.get(f"/api/v1/businessops/businesses/{a['business']['id']}", headers=headers)
    assert own.status_code == 200
    assert own.json()["id"] == a["business"]["id"]

    scoped_subs = client.get("/api/v1/businessops/subscriptions", headers=headers)
    ids = {s["package_id"] for s in scoped_subs.json()["items"]}
    assert ids == {"pkg_starter"}


def test_checkout_rejects_live_stripe_key(client, monkeypatch):
    body = _signup(client).json()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_should_never_run")
    r = client.post(
        "/api/v1/businessops/checkout",
        json={"business_id": body["business"]["id"], "package_id": "pkg_starter"},
    )
    assert r.status_code == 403
    assert "TEST" in r.json()["detail"]


def test_checkout_creates_test_session(client, monkeypatch):
    from app.services.business import stripe_checkout as sc
    monkeypatch.setattr(sc, "_import_stripe", lambda secret: _FakeStripe)
    body = _signup(client, package_id="pkg_empire").json()
    r = client.post(
        "/api/v1/businessops/checkout",
        json={
            "business_id": body["business"]["id"],
            "package_id": "pkg_empire",
            "tenant_id": body["tenant"]["id"],
            "success_url": "https://studio.empirebox.store/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://studio.empirebox.store/pricing",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["test_mode"] is True
    assert data["checkout_url"].startswith("https://checkout.stripe.com/")
    assert data["package_id"] == "pkg_empire"
    params = _FakeStripe.last_params
    assert params["mode"] == "subscription"
    assert "payment_method_types" not in params
    assert params["client_reference_id"] == body["business"]["id"]
    assert params["metadata"]["package_id"] == "pkg_empire"


def test_checkout_refuses_founder_package(client, monkeypatch):
    from app.services.business import stripe_checkout as sc
    monkeypatch.setattr(sc, "_import_stripe", lambda secret: _FakeStripe)
    body = _signup(client).json()
    r = client.post(
        "/api/v1/businessops/checkout",
        json={"business_id": body["business"]["id"], "package_id": "pkg_founder"},
    )
    assert r.status_code == 400


def test_webhook_activates_subscription(client, monkeypatch):
    from app.services.business import stripe_checkout as sc
    monkeypatch.setattr(sc, "_import_stripe", lambda secret: _FakeStripe)
    body = _signup(client, package_id="pkg_apostille_only").json()
    event = {
        "id": "evt_test_activate_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_activate_1",
                "object": "checkout.session",
                "payment_status": "paid",
                "client_reference_id": body["business"]["id"],
                "customer": "cus_test_1",
                "subscription": "sub_test_1",
                "metadata": {
                    "flow": "businessops_subscription",
                    "business_id": body["business"]["id"],
                    "package_id": "pkg_apostille_only",
                    "subscription_id": body["subscription"]["id"],
                },
            }
        },
    }
    r = client.post(
        "/api/v1/businessops/stripe-webhook",
        data=json.dumps(event),
        headers={"stripe-signature": "sig_test", "content-type": "application/json"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"]["applied"] is True

    sub = client.get(f"/api/v1/businessops/subscriptions/{body['subscription']['id']}")
    assert sub.json()["status"] == "active"
    biz = client.get(f"/api/v1/businessops/businesses/{body['business']['id']}")
    assert biz.json()["status"] == "active"

    again = client.post(
        "/api/v1/businessops/stripe-webhook",
        data=json.dumps(event),
        headers={"stripe-signature": "sig_test", "content-type": "application/json"},
    )
    assert again.json()["duplicate"] is True


def test_webhook_without_signature_is_rejected(client, monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
    r = client.post(
        "/api/v1/businessops/stripe-webhook",
        json={"type": "checkout.session.completed", "data": {"object": {}}},
    )
    assert r.status_code == 503


def test_public_packages_hide_founder_when_filtered(client):
    r = client.get("/api/v1/businessops/packages?is_internal=false")
    ids = [p["id"] for p in r.json()["items"]]
    assert "pkg_founder" not in ids
    assert "pkg_starter" in ids
    assert "pkg_growth" in ids
    assert "pkg_empire" in ids
    assert "pkg_apostille_only" in ids


def test_tenant_slug_unique(client):
    first = _signup(client, email="one@co.test", name="Same Name").json()
    second = _signup(client, email="two@co.test", name="Same Name").json()
    assert first["business"]["slug"] != second["business"]["slug"]
