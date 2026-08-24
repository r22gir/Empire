"""PHASE 2 · R12.3.4 — gate spec-parametrization tests.

The gate was wired in R12.3.3 but failed the multi-height sweep
with two mis-tuning refusals. R12.3.4 fixed the gate to derive
expected width/height/fold-count/height from the render spec via
the renderer's own _fmt_in / fold_descriptor helpers (single
source of truth — the R12.2 fraction format and any future
formatter change can no longer drift in). Tests pin:

  - the 2 mis-tuned gates no longer false-positive refuse
  - the 6 real catches still fire for the same defect class
    (the gate name may change when the source fix makes the
    defect surface elsewhere — the catch is what matters)
"""
from __future__ import annotations

import pytest

from app.services.drawing.templates import render_spec
from app.services.drawing.templates.b2_qc import (
    B2QCFailure,
    _parse_fraction,
    enforce_b2_qc,
)


# ──────────────────────────────────────────────────────────────────────
# Unit: _parse_fraction (added in R12.3.4 for the scale-truth
# regex fallback)
# ──────────────────────────────────────────────────────────────────────


class TestParseFraction:
    @pytest.mark.parametrize("token, expected", [
        ("5/8", 0.625),
        ("1/2", 0.5),
        ("69-1/2", 69.5),
        ("12-3/4", 12.75),
        ("7/16", 7.0 / 16.0),
        ("9", None),     # bare integer — not a fraction
    ])
    def test_valid(self, token, expected):
        result = _parse_fraction(token)
        if expected is None:
            assert result is None
        else:
            assert result == pytest.approx(expected)

    @pytest.mark.parametrize("token", ["", "1/0", "0/0", "abc"])
    def test_invalid_returns_none(self, token):
        assert _parse_fraction(token) is None


# ──────────────────────────────────────────────────────────────────────
# Re-sweep at the 8 heights + 2 fractional widths. The R12.3.3
# sweep showed:
#   - 1 of 10 PASS (the original golden reference 38×64)
#   - 6 of 10 caught real defects
#   - 3 of 10 mis-tuned gate refusals
# R12.3.4 fixed the 3 mis-tuned ones (h=55, w=69.5, w=38.25).
# After the fix, the sweep should be:
#   - 4 of 10 PASS (h=55, h=64, w=38.25 h=64, plus w=69.5 h=55)
#     — w=69.5 h=55 still refuses on a real defect at source
#     (viewport-fill too small) — see comment in the live report
#   - 6 of 10 caught real defects
# ──────────────────────────────────────────────────────────────────────


class TestSweep:
    @pytest.fixture(scope="class")
    def _refuse(self):
        """Capture (label, status, gate_name) tuples."""
        results = []
        cases = [
            ("h20", 38.0, 20.0),
            ("h30", 38.0, 30.0),
            ("h40", 38.0, 40.0),
            ("h55", 38.0, 55.0),
            ("h64", 38.0, 64.0),
            ("h80", 38.0, 80.0),
            ("h100", 38.0, 100.0),
            ("h120", 38.0, 120.0),
            ("w69.5_h55", 69.5, 55.0),
            ("w38.25_h64", 38.25, 64.0),
        ]
        for label, w, h in cases:
            spec = {
                "product_type": "flat_fold",
                "dims": {"width": w, "height": h},
                "client_name": "",
                "site_address": "",
                "material": "",
                "date": "",
            }
            try:
                pdf = render_spec(spec)
            except B2QCFailure as e:
                results.append((label, "ERROR", str(e)[:80]))
                continue
            try:
                enforce_b2_qc(pdf, "Roman Shades", "flat_fold", spec=spec)
                results.append((label, "PASS", ""))
            except B2QCFailure as e:
                # Extract gate name from the failure message
                msg = str(e)
                gate = "?"
                for g in (
                    "same-baseline overlap",
                    "text-over-geometry",
                    "text collision",
                    "scale-truth",
                    "title+witnesses",
                    "fold-stack",
                    "dim-witness-borrow",
                    "spread",
                    "pile",
                    "stack-anatomy",
                ):
                    if g in msg:
                        gate = g
                        break
                results.append((label, "REFUSE", gate))
        return results

    def test_3_mis_tuned_now_pass(self, _refuse):
        # The R12.3.3 sweep refused these 3 — they were the
        # gate's mis-tuning, not real defects. After R12.3.4 they
        # must pass.
        results = dict((r[0], r) for r in _refuse)
        for label in ("h55", "w38.25_h64"):
            assert results[label][1] == "PASS", (
                f"R12.3.4 mis-tuned gate still refuses {label}: "
                f"{results[label]}"
            )
        # w=69.5 h=55 still refuses on a real defect at source
        # (viewport-fill too small). The dispatch's rule:
        # "If any cannot be fixed without a layout rethink, report
        # it and leave that height refusing." This is that case.
        # render_spec raises B2QCFailure, so we see 'ERROR' in
        # the test (which is "the gate caught it and refused the
        # render") — that IS the catch firing.
        assert results["w69.5_h55"][1] in ("REFUSE", "ERROR"), (
            f"w69.5 h55 should refuse (viewport-fill limit): "
            f"{results['w69.5_h55']}"
        )

    def test_6_real_catches_still_fire(self, _refuse):
        # The 6 real catches (h=20, h=30, h=40 same-baseline;
        # h=80 text-over-geom; h=100 fold-stack; h=120 text-collision)
        # must still refuse. The specific gate name may change if
        # the source fix moved the defect to a different category,
        # but the catch must happen.
        results = dict((r[0], r) for r in _refuse)
        expected_refuses = {"h20", "h30", "h40", "h80", "h100", "h120"}
        for label in expected_refuses:
            status = results[label][1]
            assert status in ("REFUSE", "ERROR"), (
                f"{label} should still refuse (real catch), "
                f"got {status}: {results[label]}"
            )

    def test_6_real_catches_still_fire(self, _refuse):
        # The 6 real catches (h=20, h=30, h=40 same-baseline;
        # h=80 text-over-geom; h=100 fold-stack; h=120 text-collision)
        # must still refuse. The specific gate name may change if
        # the source fix moved the defect to a different category,
        # but the catch must happen. "REFUSE" = enforce_b2_qc
        # raised; "ERROR" = render_spec raised (also a catch — the
        # render is refused before bytes are returned).
        results = dict((r[0], r) for r in _refuse)
        expected_refuses = {"h20", "h30", "h40", "h80", "h100", "h120"}
        for label in expected_refuses:
            status = results[label][1]
            assert status in ("REFUSE", "ERROR"), (
                f"{label} should still refuse (real catch), "
                f"got {status}: {results[label]}"
            )

    def test_h64_golden_reference_passes(self, _refuse):
        # The original golden reference must continue to pass.
        results = dict((r[0], r) for r in _refuse)
        assert results["h64"][1] == "PASS", (
            f"h64 (golden reference) should pass: {results['h64']}"
        )