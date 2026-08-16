"""
Empire Ecosystem module: Label Station
======================================

Serves the weigh-and-label PWA and, optionally, a shared product catalog
backed by empire.db so every phone sees the same prices.

Mount into the existing EmpireBox FastAPI app:

    from modules.label_station import router as label_station_router
    app.include_router(label_station_router)

Environment:
    EMPIRE_DB              path to empire.db
                           (default /home/rg/empire-data/empire.db)
    LABEL_STATION_DIR      directory holding weigh-and-label.html
                           (default: ./static alongside this file)
    LABEL_STATION_BUSINESS default business key for the catalog
                           (default "empire_workroom" — never hardcode a value
                           into a table row; this is only the fallback key)

Design notes:
  * Every canonical table carries a `business` column, per EmpireBox rules.
  * No printer is involved. The phone renders the label and hands the PNG to
    whatever prints it. This module is hosting plus catalog storage only.
  * The app degrades gracefully: if these endpoints are unreachable it falls
    back to on-device storage, so a backend outage never blocks a sale.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("EMPIRE_DB", "/home/rg/empire-data/empire.db")
APP_DIR = Path(os.environ.get("LABEL_STATION_DIR", Path(__file__).parent / "static"))
DEFAULT_BUSINESS = os.environ.get("LABEL_STATION_BUSINESS", "empire_workroom")

MAX_PRODUCTS = 10

router = APIRouter(prefix="/label", tags=["label-station"])


# --------------------------------------------------------------------- db
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS label_catalog (
                business   TEXT PRIMARY KEY,
                products   TEXT NOT NULL DEFAULT '[]',
                settings   TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


init_db()


# ----------------------------------------------------------------- models
class Catalog(BaseModel):
    products: list[dict] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


# ----------------------------------------------------------------- routes
@router.get("/api/health")
def health():
    return {"ok": True, "module": "label_station", "max_products": MAX_PRODUCTS}


@router.get("/api/catalog")
def get_catalog(business: str = Query(DEFAULT_BUSINESS)):
    with _conn() as c:
        row = c.execute(
            "SELECT products, settings FROM label_catalog WHERE business = ?",
            (business,),
        ).fetchone()
    if not row:
        return {"products": [], "settings": {}, "business": business}
    return {
        "products": json.loads(row["products"]),
        "settings": json.loads(row["settings"]),
        "business": business,
    }


@router.put("/api/catalog")
def put_catalog(payload: Catalog, business: str = Query(DEFAULT_BUSINESS)):
    if len(payload.products) > MAX_PRODUCTS:
        raise HTTPException(400, f"Catalog is capped at {MAX_PRODUCTS} products.")
    with _conn() as c:
        c.execute(
            """
            INSERT INTO label_catalog (business, products, settings, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(business) DO UPDATE SET
                products   = excluded.products,
                settings   = excluded.settings,
                updated_at = excluded.updated_at
            """,
            (business, json.dumps(payload.products), json.dumps(payload.settings)),
        )
    return {"ok": True, "count": len(payload.products), "business": business}


@router.get("/manifest.json")
def manifest():
    return JSONResponse(
        {
            "name": "Weigh & Label Station",
            "short_name": "Weigh",
            "start_url": "/label/",
            "scope": "/label/",
            "display": "standalone",
            "background_color": "#ecefea",
            "theme_color": "#16211d",
        }
    )


@router.get("/")
def index():
    page = APP_DIR / "weigh-and-label.html"
    if not page.exists():
        raise HTTPException(
            500,
            f"weigh-and-label.html not found in {APP_DIR}. Set LABEL_STATION_DIR.",
        )
    return FileResponse(page, media_type="text/html")


@router.get("", include_in_schema=False)
def index_noslash():
    return index()
