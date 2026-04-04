"""
Empire Client Portal — Public + founder endpoints for customer portal links.
Customers can view quotes, production status, invoices, and approve quotes
via secure token-based URLs.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.client_portal_service import (
    init_portal_tables,
    generate_portal_link,
    get_portal_data,
    list_portal_links,
    revoke_portal_link,
    approve_quote_via_portal,
)

# ── Init table on module load ───────────────────────────────────────
init_portal_tables()

router = APIRouter(prefix="/portal", tags=["client-portal"])


# ── Schemas ─────────────────────────────────────────────────────────

class GenerateLinkRequest(BaseModel):
    customer_id: str
    job_id: Optional[str] = None
    quote_id: Optional[str] = None


class SendLinkRequest(BaseModel):
    customer_id: str
    job_id: Optional[str] = None
    quote_id: Optional[str] = None
    email: Optional[str] = None


# ── Founder Endpoints (static paths MUST come before /{token}) ─────

@router.post("/generate")
def portal_generate_link(body: GenerateLinkRequest):
    """Founder: generate a new portal link for a customer."""
    try:
        result = generate_portal_link(
            customer_id=body.customer_id,
            job_id=body.job_id,
            quote_id=body.quote_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate portal link: {e}")


@router.post("/send")
def portal_send_link(body: SendLinkRequest):
    """Founder: generate portal link + placeholder for email delivery."""
    try:
        result = generate_portal_link(
            customer_id=body.customer_id,
            job_id=body.job_id,
            quote_id=body.quote_id,
        )
        # TODO: wire up email delivery (SendGrid / SES / Telegram)
        result["email_sent"] = False
        result["message"] = "Portal link generated. Email delivery not yet configured."
        if body.email:
            result["email_target"] = body.email
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate portal link: {e}")


@router.get("/links", name="portal_list_links")
def portal_list_links(active_only: bool = True):
    """Founder: list all portal links."""
    return list_portal_links(active_only=active_only)


# ── Public Endpoints (token-based — must come after static paths) ──

@router.get("/{token}")
def portal_view(token: str):
    """Public: retrieve all portal data for a customer token."""
    data = get_portal_data(token)
    if not data.get("valid"):
        raise HTTPException(status_code=403, detail=data.get("error", "Access denied"))
    return data


@router.post("/{token}/approve")
def portal_approve_quote(token: str):
    """Public: customer approves their quote via portal link."""
    result = approve_quote_via_portal(token)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Approval failed"))
    return result


@router.get("/{token}/pdf")
def portal_download_pdf(token: str):
    """Public: download quote PDF through the portal."""
    data = get_portal_data(token)
    if not data.get("valid"):
        raise HTTPException(status_code=403, detail=data.get("error", "Access denied"))

    quote = data.get("quote")
    if not quote:
        raise HTTPException(status_code=404, detail="No quote associated with this portal link")

    try:
        from app.services.quote_pdf_service import generate_quote_pdf
        from fastapi.responses import Response

        pdf_bytes = generate_quote_pdf(quote["id"])
        filename = f"{quote.get('quote_number', quote['id'])}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quote not found for PDF generation")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


@router.delete("/{token}/revoke")
def portal_revoke_link(token: str):
    """Founder: revoke a portal link."""
    revoked = revoke_portal_link(token)
    if not revoked:
        raise HTTPException(status_code=404, detail="Portal link not found")
    return {"success": True, "message": "Portal link revoked"}
