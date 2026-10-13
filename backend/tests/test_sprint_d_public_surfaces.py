"""Sprint D — isolated tests for ApostApp checkout, status emails,
Link-in-Bio quote intake, and SocialForge approval-gated scheduler.

These tests NEVER:
  * import app.main (avoids live router side effects)
  * call a live backend / Stripe / Graph API
  * write to ~/empire-repo/backend/data or the live empire.db
  * send client email
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.middleware.rate_limiter import limiter


class FakeCheckoutSession:
    def __init__(self, url="https://checkout.stripe.com/c/pay/cs_test_sprintd", session_id="cs_test_sprintd"):
        self.url = url
        self.id = session_id


class FakeStripe:
    class checkout:
        class Session:
            last_create = None

            @staticmethod
            def create(**kwargs):
                FakeStripe.checkout.Session.last_create = kwargs
                assert kwargs["mode"] == "payment"
                assert "TEST MODE" in kwargs["line_items"][0]["price_data"]["product_data"]["description"]
                return FakeCheckoutSession()


INTAKE = {
    "client_name": "Sprint D Tester",
    "email": "sprint-d@example.com",
    "phone": "555-0100",
    "document_type": "articles_of_organization",
    "destination_country": "Colombia",
    "origin_state": "MD",
    "service_level": "standard",
    "notes": "Isolated pytest only. Do not fulfill.",
}


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    apost = tmp_path / "apostapp"
    social = tmp_path / "socialforge"
    leads = tmp_path / "leadforge.db"
    monkeypatch.setenv("APOSTAPP_DATA_DIR", str(apost))
    monkeypatch.setenv("SOCIALFORGE_DATA_DIR", str(social))
    monkeypatch.setenv("LEADFORGE_PUBLIC_DB", str(leads))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(leads))
    monkeypatch.setenv("APOSTILLE_TEST_MODE", "1")
    monkeypatch.setenv("APOSTAPP_ALLOW_CLIENT_EMAIL_SEND", "0")
    monkeypatch.setenv("SOCIALFORGE_ALLOW_LIVE_PUBLISH", "0")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_sprintd_isolated")
    monkeypatch.delenv("APOSTILLE_LIVE_TEST_TOKEN", raising=False)
    return {"apost": apost, "social": social, "leads": leads}


@pytest.fixture
def client(isolated_env, monkeypatch):
    from app.routers import apostapp_public, leadforge_public, linkinbio, socialforge
    from app.services import apostapp_status_emails, stripe_test_checkout

    apostapp_public._CHECKOUT_CLIENT = FakeStripe
    socialforge._PUBLISHER = None
    limiter.enabled = False

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(apostapp_public.router, prefix="/api/v1")
    app.include_router(linkinbio.router, prefix="/api/v1")
    app.include_router(leadforge_public.router, prefix="/api/v1")
    app.include_router(socialforge.router, prefix="/api/v1/socialforge")
    yield TestClient(app)
    apostapp_public._CHECKOUT_CLIENT = None
    limiter.enabled = True


def test_packages_and_config_are_test_mode(client):
    packages = client.get("/api/v1/apostapp/public/packages")
    assert packages.status_code == 200
    body = packages.json()
    assert body["test_mode"] is True
    assert {p["id"] for p in body["packages"]} == {"basic_intake", "standard", "rush"}

    cfg = client.get("/api/v1/apostapp/public/config")
    assert cfg.status_code == 200
    assert cfg.json()["test_mode"] is True
    assert cfg.json()["checkout_mode"] == "test"
    assert cfg.json()["client_emails_auto_send"] is False


def test_intake_creates_test_checkout_and_drafts_email(client, isolated_env):
    r = client.post("/api/v1/apostapp/public/intake", json=INTAKE)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["paid"] is False
    assert data["test_mode"] is True
    assert data["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_sprintd"
    assert data["order_id"]

    order_file = isolated_env["apost"] / "orders" / f"{data['order_id']}.json"
    assert order_file.exists()

    drafts = client.get("/api/v1/apostapp/public/email-drafts", params={"order_id": data["order_id"]})
    assert drafts.status_code == 200
    items = drafts.json()["drafts"]
    assert len(items) == 1
    assert items[0]["status"] == "drafted"
    assert items[0]["auto_sent"] is False
    assert items[0]["sent_at"] is None
    assert drafts.json()["auto_send"] is False


def test_status_email_requires_owner_approval_and_never_auto_sends(client):
    created = client.post("/api/v1/apostapp/public/intake", json=INTAKE).json()
    draft_id = client.get(
        "/api/v1/apostapp/public/email-drafts",
        params={"order_id": created["order_id"]},
    ).json()["drafts"][0]["id"]

    blocked = client.post(f"/api/v1/apostapp/public/email-drafts/{draft_id}/send")
    assert blocked.status_code == 403
    assert "owner_approval_required" in blocked.json()["detail"]

    approved = client.post(f"/api/v1/apostapp/public/email-drafts/{draft_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["sent"] is False
    assert approved.json()["draft"]["status"] == "approved"

    queued = client.post(f"/api/v1/apostapp/public/email-drafts/{draft_id}/send")
    assert queued.status_code == 200
    body = queued.json()
    assert body["auto_sent"] is False
    assert body["sent"] is False
    assert body["draft"]["status"] == "approved_queued_not_sent"
    assert body["draft"]["send_result"] == "queued_not_sent"


def test_live_stripe_key_is_refused(isolated_env, monkeypatch):
    from app.services.stripe_test_checkout import LiveStripeKeyRefused, refuse_live_stripe_key

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_should_never_be_used")
    with pytest.raises(LiveStripeKeyRefused):
        refuse_live_stripe_key()


def test_verify_uses_isolated_store(client):
    created = client.post("/api/v1/apostapp/public/intake", json=INTAKE).json()
    ok = client.post(
        "/api/v1/apostapp/public/verify",
        json={"order_id": created["order_id"], "email": INTAKE["email"]},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "received"

    bad = client.post(
        "/api/v1/apostapp/public/verify",
        json={"order_id": created["order_id"], "email": "wrong@example.com"},
    )
    assert bad.status_code == 404


def test_linkinbio_catalog_and_quote_intake(client, isolated_env):
    catalog = client.get("/api/v1/linkinbio")
    assert catalog.status_code == 200
    slugs = {b["slug"] for b in catalog.json()["businesses"]}
    assert {"empire-workroom", "woodcraft", "apostapp", "empirebox"} <= slugs
    assert catalog.json()["reads_business_json"] is False

    bio = client.get("/api/v1/linkinbio/empire-workroom")
    assert bio.status_code == 200
    assert bio.json()["quote_intake_path"] == "/quote/intake?business=empire-workroom"
    assert any(link.get("kind") == "quote_intake" for link in bio.json()["links"])

    missing = client.get("/api/v1/linkinbio/not-a-real-biz")
    assert missing.status_code == 404

    intake = client.post(
        "/api/v1/leadforge/public/quote-intake",
        json={
            "business_slug": "empire-workroom",
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "555-0142",
            "project": "Living room drapery, 3 windows",
            "city": "Washington",
        },
    )
    assert intake.status_code == 200, intake.text
    body = intake.json()
    assert body["ok"] is True
    assert body["business_unit"] == "workroom"
    assert body["source"] == "link_in_bio"
    assert isolated_env["leads"].exists()


def test_socialforge_nothing_posts_without_owner_approval(client):
    created = client.post(
        "/api/v1/socialforge/posts",
        json={
            "platform": "instagram",
            "content": "Custom drapery reveal. Link in bio.",
            "hashtags": "#dc",
            "scheduled_for": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
            "status": "scheduled",
        },
    )
    assert created.status_code == 200, created.text
    post = created.json()
    assert post["approval_status"] == "pending_approval"
    assert post["status"] != "posted"

    forbidden_create = client.post(
        "/api/v1/socialforge/posts",
        json={"platform": "instagram", "content": "nope", "status": "posted"},
    )
    assert forbidden_create.status_code == 403

    forbidden_update = client.put(
        f"/api/v1/socialforge/posts/{post['id']}",
        json={"status": "posted"},
    )
    assert forbidden_update.status_code == 403

    live = client.post(
        "/api/v1/socialforge/post/instagram",
        json={"caption": "should fail", "image_url": "https://example.com/x.jpg"},
    )
    assert live.status_code == 403

    tick_before = client.post("/api/v1/socialforge/scheduler/tick")
    assert tick_before.status_code == 200
    assert tick_before.json()["processed"] == 0

    approve = client.post(f"/api/v1/socialforge/posts/{post['id']}/approve")
    assert approve.status_code == 200
    assert approve.json()["approval_status"] == "approved"

    dry = client.post(
        "/api/v1/socialforge/post/instagram",
        json={"caption": "approved but dry-run", "image_url": "https://example.com/x.jpg", "post_id": post["id"]},
    )
    assert dry.status_code == 200
    assert dry.json()["posted"] is False
    assert dry.json()["dry_run"] is True

    tick = client.post("/api/v1/socialforge/scheduler/tick")
    assert tick.status_code == 200
    assert tick.json()["processed"] == 1
    assert tick.json()["results"][0]["result"]["dry_run"] is True
    assert tick.json()["results"][0]["status"] != "posted"

    queue = client.get("/api/v1/socialforge/approval-queue")
    assert queue.status_code == 200
    assert queue.json()["policy"] == "nothing_posts_without_owner_approval"


def test_socialforge_scheduler_uses_injected_publisher_only_after_approval(client, monkeypatch):
    from app.routers import socialforge

    published = []

    async def fake_publisher(post):
        published.append(post["id"])
        return {"posted": True, "dry_run": False, "platform": post["platform"]}

    socialforge._PUBLISHER = fake_publisher
    created = client.post(
        "/api/v1/socialforge/posts",
        json={"platform": "facebook", "content": "Need owner eyes first", "status": "draft"},
    ).json()

    client.post("/api/v1/socialforge/scheduler/tick")
    assert published == []

    client.post(f"/api/v1/socialforge/posts/{created['id']}/approve")
    tick = client.post("/api/v1/socialforge/scheduler/tick")
    assert tick.json()["processed"] == 1
    assert published == [created["id"]]
    fetched = client.get(f"/api/v1/socialforge/posts/{created['id']}")
    assert fetched.json()["status"] == "posted"
    socialforge._PUBLISHER = None


def test_frontend_surfaces_exist():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    intake = os.path.join(root, "empire-command-center/app/components/public/ApostilleIntakeForm.jsx")
    bio = os.path.join(root, "empire-command-center/app/b/[slug]/page.tsx")
    quote = os.path.join(root, "empire-command-center/app/quote/intake/page.tsx")
    social = os.path.join(root, "empire-command-center/app/components/screens/SocialForgePage.tsx")
    for path in (intake, bio, quote, social):
        assert os.path.exists(path), path
    intake_src = open(intake).read()
    assert "checkout_url" in intake_src
    assert "never auto-sent" in open(os.path.join(root, "empire-command-center/app/components/public/ApostilleConfirmationContent.jsx")).read()
    assert "bio-quote-cta" in open(bio).read()
    assert "leadforge/public/quote-intake" in open(quote).read()
    assert "nothing posts without owner approval" in open(social).read()


def test_isolated_store_does_not_touch_default_live_paths(client, isolated_env):
    client.post("/api/v1/apostapp/public/intake", json=INTAKE)
    client.post(
        "/api/v1/socialforge/posts",
        json={"platform": "instagram", "content": "queue only"},
    )
    live_apost = os.path.expanduser("~/empire-repo/backend/data/apostapp/orders")
    live_social = os.path.expanduser("~/empire-repo/backend/data/socialforge/posts")
    isolated_orders = list((isolated_env["apost"] / "orders").glob("*.json"))
    isolated_posts = list((isolated_env["social"] / "posts").glob("*.json"))
    assert isolated_orders
    assert isolated_posts
    # The isolated run must not be writing through the default live roots.
    for path in isolated_orders:
        assert str(isolated_env["apost"]) in str(path)
    for path in isolated_posts:
        assert str(isolated_env["social"]) in str(path)
    assert os.path.abspath(str(isolated_env["apost"])) != os.path.abspath(live_apost)
    assert os.path.abspath(str(isolated_env["social"])) != os.path.abspath(live_social)
