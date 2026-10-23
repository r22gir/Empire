"""Resolve invoice branding / Square / Outlook from business config.

Never hardcode Nelma's Workroom or Empire. Tests inject a profile.
Live resolution reads company-setup brands + env var *names* (never values
in logs). Tokens stay in the environment.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class InvoiceBusiness:
    id: str
    name: str
    tagline: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    website: str = ""
    billed_by: str = ""
    square_location_id: str = ""
    square_token_env: str = "SQUARE_ACCESS_TOKEN"
    square_location_env: str = "SQUARE_LOCATION_ID"
    outlook_mailbox: str = ""
    outlook_token_env: str = "OUTLOOK_TOKEN_PATH"
    accent: str = "#b8912f"

    def public_dict(self) -> dict:
        """Safe for tool results and logs — no tokens, no env values."""
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "website": self.website,
            "billed_by": self.billed_by or self.id,
            "square_location_env": self.square_location_env,
            "square_token_env": self.square_token_env,
            "outlook_mailbox": self.outlook_mailbox,
        }

    def square_token(self) -> str:
        return (os.getenv(self.square_token_env) or "").strip()

    def square_location(self) -> str:
        return (self.square_location_id or os.getenv(self.square_location_env) or "").strip()


def _slug(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (raw or "").strip().lower()).strip("_")


def _brand_id(brand: dict) -> str:
    return _slug(str(brand.get("id") or brand.get("name") or brand.get("dba") or ""))


def _from_brand(brand: dict, contact: dict | None = None, payments: dict | None = None,
                channels: dict | None = None) -> InvoiceBusiness:
    contact = contact or {}
    payments = payments or {}
    channels = channels or {}
    bid = _brand_id(brand) or "business"
    env_key = bid.upper()
    email = (
        brand.get("email")
        or contact.get("email")
        or contact.get("business_email")
        or (channels.get("email") if isinstance(channels.get("email"), str) else "")
        or ""
    )
    return InvoiceBusiness(
        id=bid,
        name=str(brand.get("name") or brand.get("dba") or brand.get("legal_name") or "Business"),
        tagline=str(brand.get("tagline") or brand.get("business_tagline") or contact.get("tagline") or ""),
        phone=str(brand.get("phone") or contact.get("phone") or contact.get("business_phone") or ""),
        email=str(email),
        address=str(brand.get("address") or contact.get("address") or contact.get("business_address") or ""),
        website=str(brand.get("website") or contact.get("website") or contact.get("business_website") or ""),
        billed_by=str(brand.get("id") or bid),
        square_location_id=str(
            brand.get("square_location_id")
            or (payments.get("square") or {}).get("location_id")
            or ""
        ),
        square_token_env=str(brand.get("square_token_env") or f"SQUARE_ACCESS_TOKEN_{env_key}"),
        square_location_env=str(brand.get("square_location_env") or f"SQUARE_LOCATION_ID_{env_key}"),
        outlook_mailbox=str(
            brand.get("outlook_mailbox")
            or (channels.get("outlook") if isinstance(channels.get("outlook"), str) else "")
            or email
        ),
        outlook_token_env=str(brand.get("outlook_token_env") or f"OUTLOOK_TOKEN_PATH_{env_key}"),
        accent=str((brand.get("branding") or {}).get("primary") or brand.get("accent") or "#b8912f"),
    )


def _company_setup_data() -> dict:
    try:
        from app.services.company_setup.store import load_merged
        data = load_merged()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _brands_from_setup(data: dict) -> list[dict]:
    identity = data.get("identity") if isinstance(data.get("identity"), dict) else {}
    raw = data.get("brands") or identity.get("brands") or []
    return [b for b in raw if isinstance(b, dict)]


def _match_brand(brands: list[dict], key: str) -> Optional[dict]:
    want = _slug(key)
    if not want:
        return None
    for b in brands:
        hay = {_brand_id(b), _slug(str(b.get("name") or "")), _slug(str(b.get("dba") or ""))}
        if want in hay or want in "".join(hay):
            return b
        if want.replace("nelma", "nelmas") in hay or "nelma" in want and "nelma" in _brand_id(b):
            return b
    return None


def resolve_invoice_business(
    invoice: dict | None = None,
    *,
    explicit: InvoiceBusiness | dict | None = None,
    setup: dict | None = None,
) -> InvoiceBusiness:
    """Pick the business for this invoice from config, not a hardcoded shop."""
    if isinstance(explicit, InvoiceBusiness):
        return explicit
    if isinstance(explicit, dict) and (explicit.get("id") or explicit.get("name")):
        return _from_brand(explicit)

    invoice = invoice or {}
    meta = invoice.get("metadata") if isinstance(invoice.get("metadata"), dict) else {}
    key = (
        invoice.get("business_id")
        or invoice.get("billed_by")
        or invoice.get("business")
        or invoice.get("business_name")
        or invoice.get("business_unit")
        or meta.get("billed_by")
        or meta.get("business_name")
        or ""
    )
    data = setup if isinstance(setup, dict) else _company_setup_data()
    brands = _brands_from_setup(data)
    contact = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    payments = data.get("payments") if isinstance(data.get("payments"), dict) else {}
    channels = data.get("channels") if isinstance(data.get("channels"), dict) else {}

    brand = _match_brand(brands, str(key)) if key else None
    if brand is None:
        brand = next((b for b in brands if b.get("is_default")), brands[0] if brands else None)

    if brand:
        biz = _from_brand(brand, contact, payments, channels)
        # Invoice-level contact overrides (tests / produce payload), still not hardcoded.
        return InvoiceBusiness(
            id=biz.id,
            name=str(invoice.get("business_name") or biz.name),
            tagline=str(invoice.get("business_tagline") or biz.tagline),
            phone=str(invoice.get("business_phone") or biz.phone),
            email=str(invoice.get("business_email") or biz.email),
            address=str(invoice.get("business_address") or biz.address),
            website=str(invoice.get("business_website") or biz.website),
            billed_by=str(invoice.get("billed_by") or biz.billed_by),
            square_location_id=biz.square_location_id,
            square_token_env=biz.square_token_env,
            square_location_env=biz.square_location_env,
            outlook_mailbox=str(invoice.get("outlook_mailbox") or biz.outlook_mailbox),
            outlook_token_env=biz.outlook_token_env,
            accent=biz.accent,
        )

    # Last resort: billing helper (already config-driven) — still not a Workroom constant.
    try:
        from app.config.workroom_billing import resolve_quote_billing
        bill = resolve_quote_billing(invoice)
        bid = _slug(bill.billed_by or bill.name) or "business"
        env_key = bid.upper()
        return InvoiceBusiness(
            id=bid,
            name=bill.name,
            tagline=bill.tagline,
            phone=bill.phone,
            email=bill.email,
            address=bill.address,
            website=bill.website,
            billed_by=bill.billed_by,
            square_token_env=f"SQUARE_ACCESS_TOKEN_{env_key}",
            square_location_env=f"SQUARE_LOCATION_ID_{env_key}",
            outlook_mailbox=bill.email,
            outlook_token_env=f"OUTLOOK_TOKEN_PATH_{env_key}",
        )
    except Exception:
        return InvoiceBusiness(id="business", name=str(invoice.get("business_name") or "Business"))
