"""
RecoveryForge API — status, start, stop, and MiniMax-powered image analysis.
Reads progress from /data/images/ollama_progress.json.
"""
import json
import os
import subprocess
import logging
import hashlib
import shutil
import asyncio
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import re
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.max.recoveryforge_quota import check_quota, consume_quota, quota_allow_new
from app.services.max.recoveryforge_analyzer import analyze_image

logger = logging.getLogger("recovery")

router = APIRouter()

PROGRESS_FILE = "/data/images/ollama_progress.json"
INDEX_FILE = "/data/images/presorted_inventory.json"
CLASSIFIED_DIR = "/data/images/classified"
SOCIAL_DIR = "/data/images/social-assets"
TOTAL_IMAGES = 18472  # Known total from the Layer 3 scan

CATEGORIES_FILE = "/data/images/recovery_categories.json"

BUILTIN_BUSINESSES = ["empire-workroom", "woodcraft", "general", "personal", "ambiguous", "unknown"]
BUILTIN_CATEGORIES = ["misc", "raw-materials", "finished-products", "tools", "workspace", "inspiration", "reference"]


class CategoryEntry(BaseModel):
    slug: str
    label: str
    kind: str = "category"  # "category" or "business"
    source: str = "custom"  # "builtin" or "custom"
    created_at: str | None = None


class CategoryCreate(BaseModel):
    label: str
    kind: str = "category"


def _load_categories() -> dict[str, Any]:
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"custom_categories": [], "custom_businesses": []}


def _save_categories(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CATEGORIES_FILE), exist_ok=True)
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(data, f)


def _slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9\-]", "-", label.lower()).strip("-")


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip())


class RecoveryImageReview(BaseModel):
    business: str | None = None
    category: str | None = None
    review_status: str | None = None
    social_ready: bool | None = None
    approve_social: bool = False
    copy_to_classified: bool = False


class RecoveryImageReanalyzeRequest(BaseModel):
    force: bool = True


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


def _path_readable(path: str | None) -> bool:
    if not path:
        return False
    try:
        p = Path(path)
        return p.exists() and p.is_file() and os.access(p, os.R_OK)
    except (OSError, TypeError, ValueError):
        return False


def _path_status(path: str | None) -> dict[str, Any]:
    if not path:
        return {"path": None, "exists": False, "readable": False, "is_file": False, "size_bytes": None}
    try:
        p = Path(path)
        exists = p.exists()
        is_file = p.is_file() if exists else False
        readable = bool(is_file and os.access(p, os.R_OK))
        size = p.stat().st_size if is_file else None
        return {
            "path": str(path),
            "exists": exists,
            "readable": readable,
            "is_file": is_file,
            "size_bytes": size,
        }
    except (OSError, TypeError, ValueError) as exc:
        return {
            "path": str(path),
            "exists": False,
            "readable": False,
            "is_file": False,
            "size_bytes": None,
            "error": str(exc),
        }


def _image_path_status(img: dict[str, Any]) -> dict[str, Any]:
    source_path = img.get("source_path") or img.get("path")
    return {
        "source": _path_status(source_path),
        "classified": _path_status(img.get("classified_path")),
        "social": _path_status(img.get("social_path")),
    }


def _resolve_reanalysis_path(img: dict[str, Any]) -> tuple[str | None, str | None, dict[str, Any]]:
    path_status = _image_path_status(img)
    candidates = (
        ("source_path", img.get("source_path") or img.get("path")),
        ("classified_path", img.get("classified_path")),
        ("social_path", img.get("social_path")),
    )
    for source_key, candidate in candidates:
        if _path_readable(candidate):
            return str(Path(candidate).resolve()), source_key, path_status
    return None, None, path_status


def _last_analysis_error(img: dict[str, Any]) -> str | None:
    analysis = img.get("minimax_analysis") or {}
    if analysis.get("analysis_status") == "failed" and analysis.get("error"):
        return str(analysis.get("error"))
    for key in ("last_error", "analysis_error", "error"):
        if img.get(key):
            return str(img.get(key))
    description = str(img.get("description") or "")
    if description.lower().startswith("ollama error:"):
        return description
    return None


