"""Workroom primary-lock guard: durable path, deleted-inode case, family refuse.

The Oct 23 2026 bug: tmp cleanup unlinked /tmp/empire_primary_worker.lock
while Workroom still held flock on the old inode. The family ExecStartPre
ran ``flock -n /tmp/empire_primary_worker.lock true``, which created a
new unlocked file and refused every Max-e / Maxine start.

These tests use a private lock under tmp_path and a health server on an
ephemeral port. They never open 8000 / 8011 / 8012 / 3005.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "deploy" / "workroom_primary_ready.sh"
PROOF = ROOT / "reports" / "2026-10-28_workroom_lock_deleted_inode.md"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"healthy","service":"empirebox-backend"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        return


def _start_health():
    port = _free_port()
    assert port not in {8000, 8011, 8012, 3000, 3005}
    server = HTTPServer(("127.0.0.1", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}/health"


def _run_guard(env: dict, *extra: str) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run(
        [str(GUARD), *extra],
        capture_output=True,
        text=True,
        env=merged,
    )


@pytest.fixture
def lock_env(tmp_path, monkeypatch):
    from app.worker_lock import reset_worker_lock_for_tests

    reset_worker_lock_for_tests()
    workroom = tmp_path / "workroom.lock"
    legacy = tmp_path / "legacy.lock"
    family = tmp_path / "family.lock"
    monkeypatch.delenv("EMPIRE_WORKER_LOCK", raising=False)
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    yield {
        "workroom": workroom,
        "legacy": legacy,
        "family": family,
        "tmp": tmp_path,
    }
    reset_worker_lock_for_tests()


def test_workroom_default_lock_is_not_in_tmp(lock_env, monkeypatch):
    from app.instance_url import LEGACY_WORKROOM_LOCK_PATH, WORKROOM_LOCK_PATH, primary_worker_lock_path
    from app.worker_lock import is_workroom_lock_path

    assert str(WORKROOM_LOCK_PATH) == "/home/rg/empire-data/run/empire_primary_worker.lock"
    assert str(LEGACY_WORKROOM_LOCK_PATH) == "/tmp/empire_primary_worker.lock"
    assert str(primary_worker_lock_path()) == str(WORKROOM_LOCK_PATH)
    assert is_workroom_lock_path("/tmp/empire_primary_worker.lock")
    assert is_workroom_lock_path(WORKROOM_LOCK_PATH)
    assert not is_workroom_lock_path(lock_env["family"])


def test_family_acquire_refuses_workroom_lock(lock_env, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", "/tmp/empire_primary_worker.lock")
    from app.worker_lock import acquire_primary_worker_lock, family_must_refuse_workroom_lock

    assert family_must_refuse_workroom_lock() is True
    assert acquire_primary_worker_lock() is False

    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", "/home/rg/empire-data/run/empire_primary_worker.lock")
    assert family_must_refuse_workroom_lock() is True
    assert acquire_primary_worker_lock() is False


def test_workroom_acquire_holds_and_blocks_second(lock_env, monkeypatch):
    import fcntl

    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_env["workroom"]))
    from app.worker_lock import acquire_primary_worker_lock, reset_worker_lock_for_tests

    assert acquire_primary_worker_lock() is True
    other = open(lock_env["workroom"], "a")
    try:
        with pytest.raises(OSError):
            fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        other.close()
    reset_worker_lock_for_tests()
    assert acquire_primary_worker_lock() is True
    reset_worker_lock_for_tests()


def test_family_acquire_uses_private_lock(lock_env, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_env["family"]))
    from app.worker_lock import acquire_primary_worker_lock, held_lock_file, reset_worker_lock_for_tests

    assert acquire_primary_worker_lock() is True
    assert lock_env["family"].is_file()
    assert held_lock_file() is not None
    reset_worker_lock_for_tests()


def test_apply_amp_paths_rewrites_workroom_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", "/tmp/empire_primary_worker.lock")
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    assert os.environ["EMPIRE_WORKER_LOCK"] == str(tmp_path / "run" / "empire_primary_worker.lock")
    assert (tmp_path / "run").is_dir()


def test_refresh_rebinds_after_unlink(lock_env, monkeypatch):
    import fcntl

    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_env["workroom"]))
    from app.worker_lock import (
        acquire_primary_worker_lock,
        held_lock_file,
        lock_path_matches_fd,
        refresh_primary_worker_lock,
    )

    assert acquire_primary_worker_lock() is True
    handle = held_lock_file()
    assert handle is not None
    lock_env["workroom"].unlink()
    assert not lock_env["workroom"].exists()
    assert lock_path_matches_fd(lock_env["workroom"], handle.fileno()) is False

    assert refresh_primary_worker_lock() is True
    assert lock_env["workroom"].exists()
    new_handle = held_lock_file()
    assert new_handle is not None
    assert lock_path_matches_fd(lock_env["workroom"], new_handle.fileno())

    other = open(lock_env["workroom"], "a")
    try:
        with pytest.raises(OSError):
            fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        other.close()


def test_guard_script_is_executable_and_wired():
    assert os.access(GUARD, os.X_OK)
    amp = (ROOT / "deploy" / "empire-amp.service").read_text(encoding="utf-8")
    maxine = (ROOT / "deploy" / "empire-maxine.service").read_text(encoding="utf-8")
    workroom = (ROOT / "systemd" / "empire-backend.service").read_text(encoding="utf-8")
    assert "workroom_primary_ready.sh" in amp
    assert "workroom_primary_ready.sh" in maxine
    assert "EMPIRE_WORKER_LOCK=/data/amp/run/empire_primary_worker.lock" in amp
    assert "EMPIRE_WORKER_LOCK=/data/maxine/run/empire_primary_worker.lock" in maxine
    assert "EMPIRE_WORKER_LOCK=/home/rg/empire-data/run/empire_primary_worker.lock" in workroom
    assert "--port 8000" in workroom
    assert "--port 8000" not in amp
    assert "--port 8000" not in maxine
    script = GUARD.read_text(encoding="utf-8")
    assert "never create" in script.lower() or "Never create" in script or "O_CREAT" in script
    assert "127.0.0.1:8000" in script
    assert "flock -n /tmp/empire_primary_worker.lock true" not in amp
    assert "flock -n /tmp/empire_primary_worker.lock true" not in maxine


def test_guard_refuses_workroom_lock_as_ours(lock_env):
    result = _run_guard(
        {
            "EMPIRE_EDITION": "maxine",
            "EMPIRE_WORKER_LOCK": "/tmp/empire_primary_worker.lock",
            "EMPIRE_WORKROOM_LOCK": str(lock_env["workroom"]),
            "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
            "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
        }
    )
    assert result.returncode == 1
    assert "must not use the Workroom lock" in result.stderr

    empty = _run_guard(
        {
            "EMPIRE_EDITION": "amp",
            "EMPIRE_WORKER_LOCK": "",
            "EMPIRE_WORKROOM_LOCK": str(lock_env["workroom"]),
            "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
            "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
        }
    )
    assert empty.returncode == 1
    assert "must set EMPIRE_WORKER_LOCK" in empty.stderr


def test_guard_passes_when_lock_held_without_health(lock_env):
    import fcntl

    lock_env["workroom"].write_text("", encoding="utf-8")
    holder = open(lock_env["workroom"], "a")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        result = _run_guard(
            {
                "EMPIRE_EDITION": "amp",
                "EMPIRE_WORKER_LOCK": str(lock_env["family"]),
                "EMPIRE_WORKROOM_LOCK": str(lock_env["workroom"]),
                "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
                "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
            }
        )
        assert result.returncode == 0, result.stderr
    finally:
        holder.close()


def test_guard_uses_health_when_lock_name_is_gone(lock_env):
    server, url = _start_health()
    try:
        result = _run_guard(
            {
                "EMPIRE_EDITION": "amp",
                "EMPIRE_WORKER_LOCK": str(lock_env["family"]),
                "EMPIRE_WORKROOM_LOCK": str(lock_env["workroom"]),
                "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
                "EMPIRE_WORKROOM_HEALTH_URL": url,
            }
        )
        assert result.returncode == 0, result.stderr
        assert "8000 is healthy" in result.stderr or "healthy" in result.stderr
        assert not lock_env["workroom"].exists()
        assert not lock_env["legacy"].exists()
    finally:
        server.shutdown()


def test_guard_fails_when_lock_missing_and_health_down(lock_env):
    result = _run_guard(
        {
            "EMPIRE_EDITION": "amp",
            "EMPIRE_WORKER_LOCK": str(lock_env["family"]),
            "EMPIRE_WORKROOM_LOCK": str(lock_env["workroom"]),
            "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
            "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
        }
    )
    assert result.returncode == 1
    assert "not healthy" in result.stderr
    assert not lock_env["workroom"].exists()


def test_deleted_lock_inode_real_path_proof(lock_env, monkeypatch):
    """Simulate Oct 23: unlink the name while holding the old inode."""
    import fcntl

    from app.worker_lock import (
        acquire_primary_worker_lock,
        held_lock_file,
        refresh_primary_worker_lock,
        reset_worker_lock_for_tests,
    )

    lock_path = lock_env["workroom"]
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_path))
    assert acquire_primary_worker_lock() is True
    handle = held_lock_file()
    assert handle is not None
    old_inode = os.fstat(handle.fileno()).st_ino

    lock_path.unlink()
    assert not lock_path.exists()

    naive = subprocess.run(
        ["flock", "-n", str(lock_path), "true"],
        capture_output=True,
        text=True,
    )
    naive_created = lock_path.exists()
    naive_ok = naive.returncode == 0
    if naive_created:
        lock_path.unlink()

    server, url = _start_health()
    try:
        health_pass = _run_guard(
            {
                "EMPIRE_EDITION": "amp",
                "EMPIRE_WORKER_LOCK": str(lock_env["family"]),
                "EMPIRE_WORKROOM_LOCK": str(lock_path),
                "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
                "EMPIRE_WORKROOM_HEALTH_URL": url,
            }
        )
        health_fail = _run_guard(
            {
                "EMPIRE_EDITION": "amp",
                "EMPIRE_WORKER_LOCK": str(lock_env["family"]),
                "EMPIRE_WORKROOM_LOCK": str(lock_path),
                "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
                "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
            }
        )
        rebound = refresh_primary_worker_lock()
        new_handle = held_lock_file()
        new_inode = os.fstat(new_handle.fileno()).st_ino if new_handle else None
        path_back = lock_path.exists()
        still_held = False
        if path_back:
            probe = open(lock_path, "a")
            try:
                fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                still_held = True
            finally:
                probe.close()
    finally:
        server.shutdown()
        reset_worker_lock_for_tests()

    assert naive_ok, "naive flock must reproduce the Oct 23 create-and-succeed bug"
    assert naive_created, "naive flock created a new unlocked inode"
    assert health_pass.returncode == 0, health_pass.stderr
    assert not Path(str(lock_path) + ".should-not-exist").exists()
    assert health_fail.returncode == 1
    assert rebound is True
    assert path_back
    assert still_held
    assert new_inode is not None and new_inode != old_inode

    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(
        "\n".join(
            [
                "# Workroom lock — deleted-inode proof",
                "",
                "Simulates Oct 23 2026: tmp cleanup unlinked the lock name",
                "while the holder kept flock on the old inode.",
                "",
                f"- old inode (held after unlink): `{old_inode}`",
                f"- naive `flock -n PATH true`: exit `{naive.returncode}` (created new file: `{naive_created}`)",
                f"- new guard + health up: exit `{health_pass.returncode}` (stderr: {health_pass.stderr.strip()!r})",
                f"- new guard + health down: exit `{health_fail.returncode}` (stderr: {health_fail.stderr.strip()!r})",
                f"- Workroom refresh rebound path: `{rebound}` new inode `{new_inode}` held `{still_held}`",
                "",
                "Naive flock creates a new unlocked file and would refuse family start.",
                "The new guard does not create the Workroom lock. Health on loopback",
                "is enough. Workroom re-takes the path so later flock checks see a holder.",
                "",
                json.dumps(
                    {
                        "naive_flock_exit": naive.returncode,
                        "naive_created_file": naive_created,
                        "guard_health_up": health_pass.returncode,
                        "guard_health_down": health_fail.returncode,
                        "refresh_rebound": rebound,
                        "lock_held_after_refresh": still_held,
                    },
                    indent=2,
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    text = PROOF.read_text(encoding="utf-8")
    assert "naive `flock -n PATH true`: exit `0`" in text
    assert "new guard + health up: exit `0`" in text
    assert "new guard + health down: exit `1`" in text
