"""Serialize schema changes across uvicorn workers.

The primary-worker lock is held for the life of one process, so the other
worker cannot take it to wait. This lock is acquired only while a migration
runs, then released. A second worker blocks until the first finishes, then
runs the same idempotent SQL.
"""
from __future__ import annotations

import fcntl
import threading
from contextlib import contextmanager

_guard = threading.Lock()
_depth = 0
_held = None


def migration_lock_path():
    from app.instance_url import primary_worker_lock_path

    return primary_worker_lock_path().with_name("empire_schema_migration.lock")


@contextmanager
def migration_lock():
    """Blocking exclusive lock. Re-entrant in the process that already holds it."""
    global _depth, _held
    with _guard:
        outer = _depth == 0
        if outer:
            path = migration_lock_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            fh = open(path, "a")
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            _held = fh
        _depth += 1
    try:
        yield
    finally:
        with _guard:
            _depth -= 1
            if _depth == 0 and _held is not None:
                fcntl.flock(_held.fileno(), fcntl.LOCK_UN)
                _held.close()
                _held = None