def _public_image_item(img: dict[str, Any]) -> dict[str, Any]:
    filename = img.get("filename") or Path(str(img.get("path", ""))).name
    source_path = img.get("source_path") or img.get("path")
    path_status = _image_path_status(img)
    return {
        "record_key": _record_key(img),
        "filename": filename,
        "path": source_path,
        "source_path": source_path,
        "source_exists": path_status["source"]["exists"],
        "source_readable": path_status["source"]["readable"],
        "classified_path": img.get("classified_path"),
        "classified_exists": path_status["classified"]["exists"],
        "classified_readable": path_status["classified"]["readable"],
        "social_path": img.get("social_path"),
        "social_exists": path_status["social"]["exists"],
        "business": img.get("business") or img.get("pre_tag") or "unknown",
        "pre_tag": img.get("pre_tag") or "unknown",
        "category": img.get("category") or img.get("pre_category") or "misc",
        "description": img.get("description") or img.get("generated_description") or "",
        "generated_description": img.get("generated_description") or img.get("description") or "",
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
        "minimax_analysis": img.get("minimax_analysis") or None,
        "analysis_stale": bool(img.get("minimax_analysis", {}).get("stale", False)),
        "analysis_provider": img.get("minimax_analysis", {}).get("provider") or img.get("classified_by") or None,
        "analysis_confidence": img.get("minimax_analysis", {}).get("analysis_confidence") or img.get("confidence"),
        "needs_manual_review": bool(img.get("minimax_analysis", {}).get("needs_manual_review", False)),
        "analyzed_at": img.get("analyzed_at") or img.get("minimax_analysis", {}).get("timestamp") or img.get("classified_at"),
        "last_error": _last_analysis_error(img),
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


def _apply_minimax_analysis(img: dict[str, Any], result: dict[str, Any], analyzed_path: str) -> None:
    img["minimax_analysis"] = result
    img["analyzed_at"] = result.get("timestamp") or datetime.now(timezone.utc).isoformat()
    img["last_analyzed_path"] = analyzed_path

    if result.get("analysis_status") != "success":
        img["analysis_error"] = result.get("error") or "MiniMax mmx vision analysis failed"
        return

    description = result.get("description")
    if description:
        img["description"] = description
        img["generated_description"] = description

    route = result.get("business_route")
    if route and route not in {"unknown-work", "general-business"}:
        img["business"] = route
        img["pre_tag"] = route

    confidence = result.get("analysis_confidence")
    if confidence is not None:
        img["confidence"] = confidence

    img["classified_by"] = "minimax-mmx_vision"
    img["classified_at"] = img["analyzed_at"]
    for key in ("error", "last_error", "analysis_error"):
        img.pop(key, None)


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
        "minimax_quota": check_quota(),
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
        "minimax_analysis": img.get("minimax_analysis") or None,
        "path_status": _image_path_status(img),
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
        "path_status": _image_path_status(img),
        "classified_path": classified_path,
        "social_path": social_path,
    }


@router.post("/recovery/images/{record_key}/reanalyze")
async def recovery_reanalyze_image(record_key: str, request: RecoveryImageReanalyzeRequest | None = None):
    """Re-run MiniMax/mmx vision analysis for exactly one selected RecoveryForge image."""
    data = _load_image_index()
    img = _find_image(data, record_key)
    if not img:
        raise HTTPException(status_code=404, detail=f"RecoveryForge image record not found: {record_key}")

    force = True if request is None else request.force
    existing = img.get("minimax_analysis") or {}
    if not force and existing.get("analysis_status") == "success" and not existing.get("stale"):
        return {
            "status": "existing",
            "success": True,
            "image": _public_image_item(img),
            "analysis": existing,
            "path_status": _image_path_status(img),
        }

    path, path_source, path_status = _resolve_reanalysis_path(img)
    if not path:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "No readable RecoveryForge image file found for selected record",
                "record_key": record_key,
                "path_status": path_status,
            },
        )

    if not quota_allow_new():
        quota = check_quota()
        return {
            "status": "cap_reached",
            "success": False,
            "message": (
                f"RecoveryForge MCP Understand Image cap reached. "
                f"Resets at {quota['reset_window_hint']}."
            ),
            "quota": quota,
            "image": _public_image_item(img),
            "path_source": path_source,
            "path_status": path_status,
        }

    result = await analyze_image(record_key, path)
    _apply_minimax_analysis(img, result, path)
    _save_image_index(data)

    return {
        "status": "reanalyzed" if result.get("analysis_status") == "success" else "analysis_failed",
        "success": result.get("analysis_status") == "success",
        "image": _public_image_item(img),
        "analysis": result,
        "path_source": path_source,
        "analyzed_path": path,
        "path_status": _image_path_status(img),
    }


