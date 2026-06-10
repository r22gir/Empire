"""D2 — Drawing intake schema.

Formalizes a structured drawing request shape with 6 output modes
(per the D1 + D1-Addendum recommendation):

* shop_drawing
* sketch_analysis
* concept_image
* planning_help
* animated_diagram
* visual_explainer

This module is the SINGLE source of truth for the intake enums, the
per-category required-dim table, and the default-qa-status computation.
The router (`app/routers/drawings.py`) imports from here and stays thin.

This module is read-only at runtime (no DB, no I/O). It is imported by:
* the drawings router (intake route handler)
* the drawing tests
* future D4 fab_qa module (per D1)
* future D5 Drawing Studio UI (per D1)

Conventions:
* All API response values are LOWERCASE snake_case per Founder direction.
* Animation modes (`animated_diagram`, `visual_explainer`) NEVER resolve
  to `shop_ready` — the server-side guardrail is enforced here.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ── 6 output modes (per D1 + D1-Addendum) ─────────────────────────────
class OutputMode(str, Enum):
    SHOP_DRAWING = "shop_drawing"
    SKETCH_ANALYSIS = "sketch_analysis"
    CONCEPT_IMAGE = "concept_image"
    PLANNING_HELP = "planning_help"
    ANIMATED_DIAGRAM = "animated_diagram"
    VISUAL_EXPLAINER = "visual_explainer"


# ── 3 business units ──────────────────────────────────────────────────
class BusinessUnit(str, Enum):
    EMPIRE_WORKROOM = "empire_workroom"
    EMPIRE_WOODCRAFT = "empire_woodcraft"
    SHARED = "shared"


# ── 13 categories (5 Workroom + 8 WoodCraft per Founder) ─────────────
class Category(str, Enum):
    # Empire Workroom
    CUSHION = "cushion"
    PILLOW = "pillow"
    UPHOLSTERY_WALL_PANEL = "upholstery_wall_panel"
    HEADBOARD = "headboard"
    WINDOW_TREATMENT = "window_treatment"
    # Empire WoodCraft
    BENCH = "bench"
    BANQUETTE = "banquette"
    SHELVING = "shelving"
    STORAGE_BENCH = "storage_bench"
    CABINET_MILLWORK = "cabinet_millwork"
    DESK = "desk"
    TABLE = "table"
    MURPHY_BED = "murphy_bed"


# ── Source type ──────────────────────────────────────────────────────
SourceType = Literal["text", "photo", "sketch", "mixed"]


# ── QA status (5 values, lowercase per Founder) ──────────────────────
QAStatus = Literal[
    "shop_ready",
    "review_ready",
    "needs_measurements",
    "concept_only",
    "unsupported",
]


# ── Per-category required-dim table (D2 surface only) ────────────────
# This is the MIN-DIM surface that the intake route validates against.
# It is NOT the full shop-grade dim set for D6 (parametric_renderer
# carries that; D6 is deferred per Founder).
#
# Notes:
# - bench / banquette already have full parametric support via
#   parametric_renderer.TEMPLATE_REGISTRY.
# - cushion / headboard / window_treatment / pillow are workroom-grade
#   parametric families in the registry.
# - All other categories are "shop: planned" today and fall through
#   to a generic 2-view fallback. D2 surfaces the min-dim gate; D6
#   is when the full parametric coverage lands.
REQUIRED_DIMS_BY_CATEGORY: Dict[str, List[str]] = {
    # Empire Workroom
    Category.CUSHION.value: ["width", "depth", "thickness"],
    Category.PILLOW.value: ["width", "height"],
    Category.UPHOLSTERY_WALL_PANEL.value: ["width", "height"],
    Category.HEADBOARD.value: ["width", "height"],
    Category.WINDOW_TREATMENT.value: ["width", "height"],
    # Empire WoodCraft
    Category.BENCH.value: ["width", "depth", "height"],
    Category.BANQUETTE.value: ["width", "depth", "height"],
    Category.SHELVING.value: ["width", "height", "depth"],
    Category.STORAGE_BENCH.value: ["width", "depth", "height"],
    Category.CABINET_MILLWORK.value: ["width", "height", "depth"],
    Category.DESK.value: ["width", "depth", "height"],
    Category.TABLE.value: ["width", "depth", "height"],
    Category.MURPHY_BED.value: ["width", "height"],
}


# ── Animation spec (optional) ────────────────────────────────────────
AnimationView = Literal["isometric", "exploded", "cross_section", "free", "plan", "front", "side"]
AnimationAudience = Literal["shop", "client", "installer", "internal_training"]


class AnimationFrame(BaseModel):
    step: int = Field(..., ge=1, le=20)
    label: str


class AnimationSpec(BaseModel):
    step_count: Optional[int] = Field(None, ge=2, le=20)
    duration_seconds: Optional[int] = Field(None, ge=2, le=120)
    view: Optional[AnimationView] = None
    frames: Optional[List[AnimationFrame]] = None
    sequence_notes: Optional[str] = None
    audience: Optional[AnimationAudience] = None


# ── Request model ─────────────────────────────────────────────────────
class DrawingIntakeRequest(BaseModel):
    business_unit: BusinessUnit
    category: Category
    output_mode: OutputMode
    source_type: SourceType
    dimensions: Optional[Dict[str, float]] = None
    units: Optional[Literal["mm", "inches"]] = None
    material: Optional[str] = None
    style: Optional[str] = None
    required_views: Optional[
        List[Literal["plan", "front", "side", "isometric", "section"]]
    ] = None
    requested_exports: Optional[
        List[Literal["svg", "pdf", "dxf", "csv", "bom"]]
    ] = None
    animation_spec: Optional[AnimationSpec] = None
    missing_fields: Optional[List[str]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    fabrication_readiness_status: Optional[QAStatus] = None
    warnings: Optional[List[str]] = None
    source_image_truth_note: Optional[str] = None


# ── Response model ────────────────────────────────────────────────────
class DrawingIntakeResponse(BaseModel):
    intake_id: str
    received_at: str
    # Echo of the request (after pydantic normalization)
    business_unit: BusinessUnit
    category: Category
    output_mode: OutputMode
    source_type: SourceType
    # Computed fields
    per_category_required_fields: List[str]
    per_category_missing_fields: List[str]
    default_qa_status: QAStatus
    category_unsupported: bool
    warnings: List[str] = Field(default_factory=list)

    # D4 — Fabrication QA Gate (additive, all Optional with defaults).
    # The new fabrication_qa field carries the full 10-check verdict.
    # The new qa_status is the D4-computed status (may differ from
    # default_qa_status when D4 is stricter). The new blocking_issues
    # and recommended_next_action are surfaced for the UI to display.
    # The existing default_qa_status is preserved for backward
    # compatibility with any caller that does not read the new fields.
    fabrication_qa: Optional["FabricationQAResult"] = None
    qa_status: Optional[QAStatus] = None
    blocking_issues: List[str] = Field(default_factory=list)
    recommended_next_action: Optional[str] = None


# ── Per-category default behavior ────────────────────────────────────
# Some categories (e.g. PILLOW) do not need an "animation_spec" to
# produce a useful visual; some (e.g. CABINET_MILLWORK) are richer with
# one. The intake route uses this to populate the warnings list.
ANIMATION_HINT_BY_CATEGORY: Dict[str, str] = {
    Category.CUSHION.value: "cushion construction sequence (4–6 step exploded view)",
    Category.PILLOW.value: "pillow detail explainer (close-up of corner style)",
    Category.UPHOLSTERY_WALL_PANEL.value: "wall panel assembly (panel layout, mounting method, seam alignment)",
    Category.HEADBOARD.value: "headboard mounting explanation (anchor type, anti-tip hardware)",
    Category.WINDOW_TREATMENT.value: "window treatment installation (rod/track mounting, drapery hook, stack height)",
    Category.BENCH.value: "bench assembly sequence (frame, seat, back, anchoring)",
    Category.BANQUETTE.value: "banquette assembly sequence (base frame, seat platform, back rest, cushion)",
    Category.SHELVING.value: "shelving installation diagram (bracket/cleat, level, shelf placement, load)",
    Category.STORAGE_BENCH.value: "storage bench exploded view (case, top, hinge, hardware, finish, joinery order)",
    Category.CABINET_MILLWORK.value: "millwork panel install steps (panel numbering, reveal, mounting)",
    Category.DESK.value: "desk assembly sequence (top, legs, joinery, hardware, finish, leveling)",
    Category.TABLE.value: "table assembly sequence (top, legs, joinery, hardware, finish, leveling)",
    Category.MURPHY_BED.value: "Murphy bed mechanism explanation (door/bed/counterbalance/pivot/lock sequence)",
}


# ── Public helpers (used by the thin router + future D4 fab_qa) ──────

def missing_fields_for(
    category: Category, dimensions: Optional[Dict[str, float]]
) -> List[str]:
    """Return the list of required dims that are missing for this category.

    Returns [] when the category is unknown or no dims are required.
    """
    required = REQUIRED_DIMS_BY_CATEGORY.get(category.value, [])
    if not dimensions:
        return list(required)
    return [d for d in required if d not in dimensions or dimensions[d] is None]


def is_animation_mode(output_mode: OutputMode) -> bool:
    return output_mode in (OutputMode.ANIMATED_DIAGRAM, OutputMode.VISUAL_EXPLAINER)


def has_parametric_source(
    category: Category,
    dimensions: Optional[Dict[str, float]],
    missing: List[str],
) -> bool:
    """A 'parametric source' is one with all required dims present.

    Animation / explainer outputs are REVIEW_READY when parametric, and
    CONCEPT_ONLY when not. This is the key guardrail.

    The "parametric" check is: the user supplied the required-dim set for
    their category, and there are no missing fields. This is stricter
    than a generic (width, depth, height) shortcut and matches D2 semantics.
    """
    if not dimensions:
        return False
    # If the category has no required dims, parametric is trivially True
    # when at least one dim is present.
    if not missing and dimensions:
        return True
    return False


def default_qa_status_for(
    output_mode: OutputMode,
    source_type: Optional[str],
    dimensions: Optional[Dict[str, float]],
    missing: List[str],
    category: Category,
) -> QAStatus:
    """Compute the default QA status for a request.

    Rules (per Founder direction, lowercase values; animation rules per
    the D1 Addendum and Founder's correction):

    shop_drawing:
      - missing required dims -> needs_measurements
      - all required dims present -> review_ready
      (D4 fab_qa may upgrade review_ready -> shop_ready after a 10-check
      QA pass; D2 only computes the DEFAULT.)
    sketch_analysis / concept_image / planning_help:
      - always concept_only (or n/a for planning_help via caller)
    animated_diagram / visual_explainer:
      - parametric dims present -> review_ready
      - visual source (photo/sketch/mixed) without dims -> concept_only
        (AI-only visual source, per Founder correction)
      - text source without dims -> needs_measurements
        (insufficient data, per Founder correction)
      - NEVER shop_ready (Founder guardrail, enforced here)

    Unsupported category: "unsupported".
    """
    # Guardrail: animation modes never resolve to shop_ready.
    # This is the server-side enforcement of the D1 Addendum rule.
    if is_animation_mode(output_mode):
        if has_parametric_source(category, dimensions, missing):
            return "review_ready"
        # Visual source (photo/sketch/mixed) without dims = AI-only
        # visual source. Per Founder correction: concept_only.
        if source_type in ("photo", "sketch", "mixed"):
            return "concept_only"
        # Text source without dims = insufficient data. Per Founder
        # correction: needs_measurements.
        if missing:
            return "needs_measurements"
        # No source_type and no dims: still treat as concept_only
        # (defensive: the user gave us nothing to work with).
        return "concept_only"

    if output_mode == OutputMode.SHOP_DRAWING:
        if missing:
            return "needs_measurements"
        return "review_ready"

    if output_mode in (OutputMode.SKETCH_ANALYSIS, OutputMode.CONCEPT_IMAGE):
        return "concept_only"

    if output_mode == OutputMode.PLANNING_HELP:
        # planning_help does not produce a drawing; caller treats as n/a
        return "concept_only"

    # Defensive: unknown mode -> unsupported
    return "unsupported"


def build_warnings(
    output_mode: OutputMode,
    category: Category,
    source_type: SourceType,
    has_animation_spec: bool,
) -> List[str]:
    """Compute the warnings list for a request."""
    warnings: List[str] = []
    if is_animation_mode(output_mode) and not has_animation_spec:
        hint = ANIMATION_HINT_BY_CATEGORY.get(
            category.value,
            f"{category.value} {output_mode.value} (see ANIMATION_HINT_BY_CATEGORY)",
        )
        warnings.append(
            f"Animation mode requested without an animation_spec block. "
            f"Suggested: {hint}."
        )
    if source_type in ("photo", "sketch", "mixed") and not warnings:
        # noop placeholder; future D4 may add cross-source consistency warnings
        pass
    return warnings


def supported_categories() -> List[Category]:
    return list(Category)


def animation_hint_for(category: Category) -> Optional[str]:
    return ANIMATION_HINT_BY_CATEGORY.get(category.value)


# ── D4: forward-reference rebuild ────────────────────────────────────
# DrawingIntakeResponse references FabricationQAResult (D4) which is
# defined in a separate module to avoid an import cycle. The
# forward-reference is resolved at module import time via
# model_rebuild(). This is the standard Pydantic v2 pattern.
def _d4_rebuild_response():
    try:
        from app.services.drawing.fabrication_qa import FabricationQAResult
        DrawingIntakeResponse.model_rebuild()
    except Exception:
        # If fabrication_qa is not yet importable (e.g. during early
        # boot), the rebuild is deferred. The optional field is None
        # by default and the type annotation is preserved.
        pass


_d4_rebuild_response()
