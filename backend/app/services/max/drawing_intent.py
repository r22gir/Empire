"""Deterministic drawing-intent routing for MAX chat.

This keeps drawing/CAD requests out of generic LLM completion unless MAX needs
to ask for missing structured inputs first.

D3 (per REPORT-d1-drawing-workflow-research.md and the D1 Addendum):
- DrawingHandoff now carries an `intent_mode` field. Default "unknown"
  preserves backward compatibility for any caller that does not read the
  new field.
- `classify_intent_mode(text)` is a pure-Python 6-way keyword classifier
  that runs before the existing `is_drawing_intent` check.
- Priority order matters: animated_diagram → visual_explainer →
  shop_drawing → sketch_analysis → concept_image → planning_help →
  unknown. This ensures animation/explainer keywords win substring
  matches against generic "drawing" words.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


DRAWING_KEYWORDS = (
    "drawing",
    "render",
    "sketch",
    "elevation",
    "isometric",
    "section view",
    "section drawing",
    "4-view",
    "four-view",
    "pdf drawing",
    "bench drawing",
    "cad",
    # Sprint 1d Phase A Fix #2: founder re-ask keywords — so "redraw the
    # Willard bench", "regenerate as 4-view", "redo with the new dims",
    # "new version", "same version" all route to drawing-router
    # instead of silently falling through to plain chat.
    "redraw",
    "regenerate",
    "redo",
    "new version",
    "same version",
)


def clear_handoff_state() -> None:
    """Sprint 1d Phase A Fix #3: zero any module-level state.

    Called by chat_with_max at the start of every turn. Belt-and-suspenders
    for any future state-creep that would otherwise leak dims/dims-keyed
    items between turns. The structured-question flow (`handoff.missing`)
    is the proper way to ask the founder for missing data; this helper
    only ensures no stale dataclass survives across turns.
    """
    global _LAST_HANDOFF  # noqa: defined lazily below if needed
    _LAST_HANDOFF = None

# Drawing-specific multi-token "plan" phrases. Bare "plan" is intentionally NOT
# in DRAWING_KEYWORDS: it appears in phrases like "plan mode", "make a plan",
# "Telegram voice pipeline plan", and routes them all to drawing-router.
DRAWING_PLAN_PHRASES = (
    "plan view",
    "plan drawing",
    "floor plan",
    "site plan",
    "plan section",
    "plan elevation",
    "in plan",
    "in elevation",
    "elevation plan",
    "section plan",
)


# ── D3 ────────────────────────────────────────────────────────────────
# 6-way intent classification (per D1 + D1-Addendum).
#
# Priority order (CHECK IN THIS ORDER — first match wins):
#   1. animated_diagram   (animation / sequence / step / process / assembly / exploded)
#   2. planning_help      (help me plan / how to build / how to plan) — checked
#                         before visual_explainer because planning_help
#                         keywords are more specific than the generic
#                         "how to" explainer catch-all. The Founder spec
#                         explicitly requires "Help me plan how to build
#                         this" to route to planning_help.
#   3. visual_explainer   (explainer / how-to / show me how / installation diagram)
#   4. shop_drawing       (shop drawing / fabrication drawing / cut list / draw a)
#   5. sketch_analysis    (analyze this sketch / what is this / what dimensions are missing)
#   6. concept_image      (concept image / generate an image / what would this look like)
#   7. unknown            (no match)
#
# The priority order is the ONLY safe order: animation and explainer
# keywords often co-occur with "drawing" or "diagram" words, so they
# must win the substring match.
#
# Note on "how to" substring collisions:
# - "visual_explainer" has "how to" as a generic catch-all
# - "planning_help" has "how to build" / "how to plan" as more specific
# - For "Help me plan how to build this", the explainer substring "how
#   to" matches first. We add "how to build" and "how to plan" to
#   planning_help as multi-word phrases that score before "how to" via
#   a small lookahead in classify_intent_mode below.
INTENT_MODE_KEYWORDS = {
    "animated_diagram": (
        "animated",
        "animation",
        "motion",
        "sequence",
        "step by step",
        "process",
        "assembly",
        "exploded view",
        "construction sequence",
        "how it works",
        "walkthrough",
        "show the steps",
    ),
    "visual_explainer": (
        "explainer",
        "visual explanation",
        "installation diagram",
        "how-to",
        "how to",
        "show me how",
    ),
    "shop_drawing": (
        "shop drawing",
        "fabrication drawing",
        "cut list",
        "cutting diagram",
        "manufacturing drawing",
        "production drawing",
        "draw a ",
        "draw me ",
        "draw the ",
        "draw this ",
    ),
    "sketch_analysis": (
        "analyze this sketch",
        "what is this",
        "identify this",
        "what style is this",
        "what dimensions are missing",
        "what am i missing",
    ),
    "concept_image": (
        "concept image",
        "concept art",
        "make a picture",
        "generate an image",
        "show me a concept",
        "what would this look like",
    ),
    "planning_help": (
        # Order matters: more specific multi-word phrases that contain
        # "how to" come first, so they win the substring match.
        "how to build",
        "how to plan",
        "help me plan",
        "what should i measure",
        "plan the build",
        "plan this project",
    ),
}


def classify_intent_mode(text: str) -> str:
    """Classify text into one of the 7 intent modes (6 + 'unknown').

    Pure-Python substring matching. No LLM call. No I/O.

    Returns one of: animated_diagram, visual_explainer, shop_drawing,
    sketch_analysis, concept_image, planning_help, unknown.

    Algorithm:
    1. Lowercase the text.
    2. For each intent_mode in priority order (animated_diagram first),
       check if any keyword is a substring of the text.
    3. The first mode in priority order that matches wins.
    4. If no match, return "unknown".

    Examples (per Founder spec):
    "Make a shop drawing for this banquette with dimensions"
        -> shop_drawing
    "Analyze this sketch and tell me what dimensions are missing"
        -> sketch_analysis
    "Make a concept image of this bench idea"
        -> concept_image
    "Help me plan how to build this"
        -> planning_help
    "Make an animated diagram showing the cushion construction sequence"
        -> animated_diagram
    "Create a visual explainer for how this Murphy bed mechanism works"
        -> visual_explainer
    "What's the weather like today?" -> unknown
    """
    if not text:
        return "unknown"
    lowered = text.lower()
    for mode in (
        "animated_diagram",
        "planning_help",
        "visual_explainer",
        "shop_drawing",
        "sketch_analysis",
        "concept_image",
    ):
        for keyword in INTENT_MODE_KEYWORDS[mode]:
            if keyword in lowered:
                return mode
    return "unknown"

VIEW_KEYWORDS = {
    "plan": "plan",
    "isometric": "isometric",
    "elevation": "elevation",
    "section": "section",
    "front": "front_elevation",
    "side": "side_elevation",
}

ITEM_KEYWORDS = {
    "bench": "bench",
    "banquette": "bench",
    "booth": "bench",
    "chair": "chair",
    "drapery": "window",
    "curtain": "window",
    "shade": "window",
    "roman": "window",
    "cornice": "window",
    "valance": "window",
    "cabinet": "millwork",
    "nightstand": "millwork",
    "shelving": "millwork",
    "shelf": "millwork",
    "built-in": "millwork",
    "built in": "millwork",
    "table": "table",
    "desk": "table",
}

DIMENSION_ALIASES = {
    "wide": "width",
    "width": "width",
    "w": "width",
    # HOTFIX 4.0 (c) — 'long' / 'length' / 'l' map to LENGTH (the drop
    # axis for drapery/roman/valance/cornice/wall_panel AND the
    # long-edge axis for bench/banquette). The previous mapping to
    # 'width' silently overwrote the user's first 'wide' dimension
    # when they wrote "38 wide 64 long" — see _extract_dimensions
    # test_c for the live bug report. Item-type context below
    # disambiguates the bench case (where 'long' is the long-edge
    # width) by overriding 'length' -> 'width' for furniture.
    "long": "length",
    "length": "length",
    "l": "length",
    "deep": "depth",
    "depth": "depth",
    "d": "depth",
    "high": "height",
    "height": "height",
    "h": "height",
    "overall height": "height",
    "drop": "length",      # valance / cornice / roman: drop == length axis
    "seat height": "seat_height",
    "seat h": "seat_height",
    "back height": "back_height",
    "back h": "back_height",
}


@dataclass
class DrawingHandoff:
    is_drawing_intent: bool
    subject: str = ""
    item_type: str = "generic"
    dimensions: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    views: list[str] = field(default_factory=list)
    output_format: str = "inline_svg_pdf"
    source_image: str | None = None
    tool_payload: dict[str, Any] | None = None
    response: str = ""
    # D3: 6-way intent classification (per D1 + D1-Addendum).
    # Default "unknown" preserves backward compatibility for any caller
    # that does not read the new field. Valid values: animated_diagram,
    # visual_explainer, shop_drawing, sketch_analysis, concept_image,
    # planning_help, unknown.
    intent_mode: str = "unknown"

    @property
    def ready(self) -> bool:
        return self.tool_payload is not None and not self.missing


def is_drawing_intent(text: str) -> bool:
    """Returns True if text requests a drawing/rendering action.

    Negation patterns (not asking you to draw, etc.) suppress drawing intent.

    Note: "plan" is intentionally NOT a bare drawing keyword. The router
    historically routed "plan mode, propose Telegram voice pipeline" to the
    drawing handler because the word "plan" appeared anywhere in the message.
    Now the router requires a strong draw pattern (draw a X, draw me X) OR
    a drawing-specific multi-token phrase (floor plan, plan view, etc.).
    """
    if not text:
        return False
    lowered = text.lower()

    # Suppress drawing intent when user explicitly rejects drawing
    negation_patterns = (
        "not asking you to draw",
        "not asking you to render",
        "don't draw",
        "do not draw",
        "not drawing",
        "didn't draw",
        "not a drawing",
        "not render",
        "don't render",
        "i didn't ask for a drawing",
        "not asking for a drawing",
        "don't need a drawing",
        "not asking for drawing",
        "do not use drawing-router",
        "don't use drawing-router",
        "no drawing-router",
    )
    if any(neg in lowered for neg in negation_patterns):
        return False

    # Suppress drawing intent when the user is in plan mode / proposal mode.
    # These phrases describe a planning conversation, not a drawing request.
    plan_mode_patterns = (
        "plan mode",
        "propose a plan",
        "make a plan",
        "write a plan",
        "draft a plan",
        "planning the",
        "plan a ",
        "plans for ",
        "plan for ",
        "roadmap",
        "pipeline plan",
        "voice pipeline plan",
        "telegram pipeline plan",
    )
    if any(pat in lowered for pat in plan_mode_patterns):
        return False

    # Strong drawing patterns: "draw a <thing>" or "draw me"
    # These are unambiguous — user is requesting creation of something
    strong_draw_patterns = (
        "draw a ",
        "draw me ",
        "draw it ",
        "draw the ",
        "draw this ",
    )
    if any(pattern in lowered for pattern in strong_draw_patterns):
        return True

    # Drawing-specific multi-token "plan" phrases. Bare "plan" alone is NOT enough.
    if any(phrase in lowered for phrase in DRAWING_PLAN_PHRASES):
        return True

    # D3: animated / explainer phrases (per D1 Addendum). These are
    # NOT fabrication requests, but they ARE drawing-related and should
    # be routed through the drawing handoff so MAX can apply the
    # appropriate intent_mode (animated_diagram / visual_explainer).
    animation_patterns = (
        "animated diagram",
        "animated drawing",
        "animation of",
        "animation showing",
        "visual explainer",
        "visual explanation",
        "installation diagram",
        "construction sequence",
        "exploded view",
        "assembly steps",
        "how it works",
        "walkthrough",
    )
    if any(pattern in lowered for pattern in animation_patterns):
        return True

    return any(keyword in lowered for keyword in DRAWING_KEYWORDS)


def _extract_item_type(text: str) -> tuple[str, str]:
    lowered = text.lower()
    for keyword, item_type in ITEM_KEYWORDS.items():
        if keyword in lowered:
            return keyword, item_type
    return "", "generic"


def _extract_views(text: str) -> list[str]:
    lowered = text.lower()
    views = []
    if "4-view" in lowered or "four-view" in lowered:
        views.extend(["plan", "front_elevation", "side_elevation", "isometric"])
    for keyword, view in VIEW_KEYWORDS.items():
        if keyword in lowered and view not in views:
            views.append(view)
    return views or ["plan", "elevation", "isometric"]


def _normalize_dimension(label: str) -> str:
    label = label.lower().strip().replace("_", " ")
    return DIMENSION_ALIASES.get(label, label.replace(" ", "_"))


# HOTFIX 4.0 (c) — for furniture (bench / banquette / sofa / chair /
# ottoman / daybed / settee), the conventional 'long' axis is the
# FRONT EDGE (i.e. width). For every other family (drapery / roman /
# valance / cornice / wall panel / headboard), 'long'/'length' means
# the perpendicular drop or the vertical rise — distinct from 'width'.
# Per-item-type overrides re-bind 'length' -> 'width' for furniture
# so "bench 96 wide 36 high 22 deep" still routes the 'long'-side
# dimensions to width where it belongs.
_DIMENSION_OVERRIDES_BY_ITEM_TYPE: dict[str, dict[str, str]] = {
    # Furniture: long-axis = width (the LENGTH of a bench is its width).
    "bench":        {"length": "width",  "long": "width"},
    "banquette":    {"length": "width",  "long": "width"},
    "sofa":         {"length": "width",  "long": "width"},
    "chair":        {"length": "width",  "long": "width"},
    "dining_chair": {"length": "width",  "long": "width"},
    "bar_stool":    {"length": "width",  "long": "width"},
    "chaise":       {"length": "width",  "long": "width"},
    "daybed":       {"length": "width",  "long": "width"},
    "settee":       {"length": "width",  "long": "width"},
    "loveseat":     {"length": "width",  "long": "width"},
    "sectional":    {"length": "width",  "long": "width"},
}


def _apply_item_type_overrides(
    dimensions: dict[str, str], item_type: str | None
) -> dict[str, str]:
    """Re-bind long/length keys when the item_type is furniture where
    long == width. No-op when item_type is not in the override table
    (drapery, roman, valance, cornice — keep long as length)."""
    if not item_type:
        return dimensions
    overrides = _DIMENSION_OVERRIDES_BY_ITEM_TYPE.get(
        item_type.lower().strip()
    )
    if not overrides:
        return dimensions
    out = dict(dimensions)
    for src, dst in overrides.items():
        if src in out:
            val = out.pop(src)
            # Last-write-wins — preserve the founder's intent if both
            # keys are present (e.g. user wrote "96 long, 88 wide").
            out.setdefault(dst, val)
    return out


def _extract_dimensions(
    text: str, item_type: str | None = None
) -> dict[str, str]:
    """HOTFIX 4.0 — extract dimensions from natural-language input.

    Accepts:
      "38 wide 64 long"                       (value-first; no unit)
      "18in wide 24in long"                   (value-first with units)
      "width: 96, height: 36, depth: 22"      (label-first, comma-separated)
      "28 long, 22 in wide"                   (order doesn't matter)

    For furniture (bench, banquette, sofa, ...) the long / length
    dimension is the WIDTH (front-edge length). For window treatments
    (drapery, roman, valance, cornice), the long / length dimension
    is the perpendicular drop. The override map above re-binds the
    parsed keys accordingly so the founder's intent — width along the
    front edge, length along the drop, etc. — survives the parse
    step unchanged.

    Spec-Phase A precedent: never invent dim values. Missing dims
    remain missing; a downstream validator surfaces them as
    structured questions.
    """
    dimensions: dict[str, str] = {}
    # HOTFIX 4.0 (c): 'drop' is now a recognized label for valance /
    # cornice / roman. The 'seat h' / 'back h' shortforms are also
    # recognized for furniture. HOTFIX 4.0 (c) did NOT add 'drop' to
    # the value-first pattern's label alternation because some
    # phrases ('no drop specified') would false-positive — we keep
    # the label-first form as the canonical path.
    value_first = re.compile(
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>\"|in(?:ch(?:es)?)?|ft|feet|')?\s+"
        r"(?P<label>overall height|seat height|seat h|back height|back h|wide|width|long|length|deep|depth|high|height)\b",
        re.IGNORECASE,
    )
    # HOTFIX 4.0 (c): label-first pattern grew 'drop' so the natural
    # request "width: 60, drop: 48" parses correctly for roman/valance.
    label_first = re.compile(
        r"(?P<label>overall height|seat height|seat h|back height|back h|width|length|drop|depth|height)\s*[:=]?\s*"
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>\"|in(?:ch(?:es)?)?|ft|feet|')?",
        re.IGNORECASE,
    )

    for pattern in (value_first, label_first):
        for match in pattern.finditer(text):
            label = _normalize_dimension(match.group("label"))
            value = match.group("value")
            unit = (match.group("unit") or '"').lower()
            suffix = "ft" if unit in ("ft", "feet", "'") else '"'
            dimensions[label] = f"{value}{suffix}"

    dimensions = _apply_item_type_overrides(dimensions, item_type)
    return dimensions


def _has_enough_dimensions(item_type: str, dimensions: dict[str, str], source_image: str | None) -> tuple[bool, list[str]]:
    if item_type == "bench":
        missing = []
        if "width" not in dimensions:
            missing.append("width/length")
        if "depth" not in dimensions:
            missing.append("depth")
        if "height" not in dimensions and "back_height" not in dimensions:
            missing.append("overall height or back height")
        return not missing, missing
    elif item_type in {"chair", "window", "millwork", "table"}:
        required = ["width", "depth", "height"] if item_type != "window" else ["width", "height"]
    else:
        required = ["subject/item", "width", "depth/height"]
    missing = [field for field in required if field not in dimensions and field not in ("subject/item", "depth/height")]
    if item_type == "generic":
        missing = required
    elif item_type != "window" and "depth" not in dimensions and "height" not in dimensions:
        missing.append("depth or height")
    return not missing, missing


def _shape_for_text(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("u-shape", "u shape", "u_shape")):
        return "u_shape"
    if any(token in lowered for token in ("l-shape", "l shape", "l_shape")):
        return "l_shape"
    return "straight"


def build_drawing_handoff(message: str, *, image_filename: str | None = None) -> DrawingHandoff:
    if not is_drawing_intent(message):
        # Even when the message is not a drawing intent, classify it for
        # log visibility. D3: routes that the MAX router logs "intent_mode
        # = unknown" for non-drawing messages.
        return DrawingHandoff(
            is_drawing_intent=False,
            intent_mode=classify_intent_mode(message),
        )

    # D3: classify the 6-way intent mode. Runs unconditionally for any
    # message that passes is_drawing_intent, so the router can log
    # "intent_mode = shop_drawing" (etc.) on every drawing handoff.
    intent_mode = classify_intent_mode(message)

    subject, item_type = _extract_item_type(message)
    dimensions = _extract_dimensions(message)
    views = _extract_views(message)
    enough, missing = _has_enough_dimensions(item_type, dimensions, image_filename)

    handoff = DrawingHandoff(
        is_drawing_intent=True,
        subject=subject,
        item_type=item_type,
        dimensions=dimensions,
        missing=missing,
        views=views,
        source_image=image_filename,
        intent_mode=intent_mode,
    )

    if image_filename and not dimensions:
        handoff.missing = [
            "real extracted dimensions",
            "confirmed item type" if not subject else "confirmed dimensions from source image",
        ]
    elif not subject:
        handoff.missing = ["subject/item", "dimensions or source image"]
    elif not enough:
        handoff.missing = missing

    if handoff.missing:
        if image_filename:
            handoff.response = (
                "Image detected in the current request, but I still need confirmed item type "
                "and real extracted dimensions before generating a drawing."
            )
        else:
            handoff.response = (
                "I need drawing inputs before I generate anything. "
                "Missing: confirmed item type and real dimensions, or attach a source image."
            )
        return handoff

    name = subject.title() if subject else "Source Image Drawing"
    payload: dict[str, Any] = {
        "item_type": item_type,
        "name": name,
        "description": message,
        "dimensions": dimensions,
        "notes": f"Requested views: {', '.join(views)}. Do not infer missing dimensions.",
        "views": views,
        "output_format": handoff.output_format,
    }
    if item_type == "bench":
        # Sprint 1d Phase A Fix #1: NEVER invent default dims (per Standard
        # Hard Rule 1). Each of width/depth/seat_height/back_height is taken
        # from the founder's message only — if any is missing, it's added
        # to handoff.missing so the structured-question flow fires.
        # Note: `back_height` falls back to `height` ONLY when the founder
        # explicitly supplied a "height" value (e.g. "the bench is 17 tall"),
        # because users often mean seat-to-top-of-back. We still flag the
        # missing key (back_height) if neither was supplied.
        _supplied_back_height = dimensions.get("back_height")
        _supplied_height = dimensions.get("height")
        _back_height_value = (
            _supplied_back_height
            if _supplied_back_height is not None and _supplied_back_height != ""
            else (_supplied_height if _supplied_height not in (None, "") else None)
        )
        _bench_dims = {
            "shape": _shape_for_text(message),
            "width": (dimensions.get("width", "") or "").rstrip('"') or None,
            "depth": (dimensions.get("depth", "") or "").rstrip('"') or None,
            "seat_height": (dimensions.get("seat_height", "") or "").rstrip('"') or None,
            "back_height": (
                _back_height_value.rstrip('"')
                if isinstance(_back_height_value, str) and _back_height_value
                else _back_height_value
            ),
        }
        # Drop Nones so the renderer never gets placeholders.
        _bench_dims = {k: v for k, v in _bench_dims.items() if v}
        if not _bench_dims:
            handoff.missing.extend(
                ["bench dimensions (width / depth / seat_height / back_height)"]
            )
        else:
            payload.update(_bench_dims)
    if image_filename:
        payload["source_image"] = image_filename

    handoff.tool_payload = payload
    handoff.response = "Starting the drawing workflow. I will return the generated drawing artifact here."
    return handoff
