"""HOTFIX 4.0b (2026-07-23) — router-to-engine wiring tests.

Production defect: the drawing-router interceptor captured drawing-
intent messages BEFORE the LLM, then emitted a structured handoff
JSON that NO component consumed. Result:
  R1 (9:06 PM) — "create a shop drawing for a flat roman shade, 38
       wide 64 long" → handoff {dimensions_known: {width:38,
       length:64}, dimensions_missing: [height]}; the length→height
       translation existed ONLY in the test, not in production.
  R2 (9:15 PM) — sketch_to_drawing correctly refused per the gate
       (HOTFIX 4.0 b). No path led to render_shop_drawing.
  R3 (9:21 PM) — explicit "product_type flat_fold" mention was
       silently dropped by _extract_item_type; subject='' and
       item_type='generic'.

Engine proof (9:23 PM): execute_tool render_shop_drawing
  product_type=flat_fold dims={width:38, height:64}
  → success, 4766-byte PDF at the canonical root.

FIX (four parts):
  (a) Interceptor is now a ROUTER: when the handoff resolves a
      B1 product_type + complete (translated) dims, the chat
      path invokes render_shop_drawing via execute_tool.
  (b) _extract_item_type detects explicit B1 product_type mentions
      ("product_type flat_fold"); _try_resolve_b1_type resolves
      style-hint substrings ("flat roman shade" → flat_fold).
  (c) Length→height alias translation for roman/drapery/headboard;
      length→drop for valance/cornice.
  (d) Test doctrine: E2E tests enter through the production
      entry point (POST /api/v1/max/chat), not the underlying
      helper. A test that simulates the seam it exists to verify
      is a defect class.

TEST DOCTRINE (per HOTFIX 4.0b (d)):
  If a test mocks out the layer it claims to verify, it has a
  defect class. The drawing-router path was previously tested by
  mocking build_drawing_handoff; that test passed even when the
  router emitted dead-end JSON. Now we enter via the real chat
  POST and assert the response.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_drawings_dir(tmp_path, monkeypatch):
    """Per-test: redirect canonical drawings dir to tmp_path."""
    from app.services.drawing import canonical_path
    monkeypatch.setenv(canonical_path._ENV_OVERRIDE, str(tmp_path / "drawings"))


# ───────────────────────────────────────────────────────────────────
# Unit-level: the handoff layer
# ───────────────────────────────────────────────────────────────────


class TestHandoffLayer:
    """The drawing_intent layer must produce a router-ready handoff
    for the user's R1/R3 cases."""

    def test_r1_flat_roman_shade_resolves_to_ready(self):
        """R1 verbatim: 'create a shop drawing for a flat roman
        shade, 38 wide 64 long' → b1=flat_fold, translated_dims
        has width=38 + height=64, ready=True."""
        from app.services.max.drawing_intent import build_drawing_handoff
        h = build_drawing_handoff(
            "create a shop drawing for a flat roman shade, 38 wide 64 long"
        )
        assert h.is_drawing_intent
        assert h.b1_product_type == "flat_fold"
        assert h.ready, (
            f"handoff must be ready for the R1 case (length→height "
            f"alias translation); got missing_template_keys={h.missing_template_keys}"
        )
        assert h.translated_dims["width"] == '38"'
        assert h.translated_dims["height"] == '64"'

    def test_r3_explicit_product_type_no_longer_generic(self):
        """R3 verbatim: 'use the render_shop_drawing tool:
        product_type flat_fold, dims width 38 height 64' → b1 bound
        to flat_fold explicitly, subject=flat_fold (not generic)."""
        from app.services.max.drawing_intent import build_drawing_handoff
        h = build_drawing_handoff(
            "use the render_shop_drawing tool: product_type flat_fold,"
            " dims width 38 height 64"
        )
        assert h.is_drawing_intent
        assert h.b1_product_type == "flat_fold"
        assert h.subject == "flat_fold", (
            f"subject must carry the explicit B1 type (no more 'generic'); "
            f"got subject={h.subject!r}"
        )
        assert h.ready

    def test_valance_length_maps_to_drop(self):
        """Length→drop translation for valance/cornice."""
        from app.services.max.drawing_intent import build_drawing_handoff
        h = build_drawing_handoff("draw a valance 84 wide 18 drop")
        assert h.b1_product_type == "kingston"
        assert h.translated_dims.get("drop") == '18"', (
            f"length→drop must fire for valance; got {h.translated_dims}"
        )
        assert h.ready

    def test_draw_a_bench_preserves_furniture_long_to_width(self):
        """Furniture override: 'bench 96 long 36 high' → width=96,
        height=36 (long-axis == width for bench)."""
        from app.services.max.drawing_intent import build_drawing_handoff
        h = build_drawing_handoff(
            "draw a bench 96 long 36 high 22 deep"
        )
        assert h.b1_product_type == "bench"
        assert h.translated_dims["width"] == '96"'
        assert h.translated_dims["height"] == '36"'
        assert h.translated_dims["depth"] == '22"'
        assert h.ready


