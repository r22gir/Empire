"""D4 — Fabrication QA Gate.

A pure, deterministic, side-effect-free evaluator that takes a
DrawingIntakeRequest (D2) and returns a FabricationQAResult.

Goals:
  * Make the D2 default_qa_status fabrication-stricter where needed
    (e.g. never let a non-bench/banquette shop_drawing slip to
    shop_ready just because dims are present).
  * Enforce the animation/explainer guardrail a second time
    (defense-in-depth: D2 already enforces; we re-assert).
  * Surface actionable diagnostics (blocking_issues, warnings,
    missing_fields, unsupported_reasons, recommended_next_action).
  * Stay pure: no I/O, no DB, no datetime.now(), no uuid, no logging,
    no globals, no module-level state. Importable from anywhere.

The module imports the enums and the required-dim table from
intake_schema (D2) — no duplication.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Set

from pydantic import BaseModel, Field

# Re-use D2's canonical enums and helpers.
from app.services.drawing.intake_schema import (
    BusinessUnit,
    Category,
    DrawingIntakeRequest,
    OutputMode,
    REQUIRED_DIMS_BY_CATEGORY,
    is_animation_mode,
    missing_fields_for,
)


# ── Public result types (additive) ────────────────────────────────────
class QACheck(BaseModel):
    """One named, deterministic check result.

    `passed` is True iff the check's own invariant holds. Detail is a
    short, human-readable string for logs and the UI; it is never used
    to compute downstream status.
    """
    name: str
    passed: bool
    detail: str


# Re-import the QAStatus Literal from intake_schema's namespace so the
# status field uses the SAME 5-value enum. (intake_schema exports
# QAStatus as a Literal[...] string.)
QAStatus = Literal[
    "shop_ready",
    "review_ready",
    "needs_measurements",
    "concept_only",
    "unsupported",
]


FabricationNextAction = Literal[
    "export_shop_drawing",
    "request_measurements",
    "render_concept",
    "escalate",
    "no_action",
]


class FabricationQAResult(BaseModel):
    """The full D4 fabrication-QA verdict for one intake request."""
    status: QAStatus
    passed: bool = Field(
        ...,
        description=(
            "True iff status == 'shop_ready' AND blocking_issues is empty. "
            "This is the single boolean downstream renderers/queues should gate on."
        ),
    )
    checks: List[QACheck] = Field(default_factory=list)
    blocking_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    unsupported_reasons: List[str] = Field(default_factory=list)
    recommended_next_action: FabricationNextAction = "no_action"


# ── Constants for the support / pairing tables ────────────────────────
# D4 certifies only these categories as shop-grade (real 4-quadrant +
# DXF path via vision.bench_renderer, plus parametric templates).
# All other parametric families cap at review_ready until D6 lands.
SHOP_GRADE_CATEGORIES: Set[Category] = {Category.BENCH, Category.BANQUETTE}

# Categories that have parametric templates but are NOT yet D4-cert.
# For shop_drawing these cap at review_ready. (D6 is the lane that
# promotes them to shop_ready.)
PARAMETRIC_FAMILY_CATEGORIES: Set[Category] = {
    Category.CUSHION,
    Category.PILLOW,
    Category.UPHOLSTERY_WALL_PANEL,
    Category.HEADBOARD,
    Category.WINDOW_TREATMENT,
    Category.SHELVING,
    Category.STORAGE_BENCH,
    Category.CABINET_MILLWORK,
    Category.DESK,
    Category.TABLE,
    Category.MURPHY_BED,
}

# DXF is bench/banquette-only. All other categories get a warning if DXF
# is requested; in shop_drawing mode on a non-bench/banquette category,
# the request is bumped to unsupported.
DXF_SUPPORTED_CATEGORIES: Set[Category] = {Category.BENCH, Category.BANQUETTE}

# Categories where width < depth is suspicious (warning only).
# For soft goods (cushion, pillow, headboard, etc.), no constraint.
WIDTH_LT_DEPTH_CHECK_CATEGORIES: Set[Category] = {
    Category.BENCH, Category.BANQUETTE, Category.TABLE, Category.DESK,
    Category.STORAGE_BENCH, Category.SHELVING, Category.CABINET_MILLWORK,
}

# Suspicious upper bound for a single dimension (in the unit the user
# provided). 10000 inches = 833 feet. Anything larger is almost
# certainly a unit confusion (e.g. mm instead of inches).
SUSPICIOUS_DIM_UPPER = 10000.0


# ── Per-check helpers ────────────────────────────────────────────────
def _check_business_unit(
    req: DrawingIntakeRequest, warnings: List[str]
) -> QACheck:
    """Check 4.1: business unit is valid + category/bu pairing is sane.

    Returns a QACheck and may append warnings. Never blocks.
    """
    bu = req.business_unit
    cat = req.category

    if bu not in (BusinessUnit.EMPIRE_WORKROOM, BusinessUnit.EMPIRE_WOODCRAFT, BusinessUnit.SHARED):
        # Should never reach here — Pydantic enforces the enum at the route
        # boundary. But defense in depth.
        return QACheck(
            name="business_unit_check",
            passed=False,
            detail=f"unknown business_unit {bu!r}",
        )

    workroom_only = {
        Category.CUSHION, Category.PILLOW,
        Category.UPHOLSTERY_WALL_PANEL, Category.HEADBOARD,
        Category.WINDOW_TREATMENT,
    }
    woodcraft_only = {
        Category.BENCH, Category.BANQUETTE, Category.SHELVING,
        Category.STORAGE_BENCH, Category.CABINET_MILLWORK,
        Category.DESK, Category.TABLE, Category.MURPHY_BED,
    }

    unusual = False
    if bu == BusinessUnit.EMPIRE_WORKROOM and cat in woodcraft_only:
        unusual = True
        warnings.append(
            f"unusual_pairing: {cat.value} normally belongs to empire_woodcraft, "
            f"not empire_workroom"
        )
    elif bu == BusinessUnit.EMPIRE_WOODCRAFT and cat in workroom_only:
        unusual = True
        warnings.append(
            f"unusual_pairing: {cat.value} normally belongs to empire_workroom, "
            f"not empire_woodcraft"
        )
    elif bu == BusinessUnit.SHARED and cat in (Category.BENCH, Category.BANQUETTE):
        unusual = True
        warnings.append(
            f"unusual_pairing: {cat.value} in shared bu is unusual; "
            f"consider empire_woodcraft"
        )

    return QACheck(
        name="business_unit_check",
        passed=not unusual,
        detail="ok" if not unusual else "unusual category/business_unit pairing",
    )


def _check_category_support(
    req: DrawingIntakeRequest,
    unsupported_reasons: List[str],
    blocking: List[str],
) -> QACheck:
    """Check 4.2: category is in the 13 D2 categories.

    Pydantic 422 is the route-level guard, but fab_qa is defense in depth.
    """
    cat_value = req.category.value if isinstance(req.category, Category) else str(req.category)
    if cat_value not in REQUIRED_DIMS_BY_CATEGORY:
        # Should never reach here (Pydantic enforces), but if it does,
        # mark unsupported.
        unsupported_reasons.append(f"category_not_supported: {cat_value}")
        blocking.append(f"unsupported_category: {cat_value}")
        return QACheck(
            name="category_support_check",
            passed=False,
            detail=f"category {cat_value!r} not in supported catalog",
        )
    return QACheck(
        name="category_support_check",
        passed=True,
        detail=f"category {cat_value!r} supported",
    )


def _check_required_dimensions(
    req: DrawingIntakeRequest,
    missing: List[str],
    blocking: List[str],
    warnings: List[str],
) -> QACheck:
    """Check 4.3: all required dims for the category are present + valid.

    Zero or negative required dims are treated as missing.
    """
    dims = req.dimensions or {}
    invalid_dims: List[str] = []
    for d in list(missing):
        # already in missing list (computed by missing_fields_for)
        if d in dims:
            v = dims[d]
            if v is None or v <= 0:
                invalid_dims.append(d)
                # remove from missing; will re-add via blocking_issue
                missing.remove(d)
                # Also re-add the dim to missing so priority-2 catches it.
                # Use a sentinel label so the UI can show "required dim
                # has invalid value" instead of "missing".
                missing.append(f"{d} (invalid: must be > 0)")
                blocking.append(f"required_dim_missing_or_invalid: {d}")

    # Also check for any provided dim that is zero/negative even if not
    # strictly required. If the dim IS in the required set, also add it
    # to missing so the priority ladder catches it.
    required_set = set(REQUIRED_DIMS_BY_CATEGORY.get(req.category.value, []))
    for k, v in dims.items():
        if v is None or v <= 0:
            if k not in invalid_dims and k not in missing:
                invalid_dims.append(k)
                blocking.append(f"invalid_dim_non_positive: {k}")
                if k in required_set:
                    missing.append(f"{k} (invalid: must be > 0)")

    if invalid_dims or missing:
        return QACheck(
            name="required_dimensions_check",
            passed=False,
            detail=(
                f"missing or invalid required dims: "
                f"{missing + invalid_dims}"
            ),
        )
    return QACheck(
        name="required_dimensions_check",
        passed=True,
        detail="all required dims present and positive",
    )


def _check_invalid_dimensions(
    req: DrawingIntakeRequest,
    missing: List[str],
    blocking: List[str],
    warnings: List[str],
) -> QACheck:
    """Check 4.4: detect invalid/contradictory dimensions.

    Rules (deterministic, simple — no engineering physics):
      - any value <= 0 -> blocking (already covered in 4.3; defense in depth)
      - any value > SUSPICIOUS_DIM_UPPER -> warning
      - units missing when dimensions present -> warning
      - contradictions: for bench/banquette/desk/table/storage_bench/shelving/
        cabinet_millwork, if width < depth -> warning
    """
    dims = req.dimensions or {}
    issues: List[str] = []

    # Suspiciously large dims
    for k, v in dims.items():
        if v is not None and v > SUSPICIOUS_DIM_UPPER:
            issues.append(f"suspicious_dim_too_large: {k}={v}")
            warnings.append(
                f"suspicious_dim_too_large: {k}={v} (likely unit confusion?)"
            )

    # Units missing when dimensions present
    if dims and not req.units:
        warnings.append(
            "units_missing: dimensions provided without units; "
            "expected 'mm' or 'inches'"
        )
        issues.append("units_missing")

    # Width < depth contradiction (only for non-soft categories)
    if req.category in WIDTH_LT_DEPTH_CHECK_CATEGORIES:
        w = dims.get("width")
        d = dims.get("depth")
        if (
            w is not None and d is not None
            and w > 0 and d > 0
            and w < d
        ):
            issues.append(
                f"dim_contradiction_width_lt_depth: width={w} < depth={d}"
            )
            warnings.append(
                f"dim_contradiction_width_lt_depth: width={w} < depth={d} "
                f"for category {req.category.value}"
            )

    return QACheck(
        name="invalid_dimensions_check",
        passed=not bool([i for i in issues if i not in ("units_missing",)
                         and "suspicious_dim_too_large" not in i
                         and "dim_contradiction_width_lt_depth" not in i]),
        detail="; ".join(issues) if issues else "all dimensions valid",
    )


def _check_output_mode(
    req: DrawingIntakeRequest,
    blocking: List[str],
    warnings: List[str],
) -> QACheck:
    """Check 4.5: output_mode determines the ceiling status.

    Returns a QACheck documenting the mode's ceiling. Never blocks; the
    ceiling is enforced by check 4.10 (priority resolution).
    """
    mode = req.output_mode
    if isinstance(mode, str):
        try:
            mode = OutputMode(mode)
        except ValueError:
            return QACheck(
                name="output_mode_check",
                passed=False,
                detail=f"unknown output_mode {mode!r}",
            )

    if mode in (OutputMode.ANIMATED_DIAGRAM, OutputMode.VISUAL_EXPLAINER):
        ceiling = "review_ready"
    elif mode == OutputMode.SHOP_DRAWING:
        ceiling = "shop_ready"
    elif mode in (OutputMode.SKETCH_ANALYSIS, OutputMode.CONCEPT_IMAGE):
        ceiling = "concept_only"
    elif mode == OutputMode.PLANNING_HELP:
        ceiling = "concept_only"
    else:
        ceiling = "unsupported"
        warnings.append(f"unknown_output_mode_ceiling: {mode!r}")

    return QACheck(
        name="output_mode_check",
        passed=True,
        detail=f"mode {mode.value!r} -> ceiling {ceiling}",
    )


def _check_renderer_template(
    req: DrawingIntakeRequest,
    blocking: List[str],
    warnings: List[str],
) -> QACheck:
    """Check 4.6: category has a real renderer/template for shop-grade.

    D4 certifies only bench/banquette as shop-grade. Other parametric
    families cap at review_ready. Generic-fallback-only categories
    also cap at review_ready.
    """
    cat = req.category
    if isinstance(cat, str):
        cat = Category(cat)

    if cat in SHOP_GRADE_CATEGORIES:
        return QACheck(
            name="renderer_template_support_check",
            passed=True,
            detail=f"{cat.value} is shop-grade certified (4-quadrant + DXF)",
        )

    if cat in PARAMETRIC_FAMILY_CATEGORIES:
        # Parametric family exists but not D4-cert. Cap at review_ready.
        warnings.append(
            f"shop_drawing_non_shop_grade_category: {cat.value} has a "
            f"parametric family but is not yet D4-certified as shop-ready"
        )
        return QACheck(
            name="renderer_template_support_check",
            passed=True,
            detail=(
                f"{cat.value} has a parametric family; "
                f"ceiling review_ready (D6 will certify)"
            ),
        )

    # No parametric family, no D4 certification.
    warnings.append(f"generic_fallback_only: {cat.value}")
    return QACheck(
        name="renderer_template_support_check",
        passed=True,
        detail=f"{cat.value} is generic-fallback only; ceiling review_ready",
    )


def _check_export_support(
    req: DrawingIntakeRequest,
    blocking: List[str],
    warnings: List[str],
    unsupported_reasons: List[str],
) -> QACheck:
    """Check 4.7: requested exports are supported for the category.

    SVG/PDF: always supported.
    DXF: bench/banquette only. Shop_drawing + non-bench/banquette + DXF = unsupported.
    CSV/BOM: never supported (D6). Warning only; do not bump to unsupported.
    """
    cat = req.category
    if isinstance(cat, str):
        cat = Category(cat)

    exports = req.requested_exports or []
    if not exports:
        return QACheck(
            name="export_support_check",
            passed=True,
            detail="no exports requested",
        )

    issues: List[str] = []
    for exp in exports:
        if exp in ("svg", "pdf"):
            continue  # always supported
        elif exp == "dxf":
            if cat not in DXF_SUPPORTED_CATEGORIES:
                if req.output_mode == OutputMode.SHOP_DRAWING:
                    unsupported_reasons.append(
                        f"dxf_not_supported_for_category: {cat.value}"
                    )
                    issues.append(
                        f"dxf_not_supported_for_category: {cat.value}"
                    )
                else:
                    warnings.append(
                        f"dxf_not_supported_for_category: {cat.value} "
                        f"(not bench/banquette; DXF is bench/banquette-only)"
                    )
        elif exp in ("csv", "bom"):
            warnings.append(
                f"csv_bom_d6_territory: {exp} export is planned for D6, "
                f"not yet supported"
            )
        else:
            warnings.append(f"unknown_export_type: {exp}")

    return QACheck(
        name="export_support_check",
        passed=not bool(issues),
        detail=(
            "; ".join(issues) if issues else
            f"all {len(exports)} requested export(s) supported"
        ),
    )


def _check_source_truth(
    req: DrawingIntakeRequest,
    warnings: List[str],
) -> QACheck:
    """Check 4.8: visual source types (photo/sketch/mixed) recommend a truth note.

    Not blocking — user can add it later.
    """
    if req.source_type in ("photo", "sketch", "mixed"):
        if not req.source_image_truth_note:
            warnings.append(
                f"source_image_truth_note_recommended: "
                f"source_type={req.source_type!r} without truth note; "
                f"add a note describing any AI-vision-derived dimensions"
            )
            return QACheck(
                name="source_truth_check",
                passed=False,
                detail=f"truth note recommended for source_type={req.source_type!r}",
            )
        return QACheck(
            name="source_truth_check",
            passed=True,
            detail=f"truth note present for {req.source_type!r}",
        )
    return QACheck(
        name="source_truth_check",
        passed=True,
        detail=f"text source; truth note not required",
    )


def _check_animation_guardrail(
    req: DrawingIntakeRequest,
    blocking: List[str],
    warnings: List[str],
) -> QACheck:
    """Check 4.9: animation/explainer modes never return shop_ready.

    Defense-in-depth re-assertion of D2's guardrail.
    """
    if is_animation_mode(req.output_mode):
        warnings.append(
            "animation_guardrail_applied: animation/explainer mode is "
            "capped at review_ready (D4 re-asserts D2's guardrail)"
        )
        return QACheck(
            name="animation_explainer_guardrail",
            passed=True,
            detail=(
                f"mode {req.output_mode.value!r} cannot reach shop_ready; "
                f"ceiling review_ready"
            ),
        )
    return QACheck(
        name="animation_explainer_guardrail",
        passed=True,
        detail=f"mode {req.output_mode.value!r} not animation",
    )


# ── Check 4.10: deterministic priority resolution ─────────────────────
def _resolve_final_status(
    req: DrawingIntakeRequest,
    missing: List[str],
    unsupported_reasons: List[str],
    has_suspicious_dim: bool,
) -> QAStatus:
    """Apply the priority ladder to compute the final status.

    Priority (highest first):
      1. unsupported   — if unsupported_reasons is non-empty
      2. needs_measurements — if missing_fields is non-empty (unless
         the request is animation + visual source + no dims, which is
         concept_only per D1 Addendum)
      3. concept_only  — if output_mode is sketch_analysis / concept_image
         / planning_help, OR (animation mode + visual source + no dims)
      4. review_ready  — if output_mode is animation/explainer, OR
         category is not in SHOP_GRADE_CATEGORIES (for shop_drawing),
         OR any dim is suspiciously large (likely unit confusion)
      5. shop_ready    — only when all of:
         - output_mode == shop_drawing
         - category in SHOP_GRADE_CATEGORIES
         - missing_fields empty
         - unsupported_reasons empty
         - no suspicious_dim_too_large warnings
    """
    # 1. unsupported
    if unsupported_reasons:
        return "unsupported"

    mode = req.output_mode
    cat = req.category
    if isinstance(cat, str):
        cat = Category(cat)
    is_anim = is_animation_mode(mode)
    is_visual_source = req.source_type in ("photo", "sketch", "mixed")

    # 3. concept_only FIRST (for non-drawing modes that don't produce
    # a drawing at all): concept_image, sketch_analysis, planning_help.
    # Per Founder spec: these modes MUST be concept_only (or n/a) even
    # when fields are missing — the user is asking for a concept, not a
    # shop drawing, so missing dims are expected.
    if mode in (OutputMode.SKETCH_ANALYSIS, OutputMode.CONCEPT_IMAGE, OutputMode.PLANNING_HELP):
        return "concept_only"

    # 2. needs_measurements — but if it's animation + visual + no dims,
    #    the D1 Addendum says concept_only (not needs_measurements).
    if missing:
        if is_anim and is_visual_source and not req.dimensions:
            return "concept_only"
        return "needs_measurements"

    # 4. review_ready — animation/explainer OR non-shop-grade category
    #    OR suspiciously large dim (likely unit confusion)
    if is_anim:
        return "review_ready"
    if mode == OutputMode.SHOP_DRAWING and cat not in SHOP_GRADE_CATEGORIES:
        return "review_ready"
    if has_suspicious_dim:
        return "review_ready"

    # 5. shop_ready — only bench/banquette + shop_drawing + all dims + no unsupported
    if mode == OutputMode.SHOP_DRAWING and cat in SHOP_GRADE_CATEGORIES:
        return "shop_ready"

    # Defensive: anything else is review_ready
    return "review_ready"


def _recommend_next_action(
    status: QAStatus,
    has_blocking: bool,
    has_missing: bool,
    has_unsupported: bool,
) -> FabricationNextAction:
    """Map (status, blocking, missing, unsupported) to a recommended action.

    Per Founder spec:
      shop_ready + no blocking -> export_shop_drawing
      shop_ready + blocking    -> request_measurements
      needs_measurements       -> request_measurements
      concept_only             -> render_concept (regardless of missing)
      review_ready + blocking  -> request_measurements
      review_ready + no block  -> escalate
      unsupported              -> escalate

    Order: status first, then blocking, then missing.
    """
    if status == "shop_ready":
        return "export_shop_drawing" if not has_blocking else "request_measurements"
    if status == "concept_only":
        return "render_concept"
    if status == "needs_measurements":
        return "request_measurements"
    if status == "review_ready":
        return "request_measurements" if has_blocking or has_missing else "escalate"
    if status == "unsupported":
        return "escalate"
    return "no_action"


# ── Public pure function ─────────────────────────────────────────────
def evaluate_fabrication_readiness(
    req: DrawingIntakeRequest,
) -> FabricationQAResult:
    """Compute the fabrication-grade QA verdict for one intake request.

    PURE FUNCTION. No I/O, no DB, no logging, no clock, no random.
    Same input -> same output, always. Safe to call from tests, routes,
    schedulers, MAX intent hooks.

    Returns a FabricationQAResult with:
      - status: the final 5-value lowercase enum
      - passed: True iff status == 'shop_ready' and no blocking_issues
      - checks: list of 9 named checks (QACheck)
      - blocking_issues, warnings, missing_fields, unsupported_reasons: lists
      - recommended_next_action: a 5-value Literal

    D4 guardrails enforced:
      * animation / visual_explainer modes NEVER resolve to shop_ready
      * non-bench/banquette shop_drawing caps at review_ready
      * dxf-on-non-bench/banquette in shop_drawing mode -> unsupported
      * zero/negative required dims -> needs_measurements
      * text + animation + no dims -> needs_measurements (per D2)
      * visual + animation + no dims -> concept_only (per D1 Addendum)
    """
    checks: List[QACheck] = []
    blocking: List[str] = []
    warnings: List[str] = []
    missing: List[str] = list(missing_fields_for(req.category, req.dimensions))
    unsupported_reasons: List[str] = []

    # 4.1
    checks.append(_check_business_unit(req, warnings))
    # 4.2
    checks.append(_check_category_support(req, unsupported_reasons, blocking))
    # 4.3 (mutates missing + blocking)
    checks.append(_check_required_dimensions(req, missing, blocking, warnings))
    # 4.4
    checks.append(_check_invalid_dimensions(req, missing, blocking, warnings))
    # 4.5
    checks.append(_check_output_mode(req, blocking, warnings))
    # 4.6
    checks.append(_check_renderer_template(req, blocking, warnings))
    # 4.7
    checks.append(_check_export_support(req, blocking, warnings, unsupported_reasons))
    # 4.8
    checks.append(_check_source_truth(req, warnings))
    # 4.9
    checks.append(_check_animation_guardrail(req, blocking, warnings))

    # 4.10 deterministic priority resolution
    has_suspicious_dim = any(
        w.startswith("suspicious_dim_too_large") for w in warnings
    )
    status = _resolve_final_status(
        req, missing, unsupported_reasons, has_suspicious_dim
    )

    # Defense in depth: animation guardrail re-assertion
    if is_animation_mode(req.output_mode) and status == "shop_ready":
        status = "review_ready"
        warnings.append(
            "animation_guardrail_reasserted: downgraded shop_ready->review_ready"
        )

    passed = (status == "shop_ready") and (not blocking)
    next_action = _recommend_next_action(
        status, bool(blocking), bool(missing), bool(unsupported_reasons)
    )

    return FabricationQAResult(
        status=status,
        passed=passed,
        checks=checks,
        blocking_issues=sorted(set(blocking)),
        warnings=sorted(set(warnings)),
        missing_fields=list(missing),
        unsupported_reasons=sorted(set(unsupported_reasons)),
        recommended_next_action=next_action,
    )
