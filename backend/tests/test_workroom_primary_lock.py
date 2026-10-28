"""Family Workroom-ready guard: no flock steal, realpath, both Workroom paths.

The Oct 23 2026 bug: tmp cleanup unlinked /tmp/empire_primary_worker.lock
while Workroom still held flock on the old inode. The family ExecStartPre
ran ``flock -n /tmp/empire_primary_worker.lock true``, which created a
new unlocked file and could briefly take Workroom's exclusive lock.

These tests use a private lock under tmp_path and a health server on an
ephemeral port. They never open 8000 / 8011 / 8012 / 3005.

The report this file writes is a **test-only** simulation. A real-path
check on the Dell comes later, after a backup and Rafael's OK.
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


def _run_guard(env: dict) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run(
        [str(GUARD)],
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


def test_workroom_default_lock_stays_tmp(lock_env):
    from app.instance_url import WORKROOM_LOCK_PATH, primary_worker_lock_path
    from app.worker_lock import (
        DURABLE_WORKROOM_LOCK_PATH,
        is_workroom_lock_path,
        primary_worker_lock_path as worker_path,
    )

    assert str(WORKROOM_LOCK_PATH) == "/tmp/empire_primary_worker.lock"
    assert str(primary_worker_lock_path()) == "/tmp/empire_primary_worker.lock"
    assert str(worker_path()) == "/tmp/empire_primary_worker.lock"
    assert is_workroom_lock_path("/tmp/empire_primary_worker.lock")
    assert is_workroom_lock_path("/tmp//empire_primary_worker.lock")
    assert is_workroom_lock_path(DURABLE_WORKROOM_LOCK_PATH)
    assert is_workroom_lock_path("/home/rg/empire-data/run/../run/empire_primary_worker.lock")
    assert not is_workroom_lock_path(lock_env["family"])


def test_family_acquire_refuses_both_workroom_paths(lock_env, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", "/tmp//empire_primary_worker.lock")
    from app.worker_lock import acquire_primary_worker_lock, family_must_refuse_workroom_lock

    assert family_must_refuse_workroom_lock() is True
    assert acquire_primary_worker_lock() is False

    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", "/home/rg/empire-data/run/empire_primary_worker.lock")
    assert family_must_refuse_workroom_lock() is True
    assert acquire_primary_worker_lock() is False


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
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", "/tmp//empire_primary_worker.lock")
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    assert os.environ["EMPIRE_WORKER_LOCK"] == str(tmp_path / "run" / "empire_primary_worker.lock")
    assert (tmp_path / "run").is_dir()


def test_guard_script_is_executable_and_wired():
    assert os.access(GUARD, os.X_OK)
    amp = (ROOT / "deploy" / "empire-amp.service").read_text(encoding="utf-8")
    maxine = (ROOT / "deploy" / "empire-maxine.service").read_text(encoding="utf-8")
    workroom = (ROOT / "systemd" / "empire-backend.service").read_text(encoding="utf-8")
    script = GUARD.read_text(encoding="utf-8")
    assert "workroom_primary_ready.sh" in amp
    assert "workroom_primary_ready.sh" in maxine
    assert "EMPIRE_WORKER_LOCK=/data/amp/run/empire_primary_worker.lock" in amp
    assert "EMPIRE_WORKER_LOCK=/data/maxine/run/empire_primary_worker.lock" in maxine
    assert "EMPIRE_WORKER_LOCK=/home/rg/empire-data/run/empire_primary_worker.lock" not in workroom
    assert "--port 8000" in workroom
    assert "--port 8000" not in amp
    assert "--port 8000" not in maxine
    live = [ln for ln in script.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert not any("flock" in ln for ln in live)
    assert "/proc/locks" in script
    assert "127.0.0.1:8000" in script
    assert "realpath" in script


def test_guard_refuses_workroom_lock_as_ours(lock_env):
    result = _run_guard(
        {
            "EMPIRE_EDITION": "maxine",
            "EMPIRE_WORKER_LOCK": "/tmp//empire_primary_worker.lock",
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


def test_guard_passes_when_lock_held_without_taking_it(lock_env):
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
        # Guard must not have stolen the exclusive lock.
        probe = open(lock_env["workroom"], "a")
        try:
            with pytest.raises(OSError):
                fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            probe.close()
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
        assert "healthy" in result.stderr
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


def test_deleted_lock_inode_test_only_simulation(lock_env):
    """Test-only Oct 23 simulation. Not a Dell real-path check."""
    lock_path = lock_env["workroom"]
    lock_path.write_text("held", encoding="utf-8")
    import fcntl

    holder = open(lock_path, "a")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        lock_path.unlink()
        assert not lock_path.exists()
        naive = subprocess.run(
            ["flock", "-n", str(lock_path), "true"],
            capture_output=True,
            text=True,
        )
        naive_created = lock_path.exists()
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
        finally:
            server.shutdown()
    finally:
        holder.close()

    assert naive.returncode == 0
    assert naive_created
    assert health_pass.returncode == 0, health_pass.stderr
    assert health_fail.returncode == 1
    assert not lock_path.exists()

    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(
        "\n".join(
            [
                "# Workroom lock — deleted-inode simulation (TEST ONLY)",
                "",
                "This file is a **pytest simulation**, not a real-path check on",
                "EmpireDell. A Dell real-path check comes later, after a backup",
                "and Rafael's OK.",
                "",
                "Simulates Oct 23 2026: tmp cleanup unlinked the lock name",
                "while the holder kept flock on the old inode.",
                "",
                f"- naive `flock -n PATH true`: exit `{naive.returncode}` (created new file: `{naive_created}`)",
                f"- new guard + health up: exit `{health_pass.returncode}` (stderr: {health_pass.stderr.strip()!r})",
                f"- new guard + health down: exit `{health_fail.returncode}` (stderr: {health_fail.stderr.strip()!r})",
                "",
                "Naive flock creates a new unlocked file and can steal Workroom's",
                "exclusive lock. The family guard never flocks Workroom's file.",
                "Health on loopback is enough when the name is gone.",
                "",
                json.dumps(
                    {
                        "test_only": True,
                        "not_dell_real_path": True,
                        "naive_flock_exit": naive.returncode,
                        "naive_created_file": naive_created,
                        "guard_health_up": health_pass.returncode,
                        "guard_health_down": health_fail.returncode,
                    },
                    indent=2,
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    text = PROOF.read_text(encoding="utf-8")
    assert "TEST ONLY" in text
    assert "not a real-path check" in text
    assert "naive `flock -n PATH true`: exit `0`" in text
    assert "new guard + health up: exit `0`" in text
    assert "new guard + health down: exit `1`" in text
