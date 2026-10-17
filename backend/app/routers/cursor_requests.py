"""HTTP surface for Pedir a Cursor. Launches nothing."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.edition import is_family_edition
from app.services import amp_allowlist
from app.services.cursor_requests import (
    MSG_APPROVED,
    CursorRequestError,
    create_request,
    get_request,
    list_requests,
    owner_decision,
)

router = APIRouter(tags=["cursor-requests"])


class DecisionBody(BaseModel):
    decision: str
    note: str = ""


def _email(request: Request) -> str:
    email = getattr(request.state, "amp_email", None)
    if not email:
        raise HTTPException(status_code=403, detail="Sin acceso. Entra con tu correo autorizado.")
    if not amp_allowlist.is_allowed(email=email):
        raise HTTPException(status_code=403, detail="Sin acceso. Entra con tu correo autorizado.")
    return email


def _family() -> None:
    if not is_family_edition():
        raise HTTPException(404, "Pedir a Cursor solo aplica a esta edición.")


@router.post("")
@router.post("/")
async def post_request(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    files: Optional[list[UploadFile]] = File(default=None),
):
    _family()
    email = _email(request)
    uploads: list[tuple[str, bytes]] = []
    for item in files or []:
        data = await item.read()
        uploads.append((item.filename or "shot.png", data))
    try:
        row = create_request(title=title, body=body, files=uploads, created_by=email)
    except CursorRequestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return row


@router.get("")
@router.get("/")
async def get_list(request: Request):
    _family()
    _email(request)
    try:
        return {"requests": list_requests()}
    except CursorRequestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{req_id}")
async def get_one(req_id: str, request: Request):
    _family()
    _email(request)
    try:
        return get_request(req_id)
    except CursorRequestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{req_id}/decision")
async def post_decision(req_id: str, body: DecisionBody, request: Request):
    _family()
    email = _email(request)
    try:
        row = owner_decision(req_id, decision=body.decision, note=body.note, by=email)
    except CursorRequestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    message = MSG_APPROVED if row["status"] == "owner_approved" else (
        "Listo, manito. Pediste cambios; Chief e lo vuelve a mirar."
    )
    return {"ok": True, "message": message, "request": row}
