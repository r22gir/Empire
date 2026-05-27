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

# ── Asset Intelligence Tag Dictionary ───────────────────────────────────────

TAG_DICTIONARY: dict[str, str] = {
    # Objects — furniture
    "chair": "object", "furniture": "object", "sofa": "object", "couch": "object",
    "bench": "object", "cushion": "object", "pillow": "object", "table": "object",
    "desk": "object", "cabinet": "object", "shelf": "object", "shelves": "object",
    "frame": "object", "mirror": "object", "lamp": "object", "lighting": "object",
    "bed": "object", "mattress": "object", "dining-table": "object",
    # Objects — window treatments (workroom core domain)
    "drapery": "object", "draperies": "object", "curtain": "object", "curtains": "object",
    "blind": "object", "blinds": "object", "shade": "object", "shades": "object",
    "window-treatment": "object", "valance": "object", "cornice": "object",
    "roman-shade": "object", "cellular-shade": "object", "roller-shade": "object",
    "upholstery": "object", "fabric": "object", "sheer": "object",
    "curtain-rod": "object", "curtain-track": "object", "bracket": "object",
    # Materials
    "wood": "material", "oak": "material", "pine": "material", "walnut": "material",
    "plywood": "material", "mdf": "material", "veneer": "material",
    "metal": "material", "steel": "material", "aluminum": "material",
    "glass": "material", "mirror": "material", "acrylic": "material",
    "leather": "material", "fabric": "material", "velvet": "material",
    "linen": "material", "cotton": "material", "silk": "material",
    "ceramic": "material", "tile": "material", "marble": "material",
    "granite": "material", "stone": "material", "concrete": "material",
    "bamboo": "material", "rattan": "material", "wicker": "material",
    # Rooms
    "living-room": "room", "living room": "room", "bedroom": "room",
    "kitchen": "room", "bathroom": "room", "office": "room", "workshop": "room",
    "workroom": "room", "dining-room": "room", "dining room": "room",
    "garage": "room", "basement": "room", "nursery": "room", "studio": "room",
    "garden": "room", "patio": "room", "balcony": "room", "exterior": "room",
    # People
    "person": "people", "people": "people", "man": "people", "woman": "people",
    "male": "people", "female": "people", "child": "people", "group": "people",
    "professional": "people", "designer": "people", "couple": "people",
    "family": "people", "portrait": "people",
    # Pets
    "dog": "pet", "puppy": "pet", "cat": "pet", "kitten": "pet",
    "bird": "pet", "fish": "pet", "pet": "pet",
    # Styles
    "modern": "style", "contemporary": "style", "traditional": "style",
    "classic": "style", "vintage": "style", "antique": "style", "retro": "style",
    "minimalist": "style", "minimal": "style", "scandinavian": "style",
    "industrial": "style", "rustic": "style", "farmhouse": "style",
    "bohemian": "style", "boho": "style", "coastal": "style", "beach": "style",
    "mid-century": "style", "art-deco": "style",
    # Campaigns
    "website-gallery": "campaign", "social-ad": "campaign", "social-media": "campaign",
    "facebook": "campaign", "instagram": "campaign", "pinterest": "campaign",
    "product-listing": "campaign", "lookbook": "campaign", "catalog": "campaign",
    "hero-image": "campaign", "banner": "campaign", "before-after": "campaign",
}


