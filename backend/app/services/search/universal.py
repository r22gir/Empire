"""Fan-out universal search: screens, jobs, quotes, invoices, people,
files, organizer, pending mail, cheap chat memory.

Each source has a timeout and a result cap. One slow source never blocks
the response. Unknown EMPIRE_EDITION returns empty (fail-closed).
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from app.services.search.edition import (
    can_read_business_directory,
    can_read_workroom_jobs,
    contains_blocked_term,
    edition_meta,
    is_family_edition,
    is_workroom_business,
    process_edition,
)

logger = logging.getLogger(__name__)

SOURCE_TIMEOUT_S = float(os.getenv("UNIVERSAL_SEARCH_SOURCE_TIMEOUT", "0.45"))
OVERALL_TIMEOUT_S = float(os.getenv("UNIVERSAL_SEARCH_OVERALL_TIMEOUT", "1.4"))
PER_SOURCE_CAP = int(os.getenv("UNIVERSAL_SEARCH_PER_SOURCE_CAP", "6"))
TOTAL_CAP = int(os.getenv("UNIVERSAL_SEARCH_TOTAL_CAP", "40"))
MIN_QUERY_LEN = 1

GROUP_ORDER = (
    "screen",
    "job",
    "quote",
    "invoice",
    "person",
    "file",
    "organizer",
    "mail",
    "memory",
)

GROUP_LABELS = {
    "screen": "Screens",
    "job": "Jobs",
    "quote": "Quotes",
    "invoice": "Invoices",
    "person": "People",
    "file": "Files",
    "organizer": "Organizer",
    "mail": "Pending email",
    "memory": "Memory",
}

_REQUIRED_SCREENS = (
    "improvements",
    "tokens",
    "family-help",
    "organizer",
    "minimax-usage",
    "presentation-mode",
    "presentation",
    "max-avatar",
    "search",
)


@dataclass
class SearchHit:
    id: str
    type: str
    title: str
    subtitle: str = ""
    href: str = ""
    action: dict = field(default_factory=dict)
    score: float = 0.0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "subtitle": self.subtitle,
            "href": self.href,
            "action": self.action or {
                "kind": "open",
                "label": "Open",
                "href": self.href,
            },
            "score": round(self.score, 3),
            **({"extra": self.extra} if self.extra else {}),
        }


def _open(href: str, label: str = "Open") -> dict:
    return {"kind": "open", "label": label, "href": href}


def _navigate(href: str, label: str = "Open") -> dict:
    return {"kind": "navigate", "label": label, "href": href}


def _call(phone: str, href: str) -> dict:
    return {"kind": "call", "label": "Call", "phone": phone, "href": href}


def _draft_reply(*, href: str, mail_id: str = "", source: str = "") -> dict:
    return {
        "kind": "draft_reply",
        "label": "Draft reply",
        "href": href,
        "mail_id": mail_id,
        "source": source,
    }


_STOP = frozenset({
    "find", "the", "a", "an", "my", "me", "please", "show", "open", "get",
    "quote", "quotes", "estimate", "invoice", "invoices", "job", "jobs",
    "email", "mail", "file", "files", "pdf", "for", "of", "to", "in",
    "where", "is", "are", "how", "do", "i", "can", "last", "latest",
})


def search_tokens(query: str) -> list[str]:
    """'Marley's quote' → ['marley'] so record search hits the name."""
    q = (query or "").lower().replace("'s", " ").replace("’s", " ")
    parts = re.findall(r"[a-z0-9][a-z0-9._-]{1,}", q)
    kept = [p for p in parts if p not in _STOP]
    return kept or parts


def _like(q: str) -> str:
    token = (search_tokens(q) or [q])[0]
    return f"%{token.replace('%', '').replace('_', '')}%"


def _score(query: str, *fields: str) -> float:
    tokens = search_tokens(query) or [(query or "").strip().lower()]
    if not any(tokens):
        return 0.0
    best = 0.0
    for raw in fields:
        t = (raw or "").strip().lower()
        if not t:
            continue
        for q in tokens:
            if not q:
                continue
            if t == q:
                best = max(best, 1.0)
            elif t.startswith(q):
                best = max(best, 0.9)
            elif q in t:
                best = max(best, 0.7)
            elif any(w.startswith(q) for w in t.split()):
                best = max(best, 0.75)
    return best


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (name,),
        ).fetchone()
        return bool(row)
    except Exception:
        return False


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _db():
    from app.db.database import get_db
    return get_db()


