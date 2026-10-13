"""IMP-0006 — Bench colors + basketweave options doc regression test.

Pins the DRAFT reference doc (docs/BENCH_COLORS_BASKETWEAVE_OPTIONS.md) to the
real repo records it claims to be built from, so the doc cannot silently drift
from what Empire Workroom actually quotes:

- every quoted color/code in the doc must still exist in the past-quote fabric
  seed (backend/app/routers/fabrics.py::seed_ramiro_fabrics)
- every drawing option key in the doc must still exist in the drawing engine
  (backend/app/routers/drawings.py::BenchRequest + bench_renderer BenchModel)
- the doc must stay marked DRAFT until Rafael approves (approval checklist
  present, no claim of being client-approved)

Pure file-content test: no DB, no network, no clock.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "BENCH_COLORS_BASKETWEAVE_OPTIONS.md"
FABRICS_ROUTER = REPO_ROOT / "backend" / "app" / "routers" / "fabrics.py"
DRAWINGS_ROUTER = REPO_ROOT / "backend" / "app" / "routers" / "drawings.py"
BENCH_RENDERER = (
    REPO_ROOT / "backend" / "app" / "services" / "vision" / "bench_renderer.py"
)

# (fabric code, color) pairs from seed_ramiro_fabrics — the real quoted records.
QUOTED_SEAT_FABRICS = (
    ("V639", "Spruce"),
    ("V638", "Teak"),
    ("V1012", "Hazelnut"),
)
QUOTED_BACKINGS = (
    ("NCOP-64", "Neutral"),
    ("D3191", "Fawn"),
    ("D3222", "Umber"),
)

# panel_style keys supported by the drawing engine.
DRAWING_PANEL_STYLES = (
    "flat",
    "vertical_channels",
    "horizontal_channels",
    "tufted",
)


def _doc() -> str:
    assert DOC_PATH.exists(), f"options doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


# ── Doc presence + approval status ───────────────────────────────────
def test_options_doc_exists_and_is_draft():
    text = _doc()
    assert "DRAFT" in text
    assert "Rafael" in text
    assert "UNCONFIRMED" in text
    # Must not claim to be approved/client-facing while in test-copy stage.
    lowered = text.lower()
    assert "client-facing" in lowered or "not client-facing" in lowered


def test_options_doc_has_required_sections():
    text = _doc()
    assert "Bench colors" in text
    assert "Basketweave" in text
    assert "Approval checklist" in text or "approval checklist" in text
    assert "Provenance" in text


# ── Colors grounded in the past-quote fabric seed ────────────────────
def test_quoted_colors_exist_in_fabric_seed():
    seed = FABRICS_ROUTER.read_text(encoding="utf-8")
    for code, color in (*QUOTED_SEAT_FABRICS, *QUOTED_BACKINGS):
        assert code in seed, f"fabric code {code} missing from fabrics seed"
        assert color in seed, f"fabric color {color} missing from fabrics seed"


def test_doc_lists_all_quoted_colors():
    text = _doc()
    for code, color in (*QUOTED_SEAT_FABRICS, *QUOTED_BACKINGS):
        assert code in text, f"doc missing quoted fabric code {code}"
        assert color in text, f"doc missing quoted color {color}"


# ── Weave options grounded in the drawing engine ─────────────────────
def test_panel_styles_exist_in_drawing_engine():
    drawings = DRAWINGS_ROUTER.read_text(encoding="utf-8")
    renderer = BENCH_RENDERER.read_text(encoding="utf-8")
    for style in DRAWING_PANEL_STYLES:
        assert style in drawings, f"panel style {style!r} missing from drawings router"
    assert "vertical_channels" in renderer
    assert "panel_style" in renderer


def test_doc_lists_drawing_panel_styles():
    text = _doc()
    for style in DRAWING_PANEL_STYLES:
        assert style in text, f"doc missing drawing panel style {style!r}"


def test_doc_is_honest_about_missing_basketweave_record():
    """No 'basketweave' record exists in code — the doc must say so."""
    code_hits = 0
    for path in (FABRICS_ROUTER, DRAWINGS_ROUTER, BENCH_RENDERER):
        code_hits += path.read_text(encoding="utf-8").lower().count("basketweave")
    assert code_hits == 0
    text = _doc().lower()
    assert "no true" in text and "basketweave" in text
