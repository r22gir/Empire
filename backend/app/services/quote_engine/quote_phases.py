"""
Quote Intelligence System — Multi-Phase Quote Pipeline (v6.0)

Two tracks:
  Track 1 — Quick Quote: dimensions + material + complexity → instant ballpark
  Track 2 — Multi-Phase Pipeline: 6 phases with founder review gates

Phase flow:
  0 → Intake (existing QIS analyze-photo or manual entry)
  1 → AI Vision Analysis → founder review
  2 → Measurements & Materials → founder review
  3 → Pricing & Labor → founder review
  4 → Profit & Margin → founder review
  5 → Client Quote PDF → founder approve to send

Each phase stores validated data, carries photos, and requires founder approval
before advancing to the next phase.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .pricing_tables import (
    FABRIC_GRADES,
    LABOR_RATES,
    TAX_RATES,
    TIER_MULTIPLIERS,
    DEPOSIT_PERCENTAGE,
)
from .yardage_calculator import calculate_yardage

logger = logging.getLogger(__name__)

QUOTES_DIR = os.path.expanduser("~/empire-repo/backend/data/quotes")
os.makedirs(QUOTES_DIR, exist_ok=True)


# ── Track 1: Quick Quote ─────────────────────────────────────────────────

# Complexity multipliers for quick estimation
COMPLEXITY_MULTIPLIERS = {
    "simple": 1.0,      # standard shape, no special features
    "moderate": 1.35,    # some features (welting, piping)
    "complex": 1.75,     # tufting, nailhead, multi-cushion
    "luxury": 2.25,      # full custom, special construction
}

# Base price ranges per item type (Essential tier baseline)
QUICK_PRICE_TABLE = {
    # Upholstery
    "dining_chair_seat": {"base_low": 80, "base_high": 150},
    "dining_chair_full": {"base_low": 150, "base_high": 350},
    "accent_chair": {"base_low": 300, "base_high": 600},
    "wingback_chair": {"base_low": 400, "base_high": 800},
    "club_chair": {"base_low": 350, "base_high": 700},
    "ottoman": {"base_low": 125, "base_high": 350},
    "loveseat": {"base_low": 600, "base_high": 1200},
    "sofa_2cushion": {"base_low": 800, "base_high": 1800},
    "sofa_3cushion": {"base_low": 1200, "base_high": 2800},
    "sectional_per_section": {"base_low": 800, "base_high": 1800},
    "headboard": {"base_low": 300, "base_high": 800},
    "bench": {"base_low": 200, "base_high": 600},
    "banquette": {"base_low": 300, "base_high": 1200},
    # Window treatments
    "drapery_panel": {"base_low": 200, "base_high": 450},
    "roman_shade": {"base_low": 300, "base_high": 600},
    "roller_shade": {"base_low": 150, "base_high": 350},
    "valance": {"base_low": 100, "base_high": 300},
    "cornice": {"base_low": 150, "base_high": 400},
}


def quick_quote(
    item_type: str,
    width: float,
    height: float,
    depth: float = 0,
    material_grade: str = "B",
    complexity: str = "moderate",
    quantity: int = 1,
    notes: str = "",
) -> Dict[str, Any]:
    """Generate an instant ballpark quote from basic dimensions.

    Returns a price range (low-high) for each of 3 tiers.
    Founder-only — not client-facing until promoted to full analysis.
    """
    # Validate inputs
    if item_type not in QUICK_PRICE_TABLE:
        # Fuzzy match: try partial match
        matched = None
        for k in QUICK_PRICE_TABLE:
            if item_type.lower() in k or k in item_type.lower():
                matched = k
                break
        if matched:
            item_type = matched
        else:
            item_type = "accent_chair"  # safe default

    base = QUICK_PRICE_TABLE[item_type]
    comp_mult = COMPLEXITY_MULTIPLIERS.get(complexity, 1.35)
    fabric_grade = FABRIC_GRADES.get(material_grade.upper(), FABRIC_GRADES["B"])

    # Size factor: compare to "standard" dimensions for the type
    size_factor = 1.0
    if width > 0 and height > 0:
        # For upholstery, size scales roughly with surface area
        area = width * height
        if depth > 0:
            area += width * depth * 0.5  # partial depth contribution
        # Standard area benchmark (~36x36 for chairs, ~84x36 for sofas)
        if "sofa" in item_type or "sectional" in item_type:
            std_area = 84 * 36
        elif "loveseat" in item_type:
            std_area = 60 * 36
        elif "bench" in item_type or "banquette" in item_type:
            std_area = 48 * 18
        elif "headboard" in item_type:
            std_area = 60 * 48
        elif "drapery" in item_type or "shade" in item_type:
            std_area = 48 * 84
        else:
            std_area = 30 * 34  # standard chair
        size_factor = max(0.6, min(2.0, area / std_area))

    # Fabric cost factor (relative to grade B baseline)
    fabric_factor = fabric_grade["price_per_yard"] / FABRIC_GRADES["B"]["price_per_yard"]

    # Calculate ranges
    low = round(base["base_low"] * comp_mult * size_factor * fabric_factor * quantity, -1)
    high = round(base["base_high"] * comp_mult * size_factor * fabric_factor * quantity, -1)

    # 3-tier ranges using blended multipliers (average of fabric + labor multipliers)
    tier_a_data = TIER_MULTIPLIERS.get("A", {"fabric": 1.0, "labor": 1.0})
    tier_b_data = TIER_MULTIPLIERS.get("B", {"fabric": 2.0, "labor": 1.15})
    tier_c_data = TIER_MULTIPLIERS.get("C", {"fabric": 3.5, "labor": 1.3})

    # Blend: ~60% fabric weight, ~40% labor weight for overall multiplier
    def _blend(t: dict) -> float:
        return t.get("fabric", 1.0) * 0.6 + t.get("labor", 1.0) * 0.4

    tier_a = _blend(tier_a_data)
    tier_b = _blend(tier_b_data)
    tier_c = _blend(tier_c_data)

    result = {
        "type": "quick_quote",
        "item_type": item_type,
        "dimensions": {"width": width, "height": height, "depth": depth},
        "material_grade": material_grade.upper(),
        "complexity": complexity,
        "quantity": quantity,
        "size_factor": round(size_factor, 2),
        "tiers": {
            "essential": {
                "low": round(low * tier_a),
                "high": round(high * tier_a),
                "label": "Essential (Grade A fabric)",
            },
            "designer": {
                "low": round(low * tier_b),
                "high": round(high * tier_b),
                "label": "Designer (Grade B fabric)",
            },
            "premium": {
                "low": round(low * tier_c),
                "high": round(high * tier_c),
                "label": "Premium (Grade C/D fabric)",
            },
        },
        "notes": notes,
        "disclaimer": "Ballpark estimate only. Final price requires full analysis with photos.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Quick quote: %s %s (%s) → $%d–$%d (Essential)",
        quantity, item_type, complexity,
        result["tiers"]["essential"]["low"],
        result["tiers"]["essential"]["high"],
    )

    return result


# ── Track 2: Multi-Phase Pipeline ────────────────────────────────────────

PHASE_NAMES = {
    0: "Intake",
    1: "AI Vision Analysis",
    2: "Measurements & Materials",
    3: "Pricing & Labor",
    4: "Profit & Margin",
    5: "Client Quote PDF",
}


def _load_phase_quote(quote_id: str) -> Dict[str, Any]:
    """Load quote JSON with phase data."""
    path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Quote {quote_id} not found")
    with open(path) as f:
        return json.load(f)


def _save_phase_quote(quote: Dict[str, Any]):
    """Save quote JSON with phase data."""
    path = os.path.join(QUOTES_DIR, f"{quote['id']}.json")
    with open(path, "w") as f:
        json.dump(quote, f, indent=2, default=str)


def init_phase_pipeline(quote_id: str) -> Dict[str, Any]:
    """Initialize the phase pipeline on an existing quote.

    Sets phase=0, creates the phase_history array, and marks intake as complete.
    Returns the updated quote.
    """
    quote = _load_phase_quote(quote_id)

    now = datetime.now(timezone.utc).isoformat()

    # Don't re-initialize if already in pipeline
    if quote.get("phase_pipeline"):
        return quote

    quote["phase_pipeline"] = {
        "current_phase": 0,
        "phase_status": "approved",  # Phase 0 (intake) is auto-approved
        "started_at": now,
        "phases": {
            "0": {
                "name": "Intake",
                "status": "approved",
                "started_at": now,
                "approved_at": now,
                "data": {
                    "customer_name": quote.get("customer_name", ""),
                    "items_count": len(quote.get("items", [])),
                    "has_photos": bool(quote.get("photos")),
                    "source": "existing_quote",
                },
            }
        },
    }
    quote["updated_at"] = now
    _save_phase_quote(quote)

    logger.info("Phase pipeline initialized for quote %s", quote.get("quote_number", quote_id))
    return quote


def advance_phase(quote_id: str) -> Dict[str, Any]:
    """Advance to the next phase. Runs phase-specific logic.

    Each phase auto-populates its data from existing quote data + AI analysis.
    The phase then enters 'review' status awaiting founder approval.

    Returns the updated quote.
    """
    quote = _load_phase_quote(quote_id)
    pipeline = quote.get("phase_pipeline")
    if not pipeline:
        raise ValueError(f"Quote {quote_id} has no phase pipeline. Call init_phase_pipeline first.")

    current = pipeline["current_phase"]
    if pipeline["phase_status"] != "approved":
        raise ValueError(
            f"Phase {current} ({PHASE_NAMES.get(current, '?')}) has not been approved yet. "
            f"Current status: {pipeline['phase_status']}"
        )

    next_phase = current + 1
    if next_phase > 5:
        raise ValueError("Quote is already at final phase (5). Use finalize to generate PDF.")

    now = datetime.now(timezone.utc).isoformat()

    # Run phase-specific logic
    phase_data = _run_phase_logic(quote, next_phase)

    # Record phase
    pipeline["current_phase"] = next_phase
    pipeline["phase_status"] = "review"
    pipeline["phases"][str(next_phase)] = {
        "name": PHASE_NAMES.get(next_phase, f"Phase {next_phase}"),
        "status": "review",
        "started_at": now,
        "data": phase_data,
    }

    quote["updated_at"] = now
    _save_phase_quote(quote)

    logger.info(
        "Quote %s advanced to Phase %d (%s) — awaiting review",
        quote.get("quote_number", quote_id), next_phase, PHASE_NAMES.get(next_phase),
    )

    return quote


def approve_phase(quote_id: str, founder_notes: str = "") -> Dict[str, Any]:
    """Founder approves the current phase. Unlocks advance_phase for the next one."""
    quote = _load_phase_quote(quote_id)
    pipeline = quote.get("phase_pipeline")
    if not pipeline:
        raise ValueError("No phase pipeline on this quote.")

    current = pipeline["current_phase"]
    if pipeline["phase_status"] != "review":
        raise ValueError(f"Phase {current} is not in review (status: {pipeline['phase_status']})")

    now = datetime.now(timezone.utc).isoformat()
    pipeline["phase_status"] = "approved"

    phase_record = pipeline["phases"].get(str(current), {})
    phase_record["status"] = "approved"
    phase_record["approved_at"] = now
    phase_record["founder_notes"] = founder_notes

    quote["updated_at"] = now
    _save_phase_quote(quote)

    logger.info("Phase %d approved for quote %s", current, quote.get("quote_number", quote_id))
    return quote


def reject_phase(quote_id: str, reason: str = "") -> Dict[str, Any]:
    """Founder rejects the current phase. Stays on same phase for revision."""
    quote = _load_phase_quote(quote_id)
    pipeline = quote.get("phase_pipeline")
    if not pipeline:
        raise ValueError("No phase pipeline on this quote.")

    current = pipeline["current_phase"]
    if pipeline["phase_status"] != "review":
        raise ValueError(f"Phase {current} is not in review (status: {pipeline['phase_status']})")

    now = datetime.now(timezone.utc).isoformat()
    pipeline["phase_status"] = "revision"

    phase_record = pipeline["phases"].get(str(current), {})
    phase_record["status"] = "revision"
    phase_record["rejected_at"] = now
    phase_record["rejection_reason"] = reason

    quote["updated_at"] = now
    _save_phase_quote(quote)

    logger.info("Phase %d rejected for quote %s: %s", current, quote.get("quote_number", quote_id), reason)
    return quote


def retry_phase(quote_id: str) -> Dict[str, Any]:
    """Re-run the current phase after revision (e.g., photos updated, measurements corrected)."""
    quote = _load_phase_quote(quote_id)
    pipeline = quote.get("phase_pipeline")
    if not pipeline:
        raise ValueError("No phase pipeline on this quote.")

    current = pipeline["current_phase"]
    if pipeline["phase_status"] != "revision":
        raise ValueError(f"Phase {current} is not in revision (status: {pipeline['phase_status']})")

    # Re-run phase logic
    phase_data = _run_phase_logic(quote, current)

    now = datetime.now(timezone.utc).isoformat()
    pipeline["phase_status"] = "review"

    phase_record = pipeline["phases"].get(str(current), {})
    phase_record["status"] = "review"
    phase_record["retried_at"] = now
    phase_record["data"] = phase_data

    quote["updated_at"] = now
    _save_phase_quote(quote)

    logger.info("Phase %d retried for quote %s", current, quote.get("quote_number", quote_id))
    return quote


def get_phase_status(quote_id: str) -> Dict[str, Any]:
    """Get the phase pipeline status for a quote."""
    quote = _load_phase_quote(quote_id)
    pipeline = quote.get("phase_pipeline")
    if not pipeline:
        return {
            "has_pipeline": False,
            "quote_id": quote_id,
            "quote_number": quote.get("quote_number", ""),
        }

    current = pipeline["current_phase"]
    return {
        "has_pipeline": True,
        "quote_id": quote_id,
        "quote_number": quote.get("quote_number", ""),
        "customer_name": quote.get("customer_name", ""),
        "current_phase": current,
        "current_phase_name": PHASE_NAMES.get(current, f"Phase {current}"),
        "phase_status": pipeline["phase_status"],
        "total_phases": 6,
        "progress_pct": round(current / 5 * 100),
        "phases": pipeline.get("phases", {}),
        "started_at": pipeline.get("started_at"),
    }


def edit_item_in_pipeline(
    quote_id: str, item_index: int, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Edit an item's measurements/details within the phase pipeline.

    Allows the founder to correct dimensions, change item type, update
    quantities, or add notes during any review phase. Recalculates
    yardage after dimension changes.

    Args:
        quote_id: The quote ID.
        item_index: Index of the item to edit (0-based).
        updates: Dict of fields to update (width, height, depth, quantity,
                 item_type, name, notes, construction, condition, special_features).

    Returns:
        The updated quote dict.
    """
    quote = _load_phase_quote(quote_id)
    items = quote.get("items", [])

    if item_index < 0 or item_index >= len(items):
        raise IndexError(
            f"Item index {item_index} out of range. Quote has {len(items)} items."
        )

    item = items[item_index]
    now = datetime.now(timezone.utc).isoformat()

    # Track what changed for audit
    changes = []

    # Update dimensions
    dims = item.get("dimensions", {})
    for dim_key in ("width", "height", "depth"):
        if dim_key in updates and updates[dim_key] is not None:
            old_val = dims.get(dim_key, 0)
            dims[dim_key] = updates[dim_key]
            if old_val != updates[dim_key]:
                changes.append(f"{dim_key}: {old_val} → {updates[dim_key]}")
    item["dimensions"] = dims

    # Update scalar fields
    for field in ("quantity", "name", "notes", "construction", "condition"):
        if field in updates and updates[field] is not None:
            old_val = item.get(field, "")
            item[field] = updates[field]
            if old_val != updates[field]:
                changes.append(f"{field}: {old_val} → {updates[field]}")

    # Update item type
    if "item_type" in updates and updates["item_type"] is not None:
        old_type = item.get("type", "")
        item["type"] = updates["item_type"]
        if old_type != updates["item_type"]:
            changes.append(f"type: {old_type} → {updates['item_type']}")

    # Update special features
    if "special_features" in updates and updates["special_features"] is not None:
        item["special_features"] = updates["special_features"]
        changes.append(f"special_features updated")

    # Recalculate yardage if dimensions or type changed
    dim_changed = any(k in updates for k in ("width", "height", "depth", "item_type"))
    if dim_changed:
        try:
            opts = {}
            if item.get("cushion_count"):
                opts["cushion_count"] = item["cushion_count"]
            if any("tuft" in f.lower() for f in item.get("special_features", [])):
                opts["tufted"] = True
            yardage = calculate_yardage(item.get("type", "accent_chair"), dims, opts)
            item["_yardage"] = yardage
            changes.append(f"yardage recalculated: {yardage.get('yards', 0):.1f} yards")
        except Exception as e:
            logger.warning("Yardage recalc failed for item %d: %s", item_index, e)

    # Store edit history
    if changes:
        edit_log = item.get("_edit_history", [])
        edit_log.append({
            "edited_at": now,
            "changes": changes,
            "source": "founder_review",
        })
        item["_edit_history"] = edit_log

    items[item_index] = item
    quote["items"] = items
    quote["updated_at"] = now

    _save_phase_quote(quote)

    logger.info(
        "Quote %s item %d edited: %s",
        quote.get("quote_number", quote_id),
        item_index,
        ", ".join(changes) if changes else "no changes",
    )
    return quote


