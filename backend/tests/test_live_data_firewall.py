"""Self-tests for the 2026-10-04 live-data firewall (tests/_live_data_guard.py
+ tests/conftest.py). Every probe targets a NON-EXISTENT path and uses
flags without O_CREAT, so even a broken firewall could not create or modify
anything under the live roots. Probe paths are lower-case on purpose:
conftest rewrites UPPER_CASE module constants that hold live paths."""
import os
import socket
import sqlite3
import subprocess
import sys
import types
from pathlib import Path

import pytest

import _live_data_guard as ldg


def _loaded_conftest():
    """The conftest module pytest already loaded (never re-import it)."""
    me = Path(__file__).resolve().with_name("conftest.py")
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f and hasattr(m, "_TEST_TMP_ROOT") and Path(f).resolve() == me:
            return m
    raise RuntimeError("tests/conftest.py not loaded")


cf = _loaded_conftest()

HOME = Path(os.path.expanduser("~"))
_probe_hard = HOME / "empire-data" / "brain" / "__firewall_probe_does_not_exist__.db"
_probe_soft = Path(ldg.REPO_ROOT) / "backend" / "data" / "__firewall_probe_does_not_exist__.json"


def test_data_env_vars_point_at_temp_root():
    root = str(cf._TEST_TMP_ROOT)
    for name in ("EMPIRE_DATA_DIR", "EMPIRE_BRAIN_DIR", "EMPIRE_TASK_DB", "EMPIRE_DB_PATH",
                 "EMPIRE_PHOTOS_DIR", "MAX_MEMORY_PATH", "OPENCLAW_DB_PATH"):
        value = os.environ.get(name, "")
        assert value, name
        assert ldg.classify(value) is None, f"{name} still live"
    assert os.environ["EMPIRE_DATA_DIR"].startswith(root)
    assert os.environ["EMPIRE_BRAIN_DIR"].startswith(root)


def test_journal_and_other_path_vars_forced_to_temp():
    root = str(cf._TEST_TMP_ROOT)
    for name in ("EMPIRE_MAX_JOURNAL_DB", "EMPIRE_MAX_JOURNAL_ARCHIVE", "EMPIRE_DB",
                 "COST_TRACKER_DB", "MAX_IMPROVE_SPEC_DIR", "VOICE_DOC_SESSIONS_PATH"):
        assert os.environ.get(name, "").startswith(("/tmp", root)), name
        assert ldg.classify(os.environ[name]) is None, name
    from app.services.max import session_journal as sj
    from app.services.data_paths import data_root
    assert str(sj.journal_db_path()).startswith(root)
    assert str(sj.archive_root()).startswith(root)
    assert str(data_root()).startswith(root)


def test_live_journal_watched_and_unchanged_so_far():
    assert any(p.endswith("max_session_journal.db") for p in cf._LIVE_WATCH_BEFORE)
    assert ldg.changed_files({"a": (1, 2, 3)}, {"a": (1, 2, 4)}) == ["a"]


def test_socket_to_own_tailscale_or_lan_address_refused():
    others = sorted(ip for ip in ldg.OWN_IPS if ip not in ldg.LOCAL_HOSTS and ":" not in ip)
    if not others:
        pytest.skip("no non-loopback IPv4 address on this host")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with ldg.expect_refusal() as r, pytest.raises(ConnectionRefusedError, match="LIVE_SERVICE_BLOCKED"):
            s.connect((others[0], 8443))
        assert r.caught
    finally:
        s.close()


@pytest.mark.parametrize("host", ["studio.empirebox.store", "apostapp.empirebox.store",
                                  "empiredell.example-tailnet.ts.net"])
def test_dns_for_live_public_hosts_refused(host):
    with ldg.expect_refusal() as r, pytest.raises(socket.gaierror, match="LIVE_SERVICE_BLOCKED"):
        socket.getaddrinfo(host, 443)
    assert r.caught


def test_classify_live_roots():
    assert ldg.classify(HOME / "empire-data" / "empire.db") == "hard"
    assert ldg.classify("~/empire-data/brain/unified_messages.db") == "hard"
    assert ldg.classify("/data/amp/x.db") == "hard"
    assert ldg.classify("/data/maxine/x.db") == "hard"
    assert ldg.classify(f"file:{HOME}/empire-data/empire.db?mode=ro") == "hard"
    assert ldg.classify(_probe_soft) == "soft"
    assert ldg.classify(HOME / "empire-repo" / "backend" / "data" / "tool_audit.db") == "soft"
    assert ldg.classify(cf._TEST_TMP_ROOT / "data" / "empire.db") is None
    assert ldg.classify("/tmp/whatever.db") is None


