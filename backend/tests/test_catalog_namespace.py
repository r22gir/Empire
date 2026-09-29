"""Catalog style namespace — (family, style) beats shared slugs.

The flat B1 registry keeps one winner per slug. Quote/catalog callers
pass family+style (or a family/style id, or a vision alias) so:

  valance box_pleat / balloon / rod_pocket  → Valance, not Drapery/Roman
  cornice arched / scalloped / serpentine   → Cornice, not Valance
  flat_roman / pinch-pleat / headboard      → the Max template slug
"""
from __future__ import annotations

import pytest


COLLISIONS = [
    # valance styles that the flat registry sends to drapery or roman
    ("valance", "box_pleat", "Valance", ("width", "drop")),
    ("valances", "inverted_box_pleat", "Valance", ("width", "drop")),
    ("valance", "balloon", "Valance", ("width", "drop")),
    ("valance", "austrian", "Valance", ("width", "drop")),
    ("valance", "london", "Valance", ("width", "drop")),
    ("valance", "rod_pocket", "Valance", ("width", "drop")),
    # cornice styles the flat registry sends to valance
    ("cornice", "arched", "Cornice", ("width", "depth", "drop")),
    ("cornices", "scalloped", "Cornice", ("width", "depth", "drop")),
    ("cornice", "serpentine", "Cornice", ("width", "depth", "drop")),
    # same slugs, the other family, still correct
    ("drapery", "box_pleat", "Drapery", ("width", "height")),
    ("drapery", "rod_pocket", "Drapery", ("width", "height")),
    ("roman", "balloon", "Roman Shades", ("width", "height")),
    ("roman_shades", "london", "Roman Shades", ("width", "height")),
    ("valance", "arched", "Valance", ("width", "drop")),
    ("valance", "scalloped", "Valance", ("width", "drop")),
    ("valance", "serpentine", "Valance", ("width", "drop")),
]


@pytest.mark.parametrize(
    "family,style,template_family,required", COLLISIONS,
)
def test_family_style_hits_the_catalog_template(
    family, style, template_family, required,
):
    from app.services.drawing.templates import get_template, resolve_catalog_style

    resolved = resolve_catalog_style(family=family, style=style)
    template = get_template(style, family=family)
    assert resolved.template_family == template_family
    assert template.family == template_family
    assert resolved.required_dims == required
    assert resolved.ambiguous_bare_slug is False


@pytest.mark.parametrize("catalog_id,template_family,product_type", [
    ("valances/box_pleat", "Valance", "box_pleat"),
    ("valances/balloon", "Valance", "balloon"),
    ("valances/rod_pocket", "Valance", "rod_pocket"),
    ("cornices/arched", "Cornice", "arched"),
    ("cornices/scalloped", "Cornice", "scalloped"),
    ("cornices/serpentine", "Cornice", "serpentine"),
    ("drapery/box_pleat", "Drapery", "box_pleat"),
    ("roman_shades/flat_fold", "Roman Shades", "flat_fold"),
    ("roman_shades/balloon", "Roman Shades", "balloon"),
])
def test_catalog_id_resolves_family_and_style(
    catalog_id, template_family, product_type,
):
    from app.services.drawing.templates import (
        family_for, get_template, resolve_catalog_style,
    )

    resolved = resolve_catalog_style(catalog_id)
    assert resolved.template_family == template_family
    assert resolved.product_type == product_type
    assert get_template(catalog_id).family == template_family
    assert family_for(catalog_id) == template_family


@pytest.mark.parametrize("bare,template_family", [
    ("box_pleat", "Drapery"),
    ("inverted_box_pleat", "Drapery"),
    ("rod_pocket", "Drapery"),
    ("balloon", "Roman Shades"),
    ("austrian", "Roman Shades"),
    ("london", "Roman Shades"),
    ("arched", "Valance"),
    ("scalloped", "Valance"),
    ("serpentine", "Valance"),
])
def test_bare_shared_slug_keeps_historical_b1_winner(bare, template_family):
    """Existing callers that pass only the slug do not change family."""
    from app.services.drawing.templates import get_template, resolve_catalog_style

    assert get_template(bare).family == template_family
    resolved = resolve_catalog_style(bare)
    assert resolved.template_family == template_family
    assert resolved.ambiguous_bare_slug is True


