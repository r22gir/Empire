"""
Minimal MarketForge product API used by ArchiveForge publish.

The older SQLAlchemy marketplace product router is not mounted in this runtime
and is not SQLite-safe as-is. This route keeps the public MarketForge product
creation contract small and durable: create a local product record, return its
real ID, and let ArchiveForge bind that ID to the archive item.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.database import DB_PATH, dict_rows, dict_row


router = APIRouter(prefix="/marketplace/products", tags=["marketforge-products"])


class MarketForgeProductCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    category_id: str = ""
    condition: str = Field(..., pattern="^(new|like_new|good|fair|poor)$")
    price: float = Field(..., gt=0)
    shipping_price: float | None = Field(None, ge=0)
    offers_enabled: bool = False
    minimum_offer: float | None = Field(None, gt=0)
    images: list[str] = []
    package_weight_oz: int = Field(..., gt=0)
    package_length_in: int = Field(..., gt=0)
    package_width_in: int = Field(..., gt=0)
    package_height_in: int = Field(..., gt=0)
    ships_from_zip: str = Field(..., pattern=r"^\d{5}$")
    quantity: int = Field(default=1, ge=1)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_marketforge_products() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mf_products (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL DEFAULT 'archiveforge',
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category_id TEXT DEFAULT '',
                condition TEXT NOT NULL,
                price REAL NOT NULL,
                shipping_price REAL,
                offers_enabled INTEGER NOT NULL DEFAULT 0,
                minimum_offer REAL,
                images TEXT NOT NULL DEFAULT '[]',
                package_weight_oz INTEGER NOT NULL,
                package_length_in INTEGER NOT NULL,
                package_width_in INTEGER NOT NULL,
                package_height_in INTEGER NOT NULL,
                ships_from_zip TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()


def _serialize_product(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    product = dict_row(row)
    try:
        product["images"] = json.loads(product.get("images") or "[]")
    except (TypeError, json.JSONDecodeError):
        product["images"] = []
    product["offers_enabled"] = bool(product.get("offers_enabled"))
    return product


_init_marketforge_products()


@router.get("")
def list_marketforge_products(limit: int = Query(50, ge=1, le=200)):
    with _conn() as conn:
        rows = dict_rows(
            conn.execute(
                "SELECT * FROM mf_products ORDER BY datetime(created_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        )
    for row in rows:
        try:
            row["images"] = json.loads(row.get("images") or "[]")
        except (TypeError, json.JSONDecodeError):
            row["images"] = []
        row["offers_enabled"] = bool(row.get("offers_enabled"))
    return {"products": rows, "total": len(rows), "source": "marketforge_sqlite"}


@router.post("", status_code=201)
def create_marketforge_product(payload: MarketForgeProductCreate):
    if not payload.images:
        raise HTTPException(status_code=400, detail="At least one actual listing image is required.")

    product_id = f"mf_{uuid.uuid4().hex}"
    data = payload.model_dump()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO mf_products (
                id, source, title, description, category_id, condition, price,
                shipping_price, offers_enabled, minimum_offer, images,
                package_weight_oz, package_length_in, package_width_in,
                package_height_in, ships_from_zip, quantity, status
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                product_id,
                "archiveforge",
                data["title"],
                data["description"],
                data.get("category_id") or "",
                data["condition"],
                data["price"],
                data.get("shipping_price"),
                1 if data.get("offers_enabled") else 0,
                data.get("minimum_offer"),
                json.dumps(data.get("images") or []),
                data["package_weight_oz"],
                data["package_length_in"],
                data["package_width_in"],
                data["package_height_in"],
                data["ships_from_zip"],
                data["quantity"],
                "draft",
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM mf_products WHERE id = ?", (product_id,)).fetchone()

    product = _serialize_product(row)
    return {
        **product,
        "marketforge_listing_id": product_id,
        "publish_status": "created",
    }


@router.get("/{product_id}")
def get_marketforge_product(product_id: str):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM mf_products WHERE id = ?", (product_id,)).fetchone()
    product = _serialize_product(row)
    if not product:
        raise HTTPException(status_code=404, detail="MarketForge product not found")
    return product
