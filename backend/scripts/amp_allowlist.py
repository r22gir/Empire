#!/usr/bin/env python3
"""Add, remove, or list AMP allowlist entries.

Uses EMPIRE_DATA_DIR (and EMPIRE_EDITION=amp). No secrets are stored here.

Examples (on the Dell, from the backend directory):

  EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \\
    ./venv/bin/python scripts/amp_allowlist.py list

  EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \\
    ./venv/bin/python scripts/amp_allowlist.py add --email person@example.com

  EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \\
    ./venv/bin/python scripts/amp_allowlist.py add --username juan

  EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \\
    ./venv/bin/python scripts/amp_allowlist.py remove --email person@example.com

  EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp AMP_JWT_SECRET=... \\
    ./venv/bin/python scripts/amp_allowlist.py login-link --email person@example.com
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import amp_allowlist  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="AMP edition allowlist")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    add = sub.add_parser("add")
    add.add_argument("--email")
    add.add_argument("--username")
    add.add_argument("--role", default="member")

    remove = sub.add_parser("remove")
    remove.add_argument("--email")
    remove.add_argument("--username")

    link = sub.add_parser("login-link")
    link.add_argument("--email", required=True)

    args = parser.parse_args()
    try:
        if args.cmd == "list":
            print(json.dumps(amp_allowlist.list_entries(), ensure_ascii=False, indent=2))
        elif args.cmd == "add":
            entry = amp_allowlist.add_entry(email=args.email, username=args.username, role=args.role)
            print(json.dumps(entry, ensure_ascii=False, indent=2))
        elif args.cmd == "remove":
            removed = amp_allowlist.remove_entry(email=args.email, username=args.username)
            print(json.dumps({"removed": removed}))
        elif args.cmd == "login-link":
            from app.services.amp_access import AmpAccessError, issue_login_challenge

            try:
                issued = issue_login_challenge(args.email, with_code=False)
            except AmpAccessError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            # One line, so an admin can copy the one-time link. Nothing is emailed.
            print(issued["link"])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
