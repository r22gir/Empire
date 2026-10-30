"""Pass-through vendor shipping.

Whatever the mill charges Empire is charged to the customer. Checkout
uses per-vendor estimate rules (per-yard, per-sample, minimum) plus an
optional handling fee. After the vendor invoice arrives, admin records
the actual freight; a shortfall (actual > collected) is flagged to bill.

Never free: no thresholds, no $0 quotes. Samples are charged.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.db.database import dict_row, dict_rows, get_db
from app.services.fine_fabrics.schema import DEFAULT_SHIPPING, ensure_fine_fabrics_schema

NEVER_FREE_FLOOR = 1.00
SHORTFALL_FLAG = "shortfall"


def _num(data: dict, key: str, default: float | None = None) -> float:
    value = data.get(key)
    if value is None:
        return float(DEFAULT_SHIPPING[key] if default is None else default)
    return float(value)


def _rules_for(conn, vendor_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM ff_shipping_rules WHERE vendor_id = ?", (vendor_id,)
    ).fetchone()
    if not row:
        return dict(DEFAULT_SHIPPING)
    data = dict_row(row)
    return {
        "ship_per_yard": _num(data, "ship_per_yard"),
        "ship_per_sample": _num(data, "ship_per_sample"),
        "ship_minimum": _num(data, "ship_minimum"),
        "handling_fee": _num(data, "handling_fee", 0.0),
    }


def _product_row(conn, product_id: int) -> dict | None:
    row = conn.execute(
        """SELECT p.id, p.vendor_id, p.unit, p.is_unsorted, p.category,
                  v.online_sale_allowed, v.slug AS vendor_slug
           FROM ff_products p
           JOIN ff_vendors v ON v.id = p.vendor_id
           WHERE p.id = ? AND p.is_active = 1""",
        (product_id,),
    ).fetchone()
    return dict_row(row) if row else None


def estimate_shipping(
    yardage_items: Iterable[dict],
    sample_ids: Iterable[int] = (),
    *,
    require_online: bool = True,
) -> dict:
    """Estimate vendor freight the customer must pay.

    yardage_items: {product_id, yards|quantity}
    sample_ids: product ids for cuttings (each charged ship_per_sample)
    """
    ensure_fine_fabrics_schema()
    buckets: dict[int, dict] = defaultdict(lambda: {"yards": 0.0, "samples": 0, "slug": ""})
    with get_db() as conn:
        for raw in yardage_items:
            pid = int(raw.get("product_id") or raw.get("id") or 0)
            qty = float(raw.get("yards") or raw.get("quantity") or 0)
            if pid <= 0 or qty <= 0:
                continue
            product = _product_row(conn, pid)
            if not product:
                raise PermissionError(f"Product {pid} is not available")
            if require_online and not int(product.get("online_sale_allowed") or 0):
                raise PermissionError(f"Product {pid} is not for online sale")
            if int(product.get("is_unsorted") or 0) or product.get("category") == "Unsorted":
                raise PermissionError(f"Product {pid} is still in the Unsorted queue")
            buckets[product["vendor_id"]]["yards"] += qty
            buckets[product["vendor_id"]]["slug"] = product.get("vendor_slug") or ""
        for pid in sample_ids:
            product = _product_row(conn, int(pid))
            if not product:
                raise PermissionError(f"Product {pid} is not available")
            if require_online and not int(product.get("online_sale_allowed") or 0):
                raise PermissionError(f"Product {pid} is not for online sale")
            buckets[product["vendor_id"]]["samples"] += 1
            buckets[product["vendor_id"]]["slug"] = product.get("vendor_slug") or ""

        by_vendor = []
        freight_total = 0.0
        handling_total = 0.0
        for vendor_id, bucket in buckets.items():
            rules = _rules_for(conn, vendor_id)
            raw_freight = (
                bucket["yards"] * rules["ship_per_yard"]
                + bucket["samples"] * rules["ship_per_sample"]
            )
            freight = round(max(raw_freight, rules["ship_minimum"]), 2)
            handling = round(float(rules["handling_fee"] or 0), 2)
            vendor_charge = round(freight + handling, 2)
            freight_total += freight
            handling_total += handling
            by_vendor.append(
                {
                    "vendor_id": vendor_id,
                    "yards": round(bucket["yards"], 2),
                    "samples": bucket["samples"],
                    "freight": freight,
                    "handling_fee": handling,
                    "total": vendor_charge,
                    "pass_through": True,
                    "rules": rules,
                }
            )

    shipping_total = round(freight_total + handling_total, 2)
    applied_floor = False
    if shipping_total < NEVER_FREE_FLOOR:
        shipping_total = NEVER_FREE_FLOOR
        applied_floor = True

    return {
        "pass_through": True,
        "never_free": True,
        "free_shipping": False,
        "freight": round(freight_total, 2),
        "handling_total": round(handling_total, 2),
        "shipping_total": shipping_total,
        "floor_applied": applied_floor,
        "by_vendor": by_vendor,
        "note": "Shipping is a pass-through of vendor freight plus handling. It is never free.",
    }


def record_actual_shipping(kind: str, row_id: int, actual: float) -> dict:
    """Admin records the vendor's actual freight. Shortfall is flagged to bill."""
    if actual is None or float(actual) < 0:
        raise ValueError("actual vendor shipping must be >= 0")
    actual = round(float(actual), 2)
    table = "ff_orders" if kind == "order" else "ff_sample_requests"
    ensure_fine_fabrics_schema()
    with get_db() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
        if not row:
            raise LookupError(f"{kind} {row_id} not found")
        row = dict_row(row)
        collected = float(row.get("shipping_total") or 0)
        shortfall = round(max(0.0, actual - collected), 2)
        flag = SHORTFALL_FLAG if shortfall > 0 else ""
        conn.execute(
            f"""UPDATE {table}
                SET actual_vendor_shipping = ?, shipping_shortfall = ?, shipping_flag = ?
                WHERE id = ?""",
            (actual, shortfall, flag, row_id),
        )
    return {
        "id": row_id,
        "kind": kind,
        "collected": collected,
        "actual_vendor_shipping": actual,
        "shipping_shortfall": shortfall,
        "flagged": bool(flag),
        "shipping_flag": flag,
        "bill_shortfall": shortfall > 0,
    }


