from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
import os
import json
import shutil
from collections import Counter

router = APIRouter(prefix="/api/v1/recovery-forge", tags=["RecoveryForge"])

INDEX_FILE = "/data/images/presorted_inventory.json"
SOCIAL_DIR = "/data/images/social-assets"
CLASSIFIED_DIR = "/data/images/classified"


def _load_index():
    for f in [INDEX_FILE, "/data/images/filtered_inventory.json", "/data/images/inventory.json"]:
        if os.path.exists(f):
            with open(f, "r") as fh:
                return json.load(fh)
    return {"images": [], "stats": {}}


def _save_index(data):
    with open(INDEX_FILE, "w") as f:
        json.dump(data, f)


@router.get("/index")
async def get_image_index(
    business: str = None,
    category: str = None,
    reviewed: bool = None,
    in_social: bool = None,
    min_confidence: float = None,
    pre_tag: str = None
):
    data = _load_index()
    images = data.get("images", [])
    if business:
        images = [i for i in images if i.get("business") == business or i.get("pre_tag") == business]
    if category:
        images = [i for i in images if i.get("category") == category or i.get("pre_category") == category]
    if reviewed is not None:
        images = [i for i in images if i.get("reviewed") == reviewed]
    if in_social is not None:
        images = [i for i in images if i.get("in_social") == in_social]
    if min_confidence is not None:
        images = [i for i in images if i.get("confidence", 0) >= min_confidence]
    if pre_tag:
        images = [i for i in images if i.get("pre_tag") == pre_tag]
    return {"total": len(images), "images": images, "stats": data.get("stats", {})}


@router.get("/image/{filename}")
async def serve_image(filename: str):
    data = _load_index()
    for img in data.get("images", []):
        if img.get("filename") == filename:
            for key in ("classified_path", "social_path", "path"):
                p = img.get(key)
                if p and os.path.exists(p):
                    return FileResponse(p)
    return {"error": "Image not found"}


@router.post("/review/{filename}")
async def review_image(filename: str, business: str = None, category: str = None, approve_social: bool = False):
    data = _load_index()
    for img in data.get("images", []):
        if img.get("filename") == filename:
            if business:
                img["business"] = business
                img["pre_tag"] = business
            if category:
                img["category"] = category
                img["pre_category"] = category
            img["reviewed"] = True
            _save_index(data)
            if approve_social:
                return _move_to_social(img, data)
            return {"status": "reviewed", "filename": filename}
    return {"status": "not_found"}


@router.post("/move-to-social/{filename}")
async def move_image_to_social(filename: str):
    data = _load_index()
    for img in data.get("images", []):
        if img.get("filename") == filename:
            return _move_to_social(img, data)
    return {"status": "not_found"}


def _move_to_social(img, data):
    if img.get("in_social"):
        return {"status": "already_in_social", "filename": img.get("filename")}
    biz = img.get("business") or img.get("pre_tag", "general")
    cat = img.get("category") or img.get("pre_category", "misc")
    if biz in ("personal", "ambiguous"):
        return {"status": "error", "message": f"Cannot move {biz} images to social."}
    source = img.get("classified_path") or img.get("path")
    dest_dir = os.path.join(SOCIAL_DIR, biz, cat)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, img.get("filename", "unknown"))
    if source and os.path.exists(source) and not os.path.exists(dest):
        shutil.copy2(source, dest)
    img["in_social"] = True
    img["social_path"] = dest
    img["reviewed"] = True
    _save_index(data)
    return {"status": "moved", "filename": img.get("filename"), "social_path": dest}


@router.get("/social-assets")
async def list_social_assets(business: str = None, category: str = None, limit: int = Query(default=10, le=50)):
    data = _load_index()
    results = [img for img in data.get("images", []) if img.get("in_social")]
    if business:
        results = [i for i in results if (i.get("business") or i.get("pre_tag")) == business]
    if category:
        results = [i for i in results if (i.get("category") or i.get("pre_category")) == category]
    return {"total": len(results), "images": results[:limit]}


@router.get("/stats")
async def get_stats():
    data = _load_index()
    images = data.get("images", [])
    return {
        "total": len(images),
        "by_tag": dict(Counter(i.get("pre_tag", "unknown") for i in images)),
        "by_classifier": dict(Counter(i.get("classified_by", "none") for i in images)),
        "reviewed": sum(1 for i in images if i.get("reviewed")),
        "in_social": sum(1 for i in images if i.get("in_social")),
        "ambiguous": sum(1 for i in images if i.get("pre_tag") == "ambiguous"),
    }


@router.post("/scan")
async def trigger_scan():
    """Trigger a new inventory scan (Layer 1). Returns immediately, scan runs in background."""
    import subprocess
    proc = subprocess.Popen(
        ["python3", "/home/rg/empire-repo/backend/app/services/image_inventory.py"],
        stdout=open("/data/images/inventory_scan.log", "w"),
        stderr=subprocess.STDOUT,
        cwd="/home/rg/empire-repo"
    )
    return {"status": "scan_started", "pid": proc.pid, "log": "/data/images/inventory_scan.log"}
