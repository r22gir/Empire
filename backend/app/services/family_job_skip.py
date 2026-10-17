"""Skip family background LLM jobs when the input context is unchanged.

Hashes live under ``{EMPIRE_DATA_DIR}/run/``. Family editions only.
Workroom callers get a no-op (never skip).

The hash is written only after a successful run so a failed tick retries.
Callers should include the date (or the real input payload) in *context*
so a daily job still fires the next morning.
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


def _digest(context: str) -> str:
    return hashlib.sha256((context or "").encode("utf-8")).hexdigest()


def _hash_path(job_key: str) -> Optional[Path]:
    folder = _run_dir()
    if folder is None:
        return None
    return folder / f"{_safe_key(job_key)}.hash"


def skip_if_unchanged(job_key: str, context: str) -> bool:
    """Return True when *context* matches the last successful hash for *job_key*.

    Does not write. Missing data dir or missing hash: do not skip.
    """
    path = _hash_path(job_key)
    if path is None or not path.is_file():
        return False
    digest = _digest(context)
    try:
        previous = path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return previous == digest


def mark_success(job_key: str, context: str) -> None:
    """Persist the hash after a successful run so the next identical tick can skip."""
    path = _hash_path(job_key)
    if path is None:
        return
    tmp = path.with_suffix(".hash.tmp")
    tmp.write_text(_digest(context) + "\n", encoding="utf-8")
    tmp.replace(path)
