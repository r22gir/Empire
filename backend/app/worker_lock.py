"""Workroom primary-worker lock: durable path and unlink recovery.

The lock used to live at ``/tmp/empire_primary_worker.lock``. systemd-tmpfiles
can unlink that name while this process still holds the old inode. Family
guards that then ``flock -n`` the path create a new unlocked file and treat
Workroom as down (Oct 23 2026).

Default path is now ``/home/rg/empire-data/run/empire_primary_worker.lock``.
``EMPIRE_WORKER_LOCK`` overrides. After acquire, a 30s refresh loop
re-creates the directory entry if it vanishes.

Re-lock race: between the unlink and a successful refresh (up to ~30s)
another process can create the new name and become a second primary.
If re-lock fails this module logs CRITICAL and keeps the old inode.
"""
from __future__ import annotations

import fcntl
import os
import sys
from pathlib import Path
from typing import IO, Optional

WORKROOM_LOCK_PATH = Path("/home/rg/empire-data/run/empire_primary_worker.lock")
LEGACY_WORKROOM_LOCK_PATH = Path("/tmp/empire_primary_worker.lock")

_worker_lock_file: Optional[IO[str]] = None


def _realpath(path: Path | str) -> str:
    return os.path.realpath(os.path.expanduser(str(path)))


def is_workroom_lock_path(path: Path | str) -> bool:
    """True if *path* is the Workroom lock (durable or legacy /tmp)."""
    cand = _realpath(path)
    return cand in {_realpath(WORKROOM_LOCK_PATH), _realpath(LEGACY_WORKROOM_LOCK_PATH)}


def primary_worker_lock_path() -> Path:
    """Workroom scheduler lock. Default is empire-data/run, not /tmp."""
    explicit = os.getenv("EMPIRE_WORKER_LOCK", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    return WORKROOM_LOCK_PATH


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
    """Take the exclusive Workroom primary lock. Held for process life."""
    global _worker_lock_file
    lock_path = primary_worker_lock_path()
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

    Window: the refresh loop runs every ~30 seconds. Between unlink and a
    successful re-lock, another worker can open the new name and become a
    second primary. If re-lock fails we log CRITICAL and keep the old
    inode so this process still believes it is primary.
    """
    global _worker_lock_file
    if _worker_lock_file is None:
        return False
    lock_path = primary_worker_lock_path()
    if lock_path_matches_fd(lock_path, _worker_lock_file.fileno()):
        return True
    new_handle = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        new_handle = open(lock_path, "w")
        fcntl.flock(new_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        new_handle.write(str(os.getpid()))
        new_handle.flush()
    except (OSError, IOError) as exc:
        if new_handle is not None:
            try:
                new_handle.close()
            except Exception:
                pass
        msg = (
            f"CRITICAL: Workroom primary lock re-lock failed for {lock_path}: {exc}. "
            "This process still holds the old inode. Another worker may have "
            "become a second primary on the new file. Next refresh is ~30s."
        )
        print(msg, file=sys.stderr, flush=True)
        print(msg, flush=True)
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
