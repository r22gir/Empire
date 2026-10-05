"""Proxy Final Docs hub routes to the Next.js portal.

docs-hub lives in empire-command-center (Next API routes under
app/api/v1/docs-hub/*). Cloudflare sends /api/v1/* to this FastAPI
process, so without a mount those URLs 404. Forward to the portal
(filesystem routes take precedence over the portal's /api/v1 rewrite,
so this does not loop).
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["docs-hub-portal-proxy"])

_PORTAL = (os.getenv("EMPIRE_DOCS_HUB_PORTAL")
           or os.getenv("EMPIRE_FRONTEND_HEALTH_URL")
           or "http://127.0.0.1:3005").rstrip("/")

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


async def _forward(request: Request, subpath: str = "") -> Response:
    path = "/api/v1/docs-hub" + (f"/{subpath}" if subpath else "")
    url = f"{_PORTAL}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
    body = await request.body()
    timeout = httpx.Timeout(120.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        upstream = await client.request(
            request.method, url, headers=headers, content=body or None,
        )
    out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP}
    return Response(content=upstream.content, status_code=upstream.status_code, headers=out_headers)


@router.api_route("/docs-hub", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def docs_hub_root(request: Request) -> Response:
    return await _forward(request)


@router.api_route("/docs-hub/{subpath:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def docs_hub_sub(request: Request, subpath: str) -> Response:
    return await _forward(request, subpath)
