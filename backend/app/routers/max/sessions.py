"""MAX session log API (max-sessions 2026-10-04).

Mounted inside the /max router, so it answers at both
/max/sessions/... and /api/v1/max/sessions/...

  GET  /max/sessions?days=7               recent journaled sessions
  GET  /max/sessions/{conversation_id}     full turns (images as URLs)
  GET  /max/sessions/attachment/{sha}      archived image/file bytes
  POST /max/sessions/export?date=YYYY-MM-DD  write the daily export
                                           (default: today, ET)

Main studio only: the export refuses to run in a family edition.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/sessions", tags=["MAX Sessions"])


def _attachment_urls(turn: dict) -> dict:
    out = []
    for a in turn.get("attachments") or []:
        a = {k: v for k, v in a.items() if k not in ("archive_path", "source_path")}
        if a.get("sha256"):
            a["url"] = f"/api/v1/max/sessions/attachment/{a['sha256'][:24]}"
        out.append(a)
    turn = dict(turn)
    turn["attachments"] = out
    return turn


@router.post("/export")
async def export_sessions(date_: Optional[str] = Query(None, alias="date"), include_tests: bool = False):
    from app.services.max import session_export as se
    from app.services.max.session_journal import _local_tz
    try:
        day = date.fromisoformat(date_) if date_ else datetime.now(_local_tz()).date()
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    try:
        summary = await asyncio.to_thread(se.export_day, day, include_tests=include_tests)
    except se.FamilyEditionError as exc:
        raise HTTPException(403, str(exc))
    return {
        "path": summary["path"], "date": summary["date"], "sessions": summary["sessions"],
        "turns": summary["turns"], "images": summary["images"], "counts": summary["counts"],
        "by_channel": summary["by_channel"],
    }


@router.get("")
async def list_sessions(days: int = 7, limit: int = 100):
    from app.services.max.session_journal import list_sessions as _ls
    return {"sessions": _ls(days=days, limit=limit)}


@router.get("/attachment/{sha}")
async def get_attachment(sha: str):
    from app.services.max.session_journal import attachment_path
    path = attachment_path(sha)
    if not path:
        raise HTTPException(404, "attachment not found")
    return FileResponse(path)


@router.get("/{conversation_id}")
async def get_session(conversation_id: str):
    from app.services.max.session_journal import get_session as _gs
    turns = _gs(conversation_id)
    if not turns:
        raise HTTPException(404, "session not found in journal")
    return {"conversation_id": conversation_id, "turns": [_attachment_urls(t) for t in turns]}
