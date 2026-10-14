"""Interview sections and the real 'configured' check.

A company is configured when the founder has a legal/DBA name (or a
named brand), document contact (address + phone + email), and at least
one saved interview section. The old check (business_name != "Empire")
is not used.
"""
from __future__ import annotations

from typing import Any

INTERVIEW_SECTIONS: list[dict[str, Any]] = [
    {
        "id": "identity",
        "title": "Legal name, DBA, and brands",
        "title_es": "Nombre legal, DBA y marcas",
        "summary": "Legal entity vs DBA. Multiple brands per owner (Empire Workroom default, Nelma's Workroom).",
        "required": True,
    },
    {
        "id": "contact",
        "title": "Address, phone, and email for documents",
        "title_es": "Dirección, teléfono y correo para documentos",
        "summary": "Printed on quotes, invoices, and letterhead.",
        "required": True,
    },
    {
        "id": "tax",
        "title": "EIN and sales tax",
        "title_es": "EIN e impuesto de ventas",
        "summary": "EIN plus sales tax by state/county and which items are taxable.",
        "required": False,
    },
    {
        "id": "payments",
        "title": "Payment processors and deposits",
        "title_es": "Procesadores de pago y depósitos",
        "summary": "Stripe Payment Links or Square per brand, deposit percent and terms.",
        "required": False,
    },
    {
        "id": "numbering",
        "title": "Quote and invoice numbering",
        "title_es": "Numeración de cotizaciones y facturas",
        "summary": "Prefix plus starting number for quotes and invoices.",
        "required": False,
    },
    {
        "id": "services",
        "title": "Services catalog and rate cards",
        "title_es": "Catálogo de servicios y tarifas",
        "summary": "Feeds Pricing Studio. Labor and component rates per brand.",
        "required": False,
    },
    {
        "id": "measurements",
        "title": "Measurement rules",
        "title_es": "Reglas de medida",
        "summary": "Fractions only — never decimal inches on shop or client docs.",
        "required": False,
    },
    {
        "id": "fabric",
        "title": "Fabric codes and foam allowance",
        "title_es": "Códigos de tela y merma por foam",
        "summary": "V###-Color format, next number, allowance per side by foam thickness.",
        "required": False,
    },
    {
        "id": "team",
        "title": "Team users, roles, and invites",
        "title_es": "Equipo, roles e invitaciones",
        "summary": "Invite records only — Max never emails clients or teammates.",
        "required": False,
    },
    {
        "id": "channels",
        "title": "Channels and founder numbers",
        "title_es": "Canales y números del fundador",
        "summary": "WhatsApp, email, phone, founder numbers for this edition.",
        "required": False,
    },
    {
        "id": "calendar",
        "title": "Calendar and shop hours",
        "title_es": "Calendario y horarios",
        "summary": "Open hours Max uses for scheduling.",
        "required": False,
    },
    {
        "id": "suppliers",
        "title": "Suppliers",
        "title_es": "Proveedores",
        "summary": "Fabric houses, foam, hardware — internal only.",
        "required": False,
    },
    {
        "id": "insurance",
        "title": "Insurance and COI",
        "title_es": "Seguro y COI",
        "summary": "Certificate of insurance requirements for jobs and vendors.",
        "required": False,
    },
    {
        "id": "branding",
        "title": "Logo, colors, and PDF letterhead",
        "title_es": "Logo, colores y membrete PDF",
        "summary": "Brand kit for quotes, invoices, and presentations.",
        "required": False,
    },
    {
        "id": "life",
        "title": "Personal and family life areas",
        "title_es": "Áreas de vida personal y familiar",
        "summary": "Max covers whole life, not only the Workroom. Privacy boundaries stay on.",
        "required": False,
    },
    {
        "id": "review",
        "title": "Review and confirm",
        "title_es": "Revisar y confirmar",
        "summary": "Read-only recap before marking setup complete.",
        "required": True,
    },
]