def test_assert_isolated_fails_fast_on_live_env(monkeypatch):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(HOME / "empire-data"))
    with pytest.raises(RuntimeError, match="refusing to run"):
        ldg.assert_isolated()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(cf._TEST_TMP_ROOT / "data"))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(HOME / "empire-data" / "empire.db"))
    with pytest.raises(RuntimeError, match="EMPIRE_TASK_DB"):
        ldg.assert_isolated()


def test_open_for_write_in_hard_root_refused():
    with ldg.expect_refusal() as r, pytest.raises(PermissionError, match="LIVE_DATA_VIOLATION"):
        os.open(_probe_hard, os.O_WRONLY)
    assert r.caught and not _probe_hard.exists()


def test_read_in_hard_root_refused():
    with ldg.expect_refusal() as r, pytest.raises(PermissionError):
        open(_probe_hard, "rb")
    assert r.caught


def test_write_in_soft_root_refused_read_allowed():
    with ldg.expect_refusal() as r, pytest.raises(PermissionError):
        os.open(_probe_soft, os.O_WRONLY)
    assert r.caught and not _probe_soft.exists()
    # reading a soft root (frozen snapshot, fixtures) is allowed
    with pytest.raises(FileNotFoundError):
        open(_probe_soft, "rb")


def test_mkdir_in_hard_root_refused():
    target = HOME / "empire-data" / "__firewall_probe_dir__"
    with ldg.expect_refusal() as r, pytest.raises(PermissionError):
        os.mkdir(target)
    assert r.caught and not target.exists()


def test_sqlite_connect_to_live_db_is_rewritten_to_temp():
    conn = sqlite3.connect(str(_probe_hard))
    try:
        path = conn.execute("PRAGMA database_list").fetchone()[2]
    finally:
        conn.close()
    assert path.startswith(str(cf._TEST_TMP_ROOT))
    assert not _probe_hard.exists()


def test_sqlite_connect_bypassing_wrapper_refused():
    uri = f"file:{_probe_hard}?mode=ro"
    with ldg.expect_refusal() as r, pytest.raises(PermissionError):
        cf._real_sqlite3_connect(uri, uri=True)
    assert r.caught


def test_socket_to_live_backend_port_refused():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with ldg.expect_refusal() as r, pytest.raises(ConnectionRefusedError, match="LIVE_SERVICE_BLOCKED"):
            s.connect(("127.0.0.1", 8000))
        assert r.caught
    finally:
        s.close()


def test_module_constants_and_defaults_redirected():
    mod = types.ModuleType("fake_live_mod")
    mod.LIVE_DIR = str(HOME / "empire-data" / "brain")
    mod.LIVE_FILE = Path(HOME / "empire-repo" / "backend" / "data" / "__probe__.json")
    mod.SAFE = "/tmp/fine"

    def writer(path=mod.LIVE_DIR):
        return path

    writer.__module__ = "fake_live_mod"
    mod.writer = writer
    changed = cf._redirect_live_module_constants([mod])
    assert ldg.classify(mod.LIVE_DIR) is None and mod.LIVE_DIR.startswith(str(cf._TEST_TMP_ROOT))
    assert isinstance(mod.LIVE_FILE, Path) and ldg.classify(mod.LIVE_FILE) is None
    assert mod.SAFE == "/tmp/fine"
    assert ldg.classify(writer()) is None
    assert "fake_live_mod.LIVE_DIR" in changed


def test_python_subprocess_inherits_firewall(tmp_path):
    log = tmp_path / "sub.log"
    env = dict(os.environ, EMPIRE_TEST_GUARD_LOG=str(log))
    code = (
        "import os, sqlite3, sys\n"
        "assert not os.environ['EMPIRE_DATA_DIR'].endswith('/empire-data')\n"
        f"p = {str(_probe_hard)!r}\n"
        "try:\n"
        "    sqlite3.connect('file:' + p + '?mode=ro', uri=True)\n"
        "except PermissionError:\n"
        "    print('REFUSED')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=60)
    assert "REFUSED" in out.stdout, out.stderr
    assert "LIVE_DATA_VIOLATION" in log.read_text()
