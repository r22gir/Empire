"""
SQLite-backed SupportForge ticket store.

Lives in empire.db (EMPIRE_TASK_DB). Edition rows are isolated by tenant_id
and edition_id. Family-help tickets expose only the request itself to the
founder — never edition memory, conversations, or other private data.

Nothing in this store builds, deploys, or executes a proposed action.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db.database import get_connection
from app.db.supportforge_migration import ensure_supportforge_tables
from app.services.supportforge_proposed_action import propose_action

FOUNDER_TENANT_ID = "edition:founder"
FAMILY_HELP_SOURCE = "family_help"

FOUNDER_VISIBLE_KEYS = (
    "id",
    "ticket_number",
    "subject",
    "content",
    "status",
    "priority",
    "channel",
    "category",
    "source",
    "edition_id",
    "family_help_request_id",
    "proposed_action",
    "proposed_action_summary",
    "proposed_action_status",
    "auto_build",
    "created_at",
    "updated_at",
)

ALLOWED_STATUSES = frozenset(
    {"new", "open", "pending", "progress", "in_progress", "waiting", "resolved", "closed"}
)
ALLOWED_PRIORITIES = frozenset({"low", "normal", "medium", "high", "urgent"})
ALLOWED_CHANNELS = frozenset({"email", "chat", "phone", "sms", "portal", "family-help"})

STATUS_ALIASES = {
    "progress": "in_progress",
    "in-progress": "in_progress",
    "medium": "normal",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_status(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    mapped = STATUS_ALIASES.get(value, value)
    if mapped not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid ticket status: {value}")
    return mapped


def _normalize_priority(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    mapped = STATUS_ALIASES.get(value, value)
    if mapped not in ALLOWED_PRIORITIES:
        raise ValueError(f"Invalid ticket priority: {value}")
    return mapped


def _parse_json(value: Any, default):
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _row_to_ticket(row) -> dict:
    data = dict(row)
    data["tags"] = _parse_json(data.get("tags"), [])
    data["auto_build"] = bool(data.get("auto_build"))
    return data


def founder_visible_ticket(ticket: dict) -> dict:
    """Founder may see only the request itself — not edition internals."""
    visible = {key: ticket.get(key) for key in FOUNDER_VISIBLE_KEYS}
    visible["auto_build"] = False
    return visible


class SupportForgeTicketStore:
    def __init__(self, conn=None):
        self._external_conn = conn

    def _connect(self):
        if self._external_conn is not None:
            return self._external_conn
        return get_connection()

    def _release(self, conn) -> None:
        if self._external_conn is None:
            conn.close()

    def ensure(self) -> None:
        conn = self._connect()
        try:
            ensure_supportforge_tables(conn)
        finally:
            self._release(conn)

    def _next_ticket_number(self, conn, tenant_id: str) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(ticket_number), 0) AS n FROM sf_tickets WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        return int(row["n"] if row else 0) + 1

    def _ensure_customer(
        self,
        conn,
        tenant_id: str,
        email: Optional[str],
        name: Optional[str],
    ) -> Optional[str]:
        if not email:
            return None
        existing = conn.execute(
            "SELECT id FROM sf_customers WHERE tenant_id = ? AND email = ?",
            (tenant_id, email),
        ).fetchone()
        if existing:
            return existing["id"]
        customer_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO sf_customers (id, tenant_id, email, name, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (customer_id, tenant_id, email, name, _now()),
        )
        return customer_id

    def create_ticket(
        self,
        *,
        subject: str,
        content: str,
        tenant_id: str = FOUNDER_TENANT_ID,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        channel: str = "portal",
        priority: str = "normal",
        tags: Optional[list] = None,
        category: Optional[str] = None,
        source: str = "portal",
        edition_id: Optional[str] = None,
        family_help_request_id: Optional[str] = None,
        proposed: Optional[dict] = None,
        author_id: Optional[str] = None,
    ) -> dict:
        if not subject or not subject.strip():
            raise ValueError("subject is required")
        if not content or not content.strip():
            raise ValueError("content is required")
        if channel not in ALLOWED_CHANNELS:
            raise ValueError(f"Invalid channel: {channel}")
        priority = _normalize_priority(priority) or "normal"

        if proposed is None:
            proposed = propose_action(subject, content, edition_id)

        conn = self._connect()
        try:
            ensure_supportforge_tables(conn)
            ticket_id = str(uuid.uuid4())
            now = _now()
            customer_id = self._ensure_customer(conn, tenant_id, customer_email, customer_name)
            ticket_number = self._next_ticket_number(conn, tenant_id)
            conn.execute(
                """
                INSERT INTO sf_tickets (
                    id, tenant_id, ticket_number, customer_id, subject, content,
                    status, priority, channel, tags, category, source, edition_id,
                    family_help_request_id, proposed_action, proposed_action_summary,
                    proposed_action_status, auto_build, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', 0, ?, ?)
                """,
                (
                    ticket_id,
                    tenant_id,
                    ticket_number,
                    customer_id,
                    subject.strip(),
                    content.strip(),
                    priority,
                    channel,
                    json.dumps(tags or []),
                    category,
                    source,
                    edition_id,
                    family_help_request_id,
                    proposed["kind"],
                    proposed["summary"],
                    now,
                    now,
                ),
            )
            message_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO sf_messages (
                    id, ticket_id, sender_type, sender_id, content, is_internal_note, created_at
                ) VALUES (?, ?, 'customer', ?, ?, 0, ?)
                """,
                (message_id, ticket_id, author_id or customer_id or ticket_id, content.strip(), now),
            )
            conn.commit()
            return self.get_ticket(ticket_id, tenant_id=tenant_id, conn=conn)
        finally:
            self._release(conn)

    def get_ticket(
        self,
        ticket_id: str,
        *,
        tenant_id: Optional[str] = None,
        edition_id: Optional[str] = None,
        founder_view: bool = False,
        conn=None,
    ) -> Optional[dict]:
        owns = conn is None
        if owns:
            conn = self._connect()
        try:
            ensure_supportforge_tables(conn)
            query = "SELECT * FROM sf_tickets WHERE id = ?"
            params: list[Any] = [ticket_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            if edition_id:
                query += " AND edition_id = ?"
                params.append(edition_id)
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            ticket = _row_to_ticket(row)
            if founder_view and ticket.get("source") == FAMILY_HELP_SOURCE:
                return founder_visible_ticket(ticket)
            return ticket
        finally:
            if owns:
                self._release(conn)

    def list_tickets(
        self,
        *,
        tenant_id: Optional[str] = None,
        edition_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        source: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
        founder_view: bool = False,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[dict], int]:
        status = _normalize_status(status) if status else None
        priority = _normalize_priority(priority) if priority else None
        page = max(1, page)
        per_page = min(max(1, per_page), 100)

        conn = self._connect()
        try:
            ensure_supportforge_tables(conn)
            where = ["1=1"]
            params: list[Any] = []
            if tenant_id:
                where.append("tenant_id = ?")
                params.append(tenant_id)
            if edition_id:
                where.append("edition_id = ?")
                params.append(edition_id)
            if status:
                where.append("status = ?")
                params.append(status)
            if priority:
                where.append("priority = ?")
                params.append(priority)
            if source:
                where.append("source = ?")
                params.append(source)
            if assigned_agent_id:
                where.append("assigned_agent_id = ?")
                params.append(assigned_agent_id)
            clause = " AND ".join(where)
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM sf_tickets WHERE {clause}", params
            ).fetchone()["n"]
            rows = conn.execute(
                f"""
                SELECT * FROM sf_tickets
                WHERE {clause}
                ORDER BY datetime(created_at) DESC
                LIMIT ? OFFSET ?
                """,
                (*params, per_page, (page - 1) * per_page),
            ).fetchall()
            tickets = []
            for row in rows:
                ticket = _row_to_ticket(row)
                if founder_view and ticket.get("source") == FAMILY_HELP_SOURCE:
                    ticket = founder_visible_ticket(ticket)
                tickets.append(ticket)
            return tickets, int(total)
        finally:
            self._release(conn)

    def update_ticket(
        self,
        ticket_id: str,
        *,
        tenant_id: Optional[str] = None,
        edition_id: Optional[str] = None,
        subject: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
        tags: Optional[list] = None,
        category: Optional[str] = None,
        proposed_action_status: Optional[str] = None,
    ) -> Optional[dict]:
        from app.services.supportforge_proposed_action import VALID_STATUSES

        ticket = self.get_ticket(ticket_id, tenant_id=tenant_id, edition_id=edition_id)
        if not ticket:
            return None

        updates = []
        params: list[Any] = []
        if subject is not None:
            if not subject.strip():
                raise ValueError("subject cannot be empty")
            updates.append("subject = ?")
            params.append(subject.strip())
        if status is not None:
            updates.append("status = ?")
            params.append(_normalize_status(status))
            if status in {"resolved"}:
                updates.append("resolved_at = ?")
                params.append(_now())
            if status in {"closed"}:
                updates.append("closed_at = ?")
                params.append(_now())
        if priority is not None:
            updates.append("priority = ?")
            params.append(_normalize_priority(priority))
        if assigned_agent_id is not None:
            updates.append("assigned_agent_id = ?")
            params.append(assigned_agent_id)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if proposed_action_status is not None:
            if proposed_action_status not in VALID_STATUSES:
                raise ValueError(f"Invalid proposed_action_status: {proposed_action_status}")
            updates.append("proposed_action_status = ?")
            params.append(proposed_action_status)

        if not updates:
            return ticket

        updates.append("updated_at = ?")
        params.append(_now())
        params.append(ticket_id)

        conn = self._connect()
        try:
            conn.execute(
                f"UPDATE sf_tickets SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()
            return self.get_ticket(ticket_id, tenant_id=tenant_id, edition_id=edition_id, conn=conn)
        finally:
            self._release(conn)

    def add_message(
        self,
        ticket_id: str,
        content: str,
        *,
        tenant_id: Optional[str] = None,
        edition_id: Optional[str] = None,
        sender_type: str = "agent",
        sender_id: Optional[str] = None,
        content_html: Optional[str] = None,
        is_internal_note: bool = False,
        attachments: Optional[list] = None,
    ) -> Optional[dict]:
        ticket = self.get_ticket(ticket_id, tenant_id=tenant_id, edition_id=edition_id)
        if not ticket:
            return None
        if not content or not content.strip():
            raise ValueError("content is required")

        now = _now()
        message_id = str(uuid.uuid4())
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO sf_messages (
                    id, ticket_id, sender_type, sender_id, content, content_html,
                    is_internal_note, attachments, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    ticket_id,
                    sender_type,
                    sender_id,
                    content.strip(),
                    content_html,
                    1 if is_internal_note else 0,
                    json.dumps(attachments or []),
                    now,
                ),
            )
            extras = ["updated_at = ?"]
            extra_params: list[Any] = [now]
            if sender_type == "agent" and not ticket.get("first_response_at"):
                extras.append("first_response_at = ?")
                extra_params.append(now)
            if ticket.get("status") == "new":
                extras.append("status = 'open'")
            extra_params.append(ticket_id)
            conn.execute(
                f"UPDATE sf_tickets SET {', '.join(extras)} WHERE id = ?",
                extra_params,
            )
            conn.commit()
            row = conn.execute("SELECT * FROM sf_messages WHERE id = ?", (message_id,)).fetchone()
            data = dict(row)
            data["attachments"] = _parse_json(data.get("attachments"), [])
            data["is_internal_note"] = bool(data.get("is_internal_note"))
            data["ai_suggested"] = bool(data.get("ai_suggested"))
            return data
        finally:
            self._release(conn)

    def get_messages(self, ticket_id: str) -> list[dict]:
        conn = self._connect()
        try:
            ensure_supportforge_tables(conn)
            rows = conn.execute(
                "SELECT * FROM sf_messages WHERE ticket_id = ? ORDER BY datetime(created_at) ASC",
                (ticket_id,),
            ).fetchall()
            messages = []
            for row in rows:
                data = dict(row)
                data["attachments"] = _parse_json(data.get("attachments"), [])
                data["is_internal_note"] = bool(data.get("is_internal_note"))
                data["ai_suggested"] = bool(data.get("ai_suggested"))
                messages.append(data)
            return messages
        finally:
            self._release(conn)

    def close_ticket(self, ticket_id: str, *, tenant_id: Optional[str] = None) -> Optional[dict]:
        return self.update_ticket(ticket_id, tenant_id=tenant_id, status="closed")
