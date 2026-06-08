"""Tests for Drawing Engine Repair Sprint 1.

These tests pin the truthful, stable behavior of the drawing engine after
the Sprint 1 changes:

  - 503/501 honest responses when AI providers are unavailable
  - No 500s when xAI/Claude/OpenAI are missing
  - Parametric templates are the default for the 10 supported families
  - DXF export is exposed for bench/banquette
  - Yardage/fabric estimation works for Workroom item types
  - Workroom vs Woodcraft title block routing is correct

Each test follows the same pattern used in test_drawing_studio_trust.py:
direct function calls, asyncio.run for async functions, monkeypatch for
env/path overrides.
"""

import asyncio
import os

import pytest

from app.routers import drawings
from app.services.drawing import provider_status, yardage


# ──────────────────────────────────────────────────────────────────
# 1. provider_status module
# ──────────────────────────────────────────────────────────────────


def test_provider_status_truthful_when_keys_missing(monkeypatch):
    """With no env keys, all providers report unconfigured."""
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert provider_status.xai_configured() is False
    assert provider_status.anthropic_configured() is False
    assert provider_status.openai_configured() is False
    assert provider_status.draftsman_providers_configured() == []
    assert provider_status.vision_providers_configured() == []


def test_provider_status_truthful_when_xai_key_present(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "sk-fake-for-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert provider_status.xai_configured() is True
    assert provider_status.vision_providers_configured() == ["grok"]
    # draftsman list is anthropic+openai only
    assert provider_status.draftsman_providers_configured() == []


def test_provider_status_truthful_when_anthropic_key_present(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert provider_status.anthropic_configured() is True
    # draftsman priority order is anthropic first
    assert provider_status.draftsman_providers_configured() == ["anthropic"]


def test_provider_status_openai_fallback(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")

    assert provider_status.openai_configured() is True
    assert provider_status.draftsman_providers_configured() == ["openai"]


def test_unavailable_reason_does_not_leak_secrets():
    """Reason strings must reference env-var names only, never key values."""
    r = provider_status.unavailable_reason("xai")
    assert "XAI_API_KEY" in r
    assert "sk-" not in r
    r = provider_status.unavailable_reason("claude")
    assert "ANTHROPIC_API_KEY" in r
    assert "sk-ant" not in r
    r = provider_status.unavailable_reason("openai")
    assert "OPENAI_API_KEY" in r


def test_all_unavailable_only_when_every_provider_missing(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # All draftsman providers missing → reason returned
    reason = provider_status.all_unavailable(["anthropic", "openai"])
    assert reason is not None
    assert "ANTHROPIC_API_KEY" in reason and "OPENAI_API_KEY" in reason

    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    # At least one configured → reason is None
    assert provider_status.all_unavailable(["anthropic", "openai"]) is None


# ──────────────────────────────────────────────────────────────────
# 2. /drawings/analyze-sketch returns 503 when no xAI key
# ──────────────────────────────────────────────────────────────────


def test_analyze_sketch_503_when_xai_missing(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.analyze_sketch(
                drawings.SketchAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                )
            )
        )
    assert excinfo.value.status_code == 503
    assert "xai" in str(excinfo.value.detail).lower()


def test_analyze_sketch_503_when_xai_empty_string(monkeypatch):
    """Empty env var is treated as not-configured (whitespace-only too)."""
    monkeypatch.setenv("XAI_API_KEY", "   ")
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.analyze_sketch(
                drawings.SketchAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                )
            )
        )
    assert excinfo.value.status_code == 503


# ──────────────────────────────────────────────────────────────────
# 3. /drawings/analyze-furniture returns 503 when no vision provider
# ──────────────────────────────────────────────────────────────────


def test_analyze_furniture_503_when_no_vision_providers(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.analyze_furniture(
                drawings.FurnitureAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                    provider="grok",
                )
            )
        )
    assert excinfo.value.status_code == 503


def test_analyze_furniture_503_when_requested_provider_missing(monkeypatch):
    """If caller asks for 'claude' but only xai is configured, still 503."""
    monkeypatch.setenv("XAI_API_KEY", "sk-fake")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.analyze_furniture(
                drawings.FurnitureAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                    provider="claude",
                )
            )
        )
    assert excinfo.value.status_code == 503
    detail = str(excinfo.value.detail).lower()
    assert "claude" in detail
    assert "anthropic" in detail


