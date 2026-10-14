"""Extract dates, tracking numbers, and order confirmations from mail.

Pure string parsing. No network. Never sends.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

ESTIMATE_RE = re.compile(r"\bEST[- ]?(\d{4})[- ]?(\d{2,4})\b", re.I)
SIDEMARK_RE = re.compile(r"\bsidemark\s*[:\-]\s*([^\n,;]{2,80})", re.I)
ORDER_NO_RE = re.compile(
    r"\b(?:order|po|purchase\s*order|confirmation)\s*#?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{4,24})\b",
    re.I,
)
TRACKING_RES = (
    re.compile(r"\b(1Z[A-Z0-9]{16})\b", re.I),  # UPS
    re.compile(r"\b(\d{12,22})\b"),  # FedEx / USPS numeric
    re.compile(r"\b((?:TBA|LB)\d{9,14})\b", re.I),
    re.compile(r"\btracking(?:\s*(?:number|#|no\.?))?\s*[:\-]\s*([A-Z0-9]{8,30})\b", re.I),
)
DATE_RES = (
    re.compile(
        r"\b(?:due|deadline|install|deliver(?:y|ed)?|arrive|arrival|needed by|by)\b"
        r"[^\n]{0,40}?"
        r"((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)",
        re.I,
    ),
    re.compile(
        r"\b(?:due|deadline|install|deliver(?:y|ed)?|arrive|needed by|by)\b"
        r"[^\n]{0,20}?"
        r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})",
        re.I,
    ),
)
ORDER_HINTS = (
    "order confirmation",
    "your order",
    "order has shipped",
    "shipping confirmation",
    "tracking number",
    "purchase order",
    "po #",
    "we have received your order",
)
SUPPLIER_HINTS = (
    "fabric",
    "supplier",
    "warehouse",
    "shipment",
    "ups",
    "fedex",
    "usps",
    "dhl",
    "rowley",
    "horizon",
    "mayer",
    "kravet",
    "schumacher",
)


def _blob(msg: dict) -> str:
    return " ".join(
        str(msg.get(k) or "")
        for k in ("subject", "from", "preview", "body", "to")
    )


def estimate_numbers(text: str) -> list[str]:
    out = []
    for m in ESTIMATE_RE.finditer(text or ""):
        out.append(f"EST-{m.group(1)}-{int(m.group(2)):03d}")
    return list(dict.fromkeys(out))


def sidemarks(text: str) -> list[str]:
    return [m.group(1).strip() for m in SIDEMARK_RE.finditer(text or "") if m.group(1).strip()]


def tracking_numbers(text: str) -> list[str]:
    found: list[str] = []
    blob = text or ""
    for rx in TRACKING_RES:
        for m in rx.finditer(blob):
            val = m.group(1).strip()
            if val.isdigit() and len(val) < 12:
                continue
            if val.lower() in {"confirmation", "number", "order"}:
                continue
            found.append(val.upper() if not val.isdigit() else val)
    return list(dict.fromkeys(found))


def order_numbers(text: str) -> list[str]:
    skip = {"ORDER", "CONFIRMATION", "NUMBER", "TRACKING"}
    out = []
    for m in ORDER_NO_RE.finditer(text or ""):
        val = m.group(1).strip()
        if val.upper() in skip:
            continue
        out.append(val)
    return list(dict.fromkeys(out))


def _parse_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    raw = re.sub(r"(st|nd|rd|th)\b", "", raw, flags=re.I)
    raw = raw.replace(",", " ")
    raw = re.sub(r"\s+", " ", raw).strip(" ,")
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d %Y",
        "%b %d %Y",
        "%B %d",
        "%b %d",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def proposed_dates(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    blob = text or ""
    for rx in DATE_RES:
        for m in rx.finditer(blob):
            iso = _parse_date(m.group(1))
            if not iso:
                continue
            window = blob[max(0, m.start() - 24): m.end() + 8].lower()
            kind = "deadline"
            if "install" in window:
                kind = "install"
            elif "deliver" in window or "arriv" in window:
                kind = "delivery"
            out.append({"date": iso, "kind": kind, "excerpt": m.group(0)[:160]})
    seen = set()
    unique = []
    for row in out:
        key = (row["date"], row["kind"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def is_supplier_order(msg: dict) -> bool:
    blob = _blob(msg).lower()
    if any(h in blob for h in ORDER_HINTS):
        return True
    if tracking_numbers(blob) and any(h in blob for h in SUPPLIER_HINTS):
        return True
    return False


def extract_mail_facts(msg: dict) -> dict[str, Any]:
    blob = _blob(msg)
    return {
        "estimate_numbers": estimate_numbers(blob),
        "sidemarks": sidemarks(blob),
        "tracking_numbers": tracking_numbers(blob),
        "order_numbers": order_numbers(blob),
        "proposed_dates": proposed_dates(blob),
        "is_supplier_order": is_supplier_order(msg),
        "sent": False,
    }
