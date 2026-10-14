"""3D job viewer API. Preview is a draft. Publish is founder-tap only."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.job_viewer.publisher import PublishNotConfigured, get_publisher
from app.services.job_viewer.service import (
    JobViewerError,
    ViewerForbidden,
    get_viewer_status,
    preview_from_job,
    preview_from_quote,
    publish_viewer,
    unpublish_viewer,
)

router = APIRouter(tags=["job-viewer"])


class FounderTap(BaseModel):
    founder_pin: Optional[str] = None


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, ViewerForbidden):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, PublishNotConfigured):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, JobViewerError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _preview_payload(result: dict, as_html: bool):
    if as_html:
        return HTMLResponse(result["html"], headers={"X-Viewer-Draft": "1"})
    return {
        "draft": True,
        "published": False,
        "auto_published": False,
        "title": result.get("title"),
        "html": result["html"],
        "viewer": result.get("viewer") or {"published": False, "status": "draft"},
        "job_id": result.get("job_id"),
        "quote_id": result.get("quote_id"),
        "part_count": len((result.get("scene") or {}).get("parts") or []),
    }


@router.get("/jobs/{job_id}/viewer")
def job_viewer_status(job_id: str):
    return get_viewer_status(job_id=job_id)


@router.post("/jobs/{job_id}/viewer/preview")
def job_viewer_preview(job_id: str, html: bool = False):
    try:
        result = preview_from_job(job_id)
    except Exception as exc:
        raise _err(exc)
    return _preview_payload(result, html)


@router.post("/jobs/{job_id}/viewer/publish")
def job_viewer_publish(job_id: str, body: FounderTap):
    try:
        return publish_viewer(job_id=job_id, founder_pin=body.founder_pin, publisher=get_publisher())
    except Exception as exc:
        raise _err(exc)


@router.post("/jobs/{job_id}/viewer/unpublish")
def job_viewer_unpublish(job_id: str, body: FounderTap):
    try:
        return unpublish_viewer(job_id=job_id, founder_pin=body.founder_pin, publisher=get_publisher())
    except Exception as exc:
        raise _err(exc)


@router.get("/quotes/{quote_id}/viewer")
@router.get("/quotes-v2/{quote_id}/viewer")
def quote_viewer_status(quote_id: str):
    return get_viewer_status(quote_id=quote_id)


@router.post("/quotes/{quote_id}/viewer/preview")
@router.post("/quotes-v2/{quote_id}/viewer/preview")
def quote_viewer_preview(quote_id: str, html: bool = False):
    try:
        result = preview_from_quote(quote_id)
    except Exception as exc:
        raise _err(exc)
    return _preview_payload(result, html)


@router.post("/quotes/{quote_id}/viewer/publish")
@router.post("/quotes-v2/{quote_id}/viewer/publish")
def quote_viewer_publish(quote_id: str, body: FounderTap):
    try:
        return publish_viewer(quote_id=quote_id, founder_pin=body.founder_pin, publisher=get_publisher())
    except Exception as exc:
        raise _err(exc)


@router.post("/quotes/{quote_id}/viewer/unpublish")
@router.post("/quotes-v2/{quote_id}/viewer/unpublish")
def quote_viewer_unpublish(quote_id: str, body: FounderTap):
    try:
        return unpublish_viewer(quote_id=quote_id, founder_pin=body.founder_pin, publisher=get_publisher())
    except Exception as exc:
        raise _err(exc)
