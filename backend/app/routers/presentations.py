"""Presentation sharing — client-facing presentation links."""
import os
import json
import sqlite3
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/presentations/{presentation_id}")
async def get_presentation(presentation_id: str):
    """Get a shared presentation by ID (public endpoint — no auth required)."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM design_sessions WHERE share_link LIKE ? OR id = ?",
        (f"%{presentation_id}%", presentation_id)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Presentation not found")

    d = dict(row)
    drawings = json.loads(d.get("drawing_urls") or "[]")
    quote = json.loads(d.get("quote_data") or "{}")

    return {
        "id": d["id"],
        "client_name": d.get("client_name", ""),
        "project_address": d.get("project_address", ""),
        "room": d.get("room", ""),
        "job_description": d.get("job_description", ""),
        "drawings": drawings,
        "quote_data": quote,
        "status": d.get("status", "in_progress"),
        "created_at": d.get("created_at", ""),
    }


@router.post("/presentations/{presentation_id}/viewed")
async def track_view(presentation_id: str):
    """Track when a client views a shared presentation."""
    # Log the view (could be expanded with IP, user agent, etc.)
    conn = _get_db()
    conn.execute(
        "UPDATE design_sessions SET updated_at = ? WHERE share_link LIKE ? OR id = ?",
        (datetime.now().isoformat(), f"%{presentation_id}%", presentation_id)
    )
    conn.commit()
    conn.close()
    return {"status": "viewed"}


class CreatePresentationRequest(BaseModel):
    client_name: str
    project_address: str = ""
    room: str = ""
    job_description: str = ""
    drawings: list = []
    quote_data: dict = {}


@router.post("/presentations")
async def create_presentation(req: CreatePresentationRequest):
    """Create a shareable presentation from a design session."""
    share_id = uuid.uuid4().hex[:12]
    conn = _get_db()
    conn.execute(
        """INSERT INTO design_sessions (client_name, project_address, room, job_description,
           drawing_urls, quote_data, share_link, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'completed')""",
        (req.client_name, req.project_address, req.room, req.job_description,
         json.dumps(req.drawings), json.dumps(req.quote_data), share_id)
    )
    conn.commit()
    conn.close()

    base_url = os.getenv("CC_PUBLIC_URL", "https://studio.empirebox.store")
    return {
        "share_id": share_id,
        "share_url": f"{base_url}/presentation/{share_id}",
        "status": "created",
    }
