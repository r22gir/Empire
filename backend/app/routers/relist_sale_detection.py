"""Sandbox sale-detection routes. Mounted under /api/v1/relist/sale-detection."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import relist_sale_detection as sbx

router = APIRouter(prefix="/relist/sale-detection", tags=["relist-sale-detection"])


class SettingsUpdate(BaseModel):
    owner_confirm_required: bool


class SandboxListingCreate(BaseModel):
    source_product_id: str
    platform: str
    title: str = ""
    status: str = "active"


class SnapshotRequest(BaseModel):
    listings: List[dict] = Field(default_factory=list)


class SaleRequest(BaseModel):
    listing_id: str
    sale_price: float = 0
    note: str = ""


class ConfirmRequest(BaseModel):
    approve: bool = True


@router.get("/settings")
async def get_settings():
    return sbx.get_settings()


@router.put("/settings")
async def put_settings(req: SettingsUpdate):
    return sbx.update_settings(req.owner_confirm_required)


@router.get("/sandbox/listings")
async def sandbox_listings(source_product_id: Optional[str] = None):
    return {"items": sbx.list_listings(source_product_id), "sandbox": True}


@router.post("/sandbox/listings")
async def create_sandbox_listing(req: SandboxListingCreate):
    return sbx.upsert_listing(
        source_product_id=req.source_product_id,
        platform=req.platform,
        title=req.title,
        status=req.status,
    )


@router.post("/sandbox/seed")
async def seed_sandbox(req: SnapshotRequest):
    """Seed sandbox copies from caller-supplied listing snapshots.

    Does not query or write live ra_* tables.
    """
    created = sbx.snapshot_from_live_rows(req.listings)
    return {"created": len(created), "items": created, "sandbox": True}


@router.post("/sandbox/sales")
async def record_sandbox_sale(req: SaleRequest):
    try:
        return sbx.record_sale(req.listing_id, req.sale_price, req.note)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/events")
async def events(limit: int = 50):
    return {"items": sbx.list_events(limit), "sandbox": True}


@router.get("/confirmations")
async def pending():
    return {"items": sbx.list_pending_confirmations(), "sandbox": True}


@router.post("/confirmations/{event_id}")
async def resolve(event_id: str, req: ConfirmRequest):
    try:
        return sbx.resolve_confirmation(event_id, req.approve)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/state")
async def state():
    return sbx.export_state()
