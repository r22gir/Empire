"""templates/b2_qc.py — geometric QC gates for B2 vector renderers.

HOTFIX B2b (2026-07-24) — MANDATORY test upgrade per directive.

The pre-B2b tests asserted on COUNTS and STRING PRESENCE only —
20 lines all drawn at the same coordinates still counts as 20. The
founder live-verified the broken output as "a BLANK page with all
content collapsed into an overlapping pile at the bottom-left
corner" — exactly the defect class a count-based test would miss.

QC gates (run for EVERY family renderer in the B2 rollout):

  (a) Element-spread gate: the drawing's vector bounding box
      must span ≥ 40% of page width AND ≥ 40% of page height;
      no more than 20% of elements may share near-identical
      coordinates (within 0.05" of each other — a "pile" sign).
  (b) Zone gates: title-block text lives in the right column
      (x ≥ 6.5"); drawing elements live in the left half
      (x ≤ 6.5"); nothing below the page-margin line.
  (c) Text-collision gate: word-bbox overlap between different
      lines > 30% intersection = FAIL. Catches the "every char
      at the same (x, y)" pile.

The QC helper is family-agnostic: every B2 vector renderer
passes its rendered Canvas + page dims + family name to
`enforce_b2_qc`, and the helper runs all three gates. A
family that fails any gate breaks the build.

Doctrine (B2): a test that verifies a weaker property than the
requirement is a defect class. count() and in-string checks
were the pre-B2b pattern; the QC gates are now the floor.
"""
from __future__ import annotations

import re
from typing import List, Tuple

import pdfplumber

# Import the renderer's layout constants so the scale-truth + fold-
# stack gates measure the same coordinate frames the renderer drew.
from app.services.drawing.templates.b2_renderers import (
    FRONT_X_IN, FRONT_Y_IN, FRONT_W_IN, FRONT_H_IN,
    SIDE_X_IN, SIDE_Y_IN, SIDE_W_IN, SIDE_H_IN,
    TITLE_X_IN, TITLE_Y_IN, TITLE_W_IN, TITLE_H_IN,
    N_SLATS_DEFAULT,
)


# ── Page geometry constants (landscape letter, in inches) ─────────
# Re-mapped for B2d+ golden v10 layout. The golden v10 reference
# is the binding sheet standard (per CLAUDE.md "B2 sheet standard =
# the golden reference"); the B2d-era B2c layout assumptions (margin
# 0.5", title-block x≥6.5") are SUPERSEDED.
PAGE_W_IN = 11.0
PAGE_H_IN = 8.5
MARGIN_IN = 0.32                # golden v10: 0.32" (was B2d 0.5")
HEADER_BAND_H_IN = 0.92         # golden v10: 0.92" (was B2d 1.4")
FOOTER_BAND_H_IN = 0.42         # golden v10: 0.42" (was B2d 0.5")
TITLE_X_IN_MIN = 7.90            # golden v10: title column starts at
                                  # MARGIN + 0.18 + 4.55 + 0.14 + (col_r - v2x)
                                  # ≈ 7.90. Title block now flanks the
                                  # side section, not below it.
TITLE_W_IN_MIN = 2.40            # title column must be wide enough
                                  # to hold "DIMENSIONS" label + value

# Tolerance for "near-identical coordinates" (the pile test).
COORD_TOL_IN = 0.05

# Text-collision threshold: words from different lines with bbox
# intersection > 50% of the smaller bbox are an overlap fault.
TEXT_OVERLAP_THRESHOLD = 0.50

# Element-spread thresholds (the "drawing must fill the page" test).
SPREAD_X_MIN_FRAC = 0.40
SPREAD_Y_MIN_FRAC = 0.40
PILE_FRAC_MAX = 0.20  # at most 20% of elements may be in the pile

# New B2d+ rule (learned building the golden v10 reference):
# "same-baseline overlap" — two horizontal lines (or label baselines)
# sharing the same y (within 2pt) with > 0.5" of x overlap, drawn by
# different draw calls, indicates one label was meant to replace the
# other and the second one was forgotten (or both fire on the same
# element). Catches dim-line label collisions that the old
# text-collision gate (per-word) couldn't see.
SAME_BASELINE_Y_TOL_PT = 2.0    # 2pt tolerance for "same baseline"
SAME_BASELINE_X_OVERLAP_MIN_IN = 0.50  # 0.5" of x overlap

# New B2d+ rule: "column overflow" — no rendered text may extend
# past the inner border of the column / viewport it belongs to.
# Catches layout regressions where a long title row or assumption
# bullet exceeds the column width (the B2d row-gap tuning
# occasionally overran for long fabric-mill names like
# "GP&J Baker BP10814-2 54" W · 35.46" V-repeat").
COLUMN_OVERFLOW_TOL_PT = 1.0     # 1pt tolerance for "inside border"


# Public exception
class B2QCFailure(AssertionError):
    """Raised by enforce_b2_qc when the rendered PDF fails one of
    the geometric gates. Subclass of AssertionError so test
    frameworks surface it clearly."""


def _points_to_inches(pdf_value: float) -> float:
    """ReportLab canvas default unit is points (1/72 inch).
    pdfplumber reports raw points. Convert."""
    return pdf_value / 72.0


def _top_to_bl_in(top_pts: float, page_h_in: float = 8.5) -> float:
    """pdfplumber's `top` is in PDF points from the page TOP. Convert
    to inches from the page BOTTOM (the Canvas coord system)."""
    return page_h_in - (top_pts / 72.0)


def _y0_to_bl_in(y0_pts: float, page_h_in: float = 8.5) -> float:
    """pdfplumber's `y0` is in PDF BL-coord points (from the page
    bottom). Convert to inches from the page BOTTOM (the Canvas
    coord system)."""
    return y0_pts / 72.0


def _bbox_of_lines_rects(page) -> Tuple[float, float, float, float]:
    """Bounding box (in inches, BL origin) of all lines + rects
    on a page. Excludes the giant page-frame rect (the outer
    border at 0.25"-from-page) so the spread test measures the
    DRAWING content, not the page edge."""
    all_x, all_y = [], []
    for r in page.rects:
        # Exclude the page frame (the only rect wider than 9" and
        # taller than 7"). A future-proof check: also exclude any
        # rect at the page boundary (x0<0.5", y0<0.5", x1>10.5",
        # y1>8").
        if (r['x0'] < _P_in(MARGIN_IN) - 0.1
                or r['y0'] < _P_in(MARGIN_IN) - 0.1
                or r['x1'] > _P_in(PAGE_W_IN - MARGIN_IN) + 0.1
                or r['y1'] > _P_in(PAGE_H_IN - MARGIN_IN) + 0.1):
            continue
        all_x.extend([r['x0'], r['x1']])
        all_y.extend([r['y0'], r['y1']])
    for l in page.lines:
        all_x.extend([l['x0'], l['x1']])
        all_y.extend([l['y0'], l['y1']])
    if not all_x or not all_y:
        return (0, 0, 0, 0)
    return (
        _points_to_inches(min(all_x)),
        _points_to_inches(min(all_y)),
        _points_to_inches(max(all_x)),
        _points_to_inches(max(all_y)),
    )


def _P_in(inches: float) -> float:
    """Inches to points (for the page-frame exclusion test)."""
    return inches * 72.0


# ── viewport_frame named category (HOTFIX B2d) ──────────────────────
#
# B2d directive: "Frame lines of viewports are BORDERS: exempt them
# from text-over-geometry as a named category (viewport_frame), not
# by raising thresholds globally."
#
# Implementation: viewport frames are drawn as 4 LINES (one per
# edge) rather than a single `c.rect(stroke=1)`. The text-over-
# geometry gate below checks ONLY rects (not lines), so viewport
# frames are exempt by virtue of being lines. The named category
# `viewport_frame` documents this convention; if a future renderer
# switches a viewport frame to a single stroke=1 rect, that rect
# must either be drawn as a LINE+LINE+LINE+LINE, or carry an
# explicit viewport_frame marker that this gate honors.
#
# Why not raise the threshold globally? The text-over-geometry
# gate is the B2c (6) gate that catches LAYOUT MATH / NOTES
# overprinting the shade outline — the exact defect class it was
# authored for. Raising the threshold would re-introduce that
# defect class on the bad fixtures (test_text_over_geometry_gate_
# catches_text_inside_rect still expects to FAIL). Exempt by
# category instead — see `_is_viewport_frame`.
VIEWPORT_FRAME_TAG = "viewport_frame"


def _group_near_identical(
    elements: list, tol_in: float = COORD_TOL_IN
) -> List[list]:
    """Group elements whose start coords are within tol_in (in
    inches) of each other. The pile group is the largest such
    cluster; if it contains > 20% of the elements, fail."""
    if not elements:
        return []
    tol_pts = tol_in * 72
    # Bucket by quantized (x0, y0) in points
    buckets: dict[tuple, list] = {}
    for el in elements:
        key = (round(el['x0'] / tol_pts), round(el['y0'] / tol_pts))
        buckets.setdefault(key, []).append(el)
    groups = list(buckets.values())
    groups.sort(key=len, reverse=True)
    return groups


# ── Public QC API ────────────────────────────────────────────────────


