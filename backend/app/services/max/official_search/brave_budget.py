"""Hard monthly Brave Search budget. Persist per edition, fail closed.

Brave's $5 free credit is ~1,000 requests. The default cap is 900
(``BRAVE_MONTHLY_FREE_REQUESTS``) so we stay inside that credit. When
the calendar-month count reaches the cap, Brave is skipped and search
continues on MiniMax Token Plan + Exa/Tavily + DuckDuckGo. A store
error refuses Brave rather than risking a paid overage.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.data_paths import data_root
from app.services.max.official_search.config import (
    brave_monthly_free_requests,
    process_edition,
)

logger = logging.getLogger("max.official_search.brave_budget")

_TABLE = """
CREATE TABLE IF NOT EXISTS brave_monthly_usage (
    edition TEXT NOT NULL,
    month TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (edition, month)
)
"""


def brave_month_key(now: Optional[datetime] = None) -> str:
    """UTC calendar month ``YYYY-MM``."""
    dt = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m")


def _db_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        path = Path(custom_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    root = data_root() / "max"
    root.mkdir(parents=True, exist_ok=True)
    return root / "brave_budget.db"


def _connect(custom_path: Optional[str] = None) -> sqlite3.Connection:
    path = _db_path(custom_path)
    conn = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
    conn.execute(_TABLE)
    return conn


def _exhausted_status(*, edition: str, month: str, cap: int, reason: str) -> dict[str, Any]:
    """Fail-closed snapshot: treat Brave as unavailable."""
    return {
        "provider": "brave",
        "model_pattern": "search.web",
        "cost_basis": "free_tier",
        "window": "month",
        "window_date": month,
        "edition": edition,
        "requests_month": cap,
        "monthly_limit": cap,
        "requests_day": cap,
        "rpd": cap,
        "rpd_limit": cap,
        "rpm": 0,
        "rpm_limit": 0,
        "tpd": 0,
        "tpd_limit": 0,
        "tokens_day": 0,
        "percent_used": 100.0 if cap else 100.0,
        "status": "exhausted",
        "warn": True,
        "exhausted": True,
        "available": False,
        "reset_tz": "UTC",
        "source_url": "https://brave.com/search/api/",
        "verified_date": "2026-10-12",
        "use_cases": "Official web search (Brave $5 free credit, ~1,000 req/mo)",
        "not_for": "Paid Brave overage — skip to MiniMax Token Plan, Exa/Tavily, DuckDuckGo",
        "error": reason,
    }


def _status_from_count(
    *,
    edition: str,
    month: str,
    used: int,
    cap: int,
) -> dict[str, Any]:
    used = max(0, int(used))
    cap = max(0, int(cap))
    pct = 100.0 if cap <= 0 else min(100.0, round(used / cap * 100.0, 2))
    exhausted = cap <= 0 or used >= cap
    warn = exhausted or pct >= 80.0
    status = "exhausted" if exhausted else ("warn" if warn else "normal")
    return {
        "provider": "brave",
        "model_pattern": "search.web",
        "cost_basis": "free_tier",
        "window": "month",
        "window_date": month,
        "edition": edition,
        "requests_month": used,
        "monthly_limit": cap,
        "requests_day": used,
        "rpd": cap,
        "rpd_limit": cap,
        "rpm": 0,
        "rpm_limit": 0,
        "tpd": 0,
        "tpd_limit": 0,
        "tokens_day": 0,
        "percent_used": pct,
        "status": status,
        "warn": warn,
        "exhausted": exhausted,
        "available": not exhausted,
        "reset_tz": "UTC",
        "source_url": "https://brave.com/search/api/",
        "verified_date": "2026-10-12",
        "use_cases": "Official web search (Brave $5 free credit, ~1,000 req/mo)",
        "not_for": "Paid Brave overage — skip to MiniMax Token Plan, Exa/Tavily, DuckDuckGo",
        "error": None,
    }


def brave_budget_status(
    edition: Optional[str] = None,
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """Current month usage for this edition. Fail closed on store errors."""
    ed = edition or process_edition()
    month = brave_month_key(now)
    cap = brave_monthly_free_requests()
    try:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                "SELECT request_count FROM brave_monthly_usage WHERE edition = ? AND month = ?",
                (ed, month),
            ).fetchone()
        finally:
            conn.close()
        used = int(row[0]) if row else 0
        return _status_from_count(edition=ed, month=month, used=used, cap=cap)
    except Exception as exc:
        logger.warning("[brave_budget] status failed closed: %s", exc)
        return _exhausted_status(edition=ed, month=month, cap=cap, reason=str(exc))


def brave_budget_available(
    edition: Optional[str] = None,
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> bool:
    return bool(brave_budget_status(edition=edition, now=now, db_path=db_path).get("available"))


def reserve_brave_request(
    edition: Optional[str] = None,
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Atomically count one Brave HTTP request if under the monthly cap.

    Returns True only when the increment landed. Callers must not hit
    Brave when this returns False — never exceed the cap.
    """
    ed = edition or process_edition()
    month = brave_month_key(now)
    cap = brave_monthly_free_requests()
    if cap <= 0:
        return False
    now_iso = (now or datetime.now(timezone.utc)).isoformat()
    try:
        conn = _connect(db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT request_count FROM brave_monthly_usage WHERE edition = ? AND month = ?",
                (ed, month),
            ).fetchone()
            used = int(row[0]) if row else 0
            if used >= cap:
                conn.rollback()
                return False
            if row:
                conn.execute(
                    """UPDATE brave_monthly_usage
                       SET request_count = ?, updated_at = ?
                       WHERE edition = ? AND month = ?""",
                    (used + 1, now_iso, ed, month),
                )
            else:
                conn.execute(
                    """INSERT INTO brave_monthly_usage (edition, month, request_count, updated_at)
                       VALUES (?, ?, 1, ?)""",
                    (ed, month, now_iso),
                )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("[brave_budget] reserve failed closed: %s", exc)
        return False


def brave_free_tier_card(
    edition: Optional[str] = None,
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """Shape expected by CostTracker Free-Tier Quotas cards."""
    return brave_budget_status(edition=edition, now=now, db_path=db_path)
