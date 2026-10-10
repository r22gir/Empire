"""Unit tests for PDF/document attachment routing (image-availability-check bug)."""
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
    # Force data_root re-read via the helper (it reads env each call)
    assert max_router._attachment_upload_path("estimate-test.pdf") == pdf
    assert max_router._image_upload_path("estimate-test.pdf") == pdf


def test_attachment_upload_path_still_finds_images(monkeypatch, tmp_path):
    max_router = importlib.import_module("app.routers.max.router")

    data_dir = tmp_path / "data"
    images = data_dir / "uploads" / "images"
    images.mkdir(parents=True)
    img = images / "photo.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data_dir))
    assert max_router._attachment_upload_path("photo.png") == img


def test_unavailable_doc_message_is_plain(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    msg, model, skill = max_router._unavailable_attachment_response("missing.pdf")
    assert "IMAGE_NOT_AVAILABLE" not in msg
    assert "couldn't read" in msg.lower()
    assert model == "attachment-availability-check"
    assert skill == "attachment_availability_check"

    msg_i, model_i, skill_i = max_router._unavailable_attachment_response("missing.jpg")
    assert msg_i == "IMAGE_NOT_AVAILABLE"
    assert model_i == "image-availability-check"


def test_process_attachment_extracts_pdf_text(tmp_path, monkeypatch):
    from app.services.max.ai_router import AIRouter

    docs = tmp_path / "uploads" / "documents"
    docs.mkdir(parents=True)
    pdf = docs / "fake-estimate.pdf"
    # Minimal real-enough PDF with text via reportlab if available, else write + pdftotext may fail
    # Prefer generating with a simple PDF that pdftotext can read.
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf))
        c.drawString(72, 720, "FAKE ESTIMATE TOTAL: $12,345.67")
        c.drawString(72, 700, "Client: Test Client LLC")
        c.save()
    except Exception:
        # Fallback: use subprocess to make a tiny text PDF via printf+enscript? skip if no reportlab
        pytest.skip("reportlab not available to build test PDF")

    router = AIRouter()
    router.upload_dirs = [tmp_path / "uploads"]
    image_path, text = router._process_attachment("fake-estimate.pdf")
    assert image_path is None
    assert text is not None
    assert "FAKE ESTIMATE TOTAL" in text or "12,345.67" in text
    assert "Contents of fake-estimate.pdf" in text


def test_process_attachment_plain_unsupported(tmp_path):
    from app.services.max.ai_router import AIRouter

    other = tmp_path / "uploads" / "other"
    other.mkdir(parents=True)
    blob = other / "mystery.bin"
    blob.write_bytes(b"\x00\x01\x02")

    router = AIRouter()
    router.upload_dirs = [tmp_path / "uploads"]
    image_path, text = router._process_attachment("mystery.bin")
    assert image_path is None
    assert text is not None
    assert "IMAGE_NOT_AVAILABLE" not in text
    assert "couldn't read" in text.lower()
