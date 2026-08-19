"""Tests for the Document Template Engine (P1-T·b).

Per the dispatch's standing rule: "a scoped test count is never
reported as evidence for code it does not execute." These tests
exercise the NEW package — `backend/app/presentation/template/`.
They do NOT touch the existing `tests/test_drawing_vector_b2.py`
(which covers the OLD drapery drawing lane).

Coverage:
  - `spec.Address.footer_letterhead()` renders from ONE source.
  - `JobSpec.validate()` raises SpecIncomplete with the missing list.
  - `JobSpec.validate()` passes when all required fields are present.
  - `count_openings(spec)` reads SCHEDULE qtys (single derivation).
  - `count_openings(spec)` reads window-kind items from rooms (single
    derivation) — proves ONE function, two derivations, used by both
    cover and schedule. Amendment 4 fix.
  - 4 scaffold body builders (estimate, invoice, presentation_sheet,
    board) each raise SpecIncomplete with the fixture reason.
  - `content/window_openings.draw_panel()` generates SVG fragment
    for a real panel dict.

Duplication fix:
  - `panel["dim_h"]` (hand-typed string) replaced by `_fmt_in(panel["h"])`
    (formatted from float). Gate asserts equality — negative fixture
    catches a panel whose h is changed without updating its dim_h.
"""
from __future__ import annotations

import pytest

from app.presentation.template.spec import (
    Address, JobSpec, SpecIncomplete, count_openings,
)
from app.presentation.template.chrome import _fmt_in
from app.presentation.template.content.window_openings import (
    draw_panel, resolve_items,
)


# ══════════════════════ ADDRESS — single source ══════════════════════════

class TestAddressSingleSource:
    """Amendment 1: address components live ONCE in Address; the footer
    renders from the single source."""

    def test_footer_letterhead_renders_from_components(self):
        addr = Address("5124 Frolich Ln", "Hyattsville", "MD", "20781")
        assert addr.footer_letterhead() == (
            "5124 Frolich Ln  ·  Hyattsville MD 20781"
        )

    def test_changing_components_changes_footer(self):
        """Single source — one source, one output. No derivation
        in two places. Use dataclasses.replace to mutate one field
        and verify the formatted output follows — proves the output
        derives from the source, not just that the constructor
        works."""
        import dataclasses
        addr = Address("123 Main St", "Anytown", "VA", "22000")
        assert addr.footer_letterhead() == "123 Main St  ·  Anytown VA 22000"
        # Mutate via replace — frozen dataclass semantics, but the
        # output must reflect the new value because the output derives
        # from the (now-changed) source.
        addr2 = dataclasses.replace(addr, street="999 New Rd")
        assert addr2.footer_letterhead() == "999 New Rd  ·  Anytown VA 22000"
        # Original unchanged (replace is non-mutating)
        assert addr.footer_letterhead() == "123 Main St  ·  Anytown VA 22000"


# ══════════════════════ SPEC VALIDATION — structured refusal ══════════════

class TestSpecIncomplete:
    """Per P1-T·c: builders never `sys.exit(1)`. Missing fields raise
    SpecIncomplete with the EXACT list — MAX gets a structured
    refusal it can render, not a process exit it cannot orchestrate."""

    def _empty_spec(self) -> JobSpec:
        return JobSpec(
            project="", client="", client_loc="", scope="",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="", date="", source="", status="",
            document_type="", content_family="",
        )

    def test_validate_raises_with_exact_missing_list(self):
        spec = self._empty_spec()
        with pytest.raises(SpecIncomplete) as exc:
            spec.validate()
        # 11 required fields missing per the dispatch's "structured refusal"
        assert len(exc.value.missing) == 11
        # Required fields present in the list
        assert "project" in exc.value.missing
        assert "client" in exc.value.missing
        assert "address.street" in exc.value.missing
        assert "rev" in exc.value.missing
        assert "document_type" in exc.value.missing
        assert "content_family" in exc.value.missing

    def test_validate_passes_when_complete(self):
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("5124 Frolich Ln", "Hyattsville", "MD", "20781"),
            header_tagline="POWERED BY EMPIRE WORKROOM",
            footer_letterhead="",
            locale="HYATTSVILLE MD",
            rev="A", date="19 AUG 2026", source="", status="FOR DISCUSSION",
            document_type="measurement_set",
            content_family="window_openings",
        )
        # footer_letterhead not in missing_required_fields — derived
        # from address. Empty rev would fail; "A" passes.
        spec.validate()  # no exception