def enforce_b2_qc(
    pdf_bytes: bytes,
    family: str,
    product_type: str,
) -> dict:
    """Run all three B2 QC gates against a rendered PDF.

    Args:
      pdf_bytes: the rendered PDF (raw bytes from a tool result)
      family: the family name (for error messages)
      product_type: the product_type (for error messages)

    Returns:
      dict with summary stats:
        {
          "vector_bbox_in": (min_x, min_y, max_x, max_y),
          "page_coverage_x": 0.768,
          "page_coverage_y": 0.894,
          "title_block_x_in": 7.0,
          "drawing_zone_x_in": 0.0..6.1,
          "elements_total": 25,
          "elements_in_pile": 4,
          "pile_frac": 0.16,
          "word_overlap_pairs": [],
        }

    Raises B2QCFailure when any gate fails. The class is a
    subclass of AssertionError so `pytest.raises(B2QCFailure)` works.
    """
    pdfplumber_obj = pdfplumber.open(__import__('io').BytesIO(pdf_bytes))
    try:
        page = pdfplumber_obj.pages[0]

        # ── (a) Element-spread gate ─────────────────────────
        bbox = _bbox_of_lines_rects(page)
        min_x, min_y, max_x, max_y = bbox
        cov_x = (max_x - min_x) / PAGE_W_IN if max_x > min_x else 0.0
        cov_y = (max_y - min_y) / PAGE_H_IN if max_y > min_y else 0.0
        if cov_x < SPREAD_X_MIN_FRAC:
            raise B2QCFailure(
                f"B2 QC (spread X) FAIL on {family}/{product_type}: "
                f"drawing spans {cov_x*100:.1f}% of page width "
                f"(min {SPREAD_X_MIN_FRAC*100:.0f}%). "
                f"bbox={bbox}, page=11x8.5 in. This is the "
                f"bottom-left-pile defect — coords all near (0,0)."
            )
        if cov_y < SPREAD_Y_MIN_FRAC:
            raise B2QCFailure(
                f"B2 QC (spread Y) FAIL on {family}/{product_type}: "
                f"drawing spans {cov_y*100:.1f}% of page height "
                f"(min {SPREAD_Y_MIN_FRAC*100:.0f}%). bbox={bbox}."
            )

        # Element pile check: more than PILE_FRAC_MAX of elements
        # within a COORD_TOL_IN cluster is a pile.
        all_elements = list(page.lines) + [
            r for r in page.rects
            if r['x0'] >= _P_in(MARGIN_IN) - 0.1
            and r['y0'] >= _P_in(MARGIN_IN) - 0.1
            and r['x1'] <= _P_in(PAGE_W_IN - MARGIN_IN) + 0.1
            and r['y1'] <= _P_in(PAGE_H_IN - MARGIN_IN) + 0.1
        ]
        n_total = len(all_elements)
        if n_total == 0:
            raise B2QCFailure(
                f"B2 QC (spread) FAIL on {family}/{product_type}: "
                f"NO vector elements drawn — the PDF is empty"
            )
        groups = _group_near_identical(all_elements)
        largest_pile = max(len(g) for g in groups) if groups else 0
        pile_frac = largest_pile / n_total
        if pile_frac > PILE_FRAC_MAX:
            raise B2QCFailure(
                f"B2 QC (pile) FAIL on {family}/{product_type}: "
                f"{largest_pile}/{n_total} elements "
                f"({pile_frac*100:.1f}%) cluster within "
                f"{COORD_TOL_IN}\" of each other "
                f"(max allowed {PILE_FRAC_MAX*100:.0f}%). "
                f"This is the bottom-left-pile defect — "
                f"the B2b coord-system fix did not take effect."
            )

        # ── (b) Zone gates ───────────────────────────────────
        # Title-block text in the right column (x >= 6.5").
        # Drawing elements in the left half (x <= 6.5" mostly;
        # we accept up to 6.7" to tolerate the dim-line labels
        # and the height-dim extension that bleed slightly into
        # the title-column boundary).
        right_text = []
        left_elements = []
        for char in page.chars:
            x = _points_to_inches(char['x0'])
            y = _y0_to_bl_in(char['y0'])
            if x >= TITLE_X_IN_MIN:
                right_text.append((char['text'], x, y))
            else:
                left_elements.append((char['text'], x, y))
        # Pin: at least one title-block char in the right column.
        if not right_text:
            raise B2QCFailure(
                f"B2 QC (zone title-block) FAIL on "
                f"{family}/{product_type}: NO text rendered in the "
                f"right column (x >= {TITLE_X_IN_MIN}\")"
            )
        # Pin: at least one drawing char in the left half.
        if not left_elements:
            raise B2QCFailure(
                f"B2 QC (zone drawing) FAIL on "
                f"{family}/{product_type}: NO text rendered in the "
                f"left half (x < {TITLE_X_IN_MIN}\")"
            )

        # Nothing off-page (y < 0.2" from bottom OR y > page height
        # - 0.2"). The pre-B2b bug had text rendered at y=-9.5 (off-
        # page) — that's the "spilled off the page" defect. Dim
        # labels in the bottom margin (y between 0.3 and 0.5) are
        # intentional and not a defect; the threshold of 0.2"
        # gives the layout room for those labels.
        margin_pts = _P_in(0.2)
        top_margin_pts = _P_in(PAGE_H_IN - 0.2)
        off_page = [
            (c['text'], _points_to_inches(c['x0']),
             _y0_to_bl_in(c['y0']))
            for c in page.chars
            if c['y0'] < margin_pts or c['y0'] > top_margin_pts
        ]
        if off_page:
            sample = off_page[:3]
            raise B2QCFailure(
                f"B2 QC (zone off-page) FAIL on "
                f"{family}/{product_type}: {len(off_page)} chars "
                f"off-page (y < 0.2\" or y > {PAGE_H_IN - 0.2}\"). "
                f"samples: {sample}"
            )

        # ── (c) Text-collision gate ───────────────────────────
        # Word-bbox overlap between DIFFERENT text lines > 30% of
        # the smaller bbox = overlap fault. Catches the bottom-
        # left-pile output where every char lands at the same
        # coordinate (multiple chars overlap because they're
        # stacked at one point).
        overlap_pairs = _check_text_collision(page)
        if overlap_pairs:
            raise B2QCFailure(
                f"B2 QC (text collision) FAIL on "
                f"{family}/{product_type}: {len(overlap_pairs)} "
                f"word-pair overlaps > {TEXT_OVERLAP_THRESHOLD*100:.0f}%. "
                f"samples: {overlap_pairs[:3]}"
            )

        # ── (d) Text-over-geometry collision gate (B2c (6)) ────
        # HOTFIX B2c (6): no text bbox may overlap a drawing element's
        # bbox. Catches the LAYOUT-MATH block overprinting the shade
        # outline (the pre-B2c render had LAYOUT MATH at the bottom-
        # left of the sheet, OVERLAPPING the shade outline).
        text_overlap_geom = _check_text_over_geometry(page)
        if text_overlap_geom:
            sample = text_overlap_geom[:3]
            raise B2QCFailure(
                f"B2 QC (text-over-geometry) FAIL on "
                f"{family}/{product_type}: {len(text_overlap_geom)} "
                f"text bbox(s) overlap a drawing element. samples: "
                f"{sample}"
            )

        # HOTFIX B2c corrections (2): dimension-witness-endpoint gate.
        # Every dimension's witness line endpoints must coincide (±2pt)
        # with a DRAWING-ELEMENT edge (a feature corner or a rect
        # edge), NOT with another dimension's line. This catches the
        # defect where one dim's witness line terminates on another
        # dim's line (the pre-fix B2c render had the height-dim's
        # lower witness line sharing the width-dim's reference level).
        dim_borrow = _check_dim_witness_borrow(page)
        if dim_borrow:
            sample = dim_borrow[:3]
            raise B2QCFailure(
                f"B2 QC (dim-witness-borrow) FAIL on "
                f"{family}/{product_type}: {len(dim_borrow)} dim "
                f"witness endpoint(s) borrow another dim's line. "
                f"samples: {sample}"
            )

        # B2d+ golden port: same-baseline overlap (new rule)
        baseline_ov = _check_same_baseline_overlap(page)
        if baseline_ov:
            sample = baseline_ov[:3]
            raise B2QCFailure(
                f"B2 QC (same-baseline overlap) FAIL on "
                f"{family}/{product_type}: {len(baseline_ov)} "
                f"horizontal-line pair(s) at the same baseline with "
                f"> {SAME_BASELINE_X_OVERLAP_MIN_IN}\" x overlap. "
                f"samples: {sample}"
            )

        # B2d+ golden port: column overflow (new rule)
        col_ov = _check_column_overflow(page)
        if col_ov:
            sample = col_ov[:3]
            raise B2QCFailure(
                f"B2 QC (column overflow) FAIL on "
                f"{family}/{product_type}: {len(col_ov)} char(s) "
                f"past the title column inner border (right edge at "
                f"{(PAGE_W_IN - MARGIN_IN - 0.18):.2f}\"). "
                f"samples: {sample}"
            )

        # ── Golden-port corrections R3 (2026-08-16) — 2 new gates ─
        # Gate R3-1: footer-band collision (zone min-gap)
        fc_failures = _check_footer_collision(page)
        if fc_failures:
            msgs = [f["issue"] for f in fc_failures]
            raise B2QCFailure(
                f"B2 QC (footer-collision) FAIL on "
                f"{family}/{product_type}: {'; '.join(msgs)}. "
                f"samples: {fc_failures[:3]}"
            )
        # Gate R3-2: stack anatomy (continuous fabric, NOT bar-ladder)
        sa_failures = _check_stack_anatomy(page, family=family)
        if sa_failures:
            msgs = [f["issue"] for f in sa_failures]
            raise B2QCFailure(
                f"B2 QC (stack-anatomy) FAIL on "
                f"{family}/{product_type}: {'; '.join(msgs)}. "
                f"samples: {sa_failures[:3]}"
            )

        # ── Golden-port corrections G1 (2026-08-16) — 5 new gates ─
        # Gate 1: elevation viewport-fill + scale-truth
        scale_truth_failures = _check_elevation_scale_truth(page)
        if scale_truth_failures:
            msgs = [f["issue"] for f in scale_truth_failures]
            raise B2QCFailure(
                f"B2 QC (scale-truth) FAIL on {family}/{product_type}: "
                f"{'; '.join(msgs)}. samples: {scale_truth_failures[:3]}"
            )
        # Gate 2: fold stack is flat horizontal flaps (R5/R6)
        flap_failures = _check_fold_stack_is_flat(page, family=family)
        if flap_failures:
            msgs = [f["issue"] for f in flap_failures]
            raise B2QCFailure(
                f"B2 QC (fold-stack) FAIL on {family}/{product_type}: "
                f"{'; '.join(msgs)}. samples: {flap_failures[:3]}"
            )
        # Gate 3: footer FOR DISCUSSION string present
        footer_disc_failures = _check_footer_for_discussion(page)
        if footer_disc_failures:
            msgs = [f["issue"] for f in footer_disc_failures]
            raise B2QCFailure(
                f"B2 QC (footer-discussion) FAIL on "
                f"{family}/{product_type}: {'; '.join(msgs)}. "
                f"samples: {footer_disc_failures[:3]}"
            )
        # Gate 4: duplicate viewport captions
        dup_cap_failures = _check_duplicate_viewport_captions(page)
        if dup_cap_failures:
            msgs = [f["issue"] for f in dup_cap_failures]
            raise B2QCFailure(
                f"B2 QC (duplicate-captions) FAIL on "
                f"{family}/{product_type}: {'; '.join(msgs)}. "
                f"samples: {dup_cap_failures[:3]}"
            )
        # Gate 5: title + witnesses
        title_witness_failures = _check_title_and_witnesses(page, family=family)
        if title_witness_failures:
            msgs = [f["issue"] for f in title_witness_failures]
            raise B2QCFailure(
                f"B2 QC (title+witnesses) FAIL on "
                f"{family}/{product_type}: {'; '.join(msgs)}. "
                f"samples: {title_witness_failures[:3]}"
            )
        # Gate 6 (Step 0 / G1.3): text-bounds — every rendered
        # text bbox must sit fully inside its owning frame/viewport
        # with ≥ 0.06" margin. Overflowing text shrinks or wraps,
        # never clips or spills.
        bounds_failures = _check_text_bounds(page)
        if bounds_failures:
            msgs = [f["issue"] for f in bounds_failures]
            raise B2QCFailure(
                f"B2 QC (text-bounds) FAIL on "
                f"{family}/{product_type}: {'; '.join(msgs)}. "
                f"samples: {bounds_failures[:3]}"
            )

        return {
            "vector_bbox_in": bbox,
            "page_coverage_x": cov_x,
            "page_coverage_y": cov_y,
            "elements_total": n_total,
            "elements_in_pile": largest_pile,
            "pile_frac": pile_frac,
            "title_block_chars": len(right_text),
            "drawing_zone_chars": len(left_elements),
            "off_page_chars": len(off_page),
            "word_overlap_pairs": overlap_pairs,
            "text_overlap_geom": text_overlap_geom,
            "dim_borrow": dim_borrow,
            "same_baseline_overlap": baseline_ov,
            "column_overflow": col_ov,
            "scale_truth_failures": scale_truth_failures,
            "flap_failures": flap_failures,
            "footer_disc_failures": footer_disc_failures,
            "dup_cap_failures": dup_cap_failures,
            "title_witness_failures": title_witness_failures,
        }
    finally:
        pdfplumber_obj.close()


