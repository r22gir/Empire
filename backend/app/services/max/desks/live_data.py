"""Read-only queries against the live Empire DB for desk jobs and the daily brief.

Every finding is named (invoice number, quote number, customer, task title).
Family-help tickets stay in their own bucket — never mixed into Workroom.
No function here sends anything to a client.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from app.db.max_ops_schema import ensure_max_ops_schema
from app.services.data_paths import inbox_dir
from app.services.max.brief_filters import (
    filter_followup_quotes,
    filter_real_money,
    is_promotional_mail,
    is_test_family_ticket,
    mail_account_label,
)
from app.services.max.desks.live_services import stuck_task_days

logger = logging.getLogger("max.desks.live_data")

UNPAID_INVOICE_STATUSES = ("draft", "sent", "partial", "overdue")
OPEN_QUOTE_STATUSES = ("draft", "sent", "proposal", "founder_review")
OPEN_TASK_STATUSES = ("todo", "in_progress", "waiting")
REVIEWED_INBOX = frozenset({"reviewed", "done"})


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _row_dict(row: sqlite3.Row | tuple | None) -> dict:
    if row is None:
        return {}
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return {}


def _connect():
    from app.db.database import get_db

    return get_db()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", ""))
    except ValueError:
        return None


def _days_old(value: str | None, now: datetime) -> int | None:
    dt = _parse_dt(value)
    if not dt:
        return None
    return max(0, (now.date() - dt.date()).days)


def _money(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _customer_name(row: dict) -> str:
    for key in ("customer_name", "customer", "name", "client_name", "from_name", "requester"):
        val = row.get(key)
        if val:
            return str(val)
    return "Unknown"


# ── Invoices / money ──────────────────────────────────────────────


def query_unpaid_invoices(conn: sqlite3.Connection, now: datetime | None = None) -> list[dict]:
    if not _table_exists(conn, "invoices"):
        return []
    cols = _cols(conn, "invoices")
    now = _now(now)
    has_customer = _table_exists(conn, "customers")
    join = "LEFT JOIN customers c ON c.id = invoices.customer_id" if has_customer else ""
    name_expr = "c.name" if has_customer else "NULL"
    due_expr = "invoices.due_date" if "due_date" in cols else "NULL"
    number_expr = "invoices.invoice_number" if "invoice_number" in cols else "invoices.id"
    sql = f"""
        SELECT invoices.id, {number_expr} AS invoice_number, invoices.status,
               invoices.total, invoices.amount_paid, invoices.balance_due,
               {due_expr} AS due_date, invoices.created_at,
               {name_expr} AS customer_name
        FROM invoices {join}
        WHERE invoices.status IN ({",".join("?" * len(UNPAID_INVOICE_STATUSES))})
        ORDER BY invoices.created_at ASC
    """
    rows = conn.execute(sql, UNPAID_INVOICE_STATUSES).fetchall()
    findings = []
    for raw in rows:
        row = _row_dict(raw)
        due = row.get("due_date") or row.get("created_at")
        age = _days_old(due, now)
        balance = _money(row.get("balance_due") or ( _money(row.get("total")) - _money(row.get("amount_paid")) ))
        findings.append({
            "kind": "invoice",
            "id": row.get("id"),
            "name": row.get("invoice_number") or row.get("id"),
            "customer": _customer_name(row),
            "amount": balance,
            "total": _money(row.get("total")),
            "status": row.get("status"),
            "age_days": age,
            "due_date": due,
            "overdue": bool(age is not None and age > 0 and row.get("status") in ("sent", "partial", "overdue")),
        })
    return filter_real_money(findings)


def query_payments_since(conn: sqlite3.Connection, since: datetime, now: datetime | None = None) -> list[dict]:
    now = _now(now)
    findings: list[dict] = []
    since_s = since.strftime("%Y-%m-%d")
    if _table_exists(conn, "payments"):
        has_customer = _table_exists(conn, "customers")
        join = "LEFT JOIN customers c ON c.id = payments.customer_id" if has_customer else ""
        name_expr = "c.name" if has_customer else "NULL"
        cols = _cols(conn, "payments")
        date_col = "payment_date" if "payment_date" in cols else "created_at"
        method_col = "method" if "method" in cols else "NULL"
        sql = f"""
            SELECT payments.id, payments.amount, {method_col} AS method,
                   payments.{date_col} AS payment_date, payments.invoice_id,
                   {name_expr} AS customer_name, payments.reference, payments.notes
            FROM payments {join}
            WHERE payments.{date_col} >= ?
            ORDER BY payments.{date_col} DESC
        """
        for raw in conn.execute(sql, (since_s,)).fetchall():
            row = _row_dict(raw)
            method = (row.get("method") or "").lower()
            blob = f"{row.get('reference') or ''} {row.get('notes') or ''} {method}"
            processor = None
            if "stripe" in blob:
                processor = "Stripe"
            elif "square" in blob:
                processor = "Square"
            elif method in ("card",):
                processor = "card"
            findings.append({
                "kind": "payment",
                "id": row.get("id"),
                "name": row.get("id"),
                "customer": _customer_name(row),
                "amount": _money(row.get("amount")),
                "method": method or "unknown",
                "processor": processor,
                "date": row.get("payment_date"),
            })
    if _table_exists(conn, "payments_v2"):
        cols = _cols(conn, "payments_v2")
        date_col = "payment_date" if "payment_date" in cols else "created_at"
        method_col = "payment_method" if "payment_method" in cols else "NULL"
        sql = f"""
            SELECT id, amount, {method_col} AS method, {date_col} AS payment_date,
                   notes, payment_reference
            FROM payments_v2
            WHERE {date_col} >= ?
            ORDER BY {date_col} DESC
        """
        seen = {f["id"] for f in findings}
        for raw in conn.execute(sql, (since_s,)).fetchall():
            row = _row_dict(raw)
            if row.get("id") in seen:
                continue
            method = (row.get("method") or "").lower()
            blob = f"{row.get('payment_reference') or ''} {row.get('notes') or ''} {method}"
            processor = "Stripe" if "stripe" in blob else ("Square" if "square" in blob else None)
            findings.append({
                "kind": "payment",
                "id": row.get("id"),
                "name": str(row.get("id")),
                "customer": "Unknown",
                "amount": _money(row.get("amount")),
                "method": method or "unknown",
                "processor": processor,
                "date": row.get("payment_date"),
            })
    return filter_real_money(findings)


# ── Quotes ────────────────────────────────────────────────────────


def query_stale_quotes(conn: sqlite3.Connection, min_age_days: int = 0, now: datetime | None = None) -> list[dict]:
    """Quotes awaiting a reply, sent or updated within ~60 days. No $0/test/Customer."""
    if not _table_exists(conn, "quotes_v2"):
        return []
    now = _now(now)
    cols = _cols(conn, "quotes_v2")
    sent_col = "sent_at" if "sent_at" in cols else "created_at"
    upd_col = "updated_at" if "updated_at" in cols else sent_col
    sql = f"""
        SELECT id, quote_number, customer_name, status, total,
               {sent_col} AS sent_at, {upd_col} AS updated_at, created_at
        FROM quotes_v2
        WHERE status IN ({",".join("?" * len(OPEN_QUOTE_STATUSES))})
        ORDER BY COALESCE({upd_col}, {sent_col}, created_at) DESC
    """
    findings = []
    for raw in conn.execute(sql, OPEN_QUOTE_STATUSES).fetchall():
        row = _row_dict(raw)
        sent_age = _days_old(row.get("sent_at") or row.get("created_at"), now)
        window_age = _days_old(row.get("updated_at") or row.get("sent_at") or row.get("created_at"), now)
        findings.append({
            "kind": "quote",
            "id": row.get("id"),
            "name": row.get("quote_number") or row.get("id"),
            "customer": _customer_name(row),
            "amount": _money(row.get("total")),
            "status": row.get("status"),
            "age_days": sent_age,
            "window_age_days": window_age,
            "sent_at": row.get("sent_at") or row.get("created_at"),
        })
    filtered = []
    for item in findings:
        window = item.get("window_age_days")
        if window is not None and int(window) > 60:
            continue
        if min_age_days and (item.get("age_days") or 0) < min_age_days:
            continue
        filtered.append(item)
    return filter_followup_quotes(filtered, max_age_days=60)


def query_open_quotes(conn: sqlite3.Connection) -> list[dict]:
    if not _table_exists(conn, "quotes_v2"):
        return []
    rows = conn.execute(
        f"""
        SELECT id, quote_number, customer_name, status, total, created_at
        FROM quotes_v2
        WHERE status IN ({",".join("?" * len(OPEN_QUOTE_STATUSES))})
        ORDER BY created_at DESC
        """,
        OPEN_QUOTE_STATUSES,
    ).fetchall()
    return [{
        "kind": "quote",
        "id": r["id"] if isinstance(r, sqlite3.Row) else r[0],
        "name": (r["quote_number"] if isinstance(r, sqlite3.Row) else r[1]) or (r["id"] if isinstance(r, sqlite3.Row) else r[0]),
        "customer": _customer_name(_row_dict(r)),
        "amount": _money(r["total"] if isinstance(r, sqlite3.Row) else r[4]),
        "status": r["status"] if isinstance(r, sqlite3.Row) else r[3],
    } for r in rows]


# ── Jobs / schedule / organizer ───────────────────────────────────


def query_jobs(conn: sqlite3.Connection, statuses: Iterable[str] | None = None) -> list[dict]:
    if not _table_exists(conn, "jobs"):
        return []
    cols = _cols(conn, "jobs")
    title_col = "title" if "title" in cols else "id"
    status_filter = list(statuses) if statuses else None
    where = ""
    params: list[Any] = []
    if status_filter:
        where = f"WHERE status IN ({','.join('?' * len(status_filter))})"
        params = status_filter
    name_expr = "NULL"
    join = ""
    if _table_exists(conn, "customers") and "customer_id" in cols:
        join = "LEFT JOIN customers c ON c.id = jobs.customer_id"
        name_expr = "c.name"
    sql = f"""
        SELECT jobs.id, jobs.{title_col} AS title, jobs.status,
               {name_expr} AS customer_name,
               {('jobs.scheduled_date' if 'scheduled_date' in cols else 'NULL')} AS scheduled_date,
               {('jobs.due_date' if 'due_date' in cols else 'NULL')} AS due_date
        FROM jobs {join}
        {where}
        ORDER BY jobs.created_at DESC
    """
    findings = []
    for raw in conn.execute(sql, params).fetchall():
        row = _row_dict(raw)
        findings.append({
            "kind": "job",
            "id": row.get("id"),
            "name": row.get("title") or row.get("id"),
            "customer": _customer_name(row),
            "status": row.get("status"),
            "scheduled_date": row.get("scheduled_date"),
            "due_date": row.get("due_date"),
        })
    return findings


def query_schedule(conn: sqlite3.Connection, start: datetime, end: datetime) -> list[dict]:
    """Today / this week from schedule_events (Organizer calendar) plus
    organizer_items that have a start/due in the window and are not already
    mirrored onto a schedule_event row.
    """
    findings: list[dict] = []
    seen: set[str] = set()
    start_s = start.strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")
    if _table_exists(conn, "schedule_events"):
        cols = _cols(conn, "schedule_events")
        extra = ""
        if "space_id" in cols:
            extra += ", space_id"
        if "event_kind" in cols:
            extra += ", event_kind"
        rows = conn.execute(
            f"""
            SELECT id, type, title, customer_vendor, location_address,
                   start_time, end_time, status{extra}
            FROM schedule_events
            WHERE status != 'cancelled'
              AND start_time >= ? AND start_time < ?
            ORDER BY start_time ASC
            """,
            (start_s, end_s),
        ).fetchall()
        for raw in rows:
            row = _row_dict(raw)
            eid = str(row.get("id") or "")
            seen.add(eid)
            findings.append({
                "kind": "schedule",
                "id": row.get("id"),
                "name": row.get("title") or row.get("id"),
                "customer": row.get("customer_vendor") or "Unknown",
                "type": row.get("event_kind") or row.get("type"),
                "start_time": row.get("start_time"),
                "status": row.get("status"),
                "location": row.get("location_address"),
                "space_id": row.get("space_id"),
                "source": "schedule_events",
            })
    if _table_exists(conn, "organizer_items"):
        cols = _cols(conn, "organizer_items")
        time_col = "start_time" if "start_time" in cols else ("due_at" if "due_at" in cols else None)
        if time_col:
            space_sel = "space_id" if "space_id" in cols else "NULL AS space_id"
            due_sel = "due_at" if "due_at" in cols else "NULL AS due_at"
            ev_sel = "schedule_event_id" if "schedule_event_id" in cols else "NULL AS schedule_event_id"
            rows = conn.execute(
                f"""
                SELECT id, title, kind, status, {time_col} AS start_time,
                       {due_sel}, {space_sel}, {ev_sel}
                FROM organizer_items
                WHERE status NOT IN ('done','cancelled')
                  AND COALESCE({time_col}, due_at) >= ?
                  AND COALESCE({time_col}, due_at) < ?
                """,
                (start_s, end_s),
            ).fetchall() if "due_at" in cols else conn.execute(
                f"""
                SELECT id, title, kind, status, {time_col} AS start_time,
                       NULL AS due_at, {space_sel}, {ev_sel}
                FROM organizer_items
                WHERE status NOT IN ('done','cancelled')
                  AND {time_col} >= ? AND {time_col} < ?
                """,
                (start_s, end_s),
            ).fetchall()
            for raw in rows:
                row = _row_dict(raw)
                linked = str(row.get("schedule_event_id") or "")
                oid = str(row.get("id") or "")
                if linked and linked in seen:
                    continue
                if oid in seen:
                    continue
                seen.add(oid)
                findings.append({
                    "kind": "schedule",
                    "id": row.get("id"),
                    "name": row.get("title") or row.get("id"),
                    "customer": "Organizer",
                    "type": row.get("kind"),
                    "start_time": row.get("start_time") or row.get("due_at"),
                    "status": row.get("status"),
                    "space_id": row.get("space_id"),
                    "source": "organizer_items",
                })
    findings.sort(key=lambda f: str(f.get("start_time") or ""))
    return findings


def query_overdue_schedule(conn: sqlite3.Connection, now: datetime | None = None) -> list[dict]:
    if not _table_exists(conn, "schedule_events"):
        return []
    now = _now(now)
    rows = conn.execute(
        """
        SELECT id, type, title, customer_vendor, start_time, status
        FROM schedule_events
        WHERE status IN ('planned', 'confirmed')
          AND start_time < ?
        ORDER BY start_time ASC
        """,
        (now.strftime("%Y-%m-%d %H:%M:%S"),),
    ).fetchall()
    return [{
        "kind": "schedule_overdue",
        "id": r["id"] if isinstance(r, sqlite3.Row) else r[0],
        "name": (r["title"] if isinstance(r, sqlite3.Row) else r[2]) or "",
        "customer": (r["customer_vendor"] if isinstance(r, sqlite3.Row) else r[3]) or "Unknown",
        "type": r["type"] if isinstance(r, sqlite3.Row) else r[1],
        "start_time": r["start_time"] if isinstance(r, sqlite3.Row) else r[4],
        "status": r["status"] if isinstance(r, sqlite3.Row) else r[5],
        "age_days": _days_old(r["start_time"] if isinstance(r, sqlite3.Row) else r[4], now),
    } for r in rows]


# ── Tasks / stuck / approvals ─────────────────────────────────────


def query_open_tasks(conn: sqlite3.Connection, desk: str | None = None) -> list[dict]:
    if not _table_exists(conn, "tasks"):
        return []
    cols = _cols(conn, "tasks")
    desk_col = "desk" if "desk" in cols else None
    if desk and not desk_col:
        return []
    sql = f"""
        SELECT id, title, status, {desk_col or "NULL"} AS desk, due_date, created_at
        FROM tasks
        WHERE status IN ({",".join("?" * len(OPEN_TASK_STATUSES))})
    """
    params: list[Any] = list(OPEN_TASK_STATUSES)
    if desk and desk_col:
        sql += " AND desk = ?"
        params.append(desk)
    sql += " ORDER BY created_at ASC"
    findings = []
    for raw in conn.execute(sql, params).fetchall():
        row = _row_dict(raw)
        findings.append({
            "kind": "task",
            "id": row.get("id"),
            "name": row.get("title") or row.get("id"),
            "status": row.get("status"),
            "desk": row.get("desk"),
            "due_date": row.get("due_date"),
            "created_at": row.get("created_at"),
        })
    return findings


def query_stuck_tasks(conn: sqlite3.Connection, older_than_days: int | None = None, now: datetime | None = None) -> list[dict]:
    if not _table_exists(conn, "tasks"):
        return []
    now = _now(now)
    days = older_than_days if older_than_days is not None else stuck_task_days()
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    cols = _cols(conn, "tasks")
    desk_col = "desk" if "desk" in cols else "NULL"
    rows = conn.execute(
        f"""
        SELECT id, title, status, {desk_col} AS desk, due_date, created_at, created_by
        FROM tasks
        WHERE status IN ({",".join("?" * len(OPEN_TASK_STATUSES))})
          AND created_at <= ?
        ORDER BY created_at ASC
        """,
        (*OPEN_TASK_STATUSES, cutoff),
    ).fetchall()
    findings = []
    for raw in rows:
        row = _row_dict(raw)
        findings.append({
            "kind": "stuck_task",
            "id": row.get("id"),
            "name": row.get("title") or row.get("id"),
            "status": row.get("status"),
            "desk": row.get("desk"),
            "age_days": _days_old(row.get("created_at"), now),
            "created_at": row.get("created_at"),
            "created_by": row.get("created_by"),
        })
    return findings


def query_overdue_tasks(conn: sqlite3.Connection, now: datetime | None = None) -> list[dict]:
    """Overdue open tasks. Column is ``desk``, never ``desk_id``."""
    if not _table_exists(conn, "tasks"):
        return []
    now = _now(now)
    today = now.strftime("%Y-%m-%d")
    cols = _cols(conn, "tasks")
    desk_col = "desk" if "desk" in cols else "NULL"
    rows = conn.execute(
        f"""
        SELECT title, due_date, {desk_col} AS desk, id
        FROM tasks
        WHERE status IN ('todo', 'in_progress')
          AND due_date IS NOT NULL AND due_date < ?
        ORDER BY due_date LIMIT 20
        """,
        (today,),
    ).fetchall()
    return [{
        "kind": "overdue_task",
        "id": r["id"] if isinstance(r, sqlite3.Row) else r[3],
        "name": r["title"] if isinstance(r, sqlite3.Row) else r[0],
        "due_date": r["due_date"] if isinstance(r, sqlite3.Row) else r[1],
        "desk": r["desk"] if isinstance(r, sqlite3.Row) else r[2],
    } for r in rows]


# ── Mail / inbox / family ─────────────────────────────────────────


def count_unreviewed_inbox(inbox_path: Path | None = None) -> int:
    return len(list_unreviewed_inbox(inbox_path))


def list_unreviewed_inbox(inbox_path: Path | None = None) -> list[dict]:
    """Count/list only unreviewed inbox JSON from the live data path."""
    root = Path(inbox_path) if inbox_path else inbox_dir()
    if not root.exists():
        return []
    items = []
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        status = str(data.get("status") or "received").lower()
        if status in REVIEWED_INBOX:
            continue
        items.append({
            "kind": "inbox",
            "id": data.get("id") or path.stem,
            "name": data.get("ai_summary") or (data.get("text") or "")[:80] or path.stem,
            "status": status,
            "source": data.get("source"),
            "channel": data.get("source") or "inbox",
        })
    return items


def query_pending_mail(conn: sqlite3.Connection) -> list[dict]:
    """Unanswered mail from Organizer (Gmail + Outlook, read-only).

    Draft replies stay on the approval queue. Nothing is sent.
    The pending_mail table is a fallback only.
    """
    findings: list[dict] = []
    seen: set[str] = set()

    def _add(item: dict) -> None:
        key = str(item.get("id") or item.get("name") or "")
        if not key or key in seen:
            return
        seen.add(key)
        findings.append(item)

    try:
        from app.services.organizer.mail import list_pending

        payload = list_pending(conn, limit=40)
        items = payload.get("items") if isinstance(payload, dict) else payload
        for item in items or []:
            if not isinstance(item, dict):
                continue
            if is_promotional_mail(item):
                continue
            source = item.get("source") or item.get("channel") or "email"
            _add({
                "kind": "mail",
                "id": item.get("id"),
                "name": item.get("subject") or item.get("id"),
                "customer": item.get("from_name") or item.get("from") or "Unknown",
                "channel": source,
                "account_label": mail_account_label(source),
                "status": item.get("waiting") or item.get("status") or "pending",
                "source": source,
                "preview": item.get("preview"),
                "read_only": True,
                "sent": False,
            })
    except Exception as exc:
        logger.info("organizer mail skipped: %s", exc)

    if _table_exists(conn, "pending_mail"):
        rows = conn.execute(
            """
            SELECT id, from_addr, from_name, subject, channel, status, created_at
            FROM pending_mail
            WHERE status IN ('pending', 'drafted', 'unanswered')
            ORDER BY created_at ASC
            """
        ).fetchall()
        for raw in rows:
            row = _row_dict(raw)
            channel = row.get("channel") or "email"
            fallback = {
                "kind": "mail",
                "id": row.get("id"),
                "name": row.get("subject") or row.get("id"),
                "customer": row.get("from_name") or row.get("from_addr") or "Unknown",
                "channel": channel,
                "account_label": mail_account_label(channel),
                "status": row.get("status"),
                "created_at": row.get("created_at"),
                "from": row.get("from_addr"),
            }
            if is_promotional_mail(fallback):
                continue
            _add(fallback)
    return findings


def query_family_help_tickets(conn: sqlite3.Connection) -> list[dict]:
    """Family-help only. Primary source is /data/family-help/<ed>/help.db."""
    findings: list[dict] = []
    seen: set[str] = set()
    try:
        from app.services.max.desks.family_help_store import list_open_tickets

        for item in list_open_tickets():
            key = str(item.get("id") or "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            findings.append(item)
    except Exception as exc:
        logger.info("family-help store skipped: %s", exc)

    if _table_exists(conn, "family_help_tickets"):
        rows = conn.execute(
            """
            SELECT id, requester, subject, status, created_at
            FROM family_help_tickets
            WHERE status NOT IN ('done', 'closed', 'resolved')
            ORDER BY created_at ASC
            """
        ).fetchall()
        for raw in rows:
            row = _row_dict(raw)
            key = str(row.get("id") or "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            findings.append({
                "kind": "family_ticket",
                "id": row.get("id"),
                "name": row.get("subject") or row.get("id"),
                "customer": row.get("requester") or "Family",
                "status": row.get("status"),
                "area": "family",
                "isolated": True,
            })
    if _table_exists(conn, "tasks"):
        cols = _cols(conn, "tasks")
        if "desk" in cols:
            rows = conn.execute(
                """
                SELECT id, title, status, desk
                FROM tasks
                WHERE status IN ('todo', 'in_progress', 'waiting')
                  AND desk IN ('family', 'family-help')
                """
            ).fetchall()
            for raw in rows:
                row = _row_dict(raw)
                key = str(row.get("id") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                findings.append({
                    "kind": "family_ticket",
                    "id": row.get("id"),
                    "name": row.get("title") or row.get("id"),
                    "customer": "Family",
                    "status": row.get("status"),
                    "area": "family",
                    "isolated": True,
                })
    return [f for f in findings if not is_test_family_ticket(f)]


def _space_bucket(space: str | None, blob: str = "") -> str | None:
    """Map an Organizer space onto Empire / family / personal / ventures.

    Workroom is Workroom — it does not belong in Other areas.
    """
    key = (space or "").strip().lower().replace(" ", "_")
    if ":" in key:
        key = key.split(":")[-1]
    if key == "family":
        return "family"
    if key == "personal":
        return "personal"
    if key in ("ventures", "venture"):
        return "ventures"
    if key == "empire":
        return "empire"
    if key in ("workroom", "work", "amp"):
        return None
    text = (blob or "").lower()
    if any(w in text for w in ("family", "amp", "maxine", "ayuda")):
        return "family"
    if any(w in text for w in ("personal", "dentist", "doctor", "school")):
        return "personal"
    if any(w in text for w in ("venture", "llc", "new biz", "side")):
        return "ventures"
    return None


def query_other_areas(conn: sqlite3.Connection, now: datetime | None = None) -> dict[str, list[dict]]:
    """Empire / family / personal / ventures from Organizer items + family-help."""
    now = _now(now)
    buckets: dict[str, list[dict]] = {"empire": [], "family": [], "personal": [], "ventures": []}
    buckets["family"].extend(query_family_help_tickets(conn))
    seen: set[str] = {str(i.get("id") or "") for i in buckets["family"]}

    def _put(area: str | None, item: dict) -> None:
        if not area or area not in buckets:
            return
        key = str(item.get("id") or "")
        if key and key in seen:
            return
        if key:
            seen.add(key)
        buckets[area].append(item)

    if _table_exists(conn, "organizer_items"):
        try:
            from app.services.organizer.schema import migrate_organizer_tables
            migrate_organizer_tables(conn)
        except Exception:
            pass
        cols = _cols(conn, "organizer_items")
        if "title" in cols:
            space_sel = "space_id" if "space_id" in cols else "NULL AS space_id"
            due_sel = "due_at" if "due_at" in cols else "NULL AS due_at"
            start_sel = "start_time" if "start_time" in cols else "NULL AS start_time"
            rows = conn.execute(
                f"""
                SELECT id, title, kind, status, {space_sel}, {due_sel}, {start_sel}, notes
                FROM organizer_items
                WHERE status NOT IN ('done','cancelled')
                LIMIT 80
                """
            ).fetchall()
            for raw in rows:
                row = _row_dict(raw)
                blob = f"{row.get('title') or ''} {row.get('notes') or ''} {row.get('kind') or ''}"
                area = _space_bucket(row.get("space_id"), blob)
                if area is None and str(row.get("space_id") or "") in ("", "None"):
                    area = _space_bucket(None, blob) or "empire"
                _put(area, {
                    "kind": "organizer",
                    "id": row.get("id"),
                    "name": row.get("title"),
                    "status": row.get("status"),
                    "start_time": row.get("start_time") or row.get("due_at"),
                    "area": area,
                    "space_id": row.get("space_id"),
                })

    if _table_exists(conn, "schedule_events"):
        cols = _cols(conn, "schedule_events")
        week_end = now + timedelta(days=7)
        space_sel = "space_id" if "space_id" in cols else "NULL AS space_id"
        notes_sel = "notes" if "notes" in cols else "NULL AS notes"
        rows = conn.execute(
            f"""
            SELECT id, type, title, {notes_sel}, start_time, status, {space_sel}
            FROM schedule_events
            WHERE status != 'cancelled'
              AND start_time >= ? AND start_time < ?
            """,
            (now.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchall()
        for raw in rows:
            row = _row_dict(raw)
            blob = f"{row.get('title') or ''} {row.get('notes') or ''} {row.get('type') or ''}"
            area = _space_bucket(row.get("space_id"), blob)
            _put(area, {
                "kind": "organizer",
                "id": row.get("id"),
                "name": row.get("title"),
                "start_time": row.get("start_time"),
                "area": area,
                "space_id": row.get("space_id"),
            })
    return buckets


def query_business_metrics(conn: sqlite3.Connection, now: datetime | None = None) -> dict[str, Any]:
    now = _now(now)
    metrics: dict[str, Any] = {
        "customers": 0,
        "jobs_pending": 0,
        "jobs_completed": 0,
        "invoices_unpaid": 0,
        "invoices_paid": 0,
        "revenue": 0.0,
        "expenses": 0.0,
        "open_tasks": 0,
        "inventory_items": 0,
    }
    if _table_exists(conn, "customers"):
        metrics["customers"] = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    if _table_exists(conn, "jobs"):
        metrics["jobs_pending"] = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN ('pending','scheduled','in_progress','on_hold')"
        ).fetchone()[0]
        metrics["jobs_completed"] = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'completed'"
        ).fetchone()[0]
    if _table_exists(conn, "invoices"):
        metrics["invoices_unpaid"] = conn.execute(
            f"SELECT COUNT(*) FROM invoices WHERE status IN ({','.join('?' * len(UNPAID_INVOICE_STATUSES))})",
            UNPAID_INVOICE_STATUSES,
        ).fetchone()[0]
        metrics["invoices_paid"] = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE status = 'paid'"
        ).fetchone()[0]
    if _table_exists(conn, "payments"):
        metrics["revenue"] = _money(conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments").fetchone()[0])
    if _table_exists(conn, "expenses"):
        metrics["expenses"] = _money(conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0])
    if _table_exists(conn, "tasks"):
        metrics["open_tasks"] = conn.execute(
            f"SELECT COUNT(*) FROM tasks WHERE status IN ({','.join('?' * len(OPEN_TASK_STATUSES))})",
            OPEN_TASK_STATUSES,
        ).fetchone()[0]
    if _table_exists(conn, "inventory_items"):
        metrics["inventory_items"] = conn.execute("SELECT COUNT(*) FROM inventory_items").fetchone()[0]
    metrics["as_of"] = now.isoformat()
    return metrics


def query_desk_job_results(conn: sqlite3.Connection, since: datetime | None = None) -> list[dict]:
    if not _table_exists(conn, "desk_job_results"):
        return []
    sql = "SELECT id, desk_id, job_title, status, result_text, fail_reason, retry_count, executed_at FROM desk_job_results"
    params: list[Any] = []
    if since:
        sql += " WHERE executed_at >= ?"
        params.append(since.isoformat())
    sql += " ORDER BY executed_at DESC"
    return [_row_dict(r) for r in conn.execute(sql, params).fetchall()]


def format_named_findings(title: str, findings: list[dict], empty_line: str) -> str:
    """Render specific, named findings. Never a canned one-liner."""
    lines = [title]
    if not findings:
        lines.append(empty_line)
        return "\n".join(lines)
    for f in findings:
        name = f.get("name") or f.get("id") or "item"
        customer = f.get("customer")
        amount = f.get("amount")
        age = f.get("age_days")
        status = f.get("status")
        extra = []
        if customer:
            extra.append(str(customer))
        if amount is not None and amount != "":
            extra.append(f"${_money(amount):,.2f}")
        if age is not None:
            extra.append(f"{age}d")
        if status:
            extra.append(str(status))
        suffix = f" — {', '.join(extra)}" if extra else ""
        lines.append(f"  - {name}{suffix}")
    return "\n".join(lines)


def snapshot(now: datetime | None = None) -> dict[str, Any]:
    """One DB snapshot used by desk jobs and the brief."""
    now = _now(now)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)
    yesterday = today_start - timedelta(days=1)
    with _connect() as conn:
        ensure_max_ops_schema(conn)
        unpaid = query_unpaid_invoices(conn, now)
        return {
            "now": now,
            "unpaid_invoices": unpaid,
            "overdue_invoices": [i for i in unpaid if i.get("overdue") or i.get("status") == "overdue"],
            "payments_since_yesterday": query_payments_since(conn, yesterday, now),
            "stale_quotes": query_stale_quotes(conn, 3, now),
            "open_quotes": query_open_quotes(conn),
            "jobs": query_jobs(conn),
            "jobs_active": query_jobs(conn, ("pending", "scheduled", "in_progress", "on_hold")),
            "schedule_today": query_schedule(conn, today_start, today_start + timedelta(days=1)),
            "schedule_week": query_schedule(conn, today_start, week_end),
            "schedule_next14": query_schedule(conn, week_end, today_start + timedelta(days=15)),
            "schedule_overdue": query_overdue_schedule(conn, now),
            "open_tasks": query_open_tasks(conn),
            "stuck_tasks": query_stuck_tasks(conn, None, now),
            "overdue_tasks": query_overdue_tasks(conn, now),
            "pending_mail": query_pending_mail(conn),
            "family_tickets": query_family_help_tickets(conn),
            "other_areas": query_other_areas(conn, now),
            "metrics": query_business_metrics(conn, now),
            "unreviewed_inbox": list_unreviewed_inbox(),
            "desk_results": query_desk_job_results(conn, yesterday),
        }
