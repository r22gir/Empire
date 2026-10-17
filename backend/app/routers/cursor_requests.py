"""HTTP API for the edition Cursor-request queue. Launches nothing."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.edition import is_family_edition
from app.services.cursor_requests import (
    CursorRequestError,
    MENSAJE_APPROVED,
    MENSAJE_CHANGES,
    create,
    get,
    list_requests,
    owner_decision,
)

router = APIRouter(prefix="/edition/cursor-requests", tags=["cursor-requests"])


class DecisionBody(BaseModel):
    decision: str
    note: str = ""


def _email(request: Request) -> str:
    email = getattr(request.state, "amp_email", None)
    if not email:
        raise HTTPException(status_code=403, detail="Sin acceso. Entra con tu correo autorizado.")
    return str(email)


def _family() -> None:
    if not is_family_edition():
        raise HTTPException(status_code=403, detail="Esta cola es solo de Max-e.")


def _raise(exc: CursorRequestError):
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("")
async def create_request(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    files: Optional[list[UploadFile]] = File(None),
):
    _family()
    email = _email(request)
    uploads: list[tuple[str, bytes]] = []
    for upload in files or []:
        data = await upload.read()
        uploads.append((upload.filename or "shot.png", data))
    try:
        item = create(title=title, body=body, files=uploads, created_by=email)
    except CursorRequestError as exc:
        _raise(exc)
    return item


@router.get("")
async def list_own(request: Request, status: Optional[str] = None):
    _family()
    _email(request)
    return {"requests": list_requests(status=status)}


@router.get("/{req_id}")
async def show_one(req_id: str, request: Request):
    _family()
    _email(request)
    try:
        return get(req_id)
    except CursorRequestError as exc:
        _raise(exc)


@router.post("/{req_id}/decision")
async def decide(req_id: str, body: DecisionBody, request: Request):
    _family()
    email = _email(request)
    try:
        item = owner_decision(req_id, body.decision, body.note, by=email)
    except CursorRequestError as exc:
        _raise(exc)
    message = MENSAJE_APPROVED if body.decision == "approve" else MENSAJE_CHANGES
    return {"ok": True, "message": message, "request": item}