def _slugify_tag(value: str) -> str:
    """Normalize a tag value to a safe lowercase slug."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", value.lower())).strip("-")


def _extract_asset_tags(text: str) -> dict[str, list[str]]:
    """
    Deterministically extract asset intelligence tags from description text.
    No AI call — uses substring word-in-dictionary lookup.
    """
    lower = text.lower()
    found: dict[str, set[str]] = {
        "object_tags": set(),
        "room_tags": set(),
        "material_tags": set(),
        "style_tags": set(),
        "people_tags": set(),
        "pet_tags": set(),
        "campaign_tags": set(),
        "business_domains": set(),
        "asset_tags": set(),
    }
    for term, kind in TAG_DICTIONARY.items():
        if term in lower:
            cat = f"{kind}_tags" if kind != "business_domain" else "business_domains"
            if cat in found:
                found[cat].add(term)

    # Post-process: drapery/curtain/blind/shade → window-treatment
    if found["object_tags"] & {"drapery", "draperies", "curtain", "curtains", "blind", "blinds", "shade", "shades"}:
        found["object_tags"].add("window-treatment")

    # Post-process: infer business domains
    workroom_terms = {"drapery", "draperies", "curtain", "curtains", "blind", "blinds", "shade", "shades", "window-treatment", "upholstery", "fabric", "sheer", "valance", "cornice", "roman-shade", "cellular-shade", "roller-shade", "curtain-rod", "curtain-track", "bracket", "cushion", "pillow"}
    woodcraft_terms = {"wood", "oak", "pine", "walnut", "plywood", "mdf", "veneer", "cabinet", "shelf", "shelves", "table", "desk", "frame", "rattan", "wicker", "bamboo"}
    if found["object_tags"] & workroom_terms:
        found["business_domains"].add("empire-workroom")
    if found["object_tags"] & woodcraft_terms:
        found["business_domains"].add("woodcraft")
    if found["campaign_tags"]:
        found["business_domains"].add("socialforge")

    return {cat: sorted(s) for cat, s in found.items()}


def _apply_asset_tags(img: dict[str, Any], text: str) -> None:
    """Extract and apply asset tag arrays to an image record."""
    tags = _extract_asset_tags(text)
    for cat, tag_list in tags.items():
        img[cat] = tag_list
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


def _is_persisted_analyzed(img: dict[str, Any]) -> bool:
    """Return True if this record has persisted analysis content from a successful vision run.

    Counts only real analysis products — not memory-only progress, not stale counters,
    not records with only tag arrays and no description, not pure Ollama errors.
    """
    analysis = img.get("minimax_analysis") or {}
    analysis_status = ""
    if isinstance(analysis, dict):
        analysis_status = str(analysis.get("analysis_status") or analysis.get("status") or "").lower()
    analysis_succeeded = analysis_status in {"success", "succeeded", "complete", "completed", "ok"}

    # Has real MiniMax description text (more than placeholder length)
    desc = img.get("description") or img.get("generated_description") or ""
    desc_is_error = str(desc).lower().startswith("ollama error:")
    has_description = bool(desc and len(desc) > 50 and not desc_is_error)

    # Has successful MiniMax analysis result block
    has_minimax = bool(isinstance(analysis, dict) and analysis and analysis_succeeded and not analysis.get("error"))

    # Has explicit analyzed_at timestamp tied to real analysis content
    has_analyzed_at = bool(img.get("analyzed_at") and (has_description or has_minimax))

    # Has confidence from successful classification
    conf = img.get("confidence")
    has_confidence = conf is not None and float(conf) > 0

    # Classified by MiniMax (not "none", not memory-only)
    classified = img.get("classified_by", "none")
    has_classified = classified and classified not in ("none", "")

    return has_description or has_minimax or has_analyzed_at or (has_confidence and has_classified)


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


class RecoveryImageScrapRequest(BaseModel):
    mode: str = "soft_delete"  # "soft_delete" | "delete_classified" | "delete_all_copies"
    delete_source: bool = False
    reason: str = "unrelated"
    confirm: bool = False
    confirm_text: str = ""


# Valid tag array field names
TAG_ARRAY_FIELDS: set[str] = {
    "object_tags", "room_tags", "material_tags", "style_tags",
    "people_tags", "pet_tags", "campaign_tags", "business_domains", "asset_tags",
}

# Tags that are never allowed as manual edits (too broad / meaningless)
TAG_BLOCKLIST: set[str] = {
    "none", "unknown", "misc", "other", "undefined", "n/a", "-",
}


class RecoveryImageTagsUpdate(BaseModel):
    """Manual tag edit for one image record. All fields optional — only supplied fields are updated."""
    object_tags: list[str] | None = None
    room_tags: list[str] | None = None
    material_tags: list[str] | None = None
    style_tags: list[str] | None = None
    people_tags: list[str] | None = None
    pet_tags: list[str] | None = None
    campaign_tags: list[str] | None = None
    business_domains: list[str] | None = None
    asset_tags: list[str] | None = None


def _safe_trash_path(path: str | None) -> str | None:
    """Compute a trash path for a given file path, under /data/images/trash/recoveryforge/."""
    if not path or not os.path.exists(path):
        return None
    try:
        p = Path(path).resolve()
        base = Path("/data/images/trash/recoveryforge")
        base.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        trash_name = f"{ts}_{p.name}"
        return str(base / trash_name)
    except Exception:
        return None


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


def _count_persisted_analyzed(data: dict[str, Any]) -> int:
    return sum(1 for img in data.get("images", []) if _is_persisted_analyzed(img))


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
        "object_tags": img.get("object_tags", []),
        "room_tags": img.get("room_tags", []),
        "material_tags": img.get("material_tags", []),
        "style_tags": img.get("style_tags", []),
        "people_tags": img.get("people_tags", []),
        "pet_tags": img.get("pet_tags", []),
        "campaign_tags": img.get("campaign_tags", []),
        "business_domains": img.get("business_domains", []),
        "asset_tags": img.get("asset_tags", []),
        "tags_manually_edited": bool(img.get("tags_manually_edited")),
        "tags_updated_at": img.get("tags_updated_at"),
        "tags_updated_by": img.get("tags_updated_by"),
    }


def _find_image(data: dict[str, Any], record_key: str) -> dict[str, Any] | None:
    for img in data.get("images", []):
        if _record_key(img) == record_key or img.get("filename") == record_key:
            return img
    return None


def _has_durable_analysis_truth(img: dict[str, Any] | None) -> bool:
    if not img:
        return False
    analysis = img.get("minimax_analysis") or {}
    if not isinstance(analysis, dict):
        return False
    description = img.get("description") or img.get("generated_description") or ""
    return bool(
        description
        and analysis.get("description")
        and img.get("analyzed_at")
        and img.get("classified_by")
        and _is_persisted_analyzed(img)
    )


def _save_image_index_and_verify_analysis(data: dict[str, Any], record_key: str) -> tuple[bool, dict[str, Any] | None, int]:
    _save_image_index(data)
    reloaded = _load_image_index()
    reloaded_img = _find_image(reloaded, record_key)
    return _has_durable_analysis_truth(reloaded_img), reloaded_img, _count_persisted_analyzed(reloaded)


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
    if result.get("analysis_status") == "success":
        result.setdefault("provider", "minimax")
        result.setdefault("transport", "mmx_cli")
        result.setdefault("model", "mmx_vision")

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
        _apply_asset_tags(img, description)

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
    ollama_processed = 0
    categories = {}
    stats = {}

    # Read memory-only Ollama job progress (stale after job ends)
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                pdata = json.load(f)
            ollama_list = pdata.get("processed", [])
            ollama_processed = len(ollama_list)
            stats = pdata.get("stats", {})
            categories = pdata.get("categories") or {k: v for k, v in stats.items() if k != "processed"}
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

    # Load persistent index for accurate analyzed count
    index_data = _load_image_index()
    all_images = index_data.get("images", [])
    persisted_analyzed = sum(1 for img in all_images if _is_persisted_analyzed(img))
    total_indexed = len(all_images)

    # Percentage based on indexed records (not stale Ollama counter)
    percentage = round((persisted_analyzed / total_indexed) * 100, 1) if total_indexed > 0 else 0

    return {
        "total_images": total_indexed,
        "processed": ollama_processed,
        "persisted_analyzed": persisted_analyzed,
        "percentage": percentage,
        "running": running,
        "categories": categories,
        "stats": stats,
        "index_file": INDEX_FILE,
        "progress_file": PROGRESS_FILE,
        "classified_dir": CLASSIFIED_DIR,
        "minimax_quota": check_quota(),
    }


@router.get("/recovery/persistence-audit")
async def recovery_persistence_audit():
    """Read-only audit of record persistence truth. No batch analysis."""
    index_data = _load_image_index()
    all_images = index_data.get("images", [])
    total = len(all_images)

    # Count categories
    persisted_analyzed = 0
    records_with_description = 0
    records_with_minimax = 0
    records_with_analyzed_at = 0
    records_with_confidence = 0
    records_with_classified = 0
    records_with_error = 0
    records_with_ollama_error = 0
    needs_reanalysis = 0

    for img in all_images:
        has_desc = bool(img.get("description") or img.get("generated_description"))
        if has_desc and len((img.get("description") or img.get("generated_description") or "")) > 50:
            records_with_description += 1
        if img.get("minimax_analysis"):
            records_with_minimax += 1
        if img.get("analyzed_at"):
            records_with_analyzed_at += 1
        conf = img.get("confidence")
        if conf is not None and float(conf) > 0:
            records_with_confidence += 1
        classified = img.get("classified_by")
        if classified and classified not in ("none", ""):
            records_with_classified += 1

        if _is_persisted_analyzed(img):
            persisted_analyzed += 1
        else:
            # Not persisted-analyzed
            last_err = _last_analysis_error(img)
            if last_err:
                records_with_error += 1
                if "ollama" in str(last_err).lower():
                    records_with_ollama_error += 1
            # Has a source file path and no error — candidate for reanalysis
            if img.get("path") or img.get("source_path"):
                if not last_err:
                    needs_reanalysis += 1

    # Check stale progress file
    stale_progress = False
    progress_count = 0
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                pdata = json.load(f)
            progress_count = len(pdata.get("processed", []))
            # If stats say needs-ai is still high but persisted_analyzed is very low,
            # the progress file is stale (memory-only, never persisted to index)
            needs_ai = pdata.get("stats", {}).get("needs-ai", 0)
            if needs_ai > 10000 and persisted_analyzed < 10:
                stale_progress = True
        except Exception:
            pass

    return {
        "total_records": total,
        "persisted_analyzed_count": persisted_analyzed,
        "records_with_description": records_with_description,
        "records_with_minimax_analysis": records_with_minimax,
        "records_with_analyzed_at": records_with_analyzed_at,
        "records_with_confidence_score": records_with_confidence,
        "records_with_classified_by": records_with_classified,
        "records_with_error": records_with_error,
        "records_with_ollama_error": records_with_ollama_error,
        "needs_reanalysis_candidates": needs_reanalysis,
        "stale_progress_file": stale_progress,
        "ollama_progress_count": progress_count,
        "progress_file": PROGRESS_FILE,
        "index_file": INDEX_FILE,
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
    tag_category: str | None = None,
    tag: str | None = None,
    sort: str = "classified_at_desc",
    analyzed_only: bool = True,
    limit: int = Query(default=48, ge=1, le=120),
    offset: int = Query(default=0, ge=0),
):
    """Browse RecoveryForge image index metadata from the loaded recovery router."""
    data = _load_image_index()
    images = data.get("images", [])

    if analyzed_only:
        images = [img for img in images if _is_persisted_analyzed(img)]
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
    elif status == "scrapped":
        images = [img for img in images if img.get("scrapped")]
    elif status == "active":
        images = [img for img in images if not img.get("scrapped")]
    if social_ready is not None:
        images = [img for img in images if bool(img.get("social_ready")) is social_ready]
    if min_confidence is not None:
        images = [img for img in images if float(img.get("confidence") or 0) >= min_confidence]
    if tag_category and tag:
        tag_slug = _slugify_tag(tag)
        images = [
            img for img in images
            if tag_slug in [_slugify_tag(t) for t in img.get(tag_category, [])]
        ]
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
    analyzed = [img for img in all_images if _is_persisted_analyzed(img)]
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


@router.patch("/recovery/images/{record_key}/tags")
async def recovery_update_tags(record_key: str, tags_update: RecoveryImageTagsUpdate):
    """
    Manually edit structured tag arrays for one RecoveryForge image record.
    Does NOT run analysis or call image generation.
    Only supplied fields are updated; all other tags are preserved.
    """
    data = _load_image_index()
    img = _find_image(data, record_key)
    if not img:
        raise HTTPException(status_code=404, detail=f"RecoveryForge image record not found: {record_key}")

    # Snapshot provenance fields before any mutation
    had_manual_tags = bool(img.get("tags_manually_edited"))

    # Build tag update map from supplied fields
    update_map = tags_update.model_dump(exclude_unset=True)
    rejected: list[str] = []

    for field, tag_list in update_map.items():
        if field not in TAG_ARRAY_FIELDS:
            continue

        # Slugify, de-duplicate, block dangerous tags
        normalized: list[str] = []
        for tag in tag_list:
            slug = _slugify_tag(tag)
            if slug in TAG_BLOCKLIST:
                rejected.append(slug)
                continue
            if slug and slug not in normalized:
                normalized.append(slug)

        if normalized:
            img[field] = normalized
        elif field in img and tag_list is not None:
            # Explicit empty list → clear the field
            img[field] = []

    # Update provenance
    img["tags_manually_edited"] = True
    img["tags_updated_at"] = datetime.now(timezone.utc).isoformat()
    img["tags_updated_by"] = "operator"

    _save_image_index(data)

    return {
        "status": "tags_updated",
        "record_key": record_key,
        "image": _public_image_item(img),
        "rejected_tags": rejected,
        "tags_manually_edited": True,
        "tags_updated_at": img["tags_updated_at"],
        "tags_updated_by": img["tags_updated_by"],
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


# ── Controlled Reanalysis Queue ─────────────────────────────────────────────────

QUEUE_FILE = "/data/images/recovery_reanalysis_queue.json"
ALLOWED_LIMITS = {1, 5, 10, 25, 50, 100}


def _load_queue_state() -> dict[str, Any]:
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"running": False, "paused": False}


def _save_queue_state(state: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(QUEUE_FILE, "w") as f:
        json.dump(state, f)


def _build_queue_candidates(data: dict[str, Any], filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Select reanalysis candidates: not scrapped, not persisted analyzed, has readable path."""
    candidates = []
    for img in data.get("images", []):
        # Exclude already persisted analyzed
        if _is_persisted_analyzed(img):
            continue
        # Exclude scrapped
        if img.get("scrapped") or img.get("soft_deleted"):
            continue
        # Require a readable path
        path = img.get("path") or img.get("source_path") or img.get("classified_path") or ""
        if not path or not os.path.exists(path):
            continue
        # Optional filters
        if filters.get("category"):
            cat = img.get("category") or img.get("pre_category") or ""
            if cat != filters["category"]:
                continue
        if filters.get("business"):
            biz = img.get("business") or img.get("pre_tag") or ""
            if biz != filters["business"]:
                continue
        candidates.append(img)
    return candidates


