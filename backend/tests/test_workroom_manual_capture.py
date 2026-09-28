"""Stage 0 Workroom manual capture: one CRM contact, a lead event per submit, quote prefill.

The door must not send email.
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "data"))
    from app.routers.workroom_capture import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _payload(**overrides):
    data = {
        "full_name": "Ada Designer",
        "email": "Ada@Example.com",
        "phone": "202-555-0100",
        "firm_name": "Ada Studio",
        "city_region": "Washington DC",
        "job_type": "drapery_romans",
        "message": "Living room panels, linen, install in November.",
        "photo_urls": ["https://example.com/room.jpg"],
        "source": "houzz",
        "utm_campaign": "workroom_national_48h",
        "consent_contact": "yes",
        "owner": "Rafael",
    }
    data.update(overrides)
    return data


def test_same_email_creates_one_crm_contact_and_two_lead_events(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    first = client.post("/api/v1/workroom-capture/intake", json=_payload())
    second = client.post(
        "/api/v1/workroom-capture/intake",
        json=_payload(
            email="ada@example.com",
            message="Follow-up with a second photo.",
            phone=None,
            consent_contact="unknown",
        ),
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["crm_outcome"] == "created"
    assert second.json()["crm_outcome"] == "matched"
    assert first.json()["customer_id"] == second.json()["customer_id"]
    assert first.json()["lead_id"] != second.json()["lead_id"]
    assert first.json()["outbound_email"] == "not_sent"
    assert second.json()["lead_event"] == "created"
    assert second.json()["intake"]["consent_contact"] == "unknown"
    assert second.json()["intake"]["business"] == "workroom"
    assert second.json()["intake"]["campaign"] == "workroom_national_48h"

    import sqlite3

    conn = sqlite3.connect(tmp_path / "empire.db")
    customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    leads = conn.execute(
        "SELECT COUNT(*) FROM lf_leads WHERE customer_id = ?",
        (first.json()["customer_id"],),
    ).fetchone()[0]
    assert customers == 1
    assert leads == 2


def test_source_and_utm_visible_on_the_record(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    created = client.post(
        "/api/v1/workroom-capture/intake",
        json=_payload(source="meta_ad", utm_campaign="spring_drapery"),
    )
    assert created.status_code == 200, created.text
    intake_id = created.json()["intake"]["id"]
    fetched = client.get(f"/api/v1/workroom-capture/intake/{intake_id}")
    body = fetched.json()["intake"]
    assert body["source"] == "meta_ad"
    assert body["utm_campaign"] == "spring_drapery"
    assert body["photo_urls"] == ["https://example.com/room.jpg"]


def test_quote_prefills_name_email_phone_and_message_without_sending(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    created = client.post("/api/v1/workroom-capture/intake", json=_payload())
    intake_id = created.json()["intake"]["id"]
    opened = client.post(f"/api/v1/workroom-capture/intake/{intake_id}/quote")
    assert opened.status_code == 200, opened.text
    body = opened.json()
    assert body["quote_outcome"] == "created"
    assert body["outbound_email"] == "not_sent"
    assert body["intake"]["status"] == "quoting"
    quote = body["quote"]
    assert quote["customer_name"] == "Ada Designer"
    assert quote["customer_email"] == "Ada@Example.com"
    assert quote["customer_phone"] == "202-555-0100"
    assert quote["project_description"] == "Living room panels, linen, install in November."
    assert "Living room panels" in quote["notes"]
    assert quote["business_unit"] == "workroom"
    assert quote["source"] == "houzz"
    assert quote["utm_campaign"] == "workroom_national_48h"
    assert quote["customer_id"] == created.json()["customer_id"]
    assert body["links"]["quote"] == f"/quote/{quote['id']}"

    saved = json.loads((tmp_path / "data" / "quotes" / f"{quote['id']}.json").read_text())
    assert saved["sent_at"] is None
    assert saved["status"] == "draft"
    assert saved["pricing_mode"] == "flat"

    again = client.post(f"/api/v1/workroom-capture/intake/{intake_id}/quote")
    assert again.status_code == 200
    assert again.json()["quote_outcome"] == "already_open"
    assert again.json()["quote_id"] == quote["id"]
    files = list((tmp_path / "data" / "quotes").glob("*.json"))
    assert len([path for path in files if not path.name.startswith("_")]) == 1


def test_other_business_and_bad_enums_are_rejected(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    apostille = client.post("/api/v1/workroom-capture/intake", json=_payload(business="apostille"))
    assert apostille.status_code == 400
    bad_job = client.post("/api/v1/workroom-capture/intake", json=_payload(job_type="roofing"))
    assert bad_job.status_code == 422
    missing_consent = _payload()
    missing_consent.pop("consent_contact")
    assert client.post("/api/v1/workroom-capture/intake", json=missing_consent).status_code == 422


def test_status_update_does_not_send_email(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    created = client.post("/api/v1/workroom-capture/intake", json=_payload(source="instagram"))
    intake_id = created.json()["intake"]["id"]
    updated = client.patch(
        f"/api/v1/workroom-capture/intake/{intake_id}",
        json={
            "status": "needs_info",
            "last_contacted_at": "2026-09-28T14:00:00",
            "next_action": "Ask for measures",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["outbound_email"] == "not_sent"
    assert updated.json()["intake"]["status"] == "needs_info"
    assert updated.json()["intake"]["last_contacted_at"] == "2026-09-28T14:00:00"


def test_capture_page_is_workroom_copy_only():
    page = (
        Path(__file__).resolve().parents[2]
        / "empire-command-center/app/workroom/capture/page.tsx"
    ).read_text()
    lowered = page.lower()
    assert "apostapp" not in lowered
    assert "empirebox os" not in lowered
    assert "powered by leadforge" not in lowered
    assert "workroom@empirebox.store" in lowered
    assert "workroom-capture/intake" in page
    assert "does not send email" in lowered


def test_service_has_no_outbound_mail_hooks():
    backend = Path(__file__).resolve().parents[1]
    source = (backend / "app/services/workroom_capture.py").read_text()
    router = (backend / "app/routers/workroom_capture.py").read_text()
    for text in (source, router):
        lowered = text.lower()
        assert "sendgrid" not in lowered
        assert "smtplib" not in lowered
        assert "telegram" not in lowered
        assert "mailto:" not in lowered
