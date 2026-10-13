"""SQLite store for supplier carts and job POs.

Uses EMPIRE_TASK_DB via app.db.database so tests stay on isolated temp
files. Never opens client_aliases.json, business.json, or .env.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db.database import get_db
from app.services.supplier_cart.schema import SCHEMA_SQL


def ensure_tables(conn=None) -> None:
    if conn is not None:
        conn.executescript(SCHEMA_SQL)
        return
    with get_db() as db:
        db.executescript(SCHEMA_SQL)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _row(conn, table: str, item_id: str) -> Optional[dict[str, Any]]:
    cur = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def insert_cart(*, job_id: Optional[str], supplier_name: str, notes: str, lines: list[dict]) -> dict[str, Any]:
    ensure_tables()
    cart_id = _id("cart")
    stamp = _now()
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute(
            """INSERT INTO supplier_carts
               (id, job_id, supplier_name, status, checked_out, paid, owner_yes, live_charge, notes, created_at, updated_at)
               VALUES (?, ?, ?, 'prepared', 0, 0, 0, 0, ?, ?, ?)""",
            (cart_id, job_id or "", supplier_name or "", notes or "", stamp, stamp),
        )
        for i, line in enumerate(lines):
            conn.execute(
                """INSERT INTO supplier_cart_lines
                   (id, cart_id, title, qty, unit, sku, note, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _id("line"),
                    cart_id,
                    str(line.get("title") or line.get("name") or "Materials"),
                    str(line.get("qty") or line.get("quantity") or "1"),
                    str(line.get("unit") or "ea"),
                    str(line.get("sku") or ""),
                    str(line.get("note") or line.get("notes") or ""),
                    i,
                ),
            )
    return load_cart(cart_id)


def load_cart(cart_id: str) -> dict[str, Any]:
    ensure_tables()
    with get_db() as conn:
        ensure_tables(conn)
        cart = _row(conn, "supplier_carts", cart_id)
        if not cart:
            raise KeyError(cart_id)
        lines = [dict(r) for r in conn.execute(
            "SELECT * FROM supplier_cart_lines WHERE cart_id = ? ORDER BY sort_order",
            (cart_id,),
        )]
        pos = [dict(r) for r in conn.execute(
            "SELECT * FROM job_purchase_orders WHERE cart_id = ? ORDER BY created_at",
            (cart_id,),
        )]
    cart["lines"] = lines
    cart["purchase_orders"] = pos
    cart["checked_out"] = bool(cart.get("checked_out"))
    cart["paid"] = bool(cart.get("paid"))
    cart["owner_yes"] = bool(cart.get("owner_yes"))
    cart["live_charge"] = bool(cart.get("live_charge"))
    return cart


def update_cart(cart_id: str, **fields) -> dict[str, Any]:
    ensure_tables()
    if not fields:
        return load_cart(cart_id)
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [cart_id]
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute(f"UPDATE supplier_carts SET {cols} WHERE id = ?", vals)
    return load_cart(cart_id)


def insert_po(*, cart_id: str, job_id: str, supplier_name: str, notes: str) -> dict[str, Any]:
    ensure_tables()
    if not job_id:
        raise ValueError("purchase order must be linked to a job")
    po_id = _id("po")
    stamp = _now()
    day = stamp[:10].replace("-", "")
    po_number = f"PO-{day}-{po_id[-6:].upper()}"
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute(
            """INSERT INTO job_purchase_orders
               (id, po_number, cart_id, job_id, supplier_name, status,
                owner_approved, checked_out, paid, live_charge, notes, created_at)
               VALUES (?, ?, ?, ?, ?, 'issued', 1, 0, 0, 0, ?, ?)""",
            (po_id, po_number, cart_id, job_id, supplier_name or "", notes or "", stamp),
        )
    with get_db() as conn:
        row = _row(conn, "job_purchase_orders", po_id)
    return dict(row)


def list_pos_for_job(job_id: str) -> list[dict[str, Any]]:
    ensure_tables()
    with get_db() as conn:
        ensure_tables(conn)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM job_purchase_orders WHERE job_id = ? ORDER BY created_at DESC",
            (job_id,),
        )]


def public_cart(cart: dict[str, Any]) -> dict[str, Any]:
    """API shape. Always reports that nothing was checked out or paid live."""
    pos = cart.get("purchase_orders") or []
    return {
        "id": cart["id"],
        "job_id": cart.get("job_id") or None,
        "supplier_name": cart.get("supplier_name") or "",
        "status": cart.get("status"),
        "prepared": True,
        "checked_out": False if not cart.get("checked_out") else bool(cart.get("checked_out")),
        "paid": False if not cart.get("paid") else bool(cart.get("paid")),
        "live_charge": False,
        "owner_yes": bool(cart.get("owner_yes")),
        "notes": cart.get("notes") or "",
        "lines": [
            {
                "id": ln.get("id"),
                "title": ln.get("title"),
                "qty": str(ln.get("qty") or "1"),
                "unit": ln.get("unit") or "ea",
                "sku": ln.get("sku") or "",
                "note": ln.get("note") or "",
            }
            for ln in cart.get("lines") or []
        ],
        "purchase_orders": [
            {
                "id": po.get("id"),
                "po_number": po.get("po_number"),
                "job_id": po.get("job_id"),
                "status": po.get("status"),
                "owner_approved": bool(po.get("owner_approved")),
                "checked_out": False,
                "paid": False,
                "live_charge": False,
            }
            for po in pos
        ],
        "created_at": cart.get("created_at"),
        "updated_at": cart.get("updated_at"),
    }
