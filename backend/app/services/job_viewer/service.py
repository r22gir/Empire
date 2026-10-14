"""Orchestrate preview / publish / unpublish for Max's 3D job viewer.

Preview never writes to git. Publish is founder-tap only. Republish keeps
the same unguessable slug. Unpublish removes the Pages file.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Optional

from app.db.database import get_db
from app.services.job_viewer.geometry import build_scene
from app.services.job_viewer.html_generator import render_html
from app.services.job_viewer.publisher import (
    PublishNotConfigured,
    get_publisher,
)
from app.services.job_viewer.store import (
    ensure_schema,
    get_record,
    record_to_status,
    upsert_record,
)
from app.services.max.access_control import FOUNDER_APPROVAL_PIN


class JobViewerError(ValueError):
    pass


class ViewerForbidden(PermissionError):
    pass


def _require_founder_pin(founder_pin, op_name: str) -> None:
    if not FOUNDER_APPROVAL_PIN:
        raise ViewerForbidden(f"{op_name} requires FOUNDER_APPROVAL_PIN to be set")
    if not founder_pin or str(founder_pin) != str(FOUNDER_APPROVAL_PIN):
        raise ViewerForbidden(f"{op_name} requires a valid founder tap (PIN)")


def _sha(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def _load_job(job_id: str) -> dict:
    from app.routers import jobs_unified

    try:
        payload = jobs_unified.get_job(job_id)
    except Exception as exc:
        raise JobViewerError(f"Job {job_id} not found") from exc
    job = payload.get("job") if isinstance(payload, dict) and "job" in payload else payload
    if not job:
        raise JobViewerError(f"Job {job_id} not found")
    return job


def _load_quote(quote_id: str) -> dict:
    quote = None
    try:
        from app.services import quote_service

        quote = quote_service.get_quote(quote_id) or quote_service.get_quote_by_number(quote_id)
    except Exception:
        quote = None
    if quote:
        return quote
    # Legacy JSON quotes (tests / older jobs-from-quote path).
    try:
        from app.routers import quotes as quotes_router

        folder = getattr(quotes_router, "QUOTES_DIR", None)
        if folder:
            path = os.path.join(str(folder), f"{quote_id}.json")
            if os.path.exists(path):
                return json.loads(open(path, encoding="utf-8").read())
    except Exception:
        pass
    raise JobViewerError(f"Quote {quote_id} not found")


def _forbidden_from(source: dict) -> list[str]:
    keys = (
        "client_address", "customer_address", "address", "project_address",
        "client_email", "customer_email", "client_phone", "customer_phone",
    )
    out = [str(source[k]) for k in keys if source.get(k)]
    for row in source.get("line_items") or []:
        for key in ("rate", "amount", "unit_price", "price", "total"):
            if row.get(key) not in (None, "", 0, 0.0):
                out.append(f"${row[key]}")
                out.append(str(row[key]))
    if source.get("total") not in (None, "", 0, 0.0):
        out.append(f"${source['total']}")
    return [x for x in out if x and len(str(x)) >= 3]


def preview_from_payload(source: dict, *, draft: bool = True, source_kind: str = "job") -> dict:
    scene = build_scene(source, draft=draft, source_kind=source_kind)
    html = render_html(scene, extra_forbidden=_forbidden_from(source))
    return {"html": html, "scene": scene, "draft": draft, "title": scene["title"]}


def preview_from_job(job_id: str) -> dict:
    job = _load_job(job_id)
    result = preview_from_payload(job, draft=True, source_kind="job")
    result["job_id"] = job_id
    with get_db() as conn:
        ensure_schema(conn)
        rec = get_record(conn, job_id=job_id)
        result["viewer"] = record_to_status(rec)
    return result


def preview_from_quote(quote_id: str) -> dict:
    quote = _load_quote(quote_id)
    # Prefer a linked job when one exists so publish slugs stay stable.
    job_id = quote.get("job_id")
    if job_id:
        try:
            result = preview_from_job(job_id)
            result["quote_id"] = quote_id
            return result
        except JobViewerError:
            pass
    result = preview_from_payload(quote, draft=True, source_kind="quote")
    result["quote_id"] = quote_id
    with get_db() as conn:
        ensure_schema(conn)
        rec = get_record(conn, quote_id=quote_id)
        result["viewer"] = record_to_status(rec)
    return result


def get_viewer_status(*, job_id: Optional[str] = None, quote_id: Optional[str] = None) -> dict:
    with get_db() as conn:
        ensure_schema(conn)
        rec = get_record(conn, job_id=job_id, quote_id=quote_id)
        status = record_to_status(rec)
        status["job_id"] = job_id
        status["quote_id"] = quote_id
        return status


def publish_viewer(
    *,
    job_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    founder_pin: Optional[str] = None,
    publisher=None,
) -> dict:
    _require_founder_pin(founder_pin, "publish_viewer")
    if job_id:
        built = preview_from_job(job_id)
    elif quote_id:
        built = preview_from_quote(quote_id)
    else:
        raise JobViewerError("job_id or quote_id is required")
    # Published copy drops the DRAFT banner.
    source_kind = "job" if job_id else "quote"
    source = _load_job(job_id) if job_id else _load_quote(quote_id)
    scene = build_scene(source, draft=False, source_kind=source_kind)
    html = render_html(scene, extra_forbidden=_forbidden_from(source))
    pages = publisher or get_publisher()
    with get_db() as conn:
        ensure_schema(conn)
        rec = upsert_record(
            conn,
            job_id=job_id or built.get("job_id"),
            quote_id=quote_id or built.get("quote_id"),
            title=scene["title"],
            status="draft",
            html_sha=_sha(html),
        )
        slug = rec["slug"]
        try:
            url = pages.publish(slug, html, message=f"Publish Empire Workroom 3D viewer {slug}")
        except PublishNotConfigured:
            raise
        rec = upsert_record(
            conn,
            job_id=rec.get("job_id"),
            quote_id=rec.get("quote_id"),
            slug=slug,
            status="published",
            title=scene["title"],
            public_url=url,
            html_sha=_sha(html),
        )
        conn.commit()
    return {
        "published": True,
        "slug": rec["slug"],
        "url": rec["public_url"],
        "title": rec.get("title"),
        "viewer": record_to_status(rec),
        "html": html,
    }


def unpublish_viewer(
    *,
    job_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    founder_pin: Optional[str] = None,
    publisher=None,
) -> dict:
    _require_founder_pin(founder_pin, "unpublish_viewer")
    pages = publisher or get_publisher()
    with get_db() as conn:
        ensure_schema(conn)
        rec = get_record(conn, job_id=job_id, quote_id=quote_id)
        if not rec:
            raise JobViewerError("No published viewer for this job")
        pages.unpublish(rec["slug"])
        rec = upsert_record(
            conn,
            job_id=rec.get("job_id"),
            quote_id=rec.get("quote_id"),
            slug=rec["slug"],
            status="unpublished",
            title=rec.get("title"),
            public_url=None,
            html_sha=rec.get("html_sha"),
        )
        conn.commit()
    return {"published": False, "slug": rec["slug"], "viewer": record_to_status(rec)}