def promote_quick_to_full(quick_quote_data: Dict[str, Any], customer_name: str) -> Dict[str, Any]:
    """Promote a quick quote to a full phase-pipeline quote.

    Creates a new quote JSON with the quick quote data as Phase 0 intake,
    ready for photo upload and AI analysis in Phase 1.
    """
    quote_id = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()

    item_type = quick_quote_data.get("item_type", "accent_chair")
    dims = quick_quote_data.get("dimensions", {})
    quantity = quick_quote_data.get("quantity", 1)

    quote = {
        "id": quote_id,
        "quote_number": _next_phase_quote_number(),
        "customer_name": customer_name,
        "customer_email": "",
        "customer_phone": "",
        "customer_address": "",
        "project_name": f"Quote for {customer_name}",
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "items": [
            {
                "name": item_type.replace("_", " ").title(),
                "type": item_type,
                "dimensions": dims,
                "quantity": quantity,
                "construction": "",
                "condition": "",
                "special_features": [],
            }
        ],
        "quick_quote_origin": quick_quote_data,
        "phase_pipeline": {
            "current_phase": 0,
            "phase_status": "approved",
            "started_at": now,
            "phases": {
                "0": {
                    "name": "Intake",
                    "status": "approved",
                    "started_at": now,
                    "approved_at": now,
                    "data": {
                        "source": "quick_quote_promotion",
                        "customer_name": customer_name,
                        "item_type": item_type,
                        "quick_estimate": quick_quote_data.get("tiers", {}),
                    },
                }
            },
        },
    }

    _save_phase_quote(quote)
    logger.info(
        "Quick quote promoted to full pipeline: %s → %s",
        item_type, quote["quote_number"],
    )
    return quote


