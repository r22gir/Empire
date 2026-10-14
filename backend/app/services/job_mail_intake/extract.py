"""Extract dates, tracking numbers, and order confirmations from mail.

Pure string parsing. No network. Never sends.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# Require separators. A lone EST2026034 or timezone "EST 2026 15:34"
# must not mint an estimate number. Sequence is 3–4 digits (EST-2026-034).
ESTIMATE_RE = re.compile(r"\bEST[- ](\d{4})[- ](\d{3,4})\b", re.I)
# Stop at the end of the line. Flattened bodies are trimmed after capture.
SIDEMARK_RE = re.compile(r"\bsidemark\s*[:\-]\s*([^\n]{2,80})", re.I)
JOB_CODE_RE = re.compile(r"\b((?:JOB|CF|WO)[- ]\d{4}[- ]\d{3,4})\b", re.I)
ORDER_NO_RES = (
    re.compile(
        r"\b(?:order|purchase\s*order|confirmation)(?:\s*(?:number|#|no\.?))?\s*[:\-]?\s*"
        r"([A-Z0-9]*\d[A-Z0-9\-]{2,24})\b",
        re.I,
    ),
    re.compile(r"\bPO\s*[#:\-]\s*([A-Z0-9]*\d[A-Z0-9\-]{2,24})\b", re.I),
)
_SIDEMARK_TRAIL_RE = re.compile(
    r"\s{2,}|\s+[|•]\s+|\s+(?:order|tracking|po|quote|estimate|confirmation)\b",
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
    out = []
    for m in SIDEMARK_RE.finditer(text or ""):
        val = _SIDEMARK_TRAIL_RE.split(m.group(1).strip(), maxsplit=1)[0]
        val = val.strip(" -:;,.")
        if 2 <= len(val) <= 80:
            out.append(val)
    return list(dict.fromkeys(out))


def _pad_code(prefix: str, year: str, seq: str) -> str:
    width = 4 if prefix == "JOB" else 3
    return f"{prefix}-{year}-{int(seq):0{width}d}"


def job_codes(text: str) -> list[str]:
    out = []
    for m in JOB_CODE_RE.finditer(text or ""):
        raw = re.sub(r"[\s_]+", "-", m.group(1).upper())
        parts = raw.split("-")
        if len(parts) < 3:
            continue
        out.append(_pad_code(parts[0], parts[1], parts[2]))
    return list(dict.fromkeys(out))


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
    for rx in ORDER_NO_RES:
        for m in rx.finditer(text or ""):
            val = m.group(1).strip()
            if val.upper() in skip:
                continue
            if not any(ch.isdigit() for ch in val):
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
    from app.services.job_mail_intake.filters import is_empire_identity, is_internal_mail

    # Never treat Empire / Max / our own mailboxes as a supplier.
    if is_internal_mail(msg) or is_empire_identity(msg):
        return False
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
        "job_codes": job_codes(blob),
        "sidemarks": sidemarks(blob),
        "tracking_numbers": tracking_numbers(blob),
        "order_numbers": order_numbers(blob),
        "proposed_dates": proposed_dates(blob),
        "is_supplier_order": is_supplier_order(msg),
        "sent": False,
    }
