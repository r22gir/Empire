"""Shared MiniMax meter + H3 approval API.

Founder / personal Max: full per-edition usage and the video queue.
Family editions: own remaining caps only. They cannot read sibling usage
or approve clips.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.edition import edition_name, is_family_edition, is_founder_edition

router = APIRouter(prefix="/minimax-meter", tags=["minimax-meter"])


class ImageBody(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    aspect_ratio: str = "1:1"


class VideoDraftBody(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    duration: int = 5


class ConfirmBody(BaseModel):
    explicit_yes: bool = False


def _founder_or_403() -> None:
    if is_family_edition() or not is_founder_edition():
        raise HTTPException(
            status_code=403,
            detail="El medidor MiniMax completo solo lo ve el Max personal de Rafael. / Full MiniMax meter is only for Rafael's personal Max.",
        )


def _family_or_founder() -> str:
    return edition_name()


def _require_admin(request: Request) -> None:
    if is_family_edition():
        from app.services import amp_allowlist

        email = getattr(request.state, "amp_email", None)
        role = amp_allowlist.entry_role(email=email, username=None)
        if role not in {"owner", "admin"}:
            raise HTTPException(status_code=403, detail="Sin acceso. Se requiere el dueño de esta edición.")


@router.get("/usage")
async def founder_usage():
    """Rafael-only: per-edition usage vs caps + plan bar."""
    _founder_or_403()
    from app.services.minimax_meter import founder_summary

    return founder_summary()


@router.get("/me")
async def my_usage(request: Request):
    """This edition's remaining image/TTS/text share. No sibling totals."""
    if is_family_edition():
        _require_admin(request)
    from app.services.minimax_meter import edition_public_summary

    return edition_public_summary(_family_or_founder())


@router.post("/image")
async def generate_image(body: ImageBody, request: Request):
    """image-01 through the meter. Family owners/admins only; prompts sanitized."""
    _require_admin(request)
    from app.services.minimax_media import generate_image

    result = await generate_image(body.prompt, aspect_ratio=body.aspect_ratio)
    if not result.get("success"):
        raise HTTPException(status_code=429 if result.get("blocked") else 400, detail=result.get("error"))
    return result


@router.post("/video/drafts")
async def create_video_draft(body: VideoDraftBody, request: Request):
    """Draft only. Family owners/admins only. Generation is founder UI."""
    _require_admin(request)
    from app.services.minimax_prompts import PromptRejected
    from app.services.minimax_video import create_draft

    try:
        return create_draft(body.prompt, duration=body.duration)
    except PromptRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/video/queue")
async def video_queue(status: Optional[str] = None):
    _founder_or_403()
    from app.services.minimax_video import list_queue

    return {"items": list_queue(status=status)}


@router.post("/video/{approval_id}/approve")
async def approve_video(approval_id: str, request: Request, body: ConfirmBody | None = None):
    _founder_or_403()
    from app.services.minimax_video import approve, explicit_yes

    flag = bool(body and body.explicit_yes)
    try:
        return approve(approval_id, confirmed=explicit_yes(request, flag))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/video/{approval_id}/reject")
async def reject_video(approval_id: str, request: Request, body: ConfirmBody | None = None):
    _founder_or_403()
    from app.services.minimax_video import explicit_yes, reject

    try:
        return reject(approval_id, confirmed=explicit_yes(request, bool(body and body.explicit_yes)))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/video/{approval_id}/generate")
async def generate_video(approval_id: str, request: Request, body: ConfirmBody | None = None):
    _founder_or_403()
    from app.services.minimax_video import explicit_yes, generate_approved_clip

    if not explicit_yes(request, bool(body and body.explicit_yes)):
        raise HTTPException(
            status_code=403,
            detail="Rafael debe pulsar Aprobar otra vez para generar. / Rafael must confirm again to generate.",
        )
    try:
        return await generate_approved_clip(approval_id, caller_edition=edition_name())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
