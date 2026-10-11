"""Process-wide data isolation guard for family editions (Max-e, Maxine).

Installed from ``app/__init__.py`` before any other app module loads.
No-op unless EMPIRE_EDITION is a family edition (amp, maxine).

The family backends run as the same Unix user as the owner's Workroom,
so file permissions cannot keep them out of the owner's data. A large
part of the shared codebase still hardcodes Workroom paths
(``~/empire-data/empire.db``, ``/data/images``, ``~/empire-repo/backend/data``,
``/data/empire-storage`` ...). This guard uses a CPython audit hook so
every in-process open / listdir / scandir / sqlite connect / copy / remove,
every subprocess launch and every outbound socket connect is checked:

* Paths under /home/rg, /data, /mnt, /media are denied unless they are
  inside this edition's own data dir (EMPIRE_DATA_DIR), this edition's own
  checkout, or a small set of runtime caches. Denied reads look like
  "file not found", so modules show empty state instead of owner data.
* Loopback / private-network connects are denied except this edition's
  own backend/frontend ports, so code cannot query the Workroom API (8000),
  OpenClaw (7878), Hermes (3000), etc.
* Shell subprocesses, and subprocesses whose args name a denied path, are
  refused.

Set EMPIRE_FS_GUARD=log to log instead of enforce (diagnostics only).
"""
from __future__ import annotations

import ipaddress
import os
import sys
import threading

_FAMILY = {"amp", "maxine"}
_INSTALLED = False
_local = threading.local()

_DENY_ROOTS = ("/home/rg", "/data", "/mnt", "/media", "/root")
# Owner-authored content tracked inside the edition checkout (the Workroom
# Max memory snapshot, internal docs/reports, version symlinks). Treated as
# owner data even though it lives in this checkout.
_CHECKOUT_OWNER_SUBDIRS = ("max", "docs", "versions")
_SHELLS = {"sh", "bash", "dash", "zsh", "ksh", "fish", "csh", "tcsh"}
_TEXT_MARKERS = (
    "/home/rg", "/data/", "~/", "~rg", "$HOME", "${HOME}",
    "empire-repo", "empire-data", "empire-storage", "empire-box-memory",
    ".hermes", ".openclaw", ".claude",
)


def _edition() -> str:
    return os.getenv("EMPIRE_EDITION", "").strip().lower()


