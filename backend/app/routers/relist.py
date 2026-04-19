"""Legacy RelistApp listing CRUD.

The active RelistApp surface lives in app.routers.relistapp under /relist.
These endpoints are intentionally namespaced under /relist-legacy so they do
not masquerade as the canonical drop-ship RelistApp API.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
import logging

from app.db.database import get_db, dict_rows, dict_row

router = APIRouter(prefix="/relist-legacy", tags=["relist-legacy"])
log = logging.getLogger("relist")


class ListingCreate(BaseModel):
    title: str
    description: str = ""
    price: float = 0
    category: str = "Other"
    condition: str = "good"
    platforms: List[str] = []
    quantity: int = 1


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    condition: Optional[str] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None
    quantity: Optional[int] = None


@router.get("")
async def list_listings(status: Optional[str] = None, limit: int = 100):
    """Get all listings."""
    with get_db() as db:
        if status:
            rows = dict_rows(db.execute(
                "SELECT * FROM listings WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall())
        else:
            rows = dict_rows(db.execute(
                "SELECT * FROM listings ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall())
        for d in rows:
            for field in ['images', 'platforms', 'platform_ids']:
                if field in d and isinstance(d[field], str):
                    try:
                        d[field] = json.loads(d[field])
                    except:
                        d[field] = []
        return rows


@router.post("")
async def create_listing(req: ListingCreate):
    """Create a new listing."""
    with get_db() as db:
        cursor = db.execute(
            """INSERT INTO listings (title, description, price, category, condition, platforms, quantity, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'draft')""",
            (req.title, req.description, req.price, req.category, req.condition,
             json.dumps(req.platforms), req.quantity),
        )
        db.commit()
        listing_id = cursor.lastrowid
    log.info(f"Listing #{listing_id} created: {req.title}")
    return {"id": listing_id, "title": req.title, "status": "draft", "platforms": req.platforms}


@router.get("/{listing_id}")
async def get_listing(listing_id: int):
    """Get a specific listing."""
    with get_db() as db:
        row = db.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Listing not found")
        d = dict_row(row)
        for field in ['images', 'platforms', 'platform_ids']:
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except:
                    d[field] = []
        return d


@router.put("/{listing_id}")
async def update_listing(listing_id: int, req: ListingUpdate):
    """Update a listing."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    if 'platforms' in updates:
        updates['platforms'] = json.dumps(updates['platforms'])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [listing_id]
    with get_db() as db:
        db.execute(f"UPDATE listings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        db.commit()
    return {"id": listing_id, "updated": True}


@router.delete("/{listing_id}")
async def delete_listing(listing_id: int):
    """Delete a listing."""
    with get_db() as db:
        db.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
        db.commit()
    return {"id": listing_id, "deleted": True}


@router.post("/{listing_id}/publish")
async def publish_listing(listing_id: int):
    """Publish a listing to selected platforms (stub — marks as active)."""
    with get_db() as db:
        db.execute("UPDATE listings SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (listing_id,))
        db.commit()
    return {"id": listing_id, "status": "active", "message": "Listing published (platform sync not yet connected)"}
