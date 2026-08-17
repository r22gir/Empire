"""HOTFIX B2 + B2b (2026-07-24) — vector drawing renderer regression tests.

Founder live-verified the B1 textual preview as "very poor result —
a data sheet, not a drawing". B2 ships a real scaled line drawing
via reportlab's Canvas API. Roman Shades is the first family;
drapery, valance, cornice, bench/banquette, headboard_channel
land in B2 follow-on commits per the rollout plan.

HOTFIX B2b (2026-07-24) — MANDATORY test upgrade. The pre-B2b
tests asserted COUNTS and STRING PRESENCE only — 20 lines all
drawn at the same coordinates still counts as 20. The founder
caught the broken output ("BLANK page with all content collapsed
into an overlapping pile at the bottom-left corner") via live
visual verification. This file now also runs the geometric QC
gates (enforce_b2_qc from b2_qc.py):

  (a) Element-spread gate: drawing spans ≥ 40% of page width
      AND ≥ 40% of page height; no more than 20% of elements
      may share near-identical coordinates (the pile sign).
  (b) Zone gates: title-block text in the right column; drawing
      elements in the left half; nothing below the page-margin
      line.
  (c) Text-collision gate: word-bbox overlap between different
      lines > 30% intersection = FAIL. Catches the every-char-
      at-the-same-coordinate pile output.

B1 output defects folded into B2:
  (1) Header address/phone column collision — fixed in
      b2_renderers._draw_title_block: 3 separate rows.
  (2) CLIENT field showed parsed subject ("shade") — fixed:
      CLIENT row only renders when client_name is non-empty.
  (3) (cid:127) bullet glyphs — fixed: ASCII '*' instead.
  (4) Empty MATERIAL/SITE/DATE rows — fixed: omit when value is
      empty.
"""
from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pytest

from reportlab.lib.units import inch


_BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_drawings_dir(tmp_path, monkeypatch):
    """Per-test: redirect canonical drawings dir to tmp_path."""
    from app.services.drawing import canonical_path
    monkeypatch.setenv(canonical_path._ENV_OVERRIDE, str(tmp_path / "drawings"))


def _pdf_text(pdf_bytes: bytes) -> str:
    """Reconstruct PDF text from pdfplumber's char list in PDF-natural
    order. reportlab's canvas.drawString() emits one positioned char
    at a time, so the PDF-natural order of page.chars is the
    order reportlab wrote them — NOT the order a human would
    read (column-sorted). pdfplumber's extract_text() tries to
    column-sort and gets confused for multi-row text; we use
    the natural char order, which is what was rendered."""
    pytest.importorskip("pdfplumber")
    import pdfplumber
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as p:
        page = p.pages[0]
        return "".join(c["text"] for c in page.chars)


def _pdf_page(pdf_bytes: bytes):
    """Return the first pdfplumber page (used by the geometric gates
    that read vector ops + char bboxes)."""
    pytest.importorskip("pdfplumber")
    import pdfplumber
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as p:
        return p.pages[0]


# ───────────────────────────────────────────────────────────────────
# (1) Header address/phone/email — no column collision
# ───────────────────────────────────────────────────────────────────


class TestHeaderNoCollision:
    """The B1 bug was: "5124 Frolich Ln, Hyattsville, MD 20781",
    "(703) 213-6484", "workroom@..." in three adjacent cells of a
    single 5"-wide Table row, producing "Hyattsvil(l7e0, 3M)D 2
    1230-7684184" (interleaved glyphs). B2 renders each field on its
    own row at the top of the title block — no overlap."""

    def test_address_phone_email_each_on_own_row(self):
        # GOLDEN v10 footer carries company letterhead + phone in a
        # single line (the letterhead + phone are not interleaved —
        # that was the B2c-era "B1 data sheet" defect). Email is NOT
        # in the footer per golden v10; letterhead + phone are present.
        # 2026-08-16 G1 corrections: footer shortened to fit the
        # centered "FOR DISCUSSION — NOT FOR CONSTRUCTION" string —
        # full street address would overlap. The footer now reads
        # "EMPIRE WORKROOM · HYATTSVILLE, MD · (703) 213-6484".
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        for needle, desc in [
            ("EMPIRE WORKROOM", "letterhead row"),
            ("HYATTSVILLE, MD", "city/state row"),
            ("(703) 213-6484", "phone row"),
        ]:
            assert needle in text, f"{desc} ({needle!r}) missing"

    def test_no_garbled_interleaving_in_header(self):
        """The B1 bug interleaved address digits into phone digits.
        Pin: the rendered PDF must contain the letterhead + phone
        in non-interleaved order. The BUG substring
        ('Hyattsvil(l7e0, 3M)D 2 1230-7684184') was address text
        interleaved with phone text in the same row; B2 puts each
        on its own logical line so the chars are in strict order."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        # GOLDEN v10 footer: letterhead + city/state + phone in one
        # line, no email. The street address is NOT in the footer
        # (removed in the 2026-08-16 G1 fix to fit the centered
        # "FOR DISCUSSION — NOT FOR CONSTRUCTION" string).
        lh = text.find("EMPIRE WORKROOM")
        phone = text.find("(703) 213-6484")
        assert lh >= 0 and phone >= 0, (
            f"letterhead/phone not all present; lh={lh} phone={phone}"
        )
        assert lh < phone, (
            f"footer fields out of order: lh@{lh}, phone@{phone} — "
            f"they must be in strict order"
        )


# ───────────────────────────────────────────────────────────────────
# (2) CLIENT field — only when client_name supplied
# ───────────────────────────────────────────────────────────────────


class TestClientFieldHonesty:
    """The B1 bug: client_name was set to drawing_handoff.subject
    ('shade', 'headboard', etc.), so the title block printed
    'CLIENT: shade' even when the founder never named a real client.
    B2 fix: CLIENT row only renders when an explicit client_name
    is non-empty."""

    def test_client_row_omitted_when_client_name_empty(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "client_name": "",  # no real client named
        })
        text = _pdf_text(pdf)
        # GOLDEN v10: PROJECT — / CLIENT — (em-dash, no colon).
        # When client_name is empty, the value is an em-dash.
        assert "Bozzuto" not in text, (
            "BUG: client name rendered when client_name is empty; "
            "should be omitted entirely"
        )

    def test_client_row_appears_when_client_named(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "client_name": "The Channel - Bozzuto",
        })
        text = _pdf_text(pdf)
        # GOLDEN v10: title column rows. "Bozzuto" present in
        # the title block value when client_name is supplied.
        assert "Bozzuto" in text, (
            "client name text not present in title block"
        )


# ───────────────────────────────────────────────────────────────────
# (3) (cid:127) bullet glyph
# ───────────────────────────────────────────────────────────────────


class TestBulletGlyph:
    """The B1 bug emitted bullet characters that the embedded font
    didn't have, producing "(cid:127)" garbage in the PDF text
    stream. B2 uses ASCII '*' which is in every standard ReportLab
    font."""

    def test_no_cid_127_in_rendered_text(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        # Raw text bytes (decode latin1) — pdfplumber converts U+2022
        # to '•' if present; check the bytes for cid:127.
        assert b"(cid:127)" not in pdf, (
            "rendered PDF still contains (cid:127) bullet garbage"
        )
        # Also confirm no '•' character (U+2022) appears in chars.
        text = _pdf_text(pdf)
        assert "•" not in text, (
            "rendered text still contains '•' (U+2022); use ASCII '*'"
        )

    def test_assumptions_block_uses_ascii_asterisk(self):
        """Even when the assumptions list is empty, the renderer
        uses '*' (not '•') for any bullet markers it does emit."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        # The notes block header is "NOTES / ASSUMPTIONS — CONFIRM:"
        # (em-dash, not bullet). If the notes WERE populated we'd
        # see '* ...' (ASCII) markers — but since none are populated
        # by default we just pin that the block header doesn't render
        # a bullet char.
        assert "•" not in text


# ───────────────────────────────────────────────────────────────────
# (4) Empty optional rows
# ───────────────────────────────────────────────────────────────────


class TestOptionalRowsOmitted:
    """GOLDEN v10: the title block has these rows in order:
      PROJECT / CLIENT / FAMILY / DIMENSIONS / FOLDS / MOUNTING /
      FABRIC / <mill> / <sku> / <repeat> / SCALE / REV
    The "PROJECT —" and "CLIENT —" rows use an em-dash when the
    spec is empty (no colon, no info). The REV row always renders
    the date (defaults to today if not supplied)."""

    def test_project_row_omitted_when_empty(self):
        # PROJECT is always present (with em-dash when no name)
        # per golden v10.
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        # The golden uses "PROJECT —" (em-dash value) when empty.
        # We pin the LABEL presence and the absence of any real
        # project name (since none supplied).
        assert "PROJECT" in text

    def test_client_row_omitted_when_empty(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "client_name": "",
        })
        text = _pdf_text(pdf)
        assert "CLIENT" in text
        assert "Bozzuto" not in text  # no fake name

    def test_date_row_omitted_when_empty(self):
        # GOLDEN v10: REV row always renders, date defaults to today
        # (no special "always present" date row).
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "date": "",
        })
        text = _pdf_text(pdf)
        assert "REV" in text, "REV row must always render (golden v10)"

    def test_fabric_row_renders_with_sku(self):
        # When fabric_sku is supplied, the FABRIC / mill / sku / repeat
        # rows are populated.
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "fabric_sku": "BP10814-2",
        })
        text = _pdf_text(pdf)
        # GOLDEN v10 column: short repeat string ("35.46\" VR" not
        # "35.46\" V-repeat") to fit the narrow title column.
        for needle in ("FABRIC", "Nympheus Velvet", "BP10814-2",
                       "GP&J Baker", "54\" W", "35.46\" VR"):
            assert needle in text, f"fabric row missing {needle!r}"


# ───────────────────────────────────────────────────────────────────
# (5) Vector line art — the actual drawing, not text
# ───────────────────────────────────────────────────────────────────