class _Policy:
    def __init__(self) -> None:
        ed = _edition()
        data_dir = os.getenv("EMPIRE_DATA_DIR", "").strip() or f"/data/{ed}"
        self.data_dir = os.path.realpath(data_dir)
        here = os.path.realpath(__file__)
        # backend/app/security/family_fs_guard.py -> checkout root
        self.checkout = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(here))))
        home = "/home/rg"
        self.allow = tuple(os.path.realpath(p) for p in (
            self.data_dir,
            self.checkout,
            sys.prefix,
            os.path.join(home, ".cache", "huggingface"),
            os.path.join(home, ".cache", "torch"),
            os.path.join(home, ".cache", "whisper"),
            os.path.join(home, ".cache", "pip"),
            os.path.join(home, ".cache", "ms-playwright"),
            os.path.join(home, ".cache", "fontconfig"),
            os.path.join(home, ".cache", "matplotlib"),
            os.path.join(home, ".local", "lib"),
            os.path.join(home, ".local", "bin"),
        ))
        self.allow_exact = set()
        self.owner_in_checkout = tuple(
            os.path.join(base, sub)
            for base in {self.checkout, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))}
            for sub in _CHECKOUT_OWNER_SUBDIRS
        )
        self.allow_lexical = tuple(dict.fromkeys(
            [os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
             os.path.abspath(data_dir), os.path.abspath(sys.prefix)] + list(self.allow)))
        self.mode = os.getenv("EMPIRE_FS_GUARD", "enforce").strip().lower()
        ports = set()
        for var in ("EMPIRE_BACKEND_PORT", "EMPIRE_FRONTEND_EXPECTED_PORT"):
            try:
                ports.add(int(os.getenv(var, "") or 0))
            except ValueError:
                pass
        prof = {"amp": (8011, 3011), "maxine": (8012, 3012)}.get(ed, ())
        ports.update(prof)
        ports.add(11434)  # local model runtime, holds no owner data
        ports.discard(0)
        self.local_ports = ports
        self._cache: dict = {}

    @staticmethod
    def _under(path: str, root: str) -> bool:
        return path == root or path.startswith(root.rstrip("/") + "/")

    def path_denied(self, raw) -> bool:
        if raw is None or isinstance(raw, int):
            return False
        try:
            p = os.fsdecode(raw)
        except Exception:
            return False
        if not p:
            return False
        hit = self._cache.get(p)
        if hit is not None:
            return hit
        _local.raw = True
        try:
            real = os.path.realpath(os.path.expanduser(p))
        except Exception:
            real = os.path.abspath(p)
        finally:
            _local.raw = False
        denied = False
        if any(self._under(real, r) for r in _DENY_ROOTS):
            denied = not any(self._under(real, a) for a in self.allow)
            if not denied and any(self._under(real, o) for o in self.owner_in_checkout):
                denied = True
        if len(self._cache) < 20000:
            self._cache[p] = denied
        return denied

    def text_denied(self, text: str) -> bool:
        if not text:
            return False
        own = (self.data_dir, self.checkout)
        scrubbed = text
        for o in own:
            scrubbed = scrubbed.replace(o, "")
        return any(m in scrubbed for m in _TEXT_MARKERS)

    def addr_denied(self, address) -> bool:
        if not isinstance(address, tuple) or len(address) < 2:
            return False  # unix sockets etc.
        host, port = address[0], address[1]
        try:
            ip = ipaddress.ip_address(str(host).split("%")[0])
        except ValueError:
            return False
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        internal = ip.is_loopback or ip.is_private or ip.is_link_local or (
            ip.version == 4 and ip in ipaddress.ip_network("100.64.0.0/10")
        )
        if not internal:
            return False
        return not (ip.is_loopback and int(port) in self.local_ports)


_policy: _Policy | None = None


# ---------------------------------------------------------------------------
# Redirect layer: legacy owner paths -> this edition's shadow directory.
#
# Code that still names a Workroom path (``~/empire-data/empire.db``,
# ``/data/images/...``) is transparently pointed at
# ``$EMPIRE_DATA_DIR/shadow/<original absolute path>``. Tools keep working
# and start empty; nothing reads or writes the owner's files. The audit hook
# above stays as the backstop for anything this layer does not cover.
# ---------------------------------------------------------------------------

_orig: dict = {}


def _shadow_root() -> str:
    assert _policy is not None
    return os.path.join(_policy.data_dir, "shadow")


def _map(path):
    """Return the shadow path for a denied path, else the path unchanged."""
    pol = _policy
    if pol is None or getattr(_local, "raw", False):
        return path
    if isinstance(path, int) or path is None:
        return path
    try:
        is_bytes = isinstance(path, bytes)
        s = os.fsdecode(path) if is_bytes else (os.fspath(path) if isinstance(path, os.PathLike) else path)
        if not isinstance(s, str) or not s:
            return path
    except Exception:
        return path
    if s.startswith("~"):
        s = "/home/rg" + s[1:] if (s == "~" or s.startswith("~/")) else s
    a = s if s.startswith("/") else os.path.join(os.getcwd(), s)
    a = os.path.normpath(a)
    if not any(pol._under(a, r) for r in _DENY_ROOTS):
        return path
    if any(pol._under(a, al) for al in pol.allow_lexical) and not any(
        pol._under(a, o) for o in pol.owner_in_checkout
    ):
        return path
    new = os.path.join(_shadow_root(), a.lstrip("/"))
    return os.fsencode(new) if is_bytes else new


def _wrap1(mod, name):
    fn = getattr(mod, name, None)
    if fn is None:
        return
    _orig[(mod.__name__, name)] = fn

    def wrapper(path, *args, **kwargs):
        return fn(_map(path), *args, **kwargs)

    wrapper.__name__ = getattr(fn, "__name__", name)
    wrapper.__doc__ = getattr(fn, "__doc__", None)
    wrapper.__wrapped__ = fn
    setattr(mod, name, wrapper)


