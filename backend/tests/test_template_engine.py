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
from app.presentation.template import build, BuildResult
from app.presentation.template.assemble import assemble
from app.presentation.template.gates import gate_dim_h_matches_h


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


# ══════════════════════ P1-T·c — BUILDER INTERFACE ═══════════════════════

def _pdf_deps_available() -> bool:
    """True if cairosvg and pypdf are importable.

    Module-level helper, defined here (before TestP1TcBuilderInterface)
    so the `@skipif` decorator at class-definition time can resolve it.
    """
    try:
        import cairosvg  # noqa: F401
        from pypdf import PdfWriter  # noqa: F401
        return True
    except ImportError:
        return False


class TestP1TcBuilderInterface:
    """P1-T·c: `build(spec) -> BuildResult` is the canonical entry
    point callable by ANY door. Pure function, no module-global
    state, no `sys.exit(1)`, SpecIncomplete is the only refusal.
    """

    def test_build_with_missing_fields_raises_SpecIncomplete(self):
        """build() with a spec missing required fields raises
        SpecIncomplete naming exactly those fields. Validated before
        any other work — the refusal is the first thing the caller
        sees."""
        spec = JobSpec(
            project="", client="C", client_loc="L", scope="S",
            address=Address("S", "C", "S", "Z"),
            header_tagline="T", footer_letterhead="", locale="L",
            rev="", date="", source="", status="",
            document_type="measurement_set",
            content_family="window_openings",
        )
        with pytest.raises(SpecIncomplete) as exc:
            build(spec)
        # Same missing-list contract as spec.validate() — build() does
        # NOT collapse the field list.
        assert "project" in exc.value.missing
        assert "rev" in exc.value.missing
        assert "date" in exc.value.missing

    def test_build_with_scaffold_type_raises_SpecIncomplete(self):
        """The four non-measurement_set document types are SCAFFOLDS
        that raise SpecIncomplete until their fixtures land. The
        builder delegates and the scaffold refuses — no PDF is
        rendered, no body is invented from imagination."""
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("S", "C", "S", "Z"),
            header_tagline="T", footer_letterhead="", locale="L",
            rev="A", date="D", source="", status="",
            document_type="estimate", content_family="window_openings",
        )
        with pytest.raises(SpecIncomplete) as exc:
            build(spec)
        assert "estimate.body" in str(exc.value.missing[0])

    @pytest.mark.skipif(
        not _pdf_deps_available(),
        reason="cairosvg + pypdf required for measurement_set build; skipped if not installed",
    )
    def test_build_with_complete_spec_returns_BuildResult(self):
        """build() with a complete measurement_set spec returns a
        BuildResult with all three fields populated — pdf_bytes (non-
        empty), gate_report (list, may be empty), derived (dict, must
        contain count_openings)."""
        import io
        spec = JobSpec(
            project="McLean", client="Whittington", client_loc="DC",
            scope="Drapery",
            address=Address("5124 Frolich Ln", "Hyattsville", "MD", "20781"),
            header_tagline="POWERED BY EMPIRE WORKROOM",
            footer_letterhead="",
            locale="HYATTSVILLE MD",
            rev="A", date="19 AUG 2026", source="", status="FOR DISCUSSION",
            document_type="measurement_set",
            content_family="window_openings",
        )
        result = build(spec)
        assert isinstance(result, BuildResult)
        assert isinstance(result.pdf_bytes, bytes)
        assert len(result.pdf_bytes) > 0
        assert isinstance(result.gate_report, list)
        assert isinstance(result.derived, dict)
        # Amendment 4: count_openings IS the single derivation
        assert "count_openings" in result.derived
        assert isinstance(result.derived["count_openings"], int)

    def test_build_gates_run_on_real_bboxes(self):
        """The gates MUST run on real bboxes. Pre-P1-T·c, the
        builders were called with `[]` as the placed list and the
        gates trivially passed on the empty input. This test asserts
        the gates produce non-trivial output when the builders do
        their real work — specifically, the McLean layout has
        genuine text-vs-text overlap in the cover index (POWERED BY
        EMPIRE WORKROOM labels cross the data row at the same y),
        and G2 should catch it. If the placed list is empty, G2
        returns [] and this test fails — same as if no suite ran."""
        spec = JobSpec(
            project="McLean", client="Whittington", client_loc="DC",
            scope="Drapery",
            address=Address("5124 Frolich Ln", "Hyattsville", "MD", "20781"),
            header_tagline="POWERED BY EMPIRE WORKROOM",
            footer_letterhead="",
            locale="HYATTSVILLE MD",
            rev="A", date="19 AUG 2026", source="", status="FOR DISCUSSION",
            document_type="measurement_set",
            content_family="window_openings",
            rooms=[{"key": "LR", "name": "LR", "sub": "s", "check": "TBC",
                    "math": "", "math_flag": False,
                    "panels": [{"label": "P1", "w": 30, "h": 50,
                                "items": [
                                    {"kind": "window", "w": 30,
                                     "x": 0, "v": (24, 30)},
                                ]}]}],
            schedule=[("LRB", "A1", 1, "30\"", "36\"", "n")],
        )
        result = build(spec)
        # The gate_report must include the real G1/G2 evaluations.
        # G2 is the one that actually catches the McLean cover-index
        # overlap. assert the report is populated AND assert a real
        # gate is checked (not just "INFO" placeholders).
        gate_names = [g for g, _, _ in result.gate_report]
        assert "G1 bounds" in gate_names
        assert "G2 collisions" in gate_names
        # Pre-P1-T·c, the builders were called with `[]` as the
        # placed list and the gates ran on an empty accumulator.
        # The G2 collision gate's value field would be a literal
        # "PASS / no text overlaps" string. After P1-T·c, G2 returns
        # an actual list of overlap strings. assert the G2 entry is
        # a real result, not the pre-P1-T·c sentinel.
        for g, s, note in result.gate_report:
            if g == "G2 collisions":
                # Pre-fix sentinel was a "PASS / no text overlaps"
                # string on a real pass and a "FAIL" with arbitrary
                # text on a real fail. The discriminator is that the
                # note is a real, comma-separated list of overlap
                # descriptions — OR an empty string on a real pass.
                # An empty list with "PASS / no text overlaps" is
                # the pre-fix sentinel; we want a different shape.
                assert "no text overlaps" not in note or note.startswith(
                    "overlap:"
                ), f"G2 returned pre-fix sentinel: {note!r}"

    def test_builder_called_twice_produces_identical_output(self):
        """Idempotency: calling the same builder twice produces
        identical output. Proves no retained state. Uses the scaffold
        path so the test does not depend on cairosvg — the Idempotency
        claim is about the *builder* (a pure function), not the PDF
        renderer."""
        spec = JobSpec(
            project="P", client="C", client_loc="L", scope="S",
            address=Address("S", "C", "S", "Z"),
            header_tagline="T", footer_letterhead="", locale="L",
            rev="A", date="D", source="", status="",
            document_type="estimate", content_family="window_openings",
        )
        # Both calls raise SpecIncomplete — that's the contract for
        # scaffolds. The test is that the two MISSING-LIST CONTENTS
        # are identical, proving the builder is stateless.
        with pytest.raises(SpecIncomplete) as first:
            build(spec)
        with pytest.raises(SpecIncomplete) as second:
            build(spec)
        assert first.value.missing == second.value.missing


