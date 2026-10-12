"""Organizer flow features: suggested tray, actions, day plan, waiting-on,
templates, money, search + weekly review. Isolated temp DB only. Never sends.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db


@pytest.fixture
def client():
    return TestClient(app)


def _today():
    return date.today().isoformat()


def _customer_job_quote_invoice(name="Marley"):
    cid = f"c_{name.lower()[:6]}"
    jid = f"job_{name.lower()[:6]}"
    qid = f"q_{name.lower()[:6]}"
    iid = f"inv_{name.lower()[:6]}"
    stamp = "2026-10-01T12:00:00"
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO customers (id, name, phone, address, business) VALUES (?, ?, ?, ?, 'workroom')",
            (cid, name, "2025550199", "1200 Grand Ave"),
        )
        try:
            conn.execute(
                """INSERT OR IGNORE INTO jobs
                   (id, title, customer_id, client_name, status, business_unit, address, materials_cost, labor_cost)
                   VALUES (?, ?, ?, ?, 'scheduled', 'workroom', '1200 Grand Ave', 400, 200)""",
                (jid, f"{name} drapery", cid, name),
            )
        except Exception:
            conn.execute(
                "INSERT OR IGNORE INTO jobs (id, title, customer_id, status) VALUES (?, ?, ?, 'scheduled')",
                (jid, f"{name} drapery", cid),
            )
        try:
            conn.execute(
                """INSERT OR IGNORE INTO quotes_v2
                   (id, quote_number, customer_id, customer_name, project_name, status, job_id,
                    total, deposit_required, deposit_paid, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'approved', ?, 2000, 500, 500, ?, ?)""",
                (qid, f"Q-{name[:3].upper()}", cid, name, f"{name} drapes", jid, stamp, stamp),
            )
        except Exception:
            conn.execute(
                """INSERT OR IGNORE INTO quotes_v2 (id, quote_number, status, job_id, total)
                   VALUES (?, ?, 'approved', ?, 2000)""",
                (qid, f"Q-{name[:3].upper()}", jid),
            )
        conn.execute(
            """INSERT OR IGNORE INTO invoices
               (id, invoice_number, customer_id, quote_id, status, total, amount_paid, balance_due, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'partial', 2000, 500, 1500, ?, ?)""",
            (iid, f"INV-{name[:3].upper()}", cid, qid, stamp, stamp),
        )
    return cid, jid, qid, iid


def test_suggested_tray_accept_dismiss_never_silent(client, isolated_empire_db):
    assert os.environ.get("EMPIRE_TASK_DB") == isolated_empire_db
    import app.services.organizer.mail as mailmod
    import app.services.organizer.suggestions as sug
    mailmod.TEST_INBOX = [{
        "id": "gmail:m-flow",
        "source": "gmail",
        "message_id": "m-flow",
        "subject": "Need fabric ETA",
        "from_name": "Supplier",
        "preview": "When can you ship?",
        "space_id": "workroom",
    }]
    sug.TEST_EXTRA = [
        {"source": "whatsapp", "source_ref": "wa1", "title": "WhatsApp: kids pickup", "body": "School office", "space_id": "family", "kind": "todo"},
        {"source": "voice", "source_ref": "vn1", "title": "Voice: order foam", "body": "2 inch foam", "space_id": "workroom", "kind": "todo"},
        {"source": "estimate", "source_ref": "est1", "title": "Start job from approved estimate", "body": "Approved", "space_id": "workroom", "kind": "todo", "quote_id": "q_demo"},
    ]
    try:
        before = client.get("/api/v1/organizer/items").json()["items"]
        listed = client.get("/api/v1/organizer/suggestions")
        assert listed.status_code == 200, listed.text
        body = listed.json()
        assert body["created"] is False
        assert body["sent"] is False
        srcs = {s["source"] for s in body["suggestions"]}
        assert {"email", "whatsapp", "voice", "estimate"} <= srcs
        after_harvest = client.get("/api/v1/organizer/items").json()["items"]
        assert len(after_harvest) == len(before)

        email = next(s for s in body["suggestions"] if s["source"] == "email")
        acc = client.post(f"/api/v1/organizer/suggestions/{email['id']}/accept")
        assert acc.status_code == 200, acc.text
        assert acc.json()["created"] is True
        assert acc.json()["sent"] is False
        assert acc.json()["item"]["title"].startswith("Follow up")

        wa = next(s for s in body["suggestions"] if s["source"] == "whatsapp")
        dis = client.post(f"/api/v1/organizer/suggestions/{wa['id']}/dismiss")
        assert dis.status_code == 200
        assert dis.json()["created"] is False
        assert dis.json()["sent"] is False
        titles = [i["title"] for i in client.get("/api/v1/organizer/items").json()["items"]]
        assert any("Follow up" in t for t in titles)
        assert "WhatsApp: kids pickup" not in titles
    finally:
        mailmod.TEST_INBOX = None
        sug.TEST_EXTRA = None


def test_one_tap_actions_never_pay_or_send(client, isolated_empire_db):
    cid, jid, qid, iid = _customer_job_quote_invoice()
    created = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Marley balance", "job_id": jid,
        "phone": "2025550199", "quote_id": qid, "invoice_id": iid, "space_id": "workroom",
    })
    assert created.status_code == 200, created.text
    item = created.json()["item"]
    assert item["call_link"] == "tel:2025550199"
    acts = client.get(f"/api/v1/organizer/actions?item_id={item['id']}")
    assert acts.status_code == 200, acts.text
    ids = {a["id"] for a in acts.json().get("actions") or []}
    assert {"call", "open_quote", "open_invoice", "mark_paid", "supplier_cart", "snooze", "remind"} <= ids

    cart = client.post("/api/v1/organizer/actions", json={
        "action": "supplier_cart", "item_id": item["id"],
        "lines": [{"title": "Foam", "qty": "2", "note": "Prepare only"}],
    })
    assert cart.status_code == 200, cart.text
    created = cart.json()["created"]
    assert created["prepared"] is True
    assert created["checked_out"] is False
    assert created["paid"] is False
    assert cart.json()["sent"] is False

    paid = client.post("/api/v1/organizer/actions", json={"action": "mark_paid", "item_id": item["id"]})
    assert paid.status_code == 200
    assert paid.json()["sent"] is False
    assert "/?screen=invoice" in (paid.json().get("href") or "")

    snooze = client.post("/api/v1/organizer/actions", json={"action": "snooze", "item_id": item["id"]})
    assert snooze.status_code == 200
    assert snooze.json()["created"]["status"] == "snoozed"

    remind = client.post("/api/v1/organizer/actions", json={"action": "remind", "item_id": item["id"]})
    assert remind.status_code == 200
    assert remind.json()["sent"] is False


def test_plan_my_day_requires_approval(client, isolated_empire_db):
    due = f"{_today()}T09:00:00"
    item = client.post("/api/v1/organizer/items", json={
        "kind": "followup", "title": "Call supplier about foam", "space_id": "workroom",
    }).json()["item"]
    client.post("/api/v1/organizer/items", json={
        "kind": "material_order", "title": "Order welt cord", "space_id": "workroom",
    })
    client.post("/api/v1/organizer/items", json={
        "kind": "install", "title": "Install Marley living", "start_time": due,
        "end_time": f"{_today()}T11:00:00", "space_id": "workroom",
    })
    plan = client.get(f"/api/v1/organizer/day-plan?plan_date={_today()}")
    assert plan.status_code == 200, plan.text
    body = plan.json()
    assert body["requires_approval"] is True
    assert body["approved"] is False
    titles = [s["title"] for s in body["proposed_order"]]
    assert any("foam" in t.lower() or "welt" in t.lower() or "Install" in t for t in titles)
    fresh = client.get("/api/v1/organizer/items").json()["items"]
    follow = next(i for i in fresh if i["id"] == item["id"])
    assert not follow.get("start_time")

    ok = client.post(f"/api/v1/organizer/day-plan/approve?plan_date={_today()}&apply_times=true")
    assert ok.status_code == 200, ok.text
    assert ok.json()["approved"] is True
    assert ok.json()["sent"] is False
    saved = next(i for i in client.get("/api/v1/organizer/items").json()["items"] if i["id"] == item["id"])
    assert saved.get("start_time")
    assert item["id"] in (ok.json().get("applied_ids") or [])


def test_waiting_on_draft_nudge_never_sends(client, isolated_empire_db):
    item = client.post("/api/v1/organizer/items", json={
        "kind": "followup", "title": "Deposit from Marley", "space_id": "workroom",
    }).json()["item"]
    wait = client.post(f"/api/v1/organizer/items/{item['id']}/waiting", json={"who": "Marley", "nudge_after_days": 1})
    assert wait.status_code == 200, wait.text
    assert wait.json()["sent"] is False
    row = wait.json()["item"]
    assert row["status"] == "waiting_on"
    assert row["waiting_on"] == "Marley"
    assert row["nudge_after_days"] == 1
    assert row["column"] == "doing"

    past = (date.today() - timedelta(days=3)).isoformat() + "T09:00:00"
    with get_db() as conn:
        conn.execute(
            "UPDATE organizer_items SET last_moved_at = ?, last_nudge_at = NULL WHERE id = ?",
            (past, item["id"]),
        )
    dispatched = client.post("/api/v1/organizer/waiting/dispatch")
    assert dispatched.status_code == 200, dispatched.text
    body = dispatched.json()
    assert body["sent"] is False
    assert body["outbound_sent"] is False
    assert body["dispatched"] >= 1
    assert all(d.get("sent") is False for d in body["drafts"])
    nudge = client.post("/api/v1/organizer/actions", json={"action": "waiting_nudge", "item_id": item["id"]})
    assert nudge.status_code == 200
    assert nudge.json()["sent"] is False


def test_job_template_and_custom_and_recurrence(client, isolated_empire_db):
    tpls = client.get("/api/v1/organizer/templates")
    assert tpls.status_code == 200, tpls.text
    job = next(t for t in tpls.json()["templates"] if t["slug"] == "job")
    assert job["steps"] == [
        "Order materials", "Cut", "Build", "Upholster", "Install", "Invoice", "Collect balance",
    ]
    applied = client.post(f"/api/v1/organizer/templates/{job['id']}/apply", json={
        "space_id": "workroom", "title": "Marley sofa",
    })
    assert applied.status_code == 200, applied.text
    assert applied.json()["sent"] is False
    assert applied.json()["fraction"] == "0/7"
    assert applied.json()["count"] == 7
    titles = [i["title"] for i in applied.json()["created"]]
    assert titles[0].endswith("Order materials")
    assert titles[-1].endswith("Collect balance")

    custom = client.post("/api/v1/organizer/templates", json={
        "label": "Sunday reset",
        "space_id": "personal",
        "steps": ["Laundry", "Meal prep"],
    })
    assert custom.status_code == 200
    again = client.post(f"/api/v1/organizer/templates/{custom.json()['template']['id']}/apply", json={
        "space_id": "personal",
    })
    assert again.json()["fraction"] == "0/2"

    seed = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Weekly groceries", "space_id": "family",
    }).json()["item"]
    rec = client.post(f"/api/v1/organizer/items/{seed['id']}/recurrence", json={"freq": "weekly"})
    assert rec.status_code == 200
    assert rec.json()["sent"] is False
    with get_db() as conn:
        conn.execute(
            "UPDATE organizer_recurrence SET next_due = ? WHERE item_id = ?",
            ((date.today() - timedelta(days=1)).isoformat() + "T09:00:00", seed["id"]),
        )
    spawned = client.post("/api/v1/organizer/recurrence/spawn")
    assert spawned.status_code == 200
    assert spawned.json()["sent"] is False
    assert spawned.json()["count"] >= 1
    titles = [i["title"] for i in client.get("/api/v1/organizer/items").json()["items"]]
    assert titles.count("Weekly groceries") >= 2


def test_job_money_read_only(client, isolated_empire_db):
    cid, jid, qid, iid = _customer_job_quote_invoice()
    money = client.get(f"/api/v1/organizer/jobs/{jid}/money")
    assert money.status_code == 200, money.text
    body = money.json()
    assert body["read_only"] is True
    assert body["deposit"] == 500
    assert body["paid"] >= 500
    assert body["balance"] >= 0
    assert body["total"] == 2000
    assert "/" in body["collected_fraction"]
    item = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Collect Marley balance", "job_id": jid, "space_id": "workroom",
    }).json()["item"]
    assert item.get("money")
    assert item["money"]["read_only"] is True
    assert item["money"]["deposit"] == 500


def test_search_and_weekly_review(client, isolated_empire_db):
    cid, jid, qid, iid = _customer_job_quote_invoice()
    slipped = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Late school form", "space_id": "family",
        "due_at": (date.today() - timedelta(days=4)).isoformat() + "T09:00:00",
    }).json()["item"]
    nextw = client.post("/api/v1/organizer/items", json={
        "kind": "install", "title": "Next week install", "space_id": "workroom", "job_id": jid,
        "due_at": (date.today() + timedelta(days=3)).isoformat() + "T10:00:00",
    }).json()["item"]
    stuck = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Stuck sew panels", "space_id": "workroom",
    }).json()["item"]
    with get_db() as conn:
        old = (date.today() - timedelta(days=10)).isoformat() + "T09:00:00"
        conn.execute(
            "UPDATE organizer_items SET last_moved_at = ?, updated_at = ? WHERE id = ?",
            (old, old, stuck["id"]),
        )
    search = client.get("/api/v1/organizer/search?q=Marley")
    assert search.status_code == 200, search.text
    hits = search.json()
    assert hits["items"] or hits["jobs"] or hits["clients"] or hits["estimates"]
    assert any("Marley" in (j.get("client_name") or j.get("title") or "") for j in hits["jobs"]) or \
        any("Marley" in (e.get("customer_name") or "") for e in hits["estimates"]) or \
        any("Marley" in (c.get("name") or "") for c in hits["clients"])

    form = client.get("/api/v1/organizer/search?q=school")
    assert any("school" in (i.get("title") or "").lower() for i in form.json()["items"])

    review = client.get("/api/v1/organizer/review/weekly")
    assert review.status_code == 200, review.text
    pack = review.json()
    slipped_ids = {i["id"] for i in pack["slipped"]}
    stuck_ids = {i["id"] for i in pack["stuck"]}
    next_ids = {i["id"] for i in pack["next_week"]}
    assert slipped["id"] in slipped_ids
    assert stuck["id"] in stuck_ids
    assert nextw["id"] in next_ids
    assert pack["sent"] is False


def test_family_edition_isolated_from_workroom_money_and_jobs(client, isolated_empire_db, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    _customer_job_quote_invoice("Marley")
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    search = client.get("/api/v1/organizer/search?q=Marley")
    assert search.status_code == 200
    body = search.json()
    assert body["jobs"] == []
    assert body["estimates"] == []
    assert body["clients"] == []
    money = client.get("/api/v1/organizer/jobs/job_marley/money")
    assert money.status_code == 404
    tpls = client.get("/api/v1/organizer/templates").json()["templates"]
    family = next(t for t in tpls if t["slug"] == "family-week")
    applied = client.post(f"/api/v1/organizer/templates/{family['id']}/apply", json={"space_id": "family"})
    assert applied.status_code == 200
    assert all(i["space_id"] == "family" for i in applied.json()["created"])
    blob = str(applied.json()).lower()
    assert "argos" not in blob
