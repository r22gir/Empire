"""Title-block branding for upholstery-on-shell banquette PDFs."""
from __future__ import annotations

from app.config.workroom_billing import (
    BILLED_BY_NELMA,
    get_workroom_billing,
    normalize_billed_by,
)


def resolve_banquette_branding(params: dict) -> tuple[str, str, str]:
    """Return (letterhead, subline, drawn_by) for sheet chrome.

    Default is Empire Workroom. Nelma's only when billed_by is nelmas_workroom
    or the user explicitly asks to bill as Nelma's.
    """
    notes = " ".join(
        str(params.get(k) or "")
        for k in ("description", "notes", "raw_message", "bill_as")
    ).lower()
    raw = params.get("billed_by") or params.get("bill_as") or ""
    if not raw and ("bill as nelma" in notes or "billed by nelma" in notes):
        raw = BILLED_BY_NELMA
    key = normalize_billed_by(raw) if raw else None
    if key == BILLED_BY_NELMA:
        billing = get_workroom_billing(BILLED_BY_NELMA)
        return (
            billing.letterhead_upper,
            "POWERED BY EMPIRE WORKROOM",
            "MAX AI",
        )
    billing = get_workroom_billing("empire_workroom")
    return (
        billing.letterhead_upper,
        (billing.tagline or "CUSTOM UPHOLSTERY & FABRICATION").upper(),
        "MAX AI",
    )


def normalize_banquette_job_label(
    name: str,
    shape: str,
    site: str,
    *,
    include_l: bool = False,
) -> str:
    """Avoid duplicated 'U-Banquette Upholstery — U-Banquette Upholstery'."""
    base = (site or name or "").strip()
    if include_l and shape == "u_shape":
        suffix = "U+L Banquette Upholstery"
    elif shape == "u_shape":
        suffix = "U-Banquette Upholstery"
    elif shape == "l_shape":
        suffix = "L-Banquette Upholstery"
    else:
        suffix = "Banquette Upholstery"
    if not base:
        return suffix
    low = base.lower()
    if suffix.lower() in low:
        return base
    if site or include_l:
        return f"{base} — {suffix}"
    return base
