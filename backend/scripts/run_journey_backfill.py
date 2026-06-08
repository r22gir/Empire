#!/usr/bin/env python3
"""
Journey Backfill Audit (read-only)
==================================

Runs a read-only audit of the customer ↔ quote ↔ invoice ↔ payment
carry-forward state and writes a JSON audit log.

This script is the operational counterpart to the
``POST /api/v1/journey/backfill-audit`` endpoint. It can be run from
the command line (cron-friendly) and is safe to invoke repeatedly.

Usage:
    python backend/scripts/run_journey_backfill.py
    python backend/scripts/run_journey_backfill.py --db /path/to/empire.db

The script:
    1. Opens the live DB in read-only mode
    2. Counts quotes_v2 without customer_id, invoices without
       a valid quote, payments without a valid invoice
    3. Writes a JSON audit file to
       backend/data/journey_backfill_audit.json
    4. Prints a human-readable summary to stdout

The script NEVER writes to the live DB. It only writes the audit
JSON. Any actual data writes (backfilling customer_id, etc.) are
gated behind a separate founder-approved code path that is NOT
invoked from this script.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Make the backend importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.max.journey_linkage import (
    BACKFILL_AUDIT_PATH,
    DEFAULT_DB_PATH,
    _resolve_db_path,
    run_backfill_audit,
)


def main():
    p = argparse.ArgumentParser(
        description="Run a read-only audit of the customer journey linkage state."
    )
    p.add_argument(
        "--db",
        default=None,
        help="Path to the live empire.db. Defaults to EMPIRE_DB_PATH env or "
             f"{DEFAULT_DB_PATH}.",
    )
    p.add_argument(
        "--audit-out",
        default=BACKFILL_AUDIT_PATH,
        help="Path to write the audit JSON. Defaults to "
             f"{BACKFILL_AUDIT_PATH}.",
    )
    p.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write the audit JSON; just print the summary.",
    )
    args = p.parse_args()

    db_path = args.db or _resolve_db_path()
    if not Path(db_path).exists():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    audit = run_backfill_audit(db_path=db_path)

    # Print human-readable summary
    print("=" * 70)
    print("  CUSTOMER JOURNEY BACKFILL AUDIT")
    print("=" * 70)
    print(f"  ran_at:    {audit.ran_at}")
    print(f"  db:        {audit.db_path}")
    print()
    print("  QUOTES_V2:")
    for k, v in audit.quotes_v2.items():
        print(f"    {k:<25s} {v}")
    print()
    print("  INVOICES:")
    for k, v in audit.invoices.items():
        print(f"    {k:<25s} {v}")
    print()
    print("  PAYMENTS:")
    for k, v in audit.payments.items():
        print(f"    {k:<25s} {v}")
    print()
    if audit.recommendations:
        print(f"  RECOMMENDATIONS ({len(audit.recommendations)}):")
        for r in audit.recommendations:
            print(f"    [{r['severity']:<6s}] {r['tag']:<20s} {r['summary']}")
            print(f"             {r['suggestion']}")
            print()
    else:
        print("  RECOMMENDATIONS: none — linkage is clean")
        print()
    print("  NOTES:")
    for n in audit.notes:
        print(f"    - {n}")
    print()
    print("=" * 70)

    if args.no_write:
        print("  --no-write was set; audit JSON not written.")
    else:
        # run_backfill_audit already wrote the audit. Confirm.
        if Path(BACKFILL_AUDIT_PATH).exists():
            print(f"  audit written to: {BACKFILL_AUDIT_PATH}")
        else:
            print(f"  WARN: audit JSON was not written. Check write permissions on {BACKFILL_AUDIT_PATH}.")
    print("=" * 70)

    # Exit code 0 if no high-severity recommendations, 1 otherwise
    has_high = any(r["severity"] == "high" for r in audit.recommendations)
    sys.exit(1 if has_high else 0)


if __name__ == "__main__":
    main()
