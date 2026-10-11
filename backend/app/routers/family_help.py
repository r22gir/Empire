"""HTTP API for family-edition help tickets.

Family (amp / maxine): create tickets, list/read own tickets, fetch
own attachments. Inbox and reply routes return 403.

Founder / personal Max: list the inbox, reply, close, draft. Never
exposes Workroom quotes, jobs, or CRM through these paths.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.edition import edition_name, is_family_edition, is_founder_edition

router = APIRouter(prefix="/family-help", tags=["family-help"])


class ReplyBody(BaseModel):
    body: str = Field(min_length=1)
    author: str = "Max"
    explicit_yes: bool = False


class CloseBody(BaseModel):
    status: str = "closed"


class ApplyBody(BaseModel):
    explicit_yes: bool = False


def _family_or_403() -> str:
    if not is_family_edition():
        raise HTTPException(status_code=403, detail="Solo Max-e y Maxine pueden crear o leer sus tickets.")
    return edition_name()


def _founder_or_403() -> None:
    if is_family_edition() or not is_founder_edition():
        raise HTTPException(status_code=403, detail="El buzón de ediciones familiares solo lo ve el Max personal de Rafael.")


def _sender(request: Request) -> str:
    from app.services.family_help import edition_owner_name

    email = getattr(request.state, "amp_email", None)
    if email:
        return str(email)
    return edition_owner_name()


@router.get("/status")
async def help_status():
    from app.services.family_help import public_status

    return public_status()


@router.post("/tickets")
async def create_ticket(
    request: Request,
    message: str = Form(""),
    history_json: str = Form("[]"),
    language: Optional[str] = Form(None),
    voice: Optional[UploadFile] = File(None),
    files: list[UploadFile] = File(default=[]),
):
    from app.services.family_help import create_ticket as create

    _family_or_403()
    history = []
    if history_json:
        try:
            import json
            parsed = json.loads(history_json)
            if isinstance(parsed, list):
                history = parsed
        except json.JSONDecodeError:
            history = []

    attachments = []
    transcript = ""
    if voice is not None and (voice.filename or voice.content_type):
        raw = await voice.read()
        attachments.append({
            "filename": voice.filename or "recording.webm",
            "content_type": voice.content_type or "audio/webm",
            "data": raw,
            "kind": "voice",
        })
        if raw:
            try:
                voice.file.seek(0)
            except Exception:
                pass
            try:
                from io import BytesIO
                from app.services.max.stt_http import normalize_stt_language, transcribe_upload

                class _Replay:
                    def __init__(self, data, filename, content_type):
                        self.filename = filename
                        self.content_type = content_type
                        self._buf = BytesIO(data)

                    async def read(self):
                        return self._buf.read()

                result = await transcribe_upload(
                    _Replay(raw, voice.filename, voice.content_type),
                    normalize_stt_language(language),
                )
                transcript = (result or {}).get("text") or ""
            except HTTPException:
                transcript = ""
            except Exception:
                transcript = ""

    for upload in files or []:
        if not upload or not (upload.filename or upload.content_type):
            continue
        attachments.append({
            "filename": upload.filename or "file",
            "content_type": upload.content_type or "application/octet-stream",
            "data": await upload.read(),
            "kind": "file",
        })

    try:
        ticket = create(
            message=message,
            sender=_sender(request),
            history=history,
            transcript=transcript,
            attachments=attachments,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "ticket": ticket}


@router.get("/tickets")
async def list_own_tickets(status: Optional[str] = None):
    from app.services.family_help import list_tickets

    edition = _family_or_403()
    return {"tickets": list_tickets(edition=edition, status=status)}


@router.get("/tickets/{ticket_id}")
async def get_own_ticket(ticket_id: str):
    from app.services.family_help import get_ticket

    edition = _family_or_403()
    ticket = get_ticket(ticket_id, edition=edition)
    if not ticket or ticket.get("edition") != edition:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"ticket": ticket}


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}")
async def get_own_attachment(ticket_id: str, attachment_id: str):
    from app.services.family_help import attachment_path, get_ticket

    edition = _family_or_403()
    ticket = get_ticket(ticket_id, edition=edition)
    if not ticket or ticket.get("edition") != edition:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    path = attachment_path(ticket_id, attachment_id, edition=edition)
    if path is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return FileResponse(path, filename=path.name)


@router.get("/inbox")
async def founder_inbox(edition: Optional[str] = None, status: Optional[str] = None):
    from app.services.family_help import list_tickets

    _founder_or_403()
    return {"tickets": list_tickets(edition=edition, status=status)}


@router.get("/inbox/{ticket_id}")
async def founder_ticket(ticket_id: str):
    from app.services.family_help import get_ticket

    _founder_or_403()
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"ticket": ticket}


@router.post("/inbox/{ticket_id}/reply")
async def founder_reply(ticket_id: str, body: ReplyBody):
    from app.services.family_help import add_reply

    _founder_or_403()
    try:
        ticket = add_reply(
            ticket_id,
            body.body,
            author=body.author or "Max",
            draft=False,
            explicit_yes=body.explicit_yes,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "ticket": ticket}


@router.post("/inbox/{ticket_id}/draft")
async def founder_draft(ticket_id: str):
    from app.services.family_help import draft_reply

    _founder_or_403()
    try:
        return draft_reply(ticket_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/inbox/{ticket_id}/close")
async def founder_close(ticket_id: str, body: CloseBody | None = None):
    from app.services.family_help import close_ticket

    _founder_or_403()
    try:
        return {"ok": True, "ticket": close_ticket(ticket_id)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/inbox/{ticket_id}/apply")
async def founder_apply(ticket_id: str, body: ApplyBody):
    from app.services.family_help import apply_change_from_ticket

    _founder_or_403()
    try:
        return apply_change_from_ticket(ticket_id=ticket_id, explicit_yes=body.explicit_yes)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/inbox/{ticket_id}/attachments/{attachment_id}")
async def founder_attachment(ticket_id: str, attachment_id: str):
    from app.services.family_help import attachment_path, get_ticket

    _founder_or_403()
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    path = attachment_path(ticket_id, attachment_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return FileResponse(path, filename=path.name)
