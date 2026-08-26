"""Deterministic, explainable pricing for Empire business units."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any


PRICING_ENGINE_VERSION = "empire-pricing-engine-v1"
FORMULA_VERSION = "pricing-formulas-2026.05"
WORKROOM_RATE_TABLE_VERSION = "workroom-rates-2026.05"
WOODCRAFT_RATE_TABLE_VERSION = "woodcraft-rates-2026.05"


class PricingInputError(ValueError):
    """Raised when pricing inputs are invalid or incomplete."""


class PricingClassificationError(PricingInputError):
    """Raised when a product category cannot be priced deterministically."""


WORKROOM_CATEGORY_ALIASES = {
    "upholstery": "upholstery",
    "reupholstery": "upholstery",
    "chair": "upholstery",
    "accent_chair": "upholstery",
    "sofa": "upholstery",
    "ottoman": "upholstery",
    "headboard": "upholstery",
    "cushion": "cushions",
    "seat_cushion": "cushions",
    "bench_cushion": "cushions",
    "banquette_cushion": "cushions",
    "pillow": "pillows",
    "throw_pillow": "pillows",
    "bolster": "pillows",
    "drapery": "drapery_window_treatments",
    "curtain": "drapery_window_treatments",
    "window_treatment": "drapery_window_treatments",
    "roman_shade": "drapery_window_treatments",
    "roller_shade": "drapery_window_treatments",
    "sheer": "drapery_window_treatments",
    "cornice": "drapery_window_treatments",
    "valance": "drapery_window_treatments",
    "fabric": "fabric_materials",
    "material": "fabric_materials",
    "materials": "fabric_materials",
    "labor": "labor",
    "pickup": "pickup_delivery_install",
    "delivery": "pickup_delivery_install",
    "install": "pickup_delivery_install",
    "installation": "pickup_delivery_install",
    "rush": "rush_custom_surcharge",
    "custom_surcharge": "rush_custom_surcharge",
}


WOODCRAFT_CATEGORY_ALIASES = {
    "sheet_goods": "sheet_goods",
    "sheet": "sheet_goods",
    "plywood": "sheet_goods",
    "mdf": "sheet_goods",
    "board_foot": "board_foot_material",
    "board_feet": "board_foot_material",
    "hardwood": "board_foot_material",
    "cnc": "cnc_router_time",
    "cnc_router": "cnc_router_time",
    "router": "cnc_router_time",
    "machine_time": "cnc_router_time",
    "design": "design_drawing_time",
    "drawing": "design_drawing_time",
    "assembly": "assembly_labor",
    "labor": "assembly_labor",
    "finish": "finishing",
    "finishing": "finishing",
    "staining": "finishing",
    "painting": "finishing",
    "hardware": "hardware",
    "delivery": "delivery_install",
    "install": "delivery_install",
    "installation": "delivery_install",
    "cabinet": "custom_build",
    "cabinet_style": "custom_build",
    "custom_build": "custom_build",
    "built_in": "custom_build",
    "millwork": "custom_build",
    "furniture": "custom_build",
    "sign": "custom_build",
    "cornice": "custom_build",
    "valance": "custom_build",
}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _money(value: float) -> float:
    return round(float(value or 0), 2)


def _number(inputs: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(inputs.get(key, default) or default)
    except (TypeError, ValueError):
        raise PricingInputError(f"{key} must be numeric")


def _positive(inputs: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = _number(inputs, key, default)
    if value < 0:
        raise PricingInputError(f"{key} cannot be negative")
    return value


# D37 / H77 — Zero-guard for line pricers.
#
# A workroom line pricer that silently returns $0.00 is a defect: the number
# flows downstream to a customer-facing quote and the business may be held
# to a price it never agreed to. The legacy _positive() helper above only
# raised on negative values, which let required inputs default to 0.0 and
# produced $0.00 outputs (see H76 — same defect class).
#
# _require_positive() is the engine-level fix: a category that depends on a
# given input refuses to price if the input is missing, None, non-numeric,
# zero, or negative. The error names the category AND the offending input so
# the founder can fix the upstream caller without a guess.
#
# This is the PRIMARY defense. quote_service.py:83-87 is a secondary
# belt-and-suspenders that catches any path the engine does not — both must
# stay in place. But the engine MUST make silent 0.00 unreachable regardless
# of caller, per founder directive (D37 STEP 2 ruling).
def _require_positive(inputs: dict[str, Any], key: str, *, category: str) -> float:
    """Required input for a line pricer. Raises PricingInputError if missing,
    None, non-numeric, zero, or negative — naming the category and key."""
    raw = inputs.get(key)
    if raw is None or raw == "":
        raise PricingInputError(
            f"{category}: required input '{key}' is missing — refusing to price to 0.00"
        )
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise PricingInputError(
            f"{category}: required input '{key}' must be numeric (got {raw!r})"
        )
    if value <= 0:
        raise PricingInputError(
            f"{category}: required input '{key}' must be > 0 (got {value}) — refusing to price to 0.00"
        )
    return value


def _require_reason(override_amount: float | None, override_reason: str | None):
    if override_amount is not None and not (override_reason or "").strip():
        raise PricingInputError("manual override requires override_reason")


def _normalize_discount(discount_type: str | None) -> str:
    value = (discount_type or "dollar").strip().lower()
    if value in {"flat", "fixed"}:
        return "dollar"
    if value not in {"dollar", "percent"}:
        raise PricingInputError("discount_type must be dollar or percent")
    return value


def canonical_tax_policy(
    *,
    name: str = "explicit_rate",
    tax_rate: float | None = None,
    taxable: bool | None = None,
    jurisdiction: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    rate = float(tax_rate or 0)
    if rate < 0:
        raise PricingInputError("tax_rate cannot be negative")
    return {
        "name": name,
        "taxable": bool(rate > 0) if taxable is None else bool(taxable),
        "tax_rate": rate,
        "jurisdiction": jurisdiction,
        "source": source or "explicit",
    }


def calculate_tax(taxable_base: float, tax_policy: dict[str, Any] | None) -> float:
    policy = tax_policy or canonical_tax_policy(name="non_taxable_default", tax_rate=0, taxable=False)
    if not policy.get("taxable"):
        return 0.0
    return _money(float(taxable_base or 0) * float(policy.get("tax_rate") or 0))


def calculate_deposit_balance(final_price: float, deposit_required: bool = True, deposit_percent: float = 50.0) -> dict[str, float | bool]:
    percent = float(deposit_percent or 0)
    if percent < 0 or percent > 100:
        raise PricingInputError("deposit_percent must be between 0 and 100")
    amount = _money(final_price * (percent / 100)) if deposit_required and percent else 0.0
    return {
        "deposit_required": bool(deposit_required and amount > 0),
        "deposit_amount": amount,
        "balance_due": _money(final_price - amount),
    }


def _apply_totals(
    *,
    business_unit: str,
    module: str,
    product_category: str,
    pricing_method: str,
    pricing_inputs: dict[str, Any],
    rate_table_version: str,
    calculation_steps: list[dict[str, Any]],
    calculated_subtotal: float,
    discount_type: str | None = "dollar",
    discount_amount: float = 0.0,
    tax_policy: dict[str, Any] | None = None,
    deposit_required: bool = True,
    deposit_percent: float = 50.0,
    override_amount: float | None = None,
    override_reason: str | None = None,
    source_quote_id: str | None = None,
    source_line_item_id: str | None = None,
) -> dict[str, Any]:
    _require_reason(override_amount, override_reason)
    discount_kind = _normalize_discount(discount_type)
    subtotal = _money(calculated_subtotal)
    raw_discount = _money(discount_amount)
    applied_discount = _money(subtotal * (raw_discount / 100)) if discount_kind == "percent" else raw_discount
    taxable_base = max(_money(subtotal - applied_discount), 0.0)
    policy = tax_policy or canonical_tax_policy(name="non_taxable_default", tax_rate=0, taxable=False)
    tax_amount = calculate_tax(taxable_base, policy)
    calculated_total = _money(taxable_base + tax_amount)
    final_price = _money(override_amount) if override_amount is not None else calculated_total
    deposit = calculate_deposit_balance(final_price, deposit_required, deposit_percent)
    steps = list(calculation_steps)
    steps.append({
        "label": "discount",
        "formula": "subtotal * discount_percent" if discount_kind == "percent" else "flat discount",
        "amount": -applied_discount,
    })
    steps.append({
        "label": "tax",
        "formula": "taxable_base * tax_rate",
        "tax_policy": deepcopy(policy),
        "amount": tax_amount,
    })
    if override_amount is not None:
        steps.append({
            "label": "manual override",
            "formula": "final_price = override_amount",
            "amount": final_price,
            "reason": override_reason,
        })
    steps.append({
        "label": "deposit",
        "formula": "final_price * deposit_percent",
        "amount": deposit["deposit_amount"],
        "deposit_percent": deposit_percent,
    })

    return {
        "business_unit": business_unit,
        "module": module,
        "product_category": product_category,
        "pricing_method": pricing_method,
        "pricing_inputs": deepcopy(pricing_inputs),
        "rate_table_version": rate_table_version,
        "formula_version": FORMULA_VERSION,
        "calculation_steps": steps,
        "calculated_subtotal": subtotal,
        "discount_type": discount_kind,
        "discount_amount": raw_discount,
        "tax_policy": policy,
        "tax_amount": tax_amount,
        "deposit_required": deposit["deposit_required"],
        "deposit_amount": deposit["deposit_amount"],
        "balance_due": deposit["balance_due"],
        "override_amount": _money(override_amount) if override_amount is not None else None,
        "override_reason": override_reason,
        "final_price": final_price,
        "created_at": _now(),
        "source_quote_id": source_quote_id,
        "source_line_item_id": source_line_item_id,
        "pricing_engine_version": PRICING_ENGINE_VERSION,
    }


def _category(raw: str | None, aliases: dict[str, str], business_unit: str) -> str:
    key = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        raise PricingClassificationError(f"{business_unit} product_category is required")
    if key not in aliases:
        raise PricingClassificationError(
            f"Unknown {business_unit} product_category '{raw}'. Select an explicit pricing category."
        )
    return aliases[key]


def _step(label: str, formula: str, quantity: float, rate: float, amount: float, **extra) -> dict[str, Any]:
    payload = {
        "label": label,
        "formula": formula,
        "quantity": quantity,
        "rate": rate,
        "amount": _money(amount),
    }
    payload.update(extra)
    return payload


def _sum_component_steps(inputs: dict[str, Any], category: str, business: str) -> tuple[str, list[dict[str, Any]], float]:
    method = inputs.get("pricing_method") or "composite"
    steps: list[dict[str, Any]] = []

    quantity = _positive(inputs, "quantity", 1)
    fixed_price = inputs.get("fixed_price", inputs.get("service_price"))
    if fixed_price is not None:
        amount = _positive({"fixed_price": fixed_price}, "fixed_price") * quantity
        steps.append(_step("fixed service price", "quantity * fixed_price", quantity, float(fixed_price), amount))
        method = "fixed_service_price"

    unit_rate = inputs.get("unit_rate", inputs.get("rate"))
    if unit_rate is not None and inputs.get("unit_quantity") is not None:
        unit_quantity = _positive(inputs, "unit_quantity")
        amount = unit_quantity * _positive(inputs, "unit_rate" if "unit_rate" in inputs else "rate")
        steps.append(_step("quantity x unit rate", "unit_quantity * unit_rate", unit_quantity, float(unit_rate), amount))
        method = "quantity_unit_rate" if method == "composite" else method

    labor_hours = _positive(inputs, "labor_hours")
    labor_rate = _positive(inputs, "labor_rate", 85 if business == "woodcraft" else 65)
    if labor_hours:
        amount = labor_hours * labor_rate
        steps.append(_step("labor", "labor_hours * labor_rate", labor_hours, labor_rate, amount))
        method = "labor_hours_rate" if method == "composite" else method

    fabric_yards = _positive(inputs, "fabric_yards", _positive(inputs, "yards", 0))
    fabric_rate = _positive(inputs, "fabric_price_per_yard")
    if fabric_yards or fabric_rate:
        amount = fabric_yards * fabric_rate
        steps.append(_step("fabric/material yardage", "fabric_yards * fabric_price_per_yard", fabric_yards, fabric_rate, amount))
        method = "fabric_yardage" if method == "composite" else method

    linear_feet = _positive(inputs, "linear_feet")
    linear_rate = _positive(inputs, "linear_foot_rate")
    if linear_feet or linear_rate:
        amount = linear_feet * linear_rate
        steps.append(_step("linear footage", "linear_feet * linear_foot_rate", linear_feet, linear_rate, amount))
        method = "linear_foot" if method == "composite" else method

    square_feet = _positive(inputs, "square_feet")
    square_rate = _positive(inputs, "square_foot_rate")
    if square_feet or square_rate:
        amount = square_feet * square_rate
        steps.append(_step("square footage", "square_feet * square_foot_rate", square_feet, square_rate, amount))
        method = "square_foot" if method == "composite" else method

    material_cost = _positive(inputs, "material_cost")
    markup_percent = _positive(inputs, "markup_percent")
    if material_cost:
        amount = material_cost * (1 + markup_percent / 100)
        steps.append(_step("material markup", "material_cost * (1 + markup_percent)", material_cost, markup_percent, amount))
        method = "material_cost_markup" if method == "composite" else method

    for item in inputs.get("materials", []) or []:
        if not isinstance(item, dict):
            raise PricingInputError("materials must be objects")
        cost = float(item.get("cost", item.get("total", 0)) or 0)
        markup = float(item.get("markup_percent", markup_percent) or 0)
        amount = cost * (1 + markup / 100)
        if amount:
            steps.append(_step(item.get("description") or item.get("name") or "material", "cost * (1 + markup_percent)", cost, markup, amount))

    hardware_cost = _positive(inputs, "hardware_cost")
    if hardware_cost:
        steps.append(_step("hardware", "hardware_cost", 1, hardware_cost, hardware_cost))

    install_cost = _positive(inputs, "install_cost", _positive(inputs, "delivery_install_cost", 0))
    if install_cost:
        steps.append(_step("pickup/delivery/install", "fixed install or delivery cost", 1, install_cost, install_cost))

    subtotal = _money(sum(step["amount"] for step in steps))
    complexity_multiplier = _positive(inputs, "complexity_multiplier", 1)
    if complexity_multiplier <= 0:
        raise PricingInputError("complexity_multiplier must be greater than zero")
    if complexity_multiplier != 1:
        before = subtotal
        subtotal = _money(subtotal * complexity_multiplier)
        steps.append(_step("complexity multiplier", "subtotal * complexity_multiplier", before, complexity_multiplier, subtotal - before))

    minimum_charge = _positive(inputs, "minimum_charge")
    if minimum_charge and subtotal < minimum_charge:
        steps.append(_step("minimum charge", "max(subtotal, minimum_charge)", subtotal, minimum_charge, minimum_charge - subtotal))
        subtotal = minimum_charge

    rush_surcharge = _positive(inputs, "rush_surcharge")
    if rush_surcharge:
        steps.append(_step("rush/custom surcharge", "flat surcharge", 1, rush_surcharge, rush_surcharge))
        subtotal = _money(subtotal + rush_surcharge)

    if not steps:
        raise PricingInputError(f"No deterministic pricing inputs supplied for {category}")
    return str(method), steps, subtotal


def price_workroom_item(
    product_category: str,
    pricing_inputs: dict[str, Any] | None = None,
    *,
    discount_type: str | None = "dollar",
    discount_amount: float = 0,
    tax_policy: dict[str, Any] | None = None,
    deposit_required: bool = True,
    deposit_percent: float = 50,
    override_amount: float | None = None,
    override_reason: str | None = None,
    source_quote_id: str | None = None,
    source_line_item_id: str | None = None,
) -> dict[str, Any]:
    inputs = deepcopy(pricing_inputs or {})
    category = _category(product_category, WORKROOM_CATEGORY_ALIASES, "workroom")
    method, steps, subtotal = _sum_component_steps(inputs, category, "workroom")
    return _apply_totals(
        business_unit="workroom",
        module="empire_workroom",
        product_category=category,
        pricing_method=method,
        pricing_inputs=inputs,
        rate_table_version=WORKROOM_RATE_TABLE_VERSION,
        calculation_steps=steps,
        calculated_subtotal=subtotal,
        discount_type=discount_type,
        discount_amount=discount_amount,
        tax_policy=tax_policy,
        deposit_required=deposit_required,
        deposit_percent=deposit_percent,
        override_amount=override_amount,
        override_reason=override_reason,
        source_quote_id=source_quote_id,
        source_line_item_id=source_line_item_id,
    )


def _woodcraft_component_steps(inputs: dict[str, Any], category: str) -> tuple[str, list[dict[str, Any]], float]:
    steps: list[dict[str, Any]] = []
    method = inputs.get("pricing_method") or category

    sheet_count = _positive(inputs, "sheet_count", _positive(inputs, "sheets", 0))
    sheet_cost = _positive(inputs, "cost_per_sheet")
    board_feet = _positive(inputs, "board_feet")
    cost_per_board_foot = _positive(inputs, "cost_per_board_foot")
    waste_factor = _positive(inputs, "waste_factor", 0)
    markup_percent = _positive(inputs, "markup_percent", 0)

    if sheet_count or sheet_cost:
        base = sheet_count * sheet_cost * (1 + waste_factor)
        amount = base * (1 + markup_percent / 100)
        steps.append(_step("sheet goods", "sheets * cost_per_sheet * (1 + waste_factor) * (1 + markup)", sheet_count, sheet_cost, amount, waste_factor=waste_factor, markup_percent=markup_percent))

    if board_feet or cost_per_board_foot:
        base = board_feet * cost_per_board_foot * (1 + waste_factor)
        amount = base * (1 + markup_percent / 100)
        steps.append(_step("board-foot material", "board_feet * cost_per_board_foot * (1 + waste_factor) * (1 + markup)", board_feet, cost_per_board_foot, amount, waste_factor=waste_factor, markup_percent=markup_percent))

    machine_minutes = _positive(inputs, "machine_minutes", _positive(inputs, "cnc_minutes", 0))
    machine_rate = _positive(inputs, "machine_rate_per_hour", 95)
    if machine_minutes:
        amount = (machine_minutes / 60) * machine_rate
        steps.append(_step("CNC/router machine time", "(machine_minutes / 60) * machine_rate_per_hour", machine_minutes, machine_rate, amount))

    design_hours = _positive(inputs, "design_hours", _positive(inputs, "drawing_hours", 0))
    design_rate = _positive(inputs, "design_rate", 85)
    if design_hours:
        amount = design_hours * design_rate
        steps.append(_step("design/drawing time", "design_hours * design_rate", design_hours, design_rate, amount))

    assembly_hours = _positive(inputs, "assembly_hours", _positive(inputs, "labor_hours", 0))
    assembly_rate = _positive(inputs, "assembly_rate", _positive(inputs, "labor_rate", 75))
    if assembly_hours:
        amount = assembly_hours * assembly_rate
        steps.append(_step("assembly labor", "assembly_hours * assembly_rate", assembly_hours, assembly_rate, amount))

    finishing_hours = _positive(inputs, "finishing_hours")
    finishing_rate = _positive(inputs, "finishing_rate", 70)
    finishing_sqft = _positive(inputs, "finishing_square_feet", _positive(inputs, "finish_square_feet", 0))
    finishing_sqft_rate = _positive(inputs, "finishing_square_foot_rate")
    if finishing_hours:
        amount = finishing_hours * finishing_rate
        steps.append(_step("finishing labor", "finishing_hours * finishing_rate", finishing_hours, finishing_rate, amount))
    if finishing_sqft:
        amount = finishing_sqft * finishing_sqft_rate
        steps.append(_step("finishing square footage", "finishing_square_feet * finishing_square_foot_rate", finishing_sqft, finishing_sqft_rate, amount))

    hardware_cost = _positive(inputs, "hardware_cost")
    if hardware_cost:
        amount = hardware_cost * (1 + markup_percent / 100)
        steps.append(_step("hardware", "hardware_cost * (1 + markup_percent)", hardware_cost, markup_percent, amount))

    delivery_install_cost = _positive(inputs, "delivery_install_cost", _positive(inputs, "install_cost", 0))
    if delivery_install_cost:
        steps.append(_step("delivery/install", "fixed delivery or install cost", 1, delivery_install_cost, delivery_install_cost))

    material_cost = _positive(inputs, "material_cost")
    if material_cost:
        amount = material_cost * (1 + markup_percent / 100)
        steps.append(_step("material markup", "material_cost * (1 + markup_percent)", material_cost, markup_percent, amount))

    for item in inputs.get("materials", []) or []:
        if not isinstance(item, dict):
            raise PricingInputError("materials must be objects")
        qty = float(item.get("quantity", 1) or 1)
        unit_cost = float(item.get("cost_per_unit", item.get("unit_cost", 0)) or 0)
        item_markup = float(item.get("markup_percent", markup_percent) or 0)
        amount = qty * unit_cost * (1 + item_markup / 100)
        if amount:
            steps.append(_step(item.get("description") or item.get("name") or "material", "quantity * unit_cost * (1 + markup_percent)", qty, unit_cost, amount, markup_percent=item_markup))

    fixed_price = inputs.get("fixed_price", inputs.get("service_price"))
    if fixed_price is not None:
        fixed = _positive({"fixed_price": fixed_price}, "fixed_price")
        steps.append(_step("fixed service price", "fixed_price", 1, fixed, fixed))
        method = "fixed_service_price"

    subtotal = _money(sum(step["amount"] for step in steps))
    complexity_multiplier = _positive(inputs, "complexity_multiplier", 1)
    if complexity_multiplier <= 0:
        raise PricingInputError("complexity_multiplier must be greater than zero")
    if complexity_multiplier != 1:
        before = subtotal
        subtotal = _money(subtotal * complexity_multiplier)
        steps.append(_step("complexity multiplier", "subtotal * complexity_multiplier", before, complexity_multiplier, subtotal - before))

    minimum_charge = _positive(inputs, "minimum_charge")
    if minimum_charge and subtotal < minimum_charge:
        steps.append(_step("minimum charge", "max(subtotal, minimum_charge)", subtotal, minimum_charge, minimum_charge - subtotal))
        subtotal = minimum_charge

    if not steps:
        raise PricingInputError(f"No deterministic pricing inputs supplied for {category}")
    return str(method), steps, subtotal


def price_woodcraft_item(
    product_category: str,
    pricing_inputs: dict[str, Any] | None = None,
    *,
    discount_type: str | None = "dollar",
    discount_amount: float = 0,
    tax_policy: dict[str, Any] | None = None,
    deposit_required: bool = True,
    deposit_percent: float = 50,
    override_amount: float | None = None,
    override_reason: str | None = None,
    source_quote_id: str | None = None,
    source_line_item_id: str | None = None,
) -> dict[str, Any]:
    inputs = deepcopy(pricing_inputs or {})
    category = _category(product_category, WOODCRAFT_CATEGORY_ALIASES, "woodcraft")
    method, steps, subtotal = _woodcraft_component_steps(inputs, category)
    return _apply_totals(
        business_unit="woodcraft",
        module="craftforge",
        product_category=category,
        pricing_method=method,
        pricing_inputs=inputs,
        rate_table_version=WOODCRAFT_RATE_TABLE_VERSION,
        calculation_steps=steps,
        calculated_subtotal=subtotal,
        discount_type=discount_type,
        discount_amount=discount_amount,
        tax_policy=tax_policy,
        deposit_required=deposit_required,
        deposit_percent=deposit_percent,
        override_amount=override_amount,
        override_reason=override_reason,
        source_quote_id=source_quote_id,
        source_line_item_id=source_line_item_id,
    )


# ===========================================================================
# 2026-07-06 sprint 1a — per-treatment line pricers
#
# Every function below returns a dict with EXACTLY these keys:
#   category, unit, business_unit, computed (breakdown),
#   proposed_price, final_price (=proposed initially), price_overridden (=False),
#   pricing_engine_version
#
# 1b will add PATCH endpoints that mutate final_price + price_overridden
# for each quote_line_items row. The existing price_workroom_item and
# price_woodcraft_item are LEFT UNTOUCHED for backward compatibility.
# ===========================================================================
import math

from app.data.product_catalog import PRICING_SPECS


def _compute_widths(window_width_in: float, fullness: float, fabric_width_in: float) -> int:
    if fullness <= 0 or fabric_width_in <= 0:
        raise PricingInputError("fullness and fabric_width must be positive")
    return int(math.ceil(window_width_in * fullness / fabric_width_in))


def _over_length_escalator(
    length_in: float,
    *,
    threshold: float,
    base_below: float,
    add_per_inch=None,
    add_above=None,
    floor_above: float,
) -> float:
    """Shared escalator parameterized per style.
    regular:    max(length_in * add_per_inch, floor_above)
    ripplefold: max(length_in + add_above,   floor_above)
    """
    if length_in <= threshold:
        return float(base_below)
    if add_per_inch is not None:
        return float(max(length_in * add_per_inch, floor_above))
    if add_above is not None:
        return float(max(length_in + add_above, floor_above))
    raise PricingInputError("escalator misconfigured: need add_per_inch or add_above")


def _line_result(category: str, unit: str, business_unit: str, computed: dict,
                 proposed: float) -> dict:
    """Canonical result shape. 1b will edit final_price + price_overridden."""
    p = round(float(proposed), 2)
    return {
        "category": category,
        "unit": unit,
        "business_unit": business_unit,
        "computed": computed,
        "proposed_price": p,
        "final_price": p,
        "price_overridden": False,
        "pricing_engine_version": PRICING_ENGINE_VERSION,
    }


# ---------------------------------------------------------------------------
# Drapery
# ---------------------------------------------------------------------------
def price_drapery(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["drapery"]
    style = (inputs.get("style") or "regular").lower()
    if style not in spec["styles"]:
        raise PricingInputError(f"drapery style must be one of {list(spec['styles'])}")

    style_spec = spec["styles"][style]
    window_width_in = _positive(inputs, "window_width_in")
    length_in       = _positive(inputs, "length_in")
    fullness        = _positive(inputs, "fullness",        spec["default_fullness"])
    fabric_width_in = _positive(inputs, "fabric_width_in", spec["default_fabric_width_in"])
    leading_edges   = int(_positive(inputs, "leading_edges", 0))

    widths = _compute_widths(window_width_in, fullness, fabric_width_in)

    if style == "ripplefold":
        price_per_width = _over_length_escalator(
            length_in,
            threshold=style_spec["over_threshold_in"],
            base_below=style_spec["base_rate_below_threshold"],
            add_above=style_spec["add_above"],
            floor_above=style_spec["over_floor"],
        )
    else:
        price_per_width = _over_length_escalator(
            length_in,
            threshold=style_spec["over_threshold_in"],
            base_below=style_spec["base_rate_below_threshold"],
            add_per_inch=style_spec["add_per_inch"],
            floor_above=style_spec["over_floor"],
        )

    base    = widths * price_per_width
    banding = leading_edges * spec["banding_per_leading_edge"]

    lining_type  = inputs.get("lining_type")
    lining_cost  = 0.0
    lining_yards = 0.0
    if lining_type:
        rate = spec["linings"].get(lining_type)
        if rate is None:
            raise PricingInputError(f"unknown lining_type '{lining_type}'")
        yards_per_width = math.ceil(length_in / 36)
        lining_yards = widths * yards_per_width
        lining_cost  = round(lining_yards * rate, 2)

    proposed = round(base + banding + lining_cost, 2)

    return _line_result(
        "drapery", "width", business_unit,
        {"widths": widths,
         "style": style,
         "price_per_width": price_per_width,
         "base": round(base, 2),
         "banding": round(banding, 2),
         "lining_type": lining_type,
         "lining_yards": lining_yards,
         "lining_cost": lining_cost},
        proposed,
    )


# ---------------------------------------------------------------------------
# Roman shade — sqft line + companion fabric proposal (NO fullness factor)
# ---------------------------------------------------------------------------
def propose_roman_shade_fabric(width_in: float, height_in: float,
                                fabric_width_in: float = 54,
                                default_price_per_yard: float = 30.0) -> dict:
    """Returns a fabric_only proposal SPECIFICALLY for a roman shade.
    Per 1a-correction: no fullness multiplier. Both price_per_yard and
    yards_needed are founder-editable. fabric_spec_url is stored for
    future inpaint-mockup integration.
    """
    if fabric_width_in <= 0:
        raise PricingInputError("fabric_width_in must be positive")
    widths = math.ceil(width_in / fabric_width_in)
    proposed_yards = round((widths * height_in) / 36.0, 2)
    proposed = round(proposed_yards * default_price_per_yard, 2)
    return _line_result(
        "fabric_only", "yard", "workroom",
        {"subcategory": "roman_shade_fabric",
         "proposed_yards": proposed_yards,
         "proposed_yards_editable": True,
         "default_price_per_yard": default_price_per_yard,
         "default_price_per_yard_editable": True,
         "fabric_width_in_used": fabric_width_in,
         "fabric_width_in_editable": True,
         "fabric_spec_url": None,
         "fabric_spec_url_editable": True,
         "note": ("Roman shade fabric: NO fullness factor. Founder edits "
                  "price_per_yard, yards_needed, and (optionally) fabric_width_in. "
                  "fabric_spec_url enables future auto-lookup + inpaint mockup.")},
        proposed,
    )


def price_roman_shade(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["roman_shade"]
    # D37 / H77 — width_in and height_in are REQUIRED. Zero dims silently
    # priced at $0.00; the engine refuses instead.
    width_in  = _require_positive(inputs, "width_in",  category="roman_shade")
    height_in = _require_positive(inputs, "height_in", category="roman_shade")
    rate      = _positive(inputs, "rate_per_sqft", spec["base_rate"])
    sqft      = (width_in * height_in) / 144.0
    proposed  = round(sqft * rate, 2)

    # Companion fabric proposal (separate fabric_only line item; 1b inserts both)
    fabric_width_in = _positive(inputs, "fabric_width_in",
                                spec["fabric"]["default_fabric_width_in"])
    default_price_per_yard = _positive(inputs, "default_price_per_yard",
                                       spec["fabric"]["default_price_per_yard"])
    fabric_proposal = propose_roman_shade_fabric(
        width_in=width_in, height_in=height_in,
        fabric_width_in=fabric_width_in,
        default_price_per_yard=default_price_per_yard,
    )

    return _line_result(
        "roman_shade", "sqft", business_unit,
        {"width_in": width_in, "height_in": height_in,
         "sqft": round(sqft, 2), "rate_per_sqft": rate,
         "fabric_proposal": fabric_proposal},
        proposed,
    )


# ---------------------------------------------------------------------------
# Valance
# ---------------------------------------------------------------------------
def price_valance(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["valance"]
    # D37 / H77 — width_in REQUIRED. Zero width silently priced at $0.00.
    width_in  = _require_positive(inputs, "width_in", category="valance")
    rate      = _positive(inputs, "rate_per_lineal_ft", spec["base_rate"])
    lineal_ft = width_in / 12.0
    proposed  = round(lineal_ft * rate, 2)
    return _line_result(
        "valance", "lineal_ft", business_unit,
        {"width_in": width_in, "lineal_ft": round(lineal_ft, 2),
         "rate_per_lineal_ft": rate},
        proposed,
    )


# ---------------------------------------------------------------------------
# Cornice — business_unit is an INPUT (default 'workroom'); 1c/1d may split
# ---------------------------------------------------------------------------
def price_cornice(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["cornice"]
    # D37 / H77 — width_in REQUIRED. Zero width silently priced at $0.00.
    width_in  = _require_positive(inputs, "width_in", category="cornice")
    rate      = _positive(inputs, "rate_per_lineal_ft", spec["base_rate"])
    lineal_ft = width_in / 12.0
    proposed  = round(lineal_ft * rate, 2)
    return _line_result(
        "cornice", "lineal_ft", business_unit,
        {"width_in": width_in, "lineal_ft": round(lineal_ft, 2),
         "rate_per_lineal_ft": rate,
         "note": ("Caller-supplied business_unit (default 'workroom'). 1c/1d may "
                  "split cornice into WoodCraft frame/build + Workroom covering lines.")},
        proposed,
    )


# ---------------------------------------------------------------------------
# Fabric-only (founder-editable)
# ---------------------------------------------------------------------------
def price_fabric(inputs: dict, *, business_unit: str = "workroom") -> dict:
    """Both price_per_yard and yards_needed are founder-editable.

    D37 / H77 — both are REQUIRED. Missing or zero silently produced $0.00;
    the engine refuses instead.
    """
    price_per_yard  = _require_positive(inputs, "price_per_yard", category="fabric_only")
    yards_needed    = _require_positive(inputs, "yards_needed",   category="fabric_only")
    yards_override  = bool(inputs.get("yards_override", False))
    spec_url        = inputs.get("fabric_spec_url")  # future auto-lookup
    proposed        = round(price_per_yard * yards_needed, 2)
    return _line_result(
        "fabric_only", "yard", business_unit,
        {"price_per_yard": price_per_yard,
         "yards_needed": yards_needed,
         "yards_override": yards_override,
         "fabric_spec_url": spec_url,
         "editable_fields": ["price_per_yard", "yards_needed", "fabric_spec_url"]},
        proposed,
    )


# ---------------------------------------------------------------------------
# Hardware — SUGGESTIONS only; final_price founder-editable (already in
# _line_result with price_overridden=False)
# ---------------------------------------------------------------------------
def price_hardware_rod(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["hardware_rod_1_1_8"]
    # D37 / H77 — width_in REQUIRED.
    width_in = _require_positive(inputs, "width_in", category="hardware_rod_1_1_8")
    width_ft = width_in / 12.0
    units    = int(math.ceil(width_ft / 6))
    rate     = _positive(inputs, "rate_per_run", spec["base_rate"])
    proposed = round(units * rate, 2)
    return _line_result(
        "hardware_rod_1_1_8", "rod_run", business_unit,
        {"width_ft": round(width_ft, 2), "units": units, "rate_per_run": rate,
         "suggestion_only": True},
        proposed,
    )


def price_hardware_ripplefold_track(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["hardware_ripplefold_track"]
    # D37 / H77 — width_in REQUIRED.
    width_in = _require_positive(inputs, "width_in", category="hardware_ripplefold_track")
    width_ft = width_in / 12.0
    units    = int(math.ceil(width_ft / 6))
    rate     = _positive(inputs, "rate_per_run", spec["base_rate"])
    proposed = round(units * rate, 2)
    return _line_result(
        "hardware_ripplefold_track", "track_run", business_unit,
        {"width_ft": round(width_ft, 2), "units": units, "rate_per_run": rate,
         "suggestion_only": True},
        proposed,
    )


def price_hardware_rings(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["hardware_rings"]
    # D37 / H77 — packs REQUIRED (used as the unit count). widths is optional
    # context (used only for the suggested default). packs=0 silently priced
    # at $0.00; refuse instead.
    widths = int(_positive(inputs, "widths", 1))
    packs  = int(_require_positive(inputs, "packs", category="hardware_rings"))
    rate   = _positive(inputs, "rate_per_pack", spec["base_rate"])
    proposed = round(packs * rate, 2)
    return _line_result(
        "hardware_rings", "pack_8", business_unit,
        {"widths": widths, "packs": packs, "rate_per_pack": rate,
         "suggestion_only": True},
        proposed,
    )


def price_hardware_brackets(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["hardware_brackets"]
    # D37 / H77 — count REQUIRED (default derives from width_in lookup).
    # Either width_in OR an explicit count must be supplied; without either,
    # we'd default to 2 brackets ($58) and silently price something that
    # the founder never asked for.
    if "count" in inputs and inputs["count"] is not None:
        count = int(_require_positive(inputs, "count", category="hardware_brackets"))
        width_in = _positive(inputs, "width_in")  # for the computed breakdown
        width_ft = width_in / 12.0 if width_in else 0.0
        default_count = count
    else:
        width_in = _require_positive(inputs, "width_in", category="hardware_brackets")
        width_ft = width_in / 12.0
        if width_ft <= 6:
            default_count = spec["default_count_by_width_ft"]["<=6"]
        elif width_ft <= 12:
            default_count = spec["default_count_by_width_ft"]["6-12"]
        else:
            default_count = spec["default_count_by_width_ft"][">12"]
        count = default_count
    rate    = _positive(inputs, "rate_per_bracket", spec["base_rate"])
    proposed = round(count * rate, 2)
    return _line_result(
        "hardware_brackets", "bracket", business_unit,
        {"width_ft": round(width_ft, 2),
         "default_count": default_count,
         "count": count, "rate_per_bracket": rate,
         "suggestion_only": True},
        proposed,
    )


# ---------------------------------------------------------------------------
# Labor — separate line per treatment
# ---------------------------------------------------------------------------
def price_labor(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["labor"]
    # D37 / H77 — hours REQUIRED. Zero hours silently priced at $0.00.
    hours    = _require_positive(inputs, "hours", category="labor")
    rate     = _positive(inputs, "rate_per_hour", spec["base_rate"])
    proposed = round(hours * rate, 2)
    return _line_result(
        "labor", "hour", business_unit,
        {"hours": hours, "rate_per_hour": rate},
        proposed,
    )


# ---------------------------------------------------------------------------
# Pillow — fully editable; welting +$10, flange +$20
# ---------------------------------------------------------------------------
def price_pillow(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["pillow"]
    qty          = int(_positive(inputs, "quantity", 1))
    # D37 / H77 — unit_price REQUIRED. Zero price silently priced at $0.00.
    unit_price   = _require_positive(inputs, "unit_price", category="pillow")
    has_welting  = bool(inputs.get("welting", False))
    has_flange   = bool(inputs.get("flange", False))
    welting_add  = spec["welting_add"] if has_welting else 0
    flange_add   = spec["flange_add"]  if has_flange  else 0
    suggested    = spec["base_unit_20x20"] + welting_add + flange_add
    proposed     = round(qty * unit_price, 2)
    return _line_result(
        "pillow", "each", business_unit,
        {"quantity": qty,
         "welting": has_welting,
         "flange": has_flange,
         "base_unit": spec["base_unit_20x20"],
         "welting_add": welting_add,
         "flange_add": flange_add,
         "suggested_unit_price": suggested,
         "unit_price_used": unit_price,
         "editable_fields": ["unit_price", "welting", "flange", "quantity"],
         "note": "Pillow 20x20 base $30; welting +$10; flange +$20. Founder sets final unit_price."},
        proposed,
    )


# ---------------------------------------------------------------------------
# Cover — fully editable
# ---------------------------------------------------------------------------
def price_cover(inputs: dict, *, business_unit: str = "workroom") -> dict:
    # D37 / H77 — unit_price is REQUIRED. Quantity defaults to 1; the
    # $0.00 placeholder in PRICING_SPECS["cover"] is NOT reachable as a
    # price from the engine.
    qty        = int(_positive(inputs, "quantity", 1))
    unit_price = _require_positive(inputs, "unit_price", category="cover")
    proposed   = round(qty * unit_price, 2)
    return _line_result(
        "cover", "each", business_unit,
        {"quantity": qty, "unit_price_used": unit_price,
         "editable_fields": ["unit_price", "quantity"]},
        proposed,
    )


# ---------------------------------------------------------------------------
# D38 / H77 — NEW line pricers
#
# Five categories land in this dispatch:
#   - com_fabric         : the ONE permitted $0.00 path (customer_supplied=true)
#   - hardware_rod_set   : flat rate 4-8 ft, founder override beyond
#   - hardware_ripplefold_set : flat rate 4-8 ft, founder override beyond
#   - installation       : per-treatment install (roman_shade $95/each,
#                          drapery $145/first 8 ft; beyond 8 ft founder override)
#   - manual_line        : pure pass-through; engine records, does not compute
#
# All five coexist with the existing component pricers (price_hardware_rod /
# price_hardware_ripplefold_track / etc.) — those stay; the new SET categories
# are founder-shaped bundles. Roman shade lining remains included in the shade
# price; price_roman_shade still does NOT emit a separate lining line.
# ---------------------------------------------------------------------------
def _price_in_range_or_override(
    *,
    category: str,
    width_in: float,
    spec: dict,
) -> tuple[float, dict]:
    """Helper for the flat-rate-in-range categories.
    Returns (proposed_price, computed_overrides). Always raises if out of range
    with no override. Never extrapolates.
    """
    width_ft = round(width_in / 12.0, 4)
    lo = float(spec["range_ft_min"])
    hi = float(spec["range_ft_max"])
    flat = float(spec["flat_rate_in_range"])
    if lo <= width_ft <= hi:
        return round(flat, 2), {
            "width_ft": width_ft,
            "in_range": True,
            "flat_rate_in_range": flat,
            "range_ft_min": lo,
            "range_ft_max": hi,
        }
    # Out of range — founder must supply override_price.
    raise PricingInputError(
        f"{category}: width_ft={width_ft} is outside allowed range "
        f"[{lo}, {hi}] ft — provide inputs['override_price']; "
        f"engine never extrapolates"
    )


def price_hardware_rod_set(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["hardware_rod_set"]
    width_in = _require_positive(inputs, "width_in", category="hardware_rod_set")
    override = inputs.get("override_price")
    if 4.0 <= (width_in / 12.0) <= 8.0:
        proposed, computed = _price_in_range_or_override(
            category="hardware_rod_set", width_in=width_in, spec=spec,
        )
    elif override is not None:
        try:
            override_val = float(override)
        except (TypeError, ValueError):
            raise PricingInputError(
                f"hardware_rod_set: override_price must be numeric (got {override!r})"
            )
        if override_val < 0:
            raise PricingInputError(
                f"hardware_rod_set: override_price must be >= 0 "
                f"(got {override_val})"
            )
        proposed = round(override_val, 2)
        computed = {
            "width_ft": round(width_in / 12.0, 4),
            "in_range": False,
            "override_used": True,
            "override_price": proposed,
            "range_ft_min": spec["range_ft_min"],
            "range_ft_max": spec["range_ft_max"],
        }
    else:
        raise PricingInputError(
            f"hardware_rod_set: width_ft={round(width_in / 12.0, 4)} "
            f"is outside allowed range [{spec['range_ft_min']}, "
            f"{spec['range_ft_max']}] ft — provide "
            f"inputs['override_price']; engine never extrapolates"
        )
    return _line_result("hardware_rod_set", "set", business_unit, computed, proposed)


def price_hardware_ripplefold_set(inputs: dict, *, business_unit: str = "workroom") -> dict:
    spec = PRICING_SPECS["hardware_ripplefold_set"]
    width_in = _require_positive(inputs, "width_in", category="hardware_ripplefold_set")
    override = inputs.get("override_price")
    if 4.0 <= (width_in / 12.0) <= 8.0:
        proposed, computed = _price_in_range_or_override(
            category="hardware_ripplefold_set", width_in=width_in, spec=spec,
        )
    elif override is not None:
        try:
            override_val = float(override)
        except (TypeError, ValueError):
            raise PricingInputError(
                f"hardware_ripplefold_set: override_price must be numeric "
                f"(got {override!r})"
            )
        if override_val < 0:
            raise PricingInputError(
                f"hardware_ripplefold_set: override_price must be >= 0 "
                f"(got {override_val})"
            )
        proposed = round(override_val, 2)
        computed = {
            "width_ft": round(width_in / 12.0, 4),
            "in_range": False,
            "override_used": True,
            "override_price": proposed,
            "range_ft_min": spec["range_ft_min"],
            "range_ft_max": spec["range_ft_max"],
        }
    else:
        raise PricingInputError(
            f"hardware_ripplefold_set: width_ft={round(width_in / 12.0, 4)} "
            f"is outside allowed range [{spec['range_ft_min']}, "
            f"{spec['range_ft_max']}] ft — provide "
            f"inputs['override_price']; engine never extrapolates"
        )
    return _line_result(
        "hardware_ripplefold_set", "set", business_unit, computed, proposed,
    )


def price_installation(inputs: dict, *, business_unit: str = "workroom") -> dict:
    """D38 / H77 — installation line pricer.
    drapery:     $145 first 8 ft; beyond 8 ft founder supplies override_price.
    roman_shade: $95 each (quantity * $95); stays within founder-shaped bounds.
    """
    spec = PRICING_SPECS["installation"]
    treatment = (inputs.get("treatment") or "").lower()
    if treatment not in spec["sub_rates"]:
        raise PricingInputError(
            f"installation: treatment must be one of "
            f"{list(spec['sub_rates'].keys())} (got {treatment!r})"
        )
    sub = spec["sub_rates"][treatment]

    if treatment == "roman_shade":
        quantity = _require_positive(inputs, "quantity", category="installation")
        proposed = round(float(sub["rate"]) * quantity, 2)
        computed = {
            "treatment": "roman_shade",
            "rate": sub["rate"],
            "unit": "each",
            "quantity": quantity,
        }
    elif treatment == "drapery":
        # Either width_in/width_ft supplied, or override_price for out-of-first-8ft jobs.
        width_ft_raw = inputs.get("width_ft")
        width_in_raw = inputs.get("width_in")
        if width_ft_raw is None and width_in_raw is None:
            raise PricingInputError(
                "installation: drapery requires 'width_ft' or 'width_in' "
                "(or 'override_price' for jobs beyond 8 ft)"
            )
        if width_ft_raw is None:
            width_in = _require_positive(inputs, "width_in", category="installation")
            width_ft = round(width_in / 12.0, 4)
        else:
            try:
                width_ft = float(width_ft_raw)
            except (TypeError, ValueError):
                raise PricingInputError(
                    f"installation: width_ft must be numeric (got {width_ft_raw!r})"
                )
            if width_ft <= 0:
                raise PricingInputError(
                    f"installation: width_ft must be > 0 (got {width_ft})"
                )

        if width_ft <= 8.0:
            proposed = round(float(sub["rate"]), 2)
            computed = {
                "treatment": "drapery",
                "rate": sub["rate"],
                "unit": "first_8ft",
                "width_ft": width_ft,
            }
        else:
            override = inputs.get("override_price")
            if override is None:
                raise PricingInputError(
                    f"installation: drapery width_ft={width_ft} is beyond "
                    f"the first 8 ft — provide inputs['override_price'] for "
                    f"the whole job; engine never extrapolates"
                )
            try:
                override_val = float(override)
            except (TypeError, ValueError):
                raise PricingInputError(
                    f"installation: override_price must be numeric "
                    f"(got {override!r})"
                )
            if override_val < 0:
                raise PricingInputError(
                    f"installation: override_price must be >= 0 "
                    f"(got {override_val})"
                )
            proposed = round(override_val, 2)
            computed = {
                "treatment": "drapery",
                "width_ft": width_ft,
                "override_used": True,
                "override_price": proposed,
            }
    else:
        # Should be unreachable given the membership check above.
        raise PricingInputError(f"installation: unhandled treatment {treatment!r}")

    return _line_result("installation", "each_or_first_8ft", business_unit, computed, proposed)


def price_com_fabric(inputs: dict, *, business_unit: str = "workroom") -> dict:
    """D38 / H77 — the ONE permitted $0.00 path.

    Two modes:
      customer_supplied=False → behaves like fabric_only; unit_price REQUIRED
        via _require_positive, raises PricingInputError without it. This
        matches R10/R11 and the existing H77 zero-guard.
      customer_supplied=True  → proposed_price = 0.00, with fabric_name AND
        quantity required and present in `computed`. Margin computations
        must exclude customer_supplied lines (callers check computed).

    Anti-bypass: this is one path, provable. _require_positive is unchanged.
    """
    customer_supplied = bool(inputs.get("customer_supplied", False))
    fabric_name = inputs.get("fabric_name")

    if not customer_supplied:
        # Re-use fabric_only semantics: unit_price + (optional) yards_needed
        # both required via _require_positive. The factory function
        # `price_fabric` enforces this — call through for consistency.
        return price_fabric(inputs, business_unit=business_unit)

    # customer_supplied=True path
    if fabric_name is None or str(fabric_name).strip() == "":
        raise PricingInputError(
            "com_fabric: customer_supplied=true requires 'fabric_name' "
            "(non-empty string) — refusing to emit an empty $0.00 line"
        )
    quantity = _require_positive(inputs, "quantity", category="com_fabric")

    return _line_result(
        "com_fabric", "customer_supplied", business_unit,
        {
            "customer_supplied": True,
            "fabric_name": str(fabric_name).strip(),
            "quantity": quantity,
            "label": "COM",
            "note": (
                "Customer-supplied material. $0.00 — the ONE permitted zero. "
                "Excluded from margin."
            ),
        },
        0.0,
    )


def price_manual_line(inputs: dict, *, business_unit: str = "workroom") -> dict:
    """D38 / H77 — pure pass-through. founder supplies description, unit_price,
    quantity. Engine records, does not compute. unit_price required via
    _require_positive — engine raises without it.
    """
    description = inputs.get("description")
    if description is None or str(description).strip() == "":
        raise PricingInputError(
            "manual_line: 'description' is required and must be non-empty"
        )
    unit_price = _require_positive(inputs, "unit_price", category="manual_line")
    quantity = _positive(inputs, "quantity", 1)
    if quantity <= 0:
        raise PricingInputError("manual_line: quantity must be > 0")
    proposed = round(quantity * unit_price, 2)
    return _line_result(
        "manual_line", "each", business_unit,
        {"description": str(description).strip(),
         "quantity": quantity,
         "unit_price_used": unit_price,
         "editable_fields": ["description", "unit_price", "quantity"],
         "note": "Manual pass-through — engine records, does not compute."},
        proposed,
    )


# ---------------------------------------------------------------------------
# Dispatch table + new entry point (1b will call this from routers)
# ---------------------------------------------------------------------------
WORKROOM_LINE_PRICERS = {
    "drapery":                   price_drapery,
    "roman_shade":               price_roman_shade,
    "valance":                   price_valance,
    "cornice":                   price_cornice,
    "fabric_only":               price_fabric,
    "hardware_rod_1_1_8":        price_hardware_rod,
    "hardware_ripplefold_track": price_hardware_ripplefold_track,
    "hardware_rings":            price_hardware_rings,
    "hardware_brackets":         price_hardware_brackets,
    "labor":                     price_labor,
    "pillow":                    price_pillow,
    "cover":                     price_cover,
    # D38 / H77 — NEW entries below (continues H77).
    "com_fabric":                price_com_fabric,
    "hardware_rod_set":          price_hardware_rod_set,
    "hardware_ripplefold_set":   price_hardware_ripplefold_set,
    "installation":              price_installation,
    "manual_line":               price_manual_line,
}


def price_workroom_line(category: str, inputs: dict, *,
                        business_unit: str = "workroom") -> dict:
    """Sprint 1a entry point.

    Returns a dict with proposed_price, final_price (=proposed), price_overridden
    (=False), business_unit, computed breakdown, pricing_engine_version.
    1b will add PATCH endpoints that mutate final_price + price_overridden
    on quote_line_items rows.
    """
    key = (category or "").lower()
    if key not in WORKROOM_LINE_PRICERS:
        raise PricingClassificationError(f"unknown workroom category '{category}'")
    return WORKROOM_LINE_PRICERS[key](inputs, business_unit=business_unit)
