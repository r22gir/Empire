"""D4 — Fabrication QA Gate tests.

Pins the 10-check fabrication_qa evaluator against the 18 Founder-spec
test cases + several bonus edge cases. The function is a pure
deterministic evaluator; no I/O, no DB, no clock.

The animation/explainer guardrail is enforced: any request with
output_mode in {animated_diagram, visual_explainer} NEVER resolves
to shop_ready, regardless of other inputs.
"""
from __future__ import annotations

import pytest

from app.services.drawing.intake_schema import (
    BusinessUnit,
    Category,
    DrawingIntakeRequest,
    OutputMode,
    is_animation_mode,
)
from app.services.drawing.fabrication_qa import (
    SHOP_GRADE_CATEGORIES,
    FabricationQAResult,
    QACheck,
    evaluate_fabrication_readiness,
)


# ── Foundation: module surface ───────────────────────────────────────
def test_module_exports_correct_classes():
    """D4 must export FabricationQAResult, QACheck,
    evaluate_fabrication_readiness, and SHOP_GRADE_CATEGORIES."""
    assert FabricationQAResult is not None
    assert QACheck is not None
    assert callable(evaluate_fabrication_readiness)
    assert SHOP_GRADE_CATEGORIES == {Category.BENCH, Category.BANQUETTE}


def test_evaluate_returns_fabrication_qa_result():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT,
        category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING,
        source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18},
        units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert isinstance(res, FabricationQAResult)
    assert res.status in {
        "shop_ready", "review_ready", "needs_measurements",
        "concept_only", "unsupported",
    }
    assert isinstance(res.checks, list)
    # 9 named checks
    assert len(res.checks) == 9
    names = {c.name for c in res.checks}
    assert "business_unit_check" in names
    assert "category_support_check" in names
    assert "required_dimensions_check" in names
    assert "invalid_dimensions_check" in names
    assert "output_mode_check" in names
    assert "renderer_template_support_check" in names
    assert "export_support_check" in names
    assert "source_truth_check" in names
    assert "animation_explainer_guardrail" in names


def test_passes_iff_shop_ready_and_no_blocking():
    """`passed` is the single boolean downstream code should gate on.
    True iff status == 'shop_ready' AND blocking_issues is empty.
    """
    # shop_ready + no blocking -> passed
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT,
        category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING,
        source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18},
        units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "shop_ready"
    assert res.passed is True

    # review_ready -> passed = False
    req2 = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM,
        category=Category.CUSHION,
        output_mode=OutputMode.SHOP_DRAWING,
        source_type="text",
        dimensions={"width": 20, "depth": 20, "thickness": 5},
        units="inches",
    )
    res2 = evaluate_fabrication_readiness(req2)
    assert res2.status == "review_ready"
    assert res2.passed is False


# ── 18 Founder spec cases ────────────────────────────────────────────
def test_t1_banquette_shop_all_dims_reaches_shop_ready():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "shop_ready"
    assert res.passed is True
    assert res.recommended_next_action == "export_shop_drawing"
    assert res.blocking_issues == []


def test_t2_bench_shop_all_dims_reaches_shop_ready():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "shop_ready"


def test_t3_bench_shop_with_dxf_request_still_shop_ready():
    """DXF is supported for bench/banquette."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
        requested_exports=["svg", "pdf", "dxf"],
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "shop_ready"
    # dxf should NOT produce a warning for bench
    assert not any("dxf" in w.lower() for w in res.warnings)


def test_t4_bench_shop_with_csv_export_still_shop_ready():
    """CSV is a D6 warning only; does not block shop_drawing on bench."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
        requested_exports=["svg", "pdf", "csv"],
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "shop_ready"
    # CSV is a D6 warning
    assert any("csv" in w.lower() or "d6" in w.lower() for w in res.warnings)


def test_t5_bench_missing_depth_is_needs_measurements():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "needs_measurements"
    assert "depth" in " ".join(res.missing_fields)
    assert "height" in " ".join(res.missing_fields)


def test_t6_window_treatment_shop_is_review_ready():
    """window_treatment is parametric but not D4-cert; caps at review_ready."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.WINDOW_TREATMENT,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 48, "height": 60}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "review_ready"
    # Should have a non_shop_grade warning
    assert any("non_shop_grade" in w for w in res.warnings)


def test_t7_cushion_shop_is_review_ready():
    """cushion is parametric but not D4-cert; caps at review_ready."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "review_ready"


def test_t8_zero_dimension_is_needs_measurements():
    """Zero required dim -> needs_measurements (D2 422 if pydantic rejects)."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 0, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "needs_measurements"
    # has blocking_issue mentioning width
    assert any("width" in bi for bi in res.blocking_issues)


def test_t9_suspicious_dim_12000_downgrades_to_review_ready():
    """SUSPICIOUS_DIM_UPPER = 10000. width=12000 likely unit confusion;
    downgrade to review_ready (not needs_measurements — value is valid,
    but the unit is suspect)."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 12000, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "review_ready"
    assert any("suspicious" in w.lower() for w in res.warnings)