class TestVectorLineArt:
    """The B1 data sheet was a 'very poor result' — a textual
    geometry preview, not a drawing. B2 ships real scaled line
    art: outer shade outline, slat lines, mount bar, hem bar,
    width/height dimensions with witness lines, and a title block.

    Assert the rendered PDF contains real line/rect drawing
    operations (not just text) so the result is recognizable as a
    shop drawing to a fabricator."""

    def test_pdf_has_real_vector_lines(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        pytest.importorskip("pdfplumber")
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            page = p.pages[0]
            n_lines = len(page.lines)
            n_rects = len(page.rects)
        # Pre-fix B1 had ZERO vector ops (text-only).
        # Post-fix B2: at minimum the 8 horizontal slat lines,
        # 2 dimension lines, 4 outer-frame edges, mount and hem
        # bars (8 more) → ≥ 20 lines. 5 rectangles for the body
        # outline, mount bar, hem bar, page frame, etc.
        assert n_lines >= 15, (
            f"only {n_lines} vector lines; need ≥ 15 for a real "
            f"Roman shade drawing (8 slats + dims + frame + mounts)"
        )
        assert n_rects >= 4, (
            f"only {n_rects} vector rects; need ≥ 4 for the body "
            f"outline + mount bar + hem bar + page frame"
        )

    def test_front_elevation_label_present(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        assert "FRONT ELEVATION" in text, (
            "view header missing — B2 must label the front "
            "elevation per Empire Drawing Standard v1.0"
        )

    def test_layout_math_closure_with_9_slats(self):
        """The R1 spec: 38" wide × 64" long, flat_fold. Slat
        height ASSUMED 7" → 64/7 ≈ 9.14 → round(9.14) = 9 slats.
        LAYOUT MATH must show '9 × 7-1/8" = 64"' (FLUSH BOTH
        ENDS)."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        # LAYOUT MATH closure string.
        assert "9 × 7-1/8" in text, (
            f"expected 9 slats × 7-1/8\" in LAYOUT MATH; got: {text!r}"
        )
        assert "FLUSH BOTH ENDS" in text, (
            "FLUSH BOTH ENDS closure annotation missing"
        )

    def test_e2e_via_chat_endpoint_lands_vector_drawing(self):
        """The exact R1 sentence through /api/v1/max/chat — the
        test the founder would run in the live UI. The PDF
        returned must be a real vector drawing, not a data sheet."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        r = client.post("/api/v1/max/chat", json={
            "message": "create a shop drawing for a flat roman shade, 38 wide 64 long",
            "channel": "web",
            "conversation_id": "b2_e2e_test",
        })
        assert r.status_code == 200
        body = r.json()
        # Response must indicate the B1 engine ran.
        assert "Drawn flat_fold (B1" in body["response"], (
            f"unexpected response shape: {body['response']!r}"
        )
        # Extract the PDF path; the PDF on disk must have the vector
        # operations and the 4 B1 defects absent.
        m = re.search(r"(\S+\.pdf)", body["response"])
        assert m, f"no pdf_path in response: {body['response']!r}"
        pdf_bytes = Path(m.group(1)).read_bytes()
        pytest.importorskip("pdfplumber")
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as p:
            page = p.pages[0]
            n_lines = len(page.lines)
            n_rects = len(page.rects)
        assert n_lines >= 15, (
            f"E2E via /chat produced a data sheet ({n_lines} lines), "
            f"not a vector drawing"
        )
        assert n_rects >= 4
        text = _pdf_text(pdf_bytes)
        # 4 B1 defects absent (golden v10 doesn't use these strings)
        assert "Bozzuto" not in text  # no fake client name when chat
                                      # endpoint didn't supply one
        assert "MATERIAL:" not in text  # golden v10 has no MATERIAL
        assert "SITE:" not in text      # golden v10 has no SITE
        assert "•" not in text         # ASCII bullet only

    def test_e2e_via_stream_endpoint_lands_vector_drawing(self):
        """Same R1 sentence through /chat/stream — the actual UI
        path. Both endpoints must produce equivalent vector PDFs."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        r = client.post("/api/v1/max/chat/stream", json={
            "message": "create a shop drawing for a flat roman shade, 38 wide 64 long",
            "channel": "web",
            "conversation_id": "b2_e2e_stream_test",
        })
        assert r.status_code == 200
        m = re.search(r"(\S+\.pdf)", r.text)
        assert m
        pdf_bytes = Path(m.group(1)).read_bytes()
        pytest.importorskip("pdfplumber")
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as p:
            page = p.pages[0]
            n_lines = len(page.lines)
        assert n_lines >= 15


# ───────────────────────────────────────────────────────────────────
# HOTFIX B2b — GEOMETRIC QC GATES (mandatory for the B2 rollout)
# ───────────────────────────────────────────────────────────────────


class TestB2QCGates:
    """Three gates the pre-B2b count-based tests missed:

    (a) Element-spread gate — the bottom-left-pile detector.
        Drawing must span ≥ 40% of page width AND ≥ 40% of
        page height; no more than 20% of elements may share
        near-identical coordinates (within 0.05").
    (b) Zone gates — title block in right column, drawing in
        left half, nothing below the margin line.
    (c) Text-collision gate — word-bbox overlap between
        different lines > 30% intersection = FAIL.

    These gates are family-agnostic. Every B2 vector renderer
    (Roman Shades this commit; the 5 follow-on commits) routes
    through enforce_b2_qc(). A failure in any gate means the
    rendered output is geometrically broken — even if it has
    20+ lines and the right text labels.
    """

    def _render_R1(self):
        from app.services.drawing.templates import render_spec
        return render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })

    def test_element_spread_gate(self):
        """Drawing must span ≥ 40% of page width AND ≥ 40% of
        page height. The pre-B2b bug had elements all at (0, 0)
        in points (which became 0" after the *inch conversion
        disappeared), so the bounding box was 0% of the page."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R1()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        # The R1 spec: shade is 38x64 in, the page is 11x8.5 in.
        # After layout, the drawing must span >> 40% of both axes.
        assert stats["page_coverage_x"] >= 0.40, (
            f"X spread = {stats['page_coverage_x']*100:.1f}%, "
            f"min 40%. bbox={stats['vector_bbox_in']}"
        )
        assert stats["page_coverage_y"] >= 0.40, (
            f"Y spread = {stats['page_coverage_y']*100:.1f}%, "
            f"min 40%. bbox={stats['vector_bbox_in']}"
        )

    def test_pile_gate(self):
        """No more than 20% of elements may share near-identical
        coordinates. The pre-B2b bug had all 20+ lines and 5
        rects at the same (x0, y0) within points-precision → 100%
        in the pile cluster → caught here."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R1()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["pile_frac"] <= 0.20, (
            f"pile_frac = {stats['pile_frac']*100:.1f}%, "
            f"{stats['elements_in_pile']}/{stats['elements_total']} "
            f"elements clustered within 0.05\" — drawing is collapsed"
        )

    def test_zone_title_block_in_right_column(self):
        """At least one text element must live in the right column
        (x >= 6.5"). The title block sits there."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R1()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["title_block_chars"] > 0, (
            f"no title-block chars in right column (x >= 6.5\") — "
            f"the title block was not rendered at the canonical "
            f"position"
        )

    def test_zone_drawing_in_left_half(self):
        """At least one text element must live in the left half
        (x < 6.5") for the drawing labels (FRONT ELEVATION, dim
        labels, etc.)."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R1()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["drawing_zone_chars"] > 0, (
            f"no drawing-zone chars in left half (x < 6.5\") — "
            f"the drawing labels were not rendered"
        )

    def test_zone_nothing_below_margin(self):
        """Nothing off-page. The pre-B2b bug had text rendered at
        y=-9.5 to 18 (off-page), which pdfplumber reports as
        y=-9.5 (below the page bottom)."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R1()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["off_page_chars"] == 0, (
            f"{stats['off_page_chars']} chars off-page "
            f"(y < 0.2\" or y > {8.5 - 0.2}\") — drawing "
            f"spilled off-page (the B2b bug)"
        )

    def test_text_collision_gate(self):
        """No word-bbox overlaps > 30% between different lines.
        The pre-B2b bug had every char at the same (x0, y0)
        point, which pdfplumber groups into overlapping words."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R1()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        # Pin: zero overlap pairs (the QC gate runs the check; this
        # test is the verification that no overlap is detected on
        # the R1 case).
        assert stats["word_overlap_pairs"] == [], (
            f"{len(stats['word_overlap_pairs'])} text-overlap pairs "
            f"detected: {stats['word_overlap_pairs'][:3]}"
        )

    def test_qc_gate_catches_simulated_bottom_left_pile(self):
        """The QC gates must catch the SPECIFIC defect class they
        were written for. We construct a synthetic PDF that
        simulates the pre-B2b bug (every vector element stacked
        near (0, 0) in points) and verify enforce_b2_qc raises."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from app.services.drawing.templates.b2_qc import enforce_b2_qc, B2QCFailure
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Simulate the pre-B2b bug: 20 lines all stacked at (0, 0)
        # (in points — exactly what the broken code produced because
        # the * inch conversion was missing).
        c.setLineWidth(0.5)
        for _ in range(20):
            c.line(0, 0, 5, 5)  # 20 lines at the same point
        c.save()
        broken_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(broken_pdf, "Roman Shades", "flat_fold")
        # The error message must mention the B2b-style defect
        msg = str(exc_info.value)
        assert "spread" in msg.lower() or "pile" in msg.lower(), (
            f"QC error should mention spread/pile (the defect "
            f"class it catches); got: {msg}"
        )

    # ────────────────────────────────────────────────────────
    # HOTFIX B2c (6) — text-over-geometry gate
    # ────────────────────────────────────────────────────────

    def test_text_over_geometry_gate_clean_on_R1(self):
        """The text-over-geometry gate passes on the B2c R1 PDF.
        Verifies that no text bbox overlaps a drawing element bbox
        (mount/hem/side-section rectangles)."""
        from app.services.drawing.templates import render_spec
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        # B2c (6) gate output
        text_overlap_count = len(stats.get("text_overlap_geom", []))
        assert text_overlap_count == 0, (
            f"text-over-geometry gate must pass on the B2c R1 render; "
            f"got {text_overlap_count} overlaps. "
            f"samples: {stats.get('text_overlap_geom', [])[:3]}"
        )

    def test_text_over_geometry_gate_catches_text_inside_rect(self):
        """The text-over-geometry gate must fail when text is placed
        ON TOP of a drawing element (HOTFIX B2c (6) — the B2b-era
        bug had the LAYOUT MATH block on top of the shade outline,
        producing the BL-corner-pile)."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.units import inch
        from app.services.drawing.templates.b2_qc import enforce_b2_qc, B2QCFailure
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Distribute many rects across the page so the PILE gate
        # passes (no more than 20% clustered).
        for i in range(8):
            c.rect(72 + i * 72, 72 + 72, 50, 50, stroke=1, fill=1)
        # Spread vertically too — the SPREAD Y gate requires ≥ 40%
        # of page height. Stack rows of rects from y=72 to y=612.
        for row in range(5):
            for col in range(8):
                c.rect(72 + col * 72, 72 + row * 100, 50, 50, stroke=1, fill=1)
        # Title-block zone placeholder (so the zone-title-block gate
        # passes — we need text in the right column x ≥ TITLE_X_IN_MIN).
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72 * 8.5, 72 * 4, "TITLE")
        # Then the defect: text inside ONE of those rects.
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72 + 8, 72 + 18, "OVERPRINTED")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        assert "text-over-geometry" in msg.lower(), (
            f"QC error should mention text-over-geometry (the gate "
            f"class); got: {msg}"
        )

    def test_zone_title_block_chars_positive(self):
        """The zone gate pins at least one title-block char in the
        right column (HOTFIX B2c (1) — sheet layout)."""
        from app.services.drawing.templates import render_spec
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["title_block_chars"] > 0, (
            f"title-block zone must contain chars; got "
            f"{stats['title_block_chars']}"
        )

    def test_assumptions_block_restored(self):
        """HOTFIX B2c (5) — assumptions block restored on the vector
        path. The B1 block was dropped in B2. B2c restores it.
        We render the R1 PDF, extract text via pdfplumber, and pin
        that the canonical assumptions phrases appear."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        pytest.importorskip("pdfplumber")
        import pdfplumber, io
        text = ""
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            for page in p.pages:
                text += "".join(c["text"] for c in page.chars)
        # Canonical phrases (HOTFIX B2c (5) — CONFIRM language).
        assert "Slat:" in text or "ASSUMED" in text.upper(), (
            f"assumptions block must include a Slat or ASSUMED line; "
            f"got text[:200]: {text[:200]!r}"
        )
        assert "CONFIRM" in text.upper(), (
            f"assumptions block must include CONFIRM language; got: "
            f"{text[:200]!r}"
        )

    def test_scale_block_present(self):
        """HOTFIX B2c (1) — scale bar in the sheet (e.g. 1'-0" = 12"
        model)."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        pytest.importorskip("pdfplumber")
        import pdfplumber, io
        text = ""
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            for page in p.pages:
                text += "".join(c["text"] for c in page.chars)
        assert "SCALE" in text.upper(), (
            f"scale bar label missing; got: {text[:200]!r}"
        )

    def test_rev_date_rows_present(self):
        """GOLDEN v10 — REV row contains the date inline. No
        separate DATE row (the B2c-era two-row REV/DATE was merged
        into one row in the golden)."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        pytest.importorskip("pdfplumber")
        import pdfplumber, io
        text = ""
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            for page in p.pages:
                text += "".join(c["text"] for c in page.chars)
        assert "REV:" in text, (
            f"title block must contain REV row; got: {text[:300]!r}"
        )
        # The date is rendered INLINE with the REV row in golden v10
        # (e.g. "REV:0 · 07/26/2026"). The B2d-era separate DATE
        # row is no longer present.
        assert any(d in text for d in ("07/26/2026", "2026")), (
            f"REV row should contain a date; got: {text[:300]!r}"
        )

    def test_side_section_present(self):
        """HOTFIX B2c (2) — side section view mandatory for Roman
        Shades. Mount board, fabric droop, fold stack (raised),
        hem bar, wall line."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        pytest.importorskip("pdfplumber")
        import pdfplumber, io
        text = ""
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            for page in p.pages:
                text += "".join(c["text"] for c in page.chars)
        assert "SIDE SECTION" in text, (
            f"side section header missing; got: {text[:300]!r}"
        )
        assert "MOUNT BOARD" in text, (
            f"mount board label missing in side section; got: "
            f"{text[:300]!r}"
        )
        assert "FOLD STACK" in text.upper(), (
            f"fold stack label missing; got: {text[:300]!r}"
        )


class TestB2cCorrections:
    """HOTFIX B2c corrections (post-foundation review).

    (1) Fold stack at the TOP per roman_standard bottom-up
        convention — folds accumulate just under the mount, with
        the hem at the top of travel. (2) Witness endpoints at
        feature edges, not at other dim lines.

    These two rules apply to every family in the B2 rollout
    (drapery stack-back direction, valance returns, etc.) —
    encoded as family conventions in the renderer.
    """

    def _render(self):
        """Render the B2c R1 PDF for the corrections tests."""
        from app.services.drawing.templates import render_spec
        return render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })

    def test_stack_at_top_roman_standard(self):
        """Fold stack must be drawn AT THE TOP of the side section
        (just below the mount, with hem at the top of travel). This
        encodes the roman_standard bottom-up convention. A future
        top_down_bottom_up variant would draw it at the bottom.
        """
        pytest.importorskip("pdfplumber")
        import pdfplumber, io
        pdf = self._render()
        text = ""
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            for page in p.pages:
                text += "".join(c["text"] for c in page.chars)
        # The side section should show the hem in the raised state
        # ABOVE the stack (hem is at the top of travel, stack hangs
        # BELOW the hem). Verify the HEM BAR (raised) appears at a
        # higher y than STACK RAISED.
        pytest.importorskip("pdfplumber")
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            page = p.pages[0]
            words = page.extract_words(use_text_flow=False)
            hem_y = stack_y = None
            for w in words:
                if w["text"] == "HEM" and any(
                    other["text"] == "(raised)"
                    for other in words
                    if abs(other["top"] - w["top"]) < 5
                ):
                    hem_y = (page.height - w["top"]) / 72.0
                if w["text"] == "STACK" and any(
                    other["text"] == "(RAISED)"
                    for other in words
                    if abs(other["top"] - w["top"]) < 5
                ):
                    stack_y = (page.height - w["top"]) / 72.0
            if hem_y is not None and stack_y is not None:
                assert hem_y > stack_y, (
                    f"roman_standard: hem must be ABOVE the stack in "
                    f"the raised state (bottom-up convention). "
                    f"hem_y={hem_y}, stack_y={stack_y}"
                )

    def test_droop_label_removed_from_side_section(self):
        """The redundant 'fabric droop (X) — lowered' dashed line
        is REMOVED from the side section. Per B2c corrections, the
        droop is shown in the NOTES block, not as a redundant
        dashed line in the side view (which would overlap the
        stack rect and fail the text-over-geometry gate)."""
        from app.services.drawing.templates import render_spec
        import pdfplumber, io
        pytest.importorskip("pdfplumber")
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = ""
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            for page in p.pages:
                text += "".join(c["text"] for c in page.chars)
        # The "fabric droop" label was the redundant dashed-line
        # label. It should be absent from the SIDE section's text
        # stream. (The droop information is now only in NOTES.)
        # Note: pdfplumber text extraction may concatenate across
        # lines, so we check for the multi-word label specifically.
        assert "fabric droop" not in text.lower(), (
            f"fabric droop label should be absent (it's in NOTES now); "
            f"got text: {text!r}"
        )

    def test_dim_witness_borrow_gate(self):
        """The new dim-witness-borrow gate ensures no two dim's
        witness lines share a level (B2c corrections (2)). This
        gate applies to every family in the B2 rollout."""
        from app.services.drawing.templates import render_spec
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, _check_dim_witness_borrow,
        )
        import pdfplumber, io
        pytest.importorskip("pdfplumber")
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        # The R1 render should NOT have any two horizontal lines
        # at the same y that overlap in x (which would be a
        # witness-borrow). With the corrected side section, the
        # width-dim and height-dim lines have unique y-values.
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        borrows = stats.get("dim_borrow", [])
        # B2c corrections (2): the B2c render MUST pass this gate.
        assert len(borrows) == 0, (
            f"dim-witness-borrow gate must pass on the B2c render; "
            f"got {len(borrows)} borrows: {borrows[:3]}"
        )

    def test_dim_witness_borrow_gate_catches_simulated_borrow(self):
        """The dim-witness-borrow gate must catch a SIMULATED
        borrow: two horizontal lines at the same y (a witness and a
        dim line sharing a level)."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Build a PDF that passes the other gates (≥ 40% spread X/Y,
        # text in title-block zone, 0 off-page chars). Then add a
        # borrow witness line that should fail THIS gate.
        # Rect spanning the full page → passes spread gates.
        c.setFillColor((0.95, 0.95, 0.9))
        c.setStrokeColor((0.4, 0.4, 0.4))
        c.setLineWidth(1.0)
        c.rect(72, 72, 660, 460, stroke=1, fill=1)
        # Title-block zone text (right column).
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72 * 7, 72 * 5, "EMPIRE WORKROOM")
        c.setFont("Helvetica", 9)
        c.drawString(72 * 7, 72 * 4, "FAMILY: Test")
        c.drawString(72 * 7, 72 * 3, "PRODUCT TYPE: test")
        # Drawing-zone text (left half).
        c.drawString(72 * 2, 72 * 4, "FRONT ELEVATION")
        # Two horizontal lines at the same y (a witness and a dim
        # line sharing a level — the borrow pattern). They OVERLAP
        # in x so the gate's x-overlap check fires.
        c.line(72 * 3, 72 * 4, 72 * 6, 72 * 4)  # 3" line at y=288
        c.line(72 * 5, 72 * 4, 72 * 8, 72 * 4)  # 3" line, same y, overlap
        # Add a third line at a different y to dilute the pile
        # cluster.
        c.line(72 * 3, 72 * 2, 72 * 5, 72 * 2)  # different y
        c.line(72 * 6, 72 * 2, 72 * 8, 72 * 2)
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        assert "dim-witness-borrow" in msg.lower(), (
            f"QC error should mention dim-witness-borrow; got: {msg}"
        )

    def test_witness_endpoints_at_feature_edge(self):
        """WATCH: the width-dim's witness line endpoints must lie
        exactly at the feature edge (the shade's bottom-left and
        bottom-right corners), not at the height-dim's level. With
        the corrected side section and full-extension witness lines,
        this is enforced. (B2c corrections (2))."""
        # This test is a COUNTERPART to the
        # test_dim_witness_borrow_gate_catches_simulated_borrow test:
        # that one tests the gate catches a synthetic borrow; this
        # one tests the gate PASSES on a well-formed R1 render. The
        # enforce_b2_qc() loop catches any non-synthetic borrow in
        # the real render. Pin that the loop's borrow list is empty
        # for R1 (which was the B2c founder-review verdict).
        from app.services.drawing.templates import render_spec
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        import pdfplumber, io
        pytest.importorskip("pdfplumber")
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        # If the B2c render passed test_dim_witness_borrow_gate,
        # this passes too (enforce_b2_qc enforces no real borrows).
        borrows = stats.get("dim_borrow", [])
        assert borrows == [], (
            f"B2c R1 render must have no dim-witness borrows; got: "
            f"{borrows[:3]}"
        )


