"""HTTP API for family-edition help tickets.

Family (amp / maxine): create tickets, list/read own tickets, fetch
own attachments. Inbox and reply routes return 403.

Founder / personal Max: list the inbox, reply, close, draft. Never
exposes Workroom quotes, jobs, or CRM through these paths.

``/inbox*`` is not access-exempt. On family editions it is gated by
``amp_access_middleware`` (Cloudflare Access / AMP session) and then
rejected by ``_founder_or_403``. On studio / workroom, Cloudflare Access
in front of studio.empirebox.store is the existing founder auth; the
route still requires ``is_founder_edition``.
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


class TranscribeBody(BaseModel):
    language: Optional[str] = None


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


def _confirm_send(request: Request, body_flag: bool) -> bool:
    from app.services.family_help import explicit_yes_from_ui

    return explicit_yes_from_ui(request, body_flag)


async def _read_upload(upload: UploadFile, *, kind: str) -> bytes:
    from app.services.family_help import MAX_FILE_BYTES, MAX_VOICE_BYTES, read_upload_limited

    limit = MAX_VOICE_BYTES if kind == "voice" else MAX_FILE_BYTES
    declared = None
    header_len = None
    if upload.headers:
        header_len = upload.headers.get("content-length")
    if header_len:
        try:
            declared = int(header_len)
        except ValueError:
            declared = None
    return await read_upload_limited(upload, limit=limit, content_length=declared)


def _file_response(path, filename: str, content_type: str):
    from app.services.family_help import safe_download_headers

    headers = safe_download_headers(filename, content_type)
    media = headers.get("Content-Type") or "application/octet-stream"
    return FileResponse(
        path,
        filename=filename,
        media_type=media,
        headers={
            "Content-Disposition": headers["Content-Disposition"],
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _transcribe_bytes(data: bytes, filename: str, content_type: str, language: Optional[str]) -> str:
    if not data:
        return ""
    try:
        from io import BytesIO
        from app.services.max.stt_http import normalize_stt_language, transcribe_upload

        class _Replay:
            def __init__(self, payload, name, mime):
                self.filename = name
                self.content_type = mime
                self._buf = BytesIO(payload)

            async def read(self):
                return self._buf.read()

        result = await transcribe_upload(
            _Replay(data, filename, content_type),
            normalize_stt_language(language),
        )
        return (result or {}).get("text") or ""
    except HTTPException:
        return ""
    except Exception:
        return ""


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
        raw = await _read_upload(voice, kind="voice")
        attachments.append({
            "filename": voice.filename or "recording.webm",
            "content_type": voice.content_type or "",
            "data": raw,
            "kind": "voice",
        })
        transcript = await _transcribe_bytes(
            raw,
            voice.filename or "recording.webm",
            voice.content_type or "audio/webm",
            language,
        )

    for upload in files or []:
        if not upload or not (upload.filename or upload.content_type):
            continue
        attachments.append({
            "filename": upload.filename or "file",
            "content_type": upload.content_type or "",
            "data": await _read_upload(upload, kind="file"),
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
    att = next((a for a in (ticket.get("attachments") or []) if a["id"] == attachment_id), None)
    path = attachment_path(ticket_id, attachment_id, edition=edition)
    if path is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return _file_response(path, (att or {}).get("filename") or path.name, (att or {}).get("content_type") or "")


@router.post("/tickets/{ticket_id}/transcribe")
async def retry_own_transcript(ticket_id: str, body: TranscribeBody | None = None):
    from app.services.family_help import (
        attachment_path,
        get_ticket,
        set_transcript,
        voice_attachment,
    )

    edition = _family_or_403()
    ticket = get_ticket(ticket_id, edition=edition)
    if not ticket or ticket.get("edition") != edition:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    voice = voice_attachment(ticket)
    if not voice:
        raise HTTPException(status_code=404, detail="No hay audio para transcribir")
    path = attachment_path(ticket_id, voice["id"], edition=edition)
    if path is None:
        raise HTTPException(status_code=404, detail="No hay audio para transcribir")
    text = await _transcribe_bytes(
        path.read_bytes(),
        voice.get("filename") or path.name,
        voice.get("content_type") or "",
        (body.language if body else None),
    )
    updated = set_transcript(ticket_id, text, pending=not bool(text))
    return {"ok": True, "ticket": updated, "transcript_pending": not bool(text)}


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
async def founder_reply(ticket_id: str, body: ReplyBody, request: Request):
    from app.services.family_help import add_reply

    _founder_or_403()
    confirmed = _confirm_send(request, body.explicit_yes)
    try:
        ticket = add_reply(
            ticket_id,
            body.body,
            author=body.author or "Max",
            draft=False,
            explicit_yes=confirmed,
            source="ui_confirm_button" if confirmed else "api",
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


@router.post("/inbox/{ticket_id}/reveal-attachments")
async def founder_reveal(ticket_id: str):
    from app.services.family_help import reveal_attachments

    _founder_or_403()
    try:
        return {"ok": True, "ticket": reveal_attachments(ticket_id)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/inbox/{ticket_id}/transcribe")
async def founder_retry_transcript(ticket_id: str, body: TranscribeBody | None = None):
    from app.services.family_help import (
        attachment_path,
        get_ticket,
        set_transcript,
        voice_attachment,
    )

    _founder_or_403()
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    voice = voice_attachment(ticket)
    if not voice:
        raise HTTPException(status_code=404, detail="No hay audio para transcribir")
    path = attachment_path(ticket_id, voice["id"], edition=ticket["edition"])
    if path is None:
        raise HTTPException(status_code=404, detail="No hay audio para transcribir")
    text = await _transcribe_bytes(
        path.read_bytes(),
        voice.get("filename") or path.name,
        voice.get("content_type") or "",
        (body.language if body else None),
    )
    updated = set_transcript(ticket_id, text, pending=not bool(text))
    return {"ok": True, "ticket": updated, "transcript_pending": not bool(text)}


@router.get("/inbox/{ticket_id}/attachments/{attachment_id}")
async def founder_attachment(ticket_id: str, attachment_id: str):
    from app.services.family_help import attachment_path, get_ticket

    _founder_or_403()
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    if ticket.get("edition") == "maxine" and not ticket.get("attachments_revealed"):
        raise HTTPException(status_code=403, detail="Abre los adjuntos de Maxine primero.")
    att = next((a for a in (ticket.get("attachments") or []) if a["id"] == attachment_id), None)
    path = attachment_path(ticket_id, attachment_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return _file_response(path, (att or {}).get("filename") or path.name, (att or {}).get("content_type") or "")
