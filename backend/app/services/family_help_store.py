"""
Family-help store — isolated per family edition.

Each edition writes 'Pedir ayuda a Max' requests into its own directory
and SQLite file. The founder may read the request text only; edition
memory, conversations, and other private files are never copied here
and never attached to SupportForge tickets.

Creating a request also opens a SupportForge ticket with a proposed
action (adjust / fix / create). Nothing is built automatically.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.services.data_paths import family_help_dir
from app.services.supportforge_proposed_action import propose_action
from app.services.supportforge_tickets_store import (
    FAMILY_HELP_SOURCE,
    SupportForgeTicketStore,
    founder_visible_ticket,
)

FAMILY_EDITIONS = ("amp", "maxine", "minimax-meter")
FAMILY_EDITION_SET = frozenset(FAMILY_EDITIONS)

REQUEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS help_requests (
    id TEXT PRIMARY KEY,
    edition_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    requester_name TEXT,
    ticket_id TEXT,
    proposed_action TEXT NOT NULL,
    proposed_action_summary TEXT NOT NULL,
    proposed_action_status TEXT NOT NULL DEFAULT 'proposed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_help_requests_created ON help_requests(created_at);
"""

FOUNDER_REQUEST_KEYS = (
    "id",
    "edition_id",
    "subject",
    "message",
    "requester_name",
    "ticket_id",
    "proposed_action",
    "proposed_action_summary",
    "proposed_action_status",
    "created_at",
    "updated_at",
)


def tenant_id_for_edition(edition_id: str) -> str:
    return f"edition:{edition_id}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_edition(edition_id: str) -> str:
    if edition_id not in FAMILY_EDITION_SET:
        raise ValueError(
            f"Unknown family edition '{edition_id}'. "
            f"Allowed: {', '.join(FAMILY_EDITIONS)}"
        )
    return edition_id


def _row_to_request(row) -> dict:
    return {key: row[key] for key in FOUNDER_REQUEST_KEYS}


class FamilyHelpStore:
    def __init__(self, root: Optional[Path] = None, ticket_store: Optional[SupportForgeTicketStore] = None):
        self.root = Path(root) if root is not None else family_help_dir()
        self.ticket_store = ticket_store or SupportForgeTicketStore()

    def edition_dir(self, edition_id: str) -> Path:
        edition_id = _validate_edition(edition_id)
        path = self.root / edition_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def edition_db_path(self, edition_id: str) -> Path:
        return self.edition_dir(edition_id) / "requests.db"

    def _connect(self, edition_id: str) -> sqlite3.Connection:
        path = self.edition_db_path(edition_id)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(REQUEST_SCHEMA)
        conn.commit()
        return conn

    def submit(
        self,
        *,
        edition_id: str,
        subject: str,
        message: str,
        requester_name: Optional[str] = None,
    ) -> dict:
        edition_id = _validate_edition(edition_id)
        if not subject or not subject.strip():
            raise ValueError("subject is required")
        if not message or not message.strip():
            raise ValueError("message is required")

        proposed = propose_action(subject, message, edition_id)
        request_id = str(uuid.uuid4())
        now = _now()

        ticket = self.ticket_store.create_ticket(
            subject=subject.strip(),
            content=message.strip(),
            tenant_id=tenant_id_for_edition(edition_id),
            customer_name=requester_name,
            channel="family-help",
            category="pedir-ayuda-a-max",
            source=FAMILY_HELP_SOURCE,
            edition_id=edition_id,
            family_help_request_id=request_id,
            proposed=proposed,
        )

        conn = self._connect(edition_id)
        try:
            conn.execute(
                """
                INSERT INTO help_requests (
                    id, edition_id, subject, message, requester_name, ticket_id,
                    proposed_action, proposed_action_summary, proposed_action_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?)
                """,
                (
                    request_id,
                    edition_id,
                    subject.strip(),
                    message.strip(),
                    requester_name,
                    ticket["id"],
                    proposed["kind"],
                    proposed["summary"],
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM help_requests WHERE id = ?", (request_id,)
            ).fetchone()
        finally:
            conn.close()

        request = _row_to_request(row)
        request["ticket"] = founder_visible_ticket(ticket)
        request["auto_build"] = False
        return request

    def list_for_edition(self, edition_id: str) -> list[dict]:
        edition_id = _validate_edition(edition_id)
        if not self.edition_db_path(edition_id).exists():
            return []
        conn = self._connect(edition_id)
        try:
            rows = conn.execute(
                "SELECT * FROM help_requests ORDER BY datetime(created_at) DESC"
            ).fetchall()
            return [_row_to_request(row) for row in rows]
        finally:
            conn.close()

    def get(self, edition_id: str, request_id: str) -> Optional[dict]:
        edition_id = _validate_edition(edition_id)
        if not self.edition_db_path(edition_id).exists():
            return None
        conn = self._connect(edition_id)
        try:
            row = conn.execute(
                "SELECT * FROM help_requests WHERE id = ?", (request_id,)
            ).fetchone()
            return _row_to_request(row) if row else None
        finally:
            conn.close()

    def list_for_founder(self) -> list[dict]:
        """All edition requests, request fields only. No cross-edition internals."""
        requests: list[dict] = []
        for edition_id in FAMILY_EDITIONS:
            requests.extend(self.list_for_edition(edition_id))
        requests.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return requests
