"""Sprint M isolated-store tests. Never touch live empire.db or /data family-help."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import sprint_m
from app.services.sprint_m.fabric import sanitize_fabric_code
from app.services.sprint_m.measurements import inches_to_fraction
from app.services.sprint_m.store import get_store


def _app():
    app = FastAPI()
    app.include_router(sprint_m.router, prefix="/api/v1")
    return app


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    sprint_db = tmp_path / "sprint_m.db"
    help_db = tmp_path / "family-help" / "ed" / "help.db"
    help_db.parent.mkdir(parents=True)
    monkeypatch.setenv("SPRINT_M_DB", str(sprint_db))
    monkeypatch.setenv("FAMILY_HELP_DB", str(help_db))
    monkeypatch.setenv("FAMILY_HELP_OWNER_ALERTS", "false")
    monkeypatch.delenv("FAMILY_HELP_OWNER_PHONE", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("FAMILY_HELP_SMS_TOKEN", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SQUARE_ACCESS_TOKEN", raising=False)
    client = TestClient(_app())
    return {
        "client": client,
        "sprint_db": sprint_db,
        "help_db": help_db,
        "tmp": tmp_path,
    }


APPROVED_QUOTE = {
    "id": "quote-approved-1",
    "quote_number": "EST-2026-0888",
    "status": "approved",
    "customer_name": "Ada Client",
    "customer_id": "cust-ada",
    "business_unit": "workroom",
    "project_name": "Primary bedroom panels",
    "total": 4200,
    "due_date": "2026-11-02",
    "photos": [{"url": "/uploads/quote/east-window.jpg", "original_name": "east-window.jpg"}],
    "line_items": [
        {
            "item_type": "drapery",
            "item_style": "pinch pleat",
            "description": "East window panels",
            "room": "Primary Bedroom",
            "fabric_code": "Kravet V639 Navy Velvet",
            "width": 84.5,
            "height": 96.25,
            "labor_hours": 8,
            "labor_rate": 45,
            "labor_total": 360,
            "quantity": 1,
            "photos": ["/uploads/quote/east-window.jpg"],
        }
    ],
}


def test_fabric_codes_come_from_shared_registry(isolated):
    """Kravet V639 must never leak. Next vinyl after reserved V001–V007 is V008."""
    first = sanitize_fabric_code("Kravet V639 Navy Velvet")
    assert first == "V008-Navy"
    assert "V639" not in first
    assert "Kravet" not in first
    # Same material looks up the existing assignment — never a new SKU, never reuse a new number.
    again = sanitize_fabric_code("Kravet V639 Navy Velvet")
    assert again == "V008-Navy"
    # A supplier-looking 'V639-Navy' is not in the registry, so it also assigns/looks up.
    assert sanitize_fabric_code("V639-Navy") == "V008-Navy"
    gold = sanitize_fabric_code("Fabricut V012-Soft Gold wholesale")
    assert gold == "V009-SoftGold"
    assert "V012" not in gold
    assert "Fabricut" not in gold
    assert sanitize_fabric_code("Kravet Velvet") == "V010-Unspecified"


def test_reserved_v001_through_v007_are_not_reused(isolated):
    from app.services.sprint_m.fabric import highest_sequence, next_sequence

    with get_store() as conn:
        assert highest_sequence(conn, "V") == 7
        assert next_sequence(conn, "V") == 8
        code = sanitize_fabric_code("Kravet V639 Navy Velvet", conn=conn)
        assert code == "V008-Navy"
        row = conn.execute(
            "SELECT code, supplier_sku, brand FROM sm_fabric_codes WHERE code = ?",
            ("V008-Navy",),
        ).fetchone()
        assert row["supplier_sku"] == "V639"
        assert (row["brand"] or "").lower() == "kravet"
        client = {"code": row["code"], "color": "Navy"}
        assert "Kravet" not in str(client)
        assert "V639" not in client["code"]


def test_measurements_use_fractions():
    assert inches_to_fraction(84.5) == "84 1/2 in"
    assert inches_to_fraction(96.25) == "96 1/4 in"
    assert inches_to_fraction(72) == "72 in"
    assert inches_to_fraction("12 1/2") == "12 1/2 in"


def test_unapproved_quote_is_rejected(isolated):
    client = isolated["client"]
    quote = {**APPROVED_QUOTE, "status": "draft"}
    res = client.post("/api/v1/sprint-m/work-orders/from-quote", json={"quote": quote})
    assert res.status_code == 400
    assert "approved" in res.json()["detail"].lower()


def test_work_order_from_approved_quote_carries_fields(isolated):
    client = isolated["client"]
    res = client.post("/api/v1/sprint-m/work-orders/from-quote", json={"quote": APPROVED_QUOTE})
    assert res.status_code == 200
    job = res.json()["job"]
    assert job["status"] == "sold"
    assert job["style"] == "pinch pleat"
    assert job["fabric_codes"] == ["V008-Navy"]
    assert job["organizer_space"] == "workroom"
    dumped = str(job)
    assert "Kravet" not in dumped
    assert "V639" not in dumped
    assert job["seamstress_hours"] == 8
    assert job["seamstress_pay"] == 360
    assert job["due_date"] == "2026-11-02"
    assert "/uploads/quote/east-window.jpg" in job["photos"]
    item = job["items"][0]
    assert item["fabric_code"] == "V008-Navy"
    tasks = job["organizer_tasks"]
    assert tasks
    assert all(t["space_id"] == "workroom" for t in tasks)
    assert any(t["kind"] in {"deadline", "todo"} and job["job_number"] in (t["title"] or "") for t in tasks)
    assert any(t["kind"] == "job_milestone" for t in tasks)
    assert any(t["kind"] == "material_order" and t.get("order_ref") == "V008-Navy" for t in tasks)
    with get_store() as conn:
        rows = conn.execute(
            "SELECT kind, title, space_id, job_id FROM organizer_items WHERE job_id = ?",
            (job["id"],),
        ).fetchall()
        assert rows
        assert all(r["space_id"] == "workroom" for r in rows)
    assert item["measurements"]["width"]["display"] == "84 1/2 in"
    assert item["measurements"]["height"]["display"] == "96 1/4 in"
    listed = client.get("/api/v1/sprint-m/jobs").json()["jobs"]
    assert listed[0]["items"][0]["measurements"]["width"]["display"] == "84 1/2 in"
    assert isolated["sprint_db"].exists()
    assert not Path("/data/ed/family-help/ed/help.db").exists() or isolated["help_db"] != Path("/data/ed/family-help/ed/help.db")


def test_rules_engine_drafts_only_and_never_sends(isolated):
    client = isolated["client"]
    created = client.post("/api/v1/sprint-m/work-orders/from-quote", json={"quote": APPROVED_QUOTE}).json()["job"]
    scheduled = client.post(f"/api/v1/sprint-m/jobs/{created['id']}/schedule", json={})
    assert scheduled.status_code == 200
    assert scheduled.json()["job"]["status"] == "scheduled"
    drafts = client.get("/api/v1/sprint-m/drafts").json()["drafts"]
    assert drafts
    assert all(d["status"] in {"draft", "approved"} for d in drafts)
    draft_id = drafts[0]["id"]
    send = client.post(f"/api/v1/sprint-m/drafts/{draft_id}/send")
    assert send.status_code == 403
    assert "never sends" in send.json()["detail"].lower()
    approved = client.post(f"/api/v1/sprint-m/drafts/{draft_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    still_blocked = client.post(f"/api/v1/sprint-m/drafts/{draft_id}/send")
    assert still_blocked.status_code == 403


def test_text_to_pay_stripe_and_square_are_drafts(isolated):
    client = isolated["client"]
    workroom = client.post("/api/v1/sprint-m/work-orders/from-quote", json={"quote": APPROVED_QUOTE}).json()["job"]
    sms = client.post(f"/api/v1/sprint-m/jobs/{workroom['id']}/text-to-pay", json={"channel": "sms"})
    assert sms.status_code == 200
    body = sms.json()
    assert body["max_sends_to_clients"] is False
    assert body["draft"]["status"] == "draft"
    assert body["draft"]["channel"] == "sms"
    assert body["payment_link"]["provider"] == "stripe"
    assert body["payment_link"]["brand"] == "Empire Workroom"
    assert body["payment_link"]["non_expiring"] is True
    assert body["payment_link"]["expires_at"] is None

    nelma_quote = {
        **APPROVED_QUOTE,
        "id": "quote-nelmas-1",
        "quote_number": "EST-2026-0889",
        "business_unit": "nelmas",
    }
    nelma = client.post("/api/v1/sprint-m/work-orders/from-quote", json={"quote": nelma_quote}).json()["job"]
    wa = client.post(f"/api/v1/sprint-m/jobs/{nelma['id']}/text-to-pay", json={"channel": "whatsapp"})
    assert wa.status_code == 200
    assert wa.json()["payment_link"]["provider"] == "square"
    assert wa.json()["payment_link"]["brand"] == "Nelma's"
    assert wa.json()["draft"]["channel"] == "whatsapp"
    assert wa.json()["draft"]["status"] == "draft"


def test_job_costing_planned_vs_actual_margin(isolated):
    client = isolated["client"]
    job = client.post("/api/v1/sprint-m/work-orders/from-quote", json={"quote": APPROVED_QUOTE}).json()["job"]
    summary = client.get(f"/api/v1/sprint-m/jobs/{job['id']}/costing").json()
    assert summary["revenue"] == 4200
    assert summary["planned"]["labor"] == 360
    assert summary["planned"]["materials"] == 3840
    assert summary["planned"]["margin_pct"] == 0.0
    client.post(
        f"/api/v1/sprint-m/jobs/{job['id']}/costing",
        json={"category": "materials", "description": "Actual fabric", "actual_amount": 2100},
    )
    client.post(
        f"/api/v1/sprint-m/jobs/{job['id']}/costing",
        json={"category": "labor", "description": "Actual hours", "actual_amount": 400},
    )
    after = client.get(f"/api/v1/sprint-m/jobs/{job['id']}/costing").json()
    assert after["actual"]["materials"] == 2100
    assert after["actual"]["labor"] == 400
    assert after["actual"]["total"] == 2500
    assert after["actual"]["profit"] == 1700
    assert after["actual"]["margin_pct"] == 40.48


def test_credit_memos_overpayments_apply_to_invoice(isolated):
    client = isolated["client"]
    memo = client.post(
        "/api/v1/sprint-m/credits/memos",
        json={"customer_id": "cust-ada", "customer_name": "Ada Client", "amount": 150, "reason": "Deposit adjustment"},
    )
    assert memo.status_code == 200
    assert memo.json()["credit_balance"] == 150
    over = client.post(
        "/api/v1/sprint-m/credits/overpayments",
        json={"customer_id": "cust-ada", "amount": 50, "invoice_id": "INV-OLD"},
    )
    assert over.json()["overpayment_balance"] == 50
    assert over.json()["available"] == 200
    applied = client.post(
        "/api/v1/sprint-m/credits/cust-ada/apply",
        json={"invoice_id": "INV-2026-010", "amount": 180},
    )
    assert applied.status_code == 200
    assert applied.json()["last_application"]["invoice_id"] == "INV-2026-010"
    assert applied.json()["last_application"]["amount"] == 180
    assert applied.json()["available"] == 20


def test_family_alert_is_owner_only_and_noop_without_credentials(isolated):
    client = isolated["client"]
    res = client.post(
        "/api/v1/sprint-m/family-help",
        json={"requester": "juan", "message": "Pedir ayuda a Max — please create a new drawing", "source": "Pedir ayuda a Max"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["requester"] == "Juan"
    assert body["requester_agent"] == "Max-e"
    assert body["classification"] == "create"
    assert body["recipient_role"] == "owner"
    assert body["recipient_name"] == "Rafael"
    assert body["owner_only"] is True
    assert body["sent_to_family"] is False
    assert body["delivery_status"] == "noop"
    assert body["noop_reason"] == "feature_flag_off"
    assert isolated["help_db"].exists()
    assert isolated["help_db"].is_relative_to(isolated["tmp"])


def test_family_alert_camilo_fix_queued_when_configured(isolated, monkeypatch):
    monkeypatch.setenv("FAMILY_HELP_OWNER_ALERTS", "true")
    monkeypatch.setenv("FAMILY_HELP_OWNER_PHONE", "+15551212")
    monkeypatch.setenv("FAMILY_HELP_OWNER_CHANNEL", "whatsapp")
    monkeypatch.setenv("FAMILY_HELP_WHATSAPP_TOKEN", "test-token-not-live")
    client = TestClient(_app())
    res = client.post(
        "/api/v1/sprint-m/family-help",
        json={"requester": "camilo", "message": "arreglar the broken hem, need a fix"},
    )
    body = res.json()
    assert body["requester"] == "Camilo"
    assert body["requester_agent"] == "Maxine"
    assert body["classification"] == "fix"
    assert body["delivery_status"] == "queued_not_sent"
    assert body["delivery_channel"] == "whatsapp"
    assert body["recipient"] == "+15551212"
    assert body["sent_to_family"] is False


def test_family_alert_flag_on_but_missing_credentials_is_noop(isolated, monkeypatch):
    monkeypatch.setenv("FAMILY_HELP_OWNER_ALERTS", "true")
    monkeypatch.setenv("FAMILY_HELP_OWNER_PHONE", "+15551212")
    client = TestClient(_app())
    res = client.post(
        "/api/v1/sprint-m/family-help",
        json={"requester": "juan", "message": "need an adjust on the width"},
    )
    body = res.json()
    assert body["classification"] == "adjust"
    assert body["delivery_status"] == "noop"
    assert body["noop_reason"] == "missing_credentials"


def test_status_declares_studio_isolation(isolated):
    status = isolated["client"].get("/api/v1/sprint-m/status").json()
    assert status["sprint"] == "M"
    assert status["isolated_store"] is True
    assert status["max_sends_to_clients"] is False
    assert status["fabric_policy"] == "docs/FABRIC_CODES.csv sequential registry (PR #128)"
    assert status["organizer"]["surface"] == "WorkroomOrganizer"
    assert status["organizer"]["screen"] == "calendar"
    assert status["organizer"]["duplicate_removed"] is True
    assert status["measurements"] == "fractions"
    assert status["amp_maxine_merged"] is False
    assert status["family_alerts"]["owner_only"] is True
    assert status["family_alerts"]["amp_maxine_merged"] is False