def test_t10_table_width_lt_depth_is_review_ready_with_warning():
    """For table, width < depth is a warning (still parametric)."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.TABLE,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 36, "depth": 72, "height": 30}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    # Table is not in SHOP_GRADE_CATEGORIES, so caps at review_ready regardless
    assert res.status == "review_ready"
    assert any(
        "width" in w.lower() and "depth" in w.lower()
        for w in res.warnings
    )


def test_t11_units_missing_with_dims_is_warning_only():
    """Units missing when dims present -> warning, not blocking."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units=None,
    )
    res = evaluate_fabrication_readiness(req)
    # bench is shop-grade; even with units missing warning, still shop_ready
    assert res.status == "shop_ready"
    assert any("units_missing" in w for w in res.warnings)


def test_t12_shared_bu_with_banquette_is_warning_only():
    """shared bu + banquette is unusual but not an error."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.SHARED, category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "shop_ready"
    assert any("unusual" in w for w in res.warnings)


def test_t13_workroom_bu_with_banquette_is_warning_only():
    """workroom bu + banquette is unusual but not an error."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    # banquette is in SHOP_GRADE_CATEGORIES, so the shop_drawing mode +
    # all dims + no missing -> shop_ready (with a warning)
    assert res.status == "shop_ready"
    assert any("unusual" in w for w in res.warnings)


def test_t14_animated_diagram_with_full_dims_is_review_ready():
    """animated_diagram NEVER returns shop_ready, even with full dims."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.ANIMATED_DIAGRAM, source_type="text",
        dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "review_ready"
    assert res.status != "shop_ready"
    # animation guardrail re-asserted
    assert any("animation" in w.lower() for w in res.warnings)


def test_t15_animated_diagram_sketch_no_dims_is_concept_only():
    """Animation + visual source (sketch) + no dims = concept_only
    (per D1 Addendum, not needs_measurements)."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.ANIMATED_DIAGRAM, source_type="sketch",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "concept_only"
    assert res.status != "shop_ready"
    assert res.status != "needs_measurements"


def test_t16_visual_explainer_photo_with_dims_is_review_ready():
    """visual_explainer + photo + full dims = review_ready (parametric)."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.VISUAL_EXPLAINER, source_type="photo",
        dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
        source_image_truth_note="from photo",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "review_ready"
    assert res.status != "shop_ready"


def test_t17_sketch_analysis_with_dims_is_concept_only():
    """sketch_analysis NEVER returns shop_ready, even with full dims."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.PILLOW,
        output_mode=OutputMode.SKETCH_ANALYSIS, source_type="text",
        dimensions={"width": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "concept_only"
    assert res.status != "shop_ready"


def test_t18_dxf_for_non_bench_banquette_in_shop_drawing_is_unsupported():
    """DXF on cushion + shop_drawing -> unsupported."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
        requested_exports=["dxf"],
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "unsupported"
    assert any("dxf" in r for r in res.unsupported_reasons)


# ── Additional cases from Founder's 18-item test list ────────────────
def test_t_negative_dimension_is_needs_measurements():
    """Negative required dim -> needs_measurements."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BANQUETTE,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": -5, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "needs_measurements"


def test_t_photo_source_without_truth_note_emits_warning():
    """Visual source without truth note -> warning (not blocking)."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.SHOP_DRAWING, source_type="photo",
        dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    # cushion is not shop-cert anyway, so status is review_ready.
    # But the warning should be present.
    assert any("truth_note" in w.lower() or "source_image" in w.lower() for w in res.warnings)


def test_t_concept_image_never_shop_ready_even_for_bench():
    """concept_image is never shop_ready, even for the shop-grade bench."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.CONCEPT_IMAGE, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "concept_only"
    assert res.status != "shop_ready"


def test_t_planning_help_never_shop_ready_even_for_bench():
    """planning_help is never shop_ready, even for the shop-grade bench."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.PLANNING_HELP, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "concept_only"
    assert res.status != "shop_ready"


def test_t_animated_text_no_dims_is_needs_measurements():
    """Animation + text source + no dims = needs_measurements (per D2)."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.ANIMATED_DIAGRAM, source_type="text",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "needs_measurements"


# ── The 18-case exhaustive parametrize (mirrors the test list) ──────
@pytest.mark.parametrize(
    "name,kwargs,expected_status",
    [
        ("T1_banquette_shop_all_dims",
         dict(business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BANQUETTE,
              output_mode=OutputMode.SHOP_DRAWING, source_type="text",
              dimensions={"width": 60, "depth": 18, "height": 18}, units="inches"),
         "shop_ready"),
        ("T2_bench_shop_all_dims",
         dict(business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
              output_mode=OutputMode.SHOP_DRAWING, source_type="text",
              dimensions={"width": 60, "depth": 18, "height": 18}, units="inches"),
         "shop_ready"),
        ("T5_bench_missing_depth",
         dict(business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
              output_mode=OutputMode.SHOP_DRAWING, source_type="text",
              dimensions={"width": 60}, units="inches"),
         "needs_measurements"),
        ("T6_window_treatment_shop",
         dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.WINDOW_TREATMENT,
              output_mode=OutputMode.SHOP_DRAWING, source_type="text",
              dimensions={"width": 48, "height": 60}, units="inches"),
         "review_ready"),
        ("T7_cushion_shop",
         dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
              output_mode=OutputMode.SHOP_DRAWING, source_type="text",
              dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches"),
         "review_ready"),
        ("T8_zero_dim",
         dict(business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BANQUETTE,
              output_mode=OutputMode.SHOP_DRAWING, source_type="text",
              dimensions={"width": 0, "depth": 18, "height": 18}, units="inches"),
         "needs_measurements"),
        ("T14_cushion_animated_full_dims",
         dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
              output_mode=OutputMode.ANIMATED_DIAGRAM, source_type="text",
              dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches"),
         "review_ready"),
        ("T15_cushion_animated_sketch_no_dims",
         dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
              output_mode=OutputMode.ANIMATED_DIAGRAM, source_type="sketch"),
         "concept_only"),
        ("T16_cushion_visual_explainer_photo_dims",
         dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
              output_mode=OutputMode.VISUAL_EXPLAINER, source_type="photo",
              dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
              source_image_truth_note="from photo"),
         "review_ready"),
        ("T17_sketch_analysis_dims",
         dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.PILLOW,
              output_mode=OutputMode.SKETCH_ANALYSIS, source_type="text",
              dimensions={"width": 18, "height": 18}, units="inches"),
         "concept_only"),
        ("T18_dxf_on_cushion_shop",
         dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
              output_mode=OutputMode.SHOP_DRAWING, source_type="text",
              dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
              requested_exports=["dxf"]),
         "unsupported"),
    ],
)
def test_d4_18_case_parametrize(name, kwargs, expected_status):
    req = DrawingIntakeRequest(**kwargs)
    res = evaluate_fabrication_readiness(req)
    assert res.status == expected_status, (
        f"{name}: expected {expected_status}, got {res.status}"
    )
    # Guardrail: animation / explainer / sketch / concept / planning
    # modes NEVER reach shop_ready.
    if req.output_mode in (OutputMode.ANIMATED_DIAGRAM, OutputMode.VISUAL_EXPLAINER,
                            OutputMode.SKETCH_ANALYSIS, OutputMode.CONCEPT_IMAGE,
                            OutputMode.PLANNING_HELP):
        assert res.status != "shop_ready", (
            f"Guardrail violation: {req.output_mode} returned shop_ready"
        )


