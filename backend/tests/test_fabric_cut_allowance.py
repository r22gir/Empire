"""Editable foam-thickness → fabric-allowance table. Never invent a number."""
from app.config.fabric_cut_allowance import (
    ALLOWANCE_APPLY,
    ALLOWANCE_APPLY_CONFIRMED,
    CONFIRM_WITH_RAFAEL,
    FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS,
    NEEDS_FOAM_THICKNESS,
    fabric_dimension_in,
    lookup_fabric_allowance,
)


def test_table_rows_are_labeled_and_defaults_unconfirmed():
    assert FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS
    for row in FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS:
        assert row["foam_thickness_in"] > 0
        assert row["allowance_in"] > 0
        assert row["status"] in {CONFIRM_WITH_RAFAEL, "confirmed"}
        assert row["label"]
        if row["status"] == CONFIRM_WITH_RAFAEL:
            assert "confirm with Rafael" in row["label"]


def test_lookup_unknown_does_not_guess():
    for raw in (None, "", 0, -1, "abc"):
        result = lookup_fabric_allowance(raw)
        assert result["allowance_in"] is None
        assert result["status"] == NEEDS_FOAM_THICKNESS


def test_lookup_unlisted_thickness_does_not_interpolate():
    result = lookup_fabric_allowance(2.25)
    assert result["allowance_in"] is None
    assert result["status"] == NEEDS_FOAM_THICKNESS
    assert "do not guess" in result["label"].lower()


def test_lookup_known_thicknesses_are_not_a_single_fixed_four():
    extras = {
        row["foam_thickness_in"]: lookup_fabric_allowance(row["foam_thickness_in"])["allowance_in"]
        for row in FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS
    }
    assert len(set(extras.values())) > 1
    assert extras[2.0] != 4
    assert extras[1.0] != extras[6.0]


def test_cut_list_fabric_is_wood_plus_twice_allowance():
    from types import SimpleNamespace

    from app.services.vision.bench_cut_list import generate_cut_list

    extra = lookup_fabric_allowance(2.0)["allowance_in"]
    model = SimpleNamespace(width=96, depth=22.5, bench_type="straight", foam_thickness_in=2.0)
    cuts = generate_cut_list(model)
    wood = cuts["wood"][0]
    fabric = cuts["fabric"][0]
    assert fabric["width"] == wood["width"] + 2 * extra
    assert fabric["length"] == wood["length"] + 2 * extra
    assert fabric["size"] == '32 1/2" × 106"'
    assert "(allowance unconfirmed)" in fabric["note"]
    assert "." not in fabric["size"]


def test_allowance_applies_per_side_rafael_2026_10_14():
    assert ALLOWANCE_APPLY == "per_side"
    assert ALLOWANCE_APPLY_CONFIRMED == "2026-10-14"
    extra = lookup_fabric_allowance(2.0)["allowance_in"]
    assert extra == 5.0
    assert fabric_dimension_in(12, extra) == 22
    assert fabric_dimension_in(18, extra) == 28
    for row in FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS:
        if row["foam_thickness_in"] == 2.0:
            assert row["status"] == CONFIRM_WITH_RAFAEL
