import importlib
import asyncio
import json

from starlette.requests import Request


def _json_request(payload: dict) -> Request:
    body = json.dumps(payload).encode()
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [(b"content-type", b"application/json")],
        },
        receive,
    )


def test_intake_to_quote_carries_project_fields(monkeypatch, tmp_path):
    from app.routers import intake_auth, quotes
    from app.services.max.response_quality_engine import QualityResult

    importlib.reload(intake_auth)
    importlib.reload(quotes)

    intake_db = tmp_path / "intake.db"
    uploads_dir = tmp_path / "intake_uploads"
    quotes_dir = tmp_path / "quotes"
    uploads_dir.mkdir()
    quotes_dir.mkdir()

    monkeypatch.setattr(intake_auth, "DB_PATH", str(intake_db))
    monkeypatch.setattr(intake_auth, "UPLOADS_DIR", str(uploads_dir))
    monkeypatch.setattr(intake_auth, "PHOTOS_DIR", str(tmp_path / "photos"))
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

    intake_auth.init_db()

    project_id = "project-1"
    user_id = "user-1"
    project_upload_dir = uploads_dir / project_id
    project_upload_dir.mkdir()
    (project_upload_dir / "window.jpg").write_bytes(b"fake-image")
    (project_upload_dir / "room.glb").write_bytes(b"fake-scan")

    conn = intake_auth.get_db()
    conn.execute(
        """INSERT INTO intake_users
           (id, name, email, phone, password_hash, company, role)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            "Ada Draper",
            "ada@example.com",
            "555-0111",
            "hash",
            "Ada Design",
            "designer",
        ),
    )
    conn.execute(
        """INSERT INTO intake_projects
           (id, user_id, intake_code, name, address, status, rooms, photos,
            scans, measurements, treatment, style, scope, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            project_id,
            user_id,
            "INT-2026-0001",
            "Living Room Drapery",
            "12 Window Way",
            "submitted",
            json.dumps([
                {
                    "name": "Den",
                    "treatment": "roman shade",
                    "description": "Inside mount",
                }
            ]),
            json.dumps([
                {
                    "filename": "window.jpg",
                    "original_name": "Window Before.jpg",
                    "path": f"/intake_uploads/{project_id}/window.jpg",
                    "uploaded_at": "2026-04-12T01:00:00",
                }
            ]),
            json.dumps([
                {
                    "filename": "room.glb",
                    "original_name": "Room Scan.glb",
                    "path": f"/intake_uploads/{project_id}/room.glb",
                    "uploaded_at": "2026-04-12T01:05:00",
                }
            ]),
            json.dumps([
                {
                    "room": "Living Room",
                    "width": 84,
                    "height": 96,
                    "notes": "Use blackout lining",
                }
            ]),
            "drapery",
            "modern",
            "two windows plus den shade",
            "Client prefers brass hardware",
        ),
    )
    conn.commit()
    conn.close()

    response = asyncio.run(
        intake_auth.convert_to_quote(_json_request({"business_unit": "workroom"}), project_id)
    )

    assert response["status"] == "created"
    assert response["intake_code"] == "INT-2026-0001"

    quote_path = quotes_dir / f"{response['quote_id']}.json"
    quote = json.loads(quote_path.read_text())

    assert quote["customer_name"] == "Ada Draper"
    assert quote["customer_email"] == "ada@example.com"
    assert quote["customer_phone"] == "555-0111"
    assert quote["customer_address"] == "12 Window Way"
    assert quote["business_unit"] == "workroom"
    assert quote["project_name"] == "Living Room Drapery"
    assert "INT-2026-0001" in quote["project_description"]
    assert "drapery" in quote["project_description"]
    assert "modern" in quote["project_description"]
    assert "two windows plus den shade" in quote["project_description"]
    assert quote["notes"] == "Client prefers brass hardware"
    assert quote["intake_project_id"] == project_id
    assert quote["intake_code"] == "INT-2026-0001"

    assert len(quote["rooms"]) == 2
    measured_window = quote["rooms"][0]["windows"][0]
    assert measured_window["name"] == "Living Room"
    assert measured_window["width"] == 84
    assert measured_window["height"] == 96
    assert measured_window["treatment_type"] == "drapery"
    assert measured_window["treatmentType"] == "drapery"
    assert measured_window["notes"] == "Use blackout lining"

    assert "Living Room" in quote["line_items"][0]["description"]
    assert "drapery" in quote["line_items"][0]["description"]
    copied_photo = (
        tmp_path
        / "photos"
        / "quote"
        / quote["id"]
        / quote["photos"][0]["filename"]
    )
    assert quote["photos"][0]["original_name"] == "Window Before.jpg"
    assert quote["photos"][0]["url"].startswith(f"/api/v1/photos/serve/quote/{quote['id']}/")
    assert copied_photo.exists()
    assert (copied_photo.with_suffix(copied_photo.suffix + ".meta.json")).exists()

    assert quote["scan_3d_files"][0]["filename"] == "room.glb"
    assert quote["scan_3d_files"][0]["original_name"] == "Room Scan.glb"
    assert quote["scan_3d_files"][0]["source"] == "intake"
    assert quote["scan_3d_files"][0]["intake_project_id"] == project_id
