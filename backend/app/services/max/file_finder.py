"""Rafael's file finder: read-only search across his files on the Dell.

2026-10-05. Rafael: "Max needs access to all files ... why is he not finding
all I ask?" Before this, Max only saw the Final Docs hub (quote/invoice PDF
folders + ~/jobs) through open_final_doc, which returned ONE doc by default,
and file_read only reads the code checkout. Nothing searched Downloads,
Desktop, Documents, Pictures, empire-data or the backup drive.

This module:
- indexes file NAMES (no content) under Rafael's home (following top-level
  symlinks such as ~/Downloads -> /data/empire/Downloads) and mounted drives
  under /media/<user>/* and /mnt/*;
- never indexes secrets/credentials, databases, browser profiles, hidden
  files/dirs, or family-edition data (AMP / Maxine);
- ranks ALL matches (fuzzy on file name, folder, client alias, quote number)
  and returns several, newest/finals first;
- is read-only: scandir/stat only. Reading bytes happens only in
  read_file_bytes() for an explicit share, after re-checking the rules.
"""
from __future__ import annotations

import difflib
import hashlib
import hmac
import logging
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

logger = logging.getLogger("max.file_finder")

HOME = Path(os.path.expanduser("~")).resolve()

# ── Exclusions ──────────────────────────────────────────────────────
PRUNE_DIR_NAMES = {
    "node_modules", "venv", "env", "__pycache__", "site-packages", "dist-packages",
    "snap", "$recycle.bin", "system volume information", "appdata", "application data",
    "google-chrome", "chromium", "bravesoftware", "firefox", "mozilla", "profiles", "user data",
    "keyrings", "password-store", "credentials", "secrets", "secret", "tokens",
    "lost+found", "proc", "sys",
}
# Family editions (AMP / Maxine) — never searchable from Rafael's Max.
FAMILY_SEGMENTS = {"amp", "maxine", "empire-amp", "empire-maxine"}
FAMILY_PREFIXES = ("empire-amp", "empire-maxine", "amp-portal", "amp.", "amp_", "maxine")
SECRET_NAME_RE = re.compile(
    r"(^\.env)|(\.env(\.|$))|token|credential|secret|passw|passwd|api[-_]?key|private[-_]?key|"
    r"^id_(rsa|dsa|ecdsa|ed25519)|\.(pem|key|p12|pfx|kdbx?|keystore|jks|gpg|pgp|ovpn|asc)$|"
    r"^\.?netrc$|^\.?pgpass$|client_secret|service[-_]account|oauth|\.sqlite3?(-wal|-shm)?$|"
    r"\.db(-wal|-shm|-journal)?$|\.db\.bak|\.db\?",
    re.IGNORECASE,
)


def _excluded_realpaths() -> tuple[str, ...]:
    h = str(HOME)
    return tuple(p.rstrip("/") for p in (
        "/data/amp", "/data/maxine", f"{h}/empire-amp", f"{h}/empire-maxine",
        f"{h}/.ssh", f"{h}/.gnupg", f"{h}/.hermes", f"{h}/.config", f"{h}/.local",
        f"{h}/.mozilla", f"{h}/.password-store", f"{h}/snap", "/data/empire/hermes",
    ))


_SECRET_DIR_RE = re.compile(r"token|credential|secret|passw|keyring|oauth|gnupg|ssh", re.IGNORECASE)


def _segment_blocked(seg: str) -> bool:
    s = seg.lower()
    if not s or s.startswith("."):
        return True
    if _SECRET_DIR_RE.search(s):
        return True
    if s in PRUNE_DIR_NAMES or s in FAMILY_SEGMENTS:
        return True
    if s.startswith(FAMILY_PREFIXES) or any(f in s for f in _FAMILY_SUBSTR):
        return True
    return False


_FAMILY_SUBSTR = ("maxine", "empire-amp", "amp-portal", "empire_amp")


