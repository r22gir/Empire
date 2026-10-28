"""Primary-worker lock: durable path, family isolation, unlink recovery.

Workroom used to flock ``/tmp/empire_primary_worker.lock``. systemd-tmpfiles
(and other /tmp cleaners) can unlink that name while the holder keeps the
old inode. A later ``flock -n /tmp/empire_primary_worker.lock`` then creates
a *new* unlocked file and looks like Workroom is down (Oct 23 2026, Max-e).

Workroom's default lock now lives under the empire-data run dir, not /tmp.
Family editions (Max-e, Maxine) never acquire a Workroom lock path. Their
systemd ExecStartPre uses ``deploy/workroom_primary_ready.sh``: it must not
create the Workroom lock file, and it may treat ``127.0.0.1:8000/health``
as proof Workroom is up when the name is gone.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import IO, Optional

# Durable Workroom lock. Not under /tmp — tmp cleanup unlinks the name.
WORKROOM_LOCK_PATH = Path("/home/rg/empire-data/run/empire_primary_worker.lock")
# Historical path. Family editions must still refuse it. Workroom re-takes
# this name only if EMPIRE_WORKER_LOCK points here (legacy live unit).
LEGACY_WORKROOM_LOCK_PATH = Path("/tmp/empire_primary_worker.lock")

WORKROOM_HEALTH_URL = "http://127.0.0.1:8000/health"

_worker_lock_file: Optional[IO[str]] = None


def workroom_lock_paths() -> tuple[Path, ...]:
    """Paths family editions must never flock."""
    home_data = Path.home() / "empire-data" / "run" / "empire_primary_worker.lock"
    paths = [WORKROOM_LOCK_PATH, LEGACY_WORKROOM_LOCK_PATH, home_data]
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return tuple(out)


def _norm(path: Path) -> str:
    return os.path.normpath(str(Path(path).expanduser()))


def is_workroom_lock_path(path: Path | str) -> bool:
    """True if *path* is the Workroom primary lock (durable or legacy /tmp)."""
    cand = _norm(Path(path))
    return any(cand == _norm(item) for item in workroom_lock_paths())


def primary_worker_lock_path() -> Path:
    """Scheduler singleton lock for this process.

    Workroom (no ``EMPIRE_DATA_DIR`` and no ``EMPIRE_WORKER_LOCK``) uses
    ``WORKROOM_LOCK_PATH`` under empire-data/run, not ``/tmp``. Family
    editions set ``EMPIRE_DATA_DIR`` or ``EMPIRE_WORKER_LOCK`` so the lock
    is private. They must never point those at a Workroom lock path.
    """
    explicit = os.getenv("EMPIRE_WORKER_LOCK", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    data = os.getenv("EMPIRE_DATA_DIR", "").strip()
    if data:
        return Path(data).expanduser() / "run" / "empire_primary_worker.lock"
    return WORKROOM_LOCK_PATH


def family_must_refuse_workroom_lock(path: Path | None = None) -> bool:
    """Family editions must not acquire the Workroom lock file."""
    from app.edition import is_family_edition

    if not is_family_edition():
        return False
    return is_workroom_lock_path(path if path is not None else primary_worker_lock_path())


def held_lock_file() -> Optional[IO[str]]:
    return _worker_lock_file


def lock_inode(fd: int) -> tuple[int, int]:
    st = os.fstat(fd)
    return (st.st_dev, st.st_ino)


def path_inode(path: Path) -> Optional[tuple[int, int]]:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def lock_path_matches_fd(path: Path, fd: int) -> bool:
    current = path_inode(path)
    if current is None:
        return False
    return current == lock_inode(fd)


def acquire_primary_worker_lock() -> bool:
    """Try to become the primary worker for *this* process's lock path.

    Returns True if this process now holds the lock. The fd is kept in
    ``_worker_lock_file`` for the process lifetime.

    Family editions refuse Workroom lock paths and return False (they
    stay secondary for that path — they must use their own lock file).
    """
    global _worker_lock_file
    lock_path = primary_worker_lock_path()
    if family_must_refuse_workroom_lock(lock_path):
        if _worker_lock_file:
            _worker_lock_file.close()
            _worker_lock_file = None
        print("✗ Family edition refusing Workroom primary lock "
              f"{lock_path} — set EMPIRE_WORKER_LOCK to this instance's path")
        return False
    handle = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(lock_path, "w")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.write(str(os.getpid()))
        handle.flush()
        _worker_lock_file = handle
        return True
    except (OSError, IOError):
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass
        _worker_lock_file = None
        return False


def refresh_primary_worker_lock() -> bool:
    """If we hold the lock but the directory entry vanished, recreate it.

    tmp cleanup unlinks the name; we still hold the old inode. Recreate
    the path and re-flock so family-edition guards see a held file.
    Family editions never rebind onto a Workroom path.
    """
    global _worker_lock_file
    if _worker_lock_file is None:
        return False
    lock_path = primary_worker_lock_path()
    if family_must_refuse_workroom_lock(lock_path):
        return False
    if lock_path_matches_fd(lock_path, _worker_lock_file.fileno()):
        return True
    new_handle = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        new_handle = open(lock_path, "w")
        fcntl.flock(new_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        new_handle.write(str(os.getpid()))
        new_handle.flush()
    except (OSError, IOError):
        if new_handle is not None:
            try:
                new_handle.close()
            except Exception:
                pass
        return False
    old = _worker_lock_file
    _worker_lock_file = new_handle
    try:
        old.close()
    except Exception:
        pass
    return True


def reset_worker_lock_for_tests() -> None:
    """Close any held lock. Tests only."""
    global _worker_lock_file
    if _worker_lock_file is not None:
        try:
            _worker_lock_file.close()
        except Exception:
            pass
        _worker_lock_file = None
