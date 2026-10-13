"""
SupportForge Ticket API — SQLite-backed.

The original PostgreSQL ORM path never created sf_tickets on empire.db.
This router reads and writes the SQLite store. Family-help tickets are
edition-isolated; founder responses include only the request itself.
Proposed actions are recorded, never executed.
"""
from __future__ import annotations

import math
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.schemas.supportforge_ticket import (
    MessageCreate,
    TicketCreate,
    TicketUpdate,
)
from app.services.supportforge_tickets_store import (
    FAMILY_HELP_SOURCE,
    FOUNDER_TENANT_ID,
    SupportForgeTicketStore,
    founder_visible_ticket,
)

router = APIRouter()
store = SupportForgeTicketStore()


class TicketListJSON(BaseModel):
    tickets: list[dict]
    total: int
    page: int
    per_page: int
    pages: int


def _http_error(exc: Exception, code: int = status.HTTP_400_BAD_REQUEST):
    raise HTTPException(status_code=code, detail=str(exc)) from exc


def _present(ticket: dict, *, founder_view: bool) -> dict:
    if founder_view and ticket.get("source") == FAMILY_HELP_SOURCE:
        return founder_visible_ticket(ticket)
    return ticket


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_ticket(ticket_data: TicketCreate, founder_view: bool = False):
    try:
        ticket = store.create_ticket(
            subject=ticket_data.subject,
            content=ticket_data.content,
            tenant_id=FOUNDER_TENANT_ID,
            customer_email=ticket_data.customer_email,
            customer_name=ticket_data.customer_name,
            channel=ticket_data.channel,
            priority=ticket_data.priority,
            tags=ticket_data.tags,
            category=ticket_data.category,
        )
    except ValueError as exc:
        _http_error(exc)
    return _present(ticket, founder_view=founder_view)


@router.get("/", response_model=None)
def list_tickets(
    ticket_status: Optional[str] = Query(None, alias="status"),
    assigned_agent_id: Optional[UUID] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
    edition_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    founder_view: bool = Query(
        True,
        description="Family-help tickets return only the request itself to the founder.",
    ),
    page: int = 1,
    per_page: int = Query(50, ge=1, le=100),
    limit: Optional[int] = Query(None, ge=1, le=100),
):
    if limit is not None:
        per_page = limit
    try:
        tickets, total = store.list_tickets(
            tenant_id=tenant_id,
            edition_id=edition_id,
            status=ticket_status,
            priority=priority,
            source=source,
            assigned_agent_id=str(assigned_agent_id) if assigned_agent_id else None,
            founder_view=founder_view,
            page=page,
            per_page=per_page,
        )
    except ValueError as exc:
        _http_error(exc)
    return {
        "tickets": tickets,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total else 1,
    }


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: str,
    tenant_id: Optional[str] = None,
    edition_id: Optional[str] = None,
    founder_view: bool = True,
):
    ticket = store.get_ticket(
        ticket_id,
        tenant_id=tenant_id,
        edition_id=edition_id,
        founder_view=founder_view,
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    messages = store.get_messages(ticket_id)
    if founder_view and ticket.get("source") == FAMILY_HELP_SOURCE:
        return {
            "ticket": founder_visible_ticket(ticket),
            "messages": [
                {
                    "id": msg.get("id"),
                    "content": msg.get("content"),
                    "created_at": msg.get("created_at"),
                    "sender_type": msg.get("sender_type"),
                }
                for msg in messages
                if not msg.get("is_internal_note")
            ],
            "customer": None,
            "assigned_agent": None,
        }

    return {
        "ticket": ticket,
        "messages": messages,
        "customer": None,
        "assigned_agent": None,
    }


@router.patch("/{ticket_id}")
def update_ticket(
    ticket_id: str,
    update_data: TicketUpdate,
    tenant_id: Optional[str] = None,
    edition_id: Optional[str] = None,
    founder_view: bool = True,
):
    try:
        ticket = store.update_ticket(
            ticket_id,
            tenant_id=tenant_id,
            edition_id=edition_id,
            subject=update_data.subject,
            status=update_data.status,
            priority=update_data.priority,
            assigned_agent_id=str(update_data.assigned_agent_id) if update_data.assigned_agent_id else None,
            tags=update_data.tags,
            category=update_data.category,
            proposed_action_status=getattr(update_data, "proposed_action_status", None),
        )
    except ValueError as exc:
        _http_error(exc)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return _present(ticket, founder_view=founder_view)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: str, tenant_id: Optional[str] = None):
    ticket = store.close_ticket(ticket_id, tenant_id=tenant_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")


@router.post("/{ticket_id}/messages", status_code=status.HTTP_201_CREATED)
def add_message(
    ticket_id: str,
    message_data: MessageCreate,
    tenant_id: Optional[str] = None,
    edition_id: Optional[str] = None,
    sender_type: str = "agent",
):
    try:
        message = store.add_message(
            ticket_id,
            message_data.content,
            tenant_id=tenant_id,
            edition_id=edition_id,
            sender_type=sender_type,
            content_html=message_data.content_html,
            is_internal_note=message_data.is_internal_note,
            attachments=message_data.attachments,
        )
    except ValueError as exc:
        _http_error(exc)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return message


@router.post("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: str,
    agent_id: UUID,
    tenant_id: Optional[str] = None,
):
    ticket = store.update_ticket(
        ticket_id,
        tenant_id=tenant_id,
        assigned_agent_id=str(agent_id),
        status="open",
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.post("/{ticket_id}/tags")
def update_ticket_tags(ticket_id: str, tags: List[str], tenant_id: Optional[str] = None):
    ticket = store.update_ticket(ticket_id, tenant_id=tenant_id, tags=tags)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


class ProposedActionUpdate(BaseModel):
    status: str = Field(..., pattern="^(proposed|accepted|rejected|completed)$")


@router.post("/{ticket_id}/proposed-action")
def update_proposed_action(
    ticket_id: str,
    body: ProposedActionUpdate,
    tenant_id: Optional[str] = None,
    founder_view: bool = True,
):
    """Owner records a decision on the proposal. Never builds anything."""
    try:
        ticket = store.update_ticket(
            ticket_id,
            tenant_id=tenant_id,
            proposed_action_status=body.status,
        )
    except ValueError as exc:
        _http_error(exc)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return _present(ticket, founder_view=founder_view)
