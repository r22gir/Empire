"""
RecoveryForge API — status, start, stop for the Layer 3 image classifier.
Reads progress from /data/images/ollama_progress.json.
"""
import json
import os
import subprocess
import logging
from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger("recovery")

PROGRESS_FILE = "/data/images/ollama_progress.json"
TOTAL_IMAGES = 18472  # Known total from the Layer 3 scan


@router.get("/recovery/status")
async def recovery_status():
    """Get RecoveryForge classifier status."""
    processed = 0
    categories = {}

    # Read progress
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                data = json.load(f)
            processed_list = data.get("processed", [])
            processed = len(processed_list)
            categories = data.get("categories", {})
        except Exception as e:
            logger.warning(f"Could not read progress file: {e}")

    # Check if classifier process is running
    running = False
    try:
        r = subprocess.run(
            ["pgrep", "-f", "ollama_bulk_classify"],
            capture_output=True, text=True, timeout=5,
        )
        running = r.returncode == 0
    except Exception:
        pass

    percentage = round((processed / TOTAL_IMAGES) * 100, 1) if TOTAL_IMAGES > 0 else 0

    return {
        "total_images": TOTAL_IMAGES,
        "processed": processed,
        "percentage": percentage,
        "running": running,
        "categories": categories,
    }


@router.post("/recovery/start")
async def recovery_start():
    """Start the RecoveryForge classifier (Level 3 — PIN required)."""
    # Check if already running
    try:
        r = subprocess.run(
            ["pgrep", "-f", "ollama_bulk_classify"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return {"started": False, "reason": "Classifier already running", "pid": int(r.stdout.strip().split()[0])}
    except Exception:
        pass

    try:
        venv_python = os.path.expanduser("~/empire-repo/backend/venv/bin/python3")
        proc = subprocess.Popen(
            [venv_python, "-m", "app.services.ollama_bulk_classify"],
            cwd=os.path.expanduser("~/empire-repo/backend"),
            stdout=open("/tmp/recoveryforge-classify.log", "a"),
            stderr=subprocess.STDOUT,
        )
        return {"started": True, "pid": proc.pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recovery/stop")
async def recovery_stop():
    """Stop the RecoveryForge classifier (Level 3 — PIN required)."""
    try:
        r = subprocess.run(
            ["pkill", "-f", "ollama_bulk_classify"],
            capture_output=True, text=True, timeout=5,
        )
        return {"stopped": True, "exit_code": r.returncode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
