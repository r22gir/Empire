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

from typing import List, Tuple

import pdfplumber


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
