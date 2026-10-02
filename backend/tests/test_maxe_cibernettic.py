"""Max-e has two businesses. Cibernettic documents stay drafts. Drive is per user."""
from __future__ import annotations

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
    exported = files.nightly_export()
    assert exported["uses_shared_founder_account"] is False
    assert Path(exported["working_copy"]).is_dir()
    assert exported["uploads"][0]["uploaded"] is False

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