def _name_excluded(name: str) -> bool:
    nl = name.lower()
    return (not nl or nl.startswith(".") or bool(SECRET_NAME_RE.search(name))
            or nl.startswith(FAMILY_PREFIXES) or any(f in nl for f in _FAMILY_SUBSTR))


def is_excluded(path: str | Path) -> bool:
    """True when the path (or anything it resolves to) must never be searched or shared."""
    p = str(path)
    try:
        real = os.path.realpath(p)
    except Exception:
        return True
    for cand in (p, real):
        for root in _excluded_realpaths():
            if cand == root or cand.startswith(root + "/"):
                return True
        parts = [x for x in cand.split("/") if x]
        for seg in parts[:-1]:
            if _segment_blocked(seg):
                return True
        name = parts[-1] if parts else ""
        if _name_excluded(name):
            return True
    return False


def _edition_allowed() -> bool:
    ed = (os.getenv("EMPIRE_EDITION") or "main").strip().lower()
    return ed in ("main", "workroom", "empire", "founder", "")


def search_roots() -> list[Path]:
    """Rafael's home plus mounted drives (/media/<user>/*, /mnt/*)."""
    roots: list[Path] = []
    override = os.getenv("MAX_FILE_FINDER_ROOTS")
    if override:
        return [Path(x).expanduser() for x in override.split(os.pathsep) if x.strip()]
    roots.append(HOME)
    for base in (Path("/media") / HOME.name, Path("/mnt")):
        try:
            for d in sorted(base.iterdir()):
                if d.is_dir() and os.path.ismount(d):
                    roots.append(d)
        except Exception:
            pass
    return roots


# ── Index ───────────────────────────────────────────────────────────
@dataclass
class Entry:
    path: str
    name: str
    size: int
    mtime: float
    root: str
    tokens: tuple[str, ...]
    dir_tokens: tuple[str, ...]


_TOKEN_SPLIT = re.compile(r"[^a-z0-9áéíóúñ]+")


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split((text or "").lower()) if t]


def _walk(root: Path, *, max_entries: int, follow_top_symlinks: bool = True) -> list[Entry]:
    out: list[Entry] = []
    seen_real: set[str] = set()
    stack: list[tuple[str, int]] = [(str(root), 0)]
    root_s = str(root)
    while stack and len(out) < max_entries:
        cur, depth = stack.pop()
        try:
            real = os.path.realpath(cur)
        except Exception:
            continue
        if real in seen_real:
            continue
        seen_real.add(real)
        try:
            it = os.scandir(cur)
        except Exception:
            continue
        with it:
            for de in it:
                name = de.name
                if name.startswith("."):
                    continue
                full = os.path.join(cur, name)
                try:
                    is_link = de.is_symlink()
                    if de.is_dir(follow_symlinks=False) or (is_link and depth == 0 and follow_top_symlinks
                                                            and os.path.isdir(full)):
                        if _segment_blocked(name) or depth > 14:
                            continue
                        if is_excluded(full + "/x"):
                            continue
                        stack.append((full, depth + 1))
                        continue
                    if is_link or not de.is_file(follow_symlinks=False):
                        continue
                    if _name_excluded(name):
                        continue
                    st = de.stat(follow_symlinks=False)
                except Exception:
                    continue
                rel_dir = os.path.relpath(cur, root_s)
                dir_parts = [] if rel_dir == "." else rel_dir.split(os.sep)
                out.append(Entry(
                    path=full, name=name, size=int(st.st_size), mtime=float(st.st_mtime), root=root_s,
                    tokens=tuple(_tokens(os.path.splitext(name)[0])) + tuple(_tokens(os.path.splitext(name)[1])),
                    dir_tokens=tuple(t for part in dir_parts[-4:] for t in _tokens(part)),
                ))
                if len(out) >= max_entries:
                    break
    return out


