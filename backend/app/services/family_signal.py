"""Write founder-activity + reserve signal into each family data dir.

Studio only. Family editions (Max-e / Maxine) read
``<dir>/founder-signal/status.json`` from their own tree; they cannot
read Studio's data dir. This module never imports amp or maxine code.

Schema 1 (required keys; extra optional fields are backward compatible
because family readers ignore unknown fields)::

    {
      "schema": 1,
      "updated_at": "...Z",
      "founder_active": bool,
      "founder_last_active_at": "...Z" | null,
      "reserve_ok": bool,
      "overage_allowed": bool,
      "reason": "founder_active" | "reserve_low" | "remains_unavailable"
               | "remains_stale" | "inactive_reserve_ok"
    }

Optional extras (informational / family ceiling)::

    remaining_pct, used_tokens, month, brother_ceiling_pct

``reserve_ok`` is MiniMax plan ``remaining_pct >= FOUNDER_RESERVE_PCT``
(default 40). Token sums are informational only and never drive reserve.
Unavailable or stale remains fail closed.

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
REQUIRED_STATUS_KEYS = (
    "schema",
    "updated_at",
    "founder_active",
    "founder_last_active_at",
    "reserve_ok",
    "overage_allowed",
    "reason",
)
# Schema 1 extras: family readers ignore unknown fields.
OPTIONAL_STATUS_KEYS = (
    "brother_ceiling_pct",
    "remaining_pct",
    "used_tokens",
    "month",
)
STATUS_KEYS = REQUIRED_STATUS_KEYS + OPTIONAL_STATUS_KEYS
DEFAULT_FAMILY_DIRS = "/data/amp,/data/maxine"
DEFAULT_RESERVE_PCT = 40.0
DEFAULT_BROTHER_CEILING_PCT = 40.0
DEFAULT_POOL_FLOOR = 10_000_000.0
DEFAULT_REMAINS_MAX_AGE_S = 120.0
REASONS = (
    "founder_active",
    "reserve_low",
    "remains_unavailable",
    "remains_stale",
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


def remains_max_age_s() -> float:
    return max(1.0, _float_env("FOUNDER_REMAINS_MAX_AGE_S", DEFAULT_REMAINS_MAX_AGE_S))


def brother_ceiling_pct() -> float:
    """Family overage ceiling. 8a/8b enforce it; Studio only publishes it.

    Prefer ``FAMILY_ABSOLUTE_MAX_PCT`` (amp/maxine). Fall back to
    ``FAMILY_BROTHER_CEILING_PCT`` when only that is set.
    """
    abs_raw = (os.getenv("FAMILY_ABSOLUTE_MAX_PCT") or "").strip()
    if abs_raw:
        return min(100.0, _float_env("FAMILY_ABSOLUTE_MAX_PCT", DEFAULT_BROTHER_CEILING_PCT))
    return min(100.0, _float_env("FAMILY_BROTHER_CEILING_PCT", DEFAULT_BROTHER_CEILING_PCT))


def pool_floor() -> float:
    """Informational only — not used for reserve_ok."""
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


def _reserve_from_remains() -> dict[str, Any]:
    """reserve_ok from MiniMax remaining_pct. Fail closed if missing or stale.

    Uses the existing fetch_remains / _plan_snapshot path (stubs via
    MINIMAX_REMAINS_STUB in tests; never live HTTP from this module's tests).
    """
    remaining: Optional[float] = None
    available = False
    stale = False
    try:
        from app.services.minimax_meter import _plan_snapshot, _stub_snapshot

        snap = _plan_snapshot()
        remains = (snap or {}).get("remains") or {}
        available = bool(remains.get("available") and remains.get("ok", True))
        raw_remaining = remains.get("remaining_pct")
        if raw_remaining is not None:
            remaining = float(raw_remaining)
        stale = bool(remains.get("stale"))
        stub = _stub_snapshot()
        if stub is None:
            try:
                from app.services.minimax_quota import remains_cache_age_s

                age = remains_cache_age_s()
            except Exception:
                age = None
            max_age = remains_max_age_s()
            if age is None or age > max_age:
                stale = True
    except Exception:
        available = False
        remaining = None
        stale = False

    if stale and remaining is not None:
        return {
            "reserve_ok": False,
            "readable": False,
            "stale": True,
            "remaining_pct": remaining,
            "why": "remains_stale",
        }
    if not available or remaining is None:
        return {
            "reserve_ok": False,
            "readable": False,
            "stale": False,
            "remaining_pct": remaining,
            "why": "remains_unavailable",
        }
    needed = reserve_pct()
    ok = remaining + 1e-12 >= needed
    return {
        "reserve_ok": bool(ok),
        "readable": True,
        "stale": False,
        "remaining_pct": remaining,
        "why": None if ok else "reserve_low",
    }


def recorded_month_tokens(month: Optional[str] = None) -> dict[str, Any]:
    """Sum Studio meter + family usage DBs for the UTC month (informational)."""
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
    reserve = _reserve_from_remains()
    remaining_pct = reserve.get("remaining_pct")
    reserve_ok = bool(reserve["reserve_ok"])
    overage_allowed = (not active) and reserve_ok

    if not reserve["readable"]:
        reason = reserve["why"] or "remains_unavailable"
    elif active:
        reason = "founder_active"
    elif not reserve_ok:
        reason = "reserve_low"
    else:
        reason = "inactive_reserve_ok"

    last_iso = _iso(last) if last is not None else None
    remaining_out: Optional[float] = None
    if remaining_pct is not None:
        remaining_out = round(float(remaining_pct), 2)
    return {
        "schema": SCHEMA,
        "updated_at": _iso(current),
        "founder_active": bool(active),
        "founder_last_active_at": last_iso,
        "reserve_ok": bool(reserve_ok),
        "overage_allowed": bool(overage_allowed),
        "reason": reason,
        "brother_ceiling_pct": brother_ceiling_pct(),
        "remaining_pct": remaining_out,
        "used_tokens": int(usage.get("tokens") or 0),
        "month": usage.get("month"),
    }


def _status_only(payload: dict[str, Any]) -> dict[str, Any]:
    out = {key: payload[key] for key in REQUIRED_STATUS_KEYS}
    for key in OPTIONAL_STATUS_KEYS:
        if key in payload:
            out[key] = payload[key]
    return out


def write_family_signals(now: Optional[datetime] = None) -> dict[str, Any]:
    """Write status.json into each existing family dir. Missing dirs are skipped.

    Sync. Call from the 60s loop via ``write_family_signals_offthread`` so the
    MiniMax remains probe (up to 3s) never blocks the Studio event loop.
    """
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


async def write_family_signals_offthread(now: Optional[datetime] = None) -> dict[str, Any]:
    """Run remains probe + file writes off the event loop."""
    import asyncio

    return await asyncio.to_thread(write_family_signals, now)


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
