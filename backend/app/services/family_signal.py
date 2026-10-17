"""Write founder-activity + reserve signal into each family data dir.

Studio only. Family editions (Max-e / Maxine) read
``<dir>/founder-signal/status.json`` from their own tree; they cannot
read Studio's data dir. This module never imports amp or maxine code.

Schema (no extra fields, no personal data, no secrets)::

    {
      "schema": 1,
      "updated_at": "...Z",
      "founder_active": bool,
      "founder_last_active_at": "...Z" | null,
      "reserve_ok": bool,
      "overage_allowed": bool,
      "reason": "founder_active" | "reserve_low" | "inputs_unreadable" | "inactive_reserve_ok"
    }

``overage_allowed`` is (not founder_active) and reserve_ok.
Brothers start at 20% each; past 20% they may continue only while
Rafael is inactive and his reserve is intact. Background jobs never
run on overage (enforced on the family side).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.family_signal")

SCHEMA = 1
SIGNAL_REL = Path("founder-signal") / "status.json"
STATUS_KEYS = (
    "schema",
    "updated_at",
    "founder_active",
    "founder_last_active_at",
    "reserve_ok",
    "overage_allowed",
    "reason",
)
DEFAULT_FAMILY_DIRS = "/data/amp,/data/maxine"
DEFAULT_RESERVE_PCT = 40.0
DEFAULT_BROTHER_CEILING_PCT = 40.0
DEFAULT_POOL_FLOOR = 10_000_000.0
REASONS = (
    "founder_active",
    "reserve_low",
    "inputs_unreadable",
    "inactive_reserve_ok",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    stamp = dt or _now()
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def reserve_pct() -> float:
    return min(100.0, _float_env("FOUNDER_RESERVE_PCT", DEFAULT_RESERVE_PCT))


def brother_ceiling_pct() -> float:
    """Family overage ceiling (default 40%). 8a/8b enforce it; Studio only publishes the signal."""
    return min(100.0, _float_env("FAMILY_BROTHER_CEILING_PCT", DEFAULT_BROTHER_CEILING_PCT))


def pool_floor() -> float:
    return _float_env("EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS", DEFAULT_POOL_FLOOR)


def family_signal_dirs() -> list[Path]:
    raw = (os.getenv("FAMILY_SIGNAL_DIRS") or DEFAULT_FAMILY_DIRS).strip()
    out: list[Path] = []
    seen: set[str] = set()
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        path = Path(text).expanduser()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _month_tokens_from_usage_db(path: Path, month: str) -> tuple[int, bool]:
    """Return (tokens, readable). Missing file is (0, True). Corrupt file is (0, False)."""
    if not path.is_file():
        return 0, True
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens
                FROM llm_usage
                WHERE month = ? AND blocked = 0
                """,
                (month,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return 0, False
    except OSError:
        return 0, False
    tokens = int(row[0] or 0) + int(row[1] or 0)
    return tokens, True


def _studio_usage_db() -> Optional[Path]:
    raw = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser() / "usage" / "usage.db"
    return path


def _meter_month_tokens(month: str) -> tuple[int, bool]:
    """Studio MiniMax jsonl (workroom + family logs under MINIMAX_METER_DIR)."""
    try:
        from app.services.minimax_meter import totals

        tot = totals(month=month)
        return int(tot.get("text_tokens") or 0), True
    except Exception:
        return 0, False


def _plan_reserve_ok() -> tuple[bool, bool]:
    """(plan_ok, readable). Unreadable remains => not ok.

    When the MiniMax /token_plan/remains endpoint is readable, plan usage
    must stay below the existing hard-stop margin. Stubs in tests set
    MINIMAX_REMAINS_STUB (never live HTTP from this module's tests).
    """
    try:
        from app.services.minimax_meter import _plan_snapshot, plan_hard_stop_pct

        snap = _plan_snapshot()
        remains = (snap or {}).get("remains") or {}
        if not remains.get("available"):
            return False, False
        stop = plan_hard_stop_pct()
        used = remains.get("used_pct")
        remaining = remains.get("remaining_pct")
        if used is not None and float(used) >= stop:
            return False, True
        if remaining is not None and float(remaining) <= max(0.0, 100.0 - stop):
            return False, True
        return True, True
    except Exception:
        return False, False


def recorded_month_tokens(month: Optional[str] = None) -> dict[str, Any]:
    """Sum Studio meter + family usage DBs for the UTC month."""
    month = month or _now().strftime("%Y-%m")
    readable = True
    tokens = 0
    meter_tokens, meter_ok = _meter_month_tokens(month)
    if not meter_ok:
        readable = False
    else:
        tokens += meter_tokens
    dbs: list[Path] = []
    studio_db = _studio_usage_db()
    if studio_db is not None:
        dbs.append(studio_db)
    for root in family_signal_dirs():
        dbs.append(root / "usage" / "usage.db")
    seen: set[str] = set()
    for db in dbs:
        key = str(db)
        if key in seen:
            continue
        seen.add(key)
        part, ok = _month_tokens_from_usage_db(db, month)
        if not ok:
            readable = False
            continue
        tokens += part
    return {"month": month, "tokens": tokens, "readable": readable}


def compute_status(now: Optional[datetime] = None) -> dict[str, Any]:
    current = now or _now()
    from app.services.founder_activity import founder_is_active, last_active_at

    last = last_active_at()
    active = founder_is_active(current)
    usage = recorded_month_tokens(current.strftime("%Y-%m"))
    inputs_ok = bool(usage["readable"])
    plan_ok, plan_readable = _plan_reserve_ok()
    if not plan_readable:
        inputs_ok = False

    pool = max(float(usage["tokens"]), pool_floor())
    remaining = max(0.0, pool - float(usage["tokens"]))
    reserve_share = remaining / pool if pool else 0.0
    reserve_needed = reserve_pct() / 100.0
    usage_reserve_ok = reserve_share + 1e-12 >= reserve_needed
    reserve_ok = bool(inputs_ok and usage_reserve_ok and plan_ok)
    overage_allowed = (not active) and reserve_ok

    if not inputs_ok:
        reason = "inputs_unreadable"
    elif active:
        reason = "founder_active"
    elif not reserve_ok:
        reason = "reserve_low"
    else:
        reason = "inactive_reserve_ok"

    last_iso = _iso(last) if last is not None else None
    return {
        "schema": SCHEMA,
        "updated_at": _iso(current),
        "founder_active": bool(active),
        "founder_last_active_at": last_iso,
        "reserve_ok": bool(reserve_ok),
        "overage_allowed": bool(overage_allowed),
        "reason": reason,
    }


def _status_only(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in STATUS_KEYS}


def write_family_signals(now: Optional[datetime] = None) -> dict[str, Any]:
    """Write status.json into each existing family dir. Missing dirs are skipped."""
    status = _status_only(compute_status(now=now))
    for root in family_signal_dirs():
        if not root.exists():
            continue
        if not root.is_dir():
            continue
        dest = root / SIGNAL_REL
        try:
            _atomic_write(dest, status)
        except OSError as exc:
            logger.debug("family signal skip %s: %s", dest, exc)
    return status


def read_signal(root: Path) -> Optional[dict[str, Any]]:
    path = Path(root) / SIGNAL_REL
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data