# ── Text collision ───────────────────────────────────────────────────


def _check_text_collision(page) -> List[Tuple[str, str]]:
    """Word-bbox collision: for every pair of words on different
    visual lines whose BBOXES OVERLAP IN BOTH X AND Y, if the
    overlap is > TEXT_OVERLAP_THRESHOLD of the smaller bbox, flag
    the pair.

    The pre-B2b bug had every char at the same (x, y) point in
    the pile output — many words overlapping in BOTH axes. The
    title block has words at different y positions with the same x
    start, but those DO NOT overlap in y → not flagged here.

    pdfplumber groups chars into words via `extract_words()`.
    """
    words = page.extract_words(
        use_text_flow=False,  # don't reorder rows; we want spatial truth
        keep_blank_chars=False,
    )
    if not words:
        return []
    pairs = []
    n = len(words)
    for i in range(n):
        wa = words[i]
        for j in range(i + 1, n):
            wb = words[j]
            # Bbox intersection: y-ranges must overlap (otherwise
            # the words are on vertically separated lines, which
            # is normal — different label rows, not a collision).
            y_overlap = max(0,
                            min(wa['bottom'], wb['bottom'])
                            - max(wa['top'], wb['top']))
            if y_overlap <= 0:
                continue
            # Y-overlap is real. Now check x-overlap fraction.
            x_overlap_frac = _h_overlap_frac(wa, wb)
            y_overlap_frac = (
                y_overlap / min(wa['bottom'] - wa['top'],
                                wb['bottom'] - wb['top'])
            )
            # AND-gate: words on the SAME visual line must overlap in
            # BOTH x and y. Words stacked vertically at the same x
            # (e.g. right-column title-block rows) have high x-overlap
            # but low y-overlap — they're NOT collisions. The pre-B2b
            # bug had every char at the same (x, y) point, which
            # would have high overlap in BOTH axes — that's the real
            # collision signature.
            if (x_overlap_frac > TEXT_OVERLAP_THRESHOLD
                    and y_overlap_frac > TEXT_OVERLAP_THRESHOLD):
                pairs.append((wa['text'], wb['text']))
    return pairs


def _h_overlap_frac(wa: dict, wb: dict) -> float:
    """Horizontal bbox-overlap fraction between two word bboxes.
    Returns the overlap divided by the smaller bbox's width."""
    ax0, ax1 = wa['x0'], wa['x1']
    bx0, bx1 = wb['x0'], wb['x1']
    inter = max(0, min(ax1, bx1) - max(ax0, bx0))
    a_w = ax1 - ax0
    b_w = bx1 - bx0
    if a_w <= 0 or b_w <= 0:
        return 0.0
    smaller = min(a_w, b_w)
    return inter / smaller


# ── Text-over-geometry collision (HOTFIX B2c (6)) ───────────────────


def _check_text_over_geometry(page) -> List[dict]:
    """Flag every text bbox (from page.chars) that overlaps a drawing
    element bbox (page.lines or page.rects).

    HOTFIX B2c (6) catches the specific defect where the LAYOUT-MATH
    block (bottom-center) overprinted the shade outline (left zone) —
    the text chars landed inside the rect of the shade body. The
    pre-B2c test would have been broken by this immediately.

    Returns a list of {char_text, char_x, char_y, element_kind,
    element_bbox} dicts for each overlap. Empty list = clean.
    """
    if not page.chars:
        return []
    elements = []
    # Skip lines: they are 0.4-0.6pt wide and don't realistically
    # get overprinted by text. The text-over-geometry gate is for
    # rect-shaped drawing elements (mount, hem, shade body) that
    # would visually overprint the text.
    for r in page.rects:
        # Exclude the sheet-border rect (the outer border at
        # 0.35" from page edges, 10.3" × 7.8" — HOTFIX B2c adds
        # this). It's intentional and overlaps every char by
        # design; flagging it would false-fail every render.
        if (r['x0'] <= _P_in(0.4) and r['y0'] <= _P_in(0.4)
                and r['width'] > 9.5 * 72
                and r['height'] > 7.0 * 72):
            continue
        elements.append(("rect", r['x0'], r['y0'], r['x1'], r['y1']))
    overlaps = []
    for c in page.chars:
        cx0, cy0 = c['x0'], c['y0']
        cx1 = c.get('x1', cx0)
        cy1 = c.get('y1', cy0)
        # Per-char bbox (approximate; pdfplumber chars have x0/x1
        # baseline-only but pdfminer exposes top/bottom).
        char_w = max(cx1 - cx0, 1)
        char_h = max(cy1 - cy0, 8)
        for kind, ex0, ey0, ex1, ey1 in elements:
            # Compute intersection area (must be > 0 for an overlap).
            ix0, iy0 = max(cx0, ex0), max(cy0, ey0)
            ix1, iy1 = min(cx0 + char_w, ex1), min(cy0 + char_h, ey1)
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            inter = (ix1 - ix0) * (iy1 - iy0)
            char_area = char_w * char_h
            # Skip text that's entirely INSIDE the rect (it's part
            # of the rect's content, e.g. fold-spacing dim labels
            # inside the shade body, dim labels inside the title
            # block). The gate is for text OVERPRINTING a drawing
            # element, not text that's content of one.
            if char_area > 0 and (inter / char_area) > 0.9:
                continue  # fully contained — content of the rect
            if char_area > 0 and inter / char_area > 0.05:
                overlaps.append({
                    "char_text": c.get('text', '?'),
                    "char_bbox_in": (
                        _points_to_inches(cx0),
                        _y0_to_bl_in(cy0),
                        _points_to_inches(cx0 + char_w),
                        _y0_to_bl_in(cy0 + char_h),
                    ),
                    "element_kind": kind,
                    "element_bbox_in": (
                        _points_to_inches(ex0),
                        _y0_to_bl_in(ey0),
                        _points_to_inches(ex1),
                        _y0_to_bl_in(ey1),
                    ),
                })
    return overlaps


# ── Dim-witness-borrow gate (HOTFIX B2c corrections (2)) ───────


def _check_dim_witness_borrow(page) -> list[dict]:
    """Every dim's witness line endpoints must coincide with a
    drawing-element edge (a rect or a line in the page), NOT with
    another dim's line. This catches the B2c-side defect where the
    height-dim's lower witness line shared the width-dim's level
    instead of terminating at the hem bar (a feature edge).

    The gate identifies pairs of LINES on the page. Both must be
    ≥ 0.5" long (skip short tick marks). If their y-coords are
    within 0.5pt AND their x-extents overlap by ≥ 0.5", the
    witness is BORROWING the other line as a terminator — failure.
    """
    if not page.lines:
        return []
    borrows = []
    lines = sorted(page.lines, key=lambda l: (round(l['y0'] / 2), l['x0']))
    h_lines = [l for l in lines
               if abs(l['y1'] - l['y0']) < abs(l['x1'] - l['x0'])]
    for i, la in enumerate(h_lines):
        for j, lb in enumerate(h_lines):
            if i == j:
                continue
            # Skip short tick-mark lines (lines ≤ 0.5" long are
            # usually witness tick marks, not borrow suspects).
            if (la['x1'] - la['x0']) < 0.5 * 72:
                continue
            if (lb['x1'] - lb['x0']) < 0.5 * 72:
                continue
            # Lines at the same y (within 0.5pt) are a borrow
            # suspect.
            if abs(la['y0'] - lb['y0']) > 0.5:
                continue
            # Borrow if they overlap in x by ≥ 0.5".
            x_overlap = max(0, min(la['x1'], lb['x1'])
                            - max(la['x0'], lb['x0']))
            if x_overlap >= 0.5 * 72:
                borrows.append({
                    "line_a": {
                        "x0": la['x0'], "x1": la['x1'],
                        "y0": la['y0'], "y1": la['y1'],
                    },
                    "line_b": {
                        "x0": lb['x0'], "x1": lb['x1'],
                        "y0": lb['y0'], "y1": lb['y1'],
                    },
                    "shared_y": la['y0'],
                })
    return borrows


