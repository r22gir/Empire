"""Skip family background LLM jobs when the input context is unchanged.

Hashes live under ``{EMPIRE_DATA_DIR}/run/``. Family editions only.
Workroom callers get a no-op (never skip).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional


def _run_dir() -> Optional[Path]:
    from app.edition import data_root_or_none, is_family_edition

    if not is_family_edition():
        return None
    root = data_root_or_none()
    if root is None:
        return None
    path = root / "run"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_key(job_key: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", job_key or "").strip("._")
    return (cleaned or "job")[:80]


def skip_if_unchanged(job_key: str, context: str) -> bool:
    """Return True when *context* matches the last stored hash for *job_key*.

    On a miss (first run or changed context) the new hash is stored and
    the caller should run. Missing data dir: do not skip.
    """
    folder = _run_dir()
    if folder is None:
        return False
    path = folder / f"{_safe_key(job_key)}.hash"
    digest = hashlib.sha256((context or "").encode("utf-8")).hexdigest()
    previous = ""
    if path.is_file():
        try:
            previous = path.read_text(encoding="utf-8").strip()
        except OSError:
            previous = ""
    if previous == digest:
        return True
    tmp = path.with_suffix(".hash.tmp")
    tmp.write_text(digest + "\n", encoding="utf-8")
    tmp.replace(path)
    return False
