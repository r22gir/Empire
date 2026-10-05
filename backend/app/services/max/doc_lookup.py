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
import os
import re
from pathlib import Path
from typing import Any, Callable, Optional

HubGet = Callable[[str, dict], dict]

ALIASES_PATH = Path(__file__).resolve().parents[2] / "config" / "client_aliases.json"

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