# ── B2d+ new rules: same-baseline overlap + column overflow ───


def _check_same_baseline_overlap(page) -> list[dict]:
    """B2d+ rule (learned building golden v10).

    Two horizontal lines (or label baselines) sharing the same y
    (within SAME_BASELINE_Y_TOL_PT) with > 0.5" of x overlap,
    drawn by different ReportLab draw calls, indicates one label
    was meant to replace the other and the second one was
    forgotten (or both fire on the same element).

    Catches dim-line label collisions that the old text-collision
    gate (per-word) couldn't see: e.g. width-dim's "38\"" baseline
    AND the front-elev "Slat: 7-1/8 (9 total)..." baseline
    sitting at the same y for > 0.5" of x overlap.

    Negative fixture: same as dim-borrow (any two long horizontal
    lines at the same y with x overlap will trip either gate —
    they catch overlapping defect classes).
    """
    if not page.lines:
        return []
    overlaps = []
    h_lines = [l for l in page.lines
               if abs(l['y1'] - l['y0']) < abs(l['x1'] - l['x0'])]
    for i, la in enumerate(h_lines):
        for j, lb in enumerate(h_lines):
            if i == j:
                continue
            # Skip short lines (less than 0.5" — likely tick marks
            # or annotation brackets, not suspect).
            if (la['x1'] - la['x0']) < _P_in(0.5):
                continue
            if (lb['x1'] - lb['x0']) < _P_in(0.5):
                continue
            # Same baseline (B2d+ tolerance is 2pt, looser than
            # the dim-borrow 0.5pt — the new rule is about same-Y
            # visual collision, not exact-witness-borrow).
            if abs(la['y0'] - lb['y0']) > SAME_BASELINE_Y_TOL_PT:
                continue
            # x overlap > 0.5"
            x_overlap = max(0, min(la['x1'], lb['x1'])
                            - max(la['x0'], lb['x0']))
            if x_overlap >= _P_in(SAME_BASELINE_X_OVERLAP_MIN_IN):
                overlaps.append({
                    "line_a": {"x0": la['x0'], "x1": la['x1'],
                                "y0": la['y0'], "y1": la['y1']},
                    "line_b": {"x0": lb['x0'], "x1": lb['x1'],
                                "y0": lb['y0'], "y1": lb['y1']},
                    "shared_y": la['y0'],
                })
    return overlaps


def _check_column_overflow(page) -> list[dict]:
    """B2d+ rule: no rendered text in the TITLE COLUMN may extend
    past the column's inner right border.

    Catches layout regressions where a long title row or assumption
    bullet exceeds the column width (the B2d row-gap tuning
    occasionally overran for long fabric-mill names like
    "GP&J Baker BP10814-2 54" W · 35.46\" V-repeat").

    The "title column inner border" is at x = PAGE_W_IN - MARGIN_IN
    - 0.18 (the column's right inner edge per golden v10). The check
    is restricted to chars in the title column's y-range
    (between the header and footer bands) so the footer's right
    text ("SHEET B2 · 1 OF 1" at the right margin) doesn't
    false-fire.
    """
    if not page.chars:
        return []
    overflow = []
    title_inner_right = (PAGE_W_IN - MARGIN_IN - 0.18) * 72.0
    # Y range for title column: below header band, above footer band
    y_top = (PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN) * 72.0  # pt
    y_bot = (MARGIN_IN + FOOTER_BAND_H_IN) * 72.0
    for ch in page.chars:
        if ch['x1'] <= title_inner_right + COLUMN_OVERFLOW_TOL_PT:
            continue
        # Restrict to title column y-range
        ch_y_top = ch['y0']  # pdfplumber y0 is bbox TOP
        ch_y_bot = ch['y1']  # bbox BOTTOM
        # page height = 612 pt
        if not (y_bot < ch_y_top < PAGE_H_IN * 72 and y_top < ch_y_bot):
            continue
        overflow.append({
            "char_text": ch.get("text", "?"),
            "char_x0_in": ch['x0'] / 72.0,
            "char_x1_in": ch['x1'] / 72.0,
            "column_right_in": title_inner_right / 72.0,
        })
    return overflow


# ── CORRECTION 1 — Elevation viewport-fit + scale-truth gate ─────
#
# The previous R1 port used a ROOM-fit scale (s = inner_h / (ceiling
# + margin)) which made the 38" × 64" shade only ~40% of the
# viewport width while the SCALE row stamp claimed "1\" = 1'-4\"" —
# the geometry was shrunk, the stamp was a lie. The fix: the
# renderer uses a SHADE-FIT scale and reports it honestly in the
# SCALE row.
#
# This gate asserts:
#   (a) drawn elevation bbox == real_dim * scale_factor ± 1%
#   (b) bbox fills ≥ 80% of the front-elev viewport on at least
#       ONE axis (height-limited since shade is taller than wide)
#
# Both, not either. Without (a) the stamp could be honest and the
# geometry still wrong; without (b) the stamp could match a tiny
# geometry shrunk into the corner.

def _check_elevation_scale_truth(page) -> list[dict]:
    """Gate 1: scale-truth + viewport-fill for the front elevation.

    Reads SCALE row + DIMENSIONS row from the title column, then
    measures the elevation content bbox (lines + rects inside the
    front-elev viewport frame). Asserts:
      (a) drawn elevation width  ≈ real_w * scale_factor  (±1%)
      (b) drawn elevation height ≈ real_h * scale_factor  (±1%)
      (c) drawn bbox fills ≥ 80% of viewport on at least one axis

    scale_factor is sheet-inches per model-inch (e.g. 0.0625 =
    "1\" = 1'-4\"" = 1/16).
    """
    failures = []
    text = "".join(c["text"] for c in page.chars)
    # Parse DIMENSIONS row: "DIMENSIONS:38.00\" W × 64.00\" H"
    dim_m = re.search(
        r'DIMENSIONS:?\s*([\d.]+)\s*"\s*W\s*[×x]\s*([\d.]+)\s*"\s*H',
        text, re.IGNORECASE)
    if not dim_m:
        failures.append({"gate": "scale-truth",
                         "issue": "DIMENSIONS row not parseable"})
        return failures
    real_w = float(dim_m.group(1))
    real_h = float(dim_m.group(2))
    # Parse SCALE row: "SCALE:1\" = 1'-9/16\"" (or similar)
    # Accepts "N\" = M'-K/L\"" or "N\" = M'-K\""
    scale_m = re.search(
        r'SCALE:?\s*(\d+)\s*"\s*=\s*(\d+)\s*\'\s*-\s*'
        r'(?:(\d+)(?:\s*-\s*(\d+)\s*/\s*(\d+))?)?\s*"',
        text)
    if not scale_m:
        failures.append({"gate": "scale-truth",
                         "issue": "SCALE row not parseable",
                         "text_around": _extract_SCALE_area(text)})
        return failures
    sheet_in = float(scale_m.group(1))
    feet = float(scale_m.group(2))
    inches = float(scale_m.group(3) or 0)
    frac_num = float(scale_m.group(4) or 0)
    frac_den = float(scale_m.group(5) or 1)
    if frac_den > 0 and frac_num > 0:
        inches += frac_num / frac_den
    model_in_per_sheet_in = feet * 12.0 + inches
    scale_factor = sheet_in / model_in_per_sheet_in  # sheet-in / model-in
    # Measure the SHADE BODY bbox specifically — not the entire
    # content bbox, which includes witness extension lines that
    # extend beyond the shade to the dim lines. We identify the
    # shade body as the LARGEST filled rect in the front-elev
    # viewport by area (the shade body and window casing are the
    # only large rects; the casing is +0.10" around the shade).
    vp_x0 = FRONT_X_IN * 72
    vp_y0 = FRONT_Y_IN * 72
    vp_x1 = (FRONT_X_IN + FRONT_W_IN) * 72
    vp_y1 = (FRONT_Y_IN + FRONT_H_IN) * 72
    rects_in_viewport = []
    for r in page.rects:
        cx = (r['x0'] + r['x1']) / 2
        cy = (r['y0'] + r['y1']) / 2
        if not (vp_x0 <= cx <= vp_x1 and vp_y0 <= cy <= vp_y1):
            continue
        if r['x1'] - r['x0'] > FRONT_W_IN * 72 * 0.9:
            continue
        rects_in_viewport.append(r)
    if not rects_in_viewport:
        failures.append({"gate": "scale-truth",
                         "issue": "no rects in front-elev viewport"})
        return failures
    # The shade body (and casing) are the largest rects by area.
    # Casing is slightly larger than shade body (≈ +0.10").
    # Pick the rect with the largest area — that's the casing;
    # the shade body is the second largest (or within 5% of casing
    # in area).
    rects_in_viewport.sort(key=lambda r: (r['x1'] - r['x0']) * (r['y1'] - r['y0']),
                           reverse=True)
    shade_rect = rects_in_viewport[0]  # largest = casing or shade
    # bbox in inches (pdfplumber coords: top-origin; convert to canvas BL)
    bbox_w_in = (shade_rect['x1'] - shade_rect['x0']) / 72.0
    bbox_h_in = (shade_rect['y1'] - shade_rect['y0']) / 72.0
    # Expected drawn dimensions — accounting for the window casing
    # (drawn as +0.05" around the shade on every side, so +0.10"
    # total in width and height). The casing IS the largest rect
    # in the viewport.
    CASING_OVERSHOOT_IN = 0.10
    expect_w = real_w * scale_factor + CASING_OVERSHOOT_IN
    expect_h = real_h * scale_factor + CASING_OVERSHOOT_IN
    # (a) drawn ≈ expected ±1%
    if expect_w > 0:
        w_err = abs(bbox_w_in - expect_w) / expect_w
        if w_err > 0.01:
            failures.append({"gate": "scale-truth",
                             "issue": f"drawn width {bbox_w_in:.3f}\" "
                                      f"≠ expected {expect_w:.3f}\" "
                                      f"(err {w_err*100:.1f}% > 1%)",
                             "bbox_w_in": bbox_w_in,
                             "expect_w_in": expect_w,
                             "scale_factor": scale_factor,
                             "real_w": real_w})
    if expect_h > 0:
        h_err = abs(bbox_h_in - expect_h) / expect_h
        if h_err > 0.01:
            failures.append({"gate": "scale-truth",
                             "issue": f"drawn height {bbox_h_in:.3f}\" "
                                      f"≠ expected {expect_h:.3f}\" "
                                      f"(err {h_err*100:.1f}% > 1%)",
                             "bbox_h_in": bbox_h_in,
                             "expect_h_in": expect_h,
                             "scale_factor": scale_factor,
                             "real_h": real_h})
    # (b) fill ≥ 80% of viewport on ≥ 1 axis (measured against
    # the shade body, not the casing — viewport fill from the
    # CASING bbox is even larger so this is a lower bound).
    shade_w_in = bbox_w_in - CASING_OVERSHOOT_IN
    shade_h_in = bbox_h_in - CASING_OVERSHOOT_IN
    fill_w = shade_w_in / FRONT_W_IN
    fill_h = shade_h_in / FRONT_H_IN
    if max(fill_w, fill_h) < 0.80:
        failures.append({"gate": "scale-truth",
                         "issue": f"shade fills {fill_w*100:.0f}%×{fill_h*100:.0f}%"
                                  f" of viewport, max < 80%",
                         "fill_w": fill_w,
                         "fill_h": fill_h,
                         "shade_w_in": shade_w_in,
                         "shade_h_in": shade_h_in})
    return failures