class FileIndex:
    """In-memory name index. Home rebuilds quickly (seconds); mounted drives in the background."""

    def __init__(self, ttl_home: float = 600.0, ttl_drives: float = 6 * 3600.0, max_entries: int = 1_500_000):
        self.ttl_home = ttl_home
        self.ttl_drives = ttl_drives
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._by_root: dict[str, list[Entry]] = {}
        self._built: dict[str, float] = {}
        self._building: set[str] = set()

    def _build_root(self, root: Path) -> None:
        key = str(root)
        try:
            t0 = time.time()
            entries = _walk(root, max_entries=self.max_entries)
            with self._lock:
                self._by_root[key] = entries
                self._built[key] = time.time()
            logger.info("file_finder: indexed %s files under %s in %.1fs", len(entries), key, time.time() - t0)
        finally:
            with self._lock:
                self._building.discard(key)

    def entries(self, *, wait_home: bool = True) -> tuple[list[Entry], list[str]]:
        """All indexed entries + roots still being indexed."""
        pending: list[str] = []
        roots = search_roots()
        for i, root in enumerate(roots):
            key = str(root)
            is_home = i == 0 and not os.getenv("MAX_FILE_FINDER_ROOTS")
            ttl = self.ttl_home if (is_home or os.getenv("MAX_FILE_FINDER_ROOTS")) else self.ttl_drives
            with self._lock:
                fresh = key in self._built and time.time() - self._built[key] < ttl
                have = key in self._by_root
                building = key in self._building
            if fresh:
                continue
            synchronous = (is_home or os.getenv("MAX_FILE_FINDER_ROOTS")) and wait_home and not have
            if synchronous:
                with self._lock:
                    self._building.add(key)
                self._build_root(root)
            elif not building:
                with self._lock:
                    self._building.add(key)
                threading.Thread(target=self._build_root, args=(root,), daemon=True,
                                 name=f"file-index-{root.name}").start()
                if not have:
                    pending.append(key)
            elif not have:
                pending.append(key)
        with self._lock:
            allowed = {str(r) for r in roots}
            out = [e for k, v in self._by_root.items() if k in allowed for e in v]
        return out, pending

    def clear(self) -> None:
        with self._lock:
            self._by_root.clear()
            self._built.clear()


INDEX = FileIndex()


# ── Query parsing / ranking ─────────────────────────────────────────
FILLER = {
    "show", "me", "the", "open", "latest", "last", "newest", "recent", "recently", "updated", "update",
    "please", "pull", "up", "for", "of", "a", "an", "doc", "docs", "document", "documents", "file", "files",
    "can", "you", "i", "want", "see", "view", "get", "my", "s", "here", "there", "send", "give", "attach",
    "share", "it", "them", "those", "these", "that", "this", "and", "or", "to", "in", "on", "from", "with",
    "all", "any", "some", "find", "look", "where", "is", "are", "was", "do", "does", "did", "have", "has",
    "what", "whats", "client", "job", "project", "her", "his", "their", "our", "copy", "copies",
    "folder", "drive", "computer", "dell", "downloads", "download", "desktop", "pictures", "picture",
    "aqui", "por", "favor", "mandame", "enviame", "muestrame", "abre", "el", "la", "los", "las", "de",
    "del", "documento", "documentos", "archivo", "archivos", "un", "una", "y", "o", "en", "con", "su", "mi",
    "busca", "buscar", "encuentra",
}
LOCATION_WORDS = {"downloads": "downloads", "download": "downloads", "desktop": "desktop", "documents": "documents",
                  "pictures": "pictures", "backup": "backup1", "usb": "backup1"}
