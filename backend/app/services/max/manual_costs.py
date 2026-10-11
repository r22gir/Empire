"""Providers billed outside Empire (2026-10-04): Grok Bot (Chief e) / Cursor.

Empire's token tracker only sees calls Empire itself makes. Rafael's Grok Bot
assistant (Chief e) and Cursor build agents bill to his Cursor account, which
Empire has no usage feed for. This module adds them to the API-expense module
honestly:

* Dollars come ONLY from amounts Rafael enters (one line per month); nothing is
  estimated or invented. With no entry the provider shows "not entered".
* Real activity Empire does know about is reported as counts: Cursor build
  agents launched from the Improvements queue (max_improvements.agent_id).
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional

MANUAL_PROVIDERS: dict[str, dict[str, str]] = {
    "grok_bot": {
        "label": "Grok Bot (Chief e) / Cursor",
        "billing": "Billed to Rafael's Cursor account, outside Empire. Enter the monthly amount from the Cursor dashboard.",
        "billing_url": "https://cursor.com/dashboard",
    },
}
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _db_path() -> str:
    from app.services.max.token_tracker import token_tracker
    return str(token_tracker.db_path)


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS manual_provider_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL, month TEXT NOT NULL, amount_usd REAL NOT NULL,
        note TEXT, entered_by TEXT DEFAULT 'founder',
        entered_at TEXT DEFAULT (datetime('now','localtime')))""")


def add_entry(provider: str, month: str, amount_usd: Any, note: str = "", entered_by: str = "founder") -> dict:
    provider = (provider or "").strip().lower()
    if provider not in MANUAL_PROVIDERS:
        raise ValueError(f"unknown manual provider '{provider}'")
    if not _MONTH_RE.match(month or ""):
        raise ValueError("month must be YYYY-MM")
    try:
        amount = round(float(amount_usd), 2)
    except (TypeError, ValueError):
        raise ValueError("amount_usd must be a number")
    if amount < 0 or amount > 100000:
        raise ValueError("amount_usd must be between 0 and 100000")
    conn = sqlite3.connect(_db_path(), timeout=10)
    try:
        _ensure(conn)
        cur = conn.execute(
            "INSERT INTO manual_provider_costs (provider, month, amount_usd, note, entered_by) VALUES (?,?,?,?,?)",
            (provider, month, amount, (note or "")[:300], (entered_by or "founder")[:40]))
        conn.commit()
        return {"id": cur.lastrowid, "provider": provider, "month": month, "amount_usd": amount}
    finally:
        conn.close()


def _entries(provider: str) -> list[dict]:
    try:
        conn = sqlite3.connect(_db_path(), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            _ensure(conn)
            rows = conn.execute(
                "SELECT * FROM manual_provider_costs WHERE provider=? ORDER BY month DESC, id DESC", (provider,)).fetchall()
        finally:
            conn.close()
    except Exception:
        return []
    # latest entry per month wins (a correction replaces the earlier figure)
    seen: dict[str, dict] = {}
    for r in rows:
        seen.setdefault(r["month"], dict(r))
    return sorted(seen.values(), key=lambda e: e["month"], reverse=True)


def _cursor_builds(days: int) -> Optional[int]:
    try:
        from app.services.leadforge import growth
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with growth._db() as conn:
            have = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='max_improvements'").fetchone()
            if not have:
                return 0
            return int(conn.execute(
                "SELECT COUNT(*) FROM max_improvements WHERE agent_id IS NOT NULL AND agent_id != '' "
                "AND COALESCE(approved_at, created_at) >= ?", (since,)).fetchone()[0])
    except Exception:
        return None


def summary(days: int = 30) -> list[dict]:
    """One row per manual provider for the cost module (cost None = not entered).

    Main-edition only. Family editions (Max-e / Maxine) never see the Grok Bot /
    Cursor card — that is Rafael's billing, not theirs.
    """
    try:
        from app.edition import is_family_edition
        if is_family_edition():
            return []
    except Exception:
        pass
    out = []
    months = {(datetime.now() - timedelta(days=d)).strftime("%Y-%m") for d in range(0, max(1, days))}
    for key, meta in MANUAL_PROVIDERS.items():
        entries = _entries(key)
        in_window = [e for e in entries if e["month"] in months]
        cost = round(sum(e["amount_usd"] for e in in_window), 2) if in_window else None
        out.append({
            "provider": key, "label": meta["label"], "source": "manual",
            "status": "entered" if in_window else "not_entered",
            "cost": cost, "months": [e["month"] for e in in_window],
            "entries": [{k: e[k] for k in ("month", "amount_usd", "note", "entered_at")} for e in entries[:12]],
            "billing": meta["billing"], "billing_url": meta["billing_url"],
            "usage": {"cursor_builds": _cursor_builds(days), "window_days": days},
        })
    return out
