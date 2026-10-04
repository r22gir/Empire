#!/usr/bin/env python3
"""Export Rafael's Max sessions for one America/New_York date.

    cd ~/empire-repo-main/backend
    venv/bin/python scripts/export_max_sessions.py               # today
    venv/bin/python scripts/export_max_sessions.py --date 2026-10-04
    venv/bin/python scripts/export_max_sessions.py --yesterday   # used by the nightly timer

Writes ~/empire-data/max-sessions/YYYY-MM-DD/ (per-session .jsonl + .md,
images/, summary.json). Main studio only — refuses inside a family edition.
Reads local SQLite files only; makes no network calls.

The max package __init__ pulls in the AI router and Telegram bot, so this
script registers a bare ``app.services.max`` package and imports only the
two modules it needs.
"""
import sys
import types
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import app.services  # noqa: E402,F401  (light)

if "app.services.max" not in sys.modules:
    pkg = types.ModuleType("app.services.max")
    pkg.__path__ = [str(BACKEND / "app" / "services" / "max")]
    sys.modules["app.services.max"] = pkg

from app.services.max.session_export import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
