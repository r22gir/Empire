"""Family lock guard: no Workroom wait, no flock steal, no primary jobs.

The Oct 23 2026 bug: tmp cleanup unlinked /tmp/empire_primary_worker.lock
while Workroom still held flock on the old inode. The family ExecStartPre
ran ``flock -n /tmp/empire_primary_worker.lock true``, which created a
new unlocked file and could briefly take Workroom's exclusive lock.

Family units must start when Workroom is down. They still refuse both
Workroom lock paths (realpath) and never start primary-only jobs.

These tests use a private lock under tmp_path. They never open
8000 / 8011 / 8012 / 3000 / 3005.

Reports this file writes are **test-only**. A Dell real-path check comes
later, after a backup and Rafael's OK.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "deploy" / "workroom_primary_ready.sh"
PROOF = ROOT / "reports" / "2026-10-28_workroom_lock_deleted_inode.md"
FAMILY_DOWN_PROOF = ROOT / "reports" / "2026-10-28_family_starts_workroom_down.md"
MAIN_PY = ROOT / "backend" / "app" / "main.py"
AMP_UNIT = ROOT / "deploy" / "empire-amp.service"
MAXINE_UNIT = ROOT / "deploy" / "empire-maxine.service"
WORKROOM_UNIT = ROOT / "systemd" / "empire-backend.service"


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
    amp = AMP_UNIT.read_text(encoding="utf-8")
    maxine = MAXINE_UNIT.read_text(encoding="utf-8")
    workroom = WORKROOM_UNIT.read_text(encoding="utf-8")
    script = GUARD.read_text(encoding="utf-8")
    assert "workroom_primary_ready.sh" in amp
    assert "workroom_primary_ready.sh" in maxine
    assert "EMPIRE_WORKER_LOCK=/data/amp/run/empire_primary_worker.lock" in amp
    assert "EMPIRE_WORKER_LOCK=/data/maxine/run/empire_primary_worker.lock" in maxine
    assert "EMPIRE_WORKER_LOCK=/home/rg/empire-data/run/empire_primary_worker.lock" not in workroom
    assert "--port 8000" in workroom
    assert "--port 8000" not in amp
    assert "--port 8000" not in maxine
    for unit in (amp, maxine):
        assert "After=empire-backend" not in unit
        assert "Requires=empire-backend" not in unit
        assert "Wants=empire-backend" not in unit
        assert "--port 3000" not in unit
        assert "--port 3005" not in unit
    live = [ln for ln in script.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert not any("flock" in ln for ln in live)
    assert not any("/proc/locks" in ln for ln in live)
    assert not any("127.0.0.1:8000" in ln for ln in live)
    assert not any("health_ok" in ln or "lock_is_held" in ln for ln in live)
    assert "realpath" in script
    assert "start does not wait on Workroom" in script


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


def test_guard_passes_when_workroom_lock_and_health_are_down(lock_env):
    """Family ExecStartPre must succeed while Workroom is down."""
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
    assert "does not wait on Workroom" in result.stderr
    assert not lock_env["workroom"].exists()
    assert not lock_env["legacy"].exists()
    assert not lock_env["family"].exists()

    maxine = _run_guard(
        {
            "EMPIRE_EDITION": "maxine",
            "EMPIRE_WORKER_LOCK": str(lock_env["family"]),
            "EMPIRE_WORKROOM_LOCK": str(lock_env["workroom"]),
            "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
            "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
        }
    )
    assert maxine.returncode == 0, maxine.stderr


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

        workroom_down = _run_guard(
            {
                "EMPIRE_EDITION": "amp",
                "EMPIRE_WORKER_LOCK": str(lock_env["family"]),
                "EMPIRE_WORKROOM_LOCK": str(lock_path),
                "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
                "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
            }
        )
    finally:
        holder.close()

    assert naive.returncode == 0
    assert naive_created
    assert workroom_down.returncode == 0, workroom_down.stderr
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
                f"- family guard + Workroom down: exit `{workroom_down.returncode}` (stderr: {workroom_down.stderr.strip()!r})",
                "",
                "Naive flock creates a new unlocked file and can steal Workroom's",
                "exclusive lock. The family guard never flocks Workroom's file",
                "and does not wait on Workroom health.",
                "",
                json.dumps(
                    {
                        "test_only": True,
                        "not_dell_real_path": True,
                        "naive_flock_exit": naive.returncode,
                        "naive_created_file": naive_created,
                        "guard_workroom_down": workroom_down.returncode,
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
    assert "family guard + Workroom down: exit `0`" in text


def test_family_holding_instance_lock_does_not_start_primary_jobs(lock_env, monkeypatch):
    from app.worker_lock import (
        PRIMARY_JOBS,
        acquire_primary_worker_lock,
        primary_jobs_blocked_reason,
        reset_worker_lock_for_tests,
        should_start_primary_jobs,
    )

    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(lock_env["family"]))
    assert acquire_primary_worker_lock() is True
    try:
        assert should_start_primary_jobs(True) is False
        assert primary_jobs_blocked_reason(True) == "family_edition"
        assert "telegram_bot" in PRIMARY_JOBS
        assert "gmail_email_polling" in PRIMARY_JOBS
        assert "openclaw_worker" in PRIMARY_JOBS
        assert "growth_jobs" in PRIMARY_JOBS
        assert not lock_env["workroom"].exists()
    finally:
        reset_worker_lock_for_tests()

    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    assert should_start_primary_jobs(True) is False
    assert primary_jobs_blocked_reason(False) == "family_edition"


def test_workroom_primary_still_starts_jobs_when_lock_held(lock_env, monkeypatch):
    from app.worker_lock import primary_jobs_blocked_reason, should_start_primary_jobs

    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    assert should_start_primary_jobs(True) is True
    assert primary_jobs_blocked_reason(True) is None
    assert should_start_primary_jobs(False) is False
    assert primary_jobs_blocked_reason(False) == "not_primary_worker"


def test_main_startup_gates_every_primary_job_after_family_skip():
    from app.worker_lock import PRIMARY_JOB_START_MARKERS

    main = MAIN_PY.read_text(encoding="utf-8")
    start = main.index("async def start_background_services")
    family_skip = main.index("Family edition — skipping Workroom primary jobs", start)
    secondary = main.index("Secondary worker — skipping singleton background services", start)
    primary_banner = main.index("Primary worker — starting singleton background services", start)
    assert family_skip < primary_banner
    assert secondary < primary_banner
    for marker in PRIMARY_JOB_START_MARKERS:
        idx = main.index(marker, start)
        assert idx > primary_banner, marker
    assert "gmail" in main[family_skip:family_skip + 200].lower()
    assert "openclaw" in main[family_skip:family_skip + 200].lower()
    assert "growth" in main[family_skip:family_skip + 200].lower()


def test_audit_primary_and_lock_callers_cannot_promote_family():
    """Every lock / primary-job decision stays family-safe."""
    from app.worker_lock import acquire_primary_worker_lock

    repo = ROOT / "backend" / "app"
    callers = []
    for path in repo.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "acquire_primary_worker_lock" not in text and "should_start_primary_jobs" not in text:
            continue
        callers.append(path.relative_to(ROOT).as_posix())
    assert "backend/app/worker_lock.py" in callers
    assert "backend/app/main.py" in callers
    assert acquire_primary_worker_lock.__module__ == "app.worker_lock"

    main = MAIN_PY.read_text(encoding="utf-8")
    assert "should_start_primary_jobs" in main
    assert "is_family_edition()" in main
    edition = (ROOT / "backend" / "app" / "edition.py").read_text(encoding="utf-8")
    assert "is_workroom_lock_path" in edition
    assert 'root / "run" / "empire_primary_worker.lock"' in edition


def test_family_starts_while_workroom_down_runs_no_primary_jobs(lock_env, monkeypatch):
    """Family edition starts alone: own lock, no Workroom file, no primary jobs."""
    from app.edition import apply_amp_process_paths
    from app.worker_lock import (
        acquire_primary_worker_lock,
        is_workroom_lock_path,
        reset_worker_lock_for_tests,
        should_start_primary_jobs,
    )

    data = lock_env["tmp"] / "amp"
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data))
    monkeypatch.setenv("EMPIRE_WORKER_LOCK", "/tmp//empire_primary_worker.lock")
    apply_amp_process_paths()
    family_lock = data / "run" / "empire_primary_worker.lock"
    assert os.environ["EMPIRE_WORKER_LOCK"] == str(family_lock)
    assert not is_workroom_lock_path(os.environ["EMPIRE_WORKER_LOCK"])

    guard = _run_guard(
        {
            "EMPIRE_EDITION": "amp",
            "EMPIRE_WORKER_LOCK": os.environ["EMPIRE_WORKER_LOCK"],
            "EMPIRE_WORKROOM_LOCK": str(lock_env["workroom"]),
            "EMPIRE_WORKROOM_LOCK_LEGACY": str(lock_env["legacy"]),
            "EMPIRE_WORKROOM_HEALTH_URL": "http://127.0.0.1:9/health",
        }
    )
    assert guard.returncode == 0, guard.stderr
    assert acquire_primary_worker_lock() is True
    try:
        assert should_start_primary_jobs(True) is False
        assert family_lock.is_file()
        assert not lock_env["workroom"].exists()
        assert not lock_env["legacy"].exists()
    finally:
        reset_worker_lock_for_tests()

    FAMILY_DOWN_PROOF.parent.mkdir(parents=True, exist_ok=True)
    FAMILY_DOWN_PROOF.write_text(
        "\n".join(
            [
                "# Family start while Workroom is down (TEST ONLY)",
                "",
                "This file is a **pytest simulation**, not a real-path check on",
                "EmpireDell. A Dell real-path check comes later, after a backup",
                "and Rafael's OK. Nothing here was deployed or restarted.",
                "",
                "Workroom lock missing, health on 127.0.0.1:9 (down).",
                "Family edition remaps EMPIRE_WORKER_LOCK onto /data/<instance>/run,",
                "the ExecStartPre guard exits 0, the instance lock is taken, and",
                "primary-only jobs stay off.",
                "",
                f"- guard exit: `{guard.returncode}`",
                f"- family lock created: `{family_lock.is_file()}`",
                f"- Workroom lock created: `{lock_env['workroom'].exists()}`",
                f"- should_start_primary_jobs(True): `{should_start_primary_jobs(True)}`",
                "",
                json.dumps(
                    {
                        "test_only": True,
                        "not_dell_real_path": True,
                        "workroom_down": True,
                        "guard_exit": guard.returncode,
                        "family_lock": True,
                        "workroom_lock_created": False,
                        "primary_jobs": False,
                    },
                    indent=2,
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    text = FAMILY_DOWN_PROOF.read_text(encoding="utf-8")
    assert "TEST ONLY" in text
    assert "not a real-path check" in text
    assert "should_start_primary_jobs(True): `False`" in text
    assert "primary_jobs" in text