def _next_phase_quote_number() -> str:
    """Generate sequential quote number for phase quotes."""
    year = datetime.now(timezone.utc).year
    existing = []
    if os.path.isdir(QUOTES_DIR):
        for fname in os.listdir(QUOTES_DIR):
            if fname.endswith(".json") and not fname.startswith("_"):
                try:
                    with open(os.path.join(QUOTES_DIR, fname)) as f:
                        data = json.load(f)
                    qn = data.get("quote_number", "")
                    if qn.startswith(f"EST-{year}-"):
                        num = int(qn.split("-")[-1])
                        existing.append(num)
                except Exception:
                    continue
    next_num = max(existing, default=0) + 1
    return f"EST-{year}-{next_num:03d}"


# ── Phase Logic ──────────────────────────────────────────────────────────

def _run_phase_logic(quote: Dict[str, Any], phase: int) -> Dict[str, Any]:
    """Run phase-specific data generation. Returns phase data dict."""
    if phase == 1:
        return _phase_1_vision_analysis(quote)
    elif phase == 2:
        return _phase_2_measurements(quote)
    elif phase == 3:
        return _phase_3_pricing(quote)
    elif phase == 4:
        return _phase_4_margins(quote)
    elif phase == 5:
        return _phase_5_final(quote)
    return {}