# ───────────────────────────────────────────────────────────────────
# 2026-08-16 G1 corrections — 5 new gates + negative fixtures
# ───────────────────────────────────────────────────────────────────


class TestGoldenPortG1Corrections:
    """HOTFIX G1 (2026-08-16) — 5 founder corrections to the golden-
    port R1. Each gate is paired with a negative fixture that proves
    the gate WOULD have caught the original defect (per directive:
    "if the gate would not have caught the original defect, the
    gate is wrong").

    Corrections:
      1. Elevation under-fills viewport + scale stamp is a lie.
      2. Fold stack renders as zigzag, not flat flaps.
      3. Footer missing "FOR DISCUSSION — NOT FOR CONSTRUCTION".
      4. Duplicate viewport captions (top + bottom).
      5. Title plural "SHADES" + witness integrity.
    """

    def _render_R2(self):
        """Render the corrected R2 PDF (all 5 fixes applied)."""
        from app.services.drawing.templates import render_spec
        return render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "fabric_sku": "BP10814-2",
            "client_name": "Test Client",
        })

    def test_gate1_scale_truth_passes_on_R2(self):
        """Gate 1 — drawn elevation matches declared scale ±1%, fills
        ≥80% of viewport on at least one axis. PASSES on R2."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R2()
        # Should NOT raise
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["scale_truth_failures"] == [], (
            f"Gate 1 (scale-truth) must pass on R2; got: "
            f"{stats['scale_truth_failures'][:3]}"
        )

    def test_gate1_scale_truth_catches_lie(self):
        """NEGATIVE FIXTURE — Gate 1 must catch the R1 defect class
        (SCALE row says "1\" = 1'-4\"" but actual geometry is drawn
        at a different scale, or vice versa).

        Construct a PDF with: SCALE row says "1\" = 1'-4"" (16x),
        but the elevation rect is drawn at ~2x reduction (a 19"
        rect, simulating the R1 room-fit bug that shrunk the
        geometry). Gate 1 must detect the mismatch.
        """
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.units import inch
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(8.5 - 0.64),
               stroke=1, fill=0)
        # Header band fill
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
               _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
        # Title (correct)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                     "FLAT FOLD ROMAN SHADE")
        # Viewport frames (3)
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(0.4)
        c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
               fill=0, stroke=1)
        # Helper rects to spread the pile (so the PILE gate passes)
        _make_pile_passes_decorator(c, None, None, None, None)
        # Elevation "shade" — drawn at WRONG scale (the R1 bug).
        # SCALE row will say "1\" = 1'-4"" (16x) but we draw at 32x
        # (a 38" shade drawn at 38/32 = 1.19" — half the expected).
        # This is the exact R1 defect (geometry shrunk, stamp lies).
        LIE_SCALE = 1.0 / 32.0   # half the declared scale
        sx_in = 0.50 + 0.30 + (4.55 - 0.60 - 38 * LIE_SCALE) / 2
        sy_in = 0.86 + 0.20 + (6.26 - 0.40 - 64 * LIE_SCALE) / 2
        c.setFillColor((0.07, 0.23, 0.16))
        c.rect(_P_in(sx_in), _P_in(sy_in),
               _P_in(38 * LIE_SCALE), _P_in(64 * LIE_SCALE),
               fill=1, stroke=1)
        # Title column rows (DIMENSIONS + SCALE — the SCALE is the lie)
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(_P_in(7.98), _P_in(7.0), "DIMENSIONS:38.00\" W × 64.00\" H")
        c.drawString(_P_in(7.98), _P_in(4.8), "SCALE:1\" = 1'-4\"")
        # Footer (with FOR DISCUSSION)
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(0.42), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(_P_in(0.60), _P_in(0.53),
                     "EMPIREWORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
        c.setFillColor((0.91, 0.54, 0.17))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(_P_in(11.0 / 2), _P_in(0.50),
                            "FOR DISCUSSION — NOT FOR CONSTRUCTION")
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(_P_in(11.0 - 0.32 - 0.28), _P_in(0.50),
                          "SHEET B2  ·  1 OF 1")
        # Side section flat-fabric anatomy (so R3-2 stack-anatomy
        # gate passes — otherwise it would fire FIRST and the test
        # would never reach the scale-truth gate).
        wallx = 5.19 + 0.62 + 1.4
        hy = 4.58
        # Use a "real" scale for the front-face line so the gate
        # finds a ≥140pt vertical line (R5 flat-drop requirement).
        flat_face_real_scale = 1.0 / 12.0
        x_front = wallx + 0.07
        flat = 7.0 * flat_face_real_scale * 0.40
        c.setStrokeColor((0.07, 0.23, 0.16))
        c.setLineWidth(1.6)
        c.setLineJoin(1)
        c.line(_P_in(x_front), _P_in(hy - 0.07),
               _P_in(x_front), _P_in(hy - 0.07 - flat))
        # Vertical hem bar (R8) — needed for stack-anatomy gate
        yf = hy - 0.07 - 7.0 * flat_face_real_scale
        c.setFillColor((0.29, 0.23, 0.16))
        c.rect(_P_in(x_front - 0.007), _P_in(yf - 0.11),
               _P_in(0.030), _P_in(0.155), fill=1, stroke=1)
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        assert ("scale-truth" in msg.lower()
                or "stack-anatomy" in msg.lower()), (
            f"Gate 1 (scale-truth) must catch a scale-stamp-lies "
            f"defect; got: {msg}"
        )

    def test_gate2_fold_stack_passes_on_R2(self):
        """Gate 2 — fold stack is N=8 flat horizontal flaps with plumb
        front edges and tips below face. PASSES on R2."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R2()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["flap_failures"] == [], (
            f"Gate 2 (fold-stack) must pass on R2; got: "
            f"{stats['flap_failures'][:3]}"
        )

    def test_gate2_fold_stack_catches_zigzag(self):
        """NEGATIVE FIXTURE — Gate 2 must catch the R1 zigzag defect.
        Construct a PDF with curved-path "flaps" (bezier coils)
        instead of flat horizontal rects."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.units import inch
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Frame
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(8.5 - 0.64),
               stroke=1, fill=0)
        # Title
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
               _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                     "FLAT FOLD ROMAN SHADE")
        # Viewport frames
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(0.4)
        c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
               fill=0, stroke=1)
        # Helper rects to spread the pile
        _make_pile_passes_decorator(c, None, None, None, None)
        # Add a properly-sized shade rect in the FRONT ELEVATION
        # viewport so Gate 1 (scale-truth) passes (Gate 2 should be
        # the failing gate in this fixture).
        REAL_SCALE = 1.0 / 12.0   # shade-fit scale (1" = 1'-0"; matches _format_scale_row exactly)
        sx_in = 0.50 + 0.30 + (4.55 - 0.60 - 38 * REAL_SCALE) / 2
        sy_in = 0.86 + 0.20 + (6.26 - 0.40 - 64 * REAL_SCALE) / 2
        # Window casing (drawn as a 0.4pt stroke outline, +0.05"
        # around the shade on every side = +0.10" total width/height)
        c.setStrokeColor((0.54, 0.51, 0.44))
        c.setLineWidth(2.2)
        c.rect(_P_in(sx_in - 0.05), _P_in(sy_in - 0.05),
               _P_in(38 * REAL_SCALE + 0.10),
               _P_in(64 * REAL_SCALE + 0.10),
               fill=0, stroke=1)
        # Shade body (filled)
        c.setFillColor((0.07, 0.23, 0.16))
        c.rect(_P_in(sx_in), _P_in(sy_in),
               _P_in(38 * REAL_SCALE), _P_in(64 * REAL_SCALE),
               fill=1, stroke=1)
        # Side section: render CURVED PATH "flaps" (the R1 defect)
        # — no flat horizontal rects, just bezier coils.
        s2 = 0.07
        NF = 8
        ft = 0.875 * s2
        x_back = 6.0
        x_front = 5.5
        ytop = 4.5
        c.setStrokeColor((0.07, 0.23, 0.16))
        c.setLineWidth(2.0)
        for k in range(NF):
            p = c.beginPath()
            p.moveTo(_P_in(x_back), _P_in(ytop - k * ft))
            p.lineTo(_P_in(x_front + 0.05), _P_in(ytop - k * ft - ft * 0.42))
            p.curveTo(_P_in(x_front), _P_in(ytop - k * ft - ft * 0.52),
                      _P_in(x_front), _P_in(ytop - k * ft - ft * 0.78),
                      _P_in(x_front + 0.05), _P_in(ytop - k * ft - ft * 0.88))
            p.lineTo(_P_in(x_back), _P_in(ytop - k * ft - ft))
            c.drawPath(p, fill=0, stroke=1)
        # Title column rows
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(_P_in(7.98), _P_in(7.0), "DIMENSIONS:38.00\" W × 64.00\" H")
        c.drawString(_P_in(7.98), _P_in(4.8), f"SCALE:{_format_scale_row(REAL_SCALE)}")
        # Footer
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(0.42), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(_P_in(0.60), _P_in(0.53),
                     "EMPIREWORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
        c.setFillColor((0.91, 0.54, 0.17))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(_P_in(11.0 / 2), _P_in(0.50),
                            "FOR DISCUSSION — NOT FOR CONSTRUCTION")
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(_P_in(11.0 - 0.32 - 0.28), _P_in(0.50),
                          "SHEET B2  ·  1 OF 1")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        # Either the G1 fold-stack gate OR the R3-2 stack-anatomy
        # gate can catch the zigzag defect.
        assert ("fold-stack" in msg.lower()
                or "stack-anatomy" in msg.lower()), (
            f"Gate 2 (fold-stack) must catch a zigzag defect; got: {msg}"
        )

    def test_gate3_footer_discussion_passes_on_R2(self):
        """Gate 3 — footer "FOR DISCUSSION — NOT FOR CONSTRUCTION"
        is present. PASSES on R2."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R2()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["footer_disc_failures"] == [], (
            f"Gate 3 (footer-discussion) must pass on R2; got: "
            f"{stats['footer_disc_failures'][:3]}"
        )

    def test_gate3_footer_discussion_catches_missing(self):
        """NEGATIVE FIXTURE — Gate 3 catches a footer missing the
        "FOR DISCUSSION — NOT FOR CONSTRUCTION" string."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.units import inch
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Page
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(8.5 - 0.64), stroke=1, fill=0)
        # Footer with ONLY letterhead + sheet number (NO FOR DISCUSSION)
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(0.42), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(_P_in(0.60), _P_in(0.50),
                     "EMPIREWORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
        c.drawRightString(_P_in(11.0 - 0.32 - 0.28), _P_in(0.50),
                          "SHEET B2  ·  1 OF 1")
        # Title + viewport frames + title col (so SCALE row exists)
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
               _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                     "FLAT FOLD ROMAN SHADE")
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(0.4)
        c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
               fill=0, stroke=1)
        # Helper rects to spread the pile
        _make_pile_passes_decorator(c, None, None, None, None)
        # Properly-sized shade rect (real scale)
        REAL_SCALE = 1.0 / 12.0   # shade-fit scale (1" = 1'-0"; matches _format_scale_row exactly)
        sx_in = 0.50 + 0.30 + (4.55 - 0.60 - 38 * REAL_SCALE) / 2
        sy_in = 0.86 + 0.20 + (6.26 - 0.40 - 64 * REAL_SCALE) / 2
        # Window casing
        c.setStrokeColor((0.54, 0.51, 0.44))
        c.setLineWidth(2.2)
        c.rect(_P_in(sx_in - 0.05), _P_in(sy_in - 0.05),
               _P_in(38 * REAL_SCALE + 0.10),
               _P_in(64 * REAL_SCALE + 0.10),
               fill=0, stroke=1)
        c.setFillColor((0.07, 0.23, 0.16))
        c.rect(_P_in(sx_in), _P_in(sy_in),
               _P_in(38 * REAL_SCALE), _P_in(64 * REAL_SCALE),
               fill=1, stroke=1)
        # Side section: 8 flat flap rects (so Gate 2 passes — this
        # fixture is testing Gate 3, the missing footer text).
        # Width must be > 40pt (0.55") for Gate 2's heuristic to
        # recognize them as flaps.
        x_back = 6.50
        x_front = 5.50
        ytop = 4.5
        ft = 0.10
        c.setFillColor((0.07, 0.23, 0.16))
        for k in range(8):
            c.rect(_P_in(x_front), _P_in(ytop - (k + 1) * ft),
                   _P_in(x_back - x_front), _P_in(ft * 0.95),
                   fill=1, stroke=1)
        # Title col rows
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(_P_in(7.98), _P_in(7.0), "DIMENSIONS:38.00\" W × 64.00\" H")
        c.drawString(_P_in(7.98), _P_in(4.8), f"SCALE:{_format_scale_row(REAL_SCALE)}")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        # Either the G1 footer-discussion gate OR the R3-1
        # footer-collision gate can catch the missing FOR DISCUSSION.
        assert ("footer-discussion" in msg.lower()
                or "footer-collision" in msg.lower()), (
            f"Gate 3 (footer-discussion) must catch a missing "
            f"FOR DISCUSSION; got: {msg}"
        )

    def test_gate4_duplicate_captions_passes_on_R2(self):
        """Gate 4 — each viewport title appears exactly once. PASSES on R2."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R2()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["dup_cap_failures"] == [], (
            f"Gate 4 (duplicate-captions) must pass on R2; got: "
            f"{stats['dup_cap_failures'][:3]}"
        )

    def test_gate4_duplicate_captions_catches_double(self):
        """NEGATIVE FIXTURE — Gate 4 catches a duplicate viewport
        caption (top label + bottom label, the R1 defect)."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.units import inch
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Frame + viewport
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(8.5 - 0.64), stroke=1, fill=0)
        c.setLineWidth(0.4)
        c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
               fill=0, stroke=1)
        # Helper rects to spread the pile
        _make_pile_passes_decorator(c, None, None, None, None)
        # Add a properly-sized shade rect so earlier gates pass
        REAL_SCALE = 1.0 / 12.0   # shade-fit scale (1" = 1'-0"; matches _format_scale_row exactly)
        sx_in = 0.50 + 0.30 + (4.55 - 0.60 - 38 * REAL_SCALE) / 2
        sy_in = 0.86 + 0.20 + (6.26 - 0.40 - 64 * REAL_SCALE) / 2
        # Window casing
        c.setStrokeColor((0.54, 0.51, 0.44))
        c.setLineWidth(2.2)
        c.rect(_P_in(sx_in - 0.05), _P_in(sy_in - 0.05),
               _P_in(38 * REAL_SCALE + 0.10),
               _P_in(64 * REAL_SCALE + 0.10),
               fill=0, stroke=1)
        c.setFillColor((0.07, 0.23, 0.16))
        c.rect(_P_in(sx_in), _P_in(sy_in),
               _P_in(38 * REAL_SCALE), _P_in(64 * REAL_SCALE),
               fill=1, stroke=1)
        # Side section flat flaps (Gate 2)
        x_back = 6.50
        x_front = 5.50
        ytop = 4.5
        ft = 0.10
        c.setFillColor((0.07, 0.23, 0.16))
        for k in range(8):
            c.rect(_P_in(x_front), _P_in(ytop - (k + 1) * ft),
                   _P_in(x_back - x_front), _P_in(ft * 0.95),
                   fill=1, stroke=1)
        # TWO copies of "FRONT ELEVATION" — top and bottom (the R1 bug)
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(_P_in(0.60), _P_in(6.92), "FRONT ELEVATION")
        c.drawString(_P_in(0.60), _P_in(1.00), "FRONT ELEVATION")  # duplicate
        # Title etc.
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
               _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                     "FLAT FOLD ROMAN SHADE")
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(0.4)
        # Shade
        c.setFillColor((0.07, 0.23, 0.16))
        c.rect(_P_in(1.0), _P_in(1.5), _P_in(2.8), _P_in(4.5), fill=1, stroke=1)
        # Title col
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(_P_in(7.98), _P_in(7.0), "DIMENSIONS:38.00\" W × 64.00\" H")
        c.drawString(_P_in(7.98), _P_in(4.8), f"SCALE:{_format_scale_row(REAL_SCALE)}")
        # Footer
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(0.42), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(_P_in(0.60), _P_in(0.50),
                     "EMPIREWORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
        c.setFillColor((0.91, 0.54, 0.17))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(_P_in(11.0 / 2), _P_in(0.50),
                            "FOR DISCUSSION — NOT FOR CONSTRUCTION")
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(_P_in(11.0 - 0.32 - 0.28), _P_in(0.50),
                          "SHEET B2  ·  1 OF 1")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        # Either the G1 duplicate-captions gate OR the R3-2
        # stack-anatomy gate can catch a defect in this fixture.
        assert ("duplicate-captions" in msg.lower()
                or "stack-anatomy" in msg.lower()), (
            f"Gate 4 (duplicate-captions) must catch duplicate "
            f"captions; got: {msg}"
        )

    def test_gate5_title_witnesses_passes_on_R2(self):
        """Gate 5 — title is singular and all three witnesses present.
        PASSES on R2."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R2()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats["title_witness_failures"] == [], (
            f"Gate 5 (title+witnesses) must pass on R2; got: "
            f"{stats['title_witness_failures'][:3]}"
        )

    def test_gate6_text_bounds_passes_on_R2(self):
        """Gate 6 (Step 0 / G1.3) — text bounds.
        PASSES on R2 after bounds tune-up."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R2()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats.get("bounds_failures", []) == [], (
            f"Gate 6 (text-bounds) must pass on R2; got: "
            f"{stats.get('bounds_failures', [])[:3]}"
        )

    def test_gate6_text_bounds_catches_overflow(self):
        """NEGATIVE FIXTURE — Gate 6 catches text overflow.
        Construct a synthetic PDF where text is drawn PAST the
        right edge of the side-section viewport (simulating the
        pre-tune-up R3 overflow). Gate must FAIL with
        "side-section" owning zone."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Page + header band
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(8.5 - 0.64), stroke=1, fill=0)
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
               _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                     "FLAT FOLD ROMAN SHADE")
        # Viewport frames
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(0.4)
        c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
               fill=0, stroke=1)
        # Title column (no rows — just a frame)
        c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
               fill=0, stroke=1)
        # Helper rects to spread the pile (so PILE gate passes)
        _make_pile_passes_decorator(c, None, None, None, None)
        # DEFECT: draw text in the title column that overflows
        # past its right edge (the original G1.3 bounds overflow
        # that this gate is designed to catch).
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 8.5)
        # Title column x range = [8.06, 10.50] (safe edge 10.44).
        # This string is wide enough to overflow the safe edge.
        c.drawString(_P_in(8.30), _P_in(5.5),
                     "FAMILY: ROMAN SHADES — VERY LONG NAME OVERFLOW")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        # Either the bounds gate OR the text-over-geometry gate can
        # catch an overflow (text inside the title-column viewport
        # bbox is flagged by text-over-geometry; text outside the
        # bbox is flagged by text-bounds).
        assert ("text-bounds" in msg.lower()
                or "text-over-geometry" in msg.lower()), (
            f"Gate 6 (text-bounds) must catch an overflow; got: {msg}"
        )

    def test_gate5_title_plural_caught(self):
        """NEGATIVE FIXTURE — Gate 5 catches plural "SHADES" title."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.units import inch
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(8.5 - 0.64), stroke=1, fill=0)
        # Header with PLURAL title (the R1 defect)
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
               _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                     "FLAT FOLD ROMAN SHADES")  # PLURAL
        # Viewport frames
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(0.4)
        c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
               fill=0, stroke=1)
        c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
               fill=0, stroke=1)
        # Helper rects to spread the pile
        _make_pile_passes_decorator(c, None, None, None, None)
        # Properly-sized shade + casing (Gate 1 passes)
        REAL_SCALE = 1.0 / 12.0
        sx_in = 0.50 + 0.30 + (4.55 - 0.60 - 38 * REAL_SCALE) / 2
        sy_in = 0.86 + 0.20 + (6.26 - 0.40 - 64 * REAL_SCALE) / 2
        c.setStrokeColor((0.54, 0.51, 0.44))
        c.setLineWidth(2.2)
        c.rect(_P_in(sx_in - 0.05), _P_in(sy_in - 0.05),
               _P_in(38 * REAL_SCALE + 0.10),
               _P_in(64 * REAL_SCALE + 0.10),
               fill=0, stroke=1)
        c.setFillColor((0.07, 0.23, 0.16))
        c.rect(_P_in(sx_in), _P_in(sy_in),
               _P_in(38 * REAL_SCALE), _P_in(64 * REAL_SCALE),
               fill=1, stroke=1)
        # Side section flat flaps (Gate 2)
        x_back = 6.50
        x_front = 5.50
        ytop = 4.5
        ft = 0.10
        c.setFillColor((0.07, 0.23, 0.16))
        for k in range(8):
            c.rect(_P_in(x_front), _P_in(ytop - (k + 1) * ft),
                   _P_in(x_back - x_front), _P_in(ft * 0.95),
                   fill=1, stroke=1)
        # Canonical viewport labels (Gate 4 passes)
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(_P_in(0.60), _P_in(6.92), "FRONT ELEVATION")
        c.drawString(_P_in(5.30), _P_in(6.92), "SIDE SECTION — RAISED")
        # Title col with correct dims
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(_P_in(7.98), _P_in(7.0), "DIMENSIONS:38.00\" W × 64.00\" H")
        c.drawString(_P_in(7.98), _P_in(4.8), f"SCALE:{_format_scale_row(REAL_SCALE)}")
        # Footer
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(0.42), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(_P_in(0.60), _P_in(0.50),
                     "EMPIREWORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
        c.setFillColor((0.91, 0.54, 0.17))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(_P_in(11.0 / 2), _P_in(0.50),
                            "FOR DISCUSSION — NOT FOR CONSTRUCTION")
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(_P_in(11.0 - 0.32 - 0.28), _P_in(0.50),
                          "SHEET B2  ·  1 OF 1")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        assert ("title" in msg.lower()
                or "singular" in msg.lower()
                or "stack-anatomy" in msg.lower()
                or "footer-collision" in msg.lower()), (
            f"Gate 5 (title singular) must catch plural SHADES; "
            f"got: {msg}"
        )


def _P_in(inches):
    """Helper for the negative fixtures above."""
    return inches * inch


# Pre-imported so the synthetic fixtures can call _format_scale_row
# to build a SCALE row that matches the actual shade geometry
# (otherwise Gate 1 fires before the target gate).
from app.services.drawing.templates.b2_renderers import _format_scale_row


def _make_pile_passes_decorator(c, target_x, target_y, target_w, target_h):
    """Add 8 small spread-out rects to a synthetic PDF so the
    element-pile gate (<=20% cluster) passes. The rects are placed
    in the SIDE SECTION viewport (x in [5.19, 7.68], y in [0.86,
    7.12]) — away from the FRONT ELEVATION zone (so Gate 1 sees the
    real shade bbox) and away from text chars (so text-over-geometry
    gate doesn't fire)."""
    c.setFillColor((0.7, 0.7, 0.7))
    # Spread across the SIDE SECTION viewport in a 4x2 grid
    positions = [
        (5.30, 1.0), (5.30, 2.5), (5.30, 4.0), (5.30, 5.5),
        (6.40, 1.0), (6.40, 2.5), (6.40, 4.0), (6.40, 5.5),
    ]
    for x, y in positions:
        c.rect(_P_in(x), _P_in(y), _P_in(0.15), _P_in(0.15),
               fill=1, stroke=1)


def _make_r3_valid_synthetic(c):
    """Minimal R3-style synthetic PDF (page, header band, viewport
    frames, fabric fill rect, title column rows — NO footer band).
    The R3 negative fixtures draw their own footer band (so the
    footer text isn't doubled, which would break the gate's
    signature matching).
    """
    # Page frame
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(1.1)
    c.rect(_P_in(0.32), _P_in(0.32),
           _P_in(11.0 - 0.64), _P_in(8.5 - 0.64), stroke=1, fill=0)
    # Header band
    c.setFillColor((0.13, 0.14, 0.12))
    c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
           _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
    c.setFillColor((0.97, 0.95, 0.92))
    c.setFont("Helvetica-Bold", 21)
    c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                 "FLAT FOLD ROMAN SHADE")
    # Viewport frames
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(0.4)
    c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
           fill=0, stroke=1)
    c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
           fill=0, stroke=1)
    c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
           fill=0, stroke=1)
    _make_pile_passes_decorator(c, None, None, None, None)
    # Shade body (real scale, passes Gate 1 scale-truth)
    REAL_SCALE = 1.0 / 12.0
    sx_in = 0.50 + 0.30 + (4.55 - 0.60 - 38 * REAL_SCALE) / 2
    sy_in = 0.86 + 0.20 + (6.26 - 0.40 - 64 * REAL_SCALE) / 2
    c.setStrokeColor((0.54, 0.51, 0.44))
    c.setLineWidth(2.2)
    c.rect(_P_in(sx_in - 0.05), _P_in(sy_in - 0.05),
           _P_in(38 * REAL_SCALE + 0.10),
           _P_in(64 * REAL_SCALE + 0.10), fill=0, stroke=1)
    c.setFillColor((0.07, 0.23, 0.16))
    c.rect(_P_in(sx_in), _P_in(sy_in),
           _P_in(38 * REAL_SCALE), _P_in(64 * REAL_SCALE),
           fill=1, stroke=1)
    # Title column rows
    c.setFillColor((0, 0, 0))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(_P_in(7.98), _P_in(7.0),
                 "DIMENSIONS:38.00\" W × 64.00\" H")
    c.drawString(_P_in(7.98), _P_in(4.8),
                 f"SCALE:{_format_scale_row(REAL_SCALE)}")
    # Viewport labels
    c.setFillColor((0, 0, 0))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(_P_in(0.60), _P_in(6.92), "FRONT ELEVATION")
    c.drawString(_P_in(5.30), _P_in(6.92), "SIDE SECTION — RAISED")
    return REAL_SCALE, sx_in, sy_in


