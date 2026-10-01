"""Request gate for the AMP edition.

No-op when EMPIRE_EDITION is unset or workroom, so Workroom routes,
allowlists, and module visibility stay as they are.
"""
from __future__ import annotations

import os

from fastapi.responses import JSONResponse

from app.edition import (
    access_exempt,
    disabled_module_for_path,
    is_amp,
    reset_active_business,
    set_active_business,
    sin_acceso_body,
)
from app.services import amp_allowlist


def _identity(request) -> tuple[str | None, str | None]:
    email = request.headers.get("x-user-email")
    username = request.headers.get("x-user-name")
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            from jose import jwt
            secret = os.getenv("AMP_JWT_SECRET", "empire-amp-secret-change-in-prod")
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            email = email or payload.get("email")
        except Exception:
            pass
    return email, username


async def amp_access_middleware(request, call_next):
    if not is_amp():
        return await call_next(request)

    blocked = disabled_module_for_path(request.url.path)
    if blocked:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Módulo no disponible en la edición AMP.",
                "module": blocked,
            },
        )

    slug = request.headers.get("x-empire-business") or "amp"
    token = set_active_business(slug)
    try:
        if access_exempt(request.method, request.url.path):
            return await call_next(request)
        email, username = _identity(request)
        if not amp_allowlist.is_allowed(email=email, username=username):
            return JSONResponse(status_code=403, content=sin_acceso_body())
        return await call_next(request)
    finally:
        reset_active_business(token)
