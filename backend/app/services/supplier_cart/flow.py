"""Cart → owner approval → job-linked PO. Never live checkout or pay."""
from __future__ import annotations

from typing import Any, Optional

from app.services.supplier_cart import store


class SupplierCartError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _require_owner_yes(owner_yes: Any) -> None:
    if owner_yes is True or owner_yes == "yes" or owner_yes == "true":
        return
    raise SupplierCartError(
        "Owner explicit yes is required. Nothing was checked out or paid.",
        status_code=403,
    )


def build_cart(
    *,
    job_id: Optional[str] = None,
    supplier_name: str = "",
    notes: str = "",
    lines: Optional[list[dict]] = None,
) -> dict[str, Any]:
    raw_lines = lines or [{"title": "Materials", "qty": "1", "note": "Prepare only"}]
    cart = store.insert_cart(
        job_id=job_id,
        supplier_name=supplier_name,
        notes=notes,
        lines=raw_lines,
    )
    body = store.public_cart(cart)
    body["message"] = (
        "Supplier cart prepared. Awaiting owner approval before a purchase "
        "order is created. Nothing was ordered or paid."
    )
    body["next"] = "owner_approval"
    body["checked_out"] = False
    body["paid"] = False
    return body


def cart_from_nest(nest: dict[str, Any], *, job_id: Optional[str] = None, supplier_name: str = "") -> dict[str, Any]:
    """Turn a nest result into cart lines (sheet counts + labeled fabric)."""
    lines = []
    counts = nest.get("sheet_counts") or {}
    wood_n = counts.get("wood") or "0"
    foam_n = counts.get("foam") or "0"
    fabric_n = counts.get("fabric") or "0"
    if wood_n and wood_n != "0":
        width = (nest.get("wood_sheets") or [{}])[0].get("sheet_width") if nest.get("wood_sheets") else None
        length = (nest.get("wood_sheets") or [{}])[0].get("sheet_length") if nest.get("wood_sheets") else None
        size = f"{width} x {length}" if width and length else "sheet"
        lines.append({"title": f"Plywood {size}", "qty": str(wood_n), "unit": "sheet", "note": "From CNC nest"})
    if foam_n and foam_n != "0":
        lines.append({"title": "Foam (equals wood cut)", "qty": str(foam_n), "unit": "sheet", "note": "Foam = wood true size"})
    if fabric_n and fabric_n != "0":
        for row in nest.get("cut_list") or []:
            if row.get("fabric_width"):
                lines.append({
                    "title": f'Fabric — {row.get("name")}',
                    "qty": "1",
                    "unit": "cut",
                    "note": f'{row.get("fabric_width")} x {row.get("fabric_length")} labeled size',
                })
    if not lines:
        lines = [{"title": nest.get("title") or "Nest materials", "qty": "1", "note": "From CNC nest"}]
    return build_cart(
        job_id=job_id or nest.get("job_id"),
        supplier_name=supplier_name,
        notes="Built from CNC cut-list nest. Prepare only.",
        lines=lines,
    )


def request_owner_approval(cart_id: str) -> dict[str, Any]:
    cart = store.load_cart(cart_id)
    if cart["status"] in {"approved", "po_created"}:
        body = store.public_cart(cart)
        body["message"] = "Already approved."
        return body
    cart = store.update_cart(cart_id, status="awaiting_owner")
    body = store.public_cart(cart)
    body["message"] = (
        "Owner approval requested. No purchase order, checkout, or payment "
        "until the owner says yes."
    )
    body["sent"] = False
    body["checked_out"] = False
    body["paid"] = False
    return body


