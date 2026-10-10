"""Fuzzy Final Docs lookup for Max (client aliases, addresses, "last N docs").

2026-10-04: on WhatsApp Rafael asked "Show me dhalias last 2 updated docs here".
open_final_doc sent the whole sentence to the docs hub, whose resolver needs
every word to match, so "updated" sank it ("No saved document matched").
This module sits in front of the hub:

- client aliases and job addresses (app/config/client_aliases.json), e.g.
  "Dahlia" / "dhalia" / "9408 Old Courthouse" -> Nehal Elrefai
- fuzzy match on the hub's own client list (typos, possessives)
- filler words dropped ("updated", "recent", "here", "send", ...)
- "last 2" / "two" / "latest" -> that many most recently modified finals
- when nothing matches: the closest matches, so Max can say so plainly

Read-only. Talks to the docs hub on the portal (same as open_final_doc) and
never returns public links.
"""
from __future__ import annotations

import difflib
import json
import logging
import os
import re
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

HubGet = Callable[[str, dict], dict]

ALIASES_PATH = Path(__file__).resolve().parents[2] / "config" / "client_aliases.json"
_alias_write_lock = threading.Lock()
_ALIAS_PHONE_KEYS = {
    "phone", "phones", "mobile", "telephone", "whatsapp", "wa_id",
    "msisdn", "number", "numbers", "founder_phone",
}
logger = logging.getLogger("max.doc_lookup")

FILLER = {
    "show", "me", "the", "open", "final", "finals", "latest", "last", "newest", "recent", "recently",
    "updated", "update", "modified", "changed", "new", "please", "pull", "up", "for", "of", "a", "an",
    "doc", "docs", "document", "documents", "file", "files", "pdf", "pdfs", "can", "you", "i", "want",
    "see", "view", "get", "my", "s", "version", "versions", "current", "here", "there", "send", "give",
    "attach", "share", "it", "them", "those", "these", "that", "this", "and", "or", "to", "in", "on",
    "from", "with", "all", "any", "some", "one", "ones", "two", "three", "four", "five", "most",
    "client", "clients", "job", "jobs", "project", "her", "his", "their", "our", "we", "us", "what",
    "whats", "where", "is", "are", "was", "do", "does", "did", "have", "has", "find", "look",
    "aqui", "aquí", "por", "favor", "mandame", "mándame", "enviame", "envíame", "manda", "envia",
    "muestrame", "muéstrame", "abre", "el", "la", "los", "las", "de", "del", "ultimo", "último",
    "ultimos", "últimos", "documento", "documentos", "archivo", "archivos", "dos", "tres", "un", "una",
    "y", "o", "en", "con", "su", "sus", "mis", "mi",
}
TYPE_WORDS = [
    (re.compile(r"^(estimate|estimates|quote|quotes|estimado|cotizacion|cotización|presupuesto)$"), "estimate"),
    (re.compile(r"^(presentation|presentations|deck|presentacion|presentación)$"), "presentation"),
    (re.compile(r"^(invoice|invoices|bill|factura)$"), "invoice"),
    (re.compile(r"^(drawing|drawings|shop|elevation|dibujo|dibujos|plano|planos)$"), "drawing"),
    (re.compile(r"^(photo|photos|picture|pictures|foto|fotos|image|images)$"), "photo"),
]
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "un": 1, "una": 1, "dos": 2, "tres": 3,
                "cuatro": 4, "cinco": 5, "couple": 2}
QN_RE = re.compile(r"\b(EST-\d{4}-\d{3}[A-Z]?|INV-\d{4}-\d{3})\b", re.IGNORECASE)


def _hub_base() -> str:
    return os.environ.get("EMPIRE_PORTAL_INTERNAL_URL", "http://localhost:3005").rstrip("/")


def default_hub_get(path: str, params: dict) -> dict:
    import httpx

    r = httpx.get(f"{_hub_base()}{path}", params=params, timeout=20.0)
    return r.json()


