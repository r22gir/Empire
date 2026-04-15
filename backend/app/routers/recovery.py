"""
RecoveryForge API — status, start, stop for the Layer 3 image classifier.
Reads progress from /data/images/ollama_progress.json.
"""
import json
import os
import subprocess
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter()
logger = logging.getLogger("recovery")

PROGRESS_FILE = "/data/images/ollama_progress.json"
INDEX_FILE = "/data/images/presorted_inventory.json"
CLASSIFIED_DIR = "/data/images/classified"
TOTAL_IMAGES = 18472  # Known total from the Layer 3 scan


def _load_image_index() -> dict[str, Any]:
    for path in (INDEX_FILE, "/data/images/filtered_inventory.json", "/data/images/inventory.json"):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read image index {path}: {e}")
    return {"images": [], "stats": {}}


def _public_image_item(img: dict[str, Any]) -> dict[str, Any]:
    filename = img.get("filename") or Path(str(img.get("path", ""))).name
    return {
        "filename": filename,
        "path": img.get("path"),
        "classified_path": img.get("classified_path"),
        "business": img.get("business") or img.get("pre_tag") or "unknown",
        "pre_tag": img.get("pre_tag") or "unknown",
        "category": img.get("category") or img.get("pre_category") or "misc",
        "description": img.get("description") or "",
        "quality": img.get("quality") or "",
        "social_ready": bool(img.get("social_ready")),
        "confidence": img.get("confidence"),
        "classified_by": img.get("classified_by") or "none",
        "classified_at": img.get("classified_at"),
        "date_taken": img.get("date_taken"),
        "folder_path": img.get("folder_path"),
        "image_url": f"/api/v1/recovery/image/{filename}" if filename else None,
    }


@router.get("/recovery/status")
async def recovery_status():
    """Get RecoveryForge classifier status."""
    processed = 0
    categories = {}
    stats = {}

    # Read progress
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                data = json.load(f)
            processed_list = data.get("processed", [])
            processed = len(processed_list)
            stats = data.get("stats", {})
            categories = data.get("categories") or {k: v for k, v in stats.items() if k != "processed"}
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
        "stats": stats,
        "index_file": INDEX_FILE,
        "progress_file": PROGRESS_FILE,
        "classified_dir": CLASSIFIED_DIR,
    }


@router.get("/recovery/images")
async def recovery_images(
    business: str | None = None,
    category: str | None = None,
    pre_tag: str | None = None,
    q: str | None = None,
    analyzed_only: bool = True,
    limit: int = Query(default=48, ge=1, le=120),
    offset: int = Query(default=0, ge=0),
):
    """Browse RecoveryForge image index metadata from the loaded recovery router."""
    data = _load_image_index()
    images = data.get("images", [])

    if analyzed_only:
        images = [img for img in images if img.get("description") or img.get("business") or img.get("category")]
    if business:
        images = [img for img in images if (img.get("business") or img.get("pre_tag")) == business]
    if pre_tag:
        images = [img for img in images if img.get("pre_tag") == pre_tag]
    if category:
        images = [img for img in images if (img.get("category") or img.get("pre_category")) == category]
    if q:
        needle = q.lower()
        images = [
            img for img in images
            if needle in " ".join(str(img.get(k, "")) for k in ("filename", "description", "category", "pre_tag", "folder_path")).lower()
        ]

    total = len(images)
    page = images[offset:offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "stats": data.get("stats", {}),
        "facets": {
            "business": dict(Counter((i.get("business") or i.get("pre_tag") or "unknown") for i in images)),
            "category": dict(Counter((i.get("category") or i.get("pre_category") or "misc") for i in images)),
            "classifier": dict(Counter(i.get("classified_by") or "none" for i in images)),
        },
        "images": [_public_image_item(img) for img in page],
    }


@router.get("/recovery/image/{filename}")
async def recovery_image(filename: str):
    """Serve an indexed RecoveryForge image by filename from classified copy or source path."""
    safe_name = Path(filename).name
    data = _load_image_index()
    for img in data.get("images", []):
        if img.get("filename") != safe_name:
            continue
        for key in ("classified_path", "social_path", "path"):
            path = img.get(key)
            if path and os.path.exists(path) and os.path.isfile(path):
                return FileResponse(path)
    raise HTTPException(status_code=404, detail=f"RecoveryForge image not found: {safe_name}")


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
