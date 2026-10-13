#!/usr/bin/env python3
"""Dry-run report of short 8-char chat files next to a full-id copy.

Never deletes. Never writes. Pass --dir so this cannot touch live /data
by accident.

Examples:

  ./venv/bin/python scripts/chat_history_cleanup.py --dir /tmp/chats-sample

  EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/tmp/amp-test \\
    ./venv/bin/python scripts/chat_history_cleanup.py --dir /tmp/amp-test/chats
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.chat_history_store import find_short_id_duplicates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run: list short-id chat JSON files. Does not delete."
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Chats root to scan (must be passed explicitly; live /data is not the default)",
    )
    args = parser.parse_args()
    root = Path(args.dir).expanduser().resolve()
    live_roots = ("/data/amp", "/data/maxine", "/data/workroom")
    if any(str(root).startswith(p) for p in live_roots):
        print(
            "Refusing to scan a live /data path. Copy files to a temp dir first.",
            file=sys.stderr,
        )
        return 2
    report = find_short_id_duplicates(root)
    print(json.dumps({"dry_run": True, "would_delete": False, "items": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