def approve_cart(cart_id: str, *, owner_yes: Any, job_id: Optional[str] = None) -> dict[str, Any]:
    _require_owner_yes(owner_yes)
    cart = store.load_cart(cart_id)
    linked_job = job_id or cart.get("job_id")
    if not linked_job:
        raise SupplierCartError("A job_id is required to issue a purchase order.", status_code=400)
    po = store.insert_po(
        cart_id=cart_id,
        job_id=str(linked_job),
        supplier_name=cart.get("supplier_name") or "",
        notes="Issued after owner explicit yes. Not checked out. Not paid.",
    )
    cart = store.update_cart(
        cart_id,
        status="po_created",
        owner_yes=1,
        job_id=str(linked_job),
        checked_out=0,
        paid=0,
        live_charge=0,
    )
    body = store.public_cart(cart)
    body["message"] = (
        f'Owner approved. Purchase order {po["po_number"]} is linked to job {linked_job}. '
        "Nothing was checked out or paid."
    )
    body["purchase_order"] = {
        "id": po["id"],
        "po_number": po["po_number"],
        "job_id": po["job_id"],
        "status": po["status"],
        "checked_out": False,
        "paid": False,
        "live_charge": False,
    }
    body["checked_out"] = False
    body["paid"] = False
    body["sent"] = False
    return body


def checkout_cart(cart_id: str, *, owner_yes: Any = False) -> dict[str, Any]:
    """Hard stop. In-app checkout never talks to a supplier."""
    try:
        _require_owner_yes(owner_yes)
    except SupplierCartError as exc:
        raise SupplierCartError(
            "Checkout refused. The owner must say yes. Nothing was ordered or paid.",
            status_code=403,
        ) from exc
    cart = store.load_cart(cart_id)
    body = store.public_cart(cart)
    body["checked_out"] = False
    body["paid"] = False
    body["live_charge"] = False
    body["message"] = (
        "Checkout is not performed in-app and no supplier was charged. "
        "Owner yes is recorded only as approval to issue the job purchase order."
    )
    return body


def pay_cart(cart_id: str, *, owner_yes: Any = False) -> dict[str, Any]:
    try:
        _require_owner_yes(owner_yes)
    except SupplierCartError as exc:
        raise SupplierCartError(
            "Pay refused. The owner must say yes. Nothing was charged.",
            status_code=403,
        ) from exc
    cart = store.load_cart(cart_id)
    body = store.public_cart(cart)
    body["checked_out"] = False
    body["paid"] = False
    body["live_charge"] = False
    body["message"] = (
        "Payment is not performed in-app. No live charge. "
        "Owner yes only authorizes the job-linked purchase order."
    )
    return body


def get_cart(cart_id: str) -> dict[str, Any]:
    return store.public_cart(store.load_cart(cart_id))


def list_job_purchase_orders(job_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": po["id"],
            "po_number": po["po_number"],
            "cart_id": po.get("cart_id"),
            "job_id": po["job_id"],
            "status": po["status"],
            "owner_approved": bool(po.get("owner_approved")),
            "checked_out": False,
            "paid": False,
            "live_charge": False,
            "created_at": po.get("created_at"),
        }
        for po in store.list_pos_for_job(job_id)
    ]


def organizer_supplier_cart(item: Optional[dict] = None, extra: Optional[dict] = None, job: Optional[dict] = None) -> dict[str, Any]:
    """Drop-in replacement for the PR #120 prepare-only stub.

    Builds a real cart. Still never checks out or pays. Owner approval
    (and the job PO) is a follow-up step.
    """
    extra = extra or {}
    item = item or {}
    job = job or {}
    lines = extra.get("lines") or [
        {"title": item.get("title") or "Materials", "qty": "1", "note": "Prepare only"},
    ]
    job_id = extra.get("job_id") or item.get("job_id") or job.get("id")
    cart = build_cart(
        job_id=job_id,
        supplier_name=extra.get("supplier_name") or "",
        notes=extra.get("notes") or "Organizer supplier cart stub (finished).",
        lines=lines,
    )
    return {
        "prepared": True,
        "checked_out": False,
        "paid": False,
        "live_charge": False,
        "cart_id": cart["id"],
        "job_id": job_id,
        "lines": cart["lines"],
        "status": cart["status"],
        "message": cart["message"],
        "next": "owner_approval",
        "sent": False,
    }
