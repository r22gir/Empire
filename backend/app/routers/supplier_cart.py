"""Supplier cart API. Cart → owner yes → job PO. Never live checkout/pay."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.supplier_cart.flow import (
    SupplierCartError,
    approve_cart,
    build_cart,
    cart_from_nest,
    checkout_cart,
    get_cart,
    list_job_purchase_orders,
    organizer_supplier_cart,
    pay_cart,
    request_owner_approval,
)

router = APIRouter()


class CartLineIn(BaseModel):
    title: str = "Materials"
    qty: str = "1"
    unit: str = "ea"
    sku: str = ""
    note: str = ""


class BuildCartIn(BaseModel):
    job_id: Optional[str] = None
    supplier_name: str = ""
    notes: str = ""
    lines: list[CartLineIn] = Field(default_factory=list)


class OwnerYesIn(BaseModel):
    owner_yes: bool = False
    job_id: Optional[str] = None


class OrganizerStubIn(BaseModel):
    item: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)
    job: dict[str, Any] = Field(default_factory=dict)
    lines: list[CartLineIn] = Field(default_factory=list)
    job_id: Optional[str] = None
    action: str = "supplier_cart"


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"cart not found: {exc}") from exc
    except SupplierCartError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/supplier-carts")
async def api_build_cart(body: BuildCartIn):
    return _call(
        build_cart,
        job_id=body.job_id,
        supplier_name=body.supplier_name,
        notes=body.notes,
        lines=[ln.model_dump() for ln in body.lines] or None,
    )


@router.post("/supplier-carts/from-nest")
async def api_cart_from_nest(body: dict[str, Any]):
    nest = body.get("nest") or body
    return _call(
        cart_from_nest,
        nest,
        job_id=body.get("job_id"),
        supplier_name=body.get("supplier_name") or "",
    )


@router.post("/supplier-carts/organizer-action")
async def api_organizer_stub(body: OrganizerStubIn):
    """Finish the PR #120 stub: prepare a real cart, still never pay."""
    extra = dict(body.extra)
    if body.lines:
        extra["lines"] = [ln.model_dump() for ln in body.lines]
    if body.job_id:
        extra["job_id"] = body.job_id
    return _call(organizer_supplier_cart, body.item, extra, body.job)


@router.get("/supplier-carts/{cart_id}")
async def api_get_cart(cart_id: str):
    return _call(get_cart, cart_id)


@router.post("/supplier-carts/{cart_id}/request-approval")
async def api_request_approval(cart_id: str):
    return _call(request_owner_approval, cart_id)


@router.post("/supplier-carts/{cart_id}/approve")
async def api_approve(cart_id: str, body: OwnerYesIn):
    return _call(approve_cart, cart_id, owner_yes=body.owner_yes, job_id=body.job_id)


@router.post("/supplier-carts/{cart_id}/checkout")
async def api_checkout(cart_id: str, body: OwnerYesIn):
    return _call(checkout_cart, cart_id, owner_yes=body.owner_yes)


@router.post("/supplier-carts/{cart_id}/pay")
async def api_pay(cart_id: str, body: OwnerYesIn):
    return _call(pay_cart, cart_id, owner_yes=body.owner_yes)


@router.get("/jobs/{job_id}/purchase-orders")
async def api_job_pos(job_id: str):
    return {"job_id": job_id, "purchase_orders": list_job_purchase_orders(job_id)}