def _extract_SCALE_area(text: str) -> str:
    """Return a window of text around the SCALE substring for error
    messages."""
    idx = text.upper().find("SCALE")
    if idx < 0:
        return text[:100]
    return text[max(0, idx - 10):idx + 50]


# ── CORRECTION 2 — Fold stack flat flaps gate ───────────────────
#
# The previous R1 port drew each flap as a bezier-curved path that
# rendered as a zigzag/coil (the doctrine requires flat flaps).
# This gate asserts the stack is composed of N discrete horizontal
# flap primitives, with plumb front edges and tips BELOW the face
# line.
#
# Identification heuristic: find rects in the SIDE section viewport
# with width ≈ stack_width and height ≈ ft (one flap thickness).
# Count = N_SLATS_DEFAULT. All x0 equal (plumb). The bottom-most
# flap's y0 (topmost fold tip) is below face_bottom_y.


def _check_fold_stack_is_flat(page, family: str = "Roman Shades") -> list[dict]:
    """Gate 2: assert the fold stack is N flat horizontal flap
    primitives with plumb front edges and tips below the face.

    Family-aware: only runs for "Roman Shades" (the family that has
    the fold-stack doctrine; other families don't have flaps).
    """
    failures = []
    if family != "Roman Shades":
        return failures
    # The side section viewport:
    vp_x0 = SIDE_X_IN * 72
    vp_y0 = SIDE_Y_IN * 72
    vp_x1 = (SIDE_X_IN + SIDE_W_IN) * 72
    vp_y1 = (SIDE_Y_IN + SIDE_H_IN) * 72
    # Find rects that look like flap primitives:
    #   - inside the side section viewport
    #   - aspect ratio wide-and-short (height < 0.4", width > 0.5")
    #   - height ≈ 0.05"–0.20" (one flap thickness at any scale)
    flaps = []
    for r in page.rects:
        cx = (r['x0'] + r['x1']) / 2
        cy = (r['y0'] + r['y1']) / 2
        if not (vp_x0 <= cx <= vp_x1 and vp_y0 <= cy <= vp_y1):
            continue
        w = r['x1'] - r['x0']
        h = r['y1'] - r['y0']
        if h < 1.0 or h > 15.0:    # 1pt–15pt height (flap thickness)
            continue
        if w < 40.0:                # 40pt = ~0.55" (skip thin rects)
            continue
        # Skip the hem bar (very short, ~0.10" wide)
        if w < 15.0:
            continue
        flaps.append({
            "x0": r['x0'], "y0": r['y0'],
            "x1": r['x1'], "y1": r['y1'],
            "w": w, "h": h,
        })
    # Group by similar x0 (plumb front edges) and similar height
    if not flaps:
        failures.append({"gate": "fold-stack",
                         "issue": "no flap-like rects found in side section"})
        return failures
    # CORRECTION R3-2 (2026-08-16): the G1 "8 flat flap rects"
    # check is SUPERSEDED by the new stack-anatomy gate (continuous
    # fabric). With R3-2 there are NO discrete flap rects — the
    # stack is drawn as a flat-face vertical line + 3 fold-tip V's
    # + rear-of-stack line + vertical hem bar (golden source lines
    # 197-219). This gate now only checks: if there ARE any flap-
    # like rects (e.g. a future variant that goes back to discrete
    # flaps), they must be plumb + similar-height + below the
    # flat face. Otherwise (R3-2 case) it's a no-op pass.
    if not flaps:
        # No flaps — this is the R3-2 continuous-fabric case.
        # Pass (the new stack-anatomy gate covers the real check).
        return failures
    flaps.sort(key=lambda f: f["w"] * f["h"], reverse=True)
    flap_candidates = flaps[:8]
    if len(flap_candidates) < 8:
        # Fewer than 8 flap rects — but the new anatomy may use
        # continuous fabric instead. Pass if there are at least
        # 0 (the stack-anatomy gate handles the new case).
        return failures
    # Check all front-edge x0 (left edges) are equal within tolerance
    x0s = [f["x0"] for f in flap_candidates]
    x0_range_pt = max(x0s) - min(x0s)
    if x0_range_pt > 2.0:   # 2pt = ~0.028" tolerance
        failures.append({"gate": "fold-stack",
                         "issue": f"flap front edges not plumb: "
                                  f"x0 range = {x0_range_pt:.2f}pt",
                         "x0s_pt": x0s})
    # Check heights are all similar (within 4pt = ~0.056")
    heights = [f["h"] for f in flap_candidates]
    h_range_pt = max(heights) - min(heights)
    if h_range_pt > 4.0:
        failures.append({"gate": "fold-stack",
                         "issue": f"flap heights vary: {h_range_pt:.2f}pt",
                         "heights_pt": heights})
    # Check that the topmost fold tip (bottom of the LOWEST flap,
    # i.e. the flap with the smallest y0) is BELOW the fabric face
    # line. The face line is approximately at the y of the seam
    # between the flat face rect and the stack. For Roman Shades,
    # the flat face rect is taller than ft (≈16" × scale ≈ 1.2" at
    # s=0.0751) — much taller than a flap. Identify it as the
    # rect in the side section viewport that's tall (>50pt height)
    # AND has the same x-extent as the flaps.
    face_rects = [f for f in flaps
                  if f["h"] > 50.0 and abs(f["x0"] - flap_candidates[0]["x0"]) < 4.0]
    if face_rects:
        face_bottom_y = min(r["y0"] for r in face_rects)
        # Topmost fold tip = lowest flap's y0 (bottom of flap rect)
        lowest_flap_y0 = min(f["y0"] for f in flap_candidates)
        # pdfplumber y0 is from page TOP. "Below the face" means
        # larger y0 (smaller canvas y).
        if lowest_flap_y0 < face_bottom_y - 5.0:  # 5pt tolerance
            failures.append({"gate": "fold-stack",
                             "issue": "topmost fold tip ABOVE face "
                                      "(R6 violation)",
                             "lowest_flap_y0_pt": lowest_flap_y0,
                             "face_bottom_y_pt": face_bottom_y})
    return failures


# ── CORRECTION 3 — Footer "FOR DISCUSSION" string gate ──────────
#
# The previous R1 port had the call to draw the footer center
# string, but the orange #b25a1d on INK #20241f was so low-contrast
# that it was effectively invisible. AND the ls_text center=True
# path had a units bug (treated points as inches) that shifted the
# text OFF-PAGE (x ≈ -7700 pt). Both fixed in this commit.
#
# This gate asserts the string is present, in the footer band,
# tolerant of whitespace and em-dash variants.


def _check_footer_for_discussion(page) -> list[dict]:
    """Gate 3: assert "FOR DISCUSSION — NOT FOR CONSTRUCTION"
    appears in the footer band center zone.

    Tolerant match: regex handles:
      - "FOR DISCUSSION - NOT FOR CONSTRUCTION" (ASCII dash)
      - "FOR DISCUSSION — NOT FOR CONSTRUCTION" (em-dash U+2014)
      - "FOR DISCUSSION  —  NOT FOR CONSTRUCTION" (extra spaces)
      - "FOR DISCUSSION—NOT FOR CONSTRUCTION" (no spaces)
    """
    failures = []
    # Footer band y-range (canvas y ∈ [MARGIN_IN, MARGIN_IN + FOOTER_BAND_H_IN]).
    # pdfplumber uses BL origin (y0 from page BOTTOM), so
    # canvas inches × 72 = pdfplumber y0 (no inversion needed).
    fb_y0_pdf = MARGIN_IN * 72                       # bottom of footer band
    fb_y1_pdf = (MARGIN_IN + FOOTER_BAND_H_IN) * 72  # top of footer band
    # Footer center x-range: from 30% to 70% of page width
    # (the "FOR DISCUSSION — NOT FOR CONSTRUCTION" string at 8pt
    # letterspaced is ~3" wide; centered at 50%, it spans roughly
    # 35%–65% of the 11" page, so 30-70% gives margin tolerance.)
    cx_min = PAGE_W_IN * 0.30 * 72
    cx_max = PAGE_W_IN * 0.70 * 72
    # Find chars in this region (small tolerance for char bbox extent)
    text_chars = [c["text"] for c in page.chars
                  if fb_y0_pdf - 4 <= c["y0"] <= fb_y1_pdf + 4
                  and cx_min <= c["x0"] <= cx_max]
    text = "".join(text_chars)
    # Tolerant regex: match "FOR DISCUSSION" anywhere near the
    # center; the gate asserts the key phrase is present.
    if not re.search(r'FOR\s+DISCUSSION', text, re.IGNORECASE):
        failures.append({"gate": "footer-discussion",
                         "issue": "'FOR DISCUSSION' not found in footer center",
                         "found_text": text[:200],
                         "y0_range_pt": (fb_y0_pdf, fb_y1_pdf),
                         "cx_range_pt": (cx_min, cx_max)})
    return failures


