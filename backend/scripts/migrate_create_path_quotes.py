#!/usr/bin/env python3
"""Import JSON create-path quotes into the canonical quotes_v2 store.

Dry-run by default. Pass --apply to write. Optional --limit. A backup is
taken before any apply. Does not send email.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.quote_service import migrate_legacy_json_quotes  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate JSON create-path quotes into quotes_v2")
    parser.add_argument("--apply", action="store_true", help="Write changes (default is dry-run)")
    parser.add_argument("--limit", type=int, default=None, help="Max JSON files to consider")
    args = parser.parse_args()
    result = migrate_legacy_json_quotes(apply=args.apply, limit=args.limit)
    print(json.dumps(result, indent=2))
    return 0 if not result.get("failed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
