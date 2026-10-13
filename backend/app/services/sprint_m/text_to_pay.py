"""Draft SMS/WhatsApp with a non-expiring payment link. Owner approves; Max never sends."""

from __future__ import annotations

import os
from typing import Literal

from app.services.sprint_m import drafts as draft_service
from app.services.sprint_m.work_orders import get_organizer_job

Provider = Literal["stripe", "square"]

WORKROOM_ALIASES = {"workroom", "empire workroom", "empire", "studio"}
NELMAS_ALIASES = {"nelmas", "nelma", "nelma's", "nelmas workroom", "square"}


def resolve_provider(business_unit: str | None, explicit: str | None = None) -> Provider:
    if explicit:
        value = explicit.strip().lower()
        if value in {"stripe", "empire", "workroom"}:
            return "stripe"
        if value in {"square", "nelmas", "nelma"}:
            return "square"
    unit = (business_unit or "workroom").strip().lower()
    if unit in NELMAS_ALIASES:
        return "square"
    return "stripe"


def _configured(provider: Provider) -> bool:
    if provider == "stripe":
        return bool(os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_PAYMENT_LINK_WORKROOM"))
    return bool(os.getenv("SQUARE_ACCESS_TOKEN") or os.getenv("SQUARE_PAYMENT_LINK_NELMAS"))


def build_payment_link(job: dict, provider: Provider, amount: float) -> dict:
    """Return a non-expiring link descriptor. Does not call live processors from tests."""
    job_number = job.get("job_number") or job["id"]
    configured = _configured(provider)
    if provider == "stripe":
        preset = os.getenv("STRIPE_PAYMENT_LINK_WORKROOM")
        url = preset or f"https://pay.empirebox.store/pl/{job['id']}"
        brand = "Empire Workroom"
        processor = "stripe_payment_link"
    else:
        preset = os.getenv("SQUARE_PAYMENT_LINK_NELMAS")
        url = preset or f"https://squareup.com/pay/nelmas/{job['id']}"
        brand = "Nelma's"
        processor = "square_payment_link"
    return {
        "provider": provider,
        "processor": processor,
        "brand": brand,
        "url": url,
        "amount": amount,
        "expires_at": None,
        "non_expiring": True,
        "configured": configured,
        "job_number": job_number,
        "note": "Draft link only. Live processor is not charged until the owner sends the approved draft.",
    }


def create_text_to_pay_draft(
    job_id: str,
    *,
    channel: str = "sms",
    provider: str | None = None,
    amount: float | None = None,
    to_address: str | None = None,
    actor: str = "owner",
) -> dict:
    if channel not in {"sms", "whatsapp"}:
        raise ValueError("text-to-pay channel must be sms or whatsapp")
    job = get_organizer_job(job_id)
    resolved = resolve_provider(job.get("business_unit"), provider)
    pay_amount = float(amount if amount is not None else job.get("quoted_amount") or 0)
    link = build_payment_link(job, resolved, pay_amount)
    body = (
        f"Hi {job.get('customer_name') or 'there'} — payment for {link['job_number']} "
        f"(${pay_amount:,.2f}) via {link['brand']}: {link['url']}\n"
        "This link does not expire.\n"
        "DRAFT ONLY. Max did not send this. Owner approval required."
    )
    draft = draft_service.create_draft(
        channel=channel,
        body=body,
        job_id=job_id,
        customer_id=job.get("customer_id"),
        to_address=to_address,
        subject=None,
        source="text_to_pay",
        metadata={"payment_link": link, "max_sends": False},
        actor=actor,
    )
    return {"draft": draft, "payment_link": link, "max_sends_to_clients": False}