# ── CORRECTION 4 — Duplicate viewport captions gate ────────────
#
# The previous R1 port drew each viewport label TWICE — once at
# top of frame (per doctrine) and once at bottom-left (per
# `_draw_viewport_frame`). Founder G1 verdict: remove the bottom
# set. This gate asserts each viewport title appears EXACTLY ONCE
# per viewport zone.


def _check_duplicate_viewport_captions(page) -> list[dict]:
    """Gate 4: each viewport title appears exactly once in its
    viewport zone.

    Viewport titles:
      - "FRONT ELEVATION"  → inside front-elev viewport
      - "SIDE SECTION"     → inside side-section viewport (note: the
                              full label is "SIDE SECTION — RAISED";
                              the gate matches the "SIDE SECTION"
                              prefix, tolerant of trailing text)
      - "TITLE BLOCK"      → title column has no top label, no gate

    pdfplumber.extract_words() returns words with x0 (left x) and
    top (TOP-origin Y). Convert top to canvas BL y = PAGE_H - top/72.
    """
    failures = []
    # ls_text emits each letter as a separate drawString with
    # letterspacing, so pdfplumber's extract_words() splits
    # "FRONT ELEVATION" into separate "FRONT" + "ELEVATION" words.
    # Reconstruct the label by concatenating page.chars within a
    # narrow y-band (the label baseline) and matching the needle.
    # We group consecutive chars whose y0 differs by < 2pt as one
    # "line"; then scan each line for the needle substring.
    LINE_Y_TOL_PT = 2.0
    for needle, vp in [
        ("FRONT ELEVATION", ("front", FRONT_X_IN, FRONT_Y_IN,
                              FRONT_W_IN, FRONT_H_IN)),
        ("SIDE SECTION", ("side", SIDE_X_IN, SIDE_Y_IN,
                           SIDE_W_IN, SIDE_H_IN)),
    ]:
        vp_name, vx, vy, vw, vh = vp
        vx0_pt = vx * 72
        vx1_pt = (vx + vw) * 72
        vy0_pt = vy * 72
        vy1_pt = (vy + vh) * 72
        # All chars in the viewport zone
        vp_chars = [c for c in page.chars
                    if vx0_pt - 5 <= c["x0"] <= vx1_pt + 5
                    and vy0_pt - 5 <= c["y0"] <= vy1_pt + 5]
        # Sort by y0 (descending = top to bottom), then x0
        vp_chars.sort(key=lambda c: (-c["y0"], c["x0"]))
        # Group into lines (chars with y0 within LINE_Y_TOL_PT).
        # Use a moving last_y that's updated each iteration.
        lines: list[list] = []
        cur: list = []
        last_y: float | None = None
        for c in vp_chars:
            if last_y is None or abs(c["y0"] - last_y) <= LINE_Y_TOL_PT:
                cur.append(c)
            else:
                if cur:
                    lines.append(cur)
                cur = [c]
            last_y = c["y0"]
        if cur:
            lines.append(cur)
        # Scan each line for the needle (tolerant whitespace)
        matches = []
        for line_chars in lines:
            line_chars.sort(key=lambda c: c["x0"])
            line_text = "".join(c["text"] for c in line_chars)
            # Compress whitespace for the needle match
            line_text_compact = re.sub(r'\s+', ' ', line_text).strip()
            needle_compact = re.sub(r'\s+', ' ', needle).strip()
            if needle_compact in line_text_compact:
                # Compute avg position
                wx = sum(c["x0"] for c in line_chars) / len(line_chars) / 72.0
                wy_canvas = PAGE_H_IN - sum(c["y0"] for c in line_chars) / len(line_chars) / 72.0
                matches.append((line_text_compact[:60], wx, wy_canvas))
        if len(matches) != 1:
            failures.append({
                "gate": "duplicate-captions",
                "issue": f"{needle!r} appears {len(matches)} times in "
                         f"{vp_name} viewport (must be exactly 1)",
                "matches": matches,
            })
    return failures


# ── CORRECTION R3-1 — Footer collision gate ───────────────────────
#
# Both v10 and R2 used a hand-tuned nudge (golden source line 61:
# `ls_text(c, W/2+0.72*inch, ...)`) for the center "FOR DISCUSSION"
# string. R2's longer address defeated the nudge. Neither version had a
# collision check. R3-1 replaces the nudge with computed zone widths +
# enforced minimum gap (≥ MIN_FOOTER_GAP_IN) between the three zones.
# If zones would touch: shrink CENTER tracking first, then LEFT —
# never overlap, never drop the disclaimer.
#
# Gate: compute the rendered x-bbox of each zone's text from the
# font metrics (matching ls_text's drawString math), then assert
# pairwise horizontal gaps ≥ MIN_FOOTER_GAP_IN. Pixel-sample one
# point in each gap to confirm paper shows through (i.e. no
# char from one zone overlaps the other's bbox).
#
# Negative fixture: a PDF with the golden source's +0.72 nudge AND
# the long street address must FAIL this gate (gaps shrink below
# MIN_FOOTER_GAP_IN, char-overlap detected).

def _check_footer_collision(page) -> list[dict]:
    """Gate R3-1: footer-band collision — assert pairwise horizontal
    gaps ≥ MIN_FOOTER_GAP_IN between the three footer zones
    (LEFT letterhead, CENTER disclaimer, RIGHT sheet number).
    """
    failures = []
    MIN_FOOTER_GAP_IN = 0.15
    # Footer band y-range (canvas BL origin in inches; pdfplumber
    # uses BL too — y0 = canvas y * 72).
    fb_y0 = MARGIN_IN * 72
    fb_y1 = (MARGIN_IN + FOOTER_BAND_H_IN) * 72
    # Stricter tolerance — the y0 range is the central 80% of
    # the band so we exclude any text from adjacent zones
    # (e.g. the bottom width "38\"" at y=58.2 just below the
    # band — was polluting the left zone detection).
    fb_chars = [c for c in page.chars
                if fb_y0 <= c["y0"] <= fb_y1]
    # Group by y-line (tolerant of letterspaced chars)
    fb_chars.sort(key=lambda c: (-c["y0"], c["x0"]))
    lines = []
    cur = []
    last_y = None
    for c in fb_chars:
        if last_y is None or abs(c["y0"] - last_y) <= 2.0:
            cur.append(c)
        else:
            if cur:
                lines.append(cur)
            cur = [c]
        last_y = c["y0"]
    if cur:
        lines.append(cur)
    # Build (line_text, line_x0, line_x1) for each line
    line_bboxes = []
    for line_chars in lines:
        line_chars.sort(key=lambda c: c["x0"])
        line_text = "".join(c["text"] for c in line_chars)
        x0 = min(c["x0"] for c in line_chars)
        x1 = max(c.get("x1", c["x0"]) for c in line_chars)
        line_bboxes.append({"text": line_text, "x0": x0, "x1": x1})
    # Identify the three zones by signature text. The footer
    # band often renders ALL zones on a single y-line (because
    # ls_text letterspacing keeps everything in one row), so
    # line grouping can't separate the zones. Instead, find
    # START indices of each signature and use the NEXT zone's
    # start as the end of the CURRENT zone.
    fb_text_chars = [c["text"] for c in fb_chars]
    fb_concat = "".join(fb_text_chars).upper().replace(" ", "")
    left_bbox = None
    center_bbox = None
    right_bbox = None
    # Build per-char cumulative concat (whitespace-stripped)
    idx_concat = []
    running = ""
    for ch in fb_text_chars:
        running += ch.upper().replace(" ", "")
        idx_concat.append(running)
    def _first_x_of_zone(target_full: str) -> float | None:
        """Return the x0 of the FIRST fb_chars entry that begins
        the substring `target_full` (whitespace-stripped) in the
        running footer concat. Handles internal spaces in target."""
        running = ""
        for i, c in enumerate(fb_text_chars):
            old_running = running
            running += c.upper().replace(" ", "")
            if target_full in running and target_full not in old_running:
                # Walk back through fb_chars from index i, counting
                # non-space chars, until we've walked back
                # len(target_full) chars (= position of FIRST
                # char of target_full in the running string).
                skip = len(target_full)
                start_i = i
                while skip > 0 and start_i >= 0:
                    cur = fb_text_chars[start_i].upper().replace(" ", "")
                    if cur:
                        skip -= 1
                    start_i -= 1
                return fb_chars[start_i + 1]["x0"]
        return None
    # Use single-char signatures to find each zone's x-boundary
    x_center_start = _first_x_of_zone("FORDISCUSSION")
    x_right_start = _first_x_of_zone("SHEETB2")
    if x_right_start is None:
        x_right_start = _first_x_of_zone("1OF1")
    # Build zone bboxes by RANGE on x0 (with NO fuzzy margin —
    # we want EXACT boundaries between zones, since the renderer
    # enforces min gap so zones don't overlap). LEFT zone = chars
    # with x0 < x_center_start. CENTER = chars with x0 in
    # [x_center_start, x_right_start). RIGHT = chars with x0
    # >= x_right_start.
    def _zone_bbox(x_lo_inclusive: float, x_hi_exclusive: float) -> dict | None:
        zc = [c for c in fb_chars
              if x_lo_inclusive <= c["x0"] < x_hi_exclusive]
        if not zc:
            return None
        return {
            "text": "".join(c["text"] for c in zc),
            "x0": min(c["x0"] for c in zc),
            "x1": max(c.get("x1", c["x0"]) for c in zc),
        }
    left_bbox = _zone_bbox(0.0, x_center_start) if x_center_start else None
    if x_center_start is not None and x_right_start is not None:
        center_bbox = _zone_bbox(x_center_start, x_right_start)
        right_bbox = _zone_bbox(x_right_start, 10000.0)  # to end
    elif x_center_start is not None:
        center_bbox = _zone_bbox(x_center_start, 10000.0)
        right_bbox = None
    if not (left_bbox and center_bbox and right_bbox):
        failures.append({
            "gate": "footer-collision",
            "issue": f"could not identify all 3 footer zones "
                     f"(left={left_bbox is not None}, "
                     f"center={center_bbox is not None}, "
                     f"right={right_bbox is not None})",
        })
        return failures
    # Compute gaps in inches (pdfplumber pts → inches / 72)
    gap_lc_pt = center_bbox["x0"] - left_bbox["x1"]
    gap_cr_pt = right_bbox["x0"] - center_bbox["x1"]
    gap_lc_in = gap_lc_pt / 72.0
    gap_cr_in = gap_cr_pt / 72.0
    if gap_lc_in < MIN_FOOTER_GAP_IN:
        failures.append({
            "gate": "footer-collision",
            "issue": f"LEFT-CENTER gap {gap_lc_in:.3f}\" < "
                     f"MIN {MIN_FOOTER_GAP_IN}\" "
                     f"(left x1={left_bbox['x1']/72:.3f}\", "
                     f"center x0={center_bbox['x0']/72:.3f}\")",
            "gap_lc_in": gap_lc_in,
            "min_gap_in": MIN_FOOTER_GAP_IN,
            "left_bbox_text": left_bbox["text"][:40],
            "center_bbox_text": center_bbox["text"][:40],
        })
    if gap_cr_in < MIN_FOOTER_GAP_IN:
        failures.append({
            "gate": "footer-collision",
            "issue": f"CENTER-RIGHT gap {gap_cr_in:.3f}\" < "
                     f"MIN {MIN_FOOTER_GAP_IN}\" "
                     f"(center x1={center_bbox['x1']/72:.3f}\", "
                     f"right x0={right_bbox['x0']/72:.3f}\")",
            "gap_cr_in": gap_cr_in,
            "min_gap_in": MIN_FOOTER_GAP_IN,
            "center_bbox_text": center_bbox["text"][:40],
            "right_bbox_text": right_bbox["text"][:40],
        })
    return failures


