"""LuxeForge submit lands in the normal Workroom Quotes list."""

import asyncio
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.routers import fabrics, intake_auth
from app.services import luxeforge_intake_handoff as handoff
from app.services.quote_service import create_quote, get_quote, list_quotes, set_quote_test_flag


client = TestClient(app)


def _configure_files(monkeypatch, tmp_path):
    uploads = tmp_path / "uploads"
    photos = tmp_path / "photos"
    uploads.mkdir()
    photos.mkdir()
    monkeypatch.setattr(intake_auth, "UPLOADS_DIR", str(uploads))
    monkeypatch.setattr(intake_auth, "PHOTOS_DIR", str(photos))
    intake_auth.init_db()
    fabrics._init_intake_fabrics_table()
    return uploads, photos


def _designer(monkeypatch, *, mock_handoff: bool):
    if mock_handoff:
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


def test_submit_shows_in_workroom_quotes_with_fabric_and_photos(monkeypatch, tmp_path):
    uploads, photos = _configure_files(monkeypatch, tmp_path)
    sent = {}

    async def fake_send(to, subject, html):
        sent["to"] = to
        sent["html"] = html
        return True

    async def fake_submit(body):
        assert body.email
        assert body.capture_surface == "luxeforge"
        assert body.consent_contact is True
        return {"lead_id": 41, "customer_id": "cust-41"}

    monkeypatch.setattr("app.services.email.sender.send_email", fake_send)
    monkeypatch.setattr("app.services.workroom_lead_intake.submit_intake", fake_submit)
    monkeypatch.setattr(
        handoff,
        "analyze_intake_image",
        lambda content, filename, content_type: {
            "filename": filename,
            "status": "ready",
            "overall_notes": "Two windows, existing rod.",
        },
    )

    auth, email, project_id = _designer(monkeypatch, mock_handoff=False)
    project_dir = uploads / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "swatch.heic").write_bytes(b"heic-bytes")
    (project_dir / "spec.pdf").write_bytes(b"pdf-bytes")

    uploaded = client.post(
        f"/api/v1/intake/projects/{project_id}/photos",
        headers=auth,
        files={"file": ("room.jpg", b"\xff\xd8\xff jpeg", "image/jpeg")},
    )
    assert uploaded.status_code == 200, uploaded.text
    photo_name = uploaded.json()["filename"]

    saved = client.put(
        f"/api/v1/fabrics/intake-project/{project_id}/fabrics",
        json={"fabrics": [{
            "scope": "item",
            "room_name": "Living Room",
            "item_name": "Drapery",
            "fabric_preference": "picked_out",
            "fabric_name": "Cuaderno",
            "client_notes": "ivory ground",
            "swatch_photo_path": f"/intake_uploads/{project_id}/swatch.heic",
            "swatch_files": [
                {"path": f"/intake_uploads/{project_id}/swatch.heic", "original_name": "IMG.HEIC"},
                {"path": f"/intake_uploads/{project_id}/spec.pdf", "original_name": "spec.pdf"},
            ],
        }]},
    )
    assert saved.status_code == 200, saved.text

    handoff.run_owner_photo_analysis(project_id, b"jpeg-bytes", "room.jpg", "image/jpeg")
    submitted = client.post(f"/api/v1/intake/projects/{project_id}/submit", headers=auth)
    assert submitted.status_code == 200, submitted.text
    assert "photo_analysis" not in submitted.json()

    conn = intake_auth.get_db()
    stored = conn.execute(
        "SELECT lead_id, quote_id, quote_number, status, photo_analysis FROM intake_projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    conn.close()
    assert stored["status"] == "submitted"
    assert stored["lead_id"] == 41
    assert stored["quote_id"]
    assert "Two windows, existing rod." in (stored["photo_analysis"] or "")

    listed = list_quotes(include_test=False, business_unit="workroom")
    match = next(row for row in listed["quotes"] if row["id"] == stored["quote_id"])
    assert match["status"] == "draft"
    assert int(match["is_test"] or 0) == 0
    assert match["customer_email"] == email
    assert "Cuaderno" in (match["notes"] or "")
    assert "spec.pdf" in (match["notes"] or "")
    assert "Two windows, existing rod." in (match["notes"] or "")
    assert "Owner only" in (match["notes"] or "")

    full = get_quote(stored["quote_id"])
    descriptions = " ".join(item["description"] for item in full["line_items"])
    assert "Cuaderno" in descriptions
    assert "ivory ground" in descriptions
    assert all(item["category"] == "intake_pending" for item in full["line_items"])
    originals = {photo.get("original_name") for photo in (full["photos"] or [])}
    assert "room.jpg" in originals or photo_name in {photo.get("filename") for photo in full["photos"]}
    assert any(str(photo.get("filename", "")).endswith("swatch.heic") or photo.get("original_name") == "IMG.HEIC" for photo in full["photos"])
    assert "spec.pdf" not in originals
    copied = list((photos / "quote" / stored["quote_id"]).glob("intake_*"))
    assert copied
    assert any(path.name.endswith("swatch.heic") for path in copied)
    assert any(path.name.endswith(photo_name) for path in copied)

    hidden = create_quote({
        "customer_name": "Hidden Filter Check",
        "business_unit": "workroom",
        "project_name": "flagged",
        "line_items": [{
            "description": "hidden",
            "quantity": 1,
            "unit": "ea",
            "rate": 0,
            "category": "intake_pending",
        }],
    })
    set_quote_test_flag(hidden["id"], True, changed_by="test")
    visible_ids = {row["id"] for row in list_quotes(include_test=False, business_unit="workroom")["quotes"]}
    assert stored["quote_id"] in visible_ids
    assert hidden["id"] not in visible_ids

    handoff.run_owner_photo_analysis(project_id, b"jpeg-bytes", "later.jpg", "image/jpeg")
    refreshed = get_quote(stored["quote_id"])
    assert "later.jpg" in (refreshed["notes"] or "")
    client_view = client.get(f"/api/v1/intake/projects/{project_id}", headers=auth)
    assert "photo_analysis" not in client_view.json()

    assert sent["to"] == "workroom@empirebox.store"
    assert sent["to"] != email
    assert "LuxeForge Intakes" not in sent["html"]
    assert "Quotes" in sent["html"]


def test_client_project_hides_owner_photo_analysis(monkeypatch, tmp_path):
    _configure_files(monkeypatch, tmp_path)
    auth, _email, project_id = _designer(monkeypatch, mock_handoff=True)
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

    conn = intake_auth.get_db()
    row = conn.execute(
        "SELECT photo_analysis FROM intake_projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    conn.close()
    assert "Two windows, existing rod." in row["photo_analysis"]


def test_fabric_files_save_with_the_item(monkeypatch, tmp_path):
    _configure_files(monkeypatch, tmp_path)
    _auth, _email, project_id = _designer(monkeypatch, mock_handoff=True)
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
    assert again.json()[0]["fabric_preference"] == "com"


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
        assert data["business_unit"] == "workroom"
        assert data["line_items"][0]["category"] == "intake_pending"
        assert "Not priced and not sent" in data["notes"]
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
    assert "LuxeForge Intakes" not in sent["html"]
    assert "Workroom" in sent["html"] and "Quotes" in sent["html"]
    assert result["lead_id"] == 9
    assert result["quote_id"] == "quote9"
    assert result["notice"]["customer_emailed"] is False
    assert result["quote_error"] is None


def test_public_luxe_host_cannot_read_intake_owner_paths():
    from app.security.luxe_public_edge import is_public_luxe_path_allowed

    assert not is_public_luxe_path_allowed("GET", "/api/v1/intake/owner/submissions")
    denied = TestClient(app, base_url="https://luxe.empirebox.store").get(
        "/api/v1/intake/owner/submissions"
    )
    assert denied.status_code == 401
    assert denied.json()["error"] == "luxe_public_edge_denied"
    paths = [getattr(route, "path", "") for route in app.routes]
    assert not any(path.endswith("/owner/submissions") for path in paths)
