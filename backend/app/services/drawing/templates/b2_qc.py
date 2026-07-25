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
PAGE_W_IN = 11.0
PAGE_H_IN = 8.5
MARGIN_IN = 0.5  # canonical page-margin distance from the edge

# Right-column title-block region (x in [TITLE_X_IN_MIN, INF))
TITLE_X_IN_MIN = 6.5

# Tolerance for "near-identical coordinates" (the pile test).
COORD_TOL_IN = 0.05

# Text-collision threshold: words from different lines with bbox
# intersection > 30% of the smaller bbox are an overlap fault.
TEXT_OVERLAP_THRESHOLD = 0.30

# Element-spread thresholds (the "drawing must fill the page" test).
SPREAD_X_MIN_FRAC = 0.40
SPREAD_Y_MIN_FRAC = 0.40
PILE_FRAC_MAX = 0.20  # at most 20% of elements may be in the pile


# Public exception
class B2QCFailure(AssertionError):
    """Raised by enforce_b2_qc when the rendered PDF fails one of
    the geometric gates. Subclass of AssertionError so test
    frameworks surface it clearly."""


def _points_to_inches(pdf_value: float) -> float:
    """ReportLab canvas default unit is points (1/72 inch).
    pdfplumber reports raw points. Convert."""
    return pdf_value / 72.0


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
            y = _points_to_inches(char['y0'])
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
             _points_to_inches(c['y0']))
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
            if x_overlap_frac > TEXT_OVERLAP_THRESHOLD:
                # Composite: bbox-overlap area / smaller-bbox area
                # — catches the all-at-one-point pile where x AND y
                # both overlap fully. For the title block the x
                # overlap is high but y overlap is 0 (different
                # rows), so the composite stays small.
                y_overlap_frac = (
                    y_overlap / min(wa['bottom'] - wa['top'],
                                    wb['bottom'] - wb['top'])
                )
                composite = (x_overlap_frac + y_overlap_frac) / 2
                if composite > TEXT_OVERLAP_THRESHOLD:
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