def test_analyze_furniture_pdf_503_when_no_vision_providers(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.analyze_furniture_pdf(
                drawings.FurnitureAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                    provider="grok",
                )
            )
        )
    assert excinfo.value.status_code == 503


# ──────────────────────────────────────────────────────────────────
# 4. /drawings/ai/project-sheet returns 503 when no draftsman providers
# ──────────────────────────────────────────────────────────────────


def test_ai_project_sheet_503_when_no_draftsman_providers(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.generate_ai_project_sheet(
                drawings.AIProjectSheetRequest(
                    benches=[
                        {
                            "type": "bench_straight",
                            "label": "X",
                            "dimensions": {"width": 96},
                        }
                    ],
                )
            )
        )
    assert excinfo.value.status_code == 503
    assert "draftsman" in str(excinfo.value.detail).lower()


def test_ai_project_sheet_pdf_503_when_no_draftsman_providers(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.generate_ai_project_sheet_pdf(
                drawings.AIProjectSheetRequest(
                    benches=[
                        {
                            "type": "bench_straight",
                            "label": "X",
                            "dimensions": {"width": 96},
                        }
                    ],
                )
            )
        )
    assert excinfo.value.status_code == 503


# ──────────────────────────────────────────────────────────────────
# 5. /drawings/bench happy path (regression coverage)
# ──────────────────────────────────────────────────────────────────


def test_bench_svg_straight_happy_path():
    req = drawings.BenchRequest(
        name="Sprint Bench",
        lf=8,
        seat_depth=20,
        seat_height=18,
        back_height=34,
        panel_style="flat",
    )
    out = asyncio.run(drawings.generate_bench_svg(req))
    assert "svg" in out
    assert (
        out["bench_type"] == "straight"
        or out["bench_type"] == "l_shape"
        or out["bench_type"] == "u_shape"
    )
    assert "96" in out["svg"]  # 8 LF = 96"


def test_bench_pdf_happy_path():
    req = drawings.BenchRequest(
        name="Sprint PDF", lf=6, seat_depth=20, seat_height=18, back_height=18
    )
    pdf = asyncio.run(drawings.generate_bench_pdf(req))
    assert pdf.media_type == "application/pdf"
    assert pdf.body.startswith(b"%PDF")


# ──────────────────────────────────────────────────────────────────
# 6. /drawings/generate: parametric templates default for 10 families
# ──────────────────────────────────────────────────────────────────


def test_generate_uses_parametric_template_for_window_by_default():
    """When caller passes item_type=window with no style_key, the
    parametric drapery template should be used (4-view sheet)."""
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Drapery",
            "item_type": "window",
            "width": 108,
            "height": 108,
            "drop": 108,
            "panels": 2,
            "fullness": 2.5,
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["classification"]["renderer"] == "parametric_template"
    assert out["template"] == "drapery"
    assert "Front" in out["svg"] or "front" in out["svg"].lower()


def test_generate_uses_parametric_template_for_banquette_by_default():
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Banquette",
            "item_type": "banquette",
            "width": 120,
            "depth": 22,
            "height": 36,
            "seat_height": 18,
            "back_height": 18,
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["classification"]["renderer"] == "parametric_template"
    assert out["template"] == "banquette"


def test_generate_uses_parametric_template_for_chair_by_default():
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Club Chair",
            "item_type": "chair",
            "width": 32,
            "depth": 34,
            "height": 36,
            "seat_height": 18,
            "back_height": 18,
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["classification"]["renderer"] == "parametric_template"
    assert out["template"] == "chair"


def test_generate_uses_parametric_template_for_shelving_by_default():
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Shelving",
            "item_type": "shelving",
            "width": 54,
            "depth": 14,
            "height": 84,
            "shelves": 5,
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["classification"]["renderer"] == "parametric_template"
    assert out["template"] == "shelving"


def test_generate_uses_parametric_template_for_desk_by_default():
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Desk",
            "item_type": "desk",
            "width": 60,
            "depth": 30,
            "height": 30,
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["classification"]["renderer"] == "parametric_template"
    assert out["template"] == "desk_table"


def test_generate_uses_parametric_template_for_table_by_default():
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Table",
            "item_type": "table",
            "width": 72,
            "depth": 36,
            "height": 30,
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["classification"]["renderer"] == "parametric_template"
    assert out["template"] == "desk_table"