# ══════════════════════ AMENDMENT 4 — ONE derivation, TWO consumers ══════

class TestAmendment4CountDerivesOnce:
    """Cover and schedule both read `count_openings(spec)`. The
    McLean RevA 21-vs-22 split cannot reappear."""

    def test_schedule_path(self):
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="A", date="19 AUG 2026", source="", status="",
            document_type="measurement_set",
            content_family="window_openings",
            schedule=[("R", "M-1", 3, "43\"", "79\"", "n"),
                      ("R", "M-2", 5, "27\"", "101\"", "n")],
            rooms=[],
        )
        # 3 + 5 = 8
        assert count_openings(spec) == 8

    def test_rooms_path(self):
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="A", date="19 AUG 2026", source="", status="",
            document_type="measurement_set",
            content_family="window_openings",
            rooms=[
                {"key": "R", "name": "R", "sub": "s",
                 "panels": [
                    {"label": "P1", "w": 100, "h": 50,
                     "items": [{"kind": "window", "w": 30},
                               {"kind": "window", "w": 30},
                               {"kind": "door",   "w": 30}]},
                    {"label": "P2", "w": 100, "h": 50,
                     "items": [{"kind": "window", "w": 40}]},
                 ]},
            ],
        )
        # 2 windows in P1 + 1 window in P2 = 3 (door kind not counted)
        assert count_openings(spec) == 3

    def test_both_paths_agree(self):
        """Same spec, two derivations, one number. Amendment 4."""
        # Schedule sums 2 + 1 = 3
        spec_sched = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="A", date="19 AUG 2026", source="", status="",
            document_type="measurement_set", content_family="window_openings",
            schedule=[("R", "M-1", 3, "43\"", "79\"", "n")],
            rooms=[],
        )
        # Rooms yield 3 windows
        spec_rooms = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="A", date="19 AUG 2026", source="", status="",
            document_type="measurement_set", content_family="window_openings",
            rooms=[{"key": "R", "name": "R", "sub": "s",
                    "panels": [{"label": "P1", "w": 100, "h": 50,
                                "items": [{"kind": "window", "w": 30},
                                          {"kind": "window", "w": 30},
                                          {"kind": "window", "w": 30}]}]}],
        )
        assert count_openings(spec_sched) == count_openings(spec_rooms) == 3

    def test_g5_catches_rev_a_split(self):
        """G5 must FAIL on the McLean RevA pattern: two independent
        derivations that disagree with count_openings(spec)."""
        from app.presentation.template.gates import gate_counts
        spec_split = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="A", date="19 AUG 2026", source="", status="",
            document_type="measurement_set",
            content_family="window_openings",
            schedule=[("R", "M-1", 22, "43\"", "79\"", "n")],   # 22
            rooms=[
                {"key": "R", "name": "R", "sub": "s",
                 "panels": [{"label": "P1", "w": 100, "h": 50,
                             "items": [{"kind": "window", "w": 30}]}]}],
        )
        # count_openings(spec) prefers schedule (22) over rooms (1)
        # → 22. But rooms say 1 — G5 fails.
        failures = gate_counts(spec_split)
        assert len(failures) == 1
        assert "G5 counts disagree" in failures[0]

    def test_g5_passes_when_agree(self):
        """G5 passes when derivations agree with count_openings(spec)."""
        import dataclasses
        from app.presentation.template.gates import gate_counts
        base = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="A", date="19 AUG 2026", source="", status="",
            document_type="measurement_set",
            content_family="window_openings",
            schedule=[("R", "M-1", 3, "43\"", "79\"", "n")],
            rooms=[],
        )
        # 3 windows in rooms matches schedule qty 3
        spec_agree = dataclasses.replace(base, rooms=[
            {"key": "R", "name": "R", "sub": "s",
             "panels": [{"label": "P1", "w": 100, "h": 50,
                         "items": [{"kind": "window", "w": 30},
                                   {"kind": "window", "w": 30},
                                   {"kind": "window", "w": 30}]}]},
        ])
        failures = gate_counts(spec_agree)
        assert failures == []


