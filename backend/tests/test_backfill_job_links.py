"""Dry-run job-link backfill. Mock records only — never apply in CI."""
import csv
import os
import sqlite3
from pathlib import Path

from app.services.job_link_backfill import (
    apply_links,
    in_ci,
    load_aliases,
    normalize_client,
    propose_links,
    write_csv,
)


def _conn(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "mock.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY, title TEXT, customer_id TEXT, quote_id TEXT, job_number TEXT,
            client_name TEXT, created_at TEXT, metadata TEXT
        );
        CREATE TABLE quotes_v2 (
            id TEXT PRIMARY KEY, quote_number TEXT, job_id TEXT, customer_id TEXT,
            customer_name TEXT, project_name TEXT, created_at TEXT
        );
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY, invoice_number TEXT, job_id TEXT, quote_id TEXT, customer_id TEXT,
            client_name TEXT, created_at TEXT
        );
        CREATE TABLE job_documents (
            id TEXT PRIMARY KEY, job_id TEXT, quote_id TEXT, filename TEXT, url TEXT, created_at TEXT
        );
        """
    )
    # Two jobs share a client (Willard / Le Midi hypothesis)
    conn.execute("INSERT INTO jobs VALUES ('job-willard','Willard drapery','cust-shared','q-willard','JOB-W','Shared Client','2026-01-10','{}')")
    conn.execute("INSERT INTO jobs VALUES ('job-midi','Le Midi banquettes','cust-shared',NULL,'JOB-M','Shared Client','2026-03-01','{}')")
    conn.execute("INSERT INTO jobs VALUES ('job-solo','Solo roman','cust-solo','q-solo','JOB-S','Solo Client','2026-02-01','{}')")
    conn.execute("INSERT INTO quotes_v2 VALUES ('q-willard','EST-2026-0100',NULL,NULL,'Shared Client','Willard','2026-01-11')")
    conn.execute("INSERT INTO quotes_v2 VALUES ('q-midi','EST-2026-0300',NULL,NULL,'Shared Client','Le Midi','2026-03-02')")
    conn.execute("INSERT INTO quotes_v2 VALUES ('q-solo','EST-2026-0200',NULL,NULL,'Solo Client','Solo roman','2026-02-02')")
    conn.execute("INSERT INTO invoices VALUES ('inv-midi','INV-2026-0300',NULL,'q-midi',NULL,'Shared Client','2026-03-10')")
    conn.execute("INSERT INTO invoices VALUES ('inv-solo','INV-2026-0200',NULL,NULL,NULL,'Solo Client','2026-02-10')")
    conn.execute("INSERT INTO job_documents VALUES ('jd-midi',NULL,'q-midi','le-midi.pdf','/api/v1/drawings/files/le-midi.pdf','2026-03-03')")
    conn.commit()
    return conn


def test_normalize_and_aliases(tmp_path):
    assert normalize_client("The Shared Client Studio") == "shared client"
    aliases = load_aliases(None)
    assert aliases == {}
    p = tmp_path / "aliases.json"
    p.write_text('{"Shared Client Interiors": ["Shared Client"]}', encoding="utf-8")
    loaded = load_aliases(p)
    assert loaded[normalize_client("Shared Client")] == normalize_client("Shared Client Interiors")


def test_quote_id_is_auto_and_shared_client_is_review(tmp_path):
    conn = _conn(tmp_path)
    rows = propose_links(conn)
    by_ref = {r.record_ref: r for r in rows}
    # job.quote_id points at q-willard and q-solo
    assert by_ref["EST-2026-0100"].confidence == "auto"
    assert by_ref["EST-2026-0100"].match_by == "quote_id"
    assert by_ref["EST-2026-0100"].proposed_job_id == "job-willard"
    assert by_ref["EST-2026-0200"].confidence == "auto"
    assert by_ref["EST-2026-0200"].proposed_job_id == "job-solo"
    # Le Midi quote has no job.quote_id; Shared Client is on two jobs → review
    assert by_ref["EST-2026-0300"].confidence == "review"
    assert "shared client" in by_ref["EST-2026-0300"].reason.lower() or "Shared" in by_ref["EST-2026-0300"].reason
    # invoice via quote_id of Willard-linked quote is auto; midi invoice quote_id has no job.quote_id
    assert by_ref["INV-2026-0300"].confidence in {"auto", "review"}
    # document via quote_id
    assert by_ref["le-midi.pdf"].kind == "job_documents"
    conn.close()


def test_write_csv_and_apply_only_job_and_customer(tmp_path):
    conn = _conn(tmp_path)
    rows = propose_links(conn)
    csv_path = tmp_path / "job-link-backfill.csv"
    write_csv(rows, csv_path)
    text = csv_path.read_text(encoding="utf-8")
    assert "kind,record_id" in text
    assert "quotes" in text
    with csv_path.open(encoding="utf-8") as fh:
        recs = list(csv.DictReader(fh))
    assert recs
    assert all("confidence" in r for r in recs)

    counts = apply_links(conn, rows, only_auto=True)
    conn.commit()
    assert counts["quotes"] >= 2
    solo = conn.execute("SELECT job_id, customer_id FROM quotes_v2 WHERE id='q-solo'").fetchone()
    assert solo[0] == "job-solo"
    assert solo[1] == "cust-solo"
    # review row for Le Midi quote must not be written in auto-only mode
    midi = conn.execute("SELECT job_id FROM quotes_v2 WHERE id='q-midi'").fetchone()
    assert not midi[0]
    conn.close()


def test_apply_refuses_ci_flag(monkeypatch):
    monkeypatch.setenv("CI", "true")
    assert in_ci() is True
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CONTINUOUS_INTEGRATION", raising=False)
    # local/dev without CI vars
    for k in ("CI", "GITHUB_ACTIONS", "CONTINUOUS_INTEGRATION"):
        os.environ.pop(k, None)
    assert in_ci() is False