# ── CORRECTION R3-2 — Stack-anatomy gate ──────────────────────────
#
# The previous R2 port drew the raised stack as 8 discrete horizontal
# rect flaps (the "venetian-slat" look — R5/R6 satisfied but R7/R8
# anatomy violated; not how fabric actually stacks). The golden source
# (Detail A at lines 222-264, with annotation "FRONT FACE DROPS FLAT
# ~1/3-1/2, FOLDS BELOW") specifies a CONTINUOUS fabric anatomy:
# fabric wraps board front and drops FLAT for top ~40% of stack height,
# then 3 fold-tip V's project forward BELOW the flat drop, with rear-
# of-stack line at glass side and vertical hem bar in fabric plane.
#
# Gate asserts:
#   (a) NO set of 3+ disconnected horizontal bar primitives
#       separated by vertical gaps (the bar-ladder defect).
#   (b) A continuous front-face segment spans ≥ 1/3 of stack height
#       at a single x (the flat drop, plumb — R5).
#   (c) All fold-tip vertices below the flat-drop bottom (R6 extended).
#   (d) Hem bar bottommost, vertical, in the fabric plane (R8).
# Negative fixture: the bar-ladder representation must FAIL this gate.

def _check_stack_anatomy(page, family: str = "Roman Shades") -> list[dict]:
    """Gate R3-2: assert stack anatomy matches the golden source's
    continuous-fabric model (NOT the bar-ladder)."""
    failures = []
    if family != "Roman Shades":
        return failures
    # The side section viewport bounds.
    vp_x0 = SIDE_X_IN * 72
    vp_x1 = (SIDE_X_IN + SIDE_W_IN) * 72
    vp_y0 = SIDE_Y_IN * 72
    vp_y1 = (SIDE_Y_IN + SIDE_H_IN) * 72
    # Find all rects in the side section viewport
    flaps = []
    for r in page.rects:
        cx = (r['x0'] + r['x1']) / 2
        cy = (r['y0'] + r['y1']) / 2
        if not (vp_x0 <= cx <= vp_x1 and vp_y0 <= cy <= vp_y1):
            continue
        flaps.append({
            "x0": r['x0'], "y0": r['y0'],
            "x1": r['x1'], "y1": r['y1'],
            "w": r['x1'] - r['x0'],
            "h": r['y1'] - r['y0'],
        })
    # (a) Bar-ladder detection: 3+ rects with similar width
    # (≈ stack_width) and SIMILAR short height (~1 flap thickness)
    # arranged in a vertical stack with vertical gaps between them.
    # Sort by area; the largest rects are the most likely flap rects.
    flaps.sort(key=lambda f: f["w"] * f["h"], reverse=True)
    # Filter to "flap-like": wide AND short
    flap_candidates = [f for f in flaps
                       if f["h"] < 15.0   # < 15pt height
                       and f["h"] > 0.5  # > 0.5pt
                       and f["w"] > 30.0  # > 30pt wide
                       and f["w"] / max(f["h"], 0.01) > 3.0]  # aspect > 3
    # Count rects that look like the bar-ladder (similar heights, in
    # a vertical column with gaps between them).
    if len(flap_candidates) >= 3:
        # Sort by y center to detect vertical stacking
        flap_candidates.sort(key=lambda f: (f["y0"] + f["y1"]) / 2)
        # Walk through: if 3+ consecutive rects have similar heights
        # (within 30%) AND are separated by vertical gaps (y0 of
        # rect n+1 > y1 of rect n + small gap), it's the bar-ladder.
        bar_count = 1
        prev_y1 = flap_candidates[0]["y1"]
        prev_h = flap_candidates[0]["h"]
        for fc in flap_candidates[1:]:
            if (abs(fc["h"] - prev_h) < 0.30 * prev_h
                    and fc["y0"] > prev_y1 + 1.0):   # vertical gap
                bar_count += 1
                prev_y1 = fc["y1"]
                prev_h = fc["h"]
            else:
                bar_count = 1
                prev_y1 = fc["y1"]
                prev_h = fc["h"]
            if bar_count >= 3:
                failures.append({
                    "gate": "stack-anatomy",
                    "issue": f"bar-ladder detected: {bar_count}+ "
                             f"disconnected horizontal bar rects "
                             f"with vertical gaps "
                             f"(continuous fabric anatomy required)",
                    "n_bars": bar_count,
                    "bar_heights_pt": [f["h"] for f in flap_candidates[:bar_count]],
                })
                return failures
    # (b) Continuous front-face: a vertical LINE in the side section
    # viewport with length ≥ 1/3 of stack height (the flat drop).
    # Find all vertical lines in the side section viewport.
    vertical_lines = []
    for l in page.lines:
        cx = (l['x0'] + l['x1']) / 2
        cy = (l['y0'] + l['y1']) / 2
        if not (vp_x0 <= cx <= vp_x1 and vp_y0 <= cy <= vp_y1):
            continue
        if abs(l['x1'] - l['x0']) > 2.0:
            continue   # not vertical
        vlen = abs(l['y1'] - l['y0'])
        vertical_lines.append({
            "x0": l['x0'], "y0": min(l['y0'], l['y1']),
            "x1": l['x1'], "y1": max(l['y0'], l['y1']),
            "len": vlen,
        })
    # The flat drop should be ~40% of 7" stack = 2.8" = ~200pt.
    # Threshold: a vertical line ≥ 1/3 of stack height (140pt) that
    # lives within the stack region.
    MIN_FLAT_LEN_PT = 140.0
    flat_drop = [vl for vl in vertical_lines if vl["len"] >= MIN_FLAT_LEN_PT]
    if not flat_drop:
        failures.append({
            "gate": "stack-anatomy",
            "issue": f"no continuous front-face segment ≥ "
                     f"{MIN_FLAT_LEN_PT}pt found "
                     f"(R5 flat-drop violation; "
                     f"need vertical line ≥ 1/3 of stack height)",
            "longest_vertical_pt": max((vl["len"] for vl in vertical_lines),
                                       default=0),
        })
    # (d) Hem bar: vertical, in fabric plane (≈ x_front ± 20pt).
    # The hem bar is a rect (filled+stroked) with width < 8pt
    # and height ≥ 8pt, positioned near the bottom of the stack
    # region. (Golden source's hem bar is 3.6pt × 11pt in detail,
    # and the main-stack hem bar is 2.16pt × 11pt.)
    # The hem bar can be ANYWHERE in the side section viewport
    # (main stack OR detail A callout) — just needs to be a
    # vertical thin rect (R8: vertical, in fabric plane).
    hem_bars = []
    for f in flaps:
        if f["h"] < 8.0 or f["w"] > 8.0:
            continue   # not hem-bar-shaped (vertical thin)
        hem_bars.append(f)
    if not hem_bars:
        failures.append({
            "gate": "stack-anatomy",
            "issue": "no vertical hem-bar rect found in side section "
                     "(R8 violation; need vertical thin rect, in the "
                     "fabric plane, near the bottom of the stack)",
        })
    return failures


# ── CORRECTION 5 — Title + witness integrity gate ──────────────
#
# (a) Sheet title must read FLAT FOLD ROMAN SHADE (singular).
# (b) The elevation's dimension witnesses (38" bottom, 64" right,
#     9 @ 7-1/8" left) must all be present and anchored to features.


