"""
RecoveryForge API — status, start, stop for the Layer 3 image classifier.
Reads progress from /data/images/ollama_progress.json.
"""
import json
import os
import subprocess
import logging
import hashlib
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("recovery")

PROGRESS_FILE = "/data/images/ollama_progress.json"
INDEX_FILE = "/data/images/presorted_inventory.json"
CLASSIFIED_DIR = "/data/images/classified"
SOCIAL_DIR = "/data/images/social-assets"
TOTAL_IMAGES = 18472  # Known total from the Layer 3 scan


class RecoveryImageReview(BaseModel):
    business: str | None = None
    category: str | None = None
    review_status: str | None = None
    social_ready: bool | None = None
    approve_social: bool = False
    copy_to_classified: bool = False


def _load_image_index() -> dict[str, Any]:
    for path in (INDEX_FILE, "/data/images/filtered_inventory.json", "/data/images/inventory.json"):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read image index {path}: {e}")
    return {"images": [], "stats": {}}


def _save_image_index(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(data, f)


def _record_key(img: dict[str, Any]) -> str:
    raw = "|".join(str(img.get(k, "")) for k in ("path", "filename", "hash"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _public_image_item(img: dict[str, Any]) -> dict[str, Any]:
    filename = img.get("filename") or Path(str(img.get("path", ""))).name
    return {
        "record_key": _record_key(img),
        "filename": filename,
        "path": img.get("path"),
        "classified_path": img.get("classified_path"),
        "social_path": img.get("social_path"),
        "business": img.get("business") or img.get("pre_tag") or "unknown",
        "pre_tag": img.get("pre_tag") or "unknown",
        "category": img.get("category") or img.get("pre_category") or "misc",
        "description": img.get("description") or "",
        "ocr_text": img.get("ocr_text") or img.get("ocr") or img.get("extracted_text") or "",
        "quality": img.get("quality") or "",
        "social_ready": bool(img.get("social_ready")),
        "in_social": bool(img.get("in_social")),
        "reviewed": bool(img.get("reviewed")),
        "review_status": img.get("review_status") or ("reviewed" if img.get("reviewed") else "unreviewed"),
        "confidence": img.get("confidence"),
        "classified_by": img.get("classified_by") or "none",
        "classified_at": img.get("classified_at"),
        "date_taken": img.get("date_taken"),
        "folder_path": img.get("folder_path"),
        "image_url": f"/api/v1/recovery/image/{filename}" if filename else None,
    }


def _find_image(data: dict[str, Any], record_key: str) -> dict[str, Any] | None:
    for img in data.get("images", []):
        if _record_key(img) == record_key or img.get("filename") == record_key:
            return img
    return None


def _copy_to_classified(img: dict[str, Any]) -> str | None:
    business = img.get("business") or img.get("pre_tag") or "general"
    category = img.get("category") or img.get("pre_category") or "misc"
    if business in {"ambiguous", "personal"}:
        return None
    source = img.get("classified_path") or img.get("path")
    if not source or not os.path.exists(source):
        return None
    dest_dir = os.path.join(CLASSIFIED_DIR, business, category or "misc")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, img.get("filename") or Path(source).name)
    if os.path.abspath(source) != os.path.abspath(dest):
        shutil.copy2(source, dest)
    img["classified_path"] = dest
    return dest


def _copy_to_social(img: dict[str, Any]) -> str | None:
    business = img.get("business") or img.get("pre_tag") or "general"
    category = img.get("category") or img.get("pre_category") or "misc"
    if business in {"ambiguous", "personal"}:
        return None
    source = img.get("classified_path") or img.get("path")
    if not source or not os.path.exists(source):
        return None
    dest_dir = os.path.join(SOCIAL_DIR, business, category or "misc")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, img.get("filename") or Path(source).name)
    if os.path.abspath(source) != os.path.abspath(dest):
        shutil.copy2(source, dest)
    img["in_social"] = True
    img["social_path"] = dest
    img["reviewed"] = True
    img["review_status"] = "approved"
    return dest


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
    status: str | None = None,
    social_ready: bool | None = None,
    min_confidence: float | None = None,
    sort: str = "classified_at_desc",
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
    if status == "ambiguous":
        images = [img for img in images if img.get("pre_tag") == "ambiguous"]
    elif status == "personal":
        images = [img for img in images if img.get("pre_tag") == "personal" or img.get("business") == "personal"]
    elif status == "reviewed":
        images = [img for img in images if img.get("reviewed")]
    elif status == "unreviewed":
        images = [img for img in images if not img.get("reviewed")]
    elif status == "low_confidence":
        images = [img for img in images if float(img.get("confidence") or 0) < 0.6]
    if social_ready is not None:
        images = [img for img in images if bool(img.get("social_ready")) is social_ready]
    if min_confidence is not None:
        images = [img for img in images if float(img.get("confidence") or 0) >= min_confidence]
    if q:
        needle = q.lower()
        images = [
            img for img in images
            if needle in " ".join(str(img.get(k, "")) for k in ("filename", "description", "category", "pre_tag", "folder_path")).lower()
        ]

    if sort == "confidence_asc":
        images.sort(key=lambda img: float(img.get("confidence") or 0))
    elif sort == "confidence_desc":
        images.sort(key=lambda img: float(img.get("confidence") or 0), reverse=True)
    elif sort == "filename_asc":
        images.sort(key=lambda img: str(img.get("filename") or "").lower())
    else:
        images.sort(key=lambda img: str(img.get("classified_at") or img.get("date_taken") or ""), reverse=True)

    total = len(images)
    page = images[offset:offset + limit]
    all_images = data.get("images", [])
    analyzed = [img for img in all_images if img.get("description") or img.get("business") or img.get("category")]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "stats": data.get("stats", {}),
        "completeness": {
            "total_indexed": len(all_images),
            "analyzed": len(analyzed),
            "remaining": max(0, len(all_images) - len(analyzed)),
            "low_confidence": sum(1 for img in analyzed if float(img.get("confidence") or 0) < 0.6),
            "ambiguous": sum(1 for img in all_images if img.get("pre_tag") == "ambiguous"),
            "personal": sum(1 for img in all_images if img.get("pre_tag") == "personal" or img.get("business") == "personal"),
            "social_ready": sum(1 for img in analyzed if img.get("social_ready")),
            "reviewed": sum(1 for img in all_images if img.get("reviewed")),
        },
        "facets": {
            "business": dict(Counter((i.get("business") or i.get("pre_tag") or "unknown") for i in images)),
            "category": dict(Counter((i.get("category") or i.get("pre_category") or "misc") for i in images)),
            "classifier": dict(Counter(i.get("classified_by") or "none" for i in images)),
        },
        "images": [_public_image_item(img) for img in page],
    }


