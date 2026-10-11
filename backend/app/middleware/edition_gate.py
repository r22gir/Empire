"""Request gate for the AMP edition.

No-op when EMPIRE_EDITION is unset or workroom, so Workroom routes,
allowlists, and module visibility stay as they are.

On the AMP edition, identity comes only from a verified Cloudflare Access
JWT or the AMP login session. ``X-User-Email`` and the other client-supplied
identity headers are stripped before the request is handled.
"""
from __future__ import annotations

from fastapi.responses import JSONResponse

from app.edition import (
    access_exempt,
    disabled_module_for_path,
    is_family_edition,
    reset_active_business,
    set_active_business,
    sin_acceso_body,
)
from app.middleware.family_scrub import scrub_family_response
from app.services import amp_allowlist
from app.services.amp_access import (
    apply_session_cookie,
    resolve_request_email,
    strip_client_identity_headers,
)


def _drop_cached_headers(request) -> None:
    """Starlette caches ``request.headers``. Rebuild it after the strip."""
    request.__dict__.pop("headers", None)
    request.__dict__.pop("_headers", None)
    request.scope.pop("headers_raw", None)


async def amp_access_middleware(request, call_next):
    if not is_family_edition():
        return await call_next(request)

    email, via = resolve_request_email(request.scope)
    strip_client_identity_headers(request.scope)
    _drop_cached_headers(request)
    request.state.amp_email = email
    request.state.amp_auth_via = via

    blocked = disabled_module_for_path(request.url.path)
    if blocked:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Módulo no disponible en esta edición.",
                "module": blocked,
            },
        )

    slug = request.headers.get("x-empire-business") or "amp"
    token = set_active_business(slug)
    try:
        if request.method.upper() == "OPTIONS":
            return await call_next(request)
        if access_exempt(request.method, request.url.path):
            return await scrub_family_response(request, await call_next(request))
        if not email or not amp_allowlist.is_allowed(email=email):
            return JSONResponse(status_code=403, content=sin_acceso_body())
        response = await call_next(request)
        if via == "session" and email and amp_allowlist.entry_role(email=email) == "owner":
            apply_session_cookie(response, email)
        return await scrub_family_response(request, response)
    finally:
        reset_active_business(token)
