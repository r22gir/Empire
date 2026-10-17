"""Last-seen founder activity for the family soft cap.

Rafael's rule: brothers may exceed their 20% only while he is inactive
and his protected reserve is intact. Studio records when he last used
Max (chat, voice, PIN, Cloudflare Access) so family editions can read a
signal file in their own data dir.

No personal data, message content, or secrets are stored.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.founder_activity")

SCHEMA = 1
DEFAULT_ACTIVE_WINDOW_MIN = 30
WRITE_INTERVAL_S = 30

_lock = threading.Lock()
_last_active_at: Optional[datetime] = None
_last_source: str = ""
_last_disk_write_mono: float = 0.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    stamp = dt or _now()
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(float(raw)))
    except ValueError:
        return default


def active_window_min() -> int:
    return _int_env("FOUNDER_ACTIVE_WINDOW_MIN", DEFAULT_ACTIVE_WINDOW_MIN)


def data_root() -> Path:
    raw = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser()
    from app.services.data_paths import data_root as _backend_data_root

    return _backend_data_root()


def activity_path() -> Path:
    return data_root() / "run" / "founder_activity.json"


def _atomic_write(path: Path, payload: dict[str, Any], *, file_mode: int = 0o600) -> None:
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
            os.chmod(path, file_mode)
        except OSError:
            pass
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _load_from_disk() -> Optional[datetime]:
    path = activity_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = data.get("last_active_at") if isinstance(data, dict) else None
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def last_active_at() -> Optional[datetime]:
    global _last_active_at
    with _lock:
        if _last_active_at is not None:
            return _last_active_at
    loaded = _load_from_disk()
    if loaded is None:
        return None
    with _lock:
        if _last_active_at is None:
            _last_active_at = loaded
        return _last_active_at


def founder_is_active(now: Optional[datetime] = None) -> bool:
    stamp = last_active_at()
    if stamp is None:
        return False
    current = now or _now()
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    window = timedelta(minutes=active_window_min())
    return current - stamp <= window


def mark_founder_active(source: str = "studio") -> dict[str, Any]:
    """Record founder activity. Disk writes are rate-limited to 1/30s.

    Always updates the in-memory stamp. Writes ``founder_activity.json``
    and the family signal files when the rate limit allows, and always
    on the first mark in this process.
    """
    global _last_active_at, _last_source, _last_disk_write_mono
    now = _now()
    src = (source or "studio").strip()[:40] or "studio"
    should_write = False
    with _lock:
        _last_active_at = now
        _last_source = src
        elapsed = time.monotonic() - _last_disk_write_mono
        if _last_disk_write_mono == 0.0 or elapsed >= WRITE_INTERVAL_S:
            _last_disk_write_mono = time.monotonic()
            should_write = True
    snapshot = {
        "schema": SCHEMA,
        "last_active_at": _iso(now),
        "source": src,
    }
    if should_write:
        try:
            _atomic_write(activity_path(), snapshot)
        except OSError as exc:
            logger.debug("founder_activity disk write skipped: %s", exc)
        try:
            from app.services.family_signal import write_family_signals

            write_family_signals(now=now)
        except Exception as exc:
            logger.debug("family signal write after founder activity skipped: %s", exc)
    return snapshot


def maybe_mark_founder_active(is_founder: bool, source: str = "studio") -> None:
    if not is_founder:
        return
    try:
        mark_founder_active(source)
    except Exception:
        logger.debug("mark_founder_active failed", exc_info=True)