@router.get("/recovery/reanalysis-queue/status")
async def reanalysis_queue_status():
    """Return current reanalysis queue state."""
    state = _load_queue_state()
    # Derive current persisted_analyzed from index
    index_data = _load_image_index()
    persisted_analyzed = sum(1 for img in index_data["images"] if _is_persisted_analyzed(img))
    return {
        **state,
        "persisted_analyzed": persisted_analyzed,
        "total_indexed": len(index_data["images"]),
    }


class ReanalysisQueueStartRequest(BaseModel):
    limit: int = 25
    dry_run: bool = False
    filters: dict[str, Any] = {
        "active_only": True,
        "exclude_scrapped": True,
        "persisted_analyzed_only": False,
        "category": None,
        "business": None,
        "tag_category": None,
        "tag": None,
    }


@router.post("/recovery/reanalysis-queue/start")
async def reanalysis_queue_start(request: ReanalysisQueueStartRequest):
    """Start a bounded reanalysis queue. Limits: 1, 5, 10, 25, 50, 100."""
    # Validate limit
    if request.limit not in ALLOWED_LIMITS:
        raise HTTPException(
            status_code=400,
            detail=f"limit must be one of {sorted(ALLOWED_LIMITS)}. Got {request.limit}.",
        )

    # Check current state
    current = _load_queue_state()
    if current.get("running") and not current.get("paused"):
        return {"started": False, "reason": "queue already running", "state": current}

    data = _load_image_index()
    candidates = _build_queue_candidates(data, request.filters)
    selected = candidates[: request.limit]

    if not selected:
        return {"started": False, "reason": "no eligible candidates", "state": _load_queue_state()}

    if request.dry_run:
        return {
            "dry_run": True,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "selected_keys": [_record_key(img) for img in selected],
            "filters": request.filters,
            "message": "dry_run — no images analyzed",
        }

    record_keys = [_record_key(img) for img in selected]
    state: dict[str, Any] = {
        "running": True,
        "paused": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "requested_limit": request.limit,
        "processed_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "skipped_count": 0,
        "current_record_key": None,
        "last_success_record_key": None,
        "last_error": None,
        "candidate_count": len(candidates),
        "completed_record_keys": [],
        "failed_record_keys": [],
        "image_generation_used": False,
        "filters": request.filters,
    }
    _save_queue_state(state)

    return {
        "started": True,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "selected_keys": record_keys,
        "filters": request.filters,
    }


