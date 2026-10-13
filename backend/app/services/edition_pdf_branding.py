"""Per-company identity for Max-e / Maxine estimate, quote, and invoice PDFs.

Reads the company profile under EMPIRE_DATA_DIR/businesses/<slug>/business.json.
Never opens repo client_aliases.json, repo business.json, or .env.
Never writes live data.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.edition import (
    active_business_slug,
    assert_under_root,
    assistant_name,
    is_family_edition,
    require_data_root,
)
from app.services.voice_doc.plans import cop_round, format_cop

DEFAULT_IVA_RATE = 0.19
WORKROOM_NAMES = frozenset({
    "empire workroom",
    "nelma's workroom",
    "nelmas workroom",
    "woodcraft by empire",
    "empire woodcraft",
})
_LOGO_NAMES = ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp", "logo.gif")


@dataclass(frozen=True)
class EditionPdfBrand:
    slug: str
    name: str
    legal_name: str
    tagline: str
    nit: str
    iva_rate: float
    currency: str
    phone: str
    email: str
    address: str
    website: str
    city: str
    country: str
    logo_path: Optional[Path]


def format_document_cop(amount: Any) -> str:
    """COP as $1.234.567 with no decimals."""
    return format_cop(cop_round(amount or 0))


def normalize_iva_rate(value: Any, default: float = DEFAULT_IVA_RATE) -> float:
    if value is None or value == "":
        return default
    try:
        rate = float(str(value).replace(",", ".").replace("%", "").strip())
    except (TypeError, ValueError):
        return default
    if rate > 1:
        rate = rate / 100.0
    if rate < 0:
        return default
    return min(rate, 1.0)


def _clip(value: Any, limit: int = 200) -> str:
    return str(value or "").replace("\x00", "").strip()[:limit]


def _is_workroom_name(name: str) -> bool:
    return (name or "").strip().casefold() in WORKROOM_NAMES


def business_slug_for_document(document: Optional[dict] = None) -> str:
    document = document if isinstance(document, dict) else {}
    for key in ("business_slug", "company_slug", "slug"):
        raw = _clip(document.get(key), 80).lower()
        if raw:
            return raw
    try:
        return active_business_slug()
    except Exception:
        return "amp"


def read_business_profile(slug: str) -> dict:
    """Read-only merge of the company file and registry row. No creates."""
    from app.services.amp_businesses import safe_slug, _load_registry

    wanted = safe_slug(slug)
    profile: dict = {}
    try:
        path = assert_under_root(require_data_root() / "businesses" / wanted / "business.json")
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                profile = dict(data)
    except (OSError, json.JSONDecodeError, TypeError, RuntimeError):
        profile = {}
    try:
        for row in (_load_registry().get("businesses") or []):
            if isinstance(row, dict) and row.get("slug") == wanted:
                return {**row, **profile} if profile else dict(row)
    except (OSError, RuntimeError):
        pass
    return profile


def resolve_logo_path(profile: dict, slug: str) -> Optional[Path]:
    """Local logo under the instance data root only. Remote URLs are ignored."""
    from app.services.amp_businesses import safe_slug

    wanted = safe_slug(slug)
    try:
        root = assert_under_root(require_data_root() / "businesses" / wanted)
    except (OSError, RuntimeError):
        return None
    candidates: list[Path] = []
    for key in ("logo_path", "logo", "logo_file"):
        raw = _clip(profile.get(key), 400)
        if not raw or raw.startswith(("http://", "https://", "data:")):
            continue
        candidates.append(Path(raw))
    for name in _LOGO_NAMES:
        candidates.append(root / name)
    for cand in candidates:
        try:
            resolved = cand if cand.is_absolute() else (root / cand)
            resolved = assert_under_root(resolved)
        except (OSError, RuntimeError):
            continue
        if resolved.is_file():
            return resolved
    return None


def client_nit(document: Optional[dict] = None, customer: Optional[dict] = None) -> str:
    sources = [src for src in (document, customer) if isinstance(src, dict)]
    keys = ("customer_nit", "client_nit", "nit", "tax_id", "customer_tax_id")
    for src in sources:
        for key in keys:
            value = _clip(src.get(key), 40)
            if value:
                return value
        fields = src.get("fields") or src.get("fields_json")
        if isinstance(fields, str):
            try:
                fields = json.loads(fields)
            except json.JSONDecodeError:
                fields = {}
        if isinstance(fields, dict):
            for key in ("nit", "tax_id", "n_it"):
                value = _clip(fields.get(key), 40)
                if value:
                    return value
    return ""


def _display_name(profile: dict, document: Optional[dict]) -> str:
    document = document if isinstance(document, dict) else {}
    for raw in (
        profile.get("trade_name"),
        profile.get("name"),
        profile.get("legal_name"),
        document.get("business_name"),
    ):
        name = _clip(raw, 200)
        if name and not _is_workroom_name(name):
            return name
    if is_family_edition():
        return assistant_name()
    return ""


def resolve_edition_pdf_brand(
    document: Optional[dict] = None,
    *,
    slug: Optional[str] = None,
) -> EditionPdfBrand:
    wanted = (slug or business_slug_for_document(document)).strip() or "amp"
    profile = read_business_profile(wanted) if is_family_edition() else {}
    name = _display_name(profile, document)
    legal = _clip(profile.get("legal_name"), 200)
    if _is_workroom_name(legal):
        legal = ""
    city = _clip(profile.get("city"), 80)
    country = _clip(profile.get("country"), 80) or "Colombia"
    address_parts = [
        _clip(profile.get("address") or profile.get("business_address"), 200),
        city,
        country,
    ]
    address = ", ".join(part for part in address_parts if part)
    return EditionPdfBrand(
        slug=wanted,
        name=name,
        legal_name=legal,
        tagline=_clip(profile.get("description") or profile.get("tagline") or profile.get("brand"), 200),
        nit=_clip(profile.get("tax_id") or profile.get("nit"), 40),
        iva_rate=normalize_iva_rate(profile.get("iva_rate"), DEFAULT_IVA_RATE),
        currency=(_clip(profile.get("currency"), 8).upper() or "COP"),
        phone=_clip(profile.get("contact_phone") or profile.get("phone"), 40),
        email=_clip(profile.get("contact_email") or profile.get("email"), 160),
        address=address,
        website=_clip(profile.get("website"), 200),
        city=city,
        country=country,
        logo_path=resolve_logo_path(profile, wanted) if is_family_edition() else None,
    )


def document_iva_rate(document: Optional[dict], brand: EditionPdfBrand) -> float:
    document = document if isinstance(document, dict) else {}
    if document.get("tax_rate") not in (None, ""):
        return normalize_iva_rate(document.get("tax_rate"), brand.iva_rate)
    return brand.iva_rate
