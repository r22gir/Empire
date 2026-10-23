"""Dry-run install-line backfill. Mock records only — never apply in CI."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

from app.services.install_line_backfill import apply_install_tags, propose_install_tags
from app.services.job_link_backfill import in_ci

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backfill_install_lines.py"
_spec = importlib.util.spec_from_file_location("backfill_install_lines", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
main = _mod.main


def _conn(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "mock.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE quotes_v2 (
            id TEXT PRIMARY KEY, quote_number TEXT, issued_document TEXT, project_name TEXT
        );
        CREATE TABLE quote_line_items (
            id INTEGER PRIMARY KEY, quote_id TEXT, description TEXT,
            item_type TEXT, category TEXT, quantity REAL, unit TEXT,
            width REAL, unit_price REAL, windows INTEGER, lf REAL
        );
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY, invoice_number TEXT, quote_id TEXT, notes TEXT, line_items TEXT
        );
        """
    )
    conn.execute("INSERT INTO quotes_v2 VALUES ('q-838','838','838','Willard Est 838')")
    conn.execute("INSERT INTO quotes_v2 VALUES ('q-812','812-C','812-C','Imported 812-C')")
    conn.execute("INSERT INTO quotes_v2 VALUES ('q-new','EST-2026-0400',NULL,'New')")
    conn.execute(
        "INSERT INTO quote_line_items VALUES (1,'q-838','Install 10 windows — 160\" wall','labor','labor',1,'ea',160,1450,NULL,NULL)"
    )
    conn.execute(
        "INSERT INTO quote_line_items VALUES (2,'q-812','Hourly install 5 windows','labor','labor',1,'ea',NULL,800,NULL,NULL)"
    )
    conn.execute(
        "INSERT INTO quote_line_items VALUES (3,'q-new','Roman shade fabric','labor','labor',1,'ea',48,590,NULL,NULL)"
    )
    conn.execute(
        "INSERT INTO invoices VALUES ('inv-897','897','q-838','Imported 897', ?)",
        (json.dumps([{"description": "Install 6 windows — 12 lf", "amount": 900}]),),
    )
    conn.commit()
    return conn


def test_propose_includes_legacy_and_skips_fabric(tmp_path):
    conn = _conn(tmp_path)
    rows = propose_install_tags(conn)
    kinds = {(r["kind"], str(r.get("id"))) for r in rows}
    assert ("quote_line", "1") in kinds
    assert ("quote_line", "2") in kinds
    assert ("invoice_lines", "inv-897") in kinds
    assert all(r.get("id") != 3 for r in rows if r["kind"] == "quote_line")
    willard = next(r for r in rows if r["kind"] == "quote_line" and r["id"] == 1)
    assert willard["legacy"] is True
    assert willard["after"]["item_type"] == "installation"
    assert willard["after"]["windows"] == 10
    assert abs(willard["after"]["lf"] - (160 / 12)) < 1e-9
    conn.close()


def test_dry_run_default_and_apply_writes(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    db = tmp_path / "mock.db"
    conn.close()
    rc = main(["--db", str(db)])
    assert rc == 0
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT item_type, windows, lf FROM quote_line_items WHERE id=1").fetchone()
    assert row["item_type"] == "labor"  # dry run did not write
    conn.close()

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CONTINUOUS_INTEGRATION", raising=False)
    if in_ci():
        rc = main(["--db", str(db), "--apply", "--yes"])
        assert rc == 3
        return
    rc = main(["--db", str(db), "--apply", "--yes"])
    assert rc == 0
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT item_type, windows, lf FROM quote_line_items WHERE id=1").fetchone()
    assert row["item_type"] == "installation"
    assert row["windows"] == 10
    inv = conn.execute("SELECT line_items FROM invoices WHERE id='inv-897'").fetchone()
    items = json.loads(inv["line_items"])
    assert items[0]["item_type"] == "installation"
    assert items[0]["windows"] == 6
    backups = list(tmp_path.glob("mock.db.bak-*"))
    assert backups
    conn.close()


def test_apply_without_yes_refuses(tmp_path):
    conn = _conn(tmp_path)
    db = tmp_path / "mock.db"
    conn.close()
    rc = main(["--db", str(db), "--apply"])
    assert rc == 2
