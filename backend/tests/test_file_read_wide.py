"""2026-10-08: file_read reaches Rafael's own files outside the repo; secrets and family editions never."""
import os
from app.services.max import tool_executor as te


def _read(path):
    return te._file_read({"path": str(path)})


def test_reads_rafael_file_outside_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    f = tmp_path / "jobs" / "marleys" / "notes.txt"
    f.parent.mkdir(parents=True)
    f.write_text("Marley's channel backs: 12 in channels\n")
    r = _read(f)
    assert r.success, r.error
    assert "12 in channels" in r.result["content"]


def test_secrets_and_family_never(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    for rel in [".env", "keys/id_rsa", "empire-maxine/notes.txt", "amp/notes.txt", "stuff/client_secret.json",
                "data/empire.db", "creds/token.json"]:
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("SECRET=1\n")
        r = _read(f)
        assert not r.success, rel
        assert "SECRET=1" not in str(r.result or "")


def test_family_edition_cannot_widen(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    f = tmp_path / "jobs" / "x.txt"
    f.parent.mkdir(parents=True)
    f.write_text("hello\n")
    assert not _read(f).success


def test_repo_env_file_refused():
    r = _read("backend/.env")
    assert not r.success and "secret" in (r.error or "").lower()


def test_outside_roots_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(tmp_path / "only-here"))
    (tmp_path / "only-here").mkdir()
    r = _read("/etc/hostname")
    assert not r.success