MODIFIERS = {"final", "finals", "signed", "draft"}
TYPE_WORDS = {
    "estimate": ("est", "estimate", "quote", "proposal"), "estimates": ("est", "estimate", "quote", "proposal"),
    "quote": ("est", "estimate", "quote", "proposal"), "quotes": ("est", "estimate", "quote", "proposal"),
    "invoice": ("inv", "invoice"), "invoices": ("inv", "invoice"), "presentation": ("presentation", "pres"),
    "drawing": ("drawing", "elevation", "shop"), "drawings": ("drawing", "elevation", "shop"),
    "photo": ("jpg", "jpeg", "png", "heic", "photo"), "photos": ("jpg", "jpeg", "png", "heic", "photo"),
    "pdf": ("pdf",), "pdfs": ("pdf",), "spreadsheet": ("xlsx", "xls", "csv"), "contract": ("contract", "agreement"),
}
DOC_EXT = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".pptx", ".txt", ".md", ".rtf", ".odt", ".ods"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".tif", ".tiff"}
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".pyc", ".map", ".json", ".css", ".html", ".sh", ".lock", ".log",
            ".yml", ".yaml", ".sse", ".jsonl"}
LOW_VALUE_DIRS = {"backups", "backup", "archive", "archives", "empire-repo-backups", "repo-archives", "home-backups",
                  "cache", "caches", "tmp", "test", "tests", "fixtures", "mock", "drawtest"}
QN_RE = re.compile(r"\b(EST|INV)[-\s]?(\d{4})[-\s]?(\d{3})([A-Z]?)\b", re.IGNORECASE)


from functools import lru_cache


@lru_cache(maxsize=500_000)
def _close(a: str, b: str, cutoff: float = 0.8) -> bool:
    if a == b:
        return True
    if len(a) < 4 or len(b) < 4 or abs(len(a) - len(b)) > 3:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= cutoff


def _fuzzy_in(term: str, tokens: tuple[str, ...]) -> bool:
    return term in tokens or any(_close(term, x) for x in tokens)


USER_DIRS = {"desktop", "documents", "downloads", "pictures", "jobs", "videos", "music"}
REPO_DIRS = {"empire-repo-main", "empire-repo", "opencode-empire-main", "hermes-agent", "tmp-archive",
             "empire-backups", "archive", "agent-tools", "terminals"}


def _client_terms(query: str) -> tuple[Optional[dict], list[str]]:
    """Client alias resolution (client_aliases.json via doc_lookup, read-only import)."""
    try:
        from app.services.max.doc_lookup import load_aliases, resolve_client
        aliases = load_aliases()
        client = resolve_client(query, hub_clients=[], aliases=aliases)
    except Exception:
        return None, []
    if not client:
        return None, []
    terms: set[str] = set(_tokens(client["name"]))
    alias_words: set[str] = set()
    for row in aliases:
        if row.get("name") == client["name"]:
            for al in row.get("aliases") or []:
                alias_words |= set(_tokens(al))
            addr = str(row.get("address") or "")
            alias_words |= {w for w in _tokens(addr) if len(w) >= 4 and not w.isdigit()}
    client = dict(client)
    client["alias_words"] = sorted(alias_words)
    return client, sorted(t for t in terms if len(t) >= 3)


def parse_query(query: str) -> dict[str, Any]:
    raw = query or ""
    qn = QN_RE.search(raw)
    quote_number = f"{qn.group(1).upper()}-{qn.group(2)}-{qn.group(3)}{qn.group(4).upper()}" if qn else None
    words = _tokens(QN_RE.sub(" ", raw))
    client, client_words = _client_terms(raw)
    alias_words = set((client or {}).get("alias_words") or [])
    location = next((LOCATION_WORDS[w] for w in words if w in LOCATION_WORDS), None)
    modifiers = [w.rstrip("s") for w in words if w in MODIFIERS]
    types = [w for w in words if w in TYPE_WORDS]
    terms = []
    for w in words:
        if w in FILLER or w in MODIFIERS or w in TYPE_WORDS or len(w) < 2:
            continue
        if client and (any(_close(w, c) for c in client_words) or any(_close(w, a) or _close(w.rstrip("s"), a) for a in alias_words)):
            continue
        terms.append(w)
    return {"query": raw, "quote_number": quote_number, "client": client, "client_words": client_words,
            "location": location, "modifiers": modifiers, "types": types, "terms": terms}