@router.post("/recovery/reanalysis-queue/stop")
async def reanalysis_queue_stop():
    """Stop the running queue."""
    state = _load_queue_state()
    state["running"] = False
    state["paused"] = False
    state["last_error"] = "operator stopped"
    _save_queue_state(state)
    return {"stopped": True, "state": state}


@router.post("/recovery/reanalysis-queue/pause")
async def reanalysis_queue_pause():
    """Pause the running queue."""
    state = _load_queue_state()
    if not state.get("running"):
        return {"paused": False, "reason": "queue not running"}
    state["paused"] = True
    _save_queue_state(state)
    return {"paused": True, "state": state}


@router.post("/recovery/reanalysis-queue/resume")
async def reanalysis_queue_resume():
    """Resume a paused queue."""
    state = _load_queue_state()
    if not state.get("running"):
        return {"resumed": False, "reason": "queue not running"}
    if not state.get("paused"):
        return {"resumed": False, "reason": "queue not paused"}
    state["paused"] = False
    _save_queue_state(state)
    return {"resumed": True, "state": state}


@router.post("/recovery/reanalysis-queue/process-next")
async def reanalysis_queue_process_next():
    """Process one image from the queue. Called internally or by operator trigger."""
    state = _load_queue_state()
    if not state.get("running"):
        return {"processed": False, "reason": "queue not running"}
    if state.get("paused"):
        return {"processed": False, "reason": "queue paused"}

    # Load current index
    data = _load_image_index()
    all_images = data.get("images", [])
    persisted_analyzed_before = _count_persisted_analyzed(data)

    # Find next unprocessed record in selected keys
    completed = set(state.get("completed_record_keys", []))
    failed = set(state.get("failed_record_keys", []))
    done_keys = completed | failed

    # Get candidate list for this run's filters
    filters = state.get("filters", {})
    candidates = _build_queue_candidates(data, filters)

    # Pick first eligible not already processed
    chosen = None
    for img in candidates:
        key = _record_key(img)
        if key in done_keys:
            continue
        # Skip if already persisted analyzed (could have been analyzed elsewhere)
        if _is_persisted_analyzed(img):
            done_keys.add(key)
            continue
        chosen = img
        break

    if not chosen:
        # No more candidates — queue complete
        state["running"] = False
        state["last_error"] = None
        _save_queue_state(state)
        return {"processed": False, "reason": "queue complete", "state": state}

    key = _record_key(chosen)
    state["current_record_key"] = key
    _save_queue_state(state)

    # Check quota
    if not quota_allow_new():
        quota = check_quota()
        state["last_error"] = "cap_reached"
        state["failure_count"] += 1
        state["failed_record_keys"].append(key)
        state["current_record_key"] = None
        _save_queue_state(state)
        return {
            "processed": False,
            "record_key": key,
            "status": "cap_reached",
            "message": f"Quota cap reached. {quota.get('current_window_remaining_for_recoveryforge', 0)} remaining.",
            "quota": quota,
        }

    # Resolve path
    path = (chosen.get("classified_path") or chosen.get("path") or "") if chosen else ""
    if not path or not os.path.exists(path):
        state["last_error"] = f"file_not_found: {path}"
        state["skipped_count"] += 1
        state["failed_record_keys"].append(key)
        state["current_record_key"] = None
        _save_queue_state(state)
        return {"processed": False, "record_key": key, "status": "file_not_found"}

    # Call MiniMax
    result = await analyze_image(key, path)
    _apply_minimax_analysis(chosen, result, path)

    if result.get("analysis_status") == "success":
        persisted_verified = False
        persisted_analyzed_after = persisted_analyzed_before
        persistence_error = None
        try:
            persisted_verified, _, persisted_analyzed_after = _save_image_index_and_verify_analysis(data, key)
        except Exception as exc:
            persistence_error = str(exc)[:200]

        if persisted_verified:
            state["success_count"] += 1
            state["completed_record_keys"].append(key)
            state["last_success_record_key"] = key
            state["last_error"] = None
        else:
            state["failure_count"] += 1
            state["failed_record_keys"].append(key)
            state["last_error"] = (
                f"persistence_save_failed: {persistence_error}"
                if persistence_error
                else "persistence_not_verified_after_reload"
            )
    else:
        err = result.get("error", "unknown")
        state["failure_count"] += 1
        state["failed_record_keys"].append(key)
        state["last_error"] = str(err)[:200]
        _save_image_index(data)
        persisted_analyzed_after = _count_persisted_analyzed(_load_image_index())
        persisted_verified = False

    state["processed_count"] += 1
    state["current_record_key"] = None
    _save_queue_state(state)

    return {
        "processed": True,
        "record_key": key,
        "filename": chosen.get("filename"),
        "status": result.get("analysis_status") if persisted_verified or result.get("analysis_status") != "success" else "persistence_failed",
        "success": bool(result.get("analysis_status") == "success" and persisted_verified),
        "persisted_verified": persisted_verified,
        "persisted_analyzed_before": persisted_analyzed_before,
        "persisted_analyzed_after": persisted_analyzed_after,
        "success_count": state["success_count"],
        "failure_count": state["failure_count"],
        "skipped_count": state["skipped_count"],
        "processed_count": state["processed_count"],
        "image_generation_used": False,
    }


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


