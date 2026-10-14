"""Strip anything that must never appear on a published or draft viewer.

Forbidden on every generated page:
  - supplier / brand / SKU fields from the fabric registry
  - prices and currency amounts
  - client / project street addresses
"""

from __future__ import annotations

import re
from typing import Iterable

_PRICE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:USD|CAD|EUR|GBP)?\s*\$\s*\d[\d,]*(?:\.\d{2})?\b",
    re.I,
)
_SKU_RE = re.compile(
    r"\b(?:SKU|supplier[_ ]?sku|vendor[_ ]?sku)\s*[:=]\s*\S+",
    re.I,
)
_ADDRESS_HINT_RE = re.compile(
    r"\b(?:\d{1,6}\s+(?:[NSEW]{1,2}\.?\s+)?[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,4}"
    r"\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Ct|Court|"
    r"Way|Hwy|Highway|Pkwy|Parkway|Pl|Place|Ter|Terrace)\.?)\b",
    re.I,
)


def _collect_secret_needles(extra: Iterable[str] | None = None) -> list[str]:
    needles: list[str] = []
    for raw in extra or []:
        text = (raw or "").strip()
        if len(text) >= 3:
            needles.append(text)
    try:
        from app.services.fabric_code_catalog import INTERNAL_ONLY_FIELDS, load_registry_rows

        for row in load_registry_rows():
            for key in INTERNAL_ONLY_FIELDS:
                val = row.get(key)
                if val and str(val).strip() and str(val).strip().lower() not in {"none", "n/a", "-"}:
                    needles.append(str(val).strip())
    except Exception:
        pass
    # Longest first so "Kravet Inc" is removed before "Kravet".
    needles.sort(key=len, reverse=True)
    return needles


def scrub_text(text: str, extra_forbidden: Iterable[str] | None = None) -> str:
    if not text:
        return ""
    out = str(text)
    for needle in _collect_secret_needles(extra_forbidden):
        out = re.sub(re.escape(needle), "", out, flags=re.I)
    out = _PRICE_RE.sub("", out)
    out = _SKU_RE.sub("", out)
    out = _ADDRESS_HINT_RE.sub("", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def assert_html_safe(html: str, extra_forbidden: Iterable[str] | None = None) -> None:
    """Raise ValueError if generated HTML still contains a forbidden token."""
    lowered = html.lower()
    if _PRICE_RE.search(html):
        raise ValueError("viewer HTML contains a price")
    if _SKU_RE.search(html):
        raise ValueError("viewer HTML contains a SKU")
    if _ADDRESS_HINT_RE.search(html):
        raise ValueError("viewer HTML contains a street address")
    for needle in extra_forbidden or []:
        if needle and len(needle) >= 3 and needle.lower() in lowered:
            raise ValueError(f"viewer HTML leaked forbidden token: {needle}")
    for token in ("supplier_sku", "unit_price", "customer_address", "client_address"):
        if token in lowered:
            raise ValueError(f"viewer HTML leaked field name {token}")