def _score(e: Entry, q: dict[str, Any]) -> tuple[float, list[str]]:
    why: list[str] = []
    s = 0.0
    name_l = e.name.lower()
    ext = os.path.splitext(name_l)[1]
    all_tokens = e.tokens + e.dir_tokens
    path_l = e.path.lower()
    matched_any = False
    # quote number
    if q["quote_number"]:
        qn = q["quote_number"].lower()
        digits = qn.split("-")[-1]
        if qn in name_l or qn.replace("-", "") in name_l.replace("-", ""):
            s += 12; why.append("quote number"); matched_any = True
        elif qn in path_l:
            s += 6; why.append("quote number in folder"); matched_any = True
        elif digits in e.tokens and ("est" in e.tokens or "inv" in e.tokens):
            s += 5; why.append("quote digits"); matched_any = True
        else:
            return 0.0, []
    # client
    if q["client"]:
        cw = q["client_words"] + list(q["client"].get("alias_words") or [])
        hit_name = sum(1 for c in q["client_words"] if _fuzzy_in(c, e.tokens))
        hit_dir = sum(1 for c in cw if _fuzzy_in(c, e.dir_tokens))
        hit_alias = sum(1 for a in q["client"].get("alias_words") or [] if a in e.tokens)
        if hit_name or hit_dir or hit_alias:
            s += 8 + 2 * hit_name + 1.5 * min(hit_dir, 2) + 2 * hit_alias
            why.append(f"client {q['client']['name']}")
            matched_any = True
        elif not q["quote_number"]:
            return 0.0, []
    # free terms: every term must match somewhere (fuzzy); terms in the name count more
    for t in q["terms"]:
        if t in e.tokens:
            s += 4; matched_any = True
        elif t in e.dir_tokens:
            s += 2.5; matched_any = True
        elif len(t) >= 4 and _fuzzy_in(t, e.tokens):
            s += 2.5; matched_any = True
        elif len(t) >= 4 and _fuzzy_in(t, e.dir_tokens):
            s += 1.5; matched_any = True
        elif len(t) >= 3 and t in name_l:
            s += 2; matched_any = True
        else:
            return 0.0, []
    if not matched_any and not (q["types"] and not q["terms"] and not q["client"] and not q["quote_number"]):
        if q["terms"] or q["client"] or q["quote_number"]:
            return 0.0, []
    # type words
    for tw in q["types"]:
        keys = TYPE_WORDS[tw]
        if any(k in all_tokens for k in keys) or ext.lstrip(".") in keys:
            s += 3; why.append(tw)
        else:
            s -= 2
    # modifiers
    if "final" in q["modifiers"]:
        if "final" in e.tokens:
            s += 5; why.append("FINAL")
        else:
            s -= 1
    # location hint
    if q["location"]:
        if q["location"] in [t.lower() for t in Path(e.path).parts]:
            s += 3
        elif q["location"] in path_l:
            s += 2
    # file kind
    if ext in DOC_EXT:
        s += 2
    elif ext in IMG_EXT:
        s += 0.5
    elif ext in CODE_EXT:
        s -= 3
    if any(seg.lower() in LOW_VALUE_DIRS or seg.lower().startswith("drawtest") for seg in Path(e.path).parts):
        s -= 2.5
    if not e.path.startswith(str(HOME)):
        s -= 1.0  # backup drive copies rank under live files
    else:
        top = e.path[len(str(HOME)) + 1:].split("/", 1)[0].lower()
        if top in USER_DIRS:
            s += 2.0
        elif top in REPO_DIRS:
            s -= 2.0
    # recency (newer slightly higher): up to +1.5 for the last 30 days
    age_days = max(0.0, (time.time() - e.mtime) / 86400.0)
    s += max(0.0, 1.5 - age_days / 20.0)
    return s, why


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n} B"


