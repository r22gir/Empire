"""Inbound Chief e replies for family-edition Pedir ayuda tickets.

POST /api/v1/support/tickets/{ticket_id}/reply is secret-gated
(SUPPORT_REPLY_SECRET). The family session gate must not block it —
``support_reply_exempt()`` keeps the path reachable with only the shared
secret, whether or not PR #217's login-gate changes land. The path lives
under /api/v1/* because the Cloudflare edge only exposes that prefix.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.edition import is_family_edition

router = APIRouter(tags=["support"])


class SupportReplyBody(BaseModel):
    body: str = Field(min_length=1)
    author: str = "Chief e"


def _secret_or_401(request: Request, authorization: str | None) -> None:
    from app.services.support_bridge import verify_reply_secret

    extra = request.headers.get("x-support-reply-secret")
    if verify_reply_secret(authorization, extra):
        return
    raise HTTPException(status_code=401, detail="no autorizado")


@router.post("/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    payload: SupportReplyBody,
    request: Request,
    authorization: str | None = Header(default=None),
):
    from app.services.support_bridge import add_inbound_reply

    _secret_or_401(request, authorization)
    if not is_family_edition():
        raise HTTPException(status_code=404, detail="ticket no encontrado")
    try:
        ticket = add_inbound_reply(ticket_id, payload.body, author=payload.author)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "ticket": ticket}
