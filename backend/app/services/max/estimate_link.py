"""Resolve the job's actual estimate document for "send me the estimate/quote link".

FP-N10 (Night Lab 2026-10-30/31): "send me the link for the Le Midi estimate"
returned the newest file anywhere on disk (a fabric-store mockup JPG, earlier a
lab PDF). Estimate links must come from the job's own records:

  1. EST-YYYY-NNN in the message/history -> quotes_v2.pdf_path, else that
     quote's job -> job_documents.
  2. Client/job words -> jobs (title / customer) -> job_documents estimate
     (client copy, not superseded, highest revision), else quotes_v2.pdf_path.
  3. Nothing verified on disk -> an honest "not found" (never a guess).

Read-only. No sends. Tests use temp DBs only.
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional

_ESTIMATE_WORDS = re.compile(
    r"(?i)\b(?:estimate|estimates|quote|quotes|quotation|presupuesto|cotizaci[oó]n|est-\d{4}-\d+)\b"
)
_EST_NUM = re.compile(r"(?i)\bEST-(\d{4})-(\d{1,5})\b")
_INTERNAL = re.compile(r"(?i)\binternal\b")
_STOP = {
    "send", "link", "links", "estimate", "estimates", "quote", "quotes", "quotation",
    "the", "for", "me", "a", "an", "to", "of", "please", "this", "that", "latest",
    "newest", "give", "show", "open", "share", "studio", "pdf", "file", "job", "client",
    "can", "you", "get", "new", "revised", "current", "internal", "copy", "and", "with",
    "presupuesto", "cotizacion", "cotización", "enlace", "mandame", "dame", "por", "favor",
}

# Paths that are never a job's estimate (caches, mockups, lab/test scratch).
EXCLUDED_PATH_PARTS = (
    "fabrics-preview", "mockup_cache", "/mockups/", "/mockup/", "max_continuous_test",
    "nightlab", "night_lab", "nl1031", "daysmoke", "day_smoke", "day-smoke",
    "/scratch/", "/worktrees/", "/.cache/", "/lab/", "_lab_",
)


def is_excluded_path(path: str | None) -> bool:
    low = os.path.expanduser(str(path or "")).replace("\\", "/").lower()
    if not low:
        return True
    return any(part in low for part in EXCLUDED_PATH_PARTS)


def is_estimate_link_request(text: str | None) -> bool:
    return bool(_ESTIMATE_WORDS.search(text or ""))


def _db_path() -> str:
    return os.getenv("EMPIRE_TASK_DB") or str(Path.home() / "empire-data" / "empire.db")


def _data_root() -> Path:
    return Path(os.getenv("EMPIRE_DATA_DIR") or (Path.home() / "empire-data"))


def _connect(db_path: str | None) -> Optional[sqlite3.Connection]:
    path = db_path or _db_path()
    if not os.path.isfile(path):
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _history_text(history: Any, n: int = 6) -> str:
    parts = []
    for h in list(history or [])[-n:]:
        c = h.get("content") if isinstance(h, dict) else getattr(h, "content", "")
        parts.append(str(c or ""))
    return "\n".join(parts)


def _tokens(text: str) -> list[str]:
    out = []
    for t in re.split(r"[^a-z0-9]+", (text or "").lower()):
        if len(t) >= 4 and t not in _STOP and not t.isdigit():
            out.append(t)
    return out


def _url_to_disk(url: str | None, filename: str | None, job_id: str | None) -> Optional[str]:
    cands: list[Path] = []
    u = str(url or "")
    marker = "/api/v1/files/download/"
    if marker in u:
        rel = u.split(marker, 1)[1].split("?", 1)[0]
        cands.append(_data_root() / "uploads" / rel)
    if job_id and filename:
        cands.append(_data_root() / "uploads" / "jobs" / Path(str(job_id)).name / Path(filename).name)
    for c in cands:
        try:
            if c.is_file() and not is_excluded_path(str(c)):
                return str(c.resolve())
        except OSError:
            continue
    return None


def _job_estimate_doc(conn, job_id: str, internal: bool) -> Optional[dict[str, Any]]:
    types = ("estimate_internal",) if internal else ("estimate",)
    q = (
        "SELECT * FROM job_documents WHERE job_id = ? AND document_type IN (%s) "
        "AND COALESCE(superseded,0) = 0 ORDER BY COALESCE(revision,1) DESC, created_at DESC"
        % ",".join("?" * len(types))
    )
    try:
        rows = conn.execute(q, (job_id, *types)).fetchall()
    except sqlite3.Error:
        return None
    for r in rows:
        path = _url_to_disk(r["url"], r["filename"], job_id)
        if path and path.lower().endswith(".pdf"):
            return {"path": path, "name": os.path.basename(path), "job_id": job_id,
                    "revision": r["revision"], "source": "job_documents", "doc_id": r["id"]}
    return None


def _quote_pdf(conn, where: str, args: tuple) -> Optional[dict[str, Any]]:
    try:
        rows = conn.execute(
            "SELECT quote_number, job_id, pdf_path, customer_name FROM quotes_v2 WHERE "
            + where + " AND COALESCE(is_test,0)=0 ORDER BY updated_at DESC, created_at DESC",
            args,
        ).fetchall()
    except sqlite3.Error:
        return None
    for r in rows:
        p = os.path.expanduser(str(r["pdf_path"] or ""))
        if not (p and os.path.isfile(p)) and r["quote_number"]:
            # Quote PDFs are written to <data>/quotes/pdf/<EST>.pdf even when pdf_path is blank.
            p = str(_data_root() / "quotes" / "pdf" / f"{Path(str(r['quote_number'])).name}.pdf")
        if p and os.path.isfile(p) and not is_excluded_path(p):
            return {"path": os.path.realpath(p), "name": os.path.basename(p), "job_id": r["job_id"],
                    "quote_number": r["quote_number"], "source": "quotes_v2"}
    return None


def _jobs_for_tokens(conn, tokens: list[str]) -> list[str]:
    if not tokens:
        return []
    try:
        rows = conn.execute(
            "SELECT j.id, j.title, COALESCE(c.name,'') AS cname, j.created_at FROM jobs j "
            "LEFT JOIN customers c ON c.id = j.customer_id ORDER BY j.created_at DESC"
        ).fetchall()
    except sqlite3.Error:
        return []
    hits = []
    for r in rows:
        hay = f"{r['title']} {r['cname']}".lower()
        hay_norm = re.sub(r"[^a-z0-9]+", " ", hay)
        if any(t in hay_norm.split() or t in hay_norm.replace(" ", "") for t in tokens):
            hits.append(r["id"])
    return hits


def find_job_estimate(message: str, history: Any = None, *, db_path: str | None = None) -> dict[str, Any]:
    internal = bool(_INTERNAL.search(message or ""))
    conn = _connect(db_path)
    if conn is None:
        return {"found": False, "reason": "no_db"}
    try:
        for text in (message or "", _history_text(history)):
            m = _EST_NUM.search(text)
            if m:
                num = f"EST-{m.group(1)}-{int(m.group(2)):03d}"
                hit = _quote_pdf(conn, "quote_number = ?", (num,))
                if hit:
                    return {"found": True, "match": hit, "quote_number": num}
                row = conn.execute("SELECT job_id FROM quotes_v2 WHERE quote_number = ?", (num,)).fetchone()
                if row and row["job_id"]:
                    doc = _job_estimate_doc(conn, row["job_id"], internal)
                    if doc:
                        return {"found": True, "match": doc, "quote_number": num}
                return {"found": False, "reason": "quote_pdf_missing", "quote_number": num}
            for job_id in _jobs_for_tokens(conn, _tokens(text)):
                doc = _job_estimate_doc(conn, job_id, internal) or _quote_pdf(conn, "job_id = ?", (job_id,))
                if doc:
                    return {"found": True, "match": doc}
            toks = _tokens(text)
            if toks:
                like = " OR ".join("lower(customer_name) LIKE ?" for _ in toks)
                hit = _quote_pdf(conn, f"({like})", tuple(f"%{t}%" for t in toks))
                if hit:
                    return {"found": True, "match": hit}
                if text is message:
                    # The user named someone; don't drift to an older chat's job.
                    return {"found": False, "reason": "no_estimate_for_job", "tokens": toks}
        return {"found": False, "reason": "no_job"}
    finally:
        conn.close()


def estimate_link_reply(message: str, history: Any = None, *, db_path: str | None = None) -> dict[str, Any]:
    looked = find_job_estimate(message, history, db_path=db_path)
    if not looked.get("found"):
        reason = looked.get("reason")
        if reason == "quote_pdf_missing":
            text = f"I found {looked.get('quote_number')} but no estimate PDF on file for it, so I won't send a different file."
        elif reason == "no_job":
            text = "Which job's estimate? I couldn't tell the job from the chat, so I won't guess a file."
        else:
            text = "I couldn't find an estimate document for that job in its records, so I won't send a different file."
        return {"text": text, "skill": "estimate_link", "found": False, "reason": reason}
    match = looked["match"]
    path = match["path"]
    from app.services.max.latest_job_file import studio_share_url
    url = studio_share_url(path)
    name = match["name"]
    label = match.get("quote_number") or (f"REV {match['revision']}" if match.get("revision") else "")
    if url:
        text = f"[{name}]({url})" + (f" — {label}" if label else "")
    else:
        text = f"{name} is on disk ({path}). Studio share host is not configured on this edition."
    return {"text": text, "skill": "estimate_link", "found": True, "path": path, "url": url,
            "name": name, "job_id": match.get("job_id"), "source": match.get("source")}