def _check_title_and_witnesses(page, family: str = "Roman Shades") -> list[dict]:
    """Gate 5: title exact-match + three witnesses present and
    anchored.

    pdfplumber uses BL origin (y0 from page BOTTOM). The header
    band canvas y ∈ [PAGE_H - MARGIN - HEADER_BAND, PAGE_H - MARGIN]
    = pdfplumber y0 ∈ [PAGE_H*72 - (MARGIN+HEADER_BAND)*72, PAGE_H*72 - MARGIN*72]
    = [566.4, 642.6] (approximately).

    Family-aware: Roman Shades has the title "FLAT FOLD ROMAN SHADE"
    + 38" width / 9 @ 7-1/8" folds / 64" SHADE height witnesses.
    Other families (e.g. Drapery) use family-specific title +
    family-appropriate dimensions. The witnesses for non-Roman
    families are SKIPPED (the gate is silent for them — the
    family-specific row in the title column conveys the
    dimension info).
    """
    failures = []
    text = "".join(c["text"] for c in page.chars)
    # (a) Title — must be singular. Look in the header band y-range.
    header_y0_min = (PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN) * 72
    header_y0_max = (PAGE_H_IN - MARGIN_IN) * 72
    top_chars = [c for c in page.chars
                 if header_y0_min - 5 <= c["y0"] <= header_y0_max + 5]
    top_text = "".join(c["text"] for c in top_chars)
    # Roman-shades title must be singular (Correction 5a):
    # "FLAT FOLD ROMAN SHADE" (no trailing 'S').
    if "FLAT FOLD ROMAN SHADES" in top_text:
        failures.append({
            "gate": "title-singular",
            "issue": "title is PLURAL 'SHADES' (Correction 5a fix — "
                     "must be singular)",
            "top_text": top_text,
        })
    # Roman-shades title must be present (other families can have
    # their own title via title_override).
    if family == "Roman Shades" and "FLAT FOLD ROMAN SHADE" not in top_text:
        failures.append({
            "gate": "title-singular",
            "issue": "'FLAT FOLD ROMAN SHADE' (singular) not found "
                     "in header band",
            "top_text": top_text,
        })
    # (b) Witnesses — Roman-shades specific (38", 9 @ 7-1/8",
    # 64" SHADE). Other families have their own family-specific
    # dimensions and don't need these witnesses.
    if family != "Roman Shades":
        return failures
    # Front-elev viewport: canvas x ∈ [FRONT_X_IN, FRONT_X_IN+FRONT_W_IN],
    # canvas y ∈ [FRONT_Y_IN, FRONT_Y_IN+FRONT_H_IN] → pdfplumber
    # y0 ∈ [FRONT_Y_IN*72, (FRONT_Y_IN+FRONT_H_IN)*72].
    # The right-side dim chain extends beyond the viewport
    # (xd_right = wx1_in + 0.40 = 5.15 — outside viewport x_max
    # 5.05), so the gate widens the search to include the
    # witness extension area up to the title column boundary.
    front_y0_min = FRONT_Y_IN * 72
    front_y0_max = (FRONT_Y_IN + FRONT_H_IN) * 72
    front_x_min = FRONT_X_IN * 72 - 5
    # Allow up to 0.5" beyond viewport x_max for witness extensions
    front_x_max = (FRONT_X_IN + FRONT_W_IN + 0.5) * 72
    front_chars = [c for c in page.chars
                   if front_x_min <= c["x0"] <= front_x_max
                   and front_y0_min - 5 <= c["y0"] <= front_y0_max + 5]
    front_text = "".join(c["text"] for c in front_chars)
    if "38\"" not in front_text:
        failures.append({"gate": "witness-bottom",
                         "issue": "'38\"' (width witness) missing from front-elev"})
    if "9 @ 7-1/8\"" not in front_text:
        failures.append({"gate": "witness-left-folds",
                         "issue": "'9 @ 7-1/8\"' (left fold witness) missing"})
    if not (re.search(r'64"\s*SHADE', front_text, re.IGNORECASE)
            or (re.search(r'64"', front_text) and "SHADE" in front_text)):
        failures.append({"gate": "witness-right-height",
                         "issue": "'64\" SHADE' (height witness) missing",
                         "front_text": front_text[:300]})
    return failures


# ── CORRECTION G1.3 — Text bounds gate ──────────────────────────────
#
# Founder note from G1.3: text still overflows text boxes in places.
# Every rendered text bbox must sit fully inside its owning
# frame/viewport with ≥ 0.06" margin. Overflowing text shrinks or
# wraps, never clips or spills.
#
# Zones checked:
#   - Header band: y in [PAGE_H - MARGIN - HEADER_BAND_H, PAGE_H - MARGIN]
#   - Footer band: y in [MARGIN, MARGIN + FOOTER_BAND_H]
#   - Front-elev viewport: x ∈ [FRONT_X_IN, FRONT_X_IN+FRONT_W_IN],
#     y ∈ [FRONT_Y_IN, FRONT_Y_IN+FRONT_H_IN]
#   - Side-section viewport: same logic
#   - Title column: x ∈ [TITLE_X_IN, TITLE_X_IN+TITLE_W_IN],
#     y ∈ [TITLE_Y_IN, TITLE_Y_IN+TITLE_H_IN]
# Chars in the header/footer are bounded by the band; chars in
# the viewports are bounded by the viewport frame. Tolerance:
# 0.06" inside each edge (per founder directive).

def _check_text_bounds(page) -> list[dict]:
    """Gate 6 (Step 0 / G1.3): every rendered text bbox must
    sit fully inside its owning frame/viewport with ≥ 0.06" margin.

    pdfplumber's `x0, x1, y0, y1` for chars are in BL-canvas
    points (y0 = BOTTOM of char bbox). We need to map each char
    to the zone it's drawn in (header / footer / front-elev /
    side-section / title column) by canvas x/y, then assert the
    char bbox sits ≥ MARGIN_BOUND (0.06") inside the zone edges.

    Negative fixture: a synthetic PDF that draws text past the
    right page margin (e.g. a very long row in the title column)
    must FAIL this gate.
    """
    failures = []
    MARGIN_BOUND = 0.06  # inches — char bbox must be ≥ this far
                          # inside each zone edge

    # Helper: compute char bbox in canvas inches (BL).
    def _char_bbox_in(c):
        x0 = c["x0"] / 72.0
        x1 = c.get("x1", c["x0"]) / 72.0
        y0 = c["y0"] / 72.0
        y1 = c.get("y1", c["y0"]) / 72.0
        return x0, y0, x1, y1

    # Define zones in canvas BL inches.
    zones = []

    # Header band: y ∈ [PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN,
    #                     PAGE_H_IN - MARGIN_IN]
    zones.append({
        "name": "header",
        "x0": MARGIN_IN,
        "y0": PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN,
        "x1": PAGE_W_IN - MARGIN_IN,
        "y1": PAGE_H_IN - MARGIN_IN,
    })
    # Footer band
    zones.append({
        "name": "footer",
        "x0": MARGIN_IN,
        "y0": MARGIN_IN,
        "x1": PAGE_W_IN - MARGIN_IN,
        "y1": MARGIN_IN + FOOTER_BAND_H_IN,
    })
    # Front-elev viewport
    zones.append({
        "name": "front-elev",
        "x0": FRONT_X_IN,
        "y0": FRONT_Y_IN,
        "x1": FRONT_X_IN + FRONT_W_IN,
        "y1": FRONT_Y_IN + FRONT_H_IN,
    })
    # Side-section viewport
    zones.append({
        "name": "side-section",
        "x0": SIDE_X_IN,
        "y0": SIDE_Y_IN,
        "x1": SIDE_X_IN + SIDE_W_IN,
        "y1": SIDE_Y_IN + SIDE_H_IN,
    })
    # Title column
    zones.append({
        "name": "title-column",
        "x0": TITLE_X_IN,
        "y0": TITLE_Y_IN,
        "x1": TITLE_X_IN + TITLE_W_IN,
        "y1": TITLE_Y_IN + TITLE_H_IN,
    })

    # For each char, find its owning zone (first zone whose bbox
    # contains the char's center, in BL coords) and check bounds.
    overflow_count = 0
    for c in page.chars:
        cx0, cy0, cx1, cy1 = _char_bbox_in(c)
        # Char CENTER
        cx_c = (cx0 + cx1) / 2.0
        cy_c = (cy0 + cy1) / 2.0
        # Skip chars outside any zone — they may be in the header
        # right band, footer band, or other. Try each zone; the
        # one containing the center is the owning zone.
        owning = None
        for z in zones:
            if z["x0"] <= cx_c <= z["x1"] and z["y0"] <= cy_c <= z["y1"]:
                owning = z
                break
        if owning is None:
            continue
        # Check bounds with MARGIN_BOUND padding (char must be
        # ≥ MARGIN_BOUND inside each edge of the owning zone).
        violations = []
        if cx0 < owning["x0"] + MARGIN_BOUND:
            violations.append(
                f"left edge x={cx0:.3f}\" < "
                f"zone {owning['name']} x0={owning['x0']:.3f}\" "
                f"+ margin {MARGIN_BOUND}\""
            )
        if cx1 > owning["x1"] - MARGIN_BOUND:
            violations.append(
                f"right edge x={cx1:.3f}\" > "
                f"zone {owning['name']} x1={owning['x1']:.3f}\" "
                f"- margin {MARGIN_BOUND}\""
            )
        if cy0 < owning["y0"] + MARGIN_BOUND:
            violations.append(
                f"bottom edge y={cy0:.3f}\" < "
                f"zone {owning['name']} y0={owning['y0']:.3f}\" "
                f"+ margin {MARGIN_BOUND}\""
            )
        if cy1 > owning["y1"] - MARGIN_BOUND:
            violations.append(
                f"top edge y={cy1:.3f}\" > "
                f"zone {owning['name']} y1={owning['y1']:.3f}\" "
                f"- margin {MARGIN_BOUND}\""
            )
        if violations:
            overflow_count += 1
            if overflow_count <= 30:  # cap sample list
                failures.append({
                    "gate": "text-bounds",
                    "issue": f"char '{c['text']}' overflows "
                             f"{owning['name']}: " + "; ".join(violations),
                    "char_bbox_in": (cx0, cy0, cx1, cy1),
                    "owning_zone": owning["name"],
                })
    return failures
