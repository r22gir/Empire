"""Atomic writes, timestamped backups, and an edition-scoped fcntl lock.

Every company-setup read-merge-write (overlay, progress, secrets, invites,
webhook status) goes through these helpers. Process environment / systemd
secrets files are never written here.
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import stat
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("max.company_setup")


def in_test() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("EMPIRE_TEST_GUARD_LOG"))


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def ensure_dir(path: Path, mode: int = 0o700) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, mode)
    except OSError:
        pass
    return path


def backup_file(path: Path) -> Path | None:
    """Copy ``path`` to ``path.name.<utc>.bak`` next to it. No-op if missing."""
    if not path.exists() or not path.is_file():
        return None
    dest = path.with_name(f"{path.name}.{timestamp_utc()}.bak")
    dest.write_bytes(path.read_bytes())
    try:
        os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return dest


def atomic_write(path: Path, data: Any, *, mode: int = 0o600, backup: bool = True) -> None:
    """Write JSON atomically. Backs up the previous file first."""
    ensure_dir(path.parent, 0o700)
    if backup:
        backup_file(path)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".company-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        try:
            os.chmod(path, mode)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_json_list(path: Path) -> list[Any]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


@contextmanager
def edition_lock(lock_dir: Path) -> Iterator[None]:
    """Exclusive lock for one edition's company-setup writes."""
    ensure_dir(lock_dir, 0o700)
    lock_path = lock_dir / ".company-setup.lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
