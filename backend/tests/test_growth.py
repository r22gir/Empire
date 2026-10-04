"""Growth layer: deposit->won, approval queue, ROI, social proof, Place Details cap, improvements loop.

Isolated temp DB (EMPIRE_TASK_DB); no network (Google calls go through httpx.MockTransport,
email send is monkeypatched). Nothing is sent anywhere.
"""
import asyncio
import importlib
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def g(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("MAX_IMPROVE_SPEC_DIR", str(tmp_path / "specs"))
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    from app.db import database, init_db
    importlib.reload(database); importlib.reload(init_db); init_db.init_database()
    from app.services.leadforge import prospect_engine, prospect_ops, acquisition, campaign_service, growth, place_details
    from app.services.max import improvements
    from app.routers import socialforge, leadforge, growth as growth_router
    for m in (prospect_engine, campaign_service, prospect_ops, acquisition, growth, place_details, improvements,
              socialforge, leadforge, growth_router):
        importlib.reload(m)
    monkeypatch.setattr(socialforge, "POSTS_DIR", str(tmp_path / "posts"))
    (tmp_path / "posts").mkdir()
    # LeadForge + campaign tables
    with prospect_engine._db() as conn:
        conn.execute("""INSERT INTO prospects (id, name, source, external_id, score, client_type, city)
                        VALUES (1, 'Design Pro Remodeling', 'google_places', 'PLACE1', 88, 'contractor', 'Fairfax')""")
        conn.execute("""INSERT INTO prospects (id, name, source, external_id, score, client_type, city)
                        VALUES (2, 'Elegant Kitchen', 'google_places', 'PLACE2', 86, 'contractor', 'Herndon')""")
    with growth._db() as conn:  # minimal tables the temp DB does not create on its own
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS quotes_v2 (id TEXT PRIMARY KEY, quote_number TEXT, customer_id TEXT, customer_name TEXT,
            customer_email TEXT, customer_phone TEXT, status TEXT, total REAL, photos_json TEXT, is_test INTEGER DEFAULT 0,
            sent_at TEXT, accepted_at TEXT, created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS payments_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_number TEXT, invoice_id TEXT,
            customer_id TEXT, amount REAL, payment_method TEXT, payment_reference TEXT, payment_type TEXT, status TEXT,
            account_code TEXT, notes TEXT, business_unit TEXT, stripe_session_id TEXT, payment_date TEXT,
            created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS job_documents (id TEXT PRIMARY KEY, job_id TEXT, quote_id TEXT, document_type TEXT,
            item_key TEXT, route_to TEXT, url TEXT, filename TEXT, revision INTEGER, visible_to_client INTEGER,
            source_channel TEXT, created_at TEXT);
        """)
        have = {r[1] for r in conn.execute("PRAGMA table_info(invoices)")}
        for col in ("quote_id", "client_email", "client_phone", "amount_paid", "balance_due", "payment_status", "paid_at",
                    "subtotal", "tax_rate", "total", "business_unit", "updated_at", "invoice_number", "customer_id", "status"):
            if col not in have:
                conn.execute(f"ALTER TABLE invoices ADD COLUMN {col} TEXT")
        jh = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
        for col in ("client_name", "room", "description", "client_address", "production_start", "install_date",
                    "completed_date", "pipeline_stage", "quote_id", "photos", "customer_id"):
            if col not in jh:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
    app = FastAPI(); app.include_router(growth_router.router, prefix="/api/v1"); app.include_router(leadforge.router, prefix="/api/v1")
    return dict(client=TestClient(app), growth=growth, pd=place_details, imp=improvements, sf=socialforge,
                po=prospect_ops, cs=campaign_service, tmp=tmp_path)


def _exec(sql, args=()):
    from app.services.leadforge import growth
    with growth._db() as conn:
        cur = conn.execute(sql, args)
        return cur.lastrowid


def _one(sql, args=()):
    from app.services.leadforge import growth
    with growth._db() as conn:
        r = conn.execute(sql, args).fetchone()
        return dict(r) if r else None


# ── 1. deposit paid -> lead won ─────────────────────────────────────────────
def test_deposit_paid_marks_lead_and_pipeline_won(g):
    _exec("INSERT INTO prospect_pipeline (prospect_id, status) VALUES (1, 'new')")
    lead = _exec("""INSERT INTO lf_leads (business_unit, company, email, phone, status, source, prospect_id, created_at)
                    VALUES ('workroom', 'Design Pro Remodeling', 'Owner@DesignPro.test', '(703) 555-2211', 'proposal_sent',
                            'prospecting', 1, datetime('now'))""")
    _exec("""INSERT INTO quotes_v2 (id, quote_number, customer_email, status, total, created_at)
             VALUES ('q1', 'EST-1', 'owner@designpro.test', 'sent', 4200, datetime('now'))""")
    _exec("""INSERT INTO invoices (id, customer_id, invoice_number, quote_id, client_email, total, amount_paid, status, payment_status)
             VALUES ('inv1', 'c-none', 'INV-1', 'q1', 'owner@designpro.test', 2100, 2100, 'paid', 'paid')""")
    res = g["growth"].on_invoice_paid("inv1")
    assert res["status"] == "marked_won", res
    assert res["lead_id"] == lead and res["won_value"] == 4200
    row = _one("SELECT * FROM lf_leads WHERE id=?", (lead,))
    assert row["status"] == "won" and row["won_invoice_id"] == "inv1" and row["quote_id"] == "q1"
    assert _one("SELECT status FROM prospect_pipeline WHERE prospect_id=1")["status"] == "won"
    assert _one("SELECT channel FROM lf_activities WHERE lead_id=?", (lead,))["channel"] == "deposit_paid"
    assert g["growth"].on_invoice_paid("inv1")["status"] == "already_won"
    assert g["growth"].reconcile_paid_deposits()["already_won"] == 1


def test_stripe_webhook_path_marks_won(g):
    from app.routers import payments
    importlib.reload(payments)
    lead = _exec("""INSERT INTO lf_leads (business_unit, first_name, phone, status, created_at)
                    VALUES ('workroom', 'Kate', '301-555-7788', 'new', datetime('now'))""")
    _exec("""INSERT INTO invoices (id, customer_id, invoice_number, client_phone, subtotal, tax_rate, total, amount_paid, balance_due, status)
             VALUES ('inv2', 'c-none2', 'INV-2', '+1 (301) 555-7788', 1000, 0, 1000, 0, 1000, 'sent')""")
    assert payments._update_invoice_status("inv2", "paid", stripe_session_id="cs_test_abc", amount_cents=50000)
    row = _one("SELECT status, won_invoice_id FROM lf_leads WHERE id=?", (lead,))
    assert row == {"status": "won", "won_invoice_id": "inv2"}


# ── 2. approval queue ────────────────────────────────────────────────────────
def test_approval_queue_email_needs_tap_and_uses_campaign_send_path(g, monkeypatch):
    sent = []
    from app.services.max import email_service
    monkeypatch.setattr(email_service.EmailService, "is_configured", property(lambda self: True))
    monkeypatch.setattr(email_service.EmailService, "send", lambda self, to, subject, body_html=None, **k: sent.append((to, subject, body_html)) or True)
    d = g["po"].draft_outreach(1, "email")
    qid = d["approval_queue_id"]
    assert qid and g["growth"].get_item(qid)["status"] == "pending"
    c = g["client"]
    assert c.post(f"/api/v1/growth/approvals/{qid}/approve", json={}).status_code == 403
    assert sent == []
    assert c.post(f"/api/v1/growth/approvals/{qid}/approve", json={"confirm": True}).status_code == 400  # no address yet
    r = c.post(f"/api/v1/growth/approvals/{qid}/approve",
               json={"confirm": True, "to_address": "owner@designpro.test", "body": "Hi there,\n\nLine two."})
    assert r.status_code == 200 and r.json()["sent"] is True
    assert sent[0][0] == "owner@designpro.test" and "<p>Hi there,</p>" in sent[0][2]
    cd = _one("SELECT status FROM campaign_drafts WHERE id=?", (r.json()["campaign_draft_id"],))
    assert cd["status"] == "sent"
    assert c.post(f"/api/v1/growth/approvals/{qid}/approve", json={"confirm": True}).status_code == 400  # not pending


def test_approval_queue_ig_and_social_are_copy_only(g, monkeypatch):
    from app.services.max import email_service
    monkeypatch.setattr(email_service.EmailService, "send", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    item = g["growth"].enqueue(channel="instagram", body="Hi! Love your work.", source="test", source_ref="ig1",
                               open_url="https://www.instagram.com/designpro/")
    res = asyncio.run(g["growth"].approve(item["id"], confirm=True))
    assert res["status"] == "copied" and res["sent"] is False and res["open_url"].endswith("/designpro/")
    again = g["growth"].enqueue(channel="instagram", body="dup", source="test", source_ref="ig1")
    assert again["deduped"] and again["id"] == item["id"]


def test_campaign_drafts_show_up_in_queue(g):
    _exec("""INSERT INTO campaign_drafts (step_type, to_email, to_name, subject, body, status)
             VALUES ('email', 'jen@studio.test', 'Jen', 'Samples', '<p>Hi Jen</p>', 'draft')""")
    items = g["growth"].list_queue()["items"]
    assert any(i["source"] == "campaign" and i["to_address"] == "jen@studio.test" for i in items)
    _exec("""INSERT INTO campaign_drafts (step_type, to_name, subject, body, status)
             VALUES ('follow_up_email', 'Lo', 'Re: hi', 'Just bumping this', 'draft')""")
    items = g["growth"].list_queue()["items"]
    fu = [i for i in items if i["source"] == "campaign" and i["to_name"] == "Lo"]
    assert fu and fu[0]["channel"] == "email"  # a follow-up email is email, even with no address yet


# ── 3. ROI ──────────────────────────────────────────────────────────────────
def test_roi_report_by_channel_with_manual_spend(g):
    _exec("INSERT INTO customers (id, name, source, created_at) VALUES ('c1', 'Ann', 'instagram', datetime('now'))")
    _exec("""INSERT INTO lf_leads (business_unit, first_name, source, status, customer_id, created_at)
             VALUES ('workroom', 'Ann', 'Instagram', 'won', 'c1', datetime('now'))""")
    _exec("""INSERT INTO lf_leads (business_unit, first_name, utm_source, status, created_at)
             VALUES ('workroom', 'Bo', 'ig', 'new', datetime('now'))""")
    _exec("""INSERT INTO quotes_v2 (id, quote_number, customer_id, status, total, created_at)
             VALUES ('q9', 'EST-9', 'c1', 'sent', 3000, datetime('now'))""")
    _exec("""INSERT INTO invoices (id, invoice_number, customer_id, total, amount_paid, paid_at, status)
             VALUES ('i9', 'INV-9', 'c1', 3000, 1500, datetime('now'), 'partial')""")
    month = __import__("datetime").datetime.now().strftime("%Y-%m")
    r = g["client"].post("/api/v1/growth/spend", json={"month": month, "channel": "Instagram ads", "amount": 300})
    assert r.status_code == 200 and r.json()["channel"] == "instagram"
    roi = g["client"].get("/api/v1/growth/roi").json()
    ig = next(c for c in roi["channels"] if c["channel"] == "instagram")
    assert (ig["leads"], ig["won_leads"], ig["quotes"], ig["revenue"], ig["spend"]) == (2, 1, 1, 1500, 300)
    assert ig["roi_pct"] == 400.0 and ig["cost_per_lead"] == 150.0
    assert g["client"].post("/api/v1/growth/spend", json={"month": "2026/10", "channel": "x", "amount": 1}).status_code == 400


# ── 4. social proof ──────────────────────────────────────────────────────────
def test_finished_job_makes_before_after_drafts(g):
    _exec("""INSERT INTO quotes_v2 (id, quote_number, status, total, photos_json, created_at)
             VALUES ('qp', 'EST-P', 'accepted', 5000, ?, datetime('now'))""",
          (json.dumps([{"url": "/api/v1/photos/serve/quote/qp/intake_1.jpg", "from_intake": True}]),))
    _exec("""INSERT INTO jobs (id, customer_id, title, client_name, status, quote_id, room, description, client_address, production_start, completed_date)
             VALUES ('j1', 'c-j1', 'Job for Lauren Bassett — EST-P', 'Lauren Bassett', 'completed', 'qp', 'Living Room',
                     'pinch-pleat drapery and Roman shades', '12 Elm St, Bethesda, MD 20814', '2026-09-01', datetime('now'))""")
    _exec("""INSERT INTO job_documents (id, job_id, document_type, url, filename, created_at)
             VALUES ('d1', 'j1', 'photo', '/api/v1/photos/job/j1/after-install.jpg', 'after-install.jpg', '2026-09-20')""")
    res = g["growth"].social_proof_for_job("j1")
    assert res["status"] == "drafted" and res["posted"] is False and len(res["post_ids"]) == 2
    assert res["photos"]["before"] == ["/api/v1/photos/serve/quote/qp/intake_1.jpg"]
    assert res["photos"]["after"] == ["/api/v1/photos/job/j1/after-install.jpg"]
    post = g["sf"]._load_one(g["sf"].POSTS_DIR, res["post_ids"][0])
    assert post["status"] == "draft" and "Bethesda, MD" in post["content"] and len(post["media_urls"]) == 2
    q = g["growth"].get_item(res["queue_ids"][0])
    assert q["kind"] == "social_post" and q["status"] == "pending"
    assert g["growth"].social_proof_for_job("j1")["status"] == "already_drafted"
    _exec("""INSERT INTO jobs (id, customer_id, title, status, completed_date) VALUES ('j2', 'c-j2', 'MOCK-SWEEP test job', 'completed', datetime('now'))""")
    scan = g["growth"].scan_completed_jobs()
    assert scan["skipped_test"] == 1 and scan["drafted"] == []


# ── 5. morning brief + job runner ────────────────────────────────────────────
def test_morning_brief_text_and_dry_run_never_sends(g, monkeypatch):
    txt = g["growth"].morning_brief_text()
    assert "Top prospects" in txt and "Follow-ups due" in txt and "Quotes waiting" in txt and "Nothing was sent" in txt
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("growth_jobs", pathlib.Path(__file__).parents[1] / "scripts" / "growth_jobs.py")
    gj = importlib.util.module_from_spec(spec); spec.loader.exec_module(gj)
    monkeypatch.setattr(gj, "_send_founder", lambda text: (_ for _ in ()).throw(AssertionError("must not send")))
    monkeypatch.setattr(gj, "LOG_DIR", g["tmp"]); monkeypatch.setattr(gj, "STATE", g["tmp"] / "state.json")
    res = gj.run_brief(dry_run=True)
    assert res["sent"] is False and res["dry_run"] is True


# ── 6. Google Place Details ──────────────────────────────────────────────────
def test_place_details_needs_key_then_fills_and_respects_free_cap(g, monkeypatch):
    pd = g["pd"]
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    assert pd.enrich()["status"] == "needs_key"
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-key")
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(200, json={"websiteUri": "https://designpro.test", "nationalPhoneNumber": "(703) 555-1000"})
    real = httpx.Client
    monkeypatch.setattr(pd.httpx, "Client", lambda **k: real(transport=httpx.MockTransport(handler), **k))
    monkeypatch.setattr(pd, "FREE_CALLS", 1)
    res = pd.enrich(limit=5)
    assert res["processed"] == 1 and res["status"] == "free_tier_reached" and res["calls"] == 1
    assert _one("SELECT website, phone FROM prospects WHERE id=1") == {"website": "https://designpro.test", "phone": "(703) 555-1000"}
    monkeypatch.setattr(pd, "HARD_CAP", 2)
    res2 = pd.enrich(limit=5, allow_paid=True)
    assert res2["processed"] == 1 and pd.usage()["calls"] == 2
    _exec("INSERT INTO prospects (id, name, source, external_id, score) VALUES (3, 'Third', 'google_places', 'PLACE3', 70)")
    assert pd.enrich(limit=5, allow_paid=True)["status"] == "hard_cap_reached"
    assert len(calls) == 2


# ── 7. Max improves Max ──────────────────────────────────────────────────────
def test_improvement_loop_needs_two_taps_and_never_builds_without_key(g):
    from app.services.max import tool_executor, voice_live
    importlib.reload(tool_executor)
    r = tool_executor.execute_tool({"tool": "request_improvement", "title": "Bulk approve",
                                    "problem": "Approving 20 IG drafts one by one is slow",
                                    "proposed_change": "Add select-all + approve for copy-only items",
                                    "affected_modules": ["LeadForge"], "risk": "low"}, founder=True)
    assert r.success and r.result["status"] == "proposed"
    rid = r.result["id"]
    # Max has no tool that approves, builds, merges or deploys
    assert not [t for t in tool_executor.TOOL_REGISTRY if "improve" in t and t not in ("request_improvement", "improvements_list")]
    c = g["client"]
    assert c.post(f"/api/v1/growth/improvements/{rid}/approve", json={}).status_code == 403
    a = c.post(f"/api/v1/growth/improvements/{rid}/approve", json={"confirm": True}).json()
    assert a["status"] == "awaiting_build" and a["spec_path"].endswith(".md")
    spec = open(a["spec_path"]).read()
    assert "Do not merge. Do not deploy." in spec and "max/memory.md" in spec
    assert c.post(f"/api/v1/growth/improvements/{rid}/approve-merge", json={"confirm": True}).status_code == 400
    c.post(f"/api/v1/growth/improvements/{rid}/links", json={"pr_url": "https://github.com/r22gir/Empire/pull/1"})
    m = c.post(f"/api/v1/growth/improvements/{rid}/approve-merge", json={"confirm": True}).json()
    assert m["status"] == "merge_approved"
    v = voice_live.run_voice_tool("request_improvement", {"title": "Voice ask", "problem": "p", "proposed_change": "c"})
    assert v["success"] and v["result"]["executed"] is False
    assert "request_improvement" in [t["name"] for t in voice_live.realtime_tool_definitions()]