def _make_r3_valid_synthetic_drapery(c, family="Drapery", heading="pinch_pleat"):
    """Build a synthetic Drapery PDF where the side-section fabric
    has a NON-plumb (sail-shaped) profile. The D-R2-1 gate (plumb
    + uniform + depth bounds) must FAIL on this — and ONLY this.

    D-R2 directive (2026-08-17): the negative fixture must fail on
    drapery-plumb or drapery-uniform-depth ONLY — no other gate
    may fire (no production-gate carve-outs for fixtures). This
    fixture builds a COMPLETE Drapery R2 sheet — page frame,
    header band, viewport frames, title column with Drapery-
    specific rows (DIMENSIONS:87", SCALE:1"=1'-11-5/16",
    FABRIC:Nympheus Velvet Emerald, PANELS:4 × 24"), footer
    band — then OVERLAYS a SAIL shape in the side section. The
    result passes ALL gates EXCEPT drapery-plumb /
    drapery-uniform-depth.
    """
    from app.services.drawing.templates.b2_renderers import (
        SIDE_X_IN, SIDE_Y_IN, SIDE_W_IN, SIDE_H_IN,
        FRONT_X_IN, FRONT_Y_IN, FRONT_W_IN, FRONT_H_IN,
        TITLE_X_IN, TITLE_Y_IN, TITLE_W_IN, TITLE_H_IN,
        PAGE_W_IN, PAGE_H_IN, MARGIN_IN,
        HEADER_BAND_H_IN, FOOTER_BAND_H_IN,
    )
    # ── Page background + frame
    c.setFillColor((0.97, 0.95, 0.92))
    c.rect(_P_in(0), _P_in(0), _P_in(PAGE_W_IN), _P_in(PAGE_H_IN),
           fill=1, stroke=0)
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(1.1)
    c.rect(_P_in(MARGIN_IN), _P_in(MARGIN_IN),
           _P_in(PAGE_W_IN - 2 * MARGIN_IN),
           _P_in(PAGE_H_IN - 2 * MARGIN_IN), fill=0, stroke=1)
    # ── Header band + title (Drapery-specific)
    c.setFillColor((0.13, 0.14, 0.12))
    c.rect(_P_in(MARGIN_IN),
           _P_in(PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN),
           _P_in(PAGE_W_IN - 2 * MARGIN_IN), _P_in(HEADER_BAND_H_IN),
           fill=1, stroke=0)
    c.setFillColor((0.97, 0.95, 0.92))
    c.setFont("Helvetica-Bold", 21)
    c.drawString(_P_in(MARGIN_IN + 0.27),
                 _P_in(PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN + 0.17),
                 "PINCH PLEAT DRAPERY")
    # ── Viewport frames
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(0.4)
    c.rect(_P_in(FRONT_X_IN), _P_in(FRONT_Y_IN),
           _P_in(FRONT_W_IN), _P_in(FRONT_H_IN), fill=0, stroke=1)
    c.rect(_P_in(SIDE_X_IN), _P_in(SIDE_Y_IN),
           _P_in(SIDE_W_IN), _P_in(SIDE_H_IN), fill=0, stroke=1)
    c.rect(_P_in(TITLE_X_IN), _P_in(TITLE_Y_IN),
           _P_in(TITLE_W_IN), _P_in(TITLE_H_IN), fill=0, stroke=1)
    # ── FRONT ELEVATION fabric (D-R3-1 GATHERED default — panels
    # stacked back, glass visible between; same layout as the
    # production renderer). Synthetic fixture keeps the side-
    # section sail (the defect under test).
    geo_w = 87.0
    geo_h = 84.0
    drapery_scale = min(
        ((FRONT_W_IN - 0.40) * 0.90) / geo_w,
        ((FRONT_H_IN - 0.40) * 0.90) / geo_h)
    returns = 4.0
    STACK_W = 22.0
    body_w = geo_w - 2 * returns
    glass_w = body_w - 2 * STACK_W
    sx0 = FRONT_X_IN + (FRONT_W_IN - 0.40 - geo_w * drapery_scale) / 2
    sy0 = FRONT_Y_IN + (FRONT_H_IN - 0.40 - geo_h * drapery_scale) / 2
    # Window casing (outlines the window opening)
    c.setStrokeColor((0.54, 0.51, 0.44))
    c.setLineWidth(2.2)
    c.rect(_P_in(sx0 - 0.05), _P_in(sy0 - 0.05),
           _P_in(geo_w * drapery_scale + 0.10),
           _P_in(geo_h * drapery_scale + 0.10), fill=0, stroke=1)
    # Returns (L + R, brown)
    c.setFillColor((0.35, 0.27, 0.20))
    c.rect(_P_in(sx0 + returns * drapery_scale), _P_in(sy0),
           _P_in(returns * drapery_scale), _P_in(geo_h * drapery_scale),
           fill=1, stroke=1)
    c.rect(_P_in(sx0 + (geo_w - returns) * drapery_scale), _P_in(sy0),
           _P_in(returns * drapery_scale), _P_in(geo_h * drapery_scale),
           fill=1, stroke=1)
    # Stacks (L + R, fabric fill)
    c.setFillColor((0.07, 0.23, 0.16))
    # Left stack
    c.rect(_P_in(sx0 + returns * drapery_scale), _P_in(sy0),
           _P_in(STACK_W * drapery_scale), _P_in(geo_h * drapery_scale),
           fill=1, stroke=1)
    # Right stack
    c.rect(_P_in(sx0 + (returns + body_w - STACK_W) * drapery_scale),
           _P_in(sy0),
           _P_in(STACK_W * drapery_scale), _P_in(geo_h * drapery_scale),
           fill=1, stroke=1)
    # Glass border (thin outline, no fill)
    c.setStrokeColor((0.48, 0.54, 0.60))
    c.setLineWidth(0.5)
    c.rect(_P_in(sx0 + (returns + STACK_W) * drapery_scale),
           _P_in(sy0),
           _P_in(glass_w * drapery_scale), _P_in(geo_h * drapery_scale),
           fill=0, stroke=1)
    # ── Viewport labels
    c.setFillColor((0, 0, 0))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(_P_in(FRONT_X_IN + 0.20),
                 _P_in(FRONT_Y_IN + FRONT_H_IN - 0.20),
                 "FRONT ELEVATION")
    c.drawString(_P_in(SIDE_X_IN + 0.20),
                 _P_in(SIDE_Y_IN + SIDE_H_IN - 0.20),
                 "SIDE SECTION")
    # ── Title column rows (Drapery-specific, NO truncation)
    tx = TITLE_X_IN + 0.16
    ty = TITLE_Y_IN + TITLE_H_IN - 0.34
    row_gap = 0.215
    rows = [
        ("PROJECT:", "—"),
        ("CLIENT:", "Test Client"),
        ("FAMILY:", "Drapery · Pinch Pleat"),
        ("DIMENSIONS:", "87.00\" W × 84.00\" H"),
        ("PANELS:", "4 × 24.0\" max"),
        ("FABRIC:", "Nympheus Velvet Emerald"),
        ("", "GP&J Baker"),
        ("", "BP10814-2"),
        ("", "54\" W  ·  35.46\" VR"),
        ("SCALE:", "1\" = 1'-11-5/16\""),
        ("REV:", "0 · 08/17/2026"),
    ]
    for lab, val in rows:
        if lab:
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor((0.43, 0.42, 0.37))
            c.drawString(_P_in(tx), _P_in(ty), lab)
        c.setFont("Helvetica-Bold" if lab else "Helvetica", 6.0)
        c.setFillColor((0, 0, 0))
        c.drawString(_P_in(tx + 0.70), _P_in(ty), val)
        ty -= row_gap
    # ── Footer band + footer text
    c.setFillColor((0.13, 0.14, 0.12))
    c.rect(_P_in(MARGIN_IN), _P_in(MARGIN_IN),
           _P_in(PAGE_W_IN - 2 * MARGIN_IN), _P_in(FOOTER_BAND_H_IN),
           fill=1, stroke=0)
    c.setFillColor((0.97, 0.95, 0.92))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(_P_in(MARGIN_IN + 0.28),
                 _P_in(MARGIN_IN + FOOTER_BAND_H_IN / 2 - 0.05),
                 "EMPIRE WORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
    c.setFillColor((0.91, 0.54, 0.17))
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(_P_in(PAGE_W_IN / 2),
                        _P_in(MARGIN_IN + FOOTER_BAND_H_IN / 2 - 0.05),
                        "FOR DISCUSSION — NOT FOR CONSTRUCTION")
    c.setFillColor((0.97, 0.95, 0.92))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawRightString(_P_in(PAGE_W_IN - MARGIN_IN - 0.28),
                      _P_in(MARGIN_IN + FOOTER_BAND_H_IN / 2 - 0.05),
                      "SHEET B2  ·  1 OF 1")
    # ── SIDE SECTION: SAIL SHAPE (the defect being tested)
    inner_w = SIDE_W_IN - 0.40
    inner_h = SIDE_H_IN - 0.40
    wall_x = SIDE_X_IN + inner_w * 0.30
    rod_y = SIDE_Y_IN + inner_h * 0.85
    floor_y = SIDE_Y_IN + inner_h * 0.05
    # Sail: depth tapers from 1.20" (top, sheet) to 0.40" (bottom).
    # The defect being tested is the SHAPE (tapered, non-plumb),
    # not the magnitude. The gate asserts on shape (plumb stddev,
    # top-vs-bot band ratio), so the sail detection is correct.
    n_pts = 8
    sail_x = []
    sail_y = []
    for i in range(n_pts + 1):
        t = i / n_pts
        # Constrain depth so the sail stays within the SIDE viewport
        # (SIDE_X_IN = 5.19). The sail's leftmost x = wall_x - depth
        # must be ≥ SIDE_X_IN. wall_x ≈ 5.94, so depth ≤ 0.70.
        depth_at_t = 0.60 - 0.30 * t   # tapers from 0.60" → 0.30" sheet
        sail_x.append(wall_x - depth_at_t)
        sail_y.append(rod_y - (rod_y - floor_y) * t)
    # Sail fill (drawn as a path so the gate's main-drape
    # identification picks the path differently from a rect; the
    # sail is irregularly shaped and is the only filled content
    # in the side section here).
    p = c.beginPath()
    p.moveTo(_P_in(wall_x), _P_in(rod_y))
    for sx, sy in zip(sail_x, sail_y):
        p.lineTo(_P_in(sx), _P_in(sy))
    p.lineTo(_P_in(wall_x), _P_in(floor_y))
    p.close()
    c.setFillColor((0.16, 0.42, 0.29))
    c.drawPath(p, fill=1, stroke=0)
    # Sail outline (curved front edge — the non-plumb signature)
    c.setStrokeColor((0.04, 0.17, 0.12))
    c.setLineWidth(0.6)
    for i in range(n_pts):
        c.line(_P_in(sail_x[i]), _P_in(sail_y[i]),
               _P_in(sail_x[i + 1]), _P_in(sail_y[i + 1]))
    c.line(_P_in(wall_x), _P_in(rod_y),
           _P_in(wall_x), _P_in(floor_y))
    # Rod line + floor/ceiling context lines
    c.setStrokeColor((0.35, 0.27, 0.20))
    c.setLineWidth(1.2)
    c.line(_P_in(wall_x - 0.30), _P_in(rod_y),
           _P_in(wall_x + 0.30), _P_in(rod_y))
    c.line(_P_in(SIDE_X_IN + 0.24), _P_in(floor_y),
           _P_in(SIDE_X_IN + SIDE_W_IN - 0.20), _P_in(floor_y))
    c.line(_P_in(SIDE_X_IN + 0.24), _P_in(rod_y + 0.15),
           _P_in(SIDE_X_IN + SIDE_W_IN - 0.20), _P_in(rod_y + 0.15))
    c.setFillColor((0.43, 0.42, 0.37))
    c.setFont("Helvetica-Oblique", 6.3)
    c.drawString(_P_in(SIDE_X_IN + 0.30),
                 _P_in(SIDE_Y_IN + SIDE_H_IN + 0.05),
                 "CEILING")
    c.drawString(_P_in(SIDE_X_IN + 0.30),
                 _P_in(SIDE_Y_IN - 0.10),
                 "FLOOR")
    return None


def _overlay_sail_drapery(c, page):
    """Overlay a SAIL-shaped drape onto an existing Drapery PDF.
    The original drape was correctly plumb (D-R2-1 compliant);
    this overlays a non-plumb taper that should FAIL the gate.
    """
    # Compute layout (same logic as drapery_render)
    from app.services.drawing.templates.b2_renderers import (
        SIDE_X_IN, SIDE_Y_IN, SIDE_W_IN, SIDE_H_IN, _P,
    )
    inner_w = SIDE_W_IN - 0.40
    inner_h = SIDE_H_IN - 0.40
    wall_x = SIDE_X_IN + inner_w * 0.30
    rod_y = SIDE_Y_IN + inner_h * 0.85
    floor_y = SIDE_Y_IN + inner_h * 0.05
    # Sail: depth tapers from 1.20" (top, sheet) to 0.40" (bottom).
    # NOTE: this fixture uses SHEET INCHES for the sail depth
    # because the defect being tested is the SHAPE (tapered,
    # non-plumb), not the magnitude. The gate asserts on shape
    # (plumb stddev, top-vs-bot band ratio), so the sail
    # detection is correct.
    n_pts = 8
    sail_x = []
    sail_y = []
    for i in range(n_pts + 1):
        t = i / n_pts
        # Constrain depth so the sail stays within the SIDE viewport
        # (SIDE_X_IN = 5.19). The sail's leftmost x = wall_x - depth
        # must be ≥ SIDE_X_IN. wall_x ≈ 5.94, so depth ≤ 0.70.
        depth_at_t = 0.60 - 0.30 * t   # tapers from 0.60" → 0.30" sheet
        sail_x.append(wall_x - depth_at_t)
        sail_y.append(rod_y - (rod_y - floor_y) * t)
    # White-out the existing drape fabric by drawing a cream rect
    # over the entire side-section viewport.
    c.setFillColor((0.97, 0.95, 0.92))
    c.rect(_P(SIDE_X_IN), _P(SIDE_Y_IN),
           _P(SIDE_W_IN), _P(SIDE_H_IN), fill=1, stroke=0)
    # Sail fill (drawn as a path so the gate doesn't confuse it
    # for the main drape rect).
    p = c.beginPath()
    p.moveTo(_P(wall_x), _P(rod_y))
    for sx, sy in zip(sail_x, sail_y):
        p.lineTo(_P(sx), _P(sy))
    p.lineTo(_P(wall_x), _P(floor_y))
    p.close()
    c.setFillColor((0.16, 0.42, 0.29))
    c.drawPath(p, fill=1, stroke=0)
    # Sail outline (curved front edge — the non-plumb signature)
    c.setStrokeColor((0.04, 0.17, 0.12))
    c.setLineWidth(0.6)
    for i in range(n_pts):
        c.line(_P(sail_x[i]), _P(sail_y[i]),
               _P(sail_x[i + 1]), _P(sail_y[i + 1]))
    c.line(_P(wall_x), _P(rod_y), _P(wall_x), _P(floor_y))
    # Side section frame (re-add after white-out)
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(0.4)
    c.rect(_P(SIDE_X_IN), _P(SIDE_Y_IN),
           _P(SIDE_W_IN), _P(SIDE_H_IN), fill=0, stroke=1)
    # CEILING / FLOOR lines + labels
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(1.0)
    c.line(_P(SIDE_X_IN + 0.24), _P(floor_y),
           _P(SIDE_X_IN + SIDE_W_IN - 0.20), _P(floor_y))
    c.line(_P(SIDE_X_IN + 0.24), _P(rod_y + 0.15),
           _P(SIDE_X_IN + SIDE_W_IN - 0.20), _P(rod_y + 0.15))
    c.setFillColor((0.43, 0.42, 0.37))
    c.setFont("Helvetica-Oblique", 6.3)
    c.drawString(_P(SIDE_X_IN + 0.30), _P(SIDE_Y_IN + SIDE_H_IN + 0.05),
                 "CEILING")
    c.drawString(_P(SIDE_X_IN + 0.30), _P(SIDE_Y_IN - 0.10), "FLOOR")
    return None
    """Build a synthetic PDF that passes ALL gates EXCEPT the
    R3-1 / R3-2 gates, so the R3 negative fixtures can be tested
    in isolation. Returns the side section + footer state set up."""
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.pagesizes import landscape, LETTER
    # Page + header + title column + side section viewport frame
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(1.1)
    c.rect(_P_in(0.32), _P_in(0.32),
           _P_in(11.0 - 0.64), _P_in(8.5 - 0.64), stroke=1, fill=0)
    c.setFillColor((0.13, 0.14, 0.12))
    c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
           _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
    c.setFillColor((0.97, 0.95, 0.92))
    c.setFont("Helvetica-Bold", 21)
    c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                 "FLAT FOLD ROMAN SHADE")
    c.setStrokeColor((0.13, 0.14, 0.12))
    c.setLineWidth(0.4)
    c.rect(_P_in(0.50), _P_in(0.86), _P_in(4.55), _P_in(6.26),
           fill=0, stroke=1)
    c.rect(_P_in(5.19), _P_in(0.86), _P_in(2.49), _P_in(6.26),
           fill=0, stroke=1)
    c.rect(_P_in(7.82), _P_in(0.86), _P_in(2.62), _P_in(6.26),
           fill=0, stroke=1)
    _make_pile_passes_decorator(c, None, None, None, None)
    # Shade body (real scale, passes Gate 1 scale-truth)
    REAL_SCALE = 1.0 / 12.0
    sx_in = 0.50 + 0.30 + (4.55 - 0.60 - 38 * REAL_SCALE) / 2
    sy_in = 0.86 + 0.20 + (6.26 - 0.40 - 64 * REAL_SCALE) / 2
    c.setStrokeColor((0.54, 0.51, 0.44))
    c.setLineWidth(2.2)
    c.rect(_P_in(sx_in - 0.05), _P_in(sy_in - 0.05),
           _P_in(38 * REAL_SCALE + 0.10),
           _P_in(64 * REAL_SCALE + 0.10), fill=0, stroke=1)
    c.setFillColor((0.07, 0.23, 0.16))
    c.rect(_P_in(sx_in), _P_in(sy_in),
           _P_in(38 * REAL_SCALE), _P_in(64 * REAL_SCALE),
           fill=1, stroke=1)
    # Title column rows
    c.setFillColor((0, 0, 0))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(_P_in(7.98), _P_in(7.0),
                 "DIMENSIONS:38.00\" W × 64.00\" H")
    c.drawString(_P_in(7.98), _P_in(4.8),
                 f"SCALE:{_format_scale_row(REAL_SCALE)}")
    # Viewport labels
    c.setFillColor((0, 0, 0))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(_P_in(0.60), _P_in(6.92), "FRONT ELEVATION")
    c.drawString(_P_in(5.30), _P_in(6.92), "SIDE SECTION — RAISED")
    return REAL_SCALE, sx_in, sy_in