def _phase_1_vision_analysis(quote: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 1: Summarize AI vision analysis results.

    Pulls from existing quote items (from QIS analyze-photo or manual entry).
    If items have photo_url or analysis data, include it.
    """
    items = quote.get("items", [])
    photos = quote.get("photos", [])

    analysis_summary = []
    for item in items:
        summary = {
            "name": item.get("name", "Unknown"),
            "type": item.get("type", "unknown"),
            "dimensions_detected": bool(item.get("dimensions")),
            "has_photo": bool(item.get("photo_url") or item.get("sourcePhoto")),
            "construction": item.get("construction", "not assessed"),
            "condition": item.get("condition", "not assessed"),
            "special_features": item.get("special_features", []),
        }
        analysis_summary.append(summary)

    return {
        "items_analyzed": len(items),
        "photos_attached": len(photos),
        "items": analysis_summary,
        "ai_notes": quote.get("max_analysis", "No AI analysis available — upload photos for Phase 1"),
        "review_checklist": [
            "Verify item types are correctly identified",
            "Confirm construction style matches photos",
            "Check special features (tufting, nailhead, etc.)",
            "Ensure all items are accounted for",
        ],
    }


def _phase_2_measurements(quote: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 2: Measurements & Materials.

    Compile all measurements, calculate yardage, determine material needs.
    """
    items = quote.get("items", [])
    material_summary = []

    total_yardage = 0
    for item in items:
        dims = item.get("dimensions", {})
        item_type = item.get("type", "accent_chair")
        quantity = item.get("quantity", 1)

        # Calculate yardage
        opts = {}
        if item.get("cushion_count"):
            opts["cushion_count"] = item["cushion_count"]
        if any("tuft" in f.lower() for f in item.get("special_features", [])):
            opts["tufted"] = True

        yardage = calculate_yardage(item_type, dims, opts)
        yards = yardage.get("yards", 0) * quantity

        material_summary.append({
            "name": item.get("name", ""),
            "type": item_type,
            "dimensions": dims,
            "quantity": quantity,
            "yardage": round(yards, 1),
            "yardage_breakdown": yardage,
        })
        total_yardage += yards

    return {
        "items": material_summary,
        "total_yardage": round(total_yardage, 1),
        "fabric_grades_available": {k: v["name"] for k, v in FABRIC_GRADES.items()},
        "review_checklist": [
            "Verify all measurements are accurate",
            f"Total yardage: {total_yardage:.1f} yards — add 10% waste buffer",
            "Confirm fabric grade selection with customer",
            "Check lining requirements",
        ],
    }


def _phase_3_pricing(quote: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 3: Pricing & Labor.

    Generate 3-tier pricing with itemized labor and material costs.
    Uses existing tier_generator if tiers already exist, otherwise builds fresh.
    """
    items = quote.get("items", [])
    tiers = quote.get("tiers", {})
    location = quote.get("location", "DC")

    # If tiers already exist (from QIS pipeline), summarize them
    if tiers:
        tier_summary = {}
        for key in ("A", "B", "C"):
            tier = tiers.get(key, {})
            tier_summary[key] = {
                "name": tier.get("name", f"Tier {key}"),
                "subtotal": tier.get("subtotal", 0),
                "tax": tier.get("tax", 0),
                "total": tier.get("total", 0),
                "deposit": tier.get("deposit", 0),
                "items_count": len(tier.get("items", [])),
            }

        return {
            "tiers": tier_summary,
            "location": location,
            "tax_rate": TAX_RATES.get(location.upper(), TAX_RATES.get("DC", 0.06)),
            "tier_multipliers": TIER_MULTIPLIERS,
            "review_checklist": [
                "Review tier pricing spread (A→B→C)",
                "Verify labor rates are current",
                "Check material pricing against current supplier costs",
                "Confirm tax rate for location",
            ],
        }

    # No tiers yet — build estimated pricing from item data
    estimated_items = []
    for item in items:
        item_type = item.get("type", "accent_chair")
        labor = LABOR_RATES.get(item_type, {"base": 200})
        base_labor = labor.get("base", 200)
        quantity = item.get("quantity", 1)

        # Estimate material cost from yardage
        yardage_info = item.get("yardage", item.get("_yardage", {}))
        yards = yardage_info.get("yards", 8) if isinstance(yardage_info, dict) else 8

        estimated_items.append({
            "name": item.get("name", item_type),
            "labor_base": base_labor * quantity,
            "fabric_yards": round(yards * quantity, 1),
            "fabric_cost_grade_b": round(yards * FABRIC_GRADES["B"]["price_per_yard"] * quantity, 2),
        })

    return {
        "estimated_items": estimated_items,
        "location": location,
        "tax_rate": TAX_RATES.get(location.upper(), TAX_RATES.get("DC", 0.06)),
        "tier_multipliers": TIER_MULTIPLIERS,
        "note": "Estimated pricing — run full QIS pipeline for accurate 3-tier quotes",
        "review_checklist": [
            "Review estimated labor costs",
            "Confirm fabric yardage calculations",
            "Set desired profit margins",
        ],
    }


def _phase_4_margins(quote: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 4: Profit & Margin analysis.

    Calculate margins, compare to market, suggest adjustments.
    """
    tiers = quote.get("tiers", {})
    items = quote.get("items", [])

    # Calculate total material cost (fabric + supplies)
    total_material = 0
    total_labor = 0
    for item in items:
        item_type = item.get("type", "accent_chair")
        quantity = item.get("quantity", 1)
        labor_data = LABOR_RATES.get(item_type, {"base": 200})
        total_labor += labor_data.get("base", 200) * quantity

        yardage_info = item.get("yardage", item.get("_yardage", {}))
        yards = yardage_info.get("yards", 8) if isinstance(yardage_info, dict) else 8
        total_material += yards * FABRIC_GRADES["A"]["price_per_yard"] * quantity

    cost_basis = total_material + total_labor

    margin_analysis = {}
    for key in ("A", "B", "C"):
        tier = tiers.get(key, {})
        revenue = tier.get("total", 0)
        if revenue > 0:
            profit = revenue - cost_basis
            margin_pct = (profit / revenue) * 100
        else:
            profit = 0
            margin_pct = 0
        margin_analysis[key] = {
            "revenue": round(revenue, 2),
            "cost_basis": round(cost_basis, 2),
            "profit": round(profit, 2),
            "margin_pct": round(margin_pct, 1),
        }

    # Target margins
    targets = {"A": 40, "B": 50, "C": 60}

    return {
        "cost_breakdown": {
            "materials": round(total_material, 2),
            "labor": round(total_labor, 2),
            "total_cost": round(cost_basis, 2),
        },
        "margin_analysis": margin_analysis,
        "target_margins": targets,
        "deposit_percentage": DEPOSIT_PERCENTAGE,
        "review_checklist": [
            f"Cost basis: ${cost_basis:,.2f} (materials + labor)",
            "Review margin % per tier — target: A≥40%, B≥50%, C≥60%",
            "Adjust pricing if margins are below target",
            f"Deposit: {DEPOSIT_PERCENTAGE*100:.0f}% of total",
        ],
    }


def _phase_5_final(quote: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 5: Final review before PDF generation and client delivery."""
    from .verification import verify_quote

    # Run full verification
    verification = verify_quote(quote)

    # Compile final summary
    tiers = quote.get("tiers", {})
    tier_totals = {}
    for key in ("A", "B", "C"):
        tier = tiers.get(key, {})
        tier_totals[key] = tier.get("total", 0)

    return {
        "verification": verification,
        "tier_totals": tier_totals,
        "customer": {
            "name": quote.get("customer_name", ""),
            "email": quote.get("customer_email", ""),
            "phone": quote.get("customer_phone", ""),
            "address": quote.get("customer_address", ""),
        },
        "items_count": len(quote.get("items", [])),
        "has_photos": bool(quote.get("photos")),
        "quote_number": quote.get("quote_number", ""),
        "ready_to_send": verification.get("passed", False),
        "review_checklist": [
            f"Verification: {'PASSED' if verification.get('passed') else 'FAILED'} "
            f"(score {verification.get('score', 0)}/100, grade {verification.get('grade', 'F')})",
            "Review final PDF before sending to customer",
            "Confirm customer contact information",
            "Set valid-until date",
        ],
    }
