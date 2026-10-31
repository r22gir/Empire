"""FP-N10 regression: estimate/quote links resolve the job's own estimate doc.

MOCK data only: temp DB, temp files, fake clients. No sends.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import pytest

from app.services.max import file_finder as ff
from app.services.max import latest_job_file as ljf


def _touch(p: Path, data: bytes = b"%PDF-1.4 mock", age_hours: float = 0.0) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    if age_hours:
        t = time.time() - age_hours * 3600
        os.utime(p, (t, t))
    return p


@pytest.fixture()
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    data = home / "empire-data"
    # Decoys: newer than the real estimate, in caches / lab folders.
    est = _touch(data / "uploads" / "jobs" / "job_mock1" / "MockBistro_Phase2_Estimate_REVD.pdf", age_hours=20)
    _touch(data / "uploads" / "jobs" / "job_mock1" / "MockBistro_Phase2_Estimate_REVD_INTERNAL.pdf", age_hours=20)
    _touch(data / "uploads" / "jobs" / "job_mock1" / "MockBistro_Office_Estimate_REVA.pdf", age_hours=40)
    _touch(data / "fabrics-preview" / "photos" / "mockup_cache" / "bench-mockbistro-estimate.jpg", b"JPG", 0.01)
    _touch(data / "fabrics-preview" / "photos" / "mockup_cache" / "mockbistro-estimate.pdf", age_hours=0.01)
    _touch(home / "Desktop" / "Max_Continuous_Test" / "MOCK_quote_mockbistro_estimate.pdf", age_hours=0.02)
    q_pdf = _touch(data / "quotes" / "EST-2099-501.pdf", age_hours=5)
    _touch(home / "Desktop" / "Max_Continuous_Test" / "est501_revC" / "EST-2099-501_draft_revC_p1.pdf", age_hours=0.01)

    db = data / "mock_jobs.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
    CREATE TABLE customers (id TEXT PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE jobs (id TEXT PRIMARY KEY, title TEXT NOT NULL, customer_id TEXT, created_at TEXT);
    CREATE TABLE job_documents (id TEXT PRIMARY KEY, job_id TEXT, quote_id TEXT, document_type TEXT,
        url TEXT, filename TEXT, revision INTEGER DEFAULT 1, superseded INTEGER DEFAULT 0, created_at TEXT);
    CREATE TABLE quotes_v2 (id TEXT PRIMARY KEY, quote_number TEXT, customer_name TEXT, job_id TEXT,
        pdf_path TEXT, is_test INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT);
    """)
    conn.execute("INSERT INTO customers VALUES ('c1','MOCK Bistro Owner')")
    conn.execute("INSERT INTO customers VALUES ('c2','MOCK Tavern')")
    conn.execute("INSERT INTO jobs VALUES ('job_mock1','MockBistro — Office (ripplefold + sheers)','c1','2099-01-01')")
    conn.execute("INSERT INTO jobs VALUES ('job_mock2','MOCK Tavern banquettes','c2','2099-01-02')")
    rows = [
        ("d1", "estimate_superseded", "MockBistro_Office_Estimate_REVA.pdf", 1, 0),
        ("d2", "estimate", "MockBistro_Phase2_Estimate_REVD.pdf", 4, 0),
        ("d3", "estimate_internal", "MockBistro_Phase2_Estimate_REVD_INTERNAL.pdf", 4, 0),
    ]
    for did, typ, fn, rev, sup in rows:
        conn.execute(
            "INSERT INTO job_documents VALUES (?,?,?,?,?,?,?,?,?)",
            (did, "job_mock1", None, typ, f"/api/v1/files/download/jobs/job_mock1/{fn}", fn, rev, sup, "2099-01-03"),
        )
    conn.execute("INSERT INTO quotes_v2 VALUES ('q1','EST-2099-501','MOCK Tavern','job_mock2',?,0,'2099','2099')",
                 (str(q_pdf),))
    conn.commit(); conn.close()

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(db))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data))
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(home))
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(data / "drawings"))
    monkeypatch.setenv("MAX_CLOUD_FILES_DISABLED", "1")
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    ff.INDEX.clear()
    yield {"est": est, "quote_pdf": q_pdf, "home": home}
    ff.INDEX.clear()


def test_estimate_link_returns_jobs_current_client_estimate(env):
    rep = ljf.show_link_reply("send me the link for the MockBistro estimate", [])
    assert rep and rep["found"], rep
    assert Path(rep["path"]).name == "MockBistro_Phase2_Estimate_REVD.pdf"


def test_estimate_link_never_returns_mockup_cache_or_lab_file(env):
    for msg in ("send me the link for the MockBistro estimate", "link to the MockBistro quote"):
        rep = ljf.show_link_reply(msg, [])
        p = str(rep.get("path") or "").lower()
        assert "fabrics-preview" not in p and "mockup_cache" not in p and "max_continuous_test" not in p, rep
        assert not p.endswith(".jpg"), rep


def test_estimate_number_resolves_quote_pdf_not_lab_copy(env):
    rep = ljf.show_link_reply("send me a link for EST-2099-501", [])
    assert rep["found"], rep
    assert Path(rep["path"]) == env["quote_pdf"].resolve()


def test_blank_pdf_path_uses_quotes_pdf_dir(env, tmp_path):
    data = env["home"] / "empire-data"
    pdf = _touch(data / "quotes" / "pdf" / "EST-2099-502.pdf", age_hours=3)
    conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
    conn.execute("INSERT INTO quotes_v2 VALUES ('q2','EST-2099-502','MOCK Tavern','job_mock2','',0,'2099','2099')")
    conn.commit(); conn.close()
    rep = ljf.show_link_reply("send me a link for EST-2099-502", [])
    assert rep["found"] and Path(rep["path"]) == pdf.resolve(), rep


def test_internal_copy_only_when_asked(env):
    rep = ljf.show_link_reply("send me the link for the MockBistro internal estimate", [])
    assert Path(rep["path"]).name.endswith("_INTERNAL.pdf")


def test_unknown_client_estimate_is_clear_not_found(env):
    rep = ljf.show_link_reply("link to the Zelda Nobody quote", [])
    assert rep is not None and rep["found"] is False, rep
    assert "won't" in rep["text"] or "couldn't" in rep["text"]
    assert not rep.get("path")


def test_this_quote_uses_job_from_history(env):
    hist = [{"role": "user", "content": "let's review the MockBistro office job"}]
    rep = ljf.show_link_reply("Send me a link for this quote", hist)
    assert rep["found"], rep
    assert Path(rep["path"]).name == "MockBistro_Phase2_Estimate_REVD.pdf"


def test_drawing_link_search_excludes_caches_and_lab_dirs(env):
    looked = ljf.find_newest_job_document("send me the latest MockBistro drawing", [])
    for m in looked["matches"]:
        assert "mockup_cache" not in str(m.get("path")).lower()
        assert "max_continuous_test" not in str(m.get("path")).lower()
    if looked["match"]:
        p = looked["match"]["path"].lower()
        assert "fabrics-preview" not in p and "max_continuous_test" not in p