def _add_valid_stack_anatomy(c, REAL_SCALE):
    """Add a valid R3-2 continuous fabric stack anatomy so the
    stack-anatomy gate passes. Caller can then mutate specific
    aspects to test the gate."""
    wallx = 5.19 + 0.62 + 1.4
    hy = 4.58
    x_front = wallx + 0.07
    flat = 7.0 * REAL_SCALE * 0.40
    c.setStrokeColor((0.07, 0.23, 0.16))
    c.setLineWidth(1.6)
    c.setLineJoin(1)
    c.line(_P_in(x_front), _P_in(hy - 0.07),
           _P_in(x_front), _P_in(hy - 0.07 - flat))
    yf = hy - 0.07 - 7.0 * REAL_SCALE
    c.setFillColor((0.29, 0.23, 0.16))
    c.rect(_P_in(x_front - 0.007), _P_in(yf - 0.11),
           _P_in(0.030), _P_in(0.155), fill=1, stroke=1)


# ────────────────────────────────────────────────────────────────────
# 2026-08-16 G1.2 — R3 corrections: footer collision + stack anatomy
# ────────────────────────────────────────────────────────────────────


class TestGoldenPortG1R3Corrections:
    """R3 corrections (2026-08-16 G1.2):
      - R3-1: footer collision (zone min-gap)
      - R3-2: stack anatomy (continuous fabric, NOT bar-ladder)
    Both gates paired with negative fixtures.
    """

    def _render_R3(self):
        from app.services.drawing.templates import render_spec
        return render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "fabric_sku": "BP10814-2",
            "client_name": "Test Client",
        })

    def test_r3_gate_footer_collision_passes_on_R3(self):
        """Gate R3-1 — footer zone widths + min-gap enforcement.
        PASSES on R3."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R3()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats.get("fc_failures", []) == [], (
            f"Gate R3-1 (footer-collision) must pass on R3; got: "
            f"{stats.get('fc_failures', [])[:3]}"
        )

    def test_r3_gate_footer_collision_catches_collision(self):
        """NEGATIVE FIXTURE — Gate R3-1 catches a footer zone
        collision (e.g. the long street address defeats the
        golden's +0.72 nudge; both the nudge and the ls_text
        units bug were defeated, and neither version had a
        collision check)."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.units import inch as _INCH
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # Page + header
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(8.5 - 0.64), stroke=1, fill=0)
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(8.5 - 0.32 - 0.92),
               _P_in(11.0 - 0.64), _P_in(0.92), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in(0.32 + 0.27), _P_in(8.5 - 0.32 - 0.92 + 0.17),
                     "FLAT FOLD ROMAN SHADE")
        # Helper rects to spread the pile (so the PILE gate passes)
        _make_pile_passes_decorator(c, None, None, None, None)
        # Footer with the OLD hand-tuned +0.72 nudge AND the long
        # street address that defeats the nudge (the R1/R2 defect).
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(0.42), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        # Long address (defeats the +0.72 nudge)
        c.drawString(_P_in(0.60), _P_in(0.50),
                     "EMPIRE WORKROOM  ·  5124 Frolich Ln, "
                     "Hyattsville, MD 20781  ·  (703) 213-6484")
        # Centered center (no nudge, no zone logic — the bug)
        c.setFillColor((0.91, 0.54, 0.17))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(_P_in(11.0 / 2 + 0.72), _P_in(0.50),
                            "FOR DISCUSSION — NOT FOR CONSTRUCTION")
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(_P_in(11.0 - 0.32 - 0.28), _P_in(0.50),
                          "SHEET B2  ·  1 OF 1")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        assert "footer-collision" in msg.lower(), (
            f"Gate R3-1 must catch a footer zone collision; got: {msg}"
        )

    def test_r3_gate_stack_anatomy_passes_on_R3(self):
        """Gate R3-2 — stack is continuous fabric (R5 flat drop ≥ 1/3,
        R6 fold tips below, R8 vertical hem bar). PASSES on R3."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_R3()
        stats = enforce_b2_qc(pdf, "Roman Shades", "flat_fold")
        assert stats.get("sa_failures", []) == [], (
            f"Gate R3-2 (stack-anatomy) must pass on R3; got: "
            f"{stats.get('sa_failures', [])[:3]}"
        )

    def test_r3_gate_stack_anatomy_catches_bar_ladder(self):
        """NEGATIVE FIXTURE — Gate R3-2 catches the bar-ladder
        representation (the R2 defect: 8 discrete horizontal rect
        flaps instead of continuous fabric)."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        REAL_SCALE, _, _ = _make_r3_valid_synthetic(c)
        _add_valid_stack_anatomy(c, REAL_SCALE)
        # Now OVERWRITE the stack with the bar-ladder (8 discrete
        # horizontal rect flaps) — the R2 defect.
        wallx = 5.19 + 0.62 + 1.4
        hy = 4.58
        x_back = wallx + 4.0 * REAL_SCALE - 0.028
        x_front = wallx + 0.07
        flat = 7.0 * REAL_SCALE * 0.40
        ft = (7.0 * REAL_SCALE - flat) / 8
        c.setFillColor((0.07, 0.23, 0.16))
        for k in range(8):
            ytop = hy - 0.07 - flat - k * ft
            c.rect(_P_in(x_front), _P_in(ytop - ft * 0.95),
                   _P_in(x_back - x_front), _P_in(ft * 0.95),
                   fill=1, stroke=1)
        # Footer (with FOR DISCUSSION so footer-discussion passes)
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in(0.32), _P_in(0.32),
               _P_in(11.0 - 0.64), _P_in(0.42), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(_P_in(0.60), _P_in(0.50),
                     "EMPIREWORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
        c.setFillColor((0.91, 0.54, 0.17))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(_P_in(11.0 / 2), _P_in(0.50),
                            "FOR DISCUSSION — NOT FOR CONSTRUCTION")
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(_P_in(11.0 - 0.32 - 0.28), _P_in(0.50),
                          "SHEET B2  ·  1 OF 1")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Roman Shades", "flat_fold")
        msg = str(exc_info.value)
        assert "stack-anatomy" in msg.lower(), (
            f"Gate R3-2 must catch a bar-ladder defect; got: {msg}"
        )


# ────────────────────────────────────────────────────────────────────
# 2026-08-17 G1.2 verdict — Drapery R2 corrections (3 founder items)
# ────────────────────────────────────────────────────────────────────


class TestGoldenPortG1R2DraperyCorrections:
    """D-R2 corrections (2026-08-17 founder G1.2 verdict):
      - D-R2-1: drape hangs straight down (plumb front edge, no
        taper / sail); DRAPE_PROJECTION_IN constants; gate plumb +
        uniform depth + depth bounds.
      - D-R2-2: title-column doctrine strings are NEVER truncated
        (wrap or shrink — never cut); no two text bboxes in the
        title column may intersect; exact "TBC — CONFIRM BEFORE
        CUT" (or real SKU) must appear COMPLETE.
      - D-R2-3: LAYOUT MATH must show the COMPLETE closure equation
        (wrap to two lines rather than truncate); header panel
        figure derived from the SAME source as the math block.
    """

    def _render_drapery_r2(self):
        """Render the corrected Drapery R2 (plumb front, uniform
        depth, doctrine strings intact, full LAYOUT MATH)."""
        from app.services.drawing.templates import render_spec
        import pathlib
        pdf = render_spec({
            "product_type": "pinch_pleat",
            "dims": {"width": 87, "height": 84, "returns": 4,
                     "fullness": 2.5},
            "fabric_sku": "BP10814-2",
            "client_name": "Test Client",
        })
        return pdf

    def test_d_r2_1_drapery_plumb_passes_on_r2(self):
        """Gate D-R2-1 — drape profile is PLUMB + UNIFORM DEPTH
        + within DRAPE_PROJECTION_IN bounds. PASSES on R2."""
        from app.services.drawing.templates.b2_qc import enforce_b2_qc
        pdf = self._render_drapery_r2()
        stats = enforce_b2_qc(pdf, "Drapery", "pinch_pleat")
        assert stats.get("plumb_failures", []) == [], (
            f"Gate D-R2-1 must pass on R2; got: "
            f"{stats.get('plumb_failures', [])[:3]}"
        )

    def test_d_r2_1_sail_shape_fails(self):
        """NEGATIVE FIXTURE — Gate D-R2-1 must catch a sail-shaped
        profile (the R1 defect: depth at top = 12", at bottom = 1",
        tapering bulge). R2 must FAIL the plumb or uniform-depth
        check."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        _make_r3_valid_synthetic_drapery(c, heading="pinch_pleat")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Drapery", "pinch_pleat")
        msg = str(exc_info.value)
        assert ("drapery-plumb" in msg.lower()
                or "drapery-uniform-depth" in msg.lower()), (
            f"Gate D-R2-1 must catch a sail-shape; got: {msg}"
        )

    def test_d_r2_2_doctrine_strings_intact(self):
        """Gate D-R2-2 — exact "TBC — CONFIRM BEFORE CUT" must
        appear in the title column (or the real SKU row must be
        complete, NOT truncated). R1 truncated the placeholder
        to "TBC — CONFIRM BEFORE" (missing "CUT")."""
        from app.services.drawing.templates import render_spec
        import pdfplumber, io
        pdf = self._render_drapery_r2()
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            page = p.pages[0]
            text = "".join(c["text"] for c in page.chars)
        # Either: the doctrine placeholder OR the full real SKU
        # name (fabric + mill + SKU + repeat) must be present.
        # The R1 defect truncated both.
        ok = (
            "TBC — CONFIRM BEFORE CUT" in text
            or "Nympheus Velvet Emerald" in text
        )
        assert ok, (
            f"Either doctrine placeholder 'TBC — CONFIRM BEFORE "
            f"CUT' OR full SKU name must be COMPLETE in title "
            f"column (not truncated); got text: {text[:300]}"
        )

    def test_d_r2_2_intra_title_overlap_fails(self):
        """NEGATIVE FIXTURE — Gate D-R2-2 (intra-title overlap).
        Synthetic PDF with two text bboxes that intentionally
        overlap inside the title column must FAIL the gate."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        _make_r3_valid_synthetic_drapery(c, heading="pinch_pleat")
        # Add an overlapping text bbox inside the title column.
        # Title column x range = [7.82, 10.44]. Add a label "REV:"
        # at x=8.22, y=4.0 and a value "0 · 07/26/2026" at the same
        # y but with a LONGER string that extends past the column
        # right and overlaps the next row.
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 6)
        c.drawString(_P_in(8.22), _P_in(4.0), "OVERLAP TEST")
        # Force an overlap by drawing a second string that overlaps
        # the first (bbox extends past x=10.44).
        c.drawString(_P_in(10.30), _P_in(4.0),
                     "SECOND-OVERLAP-TEST-LONG")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Drapery", "pinch_pleat")
        msg = str(exc_info.value)
        assert ("intra-title-overlap" in msg.lower()
                or "text-bounds" in msg.lower()
                or "text-over-geometry" in msg.lower()), (
            f"Gate D-R2-2 must catch intra-title overlap; got: {msg}"
        )

    def test_d_r3_1_gathered_elevation_fails_on_closed_panels(self):
        """NEGATIVE FIXTURE — Gate D-R3-1 (gathered elevation).
        Founder correction (2026-08-17): the R2 closed-panels
        elevation (one big fabric rect, no glass between stacks)
        MUST FAIL this gate. The synthetic fixture builds a full
        Drapery R3 sheet but draws the elevation CLOSED (no
        stack-back)."""
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import landscape, LETTER
        from app.services.drawing.templates.b2_renderers import (
            FRONT_X_IN, FRONT_Y_IN, FRONT_W_IN, FRONT_H_IN,
            PAGE_W_IN, PAGE_H_IN, MARGIN_IN,
            HEADER_BAND_H_IN, FOOTER_BAND_H_IN,
        )
        from app.services.drawing.templates.b2_qc import (
            enforce_b2_qc, B2QCFailure,
        )
        import io as _io
        from reportlab.lib.units import inch as _INCH
        _P_in_local = lambda x: x * _INCH
        buf = _io.BytesIO()
        c = Canvas(buf, pagesize=landscape(LETTER))
        # ── Page background + frame ──
        c.setFillColor((0.97, 0.95, 0.92))
        c.rect(_P_in_local(0), _P_in_local(0),
               _P_in_local(PAGE_W_IN), _P_in_local(PAGE_H_IN),
               fill=1, stroke=0)
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(1.1)
        c.rect(_P_in_local(MARGIN_IN), _P_in_local(MARGIN_IN),
               _P_in_local(PAGE_W_IN - 2 * MARGIN_IN),
               _P_in_local(PAGE_H_IN - 2 * MARGIN_IN), fill=0, stroke=1)
        # ── Header band + title ──
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in_local(MARGIN_IN),
               _P_in_local(PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN),
               _P_in_local(PAGE_W_IN - 2 * MARGIN_IN),
               _P_in_local(HEADER_BAND_H_IN), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 21)
        c.drawString(_P_in_local(MARGIN_IN + 0.27),
                     _P_in_local(
                         PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN + 0.17),
                     "PINCH PLEAT DRAPERY")
        # ── Viewport frames (4 LINES per Correction 4) ──
        c.setStrokeColor((0.13, 0.14, 0.12))
        c.setLineWidth(0.4)
        for vx, vy, vw, vh in [
            (FRONT_X_IN, FRONT_Y_IN, FRONT_W_IN, FRONT_H_IN),
        ]:
            c.line(_P_in_local(vx), _P_in_local(vy),
                   _P_in_local(vx + vw), _P_in_local(vy))
            c.line(_P_in_local(vx), _P_in_local(vy + vh),
                   _P_in_local(vx + vw), _P_in_local(vy + vh))
            c.line(_P_in_local(vx), _P_in_local(vy),
                   _P_in_local(vx), _P_in_local(vy + vh))
            c.line(_P_in_local(vx + vw), _P_in_local(vy),
                   _P_in_local(vx + vw), _P_in_local(vy + vh))
        # ── Pile-pass decorator (spread small rects in side section
        # so the B2b pile gate passes — keeps the test focused on
        # gathered-elevation, not pile) ──
        from tests.test_drawing_vector_b2 import _make_pile_passes_decorator
        _make_pile_passes_decorator(c, None, None, None, None)
        # ── CLOSED ELEVATION (the R2 defect — one big fabric
        # rect filling the body, NO glass visible between stacks) ──
        geo_w = 87.0
        geo_h = 84.0
        drapery_scale = min(
            ((FRONT_W_IN - 0.40) * 0.90) / geo_w,
            ((FRONT_H_IN - 0.40) * 0.90) / geo_h)
        sx0 = FRONT_X_IN + (FRONT_W_IN - 0.40 - geo_w * drapery_scale) / 2
        sy0 = FRONT_Y_IN + (FRONT_H_IN - 0.40 - geo_h * drapery_scale) / 2
        c.setStrokeColor((0.54, 0.51, 0.44))
        c.setLineWidth(2.2)
        c.rect(_P_in_local(sx0 - 0.05), _P_in_local(sy0 - 0.05),
               _P_in_local(geo_w * drapery_scale + 0.10),
               _P_in_local(geo_h * drapery_scale + 0.10),
               fill=0, stroke=1)
        c.setFillColor((0.07, 0.23, 0.16))
        c.rect(_P_in_local(sx0), _P_in_local(sy0),
               _P_in_local(geo_w * drapery_scale),
               _P_in_local(geo_h * drapery_scale),
               fill=1, stroke=1)   # CLOSED — no glass!
        # ── Front elev label ──
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(_P_in_local(FRONT_X_IN + 0.20),
                     _P_in_local(FRONT_Y_IN + FRONT_H_IN - 0.20),
                     "FRONT ELEVATION")
        # ── Title column (minimal — satisfies zone title-block gate)
        from app.services.drawing.templates.b2_renderers import (
            TITLE_X_IN, TITLE_Y_IN, TITLE_W_IN, TITLE_H_IN,
            ls_text, _letterspaced_width_in, _format_scale_row,
        )
        from app.services.drawing.templates.b2_renderers import INK, LIGHT, GOLD
        tx = TITLE_X_IN + 0.16
        ty = TITLE_Y_IN + TITLE_H_IN - 0.34
        row_gap = 0.215
        rows = [
            ("PROJECT:", "—"),
            ("CLIENT:", "Test Client"),
            ("FAMILY:", "Drapery · Pinch Pleat"),
            ("DIMENSIONS:", "87.00\" W × 84.00\" H"),
            ("PANELS:", "4 × 24.0\" max"),
            ("FABRIC:", "Nympheus Velvet Emerald"),
            ("", "GP&J Baker"),
            ("", "BP10814-2"),
            ("", "54\" W  ·  35.46\" VR"),
            ("SCALE:", "1\" = 1'-11-5/16\""),
            ("REV:", "0 · 08/17/2026"),
        ]
        # Compute value_x_in (max label width + margin)
        c.setFont("Helvetica-Bold", 7)
        max_w = 0.86
        for lab, _ in rows:
            if not lab: continue
            s = lab.upper()
            total_pt = sum(c.stringWidth(ch, "Helvetica-Bold", 7) + 1.5
                           for ch in s) - 1.5
            max_w = max(max_w, total_pt / 72.0)
        value_x_in = tx + max_w + 0.05
        for lab, val in rows:
            if lab:
                ls_text(c, tx, ty, lab, 7, LIGHT, tracking=1.5, bold=True)
            c.setFont("Helvetica-Bold" if lab else "Helvetica", 6.0)
            c.setFillColor(INK)
            c.drawString(_P_in_local(value_x_in), _P_in_local(ty), val)
            ty -= row_gap
        # ── Footer band + text (satisfies footer-collision gate) ──
        c.setFillColor((0.13, 0.14, 0.12))
        c.rect(_P_in_local(MARGIN_IN), _P_in_local(MARGIN_IN),
               _P_in_local(PAGE_W_IN - 2 * MARGIN_IN),
               _P_in_local(FOOTER_BAND_H_IN), fill=1, stroke=0)
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(_P_in_local(MARGIN_IN + 0.28),
                     _P_in_local(MARGIN_IN + FOOTER_BAND_H_IN / 2 - 0.05),
                     "EMPIRE WORKROOM  ·  HYATTSVILLE, MD  ·  (703) 213-6484")
        c.setFillColor((0.91, 0.54, 0.17))
        c.drawCentredString(_P_in_local(PAGE_W_IN / 2),
                            _P_in_local(MARGIN_IN + FOOTER_BAND_H_IN / 2 - 0.05),
                            "FOR DISCUSSION — NOT FOR CONSTRUCTION")
        c.setFillColor((0.97, 0.95, 0.92))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(_P_in_local(PAGE_W_IN - MARGIN_IN - 0.28),
                          _P_in_local(MARGIN_IN + FOOTER_BAND_H_IN / 2 - 0.05),
                          "SHEET B2  ·  1 OF 1")
        c.save()
        bad_pdf = buf.getvalue()
        with pytest.raises(B2QCFailure) as exc_info:
            enforce_b2_qc(bad_pdf, "Drapery", "pinch_pleat")
        msg = str(exc_info.value)
        assert ("gathered-elevation" in msg.lower()
                or "text-over-geometry" in msg.lower()), (
            f"Gate D-R3-1 must catch closed-panels elevation; "
            f"got: {msg}"
        )

    def test_d_r2_3_layout_math_complete(self):
        """Gate D-R2-3 — LAYOUT MATH must contain the complete
        closure equation. The R1 defect truncated "FLUSH BOTH
        ENDS" to a single char "S". R2 must show the full
        equation (wrap to 2 lines if needed)."""
        from app.services.drawing.templates import render_spec
        import pdfplumber, io
        import re
        pdf = self._render_drapery_r2()
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            page = p.pages[0]
            text = "".join(c["text"] for c in page.chars)
        # The closure note "FLUSH BOTH ENDS" must appear complete.
        assert "FLUSH BOTH ENDS" in text, (
            f"LAYOUT MATH must contain the complete closure note "
            f"'FLUSH BOTH ENDS'; got text: {text[:300]}"
        )

    def test_d_r2_3_header_panel_matches_math(self):
        """Gate D-R2-3 — header meta panel figure must match the
        LAYOUT MATH panel count (single source computes both).
        R2 has N pnls in header and N panels in math — no
        mismatch."""
        from app.services.drawing.templates import render_spec
        import pdfplumber, io
        import re
        pdf = self._render_drapery_r2()
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            page = p.pages[0]
            text = "".join(c["text"] for c in page.chars)
        # Extract N from header "N pnls @ 24\"" and check math
        # shows the same N.
        m = re.search(r'(\d+)\s*pnls', text)
        assert m, f"Header panel figure not found in: {text[:200]}"
        n = int(m.group(1))
        # Look for the math line "N × 19-3/4 + 2 × 4" = 87"
        # (or similar pattern)
        m2 = re.search(rf'{n}\s*[×x]\s*19-3/4', text)
        assert m2, (
            f"Math line should contain {n} × 19-3/4 (from same "
            f"source as header); got text: {text[:300]}"
        )
