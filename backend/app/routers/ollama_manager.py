"""Ollama Model Manager — list, pull, delete models + system-level toggle."""
import subprocess
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

OLLAMA_URL = "http://localhost:11434"


# ── System-level Ollama toggle ─────────────────────────────────────

def _is_ollama_running() -> bool:
    """Check via systemctl if Ollama service is active."""
    try:
        r = subprocess.run(
            ["systemctl", "is-active", "--quiet", "ollama"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def _is_classifier_running() -> bool:
    """Check if the RecoveryForge classifier process is running."""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "classify_images"],
            capture_output=True, text=True, timeout=5,
        )
        return bool(r.stdout.strip())
    except Exception:
        return False


@router.get("/system/ollama/status")
async def ollama_system_status():
    """Get Ollama service status and RecoveryForge classifier progress."""
    ollama_running = _is_ollama_running()
    classifier_running = _is_classifier_running()

    # Try to get classifier progress from the progress file
    images_processed = 0
    images_total = 18472
    try:
        import json
        from pathlib import Path
        progress_file = Path.home() / "empire-repo" / "backend" / "data" / "recoveryforge" / "classifier_progress.json"
        if progress_file.exists():
            data = json.loads(progress_file.read_text())
            images_processed = data.get("processed", 0)
            images_total = data.get("total", 18472)
    except Exception:
        pass

    percentage = round((images_processed / images_total) * 100, 1) if images_total > 0 else 0

    return {
        "ollama": "running" if ollama_running else "stopped",
        "classifier_running": classifier_running,
        "images_processed": images_processed,
        "images_total": images_total,
        "percentage": percentage,
    }


@router.post("/system/ollama/toggle")
async def ollama_toggle():
    """Toggle Ollama on/off. If running → stop (and kill classifier). If stopped → start."""
    ollama_running = _is_ollama_running()

    if ollama_running:
        # Stop Ollama + kill classifier
        try:
            subprocess.run(["systemctl", "stop", "ollama"], capture_output=True, timeout=15)
        except Exception:
            pass
        # Kill classifier if running
        if _is_classifier_running():
            try:
                subprocess.run(["pkill", "-f", "classify_images"], capture_output=True, timeout=5)
            except Exception:
                pass
        return {
            "ollama": "stopped",
            "classifier": "stopped",
            "message": "Ollama stopped. MAX will respond faster.",
        }
    else:
        # Start Ollama
        try:
            subprocess.run(["systemctl", "start", "ollama"], capture_output=True, timeout=15)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start Ollama: {e}")
        return {
            "ollama": "running",
            "classifier": "stopped",
            "message": "Ollama started. You can now resume RecoveryForge classification.",
        }


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
