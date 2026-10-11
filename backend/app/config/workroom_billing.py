"""Per-document Workroom billing identity for client PDFs and emails.

`billed_by` on invoices/quotes:
  - NULL or omitted → Empire Workroom (default, from business.json)
  - 'nelmas_workroom' → Nelma's Workroom (5124 Frolich Lane, Hyattsville, MD 20781)

Shared phone/email come from business.json for both entities.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_CONFIG_PATH = Path(__file__).parent / "business.json"

BILLED_BY_EMPIRE = "empire_workroom"
BILLED_BY_NELMA = "nelmas_workroom"
VALID_BILLED_BY = frozenset({BILLED_BY_EMPIRE, BILLED_BY_NELMA})

_NELMA_NAME = "Nelma's Workroom"
_NELMA_PHONE = "(703) 623-9203"
_EMPIRE_PHONE = "(703) 213-6484"
_SHARED_EMAIL = "workroom@empirebox.store"

# Public landing page. Client estimates, invoices, and presentations
# must not show the operator app or other internal hosts.
PUBLIC_CLIENT_HOST = "workroom.empirebox.store"
PUBLIC_CLIENT_ORIGIN = f"https://{PUBLIC_CLIENT_HOST}"
_INTERNAL_CLIENT_HOSTS = (
    "studio.empirebox.store",
    "api.empirebox.store",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
)


def _is_internal_client_url(value: str) -> bool:
    lowered = (value or "").strip().lower()
    return any(host in lowered for host in _INTERNAL_CLIENT_HOSTS)


def client_facing_website(raw: str | None) -> str:
    """Host shown on client documents. Internal app links become the public site."""
    text = (raw or "").strip()
    if not text or _is_internal_client_url(text):
        return PUBLIC_CLIENT_HOST
    return text.replace("https://", "").replace("http://", "").rstrip("/")


def client_facing_origin(raw: str | None = None) -> str:
    """Absolute public origin for a client link. Internal hosts are replaced."""
    text = (raw or "").strip()
    if not text or _is_internal_client_url(text):
        return PUBLIC_CLIENT_ORIGIN
    if text.startswith("http://") or text.startswith("https://"):
        return text.rstrip("/")
    return "https://" + text.rstrip("/")


def _env(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    return default


@dataclass(frozen=True)
class WorkroomBilling:
    billed_by: str
    name: str
    address: str
    phone: str
    email: str
    website: str
    tagline: str

    @property
    def letterhead_upper(self) -> str:
        return self.name.upper()

    @property
    def pdf_author(self) -> str:
        return self.name

    @property
    def chrome_subheader_upper(self) -> str:
        return "CUSTOM UPHOLSTERY & FABRICATION"

    @property
    def signature_phone_plain(self) -> str:
        digits = re.sub(r"\D", "", self.phone or "")
        if len(digits) == 10:
            return f"+1 {digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+1 {digits[1:4]}-{digits[4:7]}-{digits[7:]}"
        return self.phone


def _load_business_json() -> dict:
    from app.edition import is_founder_edition, workroom_business_config

    if not is_founder_edition():
        return {}
    return workroom_business_config()


def _contact_from_config(data: dict) -> tuple[str, str, str, str]:
    phone = data.get("business_phone") or _EMPIRE_PHONE
    email = data.get("business_email") or _SHARED_EMAIL
    website = client_facing_website(data.get("business_website"))
    tagline = data.get("business_tagline") or "Custom Window Treatments & Upholstery"
    return phone, email, website, tagline


def normalize_billed_by(raw: Optional[str]) -> str:
    """Map DB/API values to a canonical billed_by key (default Empire)."""
    if raw is None or not str(raw).strip():
        return BILLED_BY_EMPIRE
    key = str(raw).strip().lower().replace(" ", "_").replace("'", "")
    aliases = {
        "nelmas_workroom": BILLED_BY_NELMA,
        "nelma_workroom": BILLED_BY_NELMA,
        "nelmas": BILLED_BY_NELMA,
        "nelma": BILLED_BY_NELMA,
        "empire_workroom": BILLED_BY_EMPIRE,
        "empire": BILLED_BY_EMPIRE,
        "workroom": BILLED_BY_EMPIRE,
    }
    if key in aliases:
        return aliases[key]
    if key in VALID_BILLED_BY:
        return key
    return BILLED_BY_EMPIRE


def billed_by_for_storage(raw: Optional[str]) -> Optional[str]:
    """Persist NULL for default Empire; store nelmas_workroom when selected."""
    return BILLED_BY_NELMA if normalize_billed_by(raw) == BILLED_BY_NELMA else None


def founder_requests_nelmas_billing(text: str) -> bool:
    """True when founder language selects Nelma's Workroom billing."""
    if not text:
        return False
    t = text.lower()
    if "nelma" not in t:
        return False
    triggers = (
        "bill as nelma",
        "billed by nelma",
        "nelma's workroom",
        "nelmas workroom",
        "bill under nelma",
        "invoice as nelma",
        "quote as nelma",
    )
    return any(p in t for p in triggers) or (
        "nelma" in t and ("bill" in t or "billed" in t or "workroom" in t)
    )


def resolve_billing(billed_by: Optional[str] = None) -> WorkroomBilling:
    from app.edition import assistant_name, is_founder_edition

    if not is_founder_edition():
        return WorkroomBilling(
            billed_by="instance",
            name=assistant_name(),
            address="",
            phone="",
            email="",
            website="",
            tagline="",
        )
    key = normalize_billed_by(billed_by)
    data = _load_business_json()
    _phone, email, website, tagline = _contact_from_config(data)
    email = _SHARED_EMAIL
    address = _env(
        "BILLING_ENTITY_ADDRESS",
        data.get("business_address") or "5124 Frolich Ln, Hyattsville, MD 20781",
    )
    if key == BILLED_BY_NELMA:
        return WorkroomBilling(
            billed_by=BILLED_BY_NELMA,
            name=_NELMA_NAME,
            address=address,
            phone=_NELMA_PHONE,
            email=email,
            website=website,
            tagline=tagline,
        )
    empire_name = _env("BILLING_ENTITY", data.get("business_name") or "Empire Workroom")
    empire_address = address
    phone = _EMPIRE_PHONE
    return WorkroomBilling(
        billed_by=BILLED_BY_EMPIRE,
        name=empire_name,
        address=empire_address,
        phone=phone,
        email=email,
        website=website,
        tagline=tagline,
    )


def get_workroom_billing(billed_by: Optional[str] = None) -> WorkroomBilling:
    """Resolve billing for a document (default Empire Workroom)."""
    return resolve_billing(billed_by)


def reload_workroom_billing(billed_by: Optional[str] = None) -> WorkroomBilling:
    return resolve_billing(billed_by)


def ensure_billed_by_schema(conn) -> None:
    """Additive nullable billed_by column — does not backfill or alter rows."""
    for table in ("quotes_v2", "invoices"):
        try:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        except Exception:
            continue
        if "billed_by" not in cols:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN billed_by TEXT")
            except Exception:
                pass