@router.get("/recovery/images/{record_key}/file")
async def recovery_image_file(record_key: str, variant: str = Query(default="source", pattern="^(source|classified|social)$")):
    """Serve the selected RecoveryForge image file variant when the stored path exists."""
    data = _load_image_index()
    img = _find_image(data, record_key)
    if not img:
        raise HTTPException(status_code=404, detail=f"RecoveryForge image record not found: {record_key}")

    variant_path = {
        "source": img.get("source_path") or img.get("path"),
        "classified": img.get("classified_path"),
        "social": img.get("social_path"),
    }.get(variant)

    if not _path_readable(variant_path):
        raise HTTPException(status_code=404, detail=f"RecoveryForge {variant} file not found for {record_key}")

    return FileResponse(str(Path(variant_path).resolve()))


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


# ── RecoveryForge MiniMax Analysis ────────────────────────────────────────────

class AnalyzeImageRequest(BaseModel):
    image_key: str
    restart_analysis: bool = False


class BatchAnalyzeRequest(BaseModel):
    image_keys: list[str]
    restart_stale: bool = False


@router.get("/recovery/quota-status")
async def recovery_quota_status():
    """
    Returns RecoveryForge quota status:
    - daily_cap: 80
    - daily_reserved_quota: 20
    - used_today
    - remaining_recoveryforge_today
    - cap_reached
    - override_active
    - reset_date
    """
    return check_quota()


@router.post("/recovery/analyze")
async def recovery_analyze_single(image_key: str, restart_analysis: bool = False):
    """
    Analyze a single image using MiniMax vision.

    If restart_analysis=False and the image already has a MiniMax analysis
    that is not stale, returns the existing result.
    If restart_analysis=True, marks prior analysis stale and re-runs.
    """
    data = _load_image_index()
    img = _find_image(data, image_key)

    if not img:
        raise HTTPException(status_code=404, detail=f"Image not found: {image_key}")

    existing = img.get("minimax_analysis") or {}
    if not restart_analysis and existing.get("analysis_status") == "success" and not existing.get("stale"):
        return {"status": "existing", "analysis": existing}

    if not quota_allow_new():
        quota = check_quota()
        return {
            "status": "cap_reached",
            "message": f"RecoveryForge daily cap reached. {quota['daily_reserved_quota']} images reserved. Resets at {quota['reset_date']}.",
            "quota": quota,
        }

    path = img.get("classified_path") or img.get("path", "")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"Image file not found for {image_key}")

    if restart_analysis and existing.get("analysis_status") == "success":
        existing["stale"] = True
        existing["superseded_at"] = datetime.now(timezone.utc).isoformat()
        img["minimax_analysis"] = existing
        _save_image_index(data)

    result = await analyze_image(image_key, path)
    img["minimax_analysis"] = result
    _save_image_index(data)

    return {"status": "analyzed", "analysis": result}


@router.post("/recovery/batch-analyze")
async def recovery_batch_analyze(image_keys: list[str], restart_stale: bool = False):
    """
    Batch analyze multiple images via MiniMax vision.
    Respects the 80/day RecoveryForge cap and leaves 20 reserved.
    """
    quota_status = check_quota()
    available = quota_status["remaining_recoveryforge_today"]

    if not restart_stale and not quota_allow_new():
        return {
            "status": "cap_reached_before_start",
            "started": 0,
            "skipped": len(image_keys),
            "quota": quota_status,
        }

    data = _load_image_index()
    started = 0
    skipped = 0
    results = []

    for key in image_keys:
        img = _find_image(data, key)
        if not img:
            skipped += 1
            continue

        existing = img.get("minimax_analysis") or {}
        if not restart_stale and existing.get("analysis_status") == "success" and not existing.get("stale"):
            skipped += 1
            results.append({"image_key": key, "status": "existing"})
            continue

        if started >= available and not os.environ.get("RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE", "").strip() == "1":
            skipped += 1
            results.append({"image_key": key, "status": "cap_reached"})
            continue

        if restart_stale and existing.get("analysis_status") == "success":
            existing["stale"] = True
            existing["superseded_at"] = datetime.now(timezone.utc).isoformat()
            img["minimax_analysis"] = existing

        path = img.get("classified_path") or img.get("path", "")
        if not path or not os.path.exists(path):
            skipped += 1
            results.append({"image_key": key, "status": "file_not_found"})
            continue

        result = await analyze_image(key, path)
        img["minimax_analysis"] = result
        started += 1
        results.append({"image_key": key, "status": result["analysis_status"], "result": result})

    _save_image_index(data)

    return {
        "started": started,
        "skipped": skipped,
        "quota": check_quota(),
        "results": results,
    }


