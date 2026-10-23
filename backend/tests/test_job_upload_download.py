"""Job upload download route. Mock files only."""
import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app
from app.services.job_uploads import resolve_job_upload, safe_job_filename


def test_safe_filename_strips_traversal():
    assert safe_job_filename("../etc/passwd") == "passwd"
    assert safe_job_filename("..\\secret.pdf") == "secret.pdf"
    assert safe_job_filename("") != ""
    assert "/" not in safe_job_filename("a/b/c.pdf")


def test_resolve_job_upload_refuses_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    job_dir = tmp_path / "uploads" / "jobs" / "job-1"
    job_dir.mkdir(parents=True)
    (job_dir / "room.pdf").write_bytes(b"%PDF-1.4 mock")
    (tmp_path / "secret.txt").write_text("nope")
    assert resolve_job_upload("job-1", "room.pdf") == job_dir / "room.pdf"
    assert resolve_job_upload("job-1", "../secret.txt") is None
    assert resolve_job_upload("../job-1", "room.pdf") is None
    assert resolve_job_upload("job-1", "missing.pdf") is None


def test_download_route_serves_upload_and_404s_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO customers (id, name) VALUES ('cust-up','Upload Client')")
    client = TestClient(app)
    created = client.post("/api/v1/jobs", json={
        "title": "Upload job",
        "customer_id": "cust-up",
        "client_name": "Upload Client",
    })
    assert created.status_code == 200, created.text
    job_id = created.json()["job"]["id"]
    upload = client.post(
        f"/api/v1/jobs/{job_id}/upload",
        files={"file": ("site-photo.pdf", io.BytesIO(b"%PDF-1.4 mock upload"), "application/pdf")},
        data={"document_type": "photo"},
    )
    assert upload.status_code == 200, upload.text
    doc = upload.json()["document"]
    url = doc["url"]
    assert url == f"/api/v1/files/download/jobs/{job_id}/site-photo.pdf"
    saved = Path(tmp_path) / "uploads" / "jobs" / job_id / "site-photo.pdf"
    assert saved.is_file()
    got = client.get(url)
    assert got.status_code == 200
    assert got.content.startswith(b"%PDF")
    alt = client.get(f"/api/v1/jobs/{job_id}/files/site-photo.pdf")
    assert alt.status_code == 200
    bad = client.get(f"/api/v1/files/download/jobs/{job_id}/%2e%2e/secret.txt")
    assert bad.status_code in {400, 404, 422}
    missing = client.get(f"/api/v1/files/download/jobs/{job_id}/no-such.pdf")
    assert missing.status_code == 404