@router.get("/recovery/images/{record_key}")
async def recovery_image_detail(record_key: str):
    """Return a single RecoveryForge image record with raw metadata."""
    data = _load_image_index()
    img = _find_image(data, record_key)
    if not img:
        raise HTTPException(status_code=404, detail=f"RecoveryForge image record not found: {record_key}")
    return {
        "image": _public_image_item(img),
        "raw_metadata": img,
        "tags": {
            "business": img.get("business") or img.get("pre_tag"),
            "pre_tag": img.get("pre_tag"),
            "category": img.get("category") or img.get("pre_category"),
            "pre_category": img.get("pre_category"),
            "quality": img.get("quality"),
            "social_ready": img.get("social_ready"),
            "reviewed": img.get("reviewed"),
            "review_status": img.get("review_status"),
        },
        "ocr_text": img.get("ocr_text") or img.get("ocr") or img.get("extracted_text") or "",
    }


@router.patch("/recovery/images/{record_key}")
async def recovery_review_image(record_key: str, review: RecoveryImageReview):
    """Review or reclassify one RecoveryForge image record in the JSON index."""
    data = _load_image_index()
    img = _find_image(data, record_key)
    if not img:
        raise HTTPException(status_code=404, detail=f"RecoveryForge image record not found: {record_key}")

    if review.business:
        img["business"] = review.business
        img["pre_tag"] = review.business
    if review.category:
        img["category"] = review.category
        img["pre_category"] = review.category
    if review.social_ready is not None:
        img["social_ready"] = review.social_ready
    if review.review_status:
        img["review_status"] = review.review_status
        img["reviewed"] = review.review_status in {"approved", "rejected", "reviewed"}

    classified_path = _copy_to_classified(img) if review.copy_to_classified else img.get("classified_path")
    social_path = _copy_to_social(img) if review.approve_social else img.get("social_path")
    _save_image_index(data)

    return {
        "status": "updated",
        "image": _public_image_item(img),
        "classified_path": classified_path,
        "social_path": social_path,
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
