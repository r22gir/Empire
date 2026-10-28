"""Family isolation for the Workroom primary-worker lock.

Workroom's default lock path is unchanged: ``/tmp/empire_primary_worker.lock``.
A later Workroom change may move that file to
``/home/rg/empire-data/run/empire_primary_worker.lock``. Family editions
(Max-e, Maxine) must refuse **both** paths. They never flock Workroom's
lock. Path compares use ``os.path.realpath`` so ``/tmp//`` and similar
spellings do not slip through.

Family editions use a private lock under ``/data/<instance>/run``. Holding
that file is not becoming the Workroom primary worker. Primary-only jobs
stay hard-disabled on family editions even when Workroom is down.

This module does not change Workroom's default and does not re-bind a
deleted lock name. That belongs on the Workroom branch.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import IO, Optional

# Workroom default — unchanged on this family branch.
WORKROOM_LOCK_PATH = Path("/tmp/empire_primary_worker.lock")
# Future / existing durable Workroom path. Family editions refuse this too.
DURABLE_WORKROOM_LOCK_PATH = Path("/home/rg/empire-data/run/empire_primary_worker.lock")
LEGACY_WORKROOM_LOCK_PATH = WORKROOM_LOCK_PATH

WORKROOM_HEALTH_URL = "http://127.0.0.1:8000/health"

# Started only on the Workroom primary worker. Family editions never start
# these, even if they hold ``/data/<instance>/run/empire_primary_worker.lock``.
PRIMARY_JOBS = (
    "telegram_bot",
    "gmail_email_polling",
    "desk_scheduler",
    "social_publish_loop",
    "max_scheduler",
    "max_monitor",
    "openclaw_worker",
    "vendorops_alert_runner",
    "task_auto_worker",
    "startup_probes",
    "growth_jobs",
)

# Source markers in ``app.main.start_background_services`` that must sit
# after the family / secondary skip. Gmail polling and growth jobs start
# from the scheduler / monitor, not as separate create_task calls.
PRIMARY_JOB_START_MARKERS = (
    "telegram_bot.start_webhook_mode",
    "desk_scheduler.start",
    "_social_publish_loop",
    "max_scheduler.start",
    "max_monitor.start",
    "openclaw_worker_loop",
    "vendorops_alert_runner.start",
    "_task_auto_worker",
    "_startup_probes",
)

_worker_lock_file: Optional[IO[str]] = None


def workroom_lock_paths() -> tuple[Path, ...]:
    """Paths family editions must never flock."""
    home_data = Path.home() / "empire-data" / "run" / "empire_primary_worker.lock"
    paths = [WORKROOM_LOCK_PATH, DURABLE_WORKROOM_LOCK_PATH, home_data]
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        key = _realpath(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return tuple(out)


def _realpath(path: Path | str) -> str:
    """Resolve extra slashes, ``..``, and symlinks. File need not exist."""
    return os.path.realpath(os.path.expanduser(str(path)))


def is_workroom_lock_path(path: Path | str) -> bool:
    """True if *path* is a Workroom primary lock (``/tmp`` or durable)."""
    cand = _realpath(path)
    return any(cand == _realpath(item) for item in workroom_lock_paths())


def primary_worker_lock_path() -> Path:
    """Scheduler singleton lock for this process.

    Workroom default stays ``/tmp/empire_primary_worker.lock``. Family
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


def primary_jobs_blocked_reason(holds_instance_lock: bool = False) -> Optional[str]:
    """Why Workroom primary jobs must not start. None means they may start.

    Family editions are always blocked, including when they hold their
    own ``/data/<instance>/run`` lock and Workroom is down.
    """
    from app.edition import is_family_edition

    if is_family_edition():
        return "family_edition"
    if not holds_instance_lock:
        return "not_primary_worker"
    return None


def should_start_primary_jobs(holds_instance_lock: bool = False) -> bool:
    """True only for the Workroom primary worker.

    Family editions always return False. Holding a private instance lock
    is not becoming the Workroom primary.
    """
    return primary_jobs_blocked_reason(holds_instance_lock) is None


def held_lock_file() -> Optional[IO[str]]:
    return _worker_lock_file


def acquire_primary_worker_lock() -> bool:
    """Try to become the primary worker for *this* process's lock path.

    Family editions refuse both Workroom lock paths and return False.
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


def reset_worker_lock_for_tests() -> None:
    """Close any held lock. Tests only."""
    global _worker_lock_file
    if _worker_lock_file is not None:
        try:
            _worker_lock_file.close()
        except Exception:
            pass
        _worker_lock_file = None
