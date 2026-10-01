"""Client-facing billing identity for Workroom invoices, quotes, and estimates.

Override via environment:
  BILLING_ENTITY          — legal/display name (default Nelma's Workroom)
  BILLING_ENTITY_ADDRESS  — full mailing address on PDFs/emails
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "business.json"

_DEFAULT_NAME = "Nelma's Workroom"
_DEFAULT_ADDRESS = "5124 Frolich Lane, Hyattsville, MD 20781"
_DEFAULT_PHONE = "(703) 213-6484"
_DEFAULT_EMAIL = "workroom@empirebox.store"
_DEFAULT_WEBSITE = "empirebox.store"
_DEFAULT_TAGLINE = "Custom Window Treatments & Upholstery"


def _env(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    return default


@dataclass(frozen=True)
class WorkroomBilling:
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
        """House email signature line (E.164-style when possible)."""
        digits = re.sub(r"\D", "", self.phone or "")
        if len(digits) == 10:
            return f"+1 {digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+1 {digits[1:4]}-{digits[4:7]}-{digits[7:]}"
        return self.phone


@lru_cache(maxsize=1)
def get_workroom_billing() -> WorkroomBilling:
    phone = _DEFAULT_PHONE
    email = _DEFAULT_EMAIL
    website = _DEFAULT_WEBSITE
    tagline = _DEFAULT_TAGLINE
    if _CONFIG_PATH.is_file():
        try:
            data = json.loads(_CONFIG_PATH.read_text())
            phone = data.get("business_phone") or phone
            email = data.get("business_email") or email
            raw_site = data.get("business_website") or website
            website = (
                raw_site.replace("https://", "").replace("http://", "").rstrip("/")
            )
            tagline = data.get("business_tagline") or tagline
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return WorkroomBilling(
        name=_env("BILLING_ENTITY", _DEFAULT_NAME),
        address=_env("BILLING_ENTITY_ADDRESS", _DEFAULT_ADDRESS),
        phone=phone,
        email=email,
        website=website,
        tagline=tagline,
    )


def reload_workroom_billing() -> WorkroomBilling:
    get_workroom_billing.cache_clear()
    return get_workroom_billing()