# ══════════════════════ G4 LAYOUT MATH ════════════════════════════════════

class TestG4LayoutMath:
    """G4 — closure arithmetic recomputed from spec; per Amendment 2
    the build continues (WARN, not FAIL)."""

    def test_g4_warns_when_parts_disagree_with_overall(self):
        """McLean LRB center: tagged overall 222", parts 77.5+69.25+78.25=225.
        G4 reports the delta (3") as WARN — Amendment 2 says build
        continues. The gate compares TYPED dim widths (from dims_top
        end-start) against IMPLIED widths (from divisions + panel.w)."""
        from app.presentation.template.gates import gate_layout_math
        room = {
            "key": "LRB-CENTER", "name": "Living Room center wall",
            "sub": "Three windows",
            "math": "77½+69¼+78¼ = 225 vs 222 OVERALL - Δ 3\"",
            "panels": [{
                "label": "CENTER WALL", "w": 222.0, "h": 114.25,
                "divisions": [77.5, 146.75],
                "items": [],
                # TYPED dims: 77.5, 69.25, 78.25 (third is TAGGED
                # at 78¼ = 78.25, NOT implied from panel.w - 146.75
                # = 75.25). The 3" delta IS the conflict.
                "dims_top": [(0.0, 77.5, "77½\""),
                             (77.5, 146.75, "69¼\""),
                             (146.75, 225.0, "78¼\" TAGGED")],
            }],
        }
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("", "", "", ""),
            header_tagline="", footer_letterhead="", locale="",
            rev="A", date="19 AUG 2026", source="", status="",
            document_type="measurement_set", content_family="window_openings",
            rooms=[room],
        )
        results = gate_layout_math(spec)
        statuses = [s for s, _ in results]
        # WARN (not FAIL) per Amendment 2 — the build continues.
        assert "WARN" in statuses, f"expected WARN, got {results}"
        assert "FAIL" not in statuses


# ══════════════════════ SCAFFOLDS — 4 doc types refuse SpecIncomplete ═════

class TestScaffoldBodies:
    """Per the dispatch's P1-T·d: 4 doc types are SCAFFOLDS until their
    fixtures land. Each raises SpecIncomplete with the fixture reason."""

    def test_estimate_scaffold_refuses(self):
        from app.presentation.template.body import estimate
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("S", "C", "S", "Z"),
            header_tagline="T", footer_letterhead="", locale="L",
            rev="A", date="D", source="", status="",
            document_type="estimate", content_family="window_openings",
        )
        with pytest.raises(SpecIncomplete) as exc:
            estimate.build(spec)
        assert "estimate.body" in str(exc.value.missing[0])

    def test_invoice_scaffold_refuses(self):
        from app.presentation.template.body import invoice
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("S", "C", "S", "Z"),
            header_tagline="T", footer_letterhead="", locale="L",
            rev="A", date="D", source="", status="",
            document_type="invoice", content_family="window_openings",
        )
        with pytest.raises(SpecIncomplete) as exc:
            invoice.build(spec)
        assert "invoice.body" in str(exc.value.missing[0])

    def test_presentation_sheet_scaffold_refuses(self):
        from app.presentation.template.body import presentation_sheet
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("S", "C", "S", "Z"),
            header_tagline="T", footer_letterhead="", locale="L",
            rev="A", date="D", source="", status="",
            document_type="presentation_sheet",
            content_family="window_openings",
        )
        with pytest.raises(SpecIncomplete) as exc:
            presentation_sheet.build(spec)
        assert "presentation_sheet.body" in str(exc.value.missing[0])

    def test_board_scaffold_refuses(self):
        from app.presentation.template.body import board
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("S", "C", "S", "Z"),
            header_tagline="T", footer_letterhead="", locale="L",
            rev="A", date="D", source="", status="",
            document_type="board", content_family="window_openings",
        )
        with pytest.raises(SpecIncomplete) as exc:
            board.build(spec)
        # Mockup-overlay capability not in STATE/BACKLOG
        assert "board.body" in str(exc.value.missing[0])
        assert "mockup" in str(exc.value.missing[0]).lower()