def _display_path(p: str) -> str:
    h = str(HOME)
    return "~" + p[len(h):] if p.startswith(h + "/") else p


# ── File ids / share tokens ─────────────────────────────────────────
_SECRET = (os.getenv("MAX_FILE_SHARE_SECRET") or "").encode() or secrets.token_bytes(32)


def file_id(path: str) -> str:
    return hmac.new(_SECRET, os.path.realpath(path).encode(), hashlib.sha256).hexdigest()[:20]


_ID_CACHE: dict[str, str] = {}
_ID_LOCK = threading.Lock()


def _remember(path: str) -> str:
    fid = file_id(path)
    with _ID_LOCK:
        _ID_CACHE[fid] = path
        if len(_ID_CACHE) > 20000:
            for k in list(_ID_CACHE)[:5000]:
                _ID_CACHE.pop(k, None)
    return fid


def resolve_file(ref: str) -> Optional[str]:
    """file_id from a search result, or an absolute/~ path. Re-checks every rule. None if not allowed."""
    ref = (ref or "").strip()
    if not ref or not _edition_allowed():
        return None
    with _ID_LOCK:
        path = _ID_CACHE.get(ref)
    if path is None:
        if "/" not in ref and not ref.startswith("~"):
            return None
        path = os.path.expanduser(ref)
    return path if is_shareable(path) else None


def is_shareable(path: str) -> bool:
    if not path or is_excluded(path):
        return False
    real = os.path.realpath(path)
    if not os.path.isfile(real):
        return False
    roots = [str(r) for r in search_roots()]
    candidates = {path, real}
    # follow home top-level symlinks (e.g. ~/Downloads -> /data/empire/Downloads)
    allowed_reals = set()
    for r in roots:
        allowed_reals.add(os.path.realpath(r))
        if os.path.realpath(r) == str(HOME):
            try:
                for d in os.scandir(str(HOME)):
                    if d.is_symlink() and not d.name.startswith(".") and os.path.isdir(d.path) \
                            and not is_excluded(d.path + "/x"):
                        allowed_reals.add(os.path.realpath(d.path))
            except Exception:
                pass
    return any(c == a or c.startswith(a.rstrip("/") + "/") for c in candidates for a in allowed_reals | set(roots))


