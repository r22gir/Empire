"""D2 — Drawing intake schema tests.

Pins the 6 output modes, the 3 business units, the 13 categories, and
the default_qa_status computation. Includes the 8 test cases from the
Founder approval spec (plus 1 addendum case for visual source).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.services.drawing.intake_schema import (
    AnimationSpec,
    BusinessUnit,
    Category,
    DrawingIntakeRequest,
    DrawingIntakeResponse,
    OutputMode,
    REQUIRED_DIMS_BY_CATEGORY,
    build_warnings,
    default_qa_status_for,
    is_animation_mode,
    missing_fields_for,
)


# ── T1: banquette + shop_drawing + all dims -> review_ready ──────────
def test_t1_banquette_shop_all_dims_returns_review_ready():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT,
        category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING,
        source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18},
        units="inches",
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "review_ready"
    assert missing == []
    # guardrail: shop_drawing is not an animation mode
    assert not is_animation_mode(req.output_mode)


# ── T2: bench + shop_drawing + only width -> needs_measurements ──────
def test_t2_bench_shop_width_only_returns_needs_measurements():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT,
        category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING,
        source_type="text",
        dimensions={"width": 60},
        units="inches",
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "needs_measurements"
    assert "depth" in missing
    assert "height" in missing


# ── T3: cushion + animated_diagram + all dims -> review_ready (guardrail: NOT shop_ready) ─
def test_t3_cushion_animated_all_dims_returns_review_ready():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM,
        category=Category.CUSHION,
        output_mode=OutputMode.ANIMATED_DIAGRAM,
        source_type="text",
        dimensions={"width": 20, "depth": 20, "thickness": 5},
        units="inches",
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "review_ready"
    # GUARDRAIL: animation mode must NEVER return shop_ready
    assert status != "shop_ready"
    assert is_animation_mode(req.output_mode)


# ── T4: cushion + animated_diagram + no dims (text source) -> needs_measurements ─
def test_t4_cushion_animated_text_no_dims_returns_needs_measurements():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM,
        category=Category.CUSHION,
        output_mode=OutputMode.ANIMATED_DIAGRAM,
        source_type="text",
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "needs_measurements"
    # GUARDRAIL: animation mode must NEVER return shop_ready
    assert status != "shop_ready"


# ── T4b (D1 Addendum): cushion + animated_diagram + sketch source + no dims -> concept_only ─
def test_t4b_cushion_animated_sketch_no_dims_returns_concept_only():
    """Visual source (sketch/photo/mixed) without dims = AI-only visual
    source. Per Founder correction: returns concept_only, not
    needs_measurements.
    """
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM,
        category=Category.CUSHION,
        output_mode=OutputMode.ANIMATED_DIAGRAM,
        source_type="sketch",
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "concept_only"
    # GUARDRAIL: animation mode must NEVER return shop_ready
    assert status != "shop_ready"


# ── T5: headboard + visual_explainer + dims + animation_spec -> review_ready ─
def test_t5_headboard_visual_explainer_with_animation_spec():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM,
        category=Category.HEADBOARD,
        output_mode=OutputMode.VISUAL_EXPLAINER,
        source_type="text",
        dimensions={"width": 60, "height": 50},
        units="inches",
        animation_spec=AnimationSpec(
            step_count=5, view="isometric", audience="installer"
        ),
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "review_ready"
    assert is_animation_mode(req.output_mode)
    # animation_spec was preserved
    assert req.animation_spec.step_count == 5
    assert req.animation_spec.view == "isometric"
    assert req.animation_spec.audience == "installer"
    # warning should NOT include "animation mode without animation_spec"
    warnings = build_warnings(
        req.output_mode, req.category, req.source_type,
        has_animation_spec=req.animation_spec is not None,
    )
    assert not any("without an animation_spec" in w for w in warnings)


# ── T6: bench + shop_drawing + no dims at all -> needs_measurements ──
def test_t6_bench_shop_no_dims_returns_needs_measurements():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT,
        category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING,
        source_type="text",
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "needs_measurements"
    assert "width" in missing
    assert "depth" in missing
    assert "height" in missing


# ── T7: unknown category -> pydantic 422 ─────────────────────────────
def test_t7_unknown_category_raises_validation_error():
    with pytest.raises(ValidationError):
        DrawingIntakeRequest(
            business_unit=BusinessUnit.EMPIRE_WOODCRAFT,
            category="unknown_category",  # not in the enum
            output_mode=OutputMode.SHOP_DRAWING,
            source_type="text",
        )


# ── T8: shared business_unit + banquette + shop_drawing + dims -> review_ready + warning ─
def test_t8_shared_bu_banquette_shop_with_dims():
    """shared/banquette is unusual but not an error; the system surfaces
    a warning in the response.
    """
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.SHARED,
        category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING,
        source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18},
        units="inches",
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status == "review_ready"
    # No animation mode, so no animation warning
    warnings = build_warnings(
        req.output_mode, req.category, req.source_type,
        has_animation_spec=req.animation_spec is not None,
    )
    assert not any("without an animation_spec" in w for w in warnings)


# ── Foundation: enum completeness ─────────────────────────────────────
def test_required_dims_by_category_has_all_13_categories():
    expected = {
        Category.CUSHION, Category.PILLOW, Category.UPHOLSTERY_WALL_PANEL,
        Category.HEADBOARD, Category.WINDOW_TREATMENT,
        Category.BENCH, Category.BANQUETTE, Category.SHELVING,
        Category.STORAGE_BENCH, Category.CABINET_MILLWORK,
        Category.DESK, Category.TABLE, Category.MURPHY_BED,
    }
    actual = set(Category)
    assert actual == expected


def test_output_mode_has_six_values():
    assert len(list(OutputMode)) == 6
    assert {m.value for m in OutputMode} == {
        "shop_drawing", "sketch_analysis", "concept_image",
        "planning_help", "animated_diagram", "visual_explainer",
    }


def test_business_unit_has_three_values():
    assert len(list(BusinessUnit)) == 3
    assert {b.value for b in BusinessUnit} == {
        "empire_workroom", "empire_woodcraft", "shared",
    }


# ── Guardrail: every (animation_mode, source_type, dims) combination never returns shop_ready ─
@pytest.mark.parametrize(
    "mode,source_type,dims",
    [
        (OutputMode.ANIMATED_DIAGRAM, "text", None),
        (OutputMode.ANIMATED_DIAGRAM, "text", {"width": 20}),
        (OutputMode.ANIMATED_DIAGRAM, "text", {"width": 20, "depth": 20}),
        (OutputMode.ANIMATED_DIAGRAM, "text", {"width": 20, "depth": 20, "thickness": 5}),
        (OutputMode.ANIMATED_DIAGRAM, "sketch", None),
        (OutputMode.ANIMATED_DIAGRAM, "sketch", {"width": 20, "depth": 20, "thickness": 5}),
        (OutputMode.ANIMATED_DIAGRAM, "photo", {"width": 60, "height": 50}),
        (OutputMode.ANIMATED_DIAGRAM, "mixed", None),
        (OutputMode.VISUAL_EXPLAINER, "text", None),
        (OutputMode.VISUAL_EXPLAINER, "text", {"width": 60, "height": 50}),
        (OutputMode.VISUAL_EXPLAINER, "sketch", None),
    ],
)
def test_guardrail_animation_modes_never_shop_ready(mode, source_type, dims):
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM,
        category=Category.CUSHION,
        output_mode=mode,
        source_type=source_type,
        dimensions=dims,
        units="inches" if dims else None,
    )
    missing = missing_fields_for(req.category, req.dimensions)
    status = default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, req.category
    )
    assert status != "shop_ready", (
        f"Animation mode {mode} with source_type={source_type} and "
        f"dims={dims} returned shop_ready. Guardrail violated."
    )