# ══════════════════════ CONTENT — panel SVG generation ════════════════════

class TestContentPanel:
    """The content renderer produces SVG for a panel dict."""

    def test_draw_panel_returns_svg(self):
        panel = {
            "label": "BAY - 4 WINDOWS", "w": 108.0, "h": 110.5,
            "top_band": (4.5, "FLAT MOULDING"),
            "items": [
                {"kind": "window", "w": 27.0, "x": 0.0, "v": (106.0, 101.25)},
                {"kind": "window", "w": 27.0, "x": 27.0, "v": (106.0, 101.25)},
                {"kind": "window", "w": 27.0, "x": 54.0, "v": (106.0, 101.25)},
                {"kind": "window", "w": 27.0, "x": 81.0, "v": (106.0, 101.25)},
            ],
            "dims_top": [(0.0, 27.0, "27\""), (27.0, 54.0, "27\""),
                         (54.0, 81.0, "27\""), (81.0, 108.0, "27\"")],
            "dim_h": "110½\"",
        }
        placed = []
        svg = draw_panel(panel, 50.0, 250.0, 1.5, placed)
        assert "<svg" not in svg  # draw_panel returns fragments, not page
        assert "<rect" in svg
        assert "<line" in svg
        assert "<text" in svg
        # Amendment 5: every text bbox recorded in placed
        assert len(placed) > 0

    def test_resolve_items_distributes_untagged(self):
        """Untagged spacing distributes evenly between placed items.

        Reference logic: span = panel.w - used - free_total;
        gap = span / (len(free) + 1). Each free item placed at
        increasing gap offsets (cur += w + gap).
        """
        panel = {"w": 100.0, "items": [
            {"kind": "window", "w": 30.0},   # no x
            {"kind": "window", "w": 30.0, "x": 40.0},
            {"kind": "window", "w": 30.0},   # no x
        ]}
        items = resolve_items(panel)
        xs = [it["x"] for it in items]
        # Two free items, one at x=40.0
        # used = 30, free_total = 60, span = 10
        # gap = 10 / (2 + 1) = 3.333
        # Item 1 (first free, items[0]): x = 3.333
        # Item 2 (placed, items[1]):    x = 40.0 (unchanged)
        # Item 3 (second free, items[2]): x = 3.333 + 30 + 3.333 = 36.667
        assert xs[0] == pytest.approx(10/3, abs=1e-9)
        assert xs[1] == 40.0
        assert xs[2] == pytest.approx(10/3 + 30 + 10/3, abs=1e-9)
        # All items fit inside the panel (rightmost edge ≤ panel width)
        assert xs[2] + 30 <= 100 + 1e-9

    def test_resolve_items_no_op_when_all_tagged(self):
        panel = {"w": 100.0, "items": [
            {"kind": "window", "w": 30.0, "x": 5.0},
            {"kind": "window", "w": 30.0, "x": 35.0},
        ]}
        items = resolve_items(panel)
        assert items[0]["x"] == 5.0
        assert items[1]["x"] == 35.0


# ══════════════════════ DUPLICATION FIX — _fmt_in + dim_h gate ═══════════

