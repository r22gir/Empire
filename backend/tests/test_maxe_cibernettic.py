"""Max-e has two businesses. Cibernettic documents stay drafts. Drive is per user."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CONSTRUCTION_DB", str(tmp_path / "construction.db"))
    monkeypatch.setenv("VOICE_DRAFTS_DB", str(tmp_path / "voice_drafts.db"))
    monkeypatch.setenv("PHOTOS_DB", str(tmp_path / "photos.db"))
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)


def test_maxe_starts_with_amp_and_cibernettic(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.edition import edition_manifest, greeting
    from app.services.amp_businesses import _connect, ensure_maxe_businesses

    rows = ensure_maxe_businesses()
    slugs = [row["slug"] for row in rows]
    assert slugs == ["amp", "cibernettic"]
    cib = rows[1]
    assert "NIT" in cib["description"]
    assert "no guarda" in cib["description"]
    blob = Path(tmp_path, "businesses", "cibernettic", "business.json").read_text(encoding="utf-8")
    assert "900" not in blob
    conn = _connect("cibernettic")
    prices = [row["price"] for row in conn.execute("SELECT price FROM service_categories")]
    conn.close()
    assert prices
    assert all(price is None for price in prices)
    manifest = edition_manifest()
    assert [item["slug"] for item in manifest["businesses"]] == ["amp", "cibernettic"]
    assert manifest["product"]["also_known_as"] == "El Portal de la Alegría"
    assert greeting("es").startswith("Hola, soy Max-e")
    assert "Cibernettic" in greeting("es")
    assert "AMP" in greeting("es")


def test_cibernettic_quote_hours_usd_and_neutral_slots(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.voice_doc.pipeline import ingest_transcript
    from app.services.voice_doc.store import get_draft
    from app.services.voice_doc.templates import WATERMARK, it_skeleton_body

    view = ingest_transcript(
        "Cotiza una auditoría de ciberseguridad para Empresa Demo, 40 horas, 80 dolares la hora. listo",
        channel="web",
        edition="amp",
    )
    assert view["doc_type"] == "quote"
    assert view["fields"]["business"] == "cibernettic"
    assert view["fields"]["service_line"] == "audit"
    assert view["fields"]["billing"] == "hours"
    assert view["fields"]["currency"] == "USD"
    assert view["fields"]["price"] == 3200
    assert view["draft"]["sent"] is False
    draft = get_draft(view["draft"]["id"])
    titles = [item["title"] for item in draft["payload"]["attachments"]]
    assert "Acuerdo de confidencialidad" in titles
    assert "Contrato de servicios / SLA" in titles
    assert all(WATERMARK in item["body"] for item in draft["payload"]["attachments"])
    skeleton = it_skeleton_body("Acuerdo de confidencialidad")
    assert "se obliga" not in skeleton.lower()
    assert "GAC" not in skeleton
    assert "{{nit}}" in skeleton
    copies = list(Path(tmp_path, "working").rglob("*.pdf"))
    assert copies
    assert copies[0].read_bytes().startswith(b"%PDF")


def test_currency_and_business_are_choices_when_unsaid(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.voice_doc.pipeline import ingest_transcript

    view = ingest_transcript(
        "Necesito una factura para Empresa Demo.",
        channel="web",
        edition="amp",
    )
    assert view["options"]["kind"] == "business"
    assert [choice["id"] for choice in view["options"]["choices"]] == ["business_amp", "business_cibernettic"]
    picked = ingest_transcript(
        "",
        session_id=view["session_id"],
        choice_id="business_cibernettic",
        channel="web",
        edition="amp",
    )
    assert picked["fields"]["business"] == "cibernettic"
    assert picked["options"]["kind"] == "billing"


def test_drive_is_per_user_and_photos_are_picked_only(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services import instance_files as files

    assert "GMAIL_TOKEN_PATH" not in Path(files.__file__).read_text(encoding="utf-8")
    status = files.oauth_start("juan@example.com", "https://maxe.example/archivo")
    assert status["ok"] is False
    assert status["connected"] is False
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret")
    started = files.oauth_start("juan@example.com", "https://maxe.example/archivo")
    assert started["ok"] is True
    assert "client_secret" not in started["url"]
    finished = files.oauth_finish(
        "juan@example.com",
        "code",
        started["state"],
        lambda _code: {"access_token": "user-token", "refresh_token": "user-refresh"},
    )
    assert finished["connected"] is True
    assert finished["uses_shared_founder_account"] is False
    token = Path(files.token_path("juan@example.com"))
    assert str(tmp_path) in str(token)
    assert "gmail" not in str(token).lower()
    files.remember_user("juan@example.com")
    (tmp_path / "construction.db").write_bytes(b"sqlite")

    def _offline(*_args, **_kwargs):
        raise files.FileArchiveError("No hay red hacia Google para este usuario")

    monkeypatch.setattr(files, "google_request", _offline)
    exported = files.nightly_export()
    assert exported["uses_shared_founder_account"] is False
    assert Path(exported["working_copy"]).is_dir()
    assert exported["uploads"][0]["uploaded"] is False
    assert exported["uploads"][0]["drive_path"].startswith("Max-e/")

    files.save_photo(data=b"a", filename="cimentacion.jpg", project="Portal", lot="12", stage="cimentacion", source="upload")
    files.save_photo(data=b"b", filename="techo.jpg", project="Portal", lot="12", stage="techo", source="chat")
    timeline = files.photo_timeline("Portal")
    assert [item["stage"] for item in timeline] == ["cimentacion", "techo"]
    with pytest.raises(files.FileArchiveError):
        files.import_picked(user_id="juan@example.com", session_id="", project="Portal", fetch_items=lambda *_: [])
    saved = files.import_picked(
        user_id="juan@example.com",
        session_id="sess-1",
        project="Portal",
        lot="12",
        stage="obra",
        fetch_items=lambda session_id, _token: [
            {"id": "picked", "filename": "ok.jpg", "bytes": b"ok", "session_id": session_id},
            {"id": "other", "filename": "no.jpg", "bytes": b"no", "session_id": "sess-other"},
        ],
    )
    assert len(saved) == 1
    assert saved[0]["source"] == "google_photos_picker"
    refused = files.picker_session("nadie@example.com", lambda *_: {"id": "x"})
    assert refused["ok"] is False


def _connect_user(files, user_id: str):
    started = files.oauth_start(user_id, "https://example.test/archivo")
    files.oauth_finish(
        user_id,
        "code",
        started["state"],
        lambda _code: {"access_token": "user-token", "refresh_token": "user-refresh"},
    )
    files.remember_user(user_id)


def test_both_editions_upload_to_their_own_drive_folder(monkeypatch, tmp_path):
    from app.services import instance_files as files
    from app.services.voice_doc.pipeline import ingest_transcript

    calls = []

    def _fake(method, url, token="", body=None, headers=None):
        calls.append({"method": method, "url": url, "token": token, "body": body or b""})
        assert "gmail" not in url.lower()
        assert token in {"", "user-token"}
        if "oauth2.googleapis.com/token" in url:
            return 200, b'{"access_token":"user-token","refresh_token":"user-refresh"}'
        if "uploadType=multipart" in url:
            return 200, b'{"id":"file-1","name":"construction.db"}'
        if method == "GET" and "drive/v3/files" in url:
            return 200, b'{"files":[]}'
        if method == "POST" and url.endswith("/drive/v3/files"):
            return 200, b'{"id":"fld-1"}'
        if "photospicker.googleapis.com/v1/mediaItems" in url:
            assert "sessionId=sess-1" in url
            assert "albums" not in url
            return 200, json.dumps({
                "mediaItems": [{
                    "id": "picked",
                    "mediaFile": {"baseUrl": "https://photos.example/picked", "filename": "obra.jpg"},
                }],
            }).encode()
        if url == "https://photos.example/picked":
            return 200, b"jpeg"
        if url == files.PICKER_SESSION_URL:
            return 200, b'{"id":"sess-1","pickerUri":"https://photos.google.com/picker/sess-1"}'
        raise AssertionError(url)

    for edition, folder in (("amp", "Max-e"), ("maxine", "Maxine")):
        root = tmp_path / edition
        root.mkdir()
        monkeypatch.setenv("EMPIRE_EDITION", edition)
        monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
        monkeypatch.setenv("CONSTRUCTION_DB", str(root / "construction.db"))
        monkeypatch.setenv("VOICE_DRAFTS_DB", str(root / "voice_drafts.db"))
        monkeypatch.setenv("PHOTOS_DB", str(root / "photos.db"))
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client")
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret")
        monkeypatch.setattr(files, "google_request", _fake)
        calls.clear()
        assert files.drive_path(business="obra", project="Portal", client="Camilo").startswith(f"{folder}/obra/Portal/Camilo/")
        _connect_user(files, "owner@example.com")
        (root / "construction.db").write_bytes(b"sqlite")
        exported = files.nightly_export()
        assert exported["uploads"][0]["uploaded"] is True
        assert exported["uploads"][0]["drive_path"].startswith(f"{folder}/")
        assert exported["uses_shared_founder_account"] is False
        bodies = b"".join(call["body"] if isinstance(call["body"], bytes) else b"" for call in calls)
        assert folder.encode() in bodies
        assert b"client_secret" not in bodies
        opened = files.picker_session("owner@example.com", files.open_picker)
        assert opened["ok"] is True
        assert opened["picked_only"] is True
        picked = files.import_picked(
            user_id="owner@example.com",
            session_id="sess-1",
            project="Portal",
            lot="12",
            stage="cimentacion",
            fetch_items=files.fetch_picked_items,
        )
        assert len(picked) == 1
        assert picked[0]["source"] == "google_photos_picker"
        urls = [call["url"] for call in calls]
        assert any(call.startswith(files.PICKER_ITEMS_URL) for call in urls)
        assert not any("library" in call for call in urls)

    exchanged = files.exchange_auth_code("auth-code", "https://example.test/archivo")
    assert exchanged["access_token"] == "user-token"
    token_call = calls[-1]
    assert token_call["url"] == "https://oauth2.googleapis.com/token"
    assert b"client_secret" in token_call["body"]
    assert token_call["token"] == ""

    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "maxine"))
    note = ingest_transcript("Notas de la visita de hoy. listo", channel="web", edition="maxine")
    assert note["draft"]["sent"] is False
    copies = list((tmp_path / "maxine" / "working").rglob("*.pdf"))
    assert copies
    assert any("Maxine" in str(path) for path in copies)
