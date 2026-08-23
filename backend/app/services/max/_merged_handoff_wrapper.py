"""PHASE 2 · R12 Option A — wrap merge_founder_reply's dict as a
DrawingHandoff-shaped object so _drawing_render can consume it.

A merged continuation reply is by definition a drawing intent
(the founder typed dim-supplying content in answer to the missing-
keys question). Pre-fix, the chat handler accessed the dict-shape
flag directly and would AttributeError; this wrapper gives the
dict the same shape as DrawingHandoff.

After this wrapper exists, the existing chat-routing if-block
routes it through _drawing_render without falling through to the
LLM tool loop — which otherwise retries sketch_to_drawing 2-3x
on text+dims refusal and produces the 13-21s freeze (probes L
and N).

Returns None when the input is not a dict-like; the caller falls
through to the pre-existing build_drawing_handoff path.
"""
from __future__ import annotations

import types as _types


def wrap_merged_handoff(merged):
    if merged is None:
        return None
    try:
        snap = dict(merged)
        _dims = dict(snap.get("dimensions") or {})
        _missing = list(snap.get("missing") or [])
        return _types.SimpleNamespace(
            ready=not _missing,
            b1_product_type=snap.get("item_type"),
            translated_dims=_dims,
            missing_template_keys=_missing,
            missing=_missing,
            dimensions=_dims,
            intent_mode=snap.get("intent_mode", "shop_drawing"),
            subject=str(snap.get("name") or snap.get("subject") or ""),
            item_type=snap.get("item_type"),
            views=list(snap.get("views") or []),
            output_format=snap.get("output_format") or "inline_svg_pdf",
            source_image=snap.get("source_image"),
            tool_payload=snap,
            response=str(snap.get("response") or ""),
        )
    except Exception:
        return None