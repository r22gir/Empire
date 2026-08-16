"""PHASE 2 · F5-H43 portal button compatibility router.

The Command Center portal (Next.js) hits several `/api/v1/...` paths
that the legacy `quotes.py` and `finance.py` routers were supposed to
serve but couldn't — they read from the stale-fork JSON store
(`~/empire-repo/backend/data/quotes/*.json`) which has been empty
since the r1 canonical-path fix. The portal's PDF button 404 was
the canonical symptom.

This router re-implements the portal's URLs as thin wrappers over the
canonical `quote_service` (which reads from quotes_v2) so the portal
works without any front-end changes. Mounted at `/api/v1` AFTER the
legacy routers so FastAPI dispatches these paths in preference to
the broken legacy ones.

The 6 endpoints covered:
  1. POST   /quotes/{quote_id}/accept              → canonical mark-accepted
  2. POST   /quotes/{quote_id}/send                → canonical send_quote_email
  3. POST   /quotes/{quote_id}/pdf                 → canonical PDF gen
  4. DELETE /quotes/{quote_id}                     → canonical delete
  5. POST   /jobs/from-quote/{quote_id}           → canonical create_job
  6. POST   /finance/invoices/from-quote/{quote_id} → canonical create_invoice

For (5) and (6), the canonical `jobs_unified.create_job_from_quote`
and `finance.create_invoice_from_quote` route functions ALSO read
from stale-fork JSON. So we re-implement them here using the
canonical quote data + direct SQL inserts.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import Response

logger = logging.getLogger("max.portal_button_compat")

# Mounted at /api/v1 — no prefix so the paths match the portal URLs exactly.
# Registered AFTER the legacy routers in main.py so these dispatch in
# preference to the broken legacy implementations.
router = APIRouter(tags=["portal-button-compat"])


def _existing_or_404(quote_id: str) -> dict:
    """Load the canonical quote or raise 404."""
    from app.services.quote_service import get_quote
    q = get_quote(quote_id)
    if not q:
        raise HTTPException(404, f"Quote {quote_id} not found in canonical store")
    return q


@router.post("/quotes/{quote_id}/accept")
async def portal_accept_quote(quote_id: str):
    """Portal QuoteActions Accept button → canonical mark as accepted.

    `accept` is the portal's word for the founder signaling approval.
    We use the canonical `update_quote` to set status='accepted'.
    """
    try:
        q = _existing_or_404(quote_id)
        from app.services.quote_service import update_quote
        result = update_quote(quote_id, {"status": "accepted"})
        return {"status": "accepted", "quote": result or {"id": quote_id}}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"portal_accept_quote failed for {quote_id}: {e}")
        raise HTTPException(500, f"accept failed: {e}")


@router.post("/quotes/{quote_id}/send")
async def portal_send_quote(quote_id: str, body: Optional[dict] = Body(default=None)):
    """Portal QuoteActions Send Email button → canonical send_quote_email.

    Body: { "email": "..." } (the portal's field name). The canonical
    send_quote_email tool uses to_email. The canonical `_load_quote`
    reads stale-fork JSON which is empty for these quotes, so we
    re-implement here using canonical quote_service + canonical PDF.
    """
    try:
        q = _existing_or_404(quote_id)
        recipient = None
        if isinstance(body, dict):
            recipient = body.get("email") or body.get("to_email")
        if not recipient:
            raise HTTPException(400, "No recipient email (to) provided")

        # Generate PDF from canonical
        from app.services.quote_pdf_service import generate_quote_pdf
        pdf_bytes = generate_quote_pdf(quote_id)
        if not pdf_bytes:
            raise HTTPException(500, "Could not generate PDF for quote")

        # Persist the PDF to a temp file so the email service can attach it
        import tempfile, os
        from pathlib import Path
        tmp_pdf = Path(tempfile.gettempdir()) / f"quote_{quote_id}_portal.pdf"
        tmp_pdf.write_bytes(pdf_bytes)

        # Send via the canonical send_email tool (CC + Reply-To handled there)
        from app.services.max.tool_executor import execute_tool
        result = execute_tool({
            "tool": "send_email",
            "to": recipient,
            "subject": f"Quote {q.get('quote_number', quote_id)}",
            "body": (
                f"<p>Hi {q.get('customer_name','')},</p>"
                f"<p>Please find your quote attached.</p>"
                f"<p>— MAX</p>"
            ),
            "attachments": [str(tmp_pdf)],
        })
        if hasattr(result, "success"):
            if not result.success:
                raise HTTPException(500, result.error or "send_email failed")
            return {
                "status": "sent",
                "quote_id": quote_id,
                "result": result.result or {},
            }
        return {"status": "sent", "quote_id": quote_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"portal_send_quote failed for {quote_id}: {e}")
        raise HTTPException(500, f"send failed: {e}")


@router.post("/quotes/{quote_id}/pdf")
async def portal_post_quote_pdf(
    quote_id: str,
    skip_verification: bool = Query(default=False),
):
    """Portal QuoteActions Download PDF button (POST with skip_verification).

    The canonical PDF endpoint is GET. The portal hits POST. Returns
    the binary PDF.
    """
    try:
        q = _existing_or_404(quote_id)
        from app.services.quote_pdf_service import generate_quote_pdf
        pdf_bytes = generate_quote_pdf(quote_id)
        if not pdf_bytes:
            raise HTTPException(500, "PDF generation produced empty bytes")
        filename = f"{q.get('quote_number', quote_id)}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Skip-Verification": str(skip_verification).lower(),
            },
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")
    except Exception as e:
        logger.warning(f"portal_post_quote_pdf failed for {quote_id}: {e}")
        raise HTTPException(500, f"pdf failed: {e}")


@router.delete("/quotes/{quote_id}")
async def portal_delete_quote(quote_id: str):
    """Portal QuoteActions Delete button → canonical delete."""
    try:
        from app.services.quote_service import delete_quote
        result = delete_quote(quote_id)
        return {"status": "deleted", "id": quote_id, "result": result}
    except Exception as e:
        logger.warning(f"portal_delete_quote failed for {quote_id}: {e}")
        raise HTTPException(500, f"delete failed: {e}")


@router.post("/jobs/from-quote/{quote_id}")
async def portal_create_job_from_quote(quote_id: str):
    """Portal QuoteActions Create Job button → canonical create_job.

    The canonical route function reads stale-fork JSON. We re-implement
    here using canonical quote_service + direct canonical DB insert.
    """
    try:
        q = _existing_or_404(quote_id)
        from app.db.database import get_db

        business = q.get("business_unit") or "workroom"
        customer_name = q.get("customer_name") or ""
        customer_email = q.get("customer_email") or ""
        customer_phone = q.get("customer_phone") or ""
        grand_total = float(q.get("grand_total") or q.get("total") or 0)

        with get_db() as conn:
            # Find or create customer
            customer_id = None
            if customer_email:
                row = conn.execute(
                    "SELECT id FROM customers WHERE LOWER(email) = LOWER(?)",
                    (customer_email,),
                ).fetchone()
                if row:
                    customer_id = row[0]
            if not customer_id:
                customer_id = str(uuid.uuid4())[:8]
                conn.execute(
                    """INSERT INTO customers (id, name, email, phone, business)
                       VALUES (?, ?, ?, ?, ?)""",
                    (customer_id, customer_name, customer_email, customer_phone, business),
                )

            # Create job
            job_id = str(uuid.uuid4())[:8]
            row = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()
            job_number = f"JOB-{int(row[0]) + 1:04d}"
            title = f"Job for {customer_name or 'Unknown'} — {q.get('quote_number', quote_id)}"
            metadata = json.dumps({"source": "portal_button_compat", "quote_id": quote_id})
            conn.execute(
                """INSERT INTO jobs
                   (id, job_number, title, customer_id, quote_id, status, job_type,
                    notes, metadata, client_name, client_email, client_phone,
                    business_unit, quoted_amount, quote_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', 'fabrication', ?, ?, ?, ?, ?, ?,
                           ?, datetime('now'), datetime('now'), datetime('now'))""",
                (
                    job_id, job_number, title, customer_id, quote_id,
                    f"Auto-created from quote {q.get('quote_number', quote_id)}",
                    metadata, customer_name, customer_email, customer_phone,
                    business, grand_total,
                ),
            )
            conn.commit()
        return {
            "status": "created",
            "job_id": job_id,
            "job_number": job_number,
            "title": title,
            "customer_id": customer_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"portal_create_job_from_quote failed for {quote_id}: {e}")
        raise HTTPException(500, f"create job failed: {e}")


@router.post("/finance/invoices/from-quote/{quote_id}")
async def portal_create_invoice_from_quote(quote_id: str):
    """Portal QuoteActions Create Invoice button → canonical create_invoice.

    The canonical route function reads stale-fork JSON. We re-implement
    here using canonical quote_service + direct canonical DB insert.
    """
    try:
        q = _existing_or_404(quote_id)
        from app.db.database import get_db

        business = q.get("business_unit") or "workroom"
        customer_name = q.get("customer_name") or ""
        customer_email = q.get("customer_email") or ""
        customer_phone = q.get("customer_phone") or ""
        customer_address = q.get("customer_address") or ""

        # Build line items from canonical line_items
        line_items = []
        for it in q.get("line_items") or []:
            line_items.append({
                "description": it.get("description") or it.get("name") or "Item",
                "quantity": float(it.get("quantity") or 1),
                "unit_price": float(it.get("unit_price") or it.get("price") or 0),
                "total": float(it.get("total") or it.get("line_total") or 0),
            })
        subtotal = sum(li["total"] for li in line_items)
        tax_rate = 0.06
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)

        with get_db() as conn:
            # Find or create customer
            customer_id = None
            if customer_email:
                row = conn.execute(
                    "SELECT id FROM customers WHERE LOWER(email) = LOWER(?)",
                    (customer_email,),
                ).fetchone()
                if row:
                    customer_id = row[0]
            if not customer_id:
                customer_id = str(uuid.uuid4())[:8]
                conn.execute(
                    """INSERT INTO customers (id, name, email, phone, business)
                       VALUES (?, ?, ?, ?, ?)""",
                    (customer_id, customer_name, customer_email, customer_phone, business),
                )

            # Create invoice
            invoice_id = str(uuid.uuid4())[:8]
            row = conn.execute("SELECT COUNT(*) AS c FROM invoices").fetchone()
            invoice_number = f"INV-{int(row[0]) + 1:04d}"
            line_items_json = json.dumps(line_items)
            conn.execute(
                """INSERT INTO invoices
                   (id, invoice_number, customer_id, quote_id, status, subtotal,
                    tax_rate, tax_amount, total, line_items, terms,
                    client_name, client_email, client_phone, client_address,
                    business_unit, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, 'Net 30',
                           ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (
                    invoice_id, invoice_number, customer_id, quote_id,
                    round(subtotal, 2), tax_rate, tax_amount, total,
                    line_items_json,
                    customer_name, customer_email, customer_phone, customer_address,
                    business,
                ),
            )
            conn.commit()
        return {
            "status": "created",
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "customer_id": customer_id,
            "subtotal": round(subtotal, 2),
            "tax_amount": tax_amount,
            "total": total,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"portal_create_invoice_from_quote failed for {quote_id}: {e}")
        raise HTTPException(500, f"create invoice failed: {e}")
