#!/usr/bin/env python3
"""Import JSON create-path quotes into the canonical quotes_v2 store.

Idempotent. Does not send email. Safe to re-run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.quote_service import migrate_legacy_json_quotes  # noqa: E402


def main() -> int:
    result = migrate_legacy_json_quotes()
    print(json.dumps(result, indent=2))
    return 0 if not result.get("failed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
