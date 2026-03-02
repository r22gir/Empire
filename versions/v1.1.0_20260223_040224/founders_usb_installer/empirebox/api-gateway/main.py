"""EmpireBox API Gateway — routes requests to internal services."""

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await _http_client.aclose()


app = FastAPI(title="EmpireBox API Gateway", version="1.0.0", lifespan=lifespan)

_allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES = {
    "control": os.getenv("CONTROL_CENTER_URL", "http://control-center:8001"),
    "voice": os.getenv("VOICE_SERVICE_URL", "http://voice-service:8200"),
    "openclaw": os.getenv("OPENCLAW_URL", "http://openclaw:7878"),
}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(service: str, path: str, request: Request) -> Response:
    base_url = SERVICES.get(service)
    if base_url is None:
        return Response(content=f"Unknown service: {service}", status_code=404)

    url = f"{base_url}/{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    try:
        resp = await _http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )
    except httpx.TimeoutException:
        return Response(content="Upstream service timed out", status_code=504)
    except httpx.RequestError as exc:
        return Response(content=f"Could not reach upstream service: {exc}", status_code=502)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )
