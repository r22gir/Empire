#!/usr/bin/env python3
"""Set the founder row password_hash via getpass. Backs up the DB first.

Never prints or logs the password. Updates only the active founder row.
If that row has an empty email, fills it with the first FOUNDER_ACCESS_EMAILS
entry.

  python backend/scripts/set_founder_password.py --db /path/to/empire.db

Tests must pass --db (or EMPIRE_TASK_DB) to an isolated temp file.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

# Allow `python backend/scripts/set_founder_password.py` from repo root.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.founder_access import (  # noqa: E402
    backup_sqlite,
    parse_founder_access_emails,
    resolve_db_path,
    set_founder_password,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set founder Studio password (getpass, backup first).")
    parser.add_argument("--db", help="SQLite path. Defaults to EMPIRE_TASK_DB or backend/data/empire.db")
    args = parser.parse_args(argv)

    db_path = resolve_db_path(args.db)
    if not db_path.is_file():
        print(f"database not found: {db_path}", file=sys.stderr)
        return 2

    password = getpass.getpass("New founder password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        return 1

    backup = backup_sqlite(db_path)
    print(f"Backup: {backup}")
    updated = set_founder_password(db_path, password, parse_founder_access_emails())
    print(f"Rows updated: {updated}")
    return 0 if updated else 3


if __name__ == "__main__":
    sys.exit(main())