def load_aliases(path: Optional[Path] = None) -> list[dict[str, Any]]:
    p = path or Path(os.environ.get("MAX_CLIENT_ALIASES_PATH") or ALIASES_PATH)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = data.get("clients") if isinstance(data, dict) else data
    return [r for r in rows or [] if isinstance(r, dict) and r.get("name")]


def _words(text: str) -> list[str]:
    out = []
    for raw in re.split(r"[^a-z0-9áéíóúñ']+", (text or "").lower()):
        w = raw.strip("'")
        w = re.sub(r"'s$", "", w)
        if w:
            out.append(w)
    return out


def _depossess(w: str) -> list[str]:
    """dhalias -> [dhalias, dhalia]; keeps both, the alias match decides."""
    return [w, w[:-1]] if len(w) > 3 and w.endswith("s") else [w]


def _close(a: str, b: str, cutoff: float = 0.8) -> bool:
    return a == b or (len(a) >= 4 and len(b) >= 4 and difflib.SequenceMatcher(None, a, b).ratio() >= cutoff)


def parse_request(text: str) -> dict[str, Any]:
    words = _words(text)
    doc_type = None
    count = None
    for i, w in enumerate(words):
        for rx, t in TYPE_WORDS:
            if rx.match(w):
                doc_type = doc_type or t
        if w.isdigit() and len(w) <= 2 and i > 0 and words[i - 1] in ("last", "latest", "recent", "ultimos", "últimos", "top"):
            count = int(w)
        elif w in NUMBER_WORDS and i > 0 and words[i - 1] in ("last", "latest", "recent", "ultimos", "últimos", "a", "the", "top"):
            count = NUMBER_WORDS[w]
        elif w.isdigit() and len(w) <= 2 and i + 1 < len(words) and words[i + 1] in (
                "docs", "documents", "documentos", "updated", "latest", "recent", "last", "files", "pdfs", "final", "finals"):
            count = int(w)
    qn = QN_RE.search(text or "")
    terms = [w for w in words if w not in FILLER and not w.isdigit() and not any(rx.match(w) for rx, _ in TYPE_WORDS)]
    return {"type": doc_type, "count": count, "terms": terms, "quote_number": qn.group(1).upper() if qn else None,
            "words": words}


def resolve_client(text: str, *, hub_clients: Optional[list[str]] = None,
                   aliases: Optional[list[dict]] = None) -> Optional[dict[str, Any]]:
    """Client named in the text: alias, address, or fuzzy hub client name."""
    aliases = load_aliases() if aliases is None else aliases
    words = _words(text)
    for row in aliases:
        names = [row["name"]] + list(row.get("aliases") or [])
        for name in names:
            name_words = _words(name)
            if not name_words:
                continue
            # every word of the alias/name must appear (fuzzily) in the text
            if all(any(_close(nw, v) for w in words for v in _depossess(w)) for nw in name_words):
                return {"name": row["name"], "via": f"alias:{name}", "address": row.get("address", "")}
        addr = str(row.get("address") or "")
        if addr:
            aw = [w for w in _words(addr) if w not in ("rd", "road", "st", "street", "ave", "avenue", "dr", "drive", "ln", "lane", "ct", "court", "blvd", "way", "pl")]
            num = next((w for w in aw if w.isdigit()), None)
            street = [w for w in aw if not w.isdigit()]
            hits = sum(1 for sw in street if any(_close(sw, w, 0.85) for w in words))
            if (num and num in words) or (street and hits >= min(2, len(street))):
                return {"name": row["name"], "via": "address", "address": addr}
    for client in hub_clients or []:
        cw = [w for w in _words(client) if len(w) >= 4 and w.isalpha() and w not in FILLER
              and w not in ("option", "test", "quote", "project", "addendum", "final", "supplied")]
        if not cw:
            continue
        if all(any(_close(c, v, 0.8) for w in words for v in _depossess(w)) for c in cw[:2]):
            return {"name": client, "via": "hub_client", "address": ""}
    return None