@pytest.mark.parametrize("alias,family,style,product_type", [
    ("flat_roman", "roman", "flat_fold", "flat_fold"),
    ("flat-roman", "roman", "flat_fold", "flat_fold"),
    ("hobbled_roman", "roman", "hobbled_teardrop", "hobbled_teardrop"),
    ("relaxed_roman", "roman", "european_relaxed", "european_relaxed"),
    ("balloon_roman", "roman", "balloon", "balloon"),
    ("london_roman", "roman", "london", "london"),
    ("tulip_roman", "roman", "tulip", "tulip"),
    ("pinch-pleat", "drapery", "pinch_pleat", "pinch_pleat"),
    ("rod-pocket", "drapery", "rod_pocket", "rod_pocket"),
    ("goblet", "drapery", "goblet_pleat", "goblet_pleat"),
    ("inverted_box", "drapery", "inverted_box_pleat", "inverted_box_pleat"),
    ("roman-shade", "roman", "flat_fold", "flat_fold"),
    ("box_pleat_valance", "valance", "box_pleat", "box_pleat"),
    ("balloon_valance", "valance", "balloon", "balloon"),
    ("rod_pocket_valance", "valance", "rod_pocket", "rod_pocket"),
    ("board_mounted_valance", "valance", "flat_board_mounted", "flat_board_mounted"),
    ("swag_jabot", "valance", "swag_and_jabot", "swag_and_jabot"),
    ("arched_cornice", "cornice", "arched", "arched"),
    ("scalloped_cornice", "cornice", "scalloped", "scalloped"),
    ("serpentine_cornice", "cornice", "serpentine", "serpentine"),
    ("straight_cornice", "cornice", "straight", "straight"),
    ("shaped_cornice", "cornice", "custom_profile", "custom_profile"),
    ("headboard", "headboard", "headboard_channel", "headboard_channel"),
    ("headboard_channel", "headboard", "headboard_channel", "headboard_channel"),
])
def test_alias_bridge_catalog_vision_max(alias, family, style, product_type):
    from app.services.drawing.templates import get_template, resolve_catalog_style

    resolved = resolve_catalog_style(alias)
    assert resolved.catalog_family == family
    assert resolved.catalog_style == style
    assert resolved.product_type == product_type
    assert resolved.ambiguous_bare_slug is False
    assert get_template(alias).family == resolved.template_family


def test_headboard_style_stays_on_channel_template():
    from app.services.drawing.templates import resolve_catalog_style
    from app.services.drawing.templates.catalog_namespace import prepare_drawing_spec

    resolved = resolve_catalog_style(family="headboard", style="wingback")
    assert resolved.catalog_style == "wingback"
    assert resolved.product_type == "headboard_channel"
    assert resolved.template_family == "Channel Headboard"
    assert resolved.required_dims == ("width", "height")

    original = {
        "family": "upholstery",
        "style": "headboard",
        "dims": {"width": 60, "height": 54},
    }
    spec, furniture = prepare_drawing_spec({
        "product_type": "FURNITURE_STYLES/headboard/rectangular",
        "dims": {"width": 62, "height": 50},
    })
    assert furniture.catalog_style == "rectangular"
    assert furniture.product_type == "headboard_channel"
    assert spec["catalog_style"] == "rectangular"
    assert spec["product_type"] == "headboard_channel"
    assert original["style"] == "headboard"

    upholstery, _ = prepare_drawing_spec(original)
    assert upholstery["product_type"] == "headboard_channel"
    assert upholstery["catalog_family"] == "headboard"
    # Caller dict is not rewritten.
    assert "catalog_family" not in original


def test_prepare_drawing_spec_does_not_mutate_caller():
    from app.services.drawing.templates.catalog_namespace import prepare_drawing_spec

    spec = {"product_type": "flat_roman", "dims": {"width": 38, "height": 64}}
    prepared, resolved = prepare_drawing_spec(spec)
    assert spec == {"product_type": "flat_roman", "dims": {"width": 38, "height": 64}}
    assert prepared["product_type"] == "flat_fold"
    assert prepared["catalog_family"] == "roman"
    assert resolved.alias_from == "flat_roman"


def test_family_style_mismatch_raises():
    from app.services.drawing.templates import resolve_catalog_style

    with pytest.raises(KeyError):
        resolve_catalog_style(family="cornice", style="box_pleat")
    with pytest.raises(KeyError):
        resolve_catalog_style(family="drapery", style="flat_roman")