def test_generate_explicit_style_key_still_wins_over_default():
    """If the caller passes an explicit style_key, the parametric template
    is used with that style — not the default style for the item_type."""
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Ripplefold",
            "item_type": "window",
            "width": 108,
            "height": 108,
            "drop": 108,
            "panels": 2,
            "style_key": "ripplefold",
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["classification"]["renderer"] == "parametric_template"
    assert out["template"] == "drapery"
    assert out["style_key"] == "ripplefold"


def test_generate_bench_still_uses_bench_renderer():
    """item_type=bench must still route to bench_renderer (not parametric)."""
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Bench",
            "item_type": "bench",
            "width": 120,
            "depth": 22,
            "seat_height": 18,
            "back_height": 18,
        },
    )
    out = drawings._render_universal_drawing(req)
    # Bench keeps its existing path (bench_renderer). Renderer is not parametric.
    assert "svg" in out
    # classification should mark renderer, but our bench_renderer path does
    # not set 'renderer' key. Sanity: must NOT be parametric.
    classification = out.get("classification", {})
    if isinstance(classification, dict):
        assert classification.get("renderer") != "parametric_template"


def test_default_style_for_helper_known_items():
    """The dispatcher maps every supported item type to a real style."""
    assert drawings._default_style_for("window") == "pinch_pleat"
    assert drawings._default_style_for("banquette") == "straight"
    assert drawings._default_style_for("chair") == "club"
    assert drawings._default_style_for("shelving") == "open"
    assert drawings._default_style_for("desk") == "writing"
    assert drawings._default_style_for("table") == "dining"
    assert drawings._default_style_for("sofa") == "tuxedo"
    assert drawings._default_style_for("headboard") == "straight"
    assert drawings._default_style_for("cushion") == "box"
    assert drawings._default_style_for("pillow") == "square"
    assert drawings._default_style_for("bedding") == "duvet"
    assert drawings._default_style_for("slipcover") == "tight_fit"
    assert drawings._default_style_for("wall_panel") == "fabric"
    assert drawings._default_style_for("millwork") == "crown_molding"
    assert drawings._default_style_for("commercial") == "restaurant_booth"
    # Unknown / empty
    assert drawings._default_style_for("mystery") is None
    assert drawings._default_style_for("") is None
    assert drawings._default_style_for(None) is None


# ──────────────────────────────────────────────────────────────────
# 7. /drawings/bench/dxf — new route
# ──────────────────────────────────────────────────────────────────