def _fmt(doc: dict) -> dict[str, Any]:
    return {
        "doc_id": doc.get("id"), "title": doc.get("title"), "type": doc.get("type"),
        "version": doc.get("version"), "is_final": doc.get("isFinal"),
        "client": doc.get("client") or doc.get("designer"), "quote_number": doc.get("quoteNumber"),
        "modified": doc.get("modified"), "filename": doc.get("filename"),
    }


def _is_pdf(doc: dict) -> bool:
    name = str(doc.get("filename") or doc.get("location") or "").lower()
    return doc.get("type") != "photo" and (name.endswith(".pdf") or not name)


def find_docs(text: str, *, hub_get: Optional[HubGet] = None,
              aliases: Optional[list[dict]] = None) -> dict[str, Any]:
    """Resolve a natural-language doc request.

    Returns {"found": bool, "docs": [...], "client": ..., "count": n,
             "closest": [...], "query": text}
    """
    get = hub_get or default_hub_get
    req = parse_request(text)
    index = get("/api/v1/docs-hub", {"final": "1", "limit": "1"}) or {}
    hub_clients = ((index.get("facets") or {}).get("clients")) or []
    client = resolve_client(text, hub_clients=[] if req["quote_number"] else hub_clients, aliases=aliases)
    params: dict[str, str] = {"final": "1", "limit": "60"}
    if req["type"]:
        params["type"] = req["type"]
    leftover = list(req["terms"])
    if client:
        params["client"] = client["name"]
        # words that only named the client are not search terms
        cl_words = set(_words(client["name"])) | {w for a in (aliases or load_aliases()) if a.get("name") == client["name"]
                                                 for al in (a.get("aliases") or []) for w in _words(al)}
        cl_words |= set(_words(client.get("address") or ""))
        leftover = [t for t in leftover if not any(_close(t, c) or _close(t[:-1], c) for c in cl_words)]
    if req["quote_number"]:
        params["quote"] = req["quote_number"]
    docs: list[dict] = []
    if client or req["quote_number"]:
        listing = get("/api/v1/docs-hub", params) or {}
        docs = [d for d in listing.get("docs") or [] if req["type"] == "photo" or _is_pdf(d)]
        if leftover:
            narrowed = [d for d in docs if all(t in _hay(d) for t in leftover)]
            docs = narrowed or docs
    if not docs and leftover:
        res = get("/api/v1/docs-hub/resolve", {"q": " ".join(leftover + ([req["type"]] if req["type"] else []))}) or {}
        if res.get("found") and res.get("doc"):
            docs = [res["doc"]] + [a for a in res.get("alternatives") or []]
    docs.sort(key=lambda d: d.get("modified") or "", reverse=True)
    count = req["count"] or 1
    picked = docs[:max(1, min(count, 5))]
    out: dict[str, Any] = {
        "query": text, "found": bool(picked), "docs": [_fmt(d) for d in picked], "count": count,
        "client": client["name"] if client else None, "client_via": client["via"] if client else None,
        "type": req["type"], "closest": [],
    }
    if not picked:
        out["closest"] = closest_matches(text, hub_clients=hub_clients, hub_get=get)
    return out


def _hay(doc: dict) -> str:
    return " ".join(str(doc.get(k) or "") for k in ("title", "filename", "client", "designer", "project",
                                                     "quoteNumber", "jobNumber", "invoiceNumber", "jobFolder", "type")).lower()


def closest_matches(text: str, *, hub_clients: Optional[list[str]] = None, hub_get: Optional[HubGet] = None,
                    limit: int = 4) -> list[dict[str, Any]]:
    """Nearest client names (and their latest final doc) for an honest 'no match' reply."""
    get = hub_get or default_hub_get
    terms = parse_request(text)["terms"]
    scored = []
    for client in hub_clients or []:
        best = 0.0
        for cw in _words(client):
            for t in terms:
                best = max(best, difflib.SequenceMatcher(None, cw, t).ratio())
        if best >= 0.5:
            scored.append((best, client))
    scored.sort(reverse=True)
    out = []
    for _score, client in scored[:limit]:
        try:
            listing = get("/api/v1/docs-hub", {"client": client, "final": "1", "limit": "1"}) or {}
            latest = (listing.get("docs") or [None])[0]
        except Exception:
            latest = None
        out.append({"client": client, "latest": _fmt(latest) if latest else None})
    return out


