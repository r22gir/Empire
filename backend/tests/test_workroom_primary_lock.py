"""Workroom primary lock: durable default, unlink re-lock, loud failure.

Test-only. Does not touch /home/rg/empire-data or ports 8000 / 3000 / 3005.
"""
from __future__ import annotations

import fcntl
import io
from pathlib import Path

import pytest


@pytest.fixture
def lock_env(tmp_path, monkeypatch):
    from app.worker_lock import reset_worker_lock_for_tests

    reset_worker_lock_for_tests()
    monkeypatch.delenv("EMPIRE_WORKER_LOCK", raising=False)
    path = tmp_path / "run" / "empire_primary_worker.lock"
    yield path
    reset_worker_lock_for_tests()


def test_workroom_default_lock_is_durable(monkeypatch):
    monkeypatch.delenv("EMPIRE_WORKER_LOCK", raising=False)
    from app.worker_lock import (
        LEGACY_WORKROOM_LOCK_PATH,
        WORKROOM_LOCK_PATH,
        is_workroom_lock_path,
        primary_worker_lock_path,
    )

    assert str(WORKROOM_LOCK_PATH) == "/home/rg/empire-data/run/empire_primary_worker.lock"
    assert str(LEGACY_WORKROOM_LOCK_PATH) == "/tmp/empire_primary_worker.lock"
    assert primary_worker_lock_path() == WORKROOM_LOCK_PATH
    assert is_workroom_lock_path("/tmp//empire_primary_worker.lock")
    assert is_workroom_lock_path("/home/rg/empire-data/run/../run/empire_primary_worker.lock")
    assert not is_workroom_lock_path("/data/amp/run/empire_primary_worker.lock")


def test_acquire_holds_and_blocks_second(lock_env, monkeypatch):
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_env))
    from app.worker_lock import acquire_primary_worker_lock, reset_worker_lock_for_tests

    assert acquire_primary_worker_lock() is True
    other = open(lock_env, "a")
    try:
        with pytest.raises(OSError):
            fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        other.close()
    reset_worker_lock_for_tests()


def test_refresh_rebinds_after_unlink(lock_env, monkeypatch):
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_env))
    from app.worker_lock import (
        acquire_primary_worker_lock,
        held_lock_file,
        lock_path_matches_fd,
        refresh_primary_worker_lock,
    )

    assert acquire_primary_worker_lock() is True
    handle = held_lock_file()
    assert handle is not None
    lock_env.unlink()
    assert lock_path_matches_fd(lock_env, handle.fileno()) is False
    assert refresh_primary_worker_lock() is True
    assert lock_env.exists()
    assert lock_path_matches_fd(lock_env, held_lock_file().fileno())
    other = open(lock_env, "a")
    try:
        with pytest.raises(OSError):
            fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        other.close()


def test_refresh_failure_logs_critical(lock_env, monkeypatch, capsys):
    """If the new name is held by someone else, re-lock fails loudly.

    That is the ~30s two-primary window: we still hold the old inode,
    they hold the new file.
    """
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_env))
    from app.worker_lock import (
        acquire_primary_worker_lock,
        held_lock_file,
        refresh_primary_worker_lock,
    )

    assert acquire_primary_worker_lock() is True
    old = held_lock_file()
    lock_env.unlink()
    lock_env.parent.mkdir(parents=True, exist_ok=True)
    usurper = open(lock_env, "w")
    fcntl.flock(usurper.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        assert refresh_primary_worker_lock() is False
        out = capsys.readouterr()
        joined = out.out + out.err
        assert "CRITICAL" in joined
        assert "re-lock failed" in joined
        assert "~30s" in joined
        assert held_lock_file() is old
    finally:
        usurper.close()


def test_unit_and_docs_point_at_durable_path():
    root = Path(__file__).resolve().parents[2]
    unit = (root / "systemd" / "empire-backend.service").read_text(encoding="utf-8")
    assert "EMPIRE_WORKER_LOCK=/home/rg/empire-data/run/empire_primary_worker.lock" in unit
    assert "ExecStartPre=/bin/mkdir -p /home/rg/empire-data/run" in unit
    assert "--port 8000" in unit
    tmpfiles = (root / "deploy" / "tmpfiles.d" / "empire-primary-worker.conf").read_text(encoding="utf-8")
    assert "x /tmp/empire_primary_worker.lock" in tmpfiles
    main = (root / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "_primary_lock_refresh_loop" in main
    assert "asyncio.sleep(30)" in main
