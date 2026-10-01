"""Drawing-router must not intercept invoice/quote/split requests.

Regression for live bug 2026-10-01: furniture words + dims (or broad
'make a' / 'generate the' keywords) hijacked billing prompts.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_drawing_intent():
    path = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "max" / "drawing_intent.py"
    )
    spec = importlib.util.spec_from_file_location(
        "drawing_intent_business_priority_test", path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MARLEY_INVOICE = (
    "Create two draft invoices for Marley's Hyattsville, split from "
    "INV-2026-123... U-banquette seat backs | 72.65 sf | $45 ..."
)
MARLEY_WITH_DIMS = MARLEY_INVOICE + " | width 96"


def test_marley_invoice_prompt_not_drawing():
    di = _load_drawing_intent()
    assert di.is_business_document_intent(MARLEY_INVOICE)
    assert di.is_drawing_intent(MARLEY_INVOICE) is False
    handoff = di.build_drawing_handoff(MARLEY_INVOICE)
    assert handoff.is_drawing_intent is False


def test_marley_invoice_with_line_dims_still_not_drawing():
    di = _load_drawing_intent()
    assert di.is_drawing_intent(MARLEY_WITH_DIMS) is False


def test_split_inv_by_bench_section_not_drawing():
    di = _load_drawing_intent()
    msg = "split INV-2026-123 into two invoices, one per bench section"
    assert di.is_drawing_intent(msg) is False


def test_quote_bench_cushions_not_drawing():
    di = _load_drawing_intent()
    msg = "quote for 2 bench cushions 48x18"
    assert di.is_drawing_intent(msg) is False


def test_make_a_quote_not_drawing():
    di = _load_drawing_intent()
    assert di.is_drawing_intent("make a quote for the bench") is False


def test_draw_banquette_is_drawing():
    di = _load_drawing_intent()
    assert di.is_drawing_intent("draw a banquette 120in wide") is True


def test_shop_drawing_for_bench_is_drawing():
    di = _load_drawing_intent()
    assert di.is_drawing_intent("make a shop drawing for the bench") is True


def test_generate_b1_sheet_still_drawing():
    di = _load_drawing_intent()
    assert di.is_drawing_intent(
        "generate the B1 sheet for the Willard bench"
    ) is True


def test_continuation_guard_skips_invoice_after_missing_keys_turn():
    import importlib.util
    dp_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "max" / "drawing_pending.py"
    )
    spec = importlib.util.spec_from_file_location("dp_biz_test", dp_path)
    dp = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = dp
    spec.loader.exec_module(dp)
    history = [{
        "role": "assistant",
        "content": (
            "I have the 'banquette' product_type but I'm still missing: "
            "width, height, depth. Please supply those so I can render "
            "the B1 sheet."
        ),
    }]
    msg = "split INV-2026-123 into two invoices, one per bench section"
    assert dp.looks_like_continuation(msg, history) is None