def fetch_pdf(doc_id: str, *, http_get: Optional[Callable[[str, dict], Any]] = None) -> bytes:
    """PDF bytes for an indexed doc (portal /docs-hub/file, local only)."""
    url = f"{_hub_base()}/api/v1/docs-hub/file"
    if http_get is None:
        import httpx

        r = httpx.get(url, params={"id": doc_id}, timeout=30.0)
        data = r.content if r.status_code == 200 else b""
    else:
        r = http_get(url, {"id": doc_id})
        data = getattr(r, "content", r) or b""
    return data if isinstance(data, (bytes, bytearray)) and bytes(data[:5]) == b"%PDF-" else b""


# --- WhatsApp job filing (kept alongside Final Docs hub lookup) ---


def _config_path() -> Path:
    return Path(os.environ.get("MAX_CLIENT_ALIASES_PATH") or ALIASES_PATH)


def jobs_root(override: Optional[Path | str] = None) -> Path:
    """Edition-scoped jobs directory.

    Override order: explicit path, WHATSAPP_JOBS_ROOT, then EMPIRE_DATA_DIR/jobs
    (Max-e = /data/amp/jobs, Maxine = /data/maxine/jobs). Never defaults to a
    shared ~/jobs tree, so a family edition cannot see Rafael's folders.
    """
    if override:
        return Path(override)
    env = (os.getenv("WHATSAPP_JOBS_ROOT") or "").strip()
    if env:
        return Path(env)
    try:
        from app.services.data_paths import data_root

        return data_root() / "jobs"
    except Exception:
        return Path(os.getenv("EMPIRE_DATA_DIR") or ".") / "jobs"


