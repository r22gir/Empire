"""Pricing snapshot preservation for quote/design to invoice flows."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any

from .engine import (
    FORMULA_VERSION,
    PRICING_ENGINE_VERSION,
    WORKROOM_RATE_TABLE_VERSION,
    WOODCRAFT_RATE_TABLE_VERSION,
    calculate_deposit_balance,
    canonical_tax_policy,
)


def _now() -> str:
    return datetime.utcnow().isoformat()


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _qty(value: Any) -> float:
    qty = _money(value)
    return qty if qty > 0 else 1.0


def _line_amount(item: dict[str, Any]) -> float:
    qty = _qty(item.get("quantity", item.get("qty", 1)))
    rate = _money(item.get("unit_price", item.get("rate", 0)))
    explicit = item.get("total", item.get("amount"))
    if explicit not in (None, ""):
        return _money(explicit)
    return _money(qty * rate)


def _line_unit_rate(item: dict[str, Any], total: float) -> float:
    explicit = item.get("unit_price", item.get("rate"))
    if explicit not in (None, ""):
        return _money(explicit)
    qty = _qty(item.get("quantity", item.get("qty", 1)))
    return _money(total / qty) if qty else total


def _jsonish(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def _tax_policy_from_source(source: dict[str, Any], *, name: str) -> dict[str, Any]:
    tax_rate = _money(source.get("tax_rate", 0))
    policy = source.get("tax_policy") or source.get("tax_policy_json")
    parsed = _jsonish(policy)
    if isinstance(parsed, dict):
        parsed.setdefault("tax_rate", tax_rate)
        parsed.setdefault("name", name)
        parsed.setdefault("source", "source_pricing_snapshot")
        parsed.setdefault("taxable", bool(parsed.get("tax_rate") or tax_rate))
        return parsed
    return canonical_tax_policy(
        name=name,
        tax_rate=tax_rate,
        taxable=bool(tax_rate),
        source="approved_source_tax_rate",
    )


def _discount(source: dict[str, Any]) -> tuple[str, float]:
    discount_type = (source.get("discount_type") or "dollar").strip().lower()
    if discount_type == "flat":
        discount_type = "dollar"
    return discount_type, _money(source.get("discount_amount", 0))


def _source_deposit(source: dict[str, Any], final_price: float) -> tuple[bool, float, float]:
    deposit = source.get("deposit") if isinstance(source.get("deposit"), dict) else {}
    snapshot = _jsonish(source.get("pricing_snapshot_json", source.get("pricing_snapshot")))
    if not isinstance(snapshot, dict):
        snapshot = {}

    def amount_candidate(value: Any) -> float:
        if isinstance(value, bool):
            return 0.0
        return _money(value)

    amount = _money(
        amount_candidate(deposit.get("deposit_amount"))
        or amount_candidate(source.get("deposit_amount"))
        or amount_candidate(source.get("deposit_required"))
        or 0
    )
    percent = _money(
        deposit.get("deposit_percent")
        or source.get("deposit_percent")
        or 0
    )
    if not amount and percent:
        amount = _money(final_price * (percent / 100))
    if not amount:
        amount = amount_candidate(snapshot.get("deposit_amount"))
    return bool(amount), amount, _money(final_price - amount)


def _source_total(source: dict[str, Any], subtotal: float, tax_policy: dict[str, Any]) -> tuple[float, float]:
    tax_amount = source.get("tax_amount")
    if tax_amount in (None, ""):
        tax_amount = subtotal * _money(tax_policy.get("tax_rate", 0)) if tax_policy.get("taxable") else 0
    tax_amount = _money(tax_amount)
    total = source.get("total")
    if total in (None, ""):
        discount_type, discount_amount = _discount(source)
        applied_discount = _money(subtotal * (discount_amount / 100)) if discount_type == "percent" else discount_amount
        total = subtotal - applied_discount + tax_amount
    return tax_amount, _money(total)


def _preserved_snapshot(
    *,
    business_unit: str,
    module: str,
    product_category: str,
    pricing_method: str,
    pricing_inputs: dict[str, Any],
    calculated_subtotal: float,
    tax_policy: dict[str, Any],
    tax_amount: float,
    discount_type: str,
    discount_amount: float,
    final_price: float,
    deposit_required: bool,
    deposit_amount: float,
    balance_due: float,
    source_quote_id: str | None,
    source_line_item_id: str | None,
    rate_table_version: str,
    override_amount: float | None = None,
    override_reason: str | None = None,
    original_snapshot: Any = None,
) -> dict[str, Any]:
    steps = [{
        "label": "approved source price",
        "formula": "copied from approved quote/design snapshot or stored approved source fields",
        "amount": _money(calculated_subtotal),
    }]
    if original_snapshot:
        steps.append({
            "label": "original pricing snapshot",
            "formula": "preserved without recalculation",
            "snapshot": deepcopy(_jsonish(original_snapshot)),
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
        "calculated_subtotal": _money(calculated_subtotal),
        "discount_type": discount_type,
        "discount_amount": _money(discount_amount),
        "tax_policy": deepcopy(tax_policy),
        "tax_amount": _money(tax_amount),
        "deposit_required": bool(deposit_required),
        "deposit_amount": _money(deposit_amount),
        "balance_due": _money(balance_due),
        "override_amount": _money(override_amount) if override_amount is not None else None,
        "override_reason": override_reason,
        "final_price": _money(final_price),
        "created_at": _now(),
        "source_quote_id": source_quote_id,
        "source_line_item_id": str(source_line_item_id) if source_line_item_id is not None else None,
        "pricing_engine_version": PRICING_ENGINE_VERSION,
        "preserved_from_source": True,
    }


def _invoice_line(
    *,
    raw: dict[str, Any],
    description: str,
    quantity: float,
    unit_price: float,
    total: float,
    business_unit: str,
    module: str,
    product_category: str,
    source_quote_id: str | None,
    source_line_item_id: str | None,
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    original_snapshot = raw.get("pricing_snapshot_json", raw.get("pricing_snapshot"))
    snapshot = _jsonish(original_snapshot)
    if not isinstance(snapshot, dict):
        snapshot = _preserved_snapshot(
            business_unit=business_unit,
            module=module,
            product_category=product_category,
            pricing_method=raw.get("pricing_method") or "approved_source_price",
            pricing_inputs=deepcopy(raw),
            calculated_subtotal=total,
            tax_policy=tax_policy,
            tax_amount=0,
            discount_type="dollar",
            discount_amount=0,
            final_price=total,
            deposit_required=False,
            deposit_amount=0,
            balance_due=total,
            source_quote_id=source_quote_id,
            source_line_item_id=source_line_item_id,
            rate_table_version=WORKROOM_RATE_TABLE_VERSION if business_unit == "workroom" else WOODCRAFT_RATE_TABLE_VERSION,
        )
    return {
        "description": description or "Item",
        "quantity": quantity,
        "unit_price": unit_price,
        "unit_rate": unit_price,
        "rate": unit_price,
        "total": _money(total),
        "pricing_method": snapshot.get("pricing_method", raw.get("pricing_method") or "approved_source_price"),
        "pricing_inputs": snapshot.get("pricing_inputs", deepcopy(raw)),
        "pricing_result": {
            "calculated_subtotal": snapshot.get("calculated_subtotal", total),
            "final_price": snapshot.get("final_price", total),
        },
        "pricing_snapshot_json": snapshot,
    }


def _quote_tier_lines(quote: dict[str, Any], selected_tier: str | None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    tiers = quote.get("tiers") or {}
    if not isinstance(tiers, dict):
        return [], None
    selected = selected_tier or quote.get("selected_tier") or "A"
    tier_data = tiers.get(selected) or tiers.get("A") or tiers.get("B") or tiers.get("C")
    lines: list[dict[str, Any]] = []
    if tier_data and tier_data.get("items"):
        for tier_item in tier_data["items"]:
            for li in tier_item.get("line_items", []):
                if isinstance(li, dict):
                    lines.append(li)
    return lines, tier_data


def build_quote_invoice_source(quote: dict[str, Any], quote_id: str, *, selected_tier: str | None = None) -> dict[str, Any]:
    business_unit = (quote.get("business_unit") or quote.get("business") or "workroom").strip().lower()
    if business_unit in {"empire workroom", "all"}:
        business_unit = "workroom"
    if business_unit in {"craftforge", "wood craft"}:
        business_unit = "woodcraft"
    tax_policy = _tax_policy_from_source(quote, name="approved_quote_tax_rate")
    discount_type, discount_amount = _discount(quote)

    invoice_lines: list[dict[str, Any]] = []
    tier_lines, tier_data = _quote_tier_lines(quote, selected_tier)
    if tier_lines:
        for idx, raw in enumerate(tier_lines, start=1):
            total = _line_amount(raw)
            qty = _qty(raw.get("quantity", raw.get("qty", 1)))
            unit_rate = _line_unit_rate(raw, total)
            invoice_lines.append(_invoice_line(
                raw=raw,
                description=raw.get("description", "Item"),
                quantity=qty,
                unit_price=unit_rate,
                total=total,
                business_unit=business_unit,
                module="empire_workroom" if business_unit == "workroom" else "craftforge",
                product_category=raw.get("category") or raw.get("item_type") or "approved_quote_line",
                source_quote_id=quote_id,
                source_line_item_id=raw.get("id", idx),
                tax_policy=tax_policy,
            ))

    if not invoice_lines:
        for room in quote.get("rooms") or []:
            room_name = room.get("name", "Room")
            for idx, raw in enumerate((room.get("items") or room.get("windows") or []), start=1):
                if not isinstance(raw, dict):
                    continue
                total = _line_amount({"total": raw.get("total", raw.get("price", 0)), "quantity": raw.get("quantity", 1), "unit_price": raw.get("unit_price")})
                qty = _qty(raw.get("quantity", 1))
                unit_rate = _line_unit_rate(raw, total)
                description = f"{room_name} - {raw.get('name') or raw.get('type') or raw.get('treatment_type') or 'Item'}"
                invoice_lines.append(_invoice_line(
                    raw=raw,
                    description=description,
                    quantity=qty,
                    unit_price=unit_rate,
                    total=total,
                    business_unit=business_unit,
                    module="empire_workroom",
                    product_category=raw.get("treatment_type") or raw.get("type") or "approved_quote_line",
                    source_quote_id=quote_id,
                    source_line_item_id=raw.get("id", idx),
                    tax_policy=tax_policy,
                ))

    if not invoice_lines:
        for idx, raw in enumerate(quote.get("line_items") or [], start=1):
            if not isinstance(raw, dict):
                continue
            total = _line_amount(raw)
            qty = _qty(raw.get("quantity", raw.get("qty", 1)))
            unit_rate = _line_unit_rate(raw, total)
            invoice_lines.append(_invoice_line(
                raw=raw,
                description=raw.get("description", "Item"),
                quantity=qty,
                unit_price=unit_rate,
                total=total,
                business_unit=business_unit,
                module="empire_workroom" if business_unit == "workroom" else "craftforge",
                product_category=raw.get("category") or raw.get("item_type") or "approved_quote_line",
                source_quote_id=quote_id,
                source_line_item_id=raw.get("id", idx),
                tax_policy=tax_policy,
            ))

    subtotal = _money(quote.get("subtotal") or (tier_data or {}).get("subtotal") or sum(line["total"] for line in invoice_lines))
    tax_amount, final_price = _source_total(quote, subtotal, tax_policy)
    deposit_required, deposit_amount, balance_due_after_deposit = _source_deposit(quote, final_price)
    aggregate_snapshot = _preserved_snapshot(
        business_unit=business_unit,
        module="empire_workroom" if business_unit == "workroom" else "craftforge",
        product_category="approved_quote",
        pricing_method="approved_quote_snapshot",
        pricing_inputs=deepcopy(quote),
        calculated_subtotal=subtotal,
        tax_policy=tax_policy,
        tax_amount=tax_amount,
        discount_type=discount_type,
        discount_amount=discount_amount,
        final_price=final_price,
        deposit_required=deposit_required,
        deposit_amount=deposit_amount,
        balance_due=balance_due_after_deposit,
        source_quote_id=quote_id,
        source_line_item_id=None,
        rate_table_version=WORKROOM_RATE_TABLE_VERSION if business_unit == "workroom" else WOODCRAFT_RATE_TABLE_VERSION,
        original_snapshot=quote.get("pricing_snapshot_json", quote.get("pricing_snapshot")),
    )
    return {
        "source_type": "quote",
        "source_id": quote_id,
        "quote_id": quote_id,
        "job_id": None,
        "business_unit": business_unit,
        "subtotal": subtotal,
        "tax_rate": _money(tax_policy.get("tax_rate", 0)),
        "tax_policy": tax_policy,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "discount_type": discount_type,
        "total": final_price,
        "deposit_required": deposit_amount,
        "deposit_received": _money((quote.get("deposit") or {}).get("deposit_received") or quote.get("deposit_received") or 0),
        "deposit_percent": _money((quote.get("deposit") or {}).get("deposit_percent") or quote.get("deposit_percent") or 0),
        "line_items": invoice_lines,
        "pricing_snapshot_json": aggregate_snapshot,
        "customer_name": quote.get("customer_name", ""),
        "customer_email": quote.get("customer_email", ""),
        "customer_phone": quote.get("customer_phone", ""),
        "customer_address": quote.get("customer_address", ""),
        "notes": quote.get("notes") or quote.get("project_description") or "",
        "terms": quote.get("terms") or "Net 30",
    }


def build_design_invoice_source(design: dict[str, Any], design_id: str) -> dict[str, Any]:
    tax_policy = _tax_policy_from_source(design, name="approved_design_tax_rate")
    discount_type, discount_amount = _discount(design)
    line_items: list[dict[str, Any]] = []

    for idx, material in enumerate(design.get("materials") or [], start=1):
        if not isinstance(material, dict):
            continue
        qty = _qty(material.get("quantity", 1))
        unit_rate = _money(material.get("cost_per_unit", material.get("unit_price", 0)))
        total = _money(material.get("total", qty * unit_rate))
        if total:
            line_items.append(_invoice_line(
                raw=material,
                description=material.get("name") or material.get("description") or "Material",
                quantity=qty,
                unit_price=unit_rate,
                total=total,
                business_unit="woodcraft",
                module="craftforge",
                product_category=material.get("type") or "material",
                source_quote_id=design_id,
                source_line_item_id=material.get("id", f"material-{idx}"),
                tax_policy=tax_policy,
            ))

    for idx, raw in enumerate(design.get("line_items") or [], start=1):
        if not isinstance(raw, dict):
            continue
        total = _line_amount(raw)
        qty = _qty(raw.get("quantity", raw.get("qty", 1)))
        if total:
            line_items.append(_invoice_line(
                raw=raw,
                description=raw.get("description", "Item"),
                quantity=qty,
                unit_price=_line_unit_rate(raw, total),
                total=total,
                business_unit="woodcraft",
                module="craftforge",
                product_category=raw.get("category") or design.get("category") or "approved_design_line",
                source_quote_id=design_id,
                source_line_item_id=raw.get("id", idx),
                tax_policy=tax_policy,
            ))

    for label, key in (("Labor", "labor_cost"), ("Overhead", "overhead"), ("CNC Machine Time", "cnc_time_cost")):
        amount = _money(design.get(key))
        if amount:
            raw = {"description": label, "quantity": 1, "unit_price": amount, "total": amount, "category": key}
            line_items.append(_invoice_line(
                raw=raw,
                description=label,
                quantity=1,
                unit_price=amount,
                total=amount,
                business_unit="woodcraft",
                module="craftforge",
                product_category=key,
                source_quote_id=design_id,
                source_line_item_id=key,
                tax_policy=tax_policy,
            ))

    subtotal = _money(design.get("subtotal") or sum(line["total"] for line in line_items))
    tax_amount, final_price = _source_total(design, subtotal, tax_policy)
    deposit_required, deposit_amount, balance_due_after_deposit = _source_deposit(design, final_price)
    if not deposit_required:
        deposit = calculate_deposit_balance(final_price, False, 0)
        balance_due_after_deposit = deposit["balance_due"]
    aggregate_snapshot = _preserved_snapshot(
        business_unit="woodcraft",
        module="craftforge",
        product_category=design.get("category") or "approved_design",
        pricing_method="approved_design_snapshot",
        pricing_inputs=deepcopy(design),
        calculated_subtotal=subtotal,
        tax_policy=tax_policy,
        tax_amount=tax_amount,
        discount_type=discount_type,
        discount_amount=discount_amount,
        final_price=final_price,
        deposit_required=deposit_required,
        deposit_amount=deposit_amount,
        balance_due=balance_due_after_deposit,
        source_quote_id=design_id,
        source_line_item_id=None,
        rate_table_version=WOODCRAFT_RATE_TABLE_VERSION,
        original_snapshot=design.get("pricing_snapshot_json", design.get("pricing_snapshot")),
    )
    return {
        "source_type": "design",
        "source_id": design_id,
        "quote_id": design_id,
        "job_id": None,
        "business_unit": "woodcraft",
        "subtotal": subtotal,
        "tax_rate": _money(tax_policy.get("tax_rate", 0)),
        "tax_policy": tax_policy,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "discount_type": discount_type,
        "total": final_price,
        "deposit_required": deposit_amount,
        "deposit_received": _money(design.get("deposit_received", 0)),
        "deposit_percent": _money(design.get("deposit_percent", 0)),
        "line_items": line_items,
        "pricing_snapshot_json": aggregate_snapshot,
        "customer_name": design.get("customer_name", ""),
        "customer_email": design.get("customer_email", ""),
        "customer_phone": design.get("customer_phone", ""),
        "customer_address": design.get("customer_address", ""),
        "notes": design.get("notes") or design.get("description") or "",
        "terms": design.get("terms") or "Net 30",
    }


def scale_invoice_source(source: dict[str, Any], percent: float, *, stage: str) -> dict[str, Any]:
    factor = float(percent or 0) / 100
    scaled = deepcopy(source)
    scaled["subtotal"] = _money(source.get("subtotal", 0) * factor)
    scaled["tax_amount"] = _money(source.get("tax_amount", 0) * factor)
    scaled["total"] = _money(source.get("total", 0) * factor)
    scaled["deposit_required"] = scaled["total"] if stage == "deposit" else 0
    scaled_lines = []
    for item in source.get("line_items") or []:
        line = deepcopy(item)
        original_total = _money(item.get("total", 0))
        original_unit = _money(item.get("unit_price", item.get("rate", 0)))
        line["unit_price"] = _money(original_unit * factor)
        line["unit_rate"] = line["unit_price"]
        line["rate"] = line["unit_price"]
        line["total"] = _money(original_total * factor)
        line["description"] = f"{stage.title()} {percent:g}% - {item.get('description', 'Item')}"
        snapshot = deepcopy(line.get("pricing_snapshot_json") or {})
        if isinstance(snapshot, dict):
            snapshot["invoice_stage"] = stage
            snapshot["invoice_percent"] = percent
            snapshot["invoice_scaled_from_final_price"] = item.get("pricing_result", {}).get("final_price", original_total)
            line["pricing_snapshot_json"] = snapshot
        scaled_lines.append(line)
    scaled["line_items"] = scaled_lines
    snapshot = deepcopy(source.get("pricing_snapshot_json") or {})
    if isinstance(snapshot, dict):
        snapshot["invoice_stage"] = stage
        snapshot["invoice_percent"] = percent
        snapshot["final_price"] = scaled["total"]
        snapshot["calculated_subtotal"] = scaled["subtotal"]
        snapshot["tax_amount"] = scaled["tax_amount"]
        snapshot["deposit_amount"] = scaled["deposit_required"]
        snapshot["balance_due"] = _money(scaled["total"] - scaled["deposit_required"])
        scaled["pricing_snapshot_json"] = snapshot
    return scaled
