"""Atomic writes, timestamped backups, and an edition-scoped fcntl lock.

Every company-setup read-merge-write (overlay, secrets, invites) goes
through these helpers. Process environment / systemd secrets files are
never written here.

Backups keep the last 10 per file and drop anything older than 7 days.
``config/business.json`` backups live at ``~/backups/company-setup/``
(outside the repo). Webhook status and progress files are not backed up.
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import stat
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("max.company_setup")

BACKUP_KEEP = 10
BACKUP_MAX_AGE_DAYS = 7


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


def workroom_backup_dir() -> Path:
    """Off-repo backups for ``config/business.json``. Tests stay under EMPIRE_DATA_DIR."""
    if in_test():
        raw = (os.getenv("COMPANY_SETUP_BACKUP_DIR") or "").strip()
        if raw:
            return ensure_dir(Path(raw), 0o700)
        root = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
        if root:
            return ensure_dir(Path(root) / "backups" / "company-setup", 0o700)
        return ensure_dir(Path(tempfile.gettempdir()) / "company-setup-backups", 0o700)
    return ensure_dir(Path.home() / "backups" / "company-setup", 0o700)


def existing_mode(path: Path, default: int = 0o600) -> int:
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return default


def rotate_backups(directory: Path, filename: str) -> None:
    """Keep the last ``BACKUP_KEEP`` backups of ``filename`` that are under 7 days old."""
    if not directory.is_dir():
        return
    files = [p for p in directory.glob(f"{filename}.*.bak") if p.is_file()]
    cutoff = time.time() - BACKUP_MAX_AGE_DAYS * 86400
    fresh: list[tuple[float, Path]] = []
    for path in files:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            try:
                path.unlink()
            except OSError:
                pass
        else:
            fresh.append((mtime, path))
    fresh.sort(key=lambda item: item[0], reverse=True)
    for _, path in fresh[BACKUP_KEEP:]:
        try:
            path.unlink()
        except OSError:
            pass


def backup_file(path: Path, *, backup_dir: Path | None = None) -> Path | None:
    """Copy ``path`` to ``<name>.<utc>.bak`` then rotate. No-op if missing."""
    if not path.exists() or not path.is_file():
        return None
    dest_dir = ensure_dir(backup_dir or path.parent, 0o700)
    dest = dest_dir / f"{path.name}.{timestamp_utc()}.bak"
    dest.write_bytes(path.read_bytes())
    try:
        os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    rotate_backups(dest_dir, path.name)
    return dest


def atomic_write(
    path: Path,
    data: Any,
    *,
    mode: int = 0o600,
    backup: bool = True,
    backup_dir: Path | None = None,
) -> None:
    """Write JSON atomically. Optional timestamped backup of the previous file."""
    ensure_dir(path.parent, 0o700)
    if backup:
        backup_file(path, backup_dir=backup_dir)
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