def load_client_aliases() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def add_client_alias(
    name: str,
    slug: str,
    aliases: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Append one client row. Atomic write + timestamped backup. No phone numbers.

    load_client_aliases() reads the file every call (no cache), so the next
    probe sees the new row — hot-reload safe.
    """
    title = re.sub(r"\s+", " ", (name or "").strip())
    clean_slug = slugify(slug or title)
    if not title or not clean_slug:
        raise ValueError("client alias needs a name and slug")
    extra = [str(a).strip() for a in (aliases or []) if str(a).strip()]
    alias_list = [
        item for item in dict.fromkeys([title, *extra, title.lower(), clean_slug.replace("-", " ")])
        if item and not _looks_like_phone(item)
    ]
    entry = {"slug": clean_slug, "name": title, "aliases": alias_list, "address": ""}
    for key in _ALIAS_PHONE_KEYS:
        entry.pop(key, None)
    with _alias_write_lock:
        path = _config_path()
        data = load_client_aliases()
        if not data:
            data = {"clients": []}
        clients = list(data.get("clients") or [])
        for existing in clients:
            if not isinstance(existing, dict):
                continue
            if str(existing.get("slug") or "") == clean_slug:
                merged = list(existing.get("aliases") or [])
                for item in alias_list:
                    if item not in merged:
                        merged.append(item)
                existing["aliases"] = merged
                if not existing.get("name"):
                    existing["name"] = title
                _write_aliases_atomic(path, data)
                return existing
        clients.append(entry)
        data["clients"] = clients
        _write_aliases_atomic(path, data)
        return entry


def _write_aliases_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(f"{path.name}.bak-{stamp}")
        try:
            shutil.copy2(path, backup)
        except OSError as exc:
            logger.warning("could not backup client aliases %s: %s", path, exc)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".client-aliases-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _looks_like_phone(value: str) -> bool:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return len(digits) >= 10


def normalize_term(term: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", (term or "").lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (name or "").lower()).strip()
    return re.sub(r"[-\s]+", "-", s)


def _clients() -> list[dict[str, Any]]:
    data = load_client_aliases()
    clients = list(data.get("clients") or [])
    if isinstance(data, dict) and not clients:
        for key, value in data.items():
            if key == "clients":
                continue
            if isinstance(value, dict):
                clients.append(value)
            elif isinstance(value, str):
                clients.append({"slug": value, "name": str(key).title(), "aliases": [key]})
    return [c for c in clients if isinstance(c, dict)]


def _quote_customer(raw_text: str, base_dir: Path) -> Optional[dict[str, Any]]:
    quote_match = re.search(r"\b(est[-_\s]?\d+|q[-_\s]?\d+)\b", raw_text, re.IGNORECASE)
    if not quote_match:
        return None
    q_code = quote_match.group(1).upper().replace(" ", "-").replace("_", "-")
    try:
        from app.db.database import get_db

        with get_db() as conn:
            row = conn.execute(
                "SELECT customer_name, project_name FROM quotes_v2 "
                "WHERE upper(quote_number) = ? OR id = ? LIMIT 1",
                (q_code, q_code),
            ).fetchone()
        if row and row[0]:
            c_name = row[0]
            return {
                "slug": slugify(c_name),
                "client_name": c_name,
                "folder_path": str(base_dir / slugify(c_name)),
                "match_reason": f"quote {q_code}",
            }
    except Exception:
        return None
    return None


def probe_job_text(
    text: str,
    *,
    jobs_root_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Classify text as empty, unique, ambiguous, or unknown. Never guesses."""
    if not text or not str(text).strip():
        return {"status": "empty", "matches": []}

    raw_text = str(text).strip()
    norm_text = normalize_term(raw_text)
    base_dir = jobs_root(jobs_root_path)

    quoted = _quote_customer(raw_text, base_dir)
    if quoted:
        return {"status": "unique", "match": quoted, "matches": [quoted]}

    text_tokens: list[str] = []
    for w in _words(raw_text):
        text_tokens.extend(_depossess(w))
    text_token_set = {t for t in text_tokens if t and t not in FILLER}

    matches: list[dict[str, Any]] = []
    for client in _clients():
        c_slug = client.get("slug") or slugify(client.get("name", ""))
        c_name = client.get("name") or c_slug
        terms = [c_slug, str(c_name).lower()] + [str(a).lower() for a in client.get("aliases") or []]
        if client.get("address"):
            terms.append(str(client.get("address")).lower())
        hit = ""
        for term in terms:
            norm_term = normalize_term(term)
            if norm_term and re.search(r"\b" + re.escape(norm_term) + r"\b", norm_text):
                hit = norm_term
                break
            term_words = [w for w in _words(term) if w not in FILLER and len(w) >= 3]
            if term_words and all(any(tw == nw for tw in text_token_set) for nw in term_words):
                hit = norm_term or term
                break
        if hit:
            matches.append({
                "slug": c_slug,
                "client_name": c_name,
                "folder_path": str(base_dir / c_slug),
                "match_reason": f"matched term '{hit}'",
            })

    if len(matches) == 1:
        return {"status": "unique", "match": matches[0], "matches": matches}
    if len(matches) > 1:
        return {"status": "ambiguous", "matches": matches}

    dir_matches: list[dict[str, Any]] = []
    if base_dir.is_dir():
        try:
            for entry in base_dir.iterdir():
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                words = entry.name.lower().replace("-", " ").replace("_", " ")
                if entry.name.lower() in norm_text or (words and words in norm_text):
                    dir_matches.append({
                        "slug": entry.name,
                        "client_name": entry.name.replace("-", " ").title(),
                        "folder_path": str(entry),
                        "match_reason": f"matched folder {entry.name}",
                    })
        except OSError:
            pass
    if len(dir_matches) == 1:
        return {"status": "unique", "match": dir_matches[0], "matches": dir_matches}
    if len(dir_matches) > 1:
        return {"status": "ambiguous", "matches": dir_matches}
    return {"status": "unknown", "matches": []}


def resolve_job_folder(
    text: str,
    *,
    jobs_root_path: Optional[Path | str] = None,
) -> Optional[dict[str, Any]]:
    """Unique match only. None if empty, unknown, or ambiguous."""
    probed = probe_job_text(text, jobs_root_path=jobs_root_path)
    if probed.get("status") == "unique":
        return probed.get("match")
    return None


def existing_job_slug(job_slug: str, *, jobs_root_path: Optional[Path | str] = None) -> str:
    """Return a sanitized slug only if it is an existing folder under jobs_root."""
    raw = (job_slug or "").strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        return ""
    slug = re.sub(r"[^a-z0-9-]", "", raw.lower())
    if not slug or slug in {".", ".."}:
        return ""
    base_dir = jobs_root(jobs_root_path).resolve()
    try:
        candidate = (base_dir / slug).resolve()
    except (OSError, RuntimeError):
        return ""
    if candidate.parent != base_dir:
        return ""
    if candidate.is_dir():
        return slug
    return ""


def list_job_folders(*, jobs_root_path: Optional[Path | str] = None) -> list[dict[str, str]]:
    """Existing job folders under this edition's jobs root (plus named aliases that exist)."""
    base_dir = jobs_root(jobs_root_path)
    found: dict[str, dict[str, str]] = {}
    if base_dir.is_dir():
        try:
            for entry in base_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    found[entry.name] = {
                        "slug": entry.name,
                        "client_name": entry.name.replace("-", " ").title(),
                        "folder_path": str(entry),
                    }
        except OSError:
            pass
    for client in _clients():
        slug = str(client.get("slug") or slugify(client.get("name", "")))
        if not slug or slug not in found:
            continue
        found[slug]["client_name"] = str(client.get("name") or found[slug]["client_name"])
    return sorted(found.values(), key=lambda row: row["slug"])


def list_known_jobs(*, jobs_root_path: Optional[Path | str] = None) -> list[dict[str, str]]:
    """Alias clients plus existing folders — used for close-match questions."""
    base_dir = jobs_root(jobs_root_path)
    found: dict[str, dict[str, str]] = {}
    for client in _clients():
        slug = str(client.get("slug") or slugify(client.get("name", "")))
        if slug:
            found[slug] = {
                "slug": slug,
                "client_name": str(client.get("name") or slug),
                "folder_path": str(base_dir / slug),
            }
    for row in list_job_folders(jobs_root_path=jobs_root_path):
        found.setdefault(row["slug"], row)
    return sorted(found.values(), key=lambda row: row["slug"])


def suggest_jobs(text: str, *, jobs_root_path: Optional[Path | str] = None, limit: int = 5) -> list[dict[str, str]]:
    """Closest alias/folder names. Never auto-picks; callers must ask."""
    terms = [w for w in _words(text or "") if w not in FILLER and not w.isdigit()]
    expanded = []
    for t in terms:
        expanded.extend(_depossess(t))
    if not expanded:
        return list_known_jobs(jobs_root_path=jobs_root_path)[:limit]
    scored: list[tuple[float, dict[str, str]]] = []
    for row in list_known_jobs(jobs_root_path=jobs_root_path):
        names = [row.get("slug") or "", row.get("client_name") or ""]
        best = 0.0
        for name in names:
            for nw in _words(name):
                if nw in FILLER:
                    continue
                for t in expanded:
                    best = max(best, difflib.SequenceMatcher(None, nw, t).ratio())
        if best >= 0.35:
            scored.append((best, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    picked = [row for _score, row in scored[:limit]]
    if picked:
        return picked
    return list_known_jobs(jobs_root_path=jobs_root_path)[:limit]
