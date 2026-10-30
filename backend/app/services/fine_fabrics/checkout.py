"""Cart checkout via the existing quote → deposit → Stripe path.

Test mode only. A live Stripe key is refused. When Stripe is unset the
quote and deposit invoice still form; the pay link reports unconfigured,
same as the workroom cash path.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.db.database import get_db
from app.services.fine_fabrics.catalog import get_product
from app.services.fine_fabrics.schema import ensure_fine_fabrics_schema

TEST_MODE_NOTE = "Empire Fine Fabrics checkout is Stripe test-mode only."


def stripe_secret_key() -> str:
    return (os.getenv("STRIPE_SECRET_KEY") or "").strip()


def assert_test_mode() -> str:
    key = stripe_secret_key()
    if key.startswith("sk_live_"):
        raise PermissionError("Empire Fine Fabrics checkout refuses live Stripe keys")
    return "test"


def _quotes_dir() -> Path:
    from app.routers import finance

    return Path(finance.QUOTES_DIR)


def build_quote_payload(
    *,
    quote_id: str,
    customer: dict,
    items: list[dict],
    subtotal: float,
) -> dict:
    lines = []
    for item in items:
        yards = float(item["yards"])
        rate = float(item["price_per_yard"])
        amount = round(yards * rate, 2)
        lines.append(
            {
                "description": f"{item['empire_code']} {item['pattern']} {item['color']} — {yards:g} yd",
                "quantity": yards,
                "rate": rate,
                "amount": amount,
            }
        )
    return {
        "id": quote_id,
        "quote_number": f"FF-{quote_id}",
        "status": "accepted",
        "customer_name": customer.get("name") or "",
        "customer_email": customer.get("email") or "",
        "customer_phone": customer.get("phone") or "",
        "customer_address": customer.get("address") or "",
        "business_unit": "workroom",
        "business": "workroom",
        "line_items": lines,
        "subtotal": subtotal,
        "tax_rate": 0,
        "tax_amount": 0,
        "total": subtotal,
        "deposit": {"deposit_percent": 100, "deposit_amount": subtotal},
        "terms": "Fine Fabrics yardage — test-mode Stripe checkout",
        "notes": "Empire Fine Fabrics online store (test mode)",
        "source": "fine_fabrics",
    }


def resolve_cart_items(raw_items: Iterable[dict]) -> list[dict]:
    resolved = []
    for raw in raw_items:
        product_id = int(raw.get("product_id") or raw.get("id") or 0)
        yards = float(raw.get("yards") or 0)
        if product_id <= 0 or yards <= 0:
            raise ValueError("Each cart line needs product_id and yards > 0")
        product = get_product(product_id, owner=False, allow_hidden=False)
        if not product:
            raise PermissionError(f"Product {product_id} is not for online sale")
        # Never trust the client price.
        resolved.append(
            {
                "product_id": product_id,
                "pattern": product["pattern"],
                "color": product["color"],
                "empire_code": product["empire_code"],
                "category": product["category"],
                "price_per_yard": product["price_per_yard"],
                "yards": yards,
                "line_total": round(yards * product["price_per_yard"], 2),
            }
        )
    if not resolved:
        raise ValueError("Cart is empty")
    return resolved


def checkout_cart(customer: dict, raw_items: Iterable[dict], *, success_url: str | None = None, cancel_url: str | None = None) -> dict:
    ensure_fine_fabrics_schema()
    mode = assert_test_mode()
    items = resolve_cart_items(raw_items)
    subtotal = round(sum(i["line_total"] for i in items), 2)
    quote_id = f"ff{uuid.uuid4().hex[:10]}"
    quote = build_quote_payload(quote_id=quote_id, customer=customer, items=items, subtotal=subtotal)

    quotes_dir = _quotes_dir()
    quotes_dir.mkdir(parents=True, exist_ok=True)
    (quotes_dir / f"{quote_id}.json").write_text(json.dumps(quote), encoding="utf-8")

    from app.routers.finance import create_quote_deposit_pay_link

    pay = create_quote_deposit_pay_link(
        quote_id,
        percent=100,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ff_orders
               (quote_id, invoice_id, customer_name, customer_email, customer_phone,
                items_json, subtotal, checkout_url, stripe_mode, status, business)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'workroom')""",
            (
                quote_id,
                (pay.get("invoice") or {}).get("id"),
                customer.get("name") or "",
                customer.get("email") or "",
                customer.get("phone") or "",
                json.dumps(items),
                subtotal,
                (pay.get("pay_link") or {}).get("checkout_url"),
                mode,
                pay.get("payment_status") or "link_ready",
            ),
        )
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {
        "order_id": order_id,
        "quote_id": quote_id,
        "subtotal": subtotal,
        "items": items,
        "stripe_mode": mode,
        "test_mode": True,
        "note": TEST_MODE_NOTE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **pay,
    }
