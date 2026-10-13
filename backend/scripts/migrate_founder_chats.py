#!/usr/bin/env python3
"""Map pre-isolation founder/ chats to the edition's allowlisted primary user.

Dry-run by default. Writes only with --apply (copy, never delete).
Never runs automatically — this file has no import-time side effects and
is not called from app startup. You must invoke the script yourself.

Reads EMPIRE_EDITION when --edition is omitted. Skips 8-character short-id
files that sit beside a full-id record (those are leftovers, not chats).

On Max-e the only family user is Juan (AMP_OWNER_EMAIL unless
AMP_LEGACY_CHAT_EMAIL / FAMILY_LEGACY_CHAT_EMAIL is set). Maxine uses
MAXINE_LEGACY_CHAT_EMAIL or AMP_OWNER_EMAIL.

Examples:

  EMPIRE_EDITION=amp \\
    ./venv/bin/python scripts/migrate_founder_chats.py --dir /tmp/amp-chats

  EMPIRE_EDITION=amp \\
    ./venv/bin/python scripts/migrate_founder_chats.py \\
      --dir /data/amp/chats --email juan@example.com --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.chat_history_store import (  # noqa: E402
    apply_founder_migration,
    plan_founder_migration,
    primary_legacy_email,
    resolve_legacy_edition,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run (default): map founder/ chats to the allowlisted user. --apply copies."
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Chats root (the folder that contains founder/). Must be passed explicitly.",
    )
    parser.add_argument(
        "--email",
        default="",
        help="Allowlisted destination email. Defaults to the edition primary (Juan on Max-e).",
    )
    parser.add_argument(
        "--edition",
        default="",
        help="amp or maxine. Defaults to EMPIRE_EDITION.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy founder/*.json into the user folder. Without this flag, only print the plan.",
    )
    args = parser.parse_args(argv)
    root = Path(args.dir).expanduser().resolve()
    if not root.exists():
        print(json.dumps({"error": f"missing dir: {root}"}, indent=2))
        return 2
    edition = resolve_legacy_edition(args.edition)
    if args.edition.strip():
        os.environ["EMPIRE_EDITION"] = edition
    email = (args.email or primary_legacy_email(edition or None) or "").strip().lower()
    if args.apply:
        report = apply_founder_migration(root, target_email=email, edition=edition)
    else:
        report = plan_founder_migration(root, target_email=email, edition=edition)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