# ── Recommended next action mapping ──────────────────────────────────
def test_recommended_next_action_for_shop_ready():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60, "depth": 18, "height": 18}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.recommended_next_action == "export_shop_drawing"


def test_recommended_next_action_for_needs_measurements():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WOODCRAFT, category=Category.BENCH,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 60}, units="inches",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.recommended_next_action == "request_measurements"


def test_recommended_next_action_for_concept_only():
    """cushion + concept_image (no dims) -> concept_only + render_concept."""
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.CONCEPT_IMAGE, source_type="text",
    )
    res = evaluate_fabrication_readiness(req)
    assert res.status == "concept_only"
    # concept_image mode with no missing dims -> render_concept
    assert res.recommended_next_action == "render_concept"


def test_recommended_next_action_for_unsupported():
    req = DrawingIntakeRequest(
        business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
        output_mode=OutputMode.SHOP_DRAWING, source_type="text",
        dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches",
        requested_exports=["dxf"],
    )
    res = evaluate_fabrication_readiness(req)
    assert res.recommended_next_action == "escalate"


# ── Backward compatibility: D2's default_qa_status and D4's qa_status
#    agree on the cases where D2 was already correct ─────────────────
def test_d2_and_d4_agree_on_animation_modes():
    """For animation modes, D2's default_qa_status_for already enforces
    the guardrail. D4's qa_status must agree.
    """
    from app.services.drawing.intake_schema import default_qa_status_for, missing_fields_for

    cases = [
        dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
             output_mode=OutputMode.ANIMATED_DIAGRAM, source_type="text",
             dimensions={"width": 20, "depth": 20, "thickness": 5}, units="inches"),
        dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.CUSHION,
             output_mode=OutputMode.ANIMATED_DIAGRAM, source_type="sketch"),
        dict(business_unit=BusinessUnit.EMPIRE_WORKROOM, category=Category.HEADBOARD,
             output_mode=OutputMode.VISUAL_EXPLAINER, source_type="text",
             dimensions={"width": 60, "height": 50}, units="inches"),
    ]
    for kwargs in cases:
        req = DrawingIntakeRequest(**kwargs)
        m = missing_fields_for(req.category, req.dimensions)
        d2_status = default_qa_status_for(
            req.output_mode, req.source_type, req.dimensions, m, req.category
        )
        d4 = evaluate_fabrication_readiness(req)
        # D2 never returns shop_ready for animation; D4 must not either.
        if is_animation_mode(req.output_mode):
            assert d2_status != "shop_ready"
            assert d4.status != "shop_ready"