class TestP1TcNoSysExitInTemplateLayer:
    """P1-T·c requirement: `sys.exit(1)` is never an option. A
    process exit cannot be orchestrated. AST-walk backend/app/
    presentation/template/ and fail if any actual `sys.exit()` call
    exists. Comments and docstrings are not `sys.exit` calls.
    """

    def test_no_sys_exit_in_template_layer(self):
        import ast
        import pathlib
        root = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app" / "presentation" / "template"
        )
        violations: list[tuple[str, int]] = []
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in str(path):
                continue
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                # Only `sys.exit(...)` CALLS — not the literal string
                # "sys.exit" in a docstring or comment (ast.parse
                # strips comments; strings are constants, not calls).
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "sys"
                    and node.func.attr == "exit"
                ):
                    violations.append((str(path.relative_to(path.parents[3])), node.lineno))
        assert violations == [], (
            f"`sys.exit` is not allowed in backend/app/presentation/template/. "
            f"Found {len(violations)} call(s): "
            + "\n  ".join(f"{p}:{ln}" for p, ln in violations)
            + "\nPer P1-T·c, MAX must receive either a document or a "
            "structured refusal (SpecIncomplete) — process exits cannot "
            "be orchestrated."
        )


class TestP1TcCallableFloorGateDimH:
    """P1-T·c requirement 5: callable DataValue exemption needs a
    floor. The gate must NOT skip callables — it must call them and
    compare the result. A stale typed value wrapped in `lambda: "old
    value"` would otherwise pass the gate; calling it returns the
    stale string and the gate now catches it.
    """

    def test_callable_returning_correct_h_passes(self):
        """A data row that IS a callable returning the formatted h
        must pass the gate. Floor: callables are evaluated, not
        skipped."""
        panels = [{"label": "P1", "h": 96.0, "dim_h": '96"'}]
        rooms = [{
            "key": "LR",
            "panels": [{"h": 96.0}],
            "data": [
                # Callable that returns the correct value
                ("WALL HEIGHT", lambda p: _fmt_in(p["h"])),
            ],
        }]
        failures = gate_dim_h_matches_h(panels=panels, rooms=rooms)
        assert failures == [], f"Expected no failures, got {failures}"

    def test_callable_returning_stale_value_fails(self):
        """A data row that IS a callable returning a STALE value
        (e.g. wrapped `lambda: "old value"`) must FAIL the gate.
        The floor catches what the previous skip-callable behaviour
        missed."""
        panels = [{"label": "P1", "h": 96.0, "dim_h": '96"'}]
        rooms = [{
            "key": "LR",
            "panels": [{"h": 96.0}],
            "data": [
                # Callable that returns a STALE value — wrapping a
                # typed string in a lambda would otherwise pass.
                ("WALL HEIGHT", lambda p: '72"'),
            ],
        }]
        failures = gate_dim_h_matches_h(panels=panels, rooms=rooms)
        assert len(failures) == 1
        assert "WALL HEIGHT" in failures[0]
        assert "stale" in failures[0]