def _wrap2(mod, name):
    fn = getattr(mod, name, None)
    if fn is None:
        return
    _orig[(mod.__name__, name)] = fn

    def wrapper(src, dst, *args, **kwargs):
        return fn(_map(src), _map(dst), *args, **kwargs)

    wrapper.__name__ = getattr(fn, "__name__", name)
    wrapper.__wrapped__ = fn
    setattr(mod, name, wrapper)


def _install_redirects() -> None:
    import builtins
    import io
    import sqlite3

    for name in ("open", "stat", "lstat", "access", "listdir", "scandir", "mkdir", "rmdir",
                 "remove", "unlink", "chmod", "utime", "truncate", "chdir", "readlink",
                 "chown", "lchown", "pathconf", "getxattr", "listxattr"):
        _wrap1(os, name)
    for name in ("rename", "replace", "link", "symlink"):
        _wrap2(os, name)

    real_open = io.open
    real_makedirs = os.makedirs

    def _ensure_parent(original, mapped):
        if mapped is original or mapped == original:
            return
        try:
            real_makedirs(os.path.dirname(os.fsdecode(mapped)), exist_ok=True)
        except Exception:
            pass

    def guarded_open(file, *args, **kwargs):
        mapped = _map(file)
        mode = args[0] if args else kwargs.get("mode", "r")
        if isinstance(mode, str) and any(ch in mode for ch in "wax+"):
            _ensure_parent(file, mapped)
        return real_open(mapped, *args, **kwargs)

    real_os_open = _orig.get(("os", "open"))

    def guarded_os_open(path, flags, *args, **kwargs):
        mapped = _map(path)
        if flags & os.O_CREAT:
            _ensure_parent(path, mapped)
        return real_os_open(mapped, flags, *args, **kwargs)

    real_mkdir = _orig.get(("os", "mkdir"))

    def guarded_mkdir(path, *args, **kwargs):
        mapped = _map(path)
        _ensure_parent(path, mapped)
        return real_mkdir(mapped, *args, **kwargs)

    if real_mkdir is not None:
        guarded_mkdir.__wrapped__ = real_mkdir
        os.mkdir = guarded_mkdir

    if real_os_open is not None:
        guarded_os_open.__wrapped__ = real_os_open
        os.open = guarded_os_open

    guarded_open.__wrapped__ = real_open
    guarded_open.__doc__ = real_open.__doc__
    builtins.open = guarded_open
    io.open = guarded_open

    real_connect = sqlite3.connect

    def guarded_connect(database, *args, **kwargs):
        db = database
        if isinstance(db, (str, bytes, os.PathLike)):
            s = os.fsdecode(db)
            if s.startswith("file:"):
                body, _, query = s[5:].partition("?")
                mapped = _map(body)
                if mapped != body:
                    _ensure_parent(body, mapped)
                    db = "file:" + mapped + (("?" + query) if query else "")
            elif s != ":memory:" and s:
                db = _map(s)
                _ensure_parent(s, db)
        return real_connect(db, *args, **kwargs)

    guarded_connect.__wrapped__ = real_connect
    sqlite3.connect = guarded_connect
    try:
        import sqlite3.dbapi2 as _dbapi2
        _dbapi2.connect = guarded_connect
    except Exception:
        pass
    try:
        os.makedirs(_shadow_root(), exist_ok=True)
    except Exception:
        pass


def _block(exc: BaseException, event: str, detail) -> None:
    if _policy is not None and _policy.mode == "log":
        try:
            sys.stderr.write(f"[family-fs-guard] WOULD BLOCK {event}: {detail!r}\n")
        except Exception:
            pass
        return
    try:
        sys.stderr.write(f"[family-fs-guard] blocked {event}: {str(detail)[:200]}\n")
    except Exception:
        pass
    raise exc


