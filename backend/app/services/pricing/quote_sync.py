"""Price Workroom and WoodCraft quote lines with the Pricing Studio engine.

Studio calculate and quote line math both call this module, so a line quoted
in Workroom or WoodCraft uses the same rate card and the same dollars.
"""
from __future__ import annotations

from typing import Any

from app.data.product_catalog import PRICING_SPECS
from app.services.pricing.engine import (
    WORKROOM_LINE_PRICERS,
    PricingClassificationError,
    PricingInputError,
    price_woodcraft_item,
    price_workroom_item,
    price_workroom_line,
)
from app.services.pricing.rate_cards import lookup_rate


_ENVELOPE_KEYS = {
    "item_type",
    "product_category",
    "category",
    "pricing_inputs",
    "discount_type",
    "discount_amount",
    "tax_policy",
    "deposit_required",
    "deposit_percent",
    "override_amount",
    "override_reason",
    "source_quote_id",
    "source_line_item_id",
    "business_unit",
}


def _first_present(src: dict, keys: tuple[str, ...]):
    for key in keys:
        if key not in src:
            continue
        value = src.get(key)
        if value is None or value == "":
            continue
        return value
    return None


def normalize_quote_inputs(inputs: dict | None) -> dict:
    """Map quote-builder field names onto the pricing engine's names."""
    src = dict(inputs or {})
    if not src.get("window_width_in"):
        width = _first_present(src, ("finished_width", "width_in", "width"))
        if width not in (None, 0, 0.0):
            src["window_width_in"] = width
    if not src.get("length_in"):
        length = _first_present(src, ("finished_length", "length", "height_in", "height"))
        if length not in (None, 0, 0.0):
            src["length_in"] = length
    if not src.get("width_in"):
        width = _first_present(src, ("window_width_in", "finished_width", "width"))
        if width not in (None, 0, 0.0):
            src["width_in"] = width
    if not src.get("height_in"):
        height = _first_present(src, ("length_in", "finished_length", "height"))
        if height not in (None, 0, 0.0):
            src["height_in"] = height
    if not src.get("machine_minutes"):
        minutes = _first_present(src, ("cnc_minutes", "CNC_time_minutes", "estimated_time_min"))
        if minutes not in (None, 0, 0.0):
            src["machine_minutes"] = minutes
    return src


