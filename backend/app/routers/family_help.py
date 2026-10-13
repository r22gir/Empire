"""
Family editions — 'Pedir ayuda a Max'.

Each edition posts a request into its isolated family-help store.
SupportForge opens a ticket with a proposed action (adjust / fix / create).
The founder may see only the request itself. Nothing is built automatically.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.family_help_store import FAMILY_EDITIONS, FamilyHelpStore

router = APIRouter()
store = FamilyHelpStore()


class PedirAyudaRequest(BaseModel):
    edition: str = Field(..., description="Family edition id: amp, maxine, minimax-meter")
    subject: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1)
    requester_name: Optional[str] = Field(None, max_length=200)


@router.get("/editions")
def list_editions():
    return {"editions": list(FAMILY_EDITIONS), "isolated": True, "auto_build": False}


@router.post("/pedir-ayuda", status_code=status.HTTP_201_CREATED)
def pedir_ayuda(body: PedirAyudaRequest):
    try:
        return store.submit(
            edition_id=body.edition,
            subject=body.subject,
            message=body.message,
            requester_name=body.requester_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/requests")
def list_requests(
    edition: Optional[str] = Query(
        None,
        description="Edition scope. Omit for founder view of every edition's requests.",
    ),
    founder_view: bool = Query(True),
):
    try:
        if edition:
            requests = store.list_for_edition(edition)
        else:
            requests = store.list_for_founder() if founder_view else []
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "requests": requests,
        "total": len(requests),
        "founder_sees": "requests_only",
        "auto_build": False,
    }


@router.get("/requests/{request_id}")
def get_request(request_id: str, edition: str = Query(...)):
    try:
        request = store.get(edition, request_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return request
