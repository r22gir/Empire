"""Return ALL matching finals for a client, not just the newest one.

2026-10-05: "Nehal final estimate" returned only Phase 1 because
doc_lookup.find_docs picks `count or 1` docs. Rafael has two finals for Nehal
(EST-2026-297 phase 1 v26, EST-2026-298 phase 2 v8). When he names a client
and no explicit count, list every final of the asked type (or every final
estimate/presentation/invoice/drawing when no type). Read-only; uses the
same docs hub as doc_lookup (whose file is not modified here).
"""
from __future__ import annotations

from typing import Any, Optional

TYPE_ORDER = ["estimate", "presentation", "invoice", "drawing"]
MAX_DOCS = 8


def expand_finals(text: str, found: Optional[dict], *, hub_get=None) -> Optional[dict]:
    if not found or not found.get("found") or not found.get("client"):
        return found
    from app.services.max import doc_lookup as dl
    req = dl.parse_request(text)
    if req.get("count") or req.get("quote_number"):
        return found
    get = hub_get or dl.default_hub_get
    params: dict[str, str] = {"final": "1", "limit": "80", "client": str(found["client"])}
    if req.get("type"):
        params["type"] = req["type"]
    try:
        listing = get("/api/v1/docs-hub", params) or {}
    except Exception:
        return found
    docs = [d for d in listing.get("docs") or [] if dl._is_pdf(d)]
    if not req.get("type"):
        docs = [d for d in docs if d.get("type") in TYPE_ORDER]
    if len(docs) <= len(found.get("docs") or []):
        return found
    docs.sort(key=lambda d: d.get("modified") or "", reverse=True)
    docs.sort(key=lambda d: TYPE_ORDER.index(d["type"]) if d.get("type") in TYPE_ORDER else 99)
    out: dict[str, Any] = dict(found)
    out["docs"] = [dl._fmt(d) for d in docs[:MAX_DOCS]]
    out["count"] = len(out["docs"])
    out["total_finals"] = len(docs)
    return out