def share_token(path: str, ttl_seconds: int = 24 * 3600) -> str:
    exp = int(time.time()) + int(ttl_seconds)
    real = os.path.realpath(path)
    payload = f"{exp}:{real}".encode()
    import base64
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    sig = hmac.new(_SECRET, payload, hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def verify_share_token(token: str) -> Optional[str]:
    import base64
    try:
        body, sig = (token or "").rsplit(".", 1)
        payload = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        good = hmac.new(_SECRET, payload, hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(good, sig):
            return None
        exp_s, real = payload.decode().split(":", 1)
        if int(exp_s) < time.time():
            return None
    except Exception:
        return None
    return real if is_shareable(real) else None


def read_file_bytes(path: str, max_bytes: int = 25 * 1024 * 1024) -> bytes:
    if not is_shareable(path):
        raise PermissionError("file is not shareable")
    if os.path.getsize(path) > max_bytes:
        raise ValueError(f"file is larger than {max_bytes // (1024 * 1024)} MB")
    with open(path, "rb") as fh:
        return fh.read()


# ── Public search ───────────────────────────────────────────────────
def find_files(query: str, *, limit: int = 15, index: Optional[FileIndex] = None) -> dict[str, Any]:
    """Ranked matches for a natural-language file request. Read-only."""
    if not _edition_allowed():
        return {"query": query, "found": False, "matches": [], "error": "file search is not enabled in this edition"}
    idx = index or INDEX
    q = parse_query(query)
    entries, pending = idx.entries()
    if not (q["terms"] or q["client"] or q["quote_number"] or q["types"]):
        return {"query": query, "found": False, "matches": [], "total": 0, "parsed": _parsed(q),
                "indexing": pending, "error": "Say what to look for: a file name, client, quote number or words in the name."}
    scored: list[tuple[float, Entry, list[str]]] = []
    screen: list[str] = []
    if q["quote_number"]:
        screen = [q["quote_number"].lower().split("-")[-1]]
    for e in entries:
        if screen and not any(sv in e.path.lower() for sv in screen):
            continue
        sc, why = _score(e, q)
        if sc > 0:
            scored.append((sc, e, why))
    scored.sort(key=lambda x: (x[0], x[1].mtime), reverse=True)
    # collapse identical copies (same name + size): keep the best-ranked one
    seen: dict[tuple[str, int], dict] = {}
    matches: list[dict] = []
    for sc, e, why in scored:
        key = (e.name.lower(), e.size)
        if key in seen:
            seen[key]["other_copies"] += 1
            if len(seen[key]["copy_paths"]) < 3:
                seen[key]["copy_paths"].append(_display_path(e.path))
            continue
        row = {
            "file_id": _remember(e.path), "name": e.name, "path": _display_path(e.path),
            "folder": _display_path(os.path.dirname(e.path)), "size": _human_size(e.size),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(e.mtime)),
            "score": round(sc, 1), "why": why, "other_copies": 0, "copy_paths": [],
            "is_final": "final" in e.tokens,
        }
        seen[key] = row
        matches.append(row)
    total = len(matches)
    out = {"query": query, "parsed": _parsed(q), "total": total, "found": total > 0,
           "matches": matches[:max(1, min(int(limit or 15), 50))], "indexing": pending,
           "indexed_files": len(entries)}
    if not total:
        out["closest"] = closest(query, entries, q)
    return out


def _parsed(q: dict) -> dict:
    return {"client": (q["client"] or {}).get("name"), "client_via": (q["client"] or {}).get("via"),
            "quote_number": q["quote_number"], "terms": q["terms"], "types": q["types"],
            "modifiers": q["modifiers"], "location": q["location"]}


def closest(query: str, entries: Iterable[Entry], q: Optional[dict] = None, limit: int = 5) -> list[dict]:
    """Nearest file names for an honest 'nothing matched' reply (token-level fuzzy)."""
    q = q or parse_query(query)
    words = [w for w in (q["terms"] + q["client_words"]) if len(w) >= 3] or \
            [w for w in _tokens(query) if w not in FILLER and len(w) >= 3]
    if not words:
        return []
    entries = list(entries)
    by_token: dict[str, list[Entry]] = {}
    for e in entries:
        for tok in set(e.tokens):
            if len(tok) >= 3:
                by_token.setdefault(tok, []).append(e)
    vocab = list(by_token)
    scored: dict[str, float] = {}
    for w in words:
        for tok in difflib.get_close_matches(w, vocab, n=8, cutoff=0.6):
            r = difflib.SequenceMatcher(None, w, tok).ratio()
            for e in by_token[tok]:
                scored[e.path] = scored.get(e.path, 0.0) + r / len(words)
    ranked = sorted(((r, p) for p, r in scored.items()), reverse=True)
    out, seen = [], set()
    for r, path in ranked:
        name = os.path.basename(path)
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({"file_id": _remember(path), "name": name, "path": _display_path(path),
                    "similarity": round(r, 2)})
        if len(out) >= limit:
            break
    return out

def warm_index_async() -> None:
    """Build the home index in the background (called when the tool pack loads)."""
    if not _edition_allowed() or os.getenv("PYTEST_CURRENT_TEST"):
        return
    threading.Thread(target=lambda: INDEX.entries(), daemon=True, name="file-index-warm").start()