@router.post("/recovery/mark-stale")
async def recovery_mark_stale(image_keys: list[str]):
    """
    Mark prior Ollama/MiniMax analysis as stale/superseded for re-analysis.
    Does NOT delete original files. Only marks the analysis record.
    """
    data = _load_image_index()
    marked = 0
    for key in image_keys:
        img = _find_image(data, key)
        if not img:
            continue
        analysis = img.get("minimax_analysis") or img.get("analysis") or {}
        if analysis.get("analysis_status") == "success":
            analysis["stale"] = True
            analysis["superseded_at"] = datetime.now(timezone.utc).isoformat()
            img["minimax_analysis"] = analysis
            marked += 1
    _save_image_index(data)
    return {"marked_stale": marked, "total_requested": len(image_keys)}


@router.post("/recovery/clear-stale")
async def recovery_clear_stale(image_keys: list[str]):
    """
    Clear stale analysis flags from image records.
    """
    data = _load_image_index()
    cleared = 0
    for key in image_keys:
        img = _find_image(data, key)
        if not img:
            continue
        analysis = img.get("minimax_analysis") or {}
        if analysis.get("stale"):
            analysis["stale"] = False
            img["minimax_analysis"] = analysis
            cleared += 1
    _save_image_index(data)
    return {"cleared_stale": cleared, "total_requested": len(image_keys)}


@router.get("/recovery/categories")
async def recovery_list_categories(kind: str | None = None):
    """
    List all categories and businesses (builtin + custom).
    Optionally filter by kind: 'category' or 'business'.
    """
    data = _load_categories()
    now = datetime.now(timezone.utc).isoformat()

    result = []

    if not kind or kind == "category":
        for slug in sorted(BUILTIN_CATEGORIES):
            result.append({"slug": slug, "label": slug, "kind": "category", "source": "builtin", "created_at": None, "usage_count": 0})
        for entry in data.get("custom_categories", []):
            result.append({**entry, "source": "custom", "created_at": entry.get("created_at") or now})

    if not kind or kind == "business":
        for slug in sorted(BUILTIN_BUSINESSES):
            result.append({"slug": slug, "label": slug, "kind": "business", "source": "builtin", "created_at": None, "usage_count": 0})
        for entry in data.get("custom_businesses", []):
            result.append({**entry, "source": "custom", "created_at": entry.get("created_at") or now})

    def sort_key(item):
        source_order = 0 if item["source"] == "builtin" else 1
        return (source_order, item["label"].lower())
    result.sort(key=sort_key)

    return {"categories": result}


@router.post("/recovery/categories")
async def recovery_create_category(create: CategoryCreate):
    """
    Add a custom category or business.
    Rejects duplicates (case-insensitive) and empty/dangerous values.
    """
    label = _normalize_label(create.label)
    if not label:
        raise HTTPException(status_code=400, detail="Label cannot be empty")
    if len(label) > 80:
        raise HTTPException(status_code=400, detail="Label too long (max 80 chars)")

    slug = _slugify(label)
    if not slug:
        raise HTTPException(status_code=400, detail="Label must contain alphanumeric characters")
    if slug in BUILTIN_CATEGORIES or slug in BUILTIN_BUSINESSES:
        raise HTTPException(status_code=409, detail=f"'{label}' is a builtin and cannot be recreated")

    kind = create.kind or "category"
    if kind not in ("category", "business"):
        raise HTTPException(status_code=400, detail="kind must be 'category' or 'business'")

    data = _load_categories()
    collection = "custom_categories" if kind == "category" else "custom_businesses"

    # Case-insensitive duplicate check
    for entry in data.get(collection, []):
        if entry["label"].lower() == label.lower():
            raise HTTPException(status_code=409, detail=f"'{label}' already exists as a {kind}")

    now = datetime.now(timezone.utc).isoformat()
    entry = {"slug": slug, "label": label, "kind": kind, "source": "custom", "created_at": now}
    data.setdefault(collection, []).append(entry)
    _save_categories(data)

    return {"status": "created", "entry": entry}


@router.delete("/recovery/categories/{slug}")
async def recovery_delete_category(slug: str):
    """
    Delete a custom category or business by slug.
    Only custom (non-builtin) entries can be deleted.
    """
    if slug in BUILTIN_CATEGORIES or slug in BUILTIN_BUSINESSES:
        raise HTTPException(status_code=403, detail="Cannot delete builtin entries")

    data = _load_categories()
    for collection in ("custom_categories", "custom_businesses"):
        original = len(data.get(collection, []))
        data[collection] = [e for e in data.get(collection, []) if e["slug"] != slug]
        if len(data[collection]) < original:
            _save_categories(data)
            return {"status": "deleted", "slug": slug}

    raise HTTPException(status_code=404, detail=f"Category '{slug}' not found")
