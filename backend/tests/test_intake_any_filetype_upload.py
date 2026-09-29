"""LuxeForge intake uploads accept any file type.

Item 1 of the drawing-standard dispatch: designers must be able to
attach PDFs, CAD, 3D scans, docs, zip, video — not just images. Two
things had to change together:

  1. The upload endpoints (`/projects/{id}/photos`, `/projects/{id}/scans`)
     must accept arbitrary bytes, enforce a size cap, and never trust the
     client filename for the on-disk path (only a sanitized extension).
  2. The `/intake_uploads/...` serving route must never let an uploaded
     HTML/SVG file execute/render inline — everything but a small raster
     image allowlist downloads via Content-Disposition: attachment.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import intake_auth
from app.services.uploads import safe_file_serve


client = TestClient(app)


def _configure_temp_intake(monkeypatch, tmp_path):
    intake_db = tmp_path / "intake.db"
    uploads_dir = tmp_path / "intake_uploads"
    photos_dir = tmp_path / "photos"
    uploads_dir.mkdir()
    photos_dir.mkdir()
    monkeypatch.setattr(intake_auth, "DB_PATH", str(intake_db))
    monkeypatch.setattr(intake_auth, "UPLOADS_DIR", str(uploads_dir))
    monkeypatch.setattr(intake_auth, "PHOTOS_DIR", str(photos_dir))
    intake_auth.init_db()
    return uploads_dir


def _signup_and_create_project(email: str) -> tuple[dict, str]:
    signup = client.post(
        "/api/v1/intake/signup",
        json={
            "name": "Designer",
            "email": email,
            "password": "secret123",
            "role": "designer",
            "business": "workroom",
        },
    )
    assert signup.status_code == 200, signup.text
    token = signup.json()["token"]
    auth = {"Authorization": f"Bearer {token}"}

    proj = client.post(
        "/api/v1/intake/projects",
        headers=auth,
        json={"name": "Any-Filetype Project", "business": "workroom"},
    )
    assert proj.status_code == 200, proj.text
    return auth, proj.json()["id"]


def test_scans_endpoint_accepts_cad_and_pdf_files(monkeypatch, tmp_path):
    """Non-image files (CAD, PDF) upload successfully and report size."""
    _configure_temp_intake(monkeypatch, tmp_path)
    auth, project_id = _signup_and_create_project(f"designer-{uuid.uuid4().hex[:8]}@example.com")

    for filename, content_type, payload in [
        ("floorplan.dwg", "application/octet-stream", b"FAKE-DWG-BYTES" * 10),
        ("spec.pdf", "application/pdf", b"%PDF-1.4 fake pdf content"),
        ("scan.glb", "model/gltf-binary", b"glTF" + b"\x00" * 20),
    ]:
        resp = client.post(
            f"/api/v1/intake/projects/{project_id}/scans",
            headers=auth,
            files={"file": (filename, payload, content_type)},
        )
        assert resp.status_code == 200, f"{filename}: {resp.text}"
        assert resp.json()["filename"]

    proj = client.get(f"/api/v1/intake/projects/{project_id}", headers=auth)
    scans = proj.json()["scans"]
    assert len(scans) == 3
    for scan, (filename, _, payload) in zip(scans, [
        ("floorplan.dwg", None, b"FAKE-DWG-BYTES" * 10),
        ("spec.pdf", None, b"%PDF-1.4 fake pdf content"),
        ("scan.glb", None, b"glTF" + b"\x00" * 20),
    ]):
        assert scan["original_name"] == filename
        assert scan["size"] == len(payload)


def test_photos_endpoint_accepts_non_image_files_too(monkeypatch, tmp_path):
    """The image-labeled /photos endpoint must not reject non-image bytes
    now that the frontend no longer restricts uploads to accept=image/*."""
    _configure_temp_intake(monkeypatch, tmp_path)
    auth, project_id = _signup_and_create_project(f"designer-{uuid.uuid4().hex[:8]}@example.com")

    resp = client.post(
        f"/api/v1/intake/projects/{project_id}/photos",
        headers=auth,
        files={"file": ("notes.docx", b"fake docx bytes", "application/vnd.openxmlformats")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filename"].endswith(".docx")


def test_upload_rejects_oversized_file(monkeypatch, tmp_path):
    """Size cap is enforced (413) instead of silently accepting anything."""
    _configure_temp_intake(monkeypatch, tmp_path)
    auth, project_id = _signup_and_create_project(f"designer-{uuid.uuid4().hex[:8]}@example.com")

    monkeypatch.setattr(
        intake_auth, "enforce_upload_size_limit",
        lambda content: safe_file_serve.enforce_upload_size_limit(content, limit=100),
    )

    resp = client.post(
        f"/api/v1/intake/projects/{project_id}/scans",
        headers=auth,
        files={"file": ("huge.zip", b"x" * 1000, "application/zip")},
    )
    assert resp.status_code == 413


def test_uploaded_filename_is_sanitized_no_path_traversal(monkeypatch, tmp_path):
    """The on-disk filename is always a fresh UUID + sanitized extension —
    a hostile `filename` in the multipart body can't escape the project
    upload directory."""
    uploads_dir = _configure_temp_intake(monkeypatch, tmp_path)
    auth, project_id = _signup_and_create_project(f"designer-{uuid.uuid4().hex[:8]}@example.com")

    resp = client.post(
        f"/api/v1/intake/projects/{project_id}/scans",
        headers=auth,
        files={"file": ("../../../../etc/passwd.dxf", b"payload", "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    stored_filename = resp.json()["filename"]
    assert "/" not in stored_filename and ".." not in stored_filename
    assert stored_filename.endswith(".dxf")

    stored_path = uploads_dir / project_id / stored_filename
    assert stored_path.exists()
    # Nothing escaped the project directory
    assert not (tmp_path / "etc").exists()


@pytest.mark.parametrize("filename,expected_ext", [
    ("Report.PDF", ".pdf"),
    ("model.STL", ".stl"),
    ("weird`;rm -rf`.txt", ".txt"),
    ("no_extension", ".bin"),
])
def test_safe_extension_sanitizes_and_lowercases(filename, expected_ext):
    assert safe_file_serve.safe_extension(filename, default=".bin") == expected_ext


def test_serve_route_forces_attachment_for_non_image(monkeypatch, tmp_path):
    """Hitting the public /intake_uploads/... URL for a non-image upload
    (including a designer-uploaded .html) must download, never render."""
    uploads_dir = _configure_temp_intake(monkeypatch, tmp_path)
    auth, project_id = _signup_and_create_project(f"designer-{uuid.uuid4().hex[:8]}@example.com")

    resp = client.post(
        f"/api/v1/intake/projects/{project_id}/scans",
        headers=auth,
        files={"file": ("evil.html", b"<script>alert(1)</script>", "text/html")},
    )
    assert resp.status_code == 200, resp.text
    scan_path = resp.json()["filename"]

    serve_resp = client.get(f"/intake_uploads/{project_id}/{scan_path}")
    assert serve_resp.status_code == 200
    assert serve_resp.headers["content-type"].startswith("application/octet-stream")
    assert "attachment" in serve_resp.headers.get("content-disposition", "")
    assert serve_resp.headers.get("x-content-type-options") == "nosniff"


def test_serve_route_renders_image_inline(monkeypatch, tmp_path):
    """A real image upload still previews inline (no attachment header)."""
    _configure_temp_intake(monkeypatch, tmp_path)
    auth, project_id = _signup_and_create_project(f"designer-{uuid.uuid4().hex[:8]}@example.com")

    resp = client.post(
        f"/api/v1/intake/projects/{project_id}/photos",
        headers=auth,
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\nfakepngbytes", "image/png")},
    )
    assert resp.status_code == 200, resp.text
    photo_path = resp.json()["filename"]

    serve_resp = client.get(f"/intake_uploads/{project_id}/{photo_path}")
    assert serve_resp.status_code == 200
    assert serve_resp.headers["content-type"] == "image/png"
    assert "attachment" not in serve_resp.headers.get("content-disposition", "")


def test_serve_route_blocks_path_traversal():
    resp = client.get("/intake_uploads/..%2f..%2f..%2fetc%2fpasswd")
    assert resp.status_code == 404
