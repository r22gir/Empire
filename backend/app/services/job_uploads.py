"""Safe paths for files stored under ~/empire-data/uploads/jobs/<job_id>/."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path


_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def data_root() -> Path:
    return Path(os.getenv("EMPIRE_DATA_DIR") or (Path.home() / "empire-data"))


def job_upload_dir(job_id: str) -> Path:
    safe_job = Path(str(job_id or "")).name
    if not safe_job or safe_job in {".", ".."} or "/" in str(job_id) or "\\" in str(job_id):
        raise ValueError("invalid job id")
    return (data_root() / "uploads" / "jobs" / safe_job).resolve()


def safe_job_filename(filename: str | None) -> str:
    raw = Path(filename or "").name
    raw = raw.replace("\x00", "")
    if not raw or raw in {".", ".."}:
        return f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cleaned = _UNSAFE.sub("_", raw).strip("._")
    return cleaned or f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def resolve_job_upload(job_id: str, filename: str) -> Path | None:
    """Return the file path if it exists under the job upload dir. Never escapes."""
    try:
        root = job_upload_dir(job_id)
    except ValueError:
        return None
    name = Path(str(filename or "")).name
    if not name or name in {".", ".."}:
        return None
    dest = (root / name).resolve()
    try:
        dest.relative_to(root)
    except ValueError:
        return None
    if dest.is_file():
        return dest
    return None