SECTION_IDS = [s["id"] for s in INTERVIEW_SECTIONS]
REQUIRED_SECTION_IDS = [s["id"] for s in INTERVIEW_SECTIONS if s.get("required")]

DEFAULT_BRANDS = [
    {
        "id": "empire-workroom",
        "name": "Empire Workroom",
        "legal_name": "",
        "dba": "Empire Workroom",
        "is_default": True,
        "notes": "Default brand for quotes and invoices.",
    },
    {
        "id": "nelmas-workroom",
        "name": "Nelma's Workroom",
        "legal_name": "",
        "dba": "Nelma's Workroom",
        "is_default": False,
        "notes": "Second brand under the same owner.",
    },
]

FABRIC_CODE_FORMAT = "V###-Color"
MEASUREMENT_RULE = "fractions_only"

TEAM_ROLES = (
    "founder",
    "admin",
    "estimator",
    "seamstress",
    "installer",
    "viewer",
)

PAYMENT_PROCESSORS = ("stripe_payment_links", "square")

LIFE_PRIVACY = ("private", "shared_family", "workroom")

# Input keys allowed per section. Anything else is a 400.
SECTION_ALLOWLIST: dict[str, frozenset[str]] = {
    "identity": frozenset({"legal_name", "dba", "business_name", "owner_name", "tagline", "business_tagline", "brands"}),
    "contact": frozenset({"address", "phone", "email", "website", "timezone", "business_address", "business_phone", "business_email", "street", "city", "state"}),
    "tax": frozenset({"ein", "rates", "taxable_items"}),
    "payments": frozenset({"deposit_percent", "deposit_terms", "processors"}),
    "numbering": frozenset({"quote_prefix", "quote_start", "invoice_prefix", "invoice_start"}),
    "services": frozenset({"catalog", "services_catalog", "rate_cards", "labor_rate"}),
    "measurements": frozenset({"fractions_only", "notes"}),
    "fabric": frozenset({"code_format", "next_number", "allowance_by_foam_thickness"}),
    "team": frozenset({"users"}),
    "channels": frozenset({"whatsapp", "email", "phone", "founder_phones", "owner_phones"}),
    "calendar": frozenset({"hours", "notes"}),
    "suppliers": frozenset({"suppliers"}),
    "insurance": frozenset({"coi_required", "coverage", "min_amount", "notes"}),
    "branding": frozenset({"logo_url", "primary", "ink", "paper", "letterhead"}),
    "life": frozenset({"areas", "privacy_boundaries", "max_covers_whole_life"}),
    "review": frozenset(),
}

# Overlay keys a section is allowed to write. Interview-set keys win over
# later hand edits of the same key. Seed keys not in this set stay out of
# the overlay so later edits to those keys in config/business.json survive.
SECTION_OVERLAY_KEYS: dict[str, frozenset[str]] = {
    "identity": frozenset({"identity", "brands", "legal_name", "dba", "business_name", "owner_name", "business_tagline"}),
    "contact": frozenset({"contact", "business_address", "business_phone", "business_email", "business_website", "timezone"}),
    "tax": frozenset({"tax"}),
    "payments": frozenset({"payments"}),
    "numbering": frozenset({"numbering"}),
    "services": frozenset({"services_section", "services_catalog", "rate_cards", "labor_rate"}),
    "measurements": frozenset({"measurements"}),
    "fabric": frozenset({"fabric", "fabric_next_number", "fabric_code_format"}),
    "team": frozenset({"team"}),
    "channels": frozenset({"channels", "founder_phones", "owner_phones"}),
    "calendar": frozenset({"calendar"}),
    "suppliers": frozenset({"suppliers"}),
    "insurance": frozenset({"insurance"}),
    "branding": frozenset({"branding"}),
    "life": frozenset({"life"}),
    "review": frozenset(),
}


