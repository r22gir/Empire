#!/usr/bin/env python3
"""Propose job_id / customer_id links for quotes, invoices, documents, and folders.

Dry-run by default. Writes a CSV of proposed links (auto vs review).
Apply mode backs up the DB first and writes only job_id and customer_id
(plus jobs.metadata.job_folder_slug for folder-to-job rows).

Never run apply in CI.

Usage (from the Empire repo):

    python3 backend/scripts/backfill_job_links.py
    python3 backend/scripts/backfill_job_links.py --db /path/to/empire.db --csv /tmp/job-links.csv
    python3 backend/scripts/backfill_job_links.py --apply --yes   # live write; refuses CI

Optional aliases file (never committed): --aliases /path/to/client_aliases.json
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.job_link_backfill import (  # noqa: E402
    apply_links,
    backup_db,
    in_ci,
    load_aliases,
    propose_links,
    write_csv,
)


def _default_db() -> Path:
    raw = os.getenv("EMPIRE_TASK_DB") or os.getenv("EMPIRE_DB_PATH")
    if raw:
        return Path(raw)
    return Path.home() / "empire-data" / "empire.db"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Dry-run job_id / customer_id backfill.")
    p.add_argument("--db", default=None, help="Path to empire.db")
    p.add_argument("--csv", default=None, help="Where to write the proposed-links CSV")
    p.add_argument("--aliases", default=None, help="Optional client alias JSON (not committed)")
    p.add_argument("--jobs-dir", default=None, help="Per-job folders (default ~/jobs)")
    p.add_argument("--apply", action="store_true", help="Write auto matches after backup. Refuses CI.")
    p.add_argument("--yes", action="store_true", help="Required with --apply to confirm the write.")
    p.add_argument("--include-review", action="store_true", help="With --apply, also write review rows.")
    args = p.parse_args(argv)

    db_path = Path(args.db) if args.db else _default_db()
    if not db_path.is_file():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        return 1

    aliases = load_aliases(Path(args.aliases)) if args.aliases else {}
    jobs_dir = Path(args.jobs_dir) if args.jobs_dir else Path(os.getenv("EMPIRE_JOBS_DIR") or (Path.home() / "jobs"))

    conn = sqlite3.connect(str(db_path))
    try:
        rows = propose_links(conn, aliases=aliases, jobs_dir=jobs_dir)
        csv_path = Path(args.csv) if args.csv else db_path.parent / "job-link-backfill.csv"
        write_csv(rows, csv_path)
        auto = sum(1 for r in rows if r.confidence == "auto")
        review = sum(1 for r in rows if r.confidence == "review")
        print(f"Proposed {len(rows)} links ({auto} auto, {review} review).")
        print(f"CSV: {csv_path}")
        by_kind: dict[str, int] = {}
        for r in rows:
            by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
        for kind, n in sorted(by_kind.items()):
            print(f"  {kind}: {n}")

        if not args.apply:
            print("Dry run only. Re-run with --apply --yes after reviewing the CSV.")
            return 0

        if in_ci():
            print("REFUSING apply: CI environment detected.", file=sys.stderr)
            return 2
        if not args.yes:
            print("REFUSING apply: pass --yes after reviewing the CSV.", file=sys.stderr)
            return 2

        backup = backup_db(db_path)
        print(f"Backup: {backup}")
        counts = apply_links(conn, rows, only_auto=not args.include_review)
        conn.commit()
        print("Applied:", ", ".join(f"{k}={v}" for k, v in counts.items()))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
