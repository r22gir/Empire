#!/usr/bin/env python3
"""
flag_test_quotes.py — Flag known test/smoke/QA quotes in quotes_v2 as
`is_test=1` so they stop showing up in the Workroom quotes list (which
calls list_quotes(include_test=False) by default; see quote_service.py).

SAFE BY DESIGN — DRY-RUN IS THE DEFAULT:
  Running this script with no flags only PRINTS what it would change.
  Nothing is written to any database unless you pass --apply.

  This script has never been run against a real database as part of
  this change. Review the printed match list against your own DB
  before ever passing --apply.

WHAT IT MATCHES:
  Quotes whose `customer_name` contains one of the known test-fixture
  name patterns accumulated by smoke tests / manual QA over time
  (case-insensitive substring match):

    TrustTest, HOTFIX5 Test, Canonical Customer, Routed Customer,
    MOCK-SWEEP, SMOKE, diag-probe, Probe Manual, UI Mapper Sim,
    QB Map Test, Workroom UI Create Proof, Beta Test Customer,
    Jane Demo, Demo Client, Bulk1, 1c-Diag

  You can also pass explicit `--ids id1,id2,...` to flag specific rows
  regardless of name, or `--quote-numbers EST-2026-042,...` to target
  by the human-facing number.

WHAT IT NEVER TOUCHES:
  - get_quote / get_quote_by_number are unaffected by is_test — a
    flagged quote (e.g. a Max smoke fixture pinned by id, such as
    EST-2026-273 / id 6962b803) is still fetchable directly by id or
    number. Only the default list view hides it.
  - This script never DELETEs a row. It only sets is_test=1 (or, with
    --unflag, back to 0). Nothing here removes data.

USAGE:
  # Dry run against a given DB (prints matches, writes nothing):
  python scripts/flag_test_quotes.py --db /path/to/empire.db

  # Apply the flag for real, after reviewing the dry-run output:
  python scripts/flag_test_quotes.py --db /path/to/empire.db --apply

  # Flag specific ids only:
  python scripts/flag_test_quotes.py --db /path/to/empire.db \\
      --ids 6a1b2c3d,7e8f9012 --apply

  # Undo (clear the flag) for specific quote numbers:
  python scripts/flag_test_quotes.py --db /path/to/empire.db \\
      --quote-numbers EST-2026-050 --unflag --apply

DOC SNIPPET (for the founder ops runbook):
  To hide test quotes from the Workroom list without touching real
  customer data:
    1. Dry-run first:
         python backend/scripts/flag_test_quotes.py --db <path-to-empire.db>
    2. Review the printed list of matched quotes (customer name + id +
       quote_number). If it looks right, re-run with --apply.
    3. The Workroom quotes list (`GET /api/v1/quotes-v2`) now excludes
       these automatically. Pass `?include_test=true` to see them again
       (e.g. for an internal QA view). Fetching a flagged quote directly
       by id or by `/quotes-v2/by-number/<number>` still works.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Known test/smoke/QA customer-name fragments. Case-insensitive substring
# match against quotes_v2.customer_name.
DEFAULT_TEST_NAME_PATTERNS = [
    "TrustTest",
    "HOTFIX5 Test",
    "Canonical Customer",
    "Routed Customer",
    "MOCK-SWEEP",
    "SMOKE",
    "diag-probe",
    "Probe Manual",
    "UI Mapper Sim",
    "QB Map Test",
    "Workroom UI Create Proof",
    "Beta Test Customer",
    "Jane Demo",
    "Demo Client",
    "Bulk1",
    "1c-Diag",
]


def find_matches(
    conn: sqlite3.Connection,
    *,
    name_patterns: list[str],
    ids: list[str],
    quote_numbers: list[str],
) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    seen: dict[str, sqlite3.Row] = {}

    for pattern in name_patterns:
        rows = conn.execute(
            "SELECT id, quote_number, customer_name, is_test FROM quotes_v2 "
            "WHERE customer_name LIKE ? COLLATE NOCASE",
            (f"%{pattern}%",),
        ).fetchall()
        for row in rows:
            seen[row["id"]] = row

    if ids:
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT id, quote_number, customer_name, is_test FROM quotes_v2 "
            f"WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        for row in rows:
            seen[row["id"]] = row

    if quote_numbers:
        placeholders = ",".join("?" for _ in quote_numbers)
        rows = conn.execute(
            f"SELECT id, quote_number, customer_name, is_test FROM quotes_v2 "
            f"WHERE quote_number IN ({placeholders})",
            quote_numbers,
        ).fetchall()
        for row in rows:
            seen[row["id"]] = row

    return list(seen.values())


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", required=True, help="Path to the empire.db SQLite file")
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write the flag. Without this, the script only prints matches.",
    )
    parser.add_argument(
        "--unflag", action="store_true",
        help="Clear is_test (set to 0) instead of setting it.",
    )
    parser.add_argument(
        "--ids", default="",
        help="Comma-separated quotes_v2.id values to flag, in addition to name matches.",
    )
    parser.add_argument(
        "--quote-numbers", default="",
        help="Comma-separated quote_number values (e.g. EST-2026-042) to flag.",
    )
    parser.add_argument(
        "--no-name-match", action="store_true",
        help="Skip the built-in test-name-pattern matching; only use --ids/--quote-numbers.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: no database at {db_path}", file=sys.stderr)
        return 2

    ids = [v.strip() for v in args.ids.split(",") if v.strip()]
    quote_numbers = [v.strip() for v in args.quote_numbers.split(",") if v.strip()]
    name_patterns = [] if args.no_name_match else DEFAULT_TEST_NAME_PATTERNS

    conn = sqlite3.connect(str(db_path))
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(quotes_v2)").fetchall()}
        if "is_test" not in cols:
            print(
                "ERROR: quotes_v2.is_test column does not exist on this DB. "
                "Run the app once (it applies the migration on startup) or "
                "run app.db.unified_business_migration.create_all_tables first.",
                file=sys.stderr,
            )
            return 2

        matches = find_matches(
            conn, name_patterns=name_patterns, ids=ids, quote_numbers=quote_numbers,
        )
        target_flag = 0 if args.unflag else 1
        to_change = [row for row in matches if int(row["is_test"] or 0) != target_flag]

        print(f"Database: {db_path}")
        print(f"Mode: {'UNFLAG (is_test=0)' if args.unflag else 'FLAG (is_test=1)'}")
        print(f"Matched {len(matches)} quote(s); {len(to_change)} need a change.\n")
        for row in matches:
            marker = "→ CHANGE" if int(row["is_test"] or 0) != target_flag else "  (already set)"
            print(f"  {row['quote_number'] or row['id']:<16} {row['customer_name']:<40} {marker}")

        if not args.apply:
            print("\nDRY RUN — no changes written. Re-run with --apply to write these.")
            return 0

        if not to_change:
            print("\nNothing to change.")
            return 0

        for row in to_change:
            conn.execute(
                "UPDATE quotes_v2 SET is_test = ?, updated_at = datetime('now') WHERE id = ?",
                (target_flag, row["id"]),
            )
            conn.execute(
                "INSERT INTO financial_audit_log "
                "(entity_type, entity_id, action, field_name, old_value, new_value, changed_by, reason) "
                "VALUES ('quote', ?, 'updated', 'is_test', ?, ?, 'flag_test_quotes.py', 'bulk test-quote flag script')",
                (row["id"], str(row["is_test"] or 0), str(target_flag)),
            )
        conn.commit()
        print(f"\nApplied. {len(to_change)} quote(s) updated.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