class TestAmendment4DuplicationFix:
    """Per founder correction (2026-08-19): one measurement written
    three ways is the defect. The fix is INSIDE one panel — store
    ONCE as a float (panel["h"]), display strings are FORMATTED
    from it (never typed). Data rows compose from the same value.

    Cross-room agreement is NOT checked and must not be."""

    def test_fmt_in_renders_fractions(self):
        """_fmt_in formats float as canonical inches string."""
        # Whole numbers
        assert _fmt_in(99.0) == '99"'
        # Common fractions
        assert _fmt_in(110.5) == '110½"'
        assert _fmt_in(27.25) == '27¼"'
        assert _fmt_in(27.75) == '27¾"'
        # 8ths
        assert _fmt_in(105.875) == '105⅞"'

    def test_panel_dim_h_is_formatted_from_h(self):
        """Per-panel duplication fix: dim_h must equal _fmt_in(h).

        After the duplication fix (founder 2026-08-19), draw_panel
        uses _fmt_in(panel["h"]) for the vdim label — the typed
        string `panel["dim_h"]` is no longer the source. Gates.py
        G-dim-h asserts the typed string still matches the formatted
        value (catches stale typed strings).
        """
        panel = {
            "label": "TEST", "w": 100.0, "h": 110.5,
            "items": [{"kind": "window", "w": 50.0, "x": 25.0}],
            "dims_top": [],
            "dim_h": "110½\"",   # matches _fmt_in(110.5)
        }
        from app.presentation.template.gates import gate_dim_h_matches_h
        failures = gate_dim_h_matches_h([panel])
        assert failures == [], (
            f"G-dim-h gate should PASS for fresh spec; got: {failures}"
        )

    def test_gate_dim_h_catches_stale(self):
        """NEGATIVE FIXTURE: a panel whose h is changed without
        its dim_h — must FAIL the G-dim-h gate.

        Per founder correction: "Change the float and the two
        strings still print the old number. The drawing and its
        own label disagree with nothing catching it — same failure
        class as the 21/22 count."
        """
        panel = {
            "label": "STALE", "w": 100.0, "h": 110.5,
            "items": [],
            "dim_h": "99\"",   # STALE — doesn't match _fmt_in(110.5)
        }
        from app.presentation.template.gates import gate_dim_h_matches_h
        failures = gate_dim_h_matches_h([panel])
        assert len(failures) == 1
        assert "STALE" in failures[0]
        assert "110½\"" in failures[0]    # _fmt_in(110.5)
        assert "99\"" in failures[0]      # stale dim_h

    def test_gate_dim_h_catches_stale_data_row(self):
        """Per founder correction: data rows compose from the same
        value. A TYPED string data row that disagrees with _fmt_in
        (panel["h"]) must FAIL — same failure class as the dim_h
        stale case."""
        from app.presentation.template.gates import gate_dim_h_matches_h
        room = {
            "key": "STALE_DATA", "name": "Stale data room",
            "sub": "sub",
            "panels": [{"label": "P", "w": 100.0, "h": 110.5,
                        "items": []}],
            "data": [
                ("WALL HEIGHT", "99\""),   # STALE — doesn't match _fmt_in(110.5)
            ],
        }
        failures = gate_dim_h_matches_h(panels=[], rooms=[room])
        assert len(failures) == 1
        assert "WALL HEIGHT" in failures[0]
        assert "99\"" in failures[0]      # stale typed value
        assert "110½\"" in failures[0]    # expected _fmt_in(110.5)

    def test_gate_dim_h_passes_callable_data_row(self):
        """Callable data rows derive at render time — gate skips them."""
        from app.presentation.template.gates import gate_dim_h_matches_h
        from app.presentation.template.chrome import _fmt_in
        room = {
            "key": "DERIVED", "name": "Derived room",
            "sub": "sub",
            "panels": [{"label": "P", "w": 100.0, "h": 110.5,
                        "items": []}],
            "data": [
                ("WALL HEIGHT", lambda p: _fmt_in(p["h"])),
            ],
        }
        failures = gate_dim_h_matches_h(panels=[], rooms=[room])
        assert failures == []
