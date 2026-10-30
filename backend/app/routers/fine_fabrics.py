"""Empire Fine Fabrics — public catalog + owner import.

Customer endpoints never return net cost or vendor name unless the
vendor's brand_display_allowed flag is true. Vendors with
online_sale_allowed=false are omitted from the public catalog.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services.fine_fabrics.catalog import (
    CATEGORIES,
    get_product,
    list_catalog,
    list_vendors,
)
from app.services.fine_fabrics.importer import import_csv_text
from app.services.fine_fabrics.photos import photos_dir, read_photo, save_owner_photo
from app.services.fine_fabrics.preview import preview_fabric
from app.services.fine_fabrics.schema import ensure_fine_fabrics_schema

router = APIRouter(prefix="/fine-fabrics", tags=["fine-fabrics"])

ensure_fine_fabrics_schema()


class CartItemIn(BaseModel):
    product_id: int
    yards: float = Field(gt=0)


class CheckoutIn(BaseModel):
    name: str
    email: str
    phone: str = ""
    address: str = ""
    items: List[CartItemIn]
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class SampleIn(BaseModel):
    name: str
    email: str
    phone: str = ""
    product_ids: List[int]
    notes: str = ""


class PreviewIn(BaseModel):
    product_id: int
    item_type: str = "roman_shade"


class VendorFlagsIn(BaseModel):
    online_sale_allowed: Optional[bool] = None
    brand_display_allowed: Optional[bool] = None
    default_markup: Optional[float] = None


class MarkupIn(BaseModel):
    category: str
    markup: float = Field(gt=0)


def _owner_host(request: Request) -> bool:
    host = (request.headers.get("host") or "").split(":")[0].lower()
    return host not in {"fabrics.empirebox.store", "test-fabrics.empirebox.store"}


def _require_owner(request: Request) -> None:
    if not _owner_host(request):
        raise HTTPException(401, "Owner tools are not available on the public fabrics host")


@router.get("/health")
def health():
    return {"ok": True, "store": "Empire Fine Fabrics", "stripe_mode": "test"}


@router.get("/categories")
def categories():
    return {"categories": list(CATEGORIES)}


@router.get("/catalog")
def catalog(category: Optional[str] = None, search: Optional[str] = None):
    return {"products": list_catalog(category=category, search=search, owner=False)}


@router.get("/products/{product_id}")
def product_page(product_id: int):
    product = get_product(product_id, owner=False, allow_hidden=False)
    if not product:
        raise HTTPException(404, "Fabric not found")
    return product


@router.get("/photos/{product_id}")
def product_photo(product_id: int):
    product = get_product(product_id, owner=True, allow_hidden=False)
    if not product:
        raise HTTPException(404, "Photo not found")
    stored = (product.get("image_path") or "").strip()
    if not stored:
        raise HTTPException(404, "No owner photo for this fabric")
    path = read_photo(stored)
    if path is None:
        # image_path may be stored as a relative name
        candidate = photos_dir() / stored
        if not candidate.is_file():
            raise HTTPException(404, "Photo file missing")
        path = candidate
    return FileResponse(path)


@router.post("/checkout")
def checkout(payload: CheckoutIn):
    from app.services.fine_fabrics.checkout import checkout_cart

    try:
        return checkout_cart(
            {
                "name": payload.name,
                "email": payload.email,
                "phone": payload.phone,
                "address": payload.address,
            },
            [item.model_dump() for item in payload.items],
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/samples")
def request_samples(payload: SampleIn):
    if not payload.product_ids:
        raise HTTPException(400, "Select at least one fabric")
    visible = []
    for pid in payload.product_ids:
        product = get_product(pid, owner=False, allow_hidden=False)
        if not product:
            raise HTTPException(404, f"Fabric {pid} is not available for samples")
        visible.append(product["id"])
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ff_sample_requests
               (customer_name, customer_email, customer_phone, product_ids, notes, business)
               VALUES (?, ?, ?, ?, ?, 'workroom')""",
            (
                payload.name,
                payload.email,
                payload.phone,
                json.dumps(visible),
                payload.notes,
            ),
        )
        request_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {
        "id": request_id,
        "status": "new",
        "product_ids": visible,
        "message": "Sample request received. Empire will confirm by email — no client email is sent automatically.",
    }


@router.post("/preview")
def preview(payload: PreviewIn):
    try:
        return preview_fabric(payload.product_id, item_type=payload.item_type)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/vendors")
def vendors(request: Request):
    _require_owner(request)
    return {"vendors": list_vendors()}


@router.put("/vendors/{vendor_id}")
def update_vendor(vendor_id: int, payload: VendorFlagsIn, request: Request):
    _require_owner(request)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    fields = []
    values = []
    for key, value in updates.items():
        if key in ("online_sale_allowed", "brand_display_allowed"):
            value = 1 if value else 0
        fields.append(f"{key} = ?")
        values.append(value)
    values.append(vendor_id)
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM ff_vendors WHERE id = ?", (vendor_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Vendor not found")
        conn.execute(
            f"UPDATE ff_vendors SET {', '.join(fields)}, updated_at=datetime('now') WHERE id = ?",
            values,
        )
    return {"vendors": list_vendors()}


@router.put("/vendors/{vendor_id}/markups")
def set_markup(vendor_id: int, payload: MarkupIn, request: Request):
    _require_owner(request)
    if payload.category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {CATEGORIES}")
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM ff_vendors WHERE id = ?", (vendor_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Vendor not found")
        conn.execute(
            """INSERT INTO ff_markups (vendor_id, category, markup)
               VALUES (?, ?, ?)
               ON CONFLICT(vendor_id, category) DO UPDATE SET markup=excluded.markup""",
            (vendor_id, payload.category, payload.markup),
        )
    return {"vendors": list_vendors()}


@router.post("/import")
async def import_csv(request: Request, file: UploadFile = File(...)):
    _require_owner(request)
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "CSV must be UTF-8") from exc
    try:
        result = import_csv_text(text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


@router.get("/admin/products")
def admin_products(request: Request, category: Optional[str] = None, search: Optional[str] = None):
    _require_owner(request)
    return {"products": list_catalog(category=category, search=search, include_hidden=True, owner=True)}


@router.post("/products/{product_id}/photos")
async def upload_photo(product_id: int, request: Request, file: UploadFile = File(...)):
    _require_owner(request)
    product = get_product(product_id, owner=True, allow_hidden=True)
    if not product:
        raise HTTPException(404, "Fabric not found")
    content = await file.read()
    try:
        stored = save_owner_photo(product_id, file.filename or "swatch.jpg", content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    with get_db() as conn:
        conn.execute(
            "UPDATE ff_products SET image_path = ?, updated_at=datetime('now') WHERE id = ?",
            (stored, product_id),
        )
    return get_product(product_id, owner=True, allow_hidden=True)


def seed_demo_catalog() -> dict | None:
    """Load the bundled mock CSV when FINE_FABRICS_SEED_DEMO=1 and catalog is empty."""
    if os.getenv("FINE_FABRICS_SEED_DEMO") != "1":
        return None
    ensure_fine_fabrics_schema()
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM ff_products").fetchone()[0]
        if count:
            return None
    example = (
        os.path.join(os.path.dirname(__file__), "..", "data", "fine_fabrics", "example_import.csv")
    )
    path = os.path.abspath(example)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return import_csv_text(handle.read())


try:
    seed_demo_catalog()
except Exception:
    pass