def test_valance_collision_requires_drop_not_height():
    from app.services.drawing.templates import get_template

    valance = get_template("box_pleat", family="valance")
    missing = valance.validate_spec({
        "product_type": "box_pleat",
        "dims": {"width": 60, "height": 14},
    })
    assert "drop" in missing.missing_required
    assert not missing.is_complete

    ready = valance.validate_spec({
        "product_type": "box_pleat",
        "dims": {"width": 60, "drop": 14},
    })
    assert ready.is_complete
    result = valance.compute({
        "product_type": "box_pleat",
        "dims": {"width": 60, "drop": 14},
    })
    assert result.family == "Valance"
    joined = " ".join(result.assumptions)
    assert "ASSUMED" in joined
    assert "CONFIRM BEFORE FABRICATION" in joined


def test_cornice_collision_requires_depth_and_uses_cornice_sheet():
    from app.services.drawing.templates import get_template

    cornice = get_template("arched", family="cornice")
    missing = cornice.validate_spec({
        "product_type": "arched",
        "dims": {"width": 72, "drop": 12},
    })
    assert "depth" in missing.missing_required

    spec = {
        "product_type": "arched",
        "dims": {"width": 72, "depth": 6, "drop": 12},
    }
    assert cornice.validate_spec(spec).is_complete
    result = cornice.compute(spec)
    assert result.family == "Cornice"
    joined = " ".join(result.assumptions)
    assert "ASSUMED" in joined
    assert "CONFIRM BEFORE FABRICATION" in joined
    offenders = [
        ml for ml in result.layout_math
        if ml.closing_tolerance_in >= (1 / 64)
    ]
    assert not offenders


def test_render_spec_namespaced_ids_emit_pdf():
    from app.services.drawing.templates import render_spec

    valance_pdf = render_spec({
        "product_type": "valances/box_pleat",
        "dims": {"width": 60, "drop": 14},
    })
    cornice_pdf = render_spec({
        "family": "cornice",
        "style": "scalloped",
        "dims": {"width": 84, "depth": 8, "drop": 16},
    })
    assert valance_pdf[:4] == b"%PDF"
    assert cornice_pdf[:4] == b"%PDF"
    assert len(valance_pdf) > 500
    assert len(cornice_pdf) > 500


def test_unimplemented_family_still_raises_b1_keyerror():
    from app.services.drawing.templates import get_template

    with pytest.raises(KeyError) as excinfo:
        get_template("sofa")
    msg = str(excinfo.value)
    assert "sofa" in msg
    assert "Phase B1" in msg
    assert "Implemented types" in msg


def _load_drawing_intent():
    """Load drawing_intent without importing app.services.max.

    The package init pulls the AI router and Telegram bot. This module
    is pure and is the Max side of the alias bridge.
    """
    import importlib.util
    import sys
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "max" / "drawing_intent.py"
    )
    spec = importlib.util.spec_from_file_location(
        "drawing_intent_namespace_test", path,
    )
    module = importlib.util.module_from_spec(spec)
    # dataclasses on 3.12 look up the module in sys.modules while
    # the class body runs. Register it before exec.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("message,expected", [
    ("draw a valance box pleat 60 wide 14 drop", "valance/box_pleat"),
    ("balloon valance for the window", "valance/balloon"),
    ("rod pocket valance", "valance/rod_pocket"),
    ("arched cornice over the drapery", "cornice/arched"),
    ("scalloped cornice 72 wide", "cornice/scalloped"),
    ("serpentine cornice", "cornice/serpentine"),
    ("double serpentine cornice", "double_serpentine"),
    ("box pleat drapes 40 wide", "box_pleat"),
    ("flat_roman shade", "flat_fold"),
    ("pinch-pleat panels", "pinch_pleat"),
])
def test_max_style_hints_carry_family_on_collisions(message, expected):
    module = _load_drawing_intent()
    assert module._try_resolve_b1_type(message, "window") == expected


def test_namespaced_product_type_uses_family_dims():
    """length on a valance/cornice id becomes drop, and the template
    asks for that family's required keys — not the bare-slug winner."""
    module = _load_drawing_intent()
    valance = module._translate_dims_for_b1_product(
        {"width": "60", "length": "14"}, "valance/box_pleat",
    )
    assert valance.get("drop") == "14"
    assert "length" not in valance
    assert module._compute_missing_template_keys(valance, "valance/box_pleat") == []
    assert "drop" in module._compute_missing_template_keys(
        {"width": "60", "height": "14"}, "valance/box_pleat",
    )

    cornice = module._translate_dims_for_b1_product(
        {"width": "72", "length": "12"}, "cornice/arched",
    )
    assert cornice.get("drop") == "12"
    missing = module._compute_missing_template_keys(cornice, "cornice/arched")
    assert "depth" in missing
