"""Client-facing invoice copy: fractions only, V###-Color fabric, no brands."""
from __future__ import annotations

import re
from typing import Any

from app.services.invoice_pdf_service import client_visible_line_description

_V_CODE = re.compile(r"\b([VFL]\d{3,}-[A-Za-z][A-Za-z0-9 \-]*)\b")
_SKU_ONLY = re.compile(r"\b([VFL]\d{3,})(?!-[A-Za-z])\b", re.IGNORECASE)
_BRAND_RE = re.compile(
    r"\b(kravet|fabricut|schumacher|brunschwig|lee\s*jofa|pindler|osborne\s*(?:little)?"
    r"|robert\s*allen|designers?\s*guild|wholesaler|supplier|vendor|mill)\b",
    re.IGNORECASE,
)
_DEC_INCH = re.compile(r"(\d+\.\d+)\s*(\"|in(?:ch(?:es)?)?|''|”)", re.IGNORECASE)


def _fractions(text: str) -> str:
    try:
        from app.services.estimates.mclean_estimate_pdf import inches_to_fractions
        from app.services.pricing.dimensions import plain_fractions
        return plain_fractions(inches_to_fractions(text or ""))
    except Exception:
        from app.services.pricing.dimensions import plain_fractions
        return plain_fractions(text or "")


def _strip_brands(text: str, fabric_code: str = "") -> str:
    t = text or ""
    t = _BRAND_RE.sub("", t)
    t = _SKU_ONLY.sub("", t)  # supplier SKUs like V639 — never on client docs
    t = re.sub(r"\s{2,}", " ", t).strip(" ,;–—-")
    if fabric_code:
        color = fabric_code.split("-", 1)[-1]
        if color and t.lower().startswith(color.lower()):
            t = t[len(color):].strip(" ,;–—-")
        if fabric_code not in t:
            t = f"{fabric_code} {t}".strip()
        t = re.sub(rf"(?:{re.escape(fabric_code)}\s*)+", fabric_code + " ", t).strip()
    return t


def client_line_text(item: dict) -> str:
    """One client-visible description: fractions, no supplier/brand names."""
    code = str(item.get("fabric_code") or item.get("code") or "").strip()
    if not _V_CODE.match(code or "x"):
        found = _V_CODE.search(str(item.get("description") or ""))
        code = found.group(1) if found else code
    raw = client_visible_line_description(item)
    cleaned = _strip_brands(_fractions(raw), code)
    return cleaned or raw or "Item"


def sanitize_line_items(items: list[dict] | None) -> list[dict]:
    """Copy lines for the client PDF / Square / cover email."""
    out: list[dict] = []
    for it in items or []:
        row = dict(it)
        text = client_line_text(row)
        row["description"] = text
        row["client_description"] = text
        row["display_description"] = text
        out.append(row)
    return out


def line_amount(item: dict) -> float:
    for key in ("total", "amount"):
        if item.get(key) is not None:
            try:
                return float(item[key])
            except (TypeError, ValueError):
                pass
    try:
        qty = float(item.get("quantity", 1) or 1)
        rate = float(item.get("unit_price", item.get("rate", 0)) or 0)
        return round(qty * rate, 2)
    except (TypeError, ValueError):
        return 0.0


def money(amount: Any) -> str:
    try:
        return f"${float(amount or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"
