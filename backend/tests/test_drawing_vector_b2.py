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
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        # Each field must be present (no info loss).
        for needle, desc in [
            ("Frolich Ln, Hyattsville, MD 20781", "address row"),
            ("(703) 213-6484", "phone row"),
            ("workroom@empirebox.store", "email row"),
        ]:
            assert needle in text, f"{desc} ({needle!r}) missing"

    def test_no_garbled_interleaving_in_header(self):
        """The B1 bug interleaved address digits into phone digits.
        Pin: the rendered PDF must contain the three fields in
        non-interleaved order — address first, then phone, then
        email. The BUG substring ('Hyattsvil(l7e0, 3M)D 2 1230-7684184')
        was address text interleaved with phone text in the same row;
        B2 puts each on its own line so the chars are in strict
        order."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
        })
        text = _pdf_text(pdf)
        # All three fields present, in the expected non-interleaved
        # order: address → phone → email.
        addr = text.find("Frolich Ln, Hyattsville, MD 20781")
        phone = text.find("(703) 213-6484")
        email = text.find("workroom@empirebox.store")
        assert addr >= 0 and phone >= 0 and email >= 0, (
            f"address/phone/email not all present; addr={addr} "
            f"phone={phone} email={email}"
        )
        assert addr < phone < email, (
            f"header fields out of order: addr@{addr}, "
            f"phone@{phone}, email@{email} — they must be in "
            f"strict order (B2 splits them onto separate rows)"
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
        # The label "CLIENT:" should NOT appear when no client.
        assert "CLIENT:" not in text, (
            "BUG: CLIENT row rendered when client_name is empty; "
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
        assert "CLIENT:" in text, "CLIENT row missing when client named"
        assert "Channel - Bozzuto" in text, (
            "client name text not present in CLIENT row"
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
    """MATERIAL / SITE / DATE rows: when the spec value is empty,
    the row is omitted entirely (not "—")."""

    def test_material_row_omitted_when_empty(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "material": "",
        })
        text = _pdf_text(pdf)
        assert "MATERIAL:" not in text

    def test_site_row_omitted_when_empty(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "site_address": "",
        })
        text = _pdf_text(pdf)
        assert "SITE:" not in text

    def test_date_row_omitted_when_empty(self):
        """HOTFIX B2c — DATE is a STANDARD row (every drawing has
        a date; defaults to today when not specified). Pre-B2c the
        DATE row was OPTIONAL (rendered only when set); B2c
        promotes it to always-render so the title block is uniform.
        MATERIAL/SITE remain optional."""
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "date": "",
        })
        text = _pdf_text(pdf)
        assert "DATE:" in text, (
            f"DATE row should always render (B2c); got: "
            f"{text[-300:]!r}"
        )

    def test_optional_rows_render_when_set(self):
        from app.services.drawing.templates import render_spec
        pdf = render_spec({
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "material": "CB900-14 coral fabric",
            "site_address": "The Channel - Bozzuto, 650 Water St SW",
            "date": "2026-07-24",
        })
        text = _pdf_text(pdf)
        for needle in ("MATERIAL:", "CB900-14", "SITE:", "Channel - Bozzuto",
                       "DATE:", "2026-07-24"):
            assert needle in text, f"optional row missing {needle!r}"


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
        # 4 B1 defects absent
        assert "CLIENT:" not in text
        assert "MATERIAL:" not in text
        assert "SITE:" not in text
        assert "•" not in text

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
        # passes — we need text in the right column x ≥ 6.5").
        c.setFillColor((0, 0, 0))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72 * 6.6, 72 * 4, "TITLE")
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
        """HOTFIX B2c (1) — REV + DATE rows added to title block."""
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
        assert "DATE:" in text, (
            f"title block must contain DATE row; got: {text[:300]!r}"
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
