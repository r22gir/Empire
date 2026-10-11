"""Family-edition first-login welcome. 404 on Workroom / founder Max."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.edition import EditionPathError, is_family_edition
from app.services import family_welcome

router = APIRouter(tags=["family-welcome"])


def _amp_email(request: Request) -> str:
    email = getattr(request.state, "amp_email", None)
    if not email:
        raise HTTPException(status_code=403, detail="Sin acceso. Entra con tu correo autorizado.")
    return str(email)


@router.get("/welcome")
async def get_welcome(request: Request):
    if not is_family_edition():
        raise HTTPException(status_code=404, detail="La bienvenida solo aplica a las ediciones familiares")
    email = _amp_email(request)
    try:
        return family_welcome.public_state(email)
    except EditionPathError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/welcome/seen")
async def post_welcome_seen(request: Request):
    if not is_family_edition():
        raise HTTPException(status_code=404, detail="La bienvenida solo aplica a las ediciones familiares")
    email = _amp_email(request)
    try:
        entry = family_welcome.mark_seen(email)
    except EditionPathError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "seen": True, "seen_at": entry.get("seen_at")}
