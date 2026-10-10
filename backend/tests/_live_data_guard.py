"""Live-data firewall for the backend test suite (2026-10-04).

Root cause it closes: shells that have the backend env loaded (agent
shells, ``set -a; . empire-backend.env``) export EMPIRE_DATA_DIR /
EMPIRE_TASK_DB pointing at ~/empire-data. conftest used
``os.environ.setdefault`` so those live values won, and modules that
default to ~/empire-data (unified_messages, memories, chat files...)
wrote test traffic into Rafael's real data.

Two layers, installed by tests/conftest.py at load time, before any
app module is imported:

1. ``redirect_env(tmp_root)``: force every data-path env var (and any
   env var whose value points into live data) at a per-run temp tree.
2. ``install()``: a ``sys.addaudithook`` firewall for the whole test
   process, and for Python subprocesses through a generated
   ``sitecustomize``. It refuses:
     * HARD roots (~/empire-data, /data/amp, /data/maxine): any open,
       sqlite connect, mkdir, remove, rename, rmtree, chmod, utime.
     * SOFT roots (live files the backend writes inside checkouts:
       <repo>/backend/data, ~/empire-repo/backend/data,
       <repo>/max/memory.md): writes, deletes, renames, new dirs and
       any sqlite connect. Plain reads are allowed.
     * TCP connects to the live services (127.0.0.1/localhost ports
       8000, 8011, 8012, 3005, 3011, 3012, 7878).
   Each refusal raises PermissionError at the call site and is
   recorded, so even code that swallows exceptions still fails the
   test (conftest checks the record after every test and at session
   end).

There is deliberately no opt-out marker for this layer.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import pytest

HOME = Path(os.path.expanduser("~"))
REPO_ROOT = Path(__file__).resolve().parents[2]

HARD_ROOTS_RAW = [HOME / "empire-data", Path("/data/amp"), Path("/data/maxine")]
SOFT_ROOTS_RAW = [
    REPO_ROOT / "backend" / "data",
    HOME / "empire-repo" / "backend" / "data",
    REPO_ROOT / "max" / "memory.md",
]
LIVE_PORTS = {8000, 8011, 8012, 3005, 3011, 3012, 7878}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0", "127.0.1.1"}
# Reaching the live services through this host's LAN / Tailscale address
# (e.g. https://empiredell.<tailnet>.ts.net:8443 -> 100.x) is blocked too.
OWN_HOST_PORTS = {80, 443, 8443}
# Public / tailnet names that route to the live services (Cloudflare tunnel,
# Tailscale serve). DNS lookups for them are refused under test.
LIVE_HOST_SUFFIXES = ("empirebox.store", "empirebox.com", ".ts.net")
LIVE_HOST_NAMES = {"empiredell", "empiredell.local"}


def _is_live_host(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    h = str(host or "").strip().rstrip(".").lower()
    return bool(h) and (h in LIVE_HOST_NAMES or any(h == s.lstrip(".") or h.endswith(s if s.startswith(".") else "." + s) for s in LIVE_HOST_SUFFIXES))


def _own_ips() -> set:
    ips = set(LOCAL_HOSTS)
    cached = os.environ.get("EMPIRE_TEST_GUARD_OWN_IPS")
    if cached:  # handed down to subprocesses by the parent test run
        return ips | set(cached.split(","))
    try:
        import subprocess as _sp
        out = _sp.run(["ip", "-o", "addr", "show"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                ips.add(parts[3].split("/")[0])
    except Exception:
        pass
    return ips


OWN_IPS: set = set()

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
_EVENTS = frozenset({
    "open", "sqlite3.connect", "sqlite3.connect/handle", "os.mkdir", "os.remove", "os.rmdir",
    "os.rename", "shutil.rmtree", "os.truncate", "os.chmod", "os.utime", "os.symlink",
    "os.link", "shutil.copyfile", "shutil.copytree", "shutil.move", "socket.connect",
    "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex",
})

violations: list[str] = []
_state = threading.local()
_installed = False
_log_path: str | None = None


def _forms(paths):
    out = []
    for p in paths:
        s = os.path.normpath(str(p))
        out.append(s)
        try:
            r = os.path.realpath(s)
            if r != s:
                out.append(r)
        except OSError:
            pass
    return tuple(sorted(set(out)))


HARD_ROOTS = _forms(HARD_ROOTS_RAW)
SOFT_ROOTS = _forms(SOFT_ROOTS_RAW)


def _under(path: str, roots) -> bool:
    for r in roots:
        if path == r or path.startswith(r + os.sep):
            return True
    return False


def classify(path) -> str | None:
    """'hard', 'soft' or None for a filesystem path (str/bytes/PathLike)."""
    if path is None or isinstance(path, int):
        return None
    try:
        p = os.fsdecode(os.fspath(path))
    except TypeError:
        return None
    if not p or p == ":memory:" or p.startswith("file::memory:"):
        return None
    if p.startswith("file:"):
        p = p[5:].split("?", 1)[0]
    p = os.path.normpath(os.path.abspath(os.path.expanduser(p)))
    cands = [p]
    try:
        r = os.path.realpath(p)
        if r != p:
            cands.append(r)
    except OSError:
        pass
    if any(_under(c, HARD_ROOTS) for c in cands):
        return "hard"
    if any(_under(c, SOFT_ROOTS) for c in cands):
        return "soft"
    return None


def _record(msg: str) -> None:
    expected = getattr(_state, "expected", None)
    if expected is not None:  # inside expect_refusal(): firewall self-test
        expected.append(msg)
        return
    violations.append(msg)
    if _log_path:
        try:
            _state.busy = True
            with open(_log_path, "a") as fh:  # temp dir, never protected
                fh.write(f"[pid {os.getpid()}] {msg}\n")
        except Exception:
            pass
        finally:
            _state.busy = False


def _refuse(event: str, target) -> None:
    msg = f"LIVE_DATA_VIOLATION: {event} -> {target!r}"
    _record(msg)
    raise PermissionError(msg + " (tests must never touch live Empire data; see tests/_live_data_guard.py)")


blocked_connects: list[str] = []


def _block_connect(addr, dns: bool = False) -> None:
    """Live services (backend/portal/family editions/OpenClaw) are never
    contacted. Code under test sees an ordinary 'connection refused' (as if
    the service were down); the attempt is logged but is not by itself a
    test failure, because health probes are common and harmless once blocked."""
    import errno
    msg = f"LIVE_SERVICE_BLOCKED: {'dns' if dns else 'socket.connect'} -> {addr!r}"
    expected = getattr(_state, "expected", None)
    if expected is not None:
        expected.append(msg)
    else:
        blocked_connects.append(msg)
        if _log_path:
            try:
                _state.busy = True
                with open(_log_path, "a") as fh:
                    fh.write(f"[pid {os.getpid()}] {msg}\n")
            except Exception:
                pass
            finally:
                _state.busy = False
    if dns:
        import socket as _socket
        raise _socket.gaierror(_socket.EAI_NONAME, msg + " (live-data firewall: tests never contact live services)")
    raise ConnectionRefusedError(errno.ECONNREFUSED, msg + " (live-data firewall: tests never contact live services)")


def _hook(event: str, args) -> None:
    if event not in _EVENTS or getattr(_state, "busy", False):
        return
    _state.busy = True
    try:
        if event in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex"):
            host = args[0] if args else None
            if _is_live_host(host):
                _state.busy = False
                _block_connect(host, dns=True)
            return
        if event == "socket.connect":
            addr = args[1] if len(args) > 1 else None
            host = str(addr[0]).split("%")[0] if isinstance(addr, tuple) and addr else ""
            if host.startswith("::ffff:"):
                host = host[7:]
            if isinstance(addr, tuple) and len(addr) >= 2 and host in (OWN_IPS or LOCAL_HOSTS) and (
                    addr[1] in LIVE_PORTS or addr[1] in OWN_HOST_PORTS):
                _state.busy = False
                _block_connect(addr)
            return
        if event == "open":
            path, mode, flags = (list(args) + [None, None, None])[:3]
            kind = classify(path)
            if kind is None:
                return
            writes = bool(mode and any(ch in str(mode) for ch in "wax+")) or bool(
                isinstance(flags, int) and flags & _WRITE_FLAGS)
            if kind == "hard" or writes:
                _state.busy = False
                _refuse(f"open({mode or flags})", path)
            return
        if event.startswith("sqlite3.connect"):
            if event == "sqlite3.connect/handle":
                return
            if classify(args[0] if args else None):
                _state.busy = False
                _refuse(event, args[0])
            return
        if event == "os.mkdir":
            path = args[0] if args else None
            kind = classify(path)
            # hard root: always refused; soft root: refused only when it
            # would create a new directory (exist_ok on an existing one is a no-op)
            if kind == "hard" or (kind == "soft" and not os.path.isdir(os.fsdecode(os.fspath(path)))):
                _state.busy = False
                _refuse(event, path)
            return
        targets = list(args[:2]) if event in ("os.rename", "os.link", "os.symlink", "shutil.copyfile", "shutil.copytree", "shutil.move") else [args[0] if args else None]
        if event in ("shutil.copyfile", "shutil.copytree"):
            # reading a soft root as the source is fine; destination counts
            src, dst = targets[0], targets[1] if len(targets) > 1 else None
            if classify(src) == "hard":
                _state.busy = False
                _refuse(event, src)
            if classify(dst):
                _state.busy = False
                _refuse(event, dst)
            return
        for t in targets:
            if classify(t):
                _state.busy = False
                _refuse(event, t)
    finally:
        _state.busy = False


def install(log_path: str | None = None) -> None:
    global _installed, _log_path
    _log_path = log_path or os.environ.get("EMPIRE_TEST_GUARD_LOG")
    if not OWN_IPS:
        OWN_IPS.update(_own_ips())  # before the hook is active
        os.environ["EMPIRE_TEST_GUARD_OWN_IPS"] = ",".join(sorted(OWN_IPS))
    if _installed:
        return
    sys.addaudithook(_hook)
    _installed = True


# ── env redirection ──────────────────────────────────────────────────────
def redirect_env(tmp_root: Path) -> dict[str, str]:
    """Point every data env var at tmp_root. Returns {name: 'old -> new'} (no values of
    unrelated vars are touched or printed)."""
    tmp_root = Path(tmp_root)
    data = tmp_root / "data"
    (data / "brain").mkdir(parents=True, exist_ok=True)
    (tmp_root / "max").mkdir(parents=True, exist_ok=True)
    mapping = {
        os.path.normpath(str(HOME / "empire-data")): str(data),
        "/data/amp": str(tmp_root / "family-amp"),
        "/data/maxine": str(tmp_root / "family-maxine"),
    }
    changed: dict[str, str] = {}
    # 1) any env var whose value points into a protected tree
    for name, value in list(os.environ.items()):
        if not value or "/" not in value or name in ("PATH", "PWD", "OLDPWD", "HOME"):
            continue
        new = value
        for live, tmp in mapping.items():
            new = new.replace(live, tmp)
        if new != value or (classify(value) and os.pathsep not in value):
            if new == value:  # soft-root value with no tmp equivalent
                new = str(tmp_root / "redirected" / name)
            os.environ[name] = new
            changed[name] = "redirected"
    # 2) the canonical data vars, forced (never setdefault)
    forced = {
        "EMPIRE_DATA_DIR": str(data),
        "EMPIRE_BRAIN_DIR": str(data / "brain"),
        "MAX_MEMORY_PATH": str(tmp_root / "max" / "memory.md"),
        "OPENCLAW_DB_PATH": str(data / "openclaw_tasks.db"),
        "EMPIRE_TEST_GUARD_LOG": str(tmp_root / "live_data_violations.log"),
        # Max session journal: always a temp DB under test (never the live
        # ~/empire-data/brain/max_session_journal.db), images to temp too.
        "EMPIRE_MAX_JOURNAL_DB": str(data / "brain" / "max_session_journal.db"),
        "EMPIRE_MAX_JOURNAL_ARCHIVE": str(data / "max-sessions-archive" / "attachments"),
        # Other path vars whose defaults point at live data or the repo data dir.
        "COST_TRACKER_DB": str(data / "token_usage.db"),
        "MAX_IMPROVE_SPEC_DIR": str(data / "improvements"),
        "VOICE_DOC_SESSIONS_PATH": str(data / "voice_document_sessions.json"),
        "CHAT_BACKUP_DIR": str(tmp_root / "chat_backups"),
    }
    for name, value in forced.items():
        if os.environ.get(name) != value:
            changed.setdefault(name, "forced")
        os.environ[name] = value
    e2e = os.environ.get("EMPIRE_E2E_BASE_URL", "")
    if e2e and (any(f":{p}" in e2e for p in LIVE_PORTS) or "empirebox" in e2e):
        os.environ.pop("EMPIRE_E2E_BASE_URL", None)
        changed["EMPIRE_E2E_BASE_URL"] = "unset (points at a live service)"
    return changed


def write_sitecustomize(tmp_root: Path) -> str:
    """Make Python subprocesses spawned by tests load the same firewall."""
    site_dir = Path(tmp_root) / "guard_site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "sitecustomize.py").write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(Path(__file__).resolve().parent)!r})\n"
        "try:\n"
        "    import _live_data_guard as _g\n"
        "    _g.install()\n"
        "except Exception as _e:  # never block interpreter start\n"
        "    sys.stderr.write(f'live-data guard not installed: {_e}\\n')\n"
    )
    prev = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = str(site_dir) + (os.pathsep + prev if prev else "")
    return str(site_dir)


def assert_isolated() -> None:
    """Fail fast if any data path still resolves to live data."""
    bad = []
    for name in ("EMPIRE_DATA_DIR", "EMPIRE_BRAIN_DIR", "EMPIRE_TASK_DB", "EMPIRE_DB_PATH",
                 "EMPIRE_PHOTOS_DIR", "OPENCLAW_DB_PATH", "MAX_MEMORY_PATH"):
        v = os.environ.get(name)
        if v and classify(v):
            bad.append(f"{name} -> live path")
    for name, v in os.environ.items():
        if name.startswith(("EMPIRE_", "MAX_", "OPENCLAW_")) and v and "/" in v and os.pathsep not in v and classify(v):
            bad.append(f"{name} -> live path")
    if bad:
        raise RuntimeError("Test isolation failed, refusing to run: " + ", ".join(sorted(set(bad))))


class expect_refusal:
    """Context manager for the firewall's own tests: refusals inside the
    block still raise PermissionError but are collected in ``.caught``
    instead of being counted as violations of the test run."""

    def __enter__(self):
        self._prev = getattr(_state, "expected", None)
        self.caught: list[str] = []
        _state.expected = self.caught
        return self

    def __exit__(self, *exc):
        _state.expected = self._prev
        return False


# ── live-file watch ──────────────────────────────────────────────────────
# Stat-only fingerprints (size, mtime_ns, inode) of live files that must not
# change while the suite runs. Taken at conftest load and compared at session
# end; any change fails the run. Stat never opens the file.
WATCHED_LIVE_FILES = [
    HOME / "empire-data" / "brain" / "max_session_journal.db",
    HOME / "empire-data" / "brain" / "max_session_journal.db-wal",
]


def fingerprint(paths=None) -> dict:
    fp = {}
    for p in (paths or WATCHED_LIVE_FILES):
        try:
            st = os.stat(p)
            fp[str(p)] = (st.st_size, st.st_mtime_ns, st.st_ino)
        except FileNotFoundError:
            fp[str(p)] = None
        except OSError as e:
            fp[str(p)] = f"err:{e.errno}"
    return fp


def changed_files(before: dict, after: dict) -> list:
    return [p for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)]


# --- WhatsApp chat-log / filing isolation (used by test_whatsapp_*.py) ---

LIVE_GRAPH_MARKERS = (
    "graph.facebook.com",
    "lookaside.fbsbx.com",
    "graph.instagram.com",
)

PROD_PATH_MARKERS = (
    "empire-data/empire.db",
    "empire-data\\empire.db",
    "/empire-data/empire.db",
    "empire-repo/backend/data",
    "empire-repo\\backend\\data",
    "/data/amp",
    "/data/maxine",
)


def _looks_like_prod(value: str) -> bool:
    lowered = (value or "").replace("\\", "/")
    return any(marker.replace("\\", "/") in lowered for marker in PROD_PATH_MARKERS)


def assert_isolated_env() -> None:
    """Fail loudly if this process is pointed at live data or live Graph."""
    for name in ("EMPIRE_TASK_DB", "EMPIRE_DB_PATH", "EMPIRE_DATA_DIR", "WHATSAPP_JOBS_ROOT"):
        value = os.getenv(name) or ""
        if _looks_like_prod(value):
            raise RuntimeError(f"{name} points at live data: {value}")
    data_dir = os.getenv("EMPIRE_DATA_DIR") or ""
    if data_dir:
        path = Path(data_dir)
        live_backend = (Path.home() / "empire-repo" / "backend" / "data").resolve()
        try:
            if path.exists() and path.resolve() == live_backend:
                raise RuntimeError("EMPIRE_DATA_DIR resolved to the live backend/data folder")
        except OSError:
            pass


def assert_no_live_graph(url: str) -> None:
    lowered = (url or "").lower()
    if any(host in lowered for host in LIVE_GRAPH_MARKERS):
        raise RuntimeError(f"live Meta Graph call refused in tests: {url}")


def _write_test_whatsapp_labels(root: Path) -> Path:
    """Test-only labels. Real founder numbers stay out of committed business.json."""
    wa_dir = root / "whatsapp"
    wa_dir.mkdir(parents=True, exist_ok=True)
    path = wa_dir / "labels.json"
    path.write_text(
        json.dumps({
            "phones": [
                {"name": "Rafael", "phone": "+12022996975"},
                {"name": "Nelma", "phone": "+17036239203"},
            ]
        }),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def isolated_whatsapp_edition(tmp_path, monkeypatch):
    """Clean per-edition data dir + founder PIN. No live WhatsApp credentials."""
    root = tmp_path / "edition-data"
    root.mkdir(parents=True, exist_ok=True)
    jobs = tmp_path / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    for slug in ("maggie-frolich", "willard-hotel", "mclean-residence"):
        (jobs / slug).mkdir(exist_ok=True)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("WHATSAPP_JOBS_ROOT", str(jobs))
    monkeypatch.setenv("FOUNDER_PIN", "test-founder-pin")
    monkeypatch.setenv("WHATSAPP_PHOTO_BATCH_SECONDS", "0")
    monkeypatch.setenv("WHATSAPP_JOB_HINT_SECONDS", "600")
    labels = _write_test_whatsapp_labels(root)
    monkeypatch.setenv("WHATSAPP_LABELS", str(labels))
    for name in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    assert_isolated_env()
    return root
