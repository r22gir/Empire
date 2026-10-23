#!/usr/bin/env python3
"""Tag existing quote/invoice lines as installation + windows + lf.

Dry-run by default. --apply --yes backs up the DB first and writes.
Imported historical docs (legacy numbers like 812-C, 838, 897, 909, 803-A)
are included. Never run apply in CI.

Usage:

    python3 backend/scripts/backfill_install_lines.py
    python3 backend/scripts/backfill_install_lines.py --db /path/to/empire.db
    python3 backend/scripts/backfill_install_lines.py --apply --yes
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys  # noqa: I001
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.install_line_backfill import (  # noqa: E402
    apply_install_tags,
    propose_install_tags,
)
from app.services.job_link_backfill import backup_db, in_ci  # noqa: E402


def _default_db() -> Path:
    raw = os.getenv("EMPIRE_TASK_DB") or os.getenv("EMPIRE_DB_PATH")
    if raw:
        return Path(raw)
    return Path.home() / "empire-data" / "empire.db"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Dry-run install-line tag backfill.")
    p.add_argument("--db", default=None, help="Path to empire.db")
    p.add_argument("--apply", action="store_true", help="Write tags after backup. Refuses CI.")
    p.add_argument("--yes", action="store_true", help="Required with --apply to confirm the write.")
    args = p.parse_args(argv)

    db_path = Path(args.db) if args.db else _default_db()
    if not db_path.is_file():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = propose_install_tags(conn)
        changed = [r for r in rows if r.get("changed")]
        legacy = [r for r in rows if r.get("legacy")]
        print(f"Install lines found: {len(rows)} ({len(changed)} would change, {len(legacy)} on imported/legacy docs).")
        for r in changed[:20]:
            if r["kind"] == "quote_line":
                print(f"  quote_line {r['id']} {r['description'][:60]!r} {r['before']} -> {r['after']}")
            else:
                print(f"  invoice {r.get('invoice_number') or r['id']} ({len(r['after'])} lines)")
        if len(changed) > 20:
            print(f"  … {len(changed) - 20} more")

        if not args.apply:
            print("Dry run. Re-run with --apply --yes to write (backs up DB first).")
            return 0
        if not args.yes:
            print("ERROR: --apply requires --yes", file=sys.stderr)
            return 2
        if in_ci():
            print("ERROR: refuse --apply in CI", file=sys.stderr)
            return 3
        backup = backup_db(db_path)
        print(f"Backup: {backup}")
        counts = apply_install_tags(conn, rows)
        conn.commit()
        print(f"Applied: {counts}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