def _keep_text(edition: str, *parts: str) -> bool:
    blob = " ".join(p or "" for p in parts)
    return not contains_blocked_term(blob, edition)


def search_screens(query: str, *, family: bool, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    """Screens / nav from the live UI map (real LeftNav + MaxHome ids)."""
    from app.services.max.ui_map import features_for_edition

    q = (query or "").strip().lower()
    feats = features_for_edition(family=family)
    hits: list[SearchHit] = []
    for feat in feats:
        aliases = " ".join(
            [feat.name, feat.id, *(feat.aliases_en or ()), *(feat.aliases_es or ())]
        )
        score = _score(q, feat.name, feat.id.replace("-", " "), aliases) if q else (
            0.55 if feat.id in _REQUIRED_SCREENS else 0.2
        )
        if q and score <= 0:
            continue
        hits.append(SearchHit(
            id=f"screen:{feat.id}",
            type="screen",
            title=feat.name,
            subtitle=feat.group.replace("-", " ").title() if feat.group else "Screen",
            href=feat.href,
            action=_navigate(feat.href),
            score=score + (0.05 if feat.id in _REQUIRED_SCREENS else 0.0),
            extra={"feature_id": feat.id, "workroom_only": feat.workroom_only},
        ))
    hits.sort(key=lambda h: (-h.score, h.title.lower()))
    return hits[:cap]


def search_jobs(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    if not can_read_workroom_jobs(edition):
        return []
    if is_family_edition(edition):
        return []
    pattern = _like(query)
    hits: list[SearchHit] = []
    with _db() as conn:
        if not _table_exists(conn, "jobs"):
            return []
        cols = _cols(conn, "jobs")
        client = "j.client_name" if "client_name" in cols else "''"
        title = "j.title" if "title" in cols else "''"
        desc = "j.description" if "description" in cols else "''"
        num = "j.job_number" if "job_number" in cols else "''"
        biz = "j.business_unit" if "business_unit" in cols else "''"
        join_c = "LEFT JOIN customers c ON j.customer_id = c.id" if _table_exists(conn, "customers") else ""
        cust = "c.name" if join_c else "''"
        join_i = "LEFT JOIN job_items ji ON ji.job_id = j.id" if _table_exists(conn, "job_items") else ""
        item = "ji.name" if join_i else "''"
        sql = f"""
            SELECT DISTINCT j.id, {client} AS client_name, {title} AS title,
                   {num} AS job_number, {biz} AS business_unit, {cust} AS customer_name
            FROM jobs j
            {join_c}
            {join_i}
            WHERE {client} LIKE ? OR {title} LIKE ? OR {desc} LIKE ?
               OR {num} LIKE ? OR {cust} LIKE ? OR {item} LIKE ?
            ORDER BY j.id DESC
            LIMIT ?
        """
        rows = conn.execute(sql, (pattern, pattern, pattern, pattern, pattern, pattern, cap * 3)).fetchall()
        for r in rows:
            d = dict(r)
            name = d.get("client_name") or d.get("customer_name") or d.get("title") or "Job"
            jid = str(d.get("id") or "")
            href = f"/?product=workroom&section=jobhub&job={jid}"
            if not _keep_text(edition, name, str(d.get("job_number") or ""), str(d.get("title") or "")):
                continue
            hits.append(SearchHit(
                id=f"job:{jid}",
                type="job",
                title=name,
                subtitle=" · ".join(x for x in (d.get("job_number"), d.get("title"), d.get("business_unit")) if x),
                href=href,
                action=_open(href, "Open job"),
                score=_score(query, name, d.get("job_number") or "", d.get("title") or "") + 0.08,
            ))
    return hits[:cap]


def search_quotes(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    pattern = _like(query)
    family = is_family_edition(edition)
    hits: list[SearchHit] = []
    with _db() as conn:
        if not _table_exists(conn, "quotes_v2"):
            return []
        cols = _cols(conn, "quotes_v2")
        biz_sel = "business_unit" if "business_unit" in cols else "'' AS business_unit"
        notes = "notes" if "notes" in cols else "''"
        email = "customer_email" if "customer_email" in cols else "''"
        order = "created_at DESC" if "created_at" in cols else "id DESC"
        rows = conn.execute(
            f"""
            SELECT id, quote_number, customer_name, project_name, status, {biz_sel}
            FROM quotes_v2
            WHERE customer_name LIKE ? OR project_name LIKE ? OR quote_number LIKE ?
               OR {notes} LIKE ? OR {email} LIKE ?
            ORDER BY {order} LIMIT ?
            """,
            (pattern, pattern, pattern, pattern, pattern, cap * 3),
        ).fetchall()
        for r in rows:
            d = dict(r)
            if family and is_workroom_business(d.get("business_unit")):
                continue
            title = d.get("quote_number") or d.get("project_name") or "Quote"
            who = d.get("customer_name") or ""
            qid = str(d.get("id") or "")
            href = f"/?product=workroom&section=jobhub&quote={qid}" if not family else f"/?screen=quote&quote={qid}"
            if family:
                href = f"/?screen=quote&quote={qid}"
            if not _keep_text(edition, title, who, d.get("project_name") or ""):
                continue
            hits.append(SearchHit(
                id=f"quote:{qid}",
                type="quote",
                title=f"{title}" + (f" — {who}" if who else ""),
                subtitle=" · ".join(x for x in (d.get("status"), d.get("project_name"), d.get("business_unit")) if x),
                href=href,
                action=_open(href, "Open quote"),
                score=_score(query, title, who, d.get("project_name") or "") + 0.06,
            ))
    return hits[:cap]


def search_invoices(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    pattern = _like(query)
    family = is_family_edition(edition)
    hits: list[SearchHit] = []
    with _db() as conn:
        if not _table_exists(conn, "invoices"):
            return []
        cols = _cols(conn, "invoices")
        num = "i.invoice_number" if "invoice_number" in cols else "''"
        client = "i.client_name" if "client_name" in cols else "''"
        biz = "i.business_unit" if "business_unit" in cols else "''"
        status = "i.status" if "status" in cols else "''"
        join_c = "LEFT JOIN customers c ON c.id = i.customer_id" if _table_exists(conn, "customers") else ""
        cust = "c.name" if join_c else "''"
        rows = conn.execute(
            f"""
            SELECT i.id, {num} AS invoice_number, {client} AS client_name,
                   {biz} AS business_unit, {status} AS status, {cust} AS customer_name
            FROM invoices i
            {join_c}
            WHERE {num} LIKE ? OR {client} LIKE ? OR {cust} LIKE ?
            ORDER BY i.id DESC LIMIT ?
            """,
            (pattern, pattern, pattern, cap * 3),
        ).fetchall()
        for r in rows:
            d = dict(r)
            if family and is_workroom_business(d.get("business_unit")):
                continue
            who = d.get("client_name") or d.get("customer_name") or ""
            numv = d.get("invoice_number") or f"Invoice {d.get('id')}"
            iid = str(d.get("id") or "")
            href = f"/?screen=invoices&invoice={iid}"
            if not _keep_text(edition, numv, who):
                continue
            hits.append(SearchHit(
                id=f"invoice:{iid}",
                type="invoice",
                title=f"{numv}" + (f" — {who}" if who else ""),
                subtitle=" · ".join(x for x in (d.get("status"), d.get("business_unit")) if x),
                href=href,
                action=_open(href, "Open invoice"),
                score=_score(query, numv, who),
            ))
    return hits[:cap]


def search_people(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    if not can_read_business_directory(edition) and is_family_edition(edition):
        # Family still searches their own contacts table (own data dir),
        # but never the Workroom customer directory.
        pass
    pattern = _like(query)
    family = is_family_edition(edition)
    hits: list[SearchHit] = []
    with _db() as conn:
        if _table_exists(conn, "customers") and can_read_business_directory(edition):
            cols = _cols(conn, "customers")
            biz = "business" if "business" in cols else "'' AS business"
            phone_col = "phone" if "phone" in cols else "'' AS phone"
            rows = conn.execute(
                f"""
                SELECT id, name, email, {phone_col}, company, {biz}
                FROM customers
                WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? OR company LIKE ?
                ORDER BY name LIMIT ?
                """,
                (pattern, pattern, pattern, pattern, cap * 2),
            ).fetchall()
            for r in rows:
                d = dict(r)
                if family and is_workroom_business(d.get("business")):
                    continue
                name = d.get("name") or "Customer"
                cid = str(d.get("id") or "")
                href = f"/?product=crm&customer={cid}"
                phone = (d.get("phone") or "").strip()
                if not _keep_text(edition, name, d.get("company") or "", d.get("email") or ""):
                    continue
                action = _call(phone, href) if phone else _open(href, "Open")
                hits.append(SearchHit(
                    id=f"person:customer:{cid}",
                    type="person",
                    title=name,
                    subtitle=" · ".join(x for x in (d.get("company"), d.get("email"), phone, d.get("business")) if x),
                    href=href,
                    action=action,
                    score=_score(query, name, d.get("company") or "", d.get("email") or ""),
                ))
        if _table_exists(conn, "contacts"):
            cols = _cols(conn, "contacts")
            phone_col = "phone" if "phone" in cols else "'' AS phone"
            rows = conn.execute(
                f"""
                SELECT id, name, email, {phone_col}, type
                FROM contacts
                WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?
                ORDER BY name LIMIT ?
                """,
                (pattern, pattern, pattern, cap * 2),
            ).fetchall()
            for r in rows:
                d = dict(r)
                name = d.get("name") or "Contact"
                cid = str(d.get("id") or "")
                href = f"/?screen=inbox&contact={cid}"
                phone = (d.get("phone") or "").strip()
                if not _keep_text(edition, name, d.get("email") or ""):
                    continue
                if any(h.id.endswith(f":{cid}") and h.title.lower() == name.lower() for h in hits):
                    continue
                action = _call(phone, href) if phone else _open(href, "Open")
                hits.append(SearchHit(
                    id=f"person:contact:{cid}",
                    type="person",
                    title=name,
                    subtitle=" · ".join(x for x in (d.get("type"), d.get("email"), phone) if x),
                    href=href,
                    action=action,
                    score=_score(query, name, d.get("email") or ""),
                ))
    hits.sort(key=lambda h: -h.score)
    return hits[:cap]


def search_files(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    q = (query or "").strip().lower()
    if not q:
        return []
    hits: list[SearchHit] = []
    try:
        from app.api.v1.files import UPLOAD_DIR
        root = Path(UPLOAD_DIR)
    except Exception:
        root = Path.home() / "empire-repo" / "backend" / "data" / "uploads"
    if not root.exists():
        return []
    # Family editions never walk Workroom/amp/maxine sibling trees.
    blocked_parts = {"amp", "maxine"} if not is_family_edition(edition) else {"workroom", "amp", "maxine"}
    # Own edition may read its own upload root; just skip sibling edition folders.
    if process_edition() == "max_e":
        blocked_parts = {"workroom", "maxine"}
    elif process_edition() == "maxine":
        blocked_parts = {"workroom", "amp"}
    elif process_edition() == "main":
        blocked_parts = {"amp", "maxine"}
    else:
        return []
    scanned = 0
    for path in root.rglob("*"):
        scanned += 1
        if scanned > 800:
            break
        if not path.is_file():
            continue
        parts = {p.lower() for p in path.parts}
        if parts & blocked_parts:
            continue
        name = path.name
        if q not in name.lower():
            continue
        if not _keep_text(edition, name):
            continue
        rel = str(path)
        href = f"/?screen=docs&file={name}"
        hits.append(SearchHit(
            id=f"file:{name}",
            type="file",
            title=name,
            subtitle=path.parent.name,
            href=href,
            action=_open(href, "Open file"),
            score=_score(query, name),
            extra={"path": rel},
        ))
        if len(hits) >= cap:
            break
    return hits[:cap]


def search_organizer(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    """Appointments, to-dos, follow-ups — only if Organizer (PR #111) tables exist."""
    pattern = _like(query)
    hits: list[SearchHit] = []
    with _db() as conn:
        if _table_exists(conn, "organizer_items"):
            cols = _cols(conn, "organizer_items")
            ed_clause = ""
            params: list[Any] = [pattern, pattern]
            if "edition" in cols:
                from app.services.search.edition import edition_meta as _em
                keys = ("main", "workroom") if edition == "main" else (edition,)
                placeholders = ",".join("?" * len(keys))
                ed_clause = f" AND COALESCE(edition, 'workroom') IN ({placeholders})"
                params.extend(keys)
            kind = "kind" if "kind" in cols else "'' AS kind"
            due = "due_at" if "due_at" in cols else "'' AS due_at"
            notes = "notes" if "notes" in cols else "''"
            status = "status" if "status" in cols else "'' AS status"
            rows = conn.execute(
                f"""
                SELECT id, title, {kind}, {due}, {status}
                FROM organizer_items
                WHERE (title LIKE ? OR {notes} LIKE ?) {ed_clause}
                ORDER BY id DESC LIMIT ?
                """,
                (*params, cap * 2),
            ).fetchall()
            for r in rows:
                d = dict(r)
                title = d.get("title") or "Item"
                if not _keep_text(edition, title):
                    continue
                oid = str(d.get("id") or "")
                href = f"/?screen=calendar&item={oid}"
                kindv = (d.get("kind") or "todo").replace("_", " ")
                hits.append(SearchHit(
                    id=f"organizer:{oid}",
                    type="organizer",
                    title=title,
                    subtitle=" · ".join(x for x in (kindv, d.get("due_at"), d.get("status")) if x),
                    href=href,
                    action=_open(href, "Open"),
                    score=_score(query, title, kindv),
                ))
        if _table_exists(conn, "schedule_events") and len(hits) < cap:
            cols = _cols(conn, "schedule_events")
            title_c = "title" if "title" in cols else "''"
            type_c = "type" if "type" in cols else "''"
            start_c = "start_time" if "start_time" in cols else "''"
            rows = conn.execute(
                f"""
                SELECT id, {title_c} AS title, {type_c} AS type, {start_c} AS start_time
                FROM schedule_events
                WHERE {title_c} LIKE ?
                ORDER BY id DESC LIMIT ?
                """,
                (pattern, cap),
            ).fetchall()
            for r in rows:
                d = dict(r)
                title = d.get("title") or "Appointment"
                if not _keep_text(edition, title):
                    continue
                sid = str(d.get("id") or "")
                href = f"/?screen=calendar&event={sid}"
                hits.append(SearchHit(
                    id=f"organizer:event:{sid}",
                    type="organizer",
                    title=title,
                    subtitle=" · ".join(x for x in (d.get("type"), d.get("start_time")) if x),
                    href=href,
                    action=_open(href, "Open"),
                    score=_score(query, title),
                ))
        if _table_exists(conn, "tasks") and len(hits) < cap:
            cols = _cols(conn, "tasks")
            title_c = "title" if "title" in cols else "name" if "name" in cols else "''"
            rows = conn.execute(
                f"""
                SELECT id, {title_c} AS title
                FROM tasks
                WHERE {title_c} LIKE ?
                ORDER BY id DESC LIMIT ?
                """,
                (pattern, cap),
            ).fetchall()
            for r in rows:
                d = dict(r)
                title = d.get("title") or "To-do"
                if not _keep_text(edition, title):
                    continue
                tid = str(d.get("id") or "")
                href = f"/?screen=tasks&task={tid}"
                hits.append(SearchHit(
                    id=f"organizer:task:{tid}",
                    type="organizer",
                    title=title,
                    subtitle="To-do",
                    href=href,
                    action=_open(href, "Open"),
                    score=_score(query, title),
                ))
    hits.sort(key=lambda h: -h.score)
    return hits[:cap]


def search_pending_mail(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    """Read-only pending owner email. Reuses PR #111 organizer.mail when present.

    Never sends. Draft reply is an action that enqueues to the approval queue.
    """
    try:
        from app.services.organizer.mail import list_pending  # type: ignore
    except Exception:
        return []
    q = (query or "").strip().lower()
    hits: list[SearchHit] = []
    with _db() as conn:
        try:
            payload = list_pending(conn, limit=40)
        except Exception as exc:
            logger.info("pending-mail source skipped: %s", exc)
            return []
    items = (payload or {}).get("items") or []
    for item in items:
        title = item.get("subject") or item.get("from_name") or "Message"
        who = item.get("from_name") or item.get("from_email") or ""
        snippet = item.get("snippet") or item.get("suggested_reply") or ""
        blob = f"{title} {who} {snippet}"
        if q and q not in blob.lower():
            continue
        if not _keep_text(edition, blob):
            continue
        mid = str(item.get("message_id") or item.get("id") or "")
        src = item.get("source") or "gmail"
        href = item.get("open_href") or "/?screen=inbox"
        hits.append(SearchHit(
            id=f"mail:{src}:{mid}",
            type="mail",
            title=title,
            subtitle=who or "Pending email",
            href=href,
            action=_draft_reply(href=href, mail_id=mid, source=src),
            score=_score(query, title, who, snippet),
            extra={"read_only": True, "sent": False},
        ))
        if len(hits) >= cap:
            break
    return hits[:cap]


def search_memory(query: str, *, edition: str, cap: int = PER_SOURCE_CAP) -> list[SearchHit]:
    """Cheap LIKE over Max chat memory. No embeddings."""
    hits: list[SearchHit] = []
    try:
        from app.services.max.brain.memory_store import MemoryStore
        store = MemoryStore()
        rows = store.search_memories(query=query, limit=cap)
    except Exception as exc:
        logger.info("memory source skipped: %s", exc)
        return []
    for r in rows or []:
        subject = r.get("subject") or ""
        content = (r.get("content") or "")[:160]
        if not _keep_text(edition, subject, content):
            continue
        mid = str(r.get("id") or "")
        href = f"/?screen=memory-bank&q={query}"
        hits.append(SearchHit(
            id=f"memory:{mid}",
            type="memory",
            title=subject or content[:80] or "Memory",
            subtitle=content,
            href=href,
            action=_open(href, "Open"),
            score=_score(query, subject, content),
        ))
    return hits[:cap]


_SOURCES: list[tuple[str, Callable[..., list[SearchHit]]]] = [
    ("screen", search_screens),
    ("job", search_jobs),
    ("quote", search_quotes),
    ("invoice", search_invoices),
    ("person", search_people),
    ("file", search_files),
    ("organizer", search_organizer),
    ("mail", search_pending_mail),
    ("memory", search_memory),
]


def _run_source(name: str, fn: Callable, query: str, edition: str, family: bool, cap: int) -> list[SearchHit]:
    kwargs: dict[str, Any] = {"query": query, "cap": cap}
    if name == "screen":
        kwargs["family"] = family
    else:
        kwargs["edition"] = edition
    return fn(**kwargs)


def empty_blocked(query: str, edition: str) -> dict:
    return {
        "query": query,
        "edition": edition,
        "blocked": True,
        "ok": False,
        "error": "unknown_edition",
        "groups": [],
        "results": [],
        "top": None,
        "timed_out": [],
        "ms": 0,
        "note": "Unknown EMPIRE_EDITION — search is fail-closed and returns no owner data.",
    }


def rank_hits(hits: list[SearchHit]) -> list[SearchHit]:
    type_boost = {t: (len(GROUP_ORDER) - i) * 0.01 for i, t in enumerate(GROUP_ORDER)}
    return sorted(hits, key=lambda h: (-(h.score + type_boost.get(h.type, 0)), h.title.lower()))


def group_hits(hits: list[SearchHit]) -> list[dict]:
    buckets: dict[str, list[dict]] = {t: [] for t in GROUP_ORDER}
    for h in hits:
        buckets.setdefault(h.type, []).append(h.to_dict())
    groups = []
    for t in GROUP_ORDER:
        items = buckets.get(t) or []
        if items:
            groups.append({"type": t, "label": GROUP_LABELS.get(t, t.title()), "items": items})
    return groups


def run_universal_search(
    query: str,
    *,
    edition: Optional[str] = None,
    sources: Optional[list[tuple[str, Callable]]] = None,
    source_timeout: float = SOURCE_TIMEOUT_S,
    overall_timeout: float = OVERALL_TIMEOUT_S,
    per_source_cap: int = PER_SOURCE_CAP,
    total_cap: int = TOTAL_CAP,
) -> dict:
    started = time.monotonic()
    q = (query or "").strip()
    ed = edition or process_edition()
    if ed == "unknown":
        return empty_blocked(q, ed)
    family = is_family_edition(ed)
    if len(q) < MIN_QUERY_LEN:
        screens = search_screens("", family=family, cap=per_source_cap)
        ranked = rank_hits(screens)[:total_cap]
        return {
            "query": q,
            "edition": ed,
            "blocked": False,
            "ok": True,
            "groups": group_hits(ranked),
            "results": [h.to_dict() for h in ranked],
            "top": ranked[0].to_dict() if ranked else None,
            "timed_out": [],
            "ms": int((time.monotonic() - started) * 1000),
            "meta": edition_meta(ed),
        }

    pack = sources if sources is not None else _SOURCES
    collected: list[SearchHit] = []
    timed_out: list[str] = []
    deadline = time.monotonic() + overall_timeout

    def _one(name: str, fn: Callable) -> tuple[str, list[SearchHit]]:
        return name, _run_source(name, fn, q, ed, family, per_source_cap)

    workers = min(8, max(1, len(pack)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_one, name, fn): name for name, fn in pack}
        pending = set(futs)
        while pending:
            remain = deadline - time.monotonic()
            if remain <= 0:
                for fut in pending:
                    timed_out.append(futs[fut])
                    fut.cancel()
                break
            try:
                done = next(iter(as_completed(pending, timeout=min(source_timeout, remain))))
            except FuturesTimeout:
                for fut in pending:
                    timed_out.append(futs[fut])
                    fut.cancel()
                break
            pending.discard(done)
            name = futs[done]
            try:
                _n, items = done.result(timeout=0.05)
                collected.extend(items[:per_source_cap])
            except Exception as exc:
                logger.info("search source %s failed: %s", name, exc)
                timed_out.append(name)

    kept: list[SearchHit] = []
    for h in collected:
        if not _keep_text(ed, h.title, h.subtitle, h.href):
            continue
        kept.append(h)
    ranked = rank_hits(kept)[:total_cap]
    return {
        "query": q,
        "edition": ed,
        "blocked": False,
        "ok": True,
        "groups": group_hits(ranked),
        "results": [h.to_dict() for h in ranked],
        "top": ranked[0].to_dict() if ranked else None,
        "timed_out": timed_out,
        "ms": int((time.monotonic() - started) * 1000),
        "meta": edition_meta(ed),
        "outbound_policy": "Draft only. Nothing is sent without the owner's tap.",
    }


def enqueue_draft_reply(
    *,
    mail_id: str,
    source: str = "gmail",
    body: str = "",
    subject: str = "",
    to_address: str = "",
    to_name: str = "",
) -> dict:
    """Queue a draft reply. Never sends, even if confirm=true is passed."""
    ed = process_edition()
    if ed == "unknown":
        return {"ok": False, "sent": False, "error": "unknown_edition"}
    if contains_blocked_term(f"{subject} {body} {to_address} {to_name}", ed):
        return {"ok": False, "sent": False, "error": "edition_blocked"}

    # Prefer Organizer pending-mail action (PR #111) when present.
    try:
        from app.services.organizer.mail import run_mail_action  # type: ignore
        with _db() as conn:
            result = run_mail_action(
                conn,
                action="draft_reply",
                source=source or "gmail",
                message_id=mail_id,
                extra={"body": body, "confirm": True},
            )
        result = dict(result or {})
        result["sent"] = False
        result["requires_confirm"] = True
        return result
    except Exception:
        pass

    from app.services.leadforge.growth import enqueue
    approval = enqueue(
        channel="email",
        body=body or f"(Draft reply for {mail_id})",
        source="universal_search",
        source_ref=f"mail-reply-{source}-{mail_id}",
        kind="email",
        title=subject or f"Reply — {mail_id}",
        to_name=to_name,
        to_address=to_address,
        subject=subject,
        created_by="search",
    )
    return {
        "ok": True,
        "sent": False,
        "requires_confirm": True,
        "approval": approval,
        "outbound_policy": "Draft only. Nothing is sent without the owner's tap.",
        "href": "/?product=lead&section=approvals",
    }
