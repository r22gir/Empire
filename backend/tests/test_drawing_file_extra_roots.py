"""Drawing file route also finds files under empire-data/documents and ~/jobs."""
from pathlib import Path


def test_drawings_file_route_finds_empire_data_documents_and_jobs(tmp_path, monkeypatch):
    from app.services.drawing import canonical_path

    canon = tmp_path / "empire-data" / "drawings"
    docs = tmp_path / "empire-data" / "documents"
    jobs = tmp_path / "jobs" / "le-midi" / "drawings"
    canon.mkdir(parents=True)
    docs.mkdir(parents=True)
    jobs.mkdir(parents=True)
    (docs / "from-documents.pdf").write_bytes(b"%PDF-1.4 docs")
    (jobs / "from-jobs.pdf").write_bytes(b"%PDF-1.4 jobs")

    monkeypatch.setattr(canonical_path, "canonical_drawings_dir", lambda: str(canon))
    monkeypatch.setattr(canonical_path, "repo_legacy_drawings_dir", lambda: tmp_path / "missing-legacy")
    monkeypatch.setattr(canonical_path, "_empire_data_dir", lambda: tmp_path / "empire-data")
    monkeypatch.setenv("EMPIRE_JOBS_DIR", str(tmp_path / "jobs"))

    found_docs = canonical_path.resolve_existing_drawing_file("from-documents.pdf")
    assert found_docs == docs / "from-documents.pdf"

    found_jobs = canonical_path.resolve_existing_drawing_file("from-jobs.pdf")
    assert found_jobs == jobs / "from-jobs.pdf"


def test_jobs_scan_finds_file_past_former_400_cap(tmp_path, monkeypatch):
    from app.services.drawing import canonical_path

    canon = tmp_path / "empire-data" / "drawings"
    canon.mkdir(parents=True)
    decoy = tmp_path / "jobs" / "aaa-decoy"
    target = tmp_path / "jobs" / "le-midi" / "drawings"
    decoy.mkdir(parents=True)
    target.mkdir(parents=True)
    for i in range(402):
        (decoy / f"noise-{i:04d}.pdf").write_bytes(b"%PDF-1.4 n")
    wanted = target / "shop-403.pdf"
    wanted.write_bytes(b"%PDF-1.4 target")

    monkeypatch.setattr(canonical_path, "canonical_drawings_dir", lambda: str(canon))
    monkeypatch.setattr(canonical_path, "repo_legacy_drawings_dir", lambda: tmp_path / "missing-legacy")
    monkeypatch.setattr(canonical_path, "_empire_data_dir", lambda: tmp_path / "empire-data")
    monkeypatch.setenv("EMPIRE_JOBS_DIR", str(tmp_path / "jobs"))

    found = canonical_path.resolve_existing_drawing_file("shop-403.pdf")
    assert found == wanted
