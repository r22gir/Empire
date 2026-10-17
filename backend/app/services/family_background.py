"""Family-edition background helpers: skip-when-unchanged and overage guard.

Background kinds never run on overage (brief 8a ``family_overage_allowed``).
Remaining family background LLM jobs hash their input context under
``{EMPIRE_DATA_DIR}/run/`` and skip the model when nothing changed.
The hash includes the calendar date so a new day retries. The file is
written only after a successful run so failures retry.
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("max.family_background")


def _run_dir() -> Optional[Path]:
    from app.edition import data_root_or_none

    root = data_root_or_none()
    if root is None:
        return None
    folder = root / "run"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _hash_path(job_id: str) -> Optional[Path]:
    folder = _run_dir()
    if folder is None:
        return None
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in (job_id or "job"))
    return folder / f"{safe}.hash"


def context_hash(context: str, day: Optional[str] = None) -> str:
    stamp = day if day is not None else date.today().isoformat()
    payload = f"{stamp}\n{context or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def skip_if_unchanged(job_id: str, context: str, day: Optional[str] = None) -> bool:
    """Return True when ``context`` + date match the last *successful* hash.

    Does not write. Missing data dir, missing file, or first run → False.
    """
    path = _hash_path(job_id)
    if path is None or not path.is_file():
        return False
    digest = context_hash(context, day=day)
    try:
        previous = path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if previous == digest:
        logger.info("Family background skip-unchanged: %s", job_id)
        return True
    return False


def mark_unchanged(job_id: str, context: str, day: Optional[str] = None) -> None:
    """Record a successful run so the next identical day+input can skip."""
    path = _hash_path(job_id)
    if path is None:
        return
    try:
        path.write_text(context_hash(context, day=day), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not store skip-unchanged hash for %s: %s", job_id, exc)


def family_background_cap_message(*, kind: str = "desk_task", source: str = "scheduler") -> Optional[str]:
    """Refuse family background work over the 20% base (never overage)."""
    from app.edition import is_family_edition
    from app.services.instance_usage import enforce_usage_cap

    if not is_family_edition():
        return None
    return enforce_usage_cap(kind=kind, source=source, text="")


def family_desk_schedule_keys() -> list[str]:
    raw = (os.getenv("FAMILY_DESK_SCHEDULE") or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]
