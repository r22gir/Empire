"""Family editions must never read or write owner (Workroom) data."""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

PROBE = r"""
import app, os, sqlite3, socket, subprocess
from app.security import family_fs_guard as g
assert g.status()["active"]
assert not os.path.exists("/data/images/presorted_inventory.json")
assert not os.path.exists(os.path.expanduser("~/empire-data/empire.db"))
c = sqlite3.connect(os.path.expanduser("~/empire-data/empire.db"))
assert c.execute("select count(*) from sqlite_master").fetchone()[0] == 0
for cmd in (["bash", "-c", "true"], ["cat", "/home/rg/.bashrc"]):
    try:
        subprocess.run(cmd); raise SystemExit("subprocess allowed: %r" % cmd)
    except PermissionError:
        pass
s = socket.socket()
try:
    s.connect(("127.0.0.1", 8000)); raise SystemExit("workroom api reachable")
except ConnectionRefusedError:
    pass
print("OK")
"""


def test_guard_isolates_family_edition(tmp_path):
    if not Path("/home/rg").exists():
        import pytest
        pytest.skip("Dell layout only")
    env = dict(os.environ, EMPIRE_EDITION="amp", EMPIRE_DATA_DIR=str(tmp_path))
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=BACKEND, env=env,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "OK" in out.stdout, out.stderr[-2000:]
    assert (tmp_path / "shadow").exists()


def test_guard_noop_on_workroom():
    env = {k: v for k, v in os.environ.items() if k != "EMPIRE_EDITION"}
    out = subprocess.run([sys.executable, "-c",
                          "import app; from app.security import family_fs_guard as g; print(g.status()['active'])"],
                         cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60)
    assert out.stdout.strip().endswith("False"), out.stderr[-2000:]