class UnknownSectionKey(ValueError):
    """Payload included a key this section may not write."""


def validate_section_payload(section_id: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if section_id not in SECTION_ALLOWLIST:
        raise ValueError(f"Unknown company setup section: {section_id}")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("Section data must be an object")
    allowed = SECTION_ALLOWLIST[section_id]
    unknown = sorted(k for k in payload if k not in allowed)
    if unknown:
        raise UnknownSectionKey(f"Unknown keys for {section_id}: {unknown}")
    return {k: v for k, v in payload.items() if k in allowed}


# Keys that a payload must never wipe when absent or null.
PRESERVE_KEYS = (
    "business_phone",
    "founder_phones",
    "owner_phones",
    "business_email",
    "business_address",
    "business_website",
    "business_name",
    "business_tagline",
    "owner_name",
    "timezone",
    "currency",
    "tax_rate",
    "labor_rate",
    "install_rate_per_window",
    "fabric_markup",
    "quote_escalation_threshold",
    "followup_days_overdue",
    "tier",
    "ai_assistant_name",
    "ai_assistant_role",
    "telegram_enabled",
    "services",
    "industry",
)


def _text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _brands(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("brands")
    if isinstance(raw, list):
        return [b for b in raw if isinstance(b, dict)]
    return []


def configured_report(data: dict[str, Any] | None) -> dict[str, Any]:
    """Honest configured check. Missing pieces are named, never guessed."""
    data = data if isinstance(data, dict) else {}
    identity = data.get("identity") if isinstance(data.get("identity"), dict) else {}
    contact = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    brands = _brands(data) or _brands(identity)

    legal = _text(
        identity.get("legal_name"),
        data.get("legal_name"),
        identity.get("dba"),
        data.get("dba"),
        data.get("business_name"),
    )
    named_brand = next(
        (b for b in brands if _text(b.get("name"), b.get("dba"), b.get("legal_name"))),
        None,
    )
    has_name = bool(legal or named_brand)

    address = _text(
        contact.get("address"),
        contact.get("street"),
        data.get("business_address"),
    )
    if not address:
        parts = [
            _text(contact.get("street"), contact.get("address_line1")),
            _text(contact.get("city")),
            _text(contact.get("state")),
        ]
        address = ", ".join(p for p in parts if p)
    phone = _text(contact.get("phone"), data.get("business_phone"))
    email = _text(contact.get("email"), data.get("business_email"))
    has_contact = bool(address and phone and email)

    progress = data.get("company_setup") if isinstance(data.get("company_setup"), dict) else {}
    completed_sections = [
        s for s in (progress.get("completed_sections") or []) if s in SECTION_IDS
    ]
    has_progress = bool(completed_sections) or bool(progress.get("completed"))
    # A file that only has the stock Empire/Founder defaults is not configured.
    stock = (
        _text(data.get("business_name")) in {"", "Empire"}
        and _text(data.get("owner_name")) in {"", "Founder"}
        and not legal
        and not named_brand
    )

    missing: list[str] = []
    if not has_name:
        missing.append("legal_name_or_brand")
    if not address:
        missing.append("document_address")
    if not phone:
        missing.append("document_phone")
    if not email:
        missing.append("document_email")

    configured = has_name and has_contact and not stock
    return {
        "configured": configured,
        "has_name": has_name,
        "has_contact": has_contact,
        "has_progress": has_progress,
        "missing": missing,
        "completed_sections": completed_sections,
        "interview_complete": bool(progress.get("completed")),
        "brand_count": len(brands),
        "legal_name": legal,
        "default_brand": (named_brand or {}).get("name") or legal,
    }


def is_configured(data: dict[str, Any] | None) -> bool:
    return bool(configured_report(data).get("configured"))


def section_by_id(section_id: str) -> dict[str, Any] | None:
    for row in INTERVIEW_SECTIONS:
        if row["id"] == section_id:
            return dict(row)
    return None