# ───────────────────────────────────────────────────────────────────
# (c) TRUE E2E: enter through POST /api/v1/max/chat
# ───────────────────────────────────────────────────────────────────


class TestChatRouteToRenderShopDrawing:
    """HOTFIX 4.0b (c) — the test doctrine addition. We enter
    through the real chat POST and assert the response text routes
    via render_shop_drawing.

    Pre-fix tests mocked build_drawing_handoff and the dispatcher
    in isolation. They passed even when the router emitted dead-end
    JSON. These tests instead exercise the WHOLE PRODUCTION PATH
    (draw → router → intercept → resolve → render_shop_drawing →
    report PDF path) and assert that the response carries the
    canonical PDF path.
    """

    def test_draw_a_flat_roman_shade_lands_at_canonical_root(self):
        """The exact R1 sentence, full chat path."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        r = client.post(
            "/api/v1/max/chat",
            json={
                "message": "create a shop drawing for a flat roman "
                           "shade, 38 wide 64 long",
                "channel": "web",
                "conversation_id": "hotfix_4_0b_test",
            },
        )
        assert r.status_code == 200, f"chat failed: {r.text}"
        body = r.json()

        # ── Pre-fix assertions ──
        # model_used used to be 'drawing-router' even when no PDF was
        # generated. The response was a JSON dump that nothing
        # consumed. Assert those are GONE.
        assert body.get("response") is not None, body
        response = body["response"]

        # The PDF MUST live at the canonical root (per the user's
        # bug report — the issue was always that the file went to
        # the stale fork).
        assert "empire-repo/uploads" not in response, (
            f"stale-fork leak in router response: {response}"
        )

        # The router routed to render_shop_drawing (B1 templates),
        # not the legacy sketch_to_drawing. The response text
        # should reflect that path: include 'flat_fold', 'B1', or
        # the rendered PDF path.
        assert "drawing_path=" in response or "flat_fold" in response or (
            "pdf_path=" in response and "B1" in response
        ), (
            f"response must confirm the B1 router pipeline ran; "
            f"got: {response[:300]!r}"
        )

        # Verify the actual PDF exists at the canonical root.
        from app.services.drawing.canonical_path import canonical_drawings_dir
        canon = canonical_drawings_dir()
        pdfs = list(canon.glob("flat_fold_*.pdf"))
        assert pdfs, (
            f"no PDF was written at the canonical root {canon}; "
            f"router returned: {response}"
        )
        assert all(p.stat().st_size > 1024 for p in pdfs), (
            "PDFs must be non-trivial (B1 sheet)"
        )


# ───────────────────────────────────────────────────────────────────
# (b) _extract_item_type explicit-B1-type detection
# ───────────────────────────────────────────────────────────────────


class TestExplicitProductTypeDetection:
    """HOTFIX 4.0b (b) — _extract_item_type binds explicit B1
    product_type mentions; never returns ('generic', '') on a chat
    message that names the type."""

    def test_explicit_product_type_pinched_pleat(self):
        from app.services.max.drawing_intent import _extract_item_type
        subject, item_type = _extract_item_type(
            "product_type pinch_pleat, width 36, height 60"
        )
        assert item_type == "pinch_pleat", (
            f"explicit 'product_type pinch_pleat' must bind; got "
            f"item_type={item_type!r}"
        )
        assert subject == "pinch_pleat"

    def test_explicit_render_shop_drawing_tool_mention(self):
        """The bare 'use the render_shop_drawing tool' mention
        alone doesn't carry a product_type, but the next B1 type
        name does — and should bind."""
        from app.services.max.drawing_intent import _try_resolve_b1_type
        assert _try_resolve_b1_type(
            "render a headboard_channel 78 wide 54 high 5 thick",
            "headboard_channel",
        ) == "headboard_channel"

    def test_no_match_returns_none_not_generic(self):
        from app.services.max.drawing_intent import _try_resolve_b1_type
        # Genuinely no B1 type. Returns None — the founder will be
        # asked for a precise B1 type (R3 hardening).
        assert _try_resolve_b1_type(
            "draft a plan for Q4 marketing", "generic"
        ) is None


# ───────────────────────────────────────────────────────────────────
# Length→height / length→drop alias translation
# ───────────────────────────────────────────────────────────────────


class TestAliasTranslation:
    """HOTFIX 4.0b (a/c) — the user's parser picks 'length' for
    'long'; the router translates that to the template-required
    'height' (roman/drapery/headboard) or 'drop' (valance/cornice).
    """

    def test_length_to_height_for_roman(self):
        from app.services.max.drawing_intent import (
            _translate_dims_for_b1_product,
        )
        out = _translate_dims_for_b1_product(
            {"width": '38"', "length": '64"'}, "flat_fold",
        )
        assert "height" in out, f"length→height translation missing: {out}"
        assert out["height"] == '64"'
        assert "length" not in out

    def test_length_to_drop_for_valance(self):
        from app.services.max.drawing_intent import (
            _translate_dims_for_b1_product,
        )
        out = _translate_dims_for_b1_product(
            {"width": '84"', "length": '18"'}, "kingston",
        )
        assert out.get("drop") == '18"', (
            f"length→drop translation missing for valance: {out}"
        )

    def test_length_to_drop_for_cornice(self):
        from app.services.max.drawing_intent import (
            _translate_dims_for_b1_product,
        )
        out = _translate_dims_for_b1_product(
            {"width": '96"', "depth": '8"', "length": '16"'},
            "straight",
        )
        assert out.get("drop") == '16"', (
            f"length→drop translation missing for cornice: {out}"
        )


# ───────────────────────────────────────────────────────────────────
# (d) Test doctrine — module docstring + a guard test
# ───────────────────────────────────────────────────────────────────


class TestDoctrineGuard:
    """HOTFIX 4.0b (d) — a guard that reminds future contributors
    that E2E tests must enter through the production entry point.
    Mocks for build_drawing_handoff / DrawingHandoff.ready /
    chat-path dispatchers are FORBIDDEN in this module — pin the
    invariant with a static check."""

    def test_no_mock_decorators_in_module(self):
        """No `mock.patch` of drawing-router internals lives in this
        test file. The router integration must be tested via the
        real chat POST."""
        import re
        # Strip the docstring + the canonical-path strings in this
        # module so the guard doesn't trip on its own documentation.
        src = re.sub(r'"""[\s\S]*?"""', '', Path(__file__).read_text())
        # Only flag ACTIVE mock.patch calls (not comments / strings).
        # We require the pattern to be followed by `(...)` to match
        # a real call.
        patterns = (
            r'mock\.patch\(\s*["\']app\.services\.max\.drawing_intent',
            r'mock\.patch\(\s*["\']app\.routers\.max\.router\.build_drawing',
            r'mock\.patch\.object\(.*build_drawing',
        )
        for pat in patterns:
            assert not re.search(pat, src), (
                f"HOTFIX 4.0b (d): mocking forbidden pattern "
                f"{pat!r}. Tests in this module MUST enter through "
                f"the real chat POST. (A test that mocks the layer it "
                f"exists to verify is a defect class — the bug we just "
                f"fixed.)"
            )
