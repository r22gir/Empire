"""Founder family-help inbox + Studio request log.

``GET /inbox`` and ``POST /inbox/{id}/reply`` match the live Studio contract.
Inbox reads are always through the read-only ``family_help_store`` (help.db
``mode=ro``). Type / status / work log live in the Studio-side table and
never write family help.db.

If the full ``app.services.family_help.add_reply`` from the live family
line is importable, reply is handed to it. Otherwise the reply is stored
only in the Studio log.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services import family_help_drafts, family_help_store, family_request_log
from app.services.family_help_store import HELP_EDITIONS
from app.services.supportforge_proposed_action import classify_proposed_action

router = APIRouter(prefix="/family-help", tags=["family-help"])


class ReplyBody(BaseModel):
    body: str = Field(min_length=1)
    author: str = "Max"
    explicit_yes: bool = False


class MetaPatch(BaseModel):
    request_type: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None


class LogBody(BaseModel):
    body: str = Field(min_length=1)
    kind: str = "note"
    href: Optional[str] = None
    href_label: Optional[str] = None


class OrganizerBody(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class DraftSendBody(BaseModel):
    body: str = Field(min_length=1)
    author: str = "Max"
    explicit_yes: bool = False


class SaveGuideBody(BaseModel):
    title: Optional[str] = None
    body: str = Field(min_length=1)
    steps: Optional[list] = None


def _is_founder_process() -> bool:
    raw = (__import__("os").getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")
    return raw in ("", "main", "workroom", "empire")


def _founder_or_403() -> None:
    if not _is_founder_process():
        raise HTTPException(
            status_code=403,
            detail="El buzón de ediciones familiares solo lo ve el Max personal de Rafael.",
        )


def _process_edition() -> Optional[str]:
    raw = (__import__("os").getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")
    if raw in ("amp", "max_e", "maxe"):
        return "amp"
    if raw == "maxine":
        return "maxine"
    return None


def _guide_edition_or_403(requested: Optional[str]) -> Optional[str]:
    """Founder may read any edition. A family process may read only its own."""
    mine = _process_edition()
    if mine is None:
        return requested
    if requested and requested != mine:
        raise HTTPException(status_code=403, detail="Esta guía no es de tu edición.")
    return mine


def _merge(ticket: dict, *, mark: bool = False) -> dict:
    edition = ticket.get("edition") or ""
    ticket_id = ticket.get("id") or ""
    suggested = classify_proposed_action(ticket.get("message") or "", ticket.get("transcript") or "")
    if mark:
        meta = family_request_log.mark_seen(
            edition,
            ticket_id,
            message=ticket.get("message") or "",
            transcript=ticket.get("transcript") or "",
        )
    else:
        meta = family_request_log.ensure_meta(
            edition,
            ticket_id,
            message=ticket.get("message") or "",
            transcript=ticket.get("transcript") or "",
        )
    merged = dict(ticket)
    merged["request_type"] = meta["request_type"]
    merged["type"] = meta["type"]
    merged["type_suggested"] = meta["type_suggested"]
    merged["type_edited"] = meta["type_edited"]
    merged["log_status"] = meta["status"]
    merged["proposal_status"] = meta["proposal_status"]
    merged["studio_status"] = meta["status"]
    merged["unread"] = meta["unread"]
    merged["seen_at"] = meta["seen_at"]
    merged["organizer_task_id"] = meta["organizer_task_id"]
    merged["log"] = meta["log"]
    merged["suggested_type"] = suggested
    return merged


@router.get("/inbox")
async def founder_inbox(edition: Optional[str] = None, status: Optional[str] = None):
    _founder_or_403()
    editions = (edition,) if edition else None
    if edition and edition not in HELP_EDITIONS:
        return {"tickets": []}
    tickets = family_help_store.list_tickets(editions, status=status)
    return {"tickets": [_merge(t) for t in tickets]}


@router.get("/unread-count")
async def unread_count():
    _founder_or_403()
    tickets = family_help_store.list_tickets()
    seen = family_request_log.unread_ticket_ids()
    count = sum(1 for t in tickets if (t.get("edition"), t.get("id")) not in seen)
    return {"unread": count, "total": len(tickets)}


@router.get("/inbox/{ticket_id}")
async def founder_ticket(ticket_id: str):
    _founder_or_403()
    ticket = family_help_store.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"ticket": _merge(ticket, mark=True)}


@router.post("/inbox/{ticket_id}/reply")
async def founder_reply(ticket_id: str, body: ReplyBody, request: Request):
    _founder_or_403()
    ticket = family_help_store.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    text = (body.body or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="la respuesta está vacía")

    live_ticket = None
    try:
        from app.services.family_help import add_reply, explicit_yes_from_ui

        confirmed = explicit_yes_from_ui(request, body.explicit_yes)
        live_ticket = add_reply(
            ticket_id,
            text,
            author=body.author or "Max",
            draft=False,
            explicit_yes=confirmed,
            source="ui_confirm_button" if confirmed else "api",
        )
    except ImportError:
        live_ticket = None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    family_request_log.add_log(
        ticket["edition"],
        ticket_id,
        body=text,
        kind="reply",
        message=ticket.get("message") or "",
        transcript=ticket.get("transcript") or "",
    )
    refreshed = family_help_store.get_ticket(ticket_id) or live_ticket or ticket
    if live_ticket and isinstance(live_ticket, dict):
        refreshed = {**refreshed, **{k: live_ticket[k] for k in live_ticket if k != "log"}}
    return {"ok": True, "ticket": _merge(refreshed, mark=True), "wrote_help_db": live_ticket is not None}


@router.get("/inbox/{ticket_id}/attachments/{attachment_id}")
async def founder_attachment(ticket_id: str, attachment_id: str):
    _founder_or_403()
    found = family_help_store.attachment_file(ticket_id, attachment_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    path, att = found
    return FileResponse(
        path,
        filename=att.get("filename") or path.name,
        media_type=att.get("content_type") or "application/octet-stream",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.patch("/requests/{edition}/{ticket_id}")
async def patch_studio_meta(edition: str, ticket_id: str, body: MetaPatch):
    _founder_or_403()
    if edition not in HELP_EDITIONS:
        raise HTTPException(status_code=404, detail="Edición no encontrada")
    ticket = family_help_store.get_ticket(ticket_id, edition=edition)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    try:
        meta = family_request_log.update_meta(
            edition,
            ticket_id,
            request_type=body.request_type or body.type,
            status=body.status,
            message=ticket.get("message") or "",
            transcript=ticket.get("transcript") or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "ticket": _merge(ticket), "meta": meta}


@router.post("/requests/{edition}/{ticket_id}/seen")
async def mark_seen(edition: str, ticket_id: str):
    _founder_or_403()
    ticket = family_help_store.get_ticket(ticket_id, edition=edition)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    family_request_log.mark_seen(
        edition,
        ticket_id,
        message=ticket.get("message") or "",
        transcript=ticket.get("transcript") or "",
    )
    return {"ok": True, "ticket": _merge(ticket, mark=True)}


@router.post("/requests/{edition}/{ticket_id}/log")
async def add_work_log(edition: str, ticket_id: str, body: LogBody):
    _founder_or_403()
    if edition not in HELP_EDITIONS:
        raise HTTPException(status_code=404, detail="Edición no encontrada")
    ticket = family_help_store.get_ticket(ticket_id, edition=edition)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    try:
        meta = family_request_log.add_log(
            edition,
            ticket_id,
            body=body.body,
            kind=body.kind,
            href=body.href,
            href_label=body.href_label,
            message=ticket.get("message") or "",
            transcript=ticket.get("transcript") or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "ticket": _merge(ticket), "meta": meta}


@router.post("/requests/{edition}/{ticket_id}/organizer-task")
async def create_organizer_task(edition: str, ticket_id: str, body: OrganizerBody | None = None):
    _founder_or_403()
    if edition not in HELP_EDITIONS:
        raise HTTPException(status_code=404, detail="Edición no encontrada")
    ticket = family_help_store.get_ticket(ticket_id, edition=edition)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    payload = body or OrganizerBody()
    title = (payload.title or "").strip() or (ticket.get("summary") or ticket.get("message") or ticket_id)[:80]
    description = (payload.description or "").strip() or (
        f"Family request from {ticket.get('who_label') or edition}.\n\n"
        f"{ticket.get('message') or ''}"
    )
    meta = family_request_log.create_organizer_task(
        edition,
        ticket_id,
        title=title,
        description=description,
        message=ticket.get("message") or "",
        transcript=ticket.get("transcript") or "",
    )
    return {"ok": True, "ticket": _merge(ticket), "meta": meta, "task": meta.get("organizer_task")}


@router.post("/inbox/{ticket_id}/generate-reply")
async def generate_reply(ticket_id: str):
    """On-demand draft reply. Does not send or save."""
    _founder_or_403()
    ticket = family_help_store.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket = _merge(ticket)
    try:
        draft = await family_help_drafts.generate_reply(ticket)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True, "draft": draft, "would_send": False, "saved": False}


@router.post("/inbox/{ticket_id}/generate-manual")
async def generate_manual(ticket_id: str):
    """On-demand how-to draft with ui-map links. Does not send or save."""
    _founder_or_403()
    ticket = family_help_store.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket = _merge(ticket)
    try:
        draft = await family_help_drafts.generate_manual(ticket)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True, "draft": draft, "would_send": False, "saved": False}


@router.post("/inbox/{ticket_id}/send-draft")
async def send_draft(ticket_id: str, body: DraftSendBody, request: Request):
    """Send only after Rafael taps. Same path as /reply."""
    return await founder_reply(
        ticket_id,
        ReplyBody(body=body.body, author=body.author, explicit_yes=body.explicit_yes),
        request,
    )


@router.post("/inbox/{ticket_id}/save-guide")
async def save_guide(ticket_id: str, body: SaveGuideBody):
    """Save a manual to the per-edition help library. Founder tap only."""
    _founder_or_403()
    ticket = family_help_store.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    try:
        guide = family_request_log.save_guide(
            ticket["edition"],
            title=body.title or (ticket.get("summary") or ticket.get("message") or "Manual")[:80],
            body=body.body,
            ticket_id=ticket_id,
            steps=body.steps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    family_request_log.add_log(
        ticket["edition"],
        ticket_id,
        body=f"Saved help guide: {guide['title']}",
        kind="guide",
        href=f"/?screen=family-help&guide={guide['id']}",
        href_label="Open in help library",
        message=ticket.get("message") or "",
        transcript=ticket.get("transcript") or "",
    )
    return {"ok": True, "saved": True, "guide": guide, "ticket": _merge(ticket)}


@router.get("/guides")
async def list_help_guides(edition: Optional[str] = None):
    """Per-edition help library. Family processes see only their edition."""
    scoped = _guide_edition_or_403(edition)
    if scoped and scoped not in HELP_EDITIONS:
        return {"guides": []}
    guides = family_request_log.list_guides(scoped)
    return {"guides": guides, "edition": scoped}


@router.get("/guides/{guide_id}")
async def get_help_guide(guide_id: str, edition: Optional[str] = None):
    scoped = _guide_edition_or_403(edition)
    guide = family_request_log.get_guide(guide_id, edition=scoped)
    if not guide:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    if not _is_founder_process() and guide["edition"] != _process_edition():
        raise HTTPException(status_code=403, detail="Esta guía no es de tu edición.")
    return {"guide": guide}