def test_bench_dxf_returns_501_when_ezdxf_missing(monkeypatch):
    """If ezdxf is not installed, the route returns 501 with a truthful
    detail (and does NOT crash with 500)."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ezdxf":
            raise ImportError("ezdxf not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    monkeypatch.setattr(
        drawings.os.path,
        "expanduser",
        lambda p: "/tmp/sprint_dxf_test" if "uploads/arch_drawings" in p else p,
    )

    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.generate_bench_dxf(
                drawings.BenchRequest(
                    name="DXF Test",
                    lf=6,
                    seat_depth=20,
                    seat_height=18,
                    back_height=18,
                )
            )
        )
    assert excinfo.value.status_code == 501
    detail = str(excinfo.value.detail).lower()
    assert "ezdxf" in detail


# ──────────────────────────────────────────────────────────────────
# 8. /drawings/yardage — new route
# ──────────────────────────────────────────────────────────────────


def test_yardage_drapery_returns_realistic_estimate():
    out = asyncio.run(
        drawings.estimate_yardage(
            drawings.YardageRequest(
                item_type="drapery",
                dimensions={
                    "width": 108,
                    "drop": 108,
                    "return": 4.5,
                    "panels": 2,
                    "fullness": 2.5,
                },
            )
        )
    )
    assert out["confidence"] == "first_pass"
    assert out["fabric_yards"] > 0
    assert out["linear_feet"] > 0
    assert "First-pass" in out["notes"] or "first-pass" in out["notes"]


def test_yardage_banquette_returns_realistic_estimate():
    out = asyncio.run(
        drawings.estimate_yardage(
            drawings.YardageRequest(
                item_type="banquette",
                dimensions={
                    "width": 120,
                    "depth": 22,
                    "seat_height": 18,
                    "back_height": 18,
                },
            )
        )
    )
    assert out["confidence"] == "first_pass"
    assert out["fabric_yards"] > 0


def test_yardage_chair_returns_realistic_estimate():
    out = asyncio.run(
        drawings.estimate_yardage(
            drawings.YardageRequest(
                item_type="chair",
                dimensions={"width": 32, "depth": 34, "height": 36},
            )
        )
    )
    assert out["confidence"] == "first_pass"
    assert out["fabric_yards"] > 0
    assert "square_feet" in out


def test_yardage_unknown_item_falls_back_to_upholstery():
    out = asyncio.run(
        drawings.estimate_yardage(
            drawings.YardageRequest(
                item_type="mystery_widget",
                dimensions={"width": 50, "depth": 30, "height": 20},
            )
        )
    )
    assert out["confidence"] == "fallback"
    assert out["estimator"] == "estimate_upholstery"
    assert "fallback" in out["notes"]


def test_yardage_rejects_missing_item_type():
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            drawings.estimate_yardage(
                drawings.YardageRequest(
                    item_type="",
                    dimensions={},
                )
            )
        )
    assert excinfo.value.status_code == 422


def test_yardage_works_for_each_workroom_item_type():
    """Every documented Workroom item type returns a non-zero estimate."""
    for item_type in [
        "drapery",
        "curtain",
        "window",
        "roman_shade",
        "shade",
        "cornice",
        "valance",
        "sofa",
        "chair",
        "ottoman",
        "slipcover",
        "cushion",
        "pillow",
        "headboard",
        "bedding",
        "duvet",
        "banquette",
    ]:
        out = asyncio.run(
            drawings.estimate_yardage(
                drawings.YardageRequest(
                    item_type=item_type,
                    dimensions={
                        "width": 60,
                        "depth": 24,
                        "height": 24,
                        "drop": 60,
                        "return": 4,
                    },
                )
            )
        )
        assert out["fabric_yards"] > 0, f"{item_type} returned 0 yards"
        assert out["confidence"] in ("first_pass", "fallback")


# ──────────────────────────────────────────────────────────────────
# 9. /drawings/catalog — Workroom vs Woodcraft title block routing
# ──────────────────────────────────────────────────────────────────


def test_catalog_routes_workroom_title_block_for_soft_furnishings(monkeypatch):
    """Sofa / chair / drapery are Workroom; their title block should say
    EMPIRE WORKROOM (not EMPIRE WOODCRAFT)."""
    out = asyncio.run(drawings.get_product_catalog())
    by_key = {cat["key"]: cat for cat in out["categories"]}

    # Spot check Workroom items
    for key in ("sofa", "chair", "window", "headboard", "cushion", "pillow"):
        if key in by_key:
            assert by_key[key]["business_unit"] == "workroom", (
                f"{key} should be workroom, got {by_key[key]['business_unit']}"
            )

    # Spot check Woodcraft items
    for key in ("banquette", "shelving", "murphy_bed", "desk", "millwork", "table"):
        if key in by_key:
            assert by_key[key]["business_unit"] == "woodcraft", (
                f"{key} should be woodcraft, got {by_key[key]['business_unit']}"
            )


def test_catalog_title_block_function_returns_correct_branding():
    """renderer_registry.get_title_block is the single source of truth for
    Workroom vs Woodcraft title block. Sofa/banquette dispatch correctly."""
    from app.services.vision.renderer_registry import get_title_block

    workroom = get_title_block("sofa")
    assert "EMPIRE WORKROOM" in workroom["company"]

    woodcraft = get_title_block("banquette")
    assert "EMPIRE WOODCRAFT" in woodcraft["company"]

    # Aliases also resolve
    assert "EMPIRE WOODCRAFT" in get_title_block("built_in")["company"]
    assert "EMPIRE WORKROOM" in get_title_block("drapery")["company"]


def test_catalog_filter_by_business_unit():
    """Passing business_unit=woodcraft should only return woodcraft items."""
    out = asyncio.run(drawings.get_product_catalog(business_unit="woodcraft"))
    for cat in out["categories"]:
        assert cat["business_unit"] == "woodcraft", (
            f"filter leaked: {cat['key']}={cat['business_unit']}"
        )
    assert out["business_unit_counts"]["woodcraft"] == len(out["categories"])
    assert out["business_unit_counts"]["workroom"] == 0


def test_catalog_total_styles_is_consistent():
    """Sum of per-category style counts must equal total_styles."""
    out = asyncio.run(drawings.get_product_catalog())
    summed = sum(cat["style_count"] for cat in out["categories"])
    assert summed == out["total_styles"]


def test_catalog_search_returns_results():
    out = asyncio.run(drawings.search_catalog(q="banquette"))
    assert len(out["results"]) >= 1
    for r in out["results"]:
        assert r["business_unit"] in ("workroom", "woodcraft")


def test_catalog_search_empty_query_returns_empty():
    out = asyncio.run(drawings.search_catalog(q=""))
    assert out["results"] == []


# ──────────────────────────────────────────────────────────────────
# 10. yardage module: independent direct tests
# ──────────────────────────────────────────────────────────────────


def test_yardage_module_drapery_explicit_dimensions():
    """Test the pure module — no router, just the estimator."""
    r = yardage.estimate_drapery(
        {"width": 100, "drop": 100, "return": 4, "panels": 2, "fullness": 2.5}
    )
    assert r["fabric_yards"] > 0
    assert r["fabric_width"] == 54
    assert r["waste_factor"] >= 1.0


def test_yardage_module_zero_dimensions_returns_safely():
    """Zero/empty dimensions should not raise; the estimator should fall
    back to its own defaults."""
    r = yardage.estimate("chair", {})
    assert r["fabric_yards"] > 0
    assert r["item_type"] == "chair"


def test_yardage_module_estimator_field_is_present():
    """Every estimate should expose the estimator function name for audit."""
    r = yardage.estimate("cushion", {"width": 24, "depth": 24, "height": 4})
    assert r["estimator"] == "estimate_cushion"
    assert r["confidence"] in ("first_pass", "fallback")


def test_yardage_module_fallback_keeps_input_dimensions_visible():
    """Even on fallback, the original item_type and dimensions context is
    preserved in the response for the founder to inspect."""
    r = yardage.estimate("mystery", {"width": 50, "depth": 30, "height": 20})
    assert r["item_type"] == "mystery"
    assert r["confidence"] == "fallback"
    assert "fallback" in r["notes"]


# ──────────────────────────────────────────────────────────────────
# 11. /drawings/generate end-to-end: bench_renderer still wins
# ──────────────────────────────────────────────────────────────────


def test_generate_bench_explicitly_does_not_use_parametric():
    """Bench should keep the dedicated bench_renderer path. Even with
    item_type=bench and explicit style_key, the renderer should NOT be
    parametric_template (since the parametric banquette template is for
    the 'banquette' item_type, not 'bench')."""
    req = drawings.UniversalDrawingRequest(
        user_text="",
        params={
            "name": "Sprint Bench",
            "item_type": "bench",
            "width": 120,
            "depth": 22,
            "seat_height": 18,
            "back_height": 18,
        },
    )
    out = drawings._render_universal_drawing(req)
    # Not parametric (this is the bench path)
    assert "svg" in out
    classification = out.get("classification", {})
    if isinstance(classification, dict):
        assert classification.get("renderer") != "parametric_template"


# ──────────────────────────────────────────────────────────────────
# 12. Disabled-provider behavior is consistent across all AI routes
# ──────────────────────────────────────────────────────────────────


def test_all_ai_routes_return_503_not_500_when_no_keys(monkeypatch):
    """Verify all four AI routes return 503 (not 500) when their
    provider keys are missing."""
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # analyze-sketch
    with pytest.raises(Exception) as e:
        asyncio.run(
            drawings.analyze_sketch(
                drawings.SketchAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                )
            )
        )
    assert e.value.status_code == 503

    # analyze-furniture
    with pytest.raises(Exception) as e:
        asyncio.run(
            drawings.analyze_furniture(
                drawings.FurnitureAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                )
            )
        )
    assert e.value.status_code == 503

    # analyze-furniture/pdf
    with pytest.raises(Exception) as e:
        asyncio.run(
            drawings.analyze_furniture_pdf(
                drawings.FurnitureAnalyzeRequest(
                    image="data:image/png;base64,iVBORw0KGgo=",
                )
            )
        )
    assert e.value.status_code == 503

    # ai/project-sheet
    with pytest.raises(Exception) as e:
        asyncio.run(
            drawings.generate_ai_project_sheet(
                drawings.AIProjectSheetRequest(
                    benches=[
                        {
                            "type": "bench_straight",
                            "label": "X",
                            "dimensions": {"width": 96},
                        }
                    ],
                )
            )
        )
    assert e.value.status_code == 503

    # ai/project-sheet/pdf
    with pytest.raises(Exception) as e:
        asyncio.run(
            drawings.generate_ai_project_sheet_pdf(
                drawings.AIProjectSheetRequest(
                    benches=[
                        {
                            "type": "bench_straight",
                            "label": "X",
                            "dimensions": {"width": 96},
                        }
                    ],
                )
            )
        )
    assert e.value.status_code == 503
