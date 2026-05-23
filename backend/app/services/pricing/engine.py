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
