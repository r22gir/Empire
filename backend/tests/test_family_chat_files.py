"""Chat upload open/read for family editions — accented names, spaces, parens."""
from __future__ import annotations

import io
import unicodedata
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.testclient import TestClient


ACCENTED_PDFS = (
    "MeEncontreUnArcoIris (1).pdf",
    "MeEncontréUnArcoIrisPropuestaSAGAen9libros.pdf",
    "EcosistemaAMP-MeEncontreUnArcoiris.pdf",
)


def _family(monkeypatch, tmp_path, edition: str = "amp"):
    root = tmp_path / edition
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    return root


def _client():
    from app.api.v1.files import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_accented_pdf_upload_opens_and_max_can_read(monkeypatch, tmp_path):
    root = _family(monkeypatch, tmp_path, "amp")
    client = _client()
    assert "/data" not in str(root)

    for name in ACCENTED_PDFS:
        payload = b"%PDF-1.4 " + name.encode("utf-8")
        res = client.post(
            "/api/v1/files/upload",
            files={"file": (name, io.BytesIO(payload), "application/pdf")},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "success"
        assert body["category"] == "documents"
        stored = body["filename"]
        on_disk = root / "uploads" / "documents" / stored
        assert on_disk.is_file()
        assert on_disk.read_bytes() == payload
        assert not str(on_disk).startswith("/data/")

        encoded = quote(stored, safe="")
        for url in (
            f"/api/v1/files/view/documents/{encoded}",
            f"/api/v1/files/view/images/{encoded}",
            f"/api/v1/files/view/{encoded}",
            f"/api/v1/files/documents/{quote(stored)}",
        ):
            opened = client.get(url)
            assert opened.status_code == 200, f"{url} -> {opened.status_code} {opened.text}"
            assert opened.content == payload

    from app.services.uploads.chat_uploads import resolve_uploaded_file
    from app.services.max.ai_router import AIRouter

    upload_root = root / "uploads"
    for name in ACCENTED_PDFS:
        found = resolve_uploaded_file(name, "images", roots=[upload_root])
        assert found is not None, name
        assert found.is_file()
        nfd = unicodedata.normalize("NFD", name)
        assert resolve_uploaded_file(nfd, roots=[upload_root]) == found
        assert resolve_uploaded_file(quote(name), roots=[upload_root]) == found

    router = AIRouter()
    router.upload_dirs = [upload_root]
    path, _text = router._process_attachment(ACCENTED_PDFS[0])
    assert path is None
    assert _text is not None
    assert ACCENTED_PDFS[0] in _text


def test_resolve_uploaded_file_does_not_touch_live_data(tmp_path):
    from app.services.uploads.chat_uploads import resolve_uploaded_file

    docs = tmp_path / "uploads" / "documents"
    docs.mkdir(parents=True)
    name = "MeEncontré Un Libro (2).pdf"
    target = docs / name
    target.write_bytes(b"%PDF-1.4 x")
    found = resolve_uploaded_file(quote(name, safe=""), "images", roots=[tmp_path / "uploads"])
    assert found == target
    assert "/data" not in str(found)
