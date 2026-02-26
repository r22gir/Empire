"""
Empire AI Desks — API routes for desk configurations.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from app.db.database import get_db, dict_row, dict_rows
from app.db.init_db import init_database

router = APIRouter(prefix="/desks", tags=["desks"])

# Ensure DB + tables exist on import
init_database()


class DeskUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[list] = None
    layout: Optional[list] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/")
def list_desks():
    """List all desk configurations."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM desk_configs WHERE is_active = 1 ORDER BY sort_order"
        ).fetchall()
        desks = dict_rows(rows)
        # Parse JSON fields
        for d in desks:
            d["tools"] = json.loads(d["tools"]) if d.get("tools") else []
            d["layout"] = json.loads(d["layout"]) if d.get("layout") else []
        return {"desks": desks}


@router.get("/{desk_id}")
def get_desk(desk_id: str):
    """Get a single desk config with its system prompt."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM desk_configs WHERE desk_id = ?", (desk_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Desk '{desk_id}' not found")
        desk = dict_row(row)
        desk["tools"] = json.loads(desk["tools"]) if desk.get("tools") else []
        desk["layout"] = json.loads(desk["layout"]) if desk.get("layout") else []
        return desk


@router.patch("/{desk_id}")
def update_desk(desk_id: str, update: DeskUpdate):
    """Update a desk configuration."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT desk_id FROM desk_configs WHERE desk_id = ?", (desk_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Desk '{desk_id}' not found")

        fields = []
        values = []
        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        for key, val in data.items():
            if key in ("tools", "layout"):
                val = json.dumps(val)
            if key == "is_active":
                val = 1 if val else 0
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(desk_id)

        conn.execute(
            f"UPDATE desk_configs SET {', '.join(fields)} WHERE desk_id = ?",
            values,
        )
        return get_desk(desk_id)
