"""
AI Analysis Sessions — Backend persistence for PhotoAnalysisPanel sessions.
Replaces localStorage-only storage with server-side save/load.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/analysis-sessions", tags=["analysis-sessions"])

DATA_DIR = Path.home() / "empire-repo" / "backend" / "data" / "analysis_sessions"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Models ──

class AnalysisSessionSave(BaseModel):
    session_id: Optional[str] = None  # auto-generated if omitted
    mode: str = "measure"
    image_data: str = ""  # base64 or empty
    photos: list = Field(default_factory=list)
    active_photo_id: Optional[str] = None
    all_results: dict = Field(default_factory=dict)
    result: Optional[dict] = None
    measure_input_method: str = "photo"
    selected_styles: list = Field(default_factory=list)
    preferences: str = ""
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    job_id: Optional[str] = None
    title: Optional[str] = None


class AnalysisSessionMeta(BaseModel):
    session_id: str
    title: str
    mode: str
    photo_count: int
    result_count: int
    customer_name: Optional[str]
    created_at: str
    updated_at: str


# ── Helpers ──

def _session_path(session_id: str) -> Path:
    # Sanitize ID to prevent directory traversal
    safe_id = session_id.replace("/", "").replace("..", "")
    return DATA_DIR / f"{safe_id}.json"


def _load_session(session_id: str) -> dict:
    path = _session_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return json.loads(path.read_text())


# ── Endpoints ──

@router.post("/save")
async def save_session(data: AnalysisSessionSave):
    """Save or update an AI analysis session."""
    session_id = data.session_id or str(uuid.uuid4())
    path = _session_path(session_id)
    now = datetime.utcnow().isoformat()

    # Load existing to preserve created_at
    existing = None
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except Exception:
            pass

    # Auto-generate title
    title = data.title
    if not title:
        parts = []
        if data.customer_name:
            parts.append(data.customer_name)
        parts.append(data.mode.capitalize())
        photo_count = len(data.photos)
        if photo_count:
            parts.append(f"{photo_count} photo{'s' if photo_count != 1 else ''}")
        title = " — ".join(parts) if parts else f"Analysis {session_id[:8]}"

    session = {
        "session_id": session_id,
        "title": title,
        "mode": data.mode,
        "image_data": data.image_data,
        "photos": data.photos,
        "active_photo_id": data.active_photo_id,
        "all_results": data.all_results,
        "result": data.result,
        "measure_input_method": data.measure_input_method,
        "selected_styles": data.selected_styles,
        "preferences": data.preferences,
        "customer_name": data.customer_name,
        "customer_email": data.customer_email,
        "job_id": data.job_id,
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }

    path.write_text(json.dumps(session, default=str))

    return {
        "session_id": session_id,
        "title": title,
        "created_at": session["created_at"],
        "updated_at": now,
        "status": "saved",
    }


@router.get("/list")
async def list_sessions(
    customer_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List saved analysis sessions (newest first)."""
    sessions = []
    for path in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            # Filter by customer if specified
            if customer_name and customer_name.lower() not in (data.get("customer_name") or "").lower():
                continue
            sessions.append(AnalysisSessionMeta(
                session_id=data["session_id"],
                title=data.get("title", "Untitled"),
                mode=data.get("mode", "measure"),
                photo_count=len(data.get("photos", [])),
                result_count=len(data.get("all_results", {})),
                customer_name=data.get("customer_name"),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            ))
        except Exception:
            continue

    # Sort newest first
    sessions.sort(key=lambda s: s.updated_at, reverse=True)

    return {
        "sessions": [s.model_dump() for s in sessions[offset:offset + limit]],
        "total": len(sessions),
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Load a full analysis session by ID."""
    return _load_session(session_id)


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete an analysis session."""
    path = _session_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    path.unlink()
    return {"status": "deleted", "session_id": session_id}