def list_shipping_rules() -> list[dict]:
    ensure_fine_fabrics_schema()
    with get_db() as conn:
        rows = dict_rows(
            conn.execute(
                """SELECT v.id AS vendor_id, v.slug, v.name, r.ship_per_yard,
                          r.ship_per_sample, r.ship_minimum, r.handling_fee
                   FROM ff_vendors v
                   LEFT JOIN ff_shipping_rules r ON r.vendor_id = v.id
                   ORDER BY v.name"""
            ).fetchall()
        )
        for row in rows:
            for key, default in DEFAULT_SHIPPING.items():
                if row.get(key) is None:
                    row[key] = default
        return rows


def update_shipping_rules(vendor_id: int, payload: dict) -> list[dict]:
    ensure_fine_fabrics_schema()
    allowed = ("ship_per_yard", "ship_per_sample", "ship_minimum", "handling_fee")
    updates = {k: float(payload[k]) for k in allowed if k in payload and payload[k] is not None}
    if not updates:
        raise ValueError("No shipping fields to update")
    for value in updates.values():
        if value < 0:
            raise ValueError("Shipping amounts cannot be negative")
    with get_db() as conn:
        found = conn.execute("SELECT id FROM ff_vendors WHERE id = ?", (vendor_id,)).fetchone()
        if not found:
            raise LookupError("Vendor not found")
        existing = conn.execute(
            "SELECT vendor_id FROM ff_shipping_rules WHERE vendor_id = ?", (vendor_id,)
        ).fetchone()
        if existing:
            sets = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE ff_shipping_rules SET {sets} WHERE vendor_id = ?",
                list(updates.values()) + [vendor_id],
            )
        else:
            merged = dict(DEFAULT_SHIPPING)
            merged.update(updates)
            conn.execute(
                """INSERT INTO ff_shipping_rules
                   (vendor_id, ship_per_yard, ship_per_sample, ship_minimum, handling_fee)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    vendor_id,
                    merged["ship_per_yard"],
                    merged["ship_per_sample"],
                    merged["ship_minimum"],
                    merged["handling_fee"],
                ),
            )
    return list_shipping_rules()


def customer_shipping_view(estimate: dict) -> dict:
    """Customer-safe shipping quote. Mill names and rule rates stay in the workroom."""
    shipments = []
    for index, vendor in enumerate(estimate.get("by_vendor") or [], start=1):
        shipments.append(
            {
                "label": f"Shipment {index}",
                "yards": vendor.get("yards") or 0,
                "samples": vendor.get("samples") or 0,
                "freight": vendor.get("freight") or 0,
                "handling_fee": vendor.get("handling_fee") or 0,
                "total": vendor.get("total") or 0,
            }
        )
    return {
        "pass_through": True,
        "never_free": True,
        "free_shipping": False,
        "freight": estimate.get("freight") or 0,
        "handling_total": estimate.get("handling_total") or 0,
        "shipping_total": estimate.get("shipping_total") or 0,
        "floor_applied": bool(estimate.get("floor_applied")),
        "shipments": shipments,
        "note": estimate.get("note")
        or "Shipping is a pass-through of vendor freight plus handling. It is never free.",
    }


def list_shortfalls() -> list[dict]:
    ensure_fine_fabrics_schema()
    with get_db() as conn:
        orders = dict_rows(
            conn.execute(
                """SELECT id, 'order' AS kind, customer_name, shipping_total,
                          actual_vendor_shipping, shipping_shortfall, shipping_flag
                   FROM ff_orders WHERE shipping_flag = ?""",
                (SHORTFALL_FLAG,),
            ).fetchall()
        )
        samples = dict_rows(
            conn.execute(
                """SELECT id, 'sample' AS kind, customer_name, shipping_total,
                          actual_vendor_shipping, shipping_shortfall, shipping_flag
                   FROM ff_sample_requests WHERE shipping_flag = ?""",
                (SHORTFALL_FLAG,),
            ).fetchall()
        )
    return orders + samples