@router.post("/recovery/images/{record_key}/scrap")
async def recovery_scrap_image(record_key: str, scrap: RecoveryImageScrapRequest):
    """
    Scrap / soft-delete a RecoveryForge image record.

    Modes:
    - soft_delete: mark record as scrapped, hide from active list. Files untouched.
    - delete_classified: mark scrapped + trash classified/social copies. Source untouched.
    - delete_all_copies: mark scrapped + trash all copies. Requires explicit confirm_text='DELETE'.

    delete_source: if True AND confirm_text='DELETE', also moves source to trash.
    Never deletes source without explicit confirm_text match.
    """
    VALID_MODES = ("soft_delete", "delete_classified", "delete_all_copies")
    if scrap.mode not in VALID_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of: {', '.join(VALID_MODES)}")

    if scrap.mode == "delete_all_copies" and not scrap.confirm:
        raise HTTPException(status_code=400, detail="delete_all_copies requires confirm=true")
    if scrap.delete_source and scrap.confirm_text != "DELETE":
        raise HTTPException(status_code=400, detail="delete_source requires confirm_text='DELETE'")

    reason = _normalize_label(scrap.reason) or "unrelated"
    data = _load_image_index()
    img = _find_image(data, record_key)
    if not img:
        raise HTTPException(status_code=404, detail=f"RecoveryForge image record not found: {record_key}")

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "record_key": record_key,
        "mode": scrap.mode,
        "reason": reason,
        "source_deleted": False,
        "source_kept": True,
        "source_missing": False,
        "classified_deleted": False,
        "classified_missing": False,
        "social_deleted": False,
        "social_missing": False,
        "record_status": "scrapped",
    }

    # --- soft_delete: mark record only ---
    img["scrapped"] = True
    img["scrapped_at"] = now
    img["scrapped_reason"] = reason
    img["scrapped_mode"] = scrap.mode

    # --- file operations ---
    source_path = img.get("source_path") or img.get("path")
    classified_path = img.get("classified_path")
    social_path = img.get("social_path")

    def _trash_file(path: str | None) -> bool:
        """Move file to trash, return True if moved or already missing."""
        if not path:
            return True  # treat absent as success
        if not os.path.exists(path):
            return True
        trash_dest = _safe_trash_path(path)
        if not trash_dest:
            return False
        try:
            shutil.move(path, trash_dest)
            return True
        except Exception as e:
            logger.warning(f"Could not trash {path}: {e}")
            return False

    if scrap.mode in ("delete_classified", "delete_all_copies"):
        # trash classified copy
        if classified_path:
            trashed = _trash_file(classified_path)
            result["classified_deleted"] = trashed and os.path.exists(classified_path) is False
            result["classified_missing"] = not classified_path or not os.path.exists(classified_path)
            if trashed:
                img["classified_path"] = None
                img["classified_exists"] = False
        else:
            result["classified_missing"] = True

        # trash social copy
        if social_path:
            trashed = _trash_file(social_path)
            result["social_deleted"] = trashed and os.path.exists(social_path) is False
            result["social_missing"] = not social_path or not os.path.exists(social_path)
            if trashed:
                img["social_path"] = None
                img["social_exists"] = False
        else:
            result["social_missing"] = True

    if scrap.mode == "delete_all_copies" and scrap.confirm:
        if source_path and os.path.exists(source_path):
            trashed = _trash_file(source_path)
            result["source_deleted"] = trashed and os.path.exists(source_path) is False
            result["source_kept"] = not trashed
            result["source_missing"] = not os.path.exists(source_path)
            if trashed:
                img["source_path"] = None
                img["source_exists"] = False
                img["path"] = None
        else:
            result["source_missing"] = not bool(source_path) or not os.path.exists(source_path)
            result["source_kept"] = not result["source_missing"] and not result["source_deleted"]

    _save_image_index(data)

    return {
        "status": "scrapped",
        "record_key": record_key,
        "mode": scrap.mode,
        "reason": reason,
        "scrapped_at": now,
        **result,
        "image": _public_image_item(img),
        "path_status": _image_path_status(img),
    }