def resolve_treatment(category: str | None) -> tuple[str | None, dict]:
    """Map a quote item type onto a Pricing Studio treatment, plus style hints."""
    raw = (category or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not raw:
        return None, {}
    extra: dict[str, Any] = {}
    if "ripplefold" in raw:
        extra["style"] = "ripplefold"
    if raw in {"drapery", "drapery_panel", "curtain", "drape", "sheer"} or raw.startswith("drapery_"):
        return "drapery", extra
    if raw.startswith("roman"):
        return "roman_shade", extra
    if raw.startswith("valance") or raw == "valance":
        return "valance", extra
    if raw.startswith("cornice") or raw == "cornice":
        return "cornice", extra
    if raw in {"pillow", "throw_pillow", "bolster", "decorative_pillow"}:
        return "pillow", extra
    if raw in WORKROOM_LINE_PRICERS:
        return raw, extra
    return None, {}


def _treatment_inputs(category: str, inputs: dict) -> dict:
    treatment, extra = resolve_treatment(category)
    merged = normalize_quote_inputs({**extra, **(inputs or {})})
    if treatment == "pillow" and not merged.get("unit_price"):
        merged["unit_price"] = PRICING_SPECS["pillow"]["base_unit_20x20"]
        merged.setdefault("quantity", 1)
    return merged


def try_treatment_line(category: str | None, inputs: dict | None, business_unit: str = "workroom") -> dict | None:
    """Price a catalog treatment. None when this category is not a treatment line."""
    treatment, _extra = resolve_treatment(category)
    if not treatment:
        return None
    # Keep the original category so style hints (ripplefold) survive.
    merged = _treatment_inputs(category, inputs or {})
    try:
        line = price_workroom_line(treatment, merged, business_unit=business_unit or "workroom")
    except PricingInputError:
        return None
    if float(line.get("proposed_price") or 0) <= 0:
        return None
    return line


def canonical_fabrication_price(item_type: str, dimensions: dict | None = None, extra: dict | None = None) -> float | None:
    """Studio treatment price for a Workroom quote fabrication line."""
    dims = dimensions or {}
    payload = {
        "width": dims.get("width"),
        "height": dims.get("height"),
        "depth": dims.get("depth"),
    }
    if extra:
        payload.update(extra)
    line = try_treatment_line(item_type, payload, business_unit="workroom")
    if not line:
        return None
    return float(line["proposed_price"])


def canonical_cnc_cost(minutes: float, rate_per_hour: float | None = None) -> float:
    """WoodCraft CNC dollars at the Pricing Studio machine rate."""
    rate = lookup_rate("woodcraft", "machine_rate_per_hour") if rate_per_hour is None else float(rate_per_hour)
    return round((float(minutes or 0) / 60.0) * rate, 2)


def _snapshot_kwargs(body: dict) -> dict:
    override = body.get("override_amount")
    return {
        "discount_type": body.get("discount_type", "dollar"),
        "discount_amount": float(body.get("discount_amount", 0) or 0),
        "tax_policy": body.get("tax_policy"),
        "deposit_required": body.get("deposit_required", True),
        "deposit_percent": float(body.get("deposit_percent", 50) or 0),
        "override_amount": None if override is None or override == "" else override,
        "override_reason": body.get("override_reason"),
        "source_quote_id": body.get("source_quote_id"),
        "source_line_item_id": body.get("source_line_item_id"),
    }


def studio_calculate(business_unit: str, body: dict | None) -> dict:
    """Same entry Pricing Studio and quote math use for a calculate request."""
    body = body or {}
    unit = (business_unit or "workroom").strip().lower()
    category = body.get("product_category") or body.get("item_type") or body.get("category")
    raw = body.get("pricing_inputs") if isinstance(body.get("pricing_inputs"), dict) else body
    inputs = normalize_quote_inputs(raw)
    for key in _ENVELOPE_KEYS:
        inputs.pop(key, None)

    kwargs = _snapshot_kwargs(body)
    line = try_treatment_line(category, inputs, business_unit="workroom")
    priced_category = category
    if line is not None:
        treatment, _extra = resolve_treatment(category)
        priced_category = treatment or category
        inputs = {"fixed_price": line["proposed_price"]}
    elif kwargs["override_amount"] is not None and "fixed_price" not in inputs and "service_price" not in inputs:
        # Override still needs a deterministic step; the override replaces the total.
        inputs = {**inputs, "fixed_price": inputs.get("fixed_price", 0)}

    if unit == "woodcraft" and line is None:
        return price_woodcraft_item(priced_category, inputs, **kwargs)
    if unit == "woodcraft" and line is not None:
        # Treatment dollars are the rate-card line; keep the WoodCraft snapshot wrapper.
        return price_woodcraft_item(priced_category if priced_category in {"cornice", "valance"} else "custom_build", inputs, **kwargs)
    return price_workroom_item(priced_category, inputs, **kwargs)


def woodcraft_line_amount(category: str | None, inputs: dict | None) -> dict | None:
    """Canonical WoodCraft line snapshot, or None when inputs cannot be priced."""
    merged = normalize_quote_inputs(inputs or {})
    try:
        snap = price_woodcraft_item(category, merged)
    except (PricingInputError, PricingClassificationError):
        return None
    amount = float(snap.get("calculated_subtotal") or 0)
    if amount <= 0:
        return None
    return snap


def apply_canonical_cnc_pricing(data: dict) -> dict:
    """Replace a WoodCraft design's CNC dollars with the studio machine rate.

    Subtotal is pre-margin and already includes the previous CNC amount.
    Margin, discount, and tax are reapplied from the rates stored on the design.
    """
    jobs = data.get("cnc_jobs") or []
    minutes = 0.0
    for job in jobs:
        if isinstance(job, dict):
            minutes += float(job.get("estimated_time_min") or 0)
    if minutes <= 0:
        return data

    old_cnc = float(data.get("cnc_time_cost") or 0)
    new_cnc = canonical_cnc_cost(minutes)
    old_sub = float(data.get("subtotal") or 0)
    new_sub = round(old_sub - old_cnc + new_cnc, 2)
    margin_pct = float(data.get("margin_percent") or 0)
    after_margin = new_sub * (1 + margin_pct / 100)
    discount_amount = float(data.get("discount_amount") or 0)
    discount_type = (data.get("discount_type") or "dollar").strip().lower()
    if discount_type == "percent":
        discount_value = after_margin * (discount_amount / 100)
    else:
        discount_value = discount_amount
    after_discount = max(after_margin - discount_value, 0)
    tax_rate = float(data.get("tax_rate") or 0)
    tax_amount = after_discount * tax_rate
    total = after_discount + tax_amount

    data["cnc_time_cost"] = new_cnc
    data["cnc_rate_per_hour"] = lookup_rate("woodcraft", "machine_rate_per_hour")
    data["subtotal"] = round(new_sub, 2)
    data["tax_amount"] = round(tax_amount, 2)
    data["total"] = round(total, 2)
    return data
