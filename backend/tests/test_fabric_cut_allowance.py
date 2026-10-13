"""Editable foam-thickness → fabric-allowance table. Never invent a number."""
from app.config.fabric_cut_allowance import (
    CONFIRM_WITH_RAFAEL,
    FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS,
    NEEDS_FOAM_THICKNESS,
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
