"""Ollama Model Manager — list, pull, delete models via Ollama API."""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

OLLAMA_URL = "http://localhost:11434"


class PullRequest(BaseModel):
    name: str


@router.get("/ollama/models")
async def list_models():
    """List all installed Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                models.append({
                    "name": m.get("name"),
                    "size_gb": round(m.get("size", 0) / (1024 ** 3), 2),
                    "modified_at": m.get("modified_at"),
                    "digest": m.get("digest", "")[:12],
                })
            return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not reachable: {e}")


@router.post("/ollama/pull")
async def pull_model(req: PullRequest):
    """Pull a new model from Ollama registry."""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": req.name, "stream": False},
            )
            resp.raise_for_status()
            return {"status": "pulled", "model": req.name}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Pull timed out (model may be very large)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ollama/models/{name:path}")
async def delete_model(name: str):
    """Delete an installed Ollama model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{OLLAMA_URL}/api/delete",
                json={"name": name},
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Model not found: {name}")
            resp.raise_for_status()
            return {"status": "deleted", "model": name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