def _hook(event: str, args) -> None:
    pol = _policy
    if pol is None:
        return
    if getattr(_local, "busy", False):
        return
    _local.busy = True
    try:
        if event == "open":
            path = args[0] if args else None
            if pol.path_denied(path):
                _block(FileNotFoundError(2, "No such file or directory", os.fsdecode(path)), event, path)
        elif event in ("os.listdir", "os.scandir", "os.rmdir", "os.remove", "os.truncate",
                       "os.chmod", "os.chown", "os.utime", "os.chdir", "os.listxattr",
                       "os.getxattr", "os.setxattr", "os.removexattr", "shutil.rmtree",
                       "shutil.chown", "shutil.unpack_archive", "glob.glob", "glob.glob/2",
                       "os.chflags", "os.lchflags", "os.mkfifo", "os.mknod"):
            path = args[0] if args else None
            if pol.path_denied(path):
                _block(FileNotFoundError(2, "No such file or directory", os.fsdecode(path)), event, path)
        elif event == "os.mkdir":
            path = args[0] if args else None
            if pol.path_denied(path):
                _block(FileExistsError(17, "File exists", os.fsdecode(path)), event, path)
        elif event in ("os.rename", "os.link", "os.symlink", "shutil.copyfile", "shutil.copymode",
                       "shutil.copystat", "shutil.copytree", "shutil.move", "shutil.make_archive"):
            for path in list(args)[:2]:
                if isinstance(path, (str, bytes, os.PathLike)) and pol.path_denied(path):
                    _block(PermissionError(13, "Permission denied", os.fsdecode(path)), event, path)
        elif event == "sqlite3.connect":
            db = args[0] if args else None
            if isinstance(db, (str, bytes, os.PathLike)):
                s = os.fsdecode(db)
                target = s[5:].split("?", 1)[0] if s.startswith("file:") else s
                if target and target != ":memory:" and pol.path_denied(target):
                    import sqlite3
                    _block(sqlite3.OperationalError("unable to open database file"), event, s)
        elif event in ("subprocess.Popen", "os.posix_spawn", "os.exec", "os.spawn"):
            exe, argv = (args[0], args[1]) if len(args) >= 2 else (args[0] if args else None, None)
            parts = []
            if isinstance(argv, (list, tuple)):
                parts = [os.fsdecode(a) if isinstance(a, (str, bytes)) else str(a) for a in argv]
            elif isinstance(argv, (str, bytes)):
                parts = [os.fsdecode(argv)]
            exe_s = os.fsdecode(exe) if isinstance(exe, (str, bytes, os.PathLike)) else (parts[0].split()[0] if parts else "")
            base = os.path.basename(exe_s or "")
            first = os.path.basename(parts[0].split()[0]) if parts and parts[0].split() else ""
            cwd = args[2] if event == "subprocess.Popen" and len(args) >= 3 else None
            if base in _SHELLS or first in _SHELLS:
                _block(PermissionError(13, "Shell commands are disabled in this edition"), event, parts[:3])
            elif pol.text_denied(" ".join(parts)) or (exe_s and pol.path_denied(exe_s) and "/" in exe_s):
                _block(PermissionError(13, "Permission denied (owner data)"), event, parts[:3])
            elif cwd is not None and pol.path_denied(cwd):
                _block(PermissionError(13, "Permission denied (owner data)"), event, cwd)
        elif event == "os.system":
            _block(PermissionError(13, "Shell commands are disabled in this edition"), event, args[:1])
        elif event == "socket.connect":
            addr = args[1] if len(args) >= 2 else None
            if pol.addr_denied(addr):
                _block(ConnectionRefusedError(111, "Connection refused (edition isolation)"), event, addr)
    finally:
        _local.busy = False


def install() -> bool:
    """Install once per process. Returns True when active."""
    global _INSTALLED, _policy
    if _INSTALLED:
        return True
    if _edition() not in _FAMILY:
        return False
    if os.getenv("EMPIRE_FS_GUARD", "").strip().lower() in {"off", "0", "disabled"}:
        # Refuse to run unguarded: an explicit off switch is not honored in
        # family editions. Fall back to enforce.
        os.environ["EMPIRE_FS_GUARD"] = "enforce"
    _policy = _Policy()
    if _policy.mode != "log":
        _install_redirects()
    sys.addaudithook(_hook)
    _INSTALLED = True
    return True


def status() -> dict:
    pol = _policy
    return {
        "active": _INSTALLED,
        "mode": pol.mode if pol else None,
        "data_dir": pol.data_dir if pol else None,
        "local_ports": sorted(pol.local_ports) if pol else [],
    }
