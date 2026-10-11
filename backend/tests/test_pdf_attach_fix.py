"""Unit tests for PDF/document attachment routing (family-edition scoped)."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_attachment_upload_path_finds_pdf_in_documents(monkeypatch, tmp_path):
    max_router = importlib.import_module("app.routers.max.router")

    data_dir = tmp_path / "data"
    docs = data_dir / "uploads" / "documents"
    docs.mkdir(parents=True)
    pdf = docs / "estimate-test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data_dir))

    assert max_router._attachment_upload_path("estimate-test.pdf") == pdf
    assert max_router._image_upload_path("estimate-test.pdf") == pdf


def test_attachment_upload_path_ignores_workroom_uploads(monkeypatch, tmp_path):
    """Family editions must not resolve Rafael/Workroom upload trees."""
    max_router = importlib.import_module("app.routers.max.router")

    data_dir = tmp_path / "edition-data"
    (data_dir / "uploads" / "documents").mkdir(parents=True)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data_dir))

    # Even if a same-named file exists under empire-repo, family lookup is data_root only.
    assert max_router._attachment_upload_path("EST-2026-297-phase1-v26-FINAL-nobump_20261005_174641.pdf") is None


def test_unavailable_doc_message_is_plain():
    max_router = importlib.import_module("app.routers.max.router")
    msg, model, skill = max_router._unavailable_attachment_response("missing.pdf")
    assert "IMAGE_NOT_AVAILABLE" not in msg
    assert "couldn't read" in msg.lower()
    assert model == "attachment-availability-check"

    msg_i, model_i, _ = max_router._unavailable_attachment_response("missing.jpg")
    assert msg_i == "IMAGE_NOT_AVAILABLE"
    assert model_i == "image-availability-check"


def test_process_attachment_extracts_pdf_text(tmp_path):
    from app.services.max.ai_router import AIRouter

    docs = tmp_path / "uploads" / "documents"
    docs.mkdir(parents=True)
    pdf = docs / "fake-estimate.pdf"
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf))
        c.drawString(72, 720, "FAKE ESTIMATE TOTAL: $12,345.67")
        c.drawString(72, 700, "Client: Test Client LLC")
        c.save()
    except Exception:
        pytest.skip("reportlab not available to build test PDF")

    router = AIRouter()
    router.upload_dirs = [tmp_path / "uploads"]
    image_path, text = router._process_attachment("fake-estimate.pdf")
    assert image_path is None
    assert text is not None
    assert "FAKE ESTIMATE TOTAL" in text or "12,345.67" in text
    assert "Contents of fake-estimate.pdf" in text


def test_ai_router_upload_dirs_are_edition_only(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition"))
    from app.services.max.ai_router import AIRouter
    router = AIRouter()
    assert len(router.upload_dirs) == 1
    assert router.upload_dirs[0] == (tmp_path / "edition" / "uploads")
    joined = " ".join(str(p) for p in router.upload_dirs)
    assert "empire-repo" not in joined
    assert "empire-data" not in joined
