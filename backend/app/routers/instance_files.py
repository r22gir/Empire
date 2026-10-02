"""Per-user Drive archive and photo intake. No shared founder account."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.instance_files import (
    FileArchiveError,
    connection_status,
    exchange_auth_code,
    fetch_picked_items,
    import_picked,
    nightly_export,
    oauth_finish,
    oauth_start,
    open_picker,
    photo_timeline,
    picker_session,
    remember_user,
    save_photo,
    stored_redirect_uri,
)

router = APIRouter(tags=["instance-files"])


class ConnectBody(BaseModel):
    user_id: str
    redirect_uri: str


class FinishBody(BaseModel):
    user_id: str
    code: str
    state: str


class PickerBody(BaseModel):
    user_id: str


class ImportBody(BaseModel):
    user_id: str
    session_id: str
    project: str
    lot: str = ""
    stage: str = ""


def _fail(exc: FileArchiveError) -> None:
    raise HTTPException(400, str(exc))


@router.get("/files/drive/status")
def drive_status(user_id: str = ""):
    if user_id:
        remember_user(user_id)
    return connection_status(user_id)


@router.post("/files/drive/connect")
def drive_connect(body: ConnectBody):
    remember_user(body.user_id)
    return oauth_start(body.user_id, body.redirect_uri)


@router.post("/files/drive/finish")
def drive_finish(body: FinishBody):
    def _exchange(code: str) -> dict:
        return exchange_auth_code(code, stored_redirect_uri(body.user_id))

    try:
        return oauth_finish(body.user_id, body.code, body.state, _exchange)
    except FileArchiveError as exc:
        _fail(exc)


@router.post("/files/drive/export")
def drive_export_now():
    return nightly_export()


@router.post("/photos/intake")
async def photo_intake(
    file: UploadFile = File(...),
    project: str = Form(...),
    lot: str = Form(""),
    stage: str = Form(""),
    source: str = Form("upload"),
):
    data = await file.read()
    try:
        return save_photo(data=data, filename=file.filename or "foto", project=project, lot=lot, stage=stage, source=source if source in {"upload", "chat"} else "upload")
    except FileArchiveError as exc:
        _fail(exc)


@router.get("/photos/timeline")
def photos_timeline(project: str):
    return {"project": project, "items": photo_timeline(project)}


@router.post("/photos/picker/session")
def photos_picker(body: PickerBody):
    try:
        return picker_session(body.user_id, open_picker)
    except FileArchiveError as exc:
        _fail(exc)


@router.post("/photos/picker/import")
def photos_import(body: ImportBody):
    def _fetch(session_id: str, token: str):
        return fetch_picked_items(session_id, token)

    try:
        items = import_picked(
            user_id=body.user_id,
            session_id=body.session_id,
            project=body.project,
            lot=body.lot,
            stage=body.stage,
            fetch_items=_fetch,
        )
    except FileArchiveError as exc:
        _fail(exc)
    return {"imported": items, "picked_only": True}
