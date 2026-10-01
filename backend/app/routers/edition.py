"""Edition manifest, allowlist admin, and Nueva empresa."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from fastapi.responses import JSONResponse, RedirectResponse

from app.edition import (
    assistant_name,
    edition_manifest,
    ensure_assistant_files,
    greeting,
    is_amp,
)
from app.services import amp_access, amp_allowlist, amp_businesses

router = APIRouter(tags=["edition"])


class AllowlistBody(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    role: str = "member"


class BusinessCreate(BaseModel):
    name: str
    industry: str = ""
    description: str = ""
    template: Optional[str] = None


class ContactCreate(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    fields: Optional[dict] = None


def _caller(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Verified AMP identity only. Client identity headers are ignored."""
    email = getattr(request.state, "amp_email", None)
    return email, None


def _require_admin(request: Request) -> None:
    email, username = _caller(request)
    role = amp_allowlist.entry_role(email=email, username=username)
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Sin acceso. Se requiere una cuenta administrador.")


class LoginRequestBody(BaseModel):
    email: str


class LoginVerifyBody(BaseModel):
    email: str
    code: str


_LOGIN_GENERIC = {
    "ok": True,
    "detail": (
        "Si el correo está autorizado, enviamos un código de acceso. "
        "Si no llega, un administrador puede generar un enlace."
    ),
}


@router.post("/amp/auth/request")
async def request_login(body: LoginRequestBody):
    """Ask for a one-time code. Same response whether or not the email is listed.

    Does not send mail unless SMTP is configured, and never returns the code.
    """
    if not is_amp():
        raise HTTPException(404, "El acceso por correo solo aplica a la edición AMP")
    try:
        amp_access.jwt_secret()
    except amp_access.AmpAccessError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    amp_access.request_login_email(body.email)
    return _LOGIN_GENERIC


@router.post("/amp/auth/verify")
async def verify_login(body: LoginVerifyBody):
    if not is_amp():
        raise HTTPException(404, "El acceso por correo solo aplica a la edición AMP")
    email = amp_access.redeem_code(body.email, body.code)
    if not email:
        raise HTTPException(status_code=403, detail="Código inválido o vencido.")
    response = JSONResponse({"ok": True, "email": email})
    amp_access.apply_session_cookie(response, email)
    return response


@router.get("/amp/auth/magic")
async def magic_login(token: str = ""):
    if not is_amp():
        raise HTTPException(404, "El acceso por correo solo aplica a la edición AMP")
    email = amp_access.redeem_magic_token(token)
    if not email:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Enlace inválido o vencido.",
                "code": "sin_acceso",
            },
        )
    response = RedirectResponse(url=amp_access.login_redirect_path(), status_code=303)
    amp_access.apply_session_cookie(response, email)
    return response


@router.post("/amp/auth/logout")
async def logout():
    response = JSONResponse({"ok": True})
    amp_access.clear_session_cookie(response)
    return response


@router.get("/edition")
async def get_edition():
    payload = edition_manifest()
    payload["greeting"] = greeting()
    if is_amp():
        try:
            files = ensure_assistant_files()
            payload["assistant"]["memory_path"] = files["memory_path"]
            payload["assistant"]["history_path"] = files["history_path"]
            payload["assistant"]["settings_path"] = files["settings_path"]
        except Exception as exc:
            payload["assistant"]["storage_error"] = str(exc)
    return payload


@router.get("/amp/allowlist")
async def get_allowlist(request: Request):
    if not is_amp():
        raise HTTPException(404, "Allowlist solo aplica a la edición AMP")
    _require_admin(request)
    return {"entries": amp_allowlist.list_entries()}


@router.post("/amp/allowlist")
async def post_allowlist(body: AllowlistBody, request: Request):
    if not is_amp():
        raise HTTPException(404, "Allowlist solo aplica a la edición AMP")
    _require_admin(request)
    try:
        entry = amp_allowlist.add_entry(email=body.email, username=body.username, role=body.role)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return entry


@router.delete("/amp/allowlist")
async def delete_allowlist(request: Request, email: Optional[str] = None, username: Optional[str] = None):
    if not is_amp():
        raise HTTPException(404, "Allowlist solo aplica a la edición AMP")
    _require_admin(request)
    try:
        removed = amp_allowlist.remove_entry(email=email, username=username)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"removed": removed}


@router.get("/businesses/templates")
async def get_templates():
    if not is_amp():
        raise HTTPException(404, "Plantillas solo aplican a la edición AMP")
    return {"templates": amp_businesses.list_templates()}


@router.get("/businesses")
async def get_businesses():
    if not is_amp():
        raise HTTPException(404, "Empresas solo aplican a la edición AMP")
    return {"businesses": amp_businesses.list_businesses()}


@router.post("/businesses")
async def post_business(body: BusinessCreate):
    if not is_amp():
        raise HTTPException(404, "Nueva empresa solo aplica a la edición AMP")
    try:
        created = amp_businesses.create_business(
            name=body.name,
            industry=body.industry,
            description=body.description,
            template=body.template,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return created


@router.get("/businesses/{slug}")
async def get_business(slug: str):
    if not is_amp():
        raise HTTPException(404, "Empresas solo aplican a la edición AMP")
    try:
        return amp_businesses.workspace_summary(slug)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/businesses/{slug}/contacts")
async def post_contact(slug: str, body: ContactCreate):
    if not is_amp():
        raise HTTPException(404, "CRM de empresa solo aplica a la edición AMP")
    try:
        return amp_businesses.add_contact(
            slug, name=body.name, email=body.email, phone=body.phone, fields=body.fields
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/businesses/{slug}/contacts")
async def get_contacts(slug: str):
    if not is_amp():
        raise HTTPException(404, "CRM de empresa solo aplica a la edición AMP")
    try:
        return {"contacts": amp_businesses.list_contacts(slug)}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/businesses/{slug}/nota")
async def post_note(slug: str, title: str = "Nota"):
    """Generated document signed by this instance's assistant (Max-e)."""
    if not is_amp():
        raise HTTPException(404, "Documentos solo aplican a la edición AMP")
    try:
        path = amp_businesses.write_generated_note(
            slug,
            title,
            "Resumen operativo. Los precios quedan sin definir hasta que se confirmen.",
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"path": str(path), "assistant": assistant_name()}
