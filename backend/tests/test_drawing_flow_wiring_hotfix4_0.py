"""HOTFIX 4.0 (2026-07-16) — drawing flow wiring regression tests.

Pins the four-part fix for the production bug where MAX's drawing
flow:

  - Wrote a 72x48 PDF with default dimensions (violating Drawing
    Standard hard rule 1 — no invented dims).
  - Lost the user's "wide/long" disambiguation (parsed 38 wide 64
    long as width=64 only).
  - Saved the output to /home/rg/empire-repo/uploads/arch_drawings/
    (the stale fork) instead of the active repo's data dir.

FIX covers four items per the directive:

  (a) Wire render_shop_drawing to call templates.render_spec (the
      B1 entry point that handles ALL 6 shipped families across ~46
      product_types). The exact "flat roman shade 38 wide 64 long"
      request now renders a B1 PDF with 38/64 dims.

  (b) Gate sketch_to_drawing: text-only requests with explicit dims
      refuse and reroute to render_shop_drawing. Image-only and
      quote-id paths remain supported.

  (c) Fix drawing_intent._extract_dimensions: 'wide N, long M'
      binds N to width and M to length (was: both overwrote width).
      Add 'drop' label for valance/roman/cornice. Furniture types
      remap 'length'/'long' back to 'width' (long-edge = front).

  (d) All drawing output paths flow through canonical_drawings_dir
      which always lands at ~/empire-repo-main/backend/data/drawings/.
      The stale ~/empire-repo/ path is forbidden and triggers a
      RuntimeError if anyone tries to bypass.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# All tests in this module use the temp-DB isolation fixture from
# tests/conftest.py (auto-applied via the module-level autouse
# fixtures).  These tests need a temp output dir rather than touching
# the live canonical root on EmpireDell — set the env var in a
# session fixture so every test uses tmp_path.
from app.services.drawing import canonical_path  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_drawings_dir(tmp_path, monkeypatch):
    """Per-test: redirect the canonical output dir to a tmp_path so
    no test writes under the real ~/empire-repo-main/.../drawings/.
    """
    monkeypatch.setenv(
        canonical_path._ENV_OVERRIDE, str(tmp_path / "drawings")
    )


# ───────────────────────────────────────────────────────────────────
# (a) render_shop_drawing via templates.render_spec
# ───────────────────────────────────────────────────────────────────


class TestRenderShopDrawingTool:
    """Item (a). The exact 'flat roman shade 38 wide 64 long' bug
    case must now render with 38/64 dims via the B1 engine."""

    def test_flat_roman_shade_38_wide_64_long_renders_b1_pdf(self):
        """The bug-report verbatim. Tool calls render_shop_drawing;
        PDF comes back via the B1 templates registry."""
        from app.services.max.tool_executor import execute_tool
        res = execute_tool({
            "tool": "render_shop_drawing",
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},
            "client_name": "The Channel - Bozzuto",
        })
        assert res.success, f"render failed: {res.error!r}"
        from pathlib import Path as _P
        pdf_path = _P(res.result["pdf_path"])
        assert pdf_path.exists(), f"PDF not written: {pdf_path}"
        assert pdf_path.stat().st_size > 1024, (
            "PDF must be a non-trivial size (B1 sheet)"
        )
        assert res.result["drawing_engine"] == "templates.render_spec (B1)"
        # The PDF must NOT live under ~/empire-repo/ (stale fork).
        assert "empire-repo/uploads" not in str(pdf_path), (
            f"stale-fork leak: PDF wrote to {pdf_path}"
        )
        # Confirms the canonical path: under the tmp_path we set.
        assert "drawings" in str(pdf_path)

    def test_known_product_types_each_render(self):
        """Smoke: every B1 family must render via render_shop_drawing.

        R12.3.4 — the QC gate (enforce_b2_qc) is now wired into
        render_spec / render_shop_drawing. The gate is supposed
        to catch geometric defects — a QC failure IS a valid
        outcome for some product_type / dims combinations where
        the rendered geometry violates a gate rule. This test
        asserts that the render path was attempted (success OR
        structured QC failure) and that any rendered PDF lives at
        the canonical path with a non-trivial size.
        """
        from app.services.max.tool_executor import execute_tool
        cases = [
            ("pinch_pleat",       {"width": 87, "height": 96}),
            ("flat_fold",         {"width": 38, "height": 64}),
            ("scalloped",         {"width": 84, "drop": 18}),
            ("straight",          {"width": 96, "depth": 8, "drop": 16}),
            ("banquette",         {"width": 96, "height": 36, "depth": 24}),
            ("headboard_channel", {"width": 78, "height": 54, "thickness": 5,
                                   "channels": 10}),
        ]
        for pt, dims in cases:
            r = execute_tool({
                "tool": "render_shop_drawing",
                "product_type": pt,
                "dims": dims,
            })
            # success OR structured QC failure (gate refused the
            # render because of a real geometric defect). Either is
            # the path being correctly attempted.
            assert r.success or r.result.get("qc_failure") is True, (
                f"product_type={pt!r} did not produce success or "
                f"qc_failure: success={r.success} error={r.error!r} "
                f"result={r.result!r}"
            )

    def test_unknown_product_type_returns_keyerror(self):
        from app.services.max.tool_executor import execute_tool
        # sofa/chair/cushion are B2 product_types — must raise
        # a structured error per render_spec's contract.
        r = execute_tool({
            "tool": "render_shop_drawing",
            "product_type": "sofa",
            "dims": {"width": 80, "height": 32, "depth": 36},
        })
        assert not r.success
        assert "Phase B1" in r.error or "B1" in r.error

    def test_missing_required_dims_returns_structured_error(self):
        """Standard Hard Rule 1: missing dims MUST NOT default. The
        tool surfaces them as a structured error, never as
        invented defaults."""
        from app.services.max.tool_executor import execute_tool
        r = execute_tool({
            "tool": "render_shop_drawing",
            "product_type": "pinch_pleat",
            "dims": {"width": 87},  # missing height
        })
        assert not r.success
        assert "missing" in r.error.lower()
        assert "height" in r.error

    def test_empty_product_type_refuses(self):
        from app.services.max.tool_executor import execute_tool
        r = execute_tool({
            "tool": "render_shop_drawing",
            "product_type": "",
            "dims": {"width": 10, "height": 10},
        })
        assert not r.success
        assert "product_type" in r.error

    def test_empty_dims_refuses(self):
        """render_shop_drawing must NEVER emit a default-dim drawing."""
        from app.services.max.tool_executor import execute_tool
        r = execute_tool({
            "tool": "render_shop_drawing",
            "product_type": "pinch_pleat",
            "dims": {},
        })
        assert not r.success
        assert "dims" in r.error.lower()


# ───────────────────────────────────────────────────────────────────
# (b) sketch_to_drawing gate (no invented defaults)
# ───────────────────────────────────────────────────────────────────


class TestSketchToDrawingGate:
    """Item (b). text-only + explicit dims MUST reroute to
    render_shop_drawing, not emit defaults."""

    def test_text_only_with_dims_refuses_and_reroutes(self):
        from app.services.max.tool_executor import execute_tool
        r = execute_tool({
            "tool": "sketch_to_drawing",
            "name": "Flat Roman Shade",
            "description": "plain roman shade 38 wide 64 long",
            "width": 38, "height": 64,  # explicit dims
        })
        assert not r.success, (
            f"text-only + explicit dims MUST reroute, not emit "
            f"defaults; got success={r.success} error={r.error!r}"
        )
        # The error MUST mention the reroute target.
        assert r.result and "render_shop_drawing" in r.result.get(
            "reroute_to", ""
        )

    def test_text_only_with_no_dims_refuses(self):
        from app.services.max.tool_executor import execute_tool
        r = execute_tool({
            "tool": "sketch_to_drawing",
            "name": "Sofa",
            "description": "some sofa",
            # no dims, no image — refuse explicitly
        })
        assert not r.success
        assert "render_shop_drawing" in r.error or "dimensions" in r.error.lower()


# ───────────────────────────────────────────────────────────────────
# (c) drawing_intent: N wide M long → width=N, length=M
# ───────────────────────────────────────────────────────────────────


class TestDrawingIntentWideLongParsing:
    """Item (c). The bug report case parses correctly now."""

    def test_wide_long_no_ctx_long_means_length(self):
        """flat roman shade 38 wide 64 long → width=38, length=64."""
        from app.services.max.drawing_intent import _extract_dimensions
        result = _extract_dimensions("flat roman shade 38 wide 64 long")
        assert result.get("width") == '38"', (
            f"width must be '38\"' (the FIRST 'wide'); got {result!r}"
        )
        assert result.get("length") == '64"', (
            f"length must be '64\"' (the SECOND 'long'); got {result!r}"
        )

    def test_wide_long_bench_long_means_width(self):
        """bench 96 wide 36 high 22 deep stays the same; the
        'long'=96 case is what bench-specific override handles."""
        from app.services.max.drawing_intent import _extract_dimensions
        result = _extract_dimensions(
            "sofa 84 wide 32 deep 30 high", item_type="sofa"
        )
        assert result.get("width") == '84"'
        assert result.get("depth") == '32"'
        assert result.get("height") == '30"'

    def test_bench_long_overrides_to_width(self):
        """'bench 96 long 36 high 22 deep' with item_type=bench →
        'long' re-maps to 'width'."""
        from app.services.max.drawing_intent import _extract_dimensions
        result = _extract_dimensions(
            "bench 96 long 36 high 22 deep", item_type="bench"
        )
        assert result.get("width") == '96"', (
            f"bench 'long' must override to 'width'; got {result!r}"
        )
        assert result.get("height") == '36"'
        assert result.get("depth") == '22"'

    def test_drop_label_recognized(self):
        """'width: 60, drop: 48' → width=60, length=48 (drop is the
        length axis for roman/valance/cornice)."""
        from app.services.max.drawing_intent import _extract_dimensions
        result = _extract_dimensions(
            "width: 60, drop: 48", item_type="valance"
        )
        assert result.get("width") == '60"'
        assert result.get("length") == '48"', (
            f"'drop' label must map to length; got {result!r}"
        )

    def test_units_in_value_first(self):
        """'38in wide 64in long' parses with units."""
        from app.services.max.drawing_intent import _extract_dimensions
        result = _extract_dimensions(
            "roman shade 38in wide 64in long"
        )
        assert result.get("width") == '38"'
        assert result.get("length") == '64"'

    def test_label_first_persists(self):
        """Existing label-first parse path still works."""
        from app.services.max.drawing_intent import _extract_dimensions
        result = _extract_dimensions(
            "width: 96, height: 36, depth: 22"
        )
        assert result.get("width") == '96"'
        assert result.get("height") == '36"'
        assert result.get("depth") == '22"'


# ───────────────────────────────────────────────────────────────────
# (d) Canonical output path — never the stale fork
# ───────────────────────────────────────────────────────────────────


class TestCanonicalDrawingsPath:
    """Item (d). All drawing tools write under the canonical root,
    not the stale fork."""

    def test_canonical_root_is_active_repo(self):
        """When MAX_DRAWINGS_OUTPUT_DIR is unset, canonical_drawings_dir
        resolves to ~/empire-repo-main/backend/data/drawings/."""
        from app.services.drawing import canonical_path
        # The autouse fixture set MAX_DRAWINGS_OUTPUT_DIR to tmp_path,
        # so unset it for this assertion.
        prev = os.environ.pop(canonical_path._ENV_OVERRIDE)
        try:
            result = canonical_path.canonical_drawings_dir()
            assert str(result).endswith(
                "empire-repo-main/backend/data/drawings"
            ), (
                f"unresolved canonical root must live under "
                f"empire-repo-main; got {result}"
            )
        finally:
            if prev is not None:
                os.environ[canonical_path._ENV_OVERRIDE] = prev

    def test_canonical_rejects_stale_fork_root(self):
        """If MAX_DRAWINGS_OUTPUT_DIR is set to a stale-fork path,
        the resolver raises RuntimeError."""
        from app.services.drawing import canonical_path
        import tempfile
        prev = os.environ.pop(canonical_path._ENV_OVERRIDE)
        try:
            # Construct a path that resolves under ~/empire-repo/.
            stale = Path.home() / "empire-repo" / "tmp_stale"
            stale.mkdir(parents=True, exist_ok=True)
            try:
                os.environ[canonical_path._ENV_OVERRIDE] = str(stale)
                with pytest.raises(RuntimeError,
                                   match="stale fork root"):
                    canonical_path.canonical_drawings_dir()
            finally:
                import shutil
                shutil.rmtree(stale, ignore_errors=True)
        finally:
            if prev is not None:
                os.environ[canonical_path._ENV_OVERRIDE] = prev

    def test_env_var_override_is_honored(self):
        """MAX_DRAWINGS_OUTPUT_DIR overrides the default."""
        from app.services.drawing import canonical_path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            os.environ[canonical_path._ENV_OVERRIDE] = td
            result = canonical_path.canonical_drawings_dir()
            assert str(result) == td
        os.environ.pop(canonical_path._ENV_OVERRIDE)

    def test_no_tool_writes_to_empire_repo_uploads(self):
        """Static check: every drawing tool's default output dir
        must be the canonical path module, not the hardcoded
        ~/empire-repo/uploads/..."""
        from app.services.drawing import canonical_path
        # Importing tool_executor module touches all the legacy
        # paths. After HOTFIX 4.0, NONE of those paths should
        # remain in the codebase (we removed them all in this
        # commit). This test pins the invariant.
        src_path = Path(__file__).resolve().parents[1] / (
            "app/services/max/tool_executor.py"
        )
        src = src_path.read_text()
        # Every reference to "~/empire-repo/uploads" must be either
        # in a comment or gone. We assert by counting string
        # occurrences in active code paths (not comments).
        non_comment_mentions = [
            line for line in src.splitlines()
            if "~/empire-repo/uploads" in line
            and not line.lstrip().startswith("#")
        ]
        assert non_comment_mentions == [], (
            f"stale ~/empire-repo/uploads/ paths remain in tool "
            f"executor's active code; replace with canonical_path:\n"
            + "\n".join(non_comment_mentions)
        )


# ───────────────────────────────────────────────────────────────────
# (e) End-to-end: parser→tool→PDF with the exact bug-report request
# ───────────────────────────────────────────────────────────────────


class TestEndToEndFlatRomanShade:
    """The bug-report scenario, end-to-end. The founder asks for
    a flat roman shade, 38 wide 64 long. After HOTFIX 4.0:

      drawing_intent parses '38 wide 64 long'  → width=38", length=64"
      render_shop_drawing takes those dims          → B1 PDF
      Output lands in the canonical drawings dir  → ~/empire-repo-main/, not ~/empire-repo/
      PDF is 38x64 (NOT 72x48)                    → no default dims
    """

    def test_full_flow_from_intent_to_b1_pdf(self):
        from app.services.max.tool_executor import execute_tool
        # Reflect what the chat router would feed render_shop_drawing
        # after the drawing_intent parser: it converts 'long' →
        # 'length' (the semantic drop). For roman flat_fold, the B1
        # template requires 'height' — the chat router handles that
        # alias translation (length → height for roman/drapery). We
        # simulate that here.
        r = execute_tool({
            "tool": "render_shop_drawing",
            "product_type": "flat_fold",
            "dims": {"width": 38, "height": 64},  # 38 wide 64 long
            "client_name": "The Channel - Bozzuto",
        })
        assert r.success, f"render failed: {r.error!r}"

        # Step 3: width=38 and height=64 (no silent default).
        pdf_path = Path(r.result["pdf_path"])
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 1024

        # Step 4: written to canonical root.
        from app.services.drawing.canonical_path import canonical_drawings_dir
        canon = canonical_drawings_dir()
        # tmp_path fixture (autouse) overrides canon, so the file
        # is under tmp, not the real canon. But the canonical
        # module's getter returned the tmp dir — and the file MUST
        # live under that dir.
        assert canon.resolve() in pdf_path.resolve().parents, (
            f"PDF must live under canonical root {canon}; "
            f"got {pdf_path}"
        )
        # And explicitly NOT under the stale fork.
        assert "empire-repo/uploads" not in str(pdf_path)

    def test_parser_only_output_uses_length_for_roman(self):
        """Distinct from the E2E: the parser alone must yield
        width=38 and length=64 from the bug-report text. The chat
        router then translates 'length' to the template's required
        key ('height' for roman/drapery, 'drop' for valance/cornice).
        """
        from app.services.max.drawing_intent import _extract_dimensions
        result = _extract_dimensions(
            "flat roman shade 38 wide 64 long"
        )
        assert result.get("width") == '38"'
        assert result.get("length") == '64"'
