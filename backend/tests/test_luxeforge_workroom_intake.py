"""LuxeForge rich briefs and LeadForge thin ads share one Workroom door.

Repeat email → one ForgeCRM customer, one LeadForge prospect, one lead,
two intake events, two founder notifications. Quote create uses
quotes.create_quote and prefills name, email, phone, message, measure notes,
and photo URLs.
"""

import importlib
import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def _boot(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    import app.db.database as database
    import app.db.init_db as init_db

    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()

    import app.routers.quotes as quotes
    from app.services.max.response_quality_engine import QualityResult

    importlib.reload(quotes)
    quotes_dir = tmp_path / "quotes"
    quotes_dir.mkdir()
    monkeypatch.setattr(quotes, "QUOTES_DIR", str(quotes_dir))
    monkeypatch.setattr(quotes, "COUNTER_FILE", str(quotes_dir / "_counter.json"))
    monkeypatch.setattr(
        quotes.quality_engine,
        "validate",
        lambda content, channel, context: QualityResult(
            original=content,
            cleaned=content,
            channel=getattr(channel, "value", str(channel)),
            mode="test",
        ),
    )

    import app.routers.workroom_intake as workroom_intake

    importlib.reload(workroom_intake)
    app = FastAPI()
    app.include_router(workroom_intake.router, prefix="/api/v1")
    return TestClient(app)


def _brief(**overrides):
    payload = {
        "full_name": "Ada Draper",
        "email": "Ada@Studio.example",
        "phone": "555-0148",
        "firm_name": "Ada Design",
        "city_region": "Baltimore, MD",
        "job_type": "drapery_romans",
        "message": "Living room sheers and a roman in the study.",
        "measure_notes": "Living 96w x 108h outside mount. Study 42w x 60h.",
        "photo_urls": ["https://cdn.example/window.jpg"],
        "source": "houzz",
        "utm_campaign": "spring-designers",
        "consent_contact": True,
        "capture_channel": "luxeforge",
        "business": "workroom",
    }
    payload.update(overrides)
    return payload


def _counts(tmp_path, email="ada@studio.example"):
    conn = sqlite3.connect(tmp_path / "empire.db")
    conn.row_factory = sqlite3.Row
    customer = conn.execute(
        "SELECT COUNT(*) AS c FROM customers WHERE LOWER(email) = LOWER(?)",
        (email,),
    ).fetchone()["c"]
    prospect = conn.execute(
        "SELECT COUNT(*) AS c FROM prospects WHERE LOWER(email) = LOWER(?)",
        (email,),
    ).fetchone()["c"]
    lead = conn.execute(
        "SELECT COUNT(*) AS c FROM lf_leads WHERE LOWER(email) = LOWER(?) AND business_unit = 'workroom'",
        (email,),
    ).fetchone()["c"]
    events = conn.execute(
        "SELECT COUNT(*) AS c FROM lf_workroom_intake_events WHERE LOWER(email) = LOWER(?)",
        (email,),
    ).fetchone()["c"]
    notes = conn.execute(
        """SELECT COUNT(*) AS c FROM lf_activities a
           JOIN lf_leads l ON l.id = a.lead_id
           WHERE LOWER(l.email) = LOWER(?) AND a.type = 'note'""",
        (email,),
    ).fetchone()["c"]
    lead_row = conn.execute(
        "SELECT * FROM lf_leads WHERE LOWER(email) = LOWER(?)",
        (email,),
    ).fetchone()
    conn.close()
    return {
        "customers": customer,
        "prospects": prospect,
        "leads": lead,
        "events": events,
        "notes": notes,
        "lead": dict(lead_row) if lead_row else None,
    }


def test_luxeforge_brief_upserts_crm_lead_and_prefills_quote(monkeypatch, tmp_path):
    client = _boot(monkeypatch, tmp_path)
    first = client.post("/api/v1/leadforge/intake", json=_brief())
    assert first.status_code == 200, first.text
    saved = first.json()
    assert saved["crm_outcome"] == "created"
    assert saved["lead_outcome"] == "created"
    assert saved["prospect_outcome"] == "created"
    assert saved["business"] == "workroom"
    assert saved["capture_channel"] == "luxeforge"
    assert saved["events_for_email"] == 1
    assert saved["notified"] is True
    assert saved["quote_prefill"]["customer_name"] == "Ada Draper"
    assert saved["quote_prefill"]["customer_email"] == "ada@studio.example"
    assert saved["quote_prefill"]["customer_phone"] == "555-0148"
    assert "Living room sheers" in saved["quote_prefill"]["notes"]
    assert "96w x 108h" in saved["quote_prefill"]["notes"]
    assert saved["quote_prefill"]["photos"][0]["url"] == "https://cdn.example/window.jpg"
    assert saved["quote_prefill"]["business_unit"] == "workroom"

    second = client.post(
        "/api/v1/leadforge/intake",
        json=_brief(
            email="ada@studio.example",
            message="Updated: add a banquette cushion in the nook.",
            job_type="mixed",
            phone="555-0199",
        ),
    )
    assert second.status_code == 200, second.text
    again = second.json()
    assert again["lead_id"] == saved["lead_id"]
    assert again["customer_id"] == saved["customer_id"]
    assert again["prospect_id"] == saved["prospect_id"]
    assert again["crm_outcome"] == "matched"
    assert again["lead_outcome"] == "updated"
    assert again["events_for_email"] == 2
    assert "banquette cushion" in again["quote_prefill"]["notes"]

    counts = _counts(tmp_path)
    assert counts["customers"] == 1
    assert counts["prospects"] == 1
    assert counts["leads"] == 1
    assert counts["events"] == 2
    assert counts["notes"] == 2
    assert counts["lead"]["source"] == "houzz"
    assert counts["lead"]["utm_campaign"] == "spring-designers"
    assert counts["lead"]["business_unit"] == "workroom"
    tags = json.loads(counts["lead"]["tags"])
    assert "business=workroom" in tags
    assert "utm=spring-designers" in tags

    inbox = list((tmp_path / "data" / "inbox").glob("wri-*.json"))
    assert len(inbox) == 2
    notice = json.loads(inbox[0].read_text())
    assert notice["customer_id"] == saved["customer_id"]
    assert notice["deep_link"] == "/luxe"
    assert "ada@studio.example" in notice["text"]

    detail = client.get(f"/api/v1/leadforge/intake/{saved['lead_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["source"] == "houzz"
    assert body["utm_campaign"] == "spring-designers"
    assert body["customer"]["id"] == saved["customer_id"]
    assert body["prospect"]["id"] == saved["prospect_id"]
    assert len(body["events"]) == 2

    opened = client.post(f"/api/v1/leadforge/intake/{saved['lead_id']}/quote")
    assert opened.status_code == 200, opened.text
    quote = opened.json()["quote"]
    assert quote["customer_name"] == "Ada Draper"
    assert quote["customer_email"] == "ada@studio.example"
    assert quote["customer_phone"] == "555-0199"
    assert quote["business_unit"] == "workroom"
    assert "banquette cushion" in quote["notes"]
    assert "96w x 108h" in quote["notes"]
    assert quote["photos"][0]["url"] == "https://cdn.example/window.jpg"
    assert quote["customer_id"] == saved["customer_id"]
    assert quote["lead_id"] == saved["lead_id"]

    repeated = client.post(f"/api/v1/leadforge/intake/{saved['lead_id']}/quote")
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "existing"
    assert repeated.json()["quote_id"] == quote["id"]
    assert _counts(tmp_path)["customers"] == 1


def test_leadforge_thin_intake_uses_same_customer_table(monkeypatch, tmp_path):
    client = _boot(monkeypatch, tmp_path)
    rich = client.post("/api/v1/leadforge/intake", json=_brief())
    assert rich.status_code == 200

    thin = client.post(
        "/api/v1/leadforge/intake",
        json={
            "full_name": "Sam Buyer",
            "email": "sam@ads.example",
            "job_type": "soft_seating",
            "message": "Need a sofa recovered.",
            "source": "meta_ad",
            "consent_contact": True,
        },
    )
    assert thin.status_code == 200, thin.text
    saved = thin.json()
    assert saved["capture_channel"] == "leadforge"
    assert saved["business"] == "workroom"
    assert "campaign=workroom_national_48h" in saved["tags"]
    assert saved["customer_id"] != rich.json()["customer_id"]

    conn = sqlite3.connect(tmp_path / "empire.db")
    rows = conn.execute("SELECT email, business FROM customers ORDER BY email").fetchall()
    conn.close()
    assert {row[0] for row in rows} == {"ada@studio.example", "sam@ads.example"}
    assert {row[1] for row in rows} == {"workroom"}


def test_intake_rejects_missing_consent_and_non_workroom_business(monkeypatch, tmp_path):
    client = _boot(monkeypatch, tmp_path)
    denied = client.post("/api/v1/leadforge/intake", json=_brief(consent_contact=False))
    assert denied.status_code == 400

    other = client.post("/api/v1/leadforge/intake", json=_brief(business="apostille"))
    assert other.status_code == 422
    conn = sqlite3.connect(tmp_path / "empire.db")
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
    conn.close()


def test_brief_ui_posts_to_shared_leadforge_path_without_side_product_copy():
    form = (ROOT / "empire-command-center/app/components/screens/WorkroomBriefForm.tsx").read_text()
    page = (ROOT / "empire-command-center/app/components/screens/LuxeForgePage.tsx").read_text()
    routes = (ROOT / "empire-command-center/app/luxe/page.tsx").read_text() + (
        ROOT / "empire-command-center/app/luxeforge/page.tsx"
    ).read_text()
    middleware = (ROOT / "empire-command-center/middleware.ts").read_text()

    assert 'capture_channel: \'luxeforge\'' in form
    assert "/leadforge/intake" in form
    assert "workroom@empirebox.store" in form
    assert "ApostApp" not in form
    assert "EmpireBox OS" not in form
    assert "WorkroomBriefForm" in page
    assert "LuxeForgePage" in routes
    assert 'url.pathname = "/intake"' in middleware
    assert "luxe.empirebox.store" in middleware
