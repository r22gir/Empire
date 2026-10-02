"""LuxeForge submit lands in the owner list, not only in the designer portal."""

import asyncio
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.db import database
from app.routers import fabrics, intake_auth
from app.services import luxeforge_intake_handoff as handoff


client = TestClient(app)


def _configure(monkeypatch, tmp_path):
    db = tmp_path / "empire.db"
    uploads = tmp_path / "uploads"
    photos = tmp_path / "photos"
    uploads.mkdir()
    photos.mkdir()
    monkeypatch.setattr(intake_auth, "DB_PATH", str(db))
    monkeypatch.setattr(intake_auth, "UPLOADS_DIR", str(uploads))
    monkeypatch.setattr(intake_auth, "PHOTOS_DIR", str(photos))
    monkeypatch.setattr(database, "DB_PATH", str(db))
    intake_auth.init_db()
    fabrics._init_intake_fabrics_table()
    return db


def _signup_and_project(monkeypatch):
    async def _noop_handoff(project, user, fabrics_rows):
        return {
            "lead_id": 41,
            "customer_id": "cust-41",
            "quote_id": "q41",
            "quote_number": "EST-41",
            "notice": {"to": handoff.OWNER_NOTICE_EMAIL, "sent": True, "customer_emailed": False},
        }

    monkeypatch.setattr(handoff, "handoff_submitted_intake", _noop_handoff)
    email = f"designer-{uuid.uuid4().hex[:8]}@example.com"
    user_id = str(uuid.uuid4())
    conn = intake_auth.get_db()
    conn.execute(
        """INSERT INTO intake_users
           (id, name, email, phone, password_hash, company, role, business)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, "Rafael Designer", email, "555-0101", "hash", "Studio North", "client", "workroom"),
    )
    conn.commit()
    conn.close()
    auth = {"Authorization": f"Bearer {intake_auth.create_token(user_id, email)}"}
    created = client.post("/api/v1/intake/projects", headers=auth, json={
        "name": "Johnson Residence",
        "address": "1 Main St",
        "treatment": "drapery",
        "business": "workroom",
        "rooms": [{"name": "Living Room", "treatment": "drapery", "description": "two panels"}],
        "notes": "Need a quote",
    })
    assert created.status_code == 200, created.text
    return auth, email, created.json()["id"]


def test_submit_stores_lead_and_quote_for_the_owner(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    auth, email, project_id = _signup_and_project(monkeypatch)
    submitted = client.post(f"/api/v1/intake/projects/{project_id}/submit", headers=auth)
    assert submitted.status_code == 200, submitted.text
    assert "photo_analysis" not in submitted.json()

    owner = client.get("/api/v1/intake/owner/submissions")
    assert owner.status_code == 200, owner.text
    rows = owner.json()["submissions"]
    match = next(row for row in rows if row["id"] == project_id)
    assert match["contact"]["email"] == email
    assert match["contact"]["name"] == "Rafael Designer"
    assert match["rooms"][0]["name"] == "Living Room"
    assert match["lead_id"] == 41
    assert match["quote_id"] == "q41"
    assert match["quote_number"] == "EST-41"
    assert match["status"] == "submitted"


def test_client_project_hides_owner_photo_analysis(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    auth, _email, project_id = _signup_and_project(monkeypatch)
    monkeypatch.setattr(
        handoff,
        "analyze_intake_image",
        lambda content, filename, content_type: {
            "filename": filename,
            "status": "ready",
            "overall_notes": "Two windows, existing rod.",
        },
    )
    handoff.run_owner_photo_analysis(project_id, b"jpeg-bytes", "room.jpg", "image/jpeg")

    client_view = client.get(f"/api/v1/intake/projects/{project_id}", headers=auth)
    assert client_view.status_code == 200
    assert "photo_analysis" not in client_view.json()

    owner = client.get("/api/v1/intake/owner/submissions")
    match = next(row for row in owner.json()["submissions"] if row["id"] == project_id)
    assert match["photo_analysis"][0]["overall_notes"] == "Two windows, existing rod."


def test_fabric_files_save_with_the_item(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    _auth, _email, project_id = _signup_and_project(monkeypatch)
    saved = client.put(
        f"/api/v1/fabrics/intake-project/{project_id}/fabrics",
        json={"fabrics": [{
            "scope": "item",
            "room_name": "Living Room",
            "item_name": "Drapery",
            "fabric_preference": "picked_out",
            "fabric_name": "Cuaderno",
            "swatch_photo_path": f"/intake_uploads/{project_id}/swatch.heic",
            "swatch_files": [
                {"path": f"/intake_uploads/{project_id}/swatch.heic", "original_name": "IMG.HEIC"},
                {"path": f"/intake_uploads/{project_id}/spec.pdf", "original_name": "spec.pdf"},
            ],
        }]},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert len(body) == 1
    assert body[0]["swatch_files"][0]["original_name"] == "IMG.HEIC"
    again = client.put(
        f"/api/v1/fabrics/intake-project/{project_id}/fabrics",
        json={"fabrics": [{
            "scope": "item",
            "item_name": "Drapery",
            "fabric_preference": "com",
            "swatch_photo_path": f"/intake_uploads/{project_id}/swatch.heic",
            "swatch_files": [{"path": f"/intake_uploads/{project_id}/swatch.heic", "original_name": "IMG.HEIC"}],
        }]},
    )
    assert again.status_code == 200
    assert len(again.json()) == 1

    owner = client.get("/api/v1/intake/owner/submissions")
    match = next(row for row in owner.json()["submissions"] if row["id"] == project_id)
    assert match["fabrics"][0]["fabric_preference"] == "com"
    assert match["fabrics"][0]["swatch_files"][0]["original_name"] == "IMG.HEIC"


def test_owner_notice_is_only_the_workroom_mailbox(monkeypatch):
    sent = {}

    async def fake_send(to, subject, html):
        sent["to"] = to
        sent["subject"] = subject
        sent["html"] = html
        return True

    async def fake_submit(body):
        assert body.email == "designer@example.com"
        assert body.capture_surface == "luxeforge"
        assert body.consent_contact is True
        return {"lead_id": 9, "customer_id": "c9"}

    def fake_quote(data):
        assert data["customer_email"] == "designer@example.com"
        assert data["status"] if "status" in data else "draft"
        assert data["line_items"][0]["category"] == "intake_pending"
        return {"id": "quote9", "quote_number": "EST-9", "status": "draft"}

    monkeypatch.setattr("app.services.email.sender.send_email", fake_send)
    monkeypatch.setattr("app.services.workroom_lead_intake.submit_intake", fake_submit)
    monkeypatch.setattr("app.services.quote_service.create_quote", fake_quote)

    result = asyncio.run(handoff.handoff_submitted_intake(
        {
            "id": "p1",
            "intake_code": "INT-2026-0007",
            "name": "Johnson Residence",
            "treatment": "drapery",
            "notes": "two panels",
            "rooms": [{"name": "Living Room", "treatment": "drapery"}],
            "photos": [],
        },
        {"name": "Designer", "email": "designer@example.com", "phone": "555", "company": "North"},
        [],
    ))
    assert sent["to"] == "workroom@empirebox.store"
    assert sent["to"] != "designer@example.com"
    assert "not sent to the customer" in sent["html"]
    assert "draft waiting" in sent["html"]
    assert result["lead_id"] == 9
    assert result["quote_id"] == "quote9"
    assert result["notice"]["customer_emailed"] is False


def test_public_luxe_host_cannot_list_intakes():
    from app.security.luxe_public_edge import is_public_luxe_path_allowed

    assert not is_public_luxe_path_allowed("GET", "/api/v1/intake/owner/submissions")
    denied = TestClient(app, base_url="https://luxe.empirebox.store").get(
        "/api/v1/intake/owner/submissions"
    )
    assert denied.status_code == 401
    assert denied.json()["error"] == "luxe_public_edge_denied"
