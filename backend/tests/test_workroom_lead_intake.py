"""Workroom LeadForge intake: CRM upsert, lead events, quote prefill, source/utm."""

import importlib
import sqlite3
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_quotes_without_booting_max():
    """quotes.py only needs the quality engine. The max package __init__
    imports the AI router and Telegram client, which are not part of intake."""
    max_name = "app.services.max"
    existing = sys.modules.get(max_name)
    if existing is not None and getattr(existing, "__file__", None):
        return
    pkg = types.ModuleType(max_name)
    pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "app" / "services" / "max")]
    pkg.__package__ = max_name
    sys.modules[max_name] = pkg


def _build(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_FOUNDER_CHAT_ID", raising=False)

    import app.db.database as database
    importlib.reload(database)

    import app.routers.leadforge as leadforge
    importlib.reload(leadforge)

    _load_quotes_without_booting_max()
    import app.routers.quotes as quotes
    importlib.reload(quotes)

    from app.routers import notifications
    from app.services import workroom_lead_intake as intake

    importlib.reload(intake)
    notifications.notifications_db.clear()
    intake.reset_intake_state_for_tests()

    app = FastAPI()
    app.include_router(leadforge.router, prefix="/api/v1")
    app.include_router(leadforge.intake_alias_router, prefix="/api/v1")
    return TestClient(app), tmp_path / "empire.db", notifications


def _payload(**overrides):
    body = {
        "full_name": "Ada Designer",
        "email": "Ada@Example.com",
        "phone": "555-0100",
        "firm_name": "Ada Studio",
        "city_region": "Mid-Atlantic",
        "job_type": "drapery_romans",
        "message": "Living room panels, four windows, linen preferred.",
        "photo_urls": ["https://cdn.example/room.jpg"],
        "source": "meta_ad",
        "utm_campaign": "spring_drapery",
        "consent_contact": True,
        "business": "workroom",
        "capture_surface": "workroom_form",
    }
    body.update(overrides)
    return body


def test_double_submit_same_email_one_contact_two_leads(monkeypatch, tmp_path):
    client, db_path, notifications = _build(monkeypatch, tmp_path)

    first = client.post("/api/v1/leads/intake", json=_payload())
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["customer_outcome"] == "created"
    assert first_body["notification"]["channel"] == "founder_inbox"
    assert first_body["notification"]["telegram"] == "not_configured"

    second = client.post(
        "/api/v1/leads/intake",
        json=_payload(email="ada@example.com", message="Second room: primary bedroom romans."),
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["customer_outcome"] == "updated"
    assert second_body["customer_id"] == first_body["customer_id"]
    assert second_body["lead_id"] != first_body["lead_id"]

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM lf_leads").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM lf_prospects").fetchone()[0] == 2
    customer = conn.execute("SELECT business, email, tags FROM customers").fetchone()
    assert customer[0] == "workroom"
    assert customer[1] == "Ada@Example.com"
    assert "business=workroom" in customer[2]
    conn.close()

    intake_notes = [
        note for note in notifications.notifications_db
        if (note.get("context") or {}).get("event") == "workroom_lead_intake"
    ]
    assert len(intake_notes) == 2
    assert {note["context"]["lead_id"] for note in intake_notes} == {
        first_body["lead_id"],
        second_body["lead_id"],
    }


def test_source_and_utm_visible_on_lead(monkeypatch, tmp_path):
    client, _db_path, _notifications = _build(monkeypatch, tmp_path)
    created = client.post("/api/v1/leads/intake", json=_payload()).json()

    lead = client.get(f"/api/v1/leads/{created['lead_id']}")
    assert lead.status_code == 200, lead.text
    row = lead.json()["lead"]
    assert row["source"] == "meta_ad"
    assert row["utm_campaign"] == "spring_drapery"
    assert row["business_unit"] == "workroom"
    assert row["job_type"] == "drapery_romans"
    assert row["campaign"] == "workroom_national_48h"
    assert "business=workroom" in row["tags"]
    assert "utm_campaign=spring_drapery" in row["tags"]
    assert "source=meta_ad" in row["tags"]
    assert row["photo_urls"] == ["https://cdn.example/room.jpg"]


def test_workroom_quote_prefills_lead_and_is_idempotent(monkeypatch, tmp_path):
    client, _db_path, _notifications = _build(monkeypatch, tmp_path)
    created = client.post("/api/v1/leads/intake", json=_payload()).json()

    opened = client.post(f"/api/v1/leads/{created['lead_id']}/workroom-quote")
    assert opened.status_code == 200, opened.text
    body = opened.json()
    assert body["status"] == "created"
    quote = body["quote"]
    assert quote["customer_name"] == "Ada Designer"
    assert quote["customer_email"] == "Ada@Example.com"
    assert quote["customer_phone"] == "555-0100"
    assert "Living room panels" in quote["notes"]
    assert "Living room panels" in quote["project_description"]
    assert quote["business_unit"] == "workroom"
    assert quote["customer_id"] == created["customer_id"]
    assert quote["lead_id"] == created["lead_id"]
    assert quote["intake_source"] == "meta_ad"
    assert quote["utm_campaign"] == "spring_drapery"
    assert quote["photos"] == [
        {"url": "https://cdn.example/room.jpg", "type": "reference", "source": "workroom_intake"}
    ]
    assert quote["firm_name"] == "Ada Studio"
    assert quote["city_region"] == "Mid-Atlantic"

    again = client.post(f"/api/v1/leads/{created['lead_id']}/workroom-quote")
    assert again.status_code == 200, again.text
    assert again.json()["status"] == "existing"
    assert again.json()["quote"]["id"] == quote["id"]


def test_rejects_non_workroom_and_missing_consent(monkeypatch, tmp_path):
    client, db_path, notifications = _build(monkeypatch, tmp_path)
    before = len(notifications.notifications_db)

    apostille = client.post("/api/v1/leads/intake", json=_payload(business="apostille"))
    assert apostille.status_code == 400

    consent = client.post("/api/v1/leads/intake", json=_payload(consent_contact=False))
    assert consent.status_code == 400

    honeypot = client.post("/api/v1/leads/intake", json=_payload(fax_number="555"))
    assert honeypot.status_code == 400

    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "customers" in tables:
        assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM lf_leads").fetchone()[0] == 0
    conn.close()
    assert len(notifications.notifications_db) == before


def test_luxeforge_handoff_uses_same_crm_and_quote_path(monkeypatch, tmp_path):
    client, db_path, _notifications = _build(monkeypatch, tmp_path)
    first = client.post("/api/v1/leads/intake", json=_payload()).json()

    contract = client.get("/api/v1/leadforge/intake/contract")
    assert contract.status_code == 200
    assert contract.json()["luxeforge_handoff"]["same_customer_lead_quote_path"] is True
    assert "brief" in contract.json()["luxeforge_handoff"]["fields"]

    handoff = client.post(
        "/api/v1/leadforge/intake",
        json=_payload(
            email="ada@example.com",
            capture_surface="luxeforge",
            campaign="luxeforge_intake",
            message="Designer portal brief for the living room.",
            luxeforge={
                "brief": "Floor-to-ceiling linen, two windows.",
                "room_count": 2,
                "measure_urls": ["https://cdn.example/measures.pdf"],
                "project_timeline": "6 weeks",
            },
        ),
    )
    assert handoff.status_code == 200, handoff.text
    body = handoff.json()
    assert body["customer_id"] == first["customer_id"]
    assert body["customer_outcome"] == "updated"
    assert body["capture_surface"] == "luxeforge"

    lead = client.get(f"/api/v1/leads/{body['lead_id']}").json()["lead"]
    assert lead["intake_payload"]["luxeforge"]["room_count"] == 2
    assert lead["campaign"] == "luxeforge_intake"

    quote = client.post(f"/api/v1/leads/{body['lead_id']}/workroom-quote").json()["quote"]
    assert "Designer portal brief" in quote["notes"]
    assert "Floor-to-ceiling linen" in quote["notes"]
    assert {"url": "https://cdn.example/measures.pdf", "type": "measure", "source": "luxeforge"} in quote["photos"]
    assert quote["customer_id"] == first["customer_id"]

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 1
    conn.close()


@pytest.mark.parametrize(
    "path",
    ["/api/v1/leads/intake/contract", "/api/v1/leadforge/intake/contract"],
)
def test_contract_documents_how_to_hit_intake(monkeypatch, tmp_path, path):
    client, _db_path, _notifications = _build(monkeypatch, tmp_path)
    response = client.get(path)
    assert response.status_code == 200
    body = response.json()
    assert body["paths"]["intake"] == "POST /api/v1/leads/intake"
    assert body["contact_email"] == "workroom@empirebox.store"
    assert "521" in body["public_host"]
