"""
ForgeCRM unified WhatsApp/SMS thread routes.

Inbound webhooks store only. Outbound is draft-until-owner-approve.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services import crm_messaging as crm
from app.services.feature_flags import forgecrm_messaging_enabled

router = APIRouter(prefix="/crm", tags=["crm-messaging"])


class DraftCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    channel: str = Field(default="sms")
    to_address: Optional[str] = None


class ApproveRequest(BaseModel):
    owner_id: str = Field(..., min_length=1, max_length=80)


class InboundWebhook(BaseModel):
    channel: str
    body: str
    from_address: str
    to_address: Optional[str] = None
    customer_id: Optional[str] = None
    provider_message_id: Optional[str] = None


def _require_messaging() -> None:
    if not forgecrm_messaging_enabled():
        raise HTTPException(status_code=403, detail="ForgeCRM messaging is disabled")


def _raise(exc: crm.CrmMessagingError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/threads")
def list_threads(limit: int = Query(100, ge=1, le=500)):
    _require_messaging()
    with get_db() as conn:
        crm.ensure_schema(conn)
        return {"threads": crm.list_threads(conn, limit=limit), "policy": crm.POLICY}


@router.get("/customers/{customer_id}/thread")
def get_customer_thread(customer_id: str):
    _require_messaging()
    try:
        with get_db() as conn:
            return crm.get_thread_payload(conn, customer_id)
    except crm.CrmMessagingError as exc:
        _raise(exc)


@router.post("/customers/{customer_id}/thread/draft")
def create_outbound_draft(customer_id: str, payload: DraftCreate):
    """Create an outbound DRAFT. Does not send."""
    _require_messaging()
    try:
        with get_db() as conn:
            return crm.compose_draft(
                conn,
                customer_id=customer_id,
                body=payload.body,
                channel=payload.channel,
                to_address=payload.to_address,
            )
    except crm.CrmMessagingError as exc:
        _raise(exc)


@router.post("/customers/{customer_id}/thread/messages/{message_id}/approve")
def approve_outbound(
    customer_id: str,
    message_id: str,
    payload: ApproveRequest,
):
    """Owner-explicit per-message approval. Sandbox send only."""
    _require_messaging()
    try:
        with get_db() as conn:
            return crm.approve_and_sandbox_send(
                conn,
                message_id,
                customer_id=customer_id,
                owner_id=payload.owner_id,
            )
    except crm.CrmMessagingError as exc:
        _raise(exc)


@router.post("/customers/{customer_id}/thread/messages/{message_id}/reject")
def reject_outbound(customer_id: str, message_id: str):
    _require_messaging()
    try:
        with get_db() as conn:
            return crm.reject_draft(conn, message_id, customer_id=customer_id)
    except crm.CrmMessagingError as exc:
        _raise(exc)


@router.post("/customers/{customer_id}/thread/messages/{message_id}/send")
def send_blocked_without_approval(customer_id: str, message_id: str):
    """Send-shaped route: blocked unless the owner already approved this draft."""
    _require_messaging()
    try:
        with get_db() as conn:
            return crm.send_without_approval_blocked(conn, message_id)
    except crm.CrmMessagingError as exc:
        _raise(exc)


@router.post("/webhooks/whatsapp")
def whatsapp_inbound(payload: InboundWebhook):
    """Inbound WhatsApp only. Never replies."""
    _require_messaging()
    try:
        with get_db() as conn:
            result = crm.ingest_inbound(
                conn,
                channel="whatsapp",
                body=payload.body,
                from_address=payload.from_address,
                to_address=payload.to_address,
                customer_id=payload.customer_id,
                provider_message_id=payload.provider_message_id,
            )
            return crm.webhook_ingest_only(result)
    except crm.CrmMessagingError as exc:
        _raise(exc)


@router.post("/webhooks/sms")
def sms_inbound(payload: InboundWebhook):
    """Inbound SMS only. Never replies."""
    _require_messaging()
    try:
        with get_db() as conn:
            result = crm.ingest_inbound(
                conn,
                channel="sms",
                body=payload.body,
                from_address=payload.from_address,
                to_address=payload.to_address,
                customer_id=payload.customer_id,
                provider_message_id=payload.provider_message_id,
            )
            return crm.webhook_ingest_only(result)
    except crm.CrmMessagingError as exc:
        _raise(exc)
