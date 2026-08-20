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
    # H57 FIX (2026-08-19): bare "drawing" removed — it matched
    # too broadly (any mention of "drawing" routed, including
    # "what is a drawing"). Multi-token phrases that contain the
    # word still match (regex matches the full phrase).
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
    # H57 FIX: "generate" + "make" verbs — cover positive fixture 5
    # ("generate the B1 sheet for the Willard bench") and
    # similar explicit generation requests.
    "generate drawing",
    "generate the",
    "make a",
    "make me",
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
    # HOTFIX 4.0b — explicit B1 product_type when detected. The
    # interceptor used to only carry a coarse bucket (window/bench/etc.)
    # which left render_spec unable to dispatch. We now carry:
    #   b1_product_type — the actual product_type from the B1
    #                     registry (e.g. 'flat_fold', 'pinch_pleat',
    #                     'headboard_channel', 'banquette'). Default
    #                     None until resolved via _try_resolve_b1_type.
    #   translated_dims  — the dimensions dict after alias translation
    #                     (length -> height for roman/drapery; length
    #                     -> drop for valance/cornice). Pre-fill keys.
    b1_product_type: str | None = None
    dimensions: dict[str, str] = field(default_factory=dict)
    translated_dims: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    # missing_template_keys: template-side required keys that the
    # translated_dims still don't cover. Surfaced to the founder as
    # the structured-question set when the handoff is NOT ready.
    missing_template_keys: list[str] = field(default_factory=list)
    views: list[str] = field(default_factory=list)
    output_format: str = "inline_svg_pdf"
    source_image: str | None = None
    tool_payload: dict[str, Any] | None = None
    response: str = ""

    @property
    def ready(self) -> bool:
        """HOTFIX 4.0b — True iff translated dims cover every
        template-required key (and the B1 product_type is known).
        Replaces the legacy 'subject + enough dims' gate; the
        interceptor used to consider itself ready with just any
        bucket item_type, which led to dead-end output."""
        return bool(self.b1_product_type and not self.missing_template_keys)
    # D3: 6-way intent classification (per D1 + D1-Addendum).
    # Default "unknown" preserves backward compatibility for any caller
    # that does not read the new field. Valid values: animated_diagram,
    # visual_explainer, shop_drawing, sketch_analysis, concept_image,
    # planning_help, unknown.
    intent_mode: str = "unknown"

    @property
    def ready(self) -> bool:
        """HOTFIX 4.0b — True iff translated dims cover every
        template-required key (and the B1 product_type is known).

        Pre-fix, `ready` was defined as:
            self.tool_payload is not None and not self.missing
        which over-read `tool_payload` (set only at the very end of
        build_drawing_handoff) and over-claimed ready=True for
        generic-bucket handoffs whose dims were incomplete. The new
        definition supersedes both: the B1 template validates the
        translated dims; tool_payload is no longer required."""
        return bool(self.b1_product_type and not self.missing_template_keys)


def is_drawing_intent(text: str) -> bool:
    """Returns True if text requests a drawing/rendering action.

    H57 FIX (2026-08-19): route on INTENT TO GENERATE, never on
    vocabulary. A message that merely MENTIONS a drawing is not a
    request for one.

    Three suppress classes (any of these returns False):
      1. Question forms ("what is", "explain", "how does", ...)
      2. Long pastes (>500 chars containing the word — likely a paste,
         not a request)
      3. Explicit user rejections + plan-mode phrases (pre-existing)

    Then a strong draw pattern OR a drawing-specific multi-token
    phrase OR a known animation phrase returns True.

    Finally a word-boundary substring match against DRAWING_KEYWORDS
    (the bare "drawing", "render", etc. — but ONLY as a whole word,
    never a substring of a longer word like "withdrawing").
    """
    if not text:
        return False
    lowered = text.lower()

    # Strip negation patterns (pre-existing). User explicitly rejects.
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

    # H57: question forms NEVER route. A user asking "what is a
    # drawing" or "explain the difference between a drawing and a
    # sketch" is asking a question, not requesting a fabrication.
    question_forms = (
        "what is",
        "what's",
        "whats",
        "what does",
        "explain",
        "tell me about",
        "how does",
        "how do",
        "why ",
        "why?",
        "define ",
        "meaning of",
        "describe ",
        "difference between",
    )
    # Only treat as a question when the question form is the LEADING
    # intent — not when "what" appears mid-sentence in a fabrication
    # request. We accept a trailing "?" as a strong question signal.
    if lowered.endswith("?"):
        if any(qf in lowered for qf in question_forms):
            return False
    if any(lowered.startswith(qf) for qf in question_forms):
        return False

    # H57: long pastes (body > 500 chars) NEVER route. A 200-line
    # dispatch paste containing "drapery" or "drawing" is a
    # document being submitted for review, not a generation prompt.
    # Cap at 500 chars per the dispatch's threshold.
    if len(text) > 500 and any(kw in lowered for kw in DRAWING_KEYWORDS):
        return False

    # Pre-existing: plan mode / proposal mode (separate intent)
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

    # H57 FIX: explicit drawing request with item-type + dims.
    # A message that names an item (shade, bench, valance, etc.) AND
    # specifies dimensions (width 38, drop 70, 68 high, etc.) is a
    # fabrication request even without the verb "draw" — per
    # dispatch fixture 6 ("Roman shade, width 68, drop 70").
    if any(item in lowered for item in _ITEM_TYPE_KEYWORDS_LOWER):
        # Look for dimension-like text — at least one digit followed
        # by a unit, OR an explicit width/drop/high keyword.
        if _DIM_LIKE.search(text):
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

    # H57 FIX: word-boundary substring match. Pre-fix used
    # `keyword in lowered` which matched "drawing" inside
    # "withdrawing", "redrawing", "drawings", etc. Post-fix uses a
    # regex with word boundaries (\b). The pattern is case-insensitive
    # and matches Unicode word characters on either side.
    import re as _re
    for keyword in DRAWING_KEYWORDS:
        # \b in re treats _ as a word character; keywords with
        # embedded spaces (e.g. "section view") match whole phrase.
        # The match is whole-word (not substring of a longer word).
        if _re.search(r"(?<![A-Za-z0-9])" + _re.escape(keyword) + r"(?![A-Za-z0-9])",
                      lowered):
            return True
    return False


# H57 FIX: helper constants for the "item + dims" intent check
# (positive fixture 6: "Roman shade, width 68, drop 70").
# Lower-cased once at module load for fast matching.
_ITEM_TYPE_KEYWORDS_LOWER = tuple(
    kw.lower() for kw in (
        "bench", "banquette", "booth", "chair", "drapery", "curtain",
        "shade", "roman", "cornice", "valance", "headboard",
    )
)
# Matches dimension-like text: a number with a unit (e.g. "68\"", "70 in",
# "38cm") or an explicit width/drop/high keyword with a number.
import re as _re_module
_DIM_LIKE = _re_module.compile(
    r"(?:\b\d+\s*(?:[\"'\u2033]\b|in\b|cm\b|mm\b|ft\b|inch\b|"
    r"inches\b|wide\b|tall\b|high\b|drop\b))"
    r"|(?:width\s*\d|drop\s*\d|height\s*\d|high\s*\d|long\s*\d)",
    _re_module.IGNORECASE,
)


def _extract_item_type(text: str) -> tuple[str, str]:
    """HOTFIX 4.0b (b) — fix the silent 'generic' bug from R3.

    Pre-fix, this returned ('shade', 'window') for "flat roman shade"
    (substring match) and ('', 'generic') for the explicit
    "use the render_shop_drawing tool: product_type flat_fold, dims
    width 38 height 64" prompt (no substring keyword). The
    'generic' bucket then surfaced a misleading missing-field list.

    Post-fix:
      1. Detect an explicit "product_type <name>" mention FIRST and
         return that B1 product_type as both subject AND item_type
         (the router will later call render_shop_drawing with it).
      2. Otherwise, fall back to the substring keyword table. The
         match with the longest keyword wins so "flat roman shade"
         doesn't accidentally collapse to "roman" → a higher-specificity
         hint should win. (Today we keep the first-match behavior
         because the B1 type resolution happens separately in
         _try_resolve_b1_type.)
    """
    lowered = text.lower()

    # Path 1: explicit B1 product_type mention. The router's
    # _try_resolve_b1_type picks up the same patterns; we just surface
    # the b1 type as the subject here so the user-visible handoff
    # carries an explicit name (no more "generic").
    for pattern, b1_type in _EXPLICIT_B1_TYPE_PATTERNS:
        if pattern in lowered and b1_type is not None:
            return b1_type, b1_type

    # Path 2: substring match against ITEM_KEYWORDS.
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


# ── HOTFIX 4.0b (a) — router-to-engine wiring helpers ────────────────

# Map (item_type, free-text style hint) → B1 product_type. The chat
# most commonly names the style without using the precise registry
# name ("flat roman shade" instead of "flat_fold"). Each entry is a
# (style-hint-substring, B1 product_type). First match wins.
_B1_TYPE_BY_STYLE_HINT = (
    # ── Drapery (15 styles) — natural-language aliases ────────────
    ("pinch pleat",       "pinch_pleat"),
    ("french pleat",      "french_pleat"),
    ("euro pleat",        "euro_pleat"),
    ("cartridge pleat",   "cartridge_pleat"),
    ("box pleat",         "box_pleat"),
    ("inverted box",      "inverted_box_pleat"),
    ("goblet pleat",      "goblet_pleat"),
    ("butterfly pleat",   "butterfly_pleat"),
    ("ripplefold",        "ripplefold"),
    ("rod pocket",        "rod_pocket"),
    ("tab top",           "tab_top"),
    ("grommet",           "grommet"),
    ("pencil pleat",      "pencil_pleat"),
    ("smocked",           "smocked"),
    ("fan pleat",         "fan_pleat"),
    # ── Roman shades (9 styles) ─────────────────────────────────
    ("flat roman",        "flat_fold"),
    ("hobbled",           "hobbled_teardrop"),
    ("hobbled teardrop",  "hobbled_teardrop"),
    ("european relaxed",  "european_relaxed"),
    ("balloon",           "balloon"),
    ("austrian",          "austrian"),
    ("london",            "london"),
    ("cascade",           "cascade"),
    ("waterfall",         "waterfall"),
    ("tulip",             "tulip"),
    # generic "roman shade" without "flat" → flat_fold (the most common)
    ("roman shade",       "flat_fold"),
    ("roman",             "flat_fold"),
    # ── Valance (14 styles) ────────────────────────────────────
    ("kingston",          "kingston"),
    ("cambridge",         "cambridge"),
    ("scalloped",         "scalloped"),
    ("arched",            "arched"),
    ("serpentine",        "serpentine"),
    ("flat board mounted","flat_board_mounted"),
    ("flat_board_mounted","flat_board_mounted"),
    ("shaped",            "shaped"),
    ("pleated valance",   "pleated"),
    ("pleated",           "pleated"),
    ("gathered",          "gathered"),
    ("swag and jabot",    "swag_and_jabot"),
    ("swag_and_jabot",    "swag_and_jabot"),
    ("jabot",             "swag_and_jabot"),
    ("cascades",          "cascades"),
    ("empire valance",    "empire"),
    ("empire",            "empire"),
    ("tab valance",       "tab"),
    ("cornice with fabric","cornice_with_fabric"),
    ("cornice_with_fabric","cornice_with_fabric"),
    ("valance",           "kingston"),   # generic fallback
    # ── Cornice (5 styles) ─────────────────────────────────────
    ("straight cornice",  "straight"),
    ("cornice straight",  "straight"),
    ("double serpentine", "double_serpentine"),
    ("pagoda",            "pagoda"),
    ("stepped",           "stepped"),
    ("custom profile",    "custom_profile"),
    ("cornice",           "straight"),
    # ── Bench / Banquette (treated as furniture long-axis = width) ──
    ("banquette",         "banquette"),
    ("bench",             "bench"),
    # ── Headboard ─────────────────────────────────────────────
    ("headboard channel", "headboard_channel"),
    ("channel headboard", "headboard_channel"),
    ("upholstered headboard", "headboard_channel"),
    ("headboard",         "headboard_channel"),
)

# Explicit "use the X tool: product_type Y, dims ..." patterns. The
# R3 reproduction showed the interceptor ignoring explicit B1 type
# mentions — this list catches them.
_EXPLICIT_B1_TYPE_PATTERNS = (
    ("render_shop_drawing tool", None),  # presence-only signal
    ("product_type flat_fold", "flat_fold"),
    ("product_type pinch_pleat", "pinch_pleat"),
    ("product_type flat_roman", "flat_fold"),
    ("product_type roman", "flat_fold"),
    ("product_type headboard_channel", "headboard_channel"),
    ("product_type banquette", "banquette"),
    ("product_type bench", "bench"),
    ("product_type double_serpentine", "double_serpentine"),
    ("product_type scalloped", "scalloped"),
)


def _try_resolve_b1_type(message: str, item_type: str) -> str | None:
    """HOTFIX 4.0b — resolve a B1 product_type from the message text.

    Two paths:
      1. Explicit "product_type <name>" patterns (R3 reproduction case)
      2. Style-hint substring mapping ("flat roman shade" -> flat_fold)

    Returns None when no B1 product_type can be resolved — the
    handoff is then NOT ready (template-ready gate requires a B1
    type) and the founder is asked for a precise B1 type.
    """
    lowered = message.lower()
    # Path 1: explicit "product_type <name>" mentions.
    for pattern, b1_type in _EXPLICIT_B1_TYPE_PATTERNS:
        if pattern in lowered and b1_type is not None:
            return b1_type
    # Path 2: style-hint substring mapping. Longer hints win over
    # shorter so "flat roman shade" beats "roman".
    best_hit: tuple[int, str] | None = None
    for hint, b1_type in _B1_TYPE_BY_STYLE_HINT:
        if hint in lowered:
            if best_hit is None or len(hint) > best_hit[0]:
                best_hit = (len(hint), b1_type)
    return best_hit[1] if best_hit else None


def _translate_dims_for_b1_product(
    dimensions: dict[str, str], b1_product_type: str | None,
) -> dict[str, str]:
    """HOTFIX 4.0b — alias-translate the parsed dims to the
    template-required keys.

    The user-parser stays surface-level (it captures 'length' for
    'long'/'long' etc.). The translation layer maps the user's
    intent onto the B1 template's required-dim keys:

      length -> height   for roman shades, drapery, headboard
      length -> drop     for valance, cornice
      length stays length after furniture override (the parser
                            already re-mapped furniture's 'long' to
                            'width' so by the time we get here, the
                            remaining keys are usually width/height/
                            depth/...).
    """
    out = dict(dimensions)
    if not b1_product_type:
        return out
    # Family is "Roman Shades", "Drapery", etc. — normalize to a
    # spaces-removed lowercase key so we can match against compact
    # sets without whitespace surprises.
    family = b1_product_type_to_family(b1_product_type).replace(" ", "").lower()

    # Window-treatments (roman shades + drapery + headboard_channel):
    # the user-written "length" or "long" is actually the height axis.
    roman_family = {"romanshades", "drapery", "channelheadboard"}
    valance_family = {"valance"}
    cornice_family = {"cornice"}

    if family in roman_family:
        if "length" in out and "height" not in out:
            out["height"] = out.pop("length")
    elif family in valance_family or family in cornice_family:
        if "length" in out and "drop" not in out:
            out["drop"] = out.pop("length")
    return out


def b1_product_type_to_family(b1_product_type: str) -> str:
    """Map B1 product_type to its family name. Centralized so the
    router and the drawing_intent module agree on which translation
    rule applies."""
    try:
        from app.services.drawing.templates.registry import family_for
        return family_for(b1_product_type) or ""
    except Exception:
        return ""


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
        r"(?P<label>overall height|seat height|seat h|back height|back h|wide|width|long|length|deep|depth|high|height|drop)\b",
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


def _compute_missing_template_keys(
    translated_dims: dict[str, str], b1_product_type: str | None,
) -> list[str]:
    """HOTFIX 4.0b — compute the template-required keys that the
    translated dims still don't cover. Calls templates.registry.
    get_template(b1_product_type).validate_spec({dims}) — that
    function is the canonical source of "what's missing for THIS
    family" and is the same gate the render_shop_drawing tool runs
    before invoking render_spec.

    Returns an empty list when the translated dims satisfy the
    template (handoff.ready). Imports the registry lazily to avoid
    import-time cycles (the templates module imports back into
    the data dir lazily via product_catalog).
    """
    if not b1_product_type:
        return ["b1_product_type"]
    try:
        from app.services.drawing.templates import get_template
        template = get_template(b1_product_type)
    except KeyError:
        # B1 product_type not in the B1 registry — surface it as the
        # missing key so the founder can pick a real one.
        return ["b1_product_type"]
    except Exception:
        return ["b1_product_type"]

    missing = template.validate_spec({
        "product_type": b1_product_type,
        "dims": translated_dims,
    }).missing_required
    return list(missing)


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
    dimensions = _extract_dimensions(message, item_type=item_type)
    views = _extract_views(message)

    # HOTFIX 4.0b — resolve B1 product_type, alias-translate dims,
    # and validate the translated set against the template's required
    # keys. Pre-fix, the handoff was "ready" with just enough
    # generic-bucket dims to pass _has_enough_dimensions; that
    # resulted in a dead-end response. Post-fix the ready gate is the
    # template's REQUIRED set covered by translated dims AND a known
    # B1 product_type.
    b1_product_type = _try_resolve_b1_type(message, item_type)
    translated_dims = _translate_dims_for_b1_product(
        dimensions, b1_product_type
    )
    missing_template_keys = _compute_missing_template_keys(
        translated_dims, b1_product_type
    )

    # legacy fields kept populated so the existing router code path
    # still gets something to look at during the migration window.
    enough, missing_legacy = _has_enough_dimensions(
        item_type, translated_dims, image_filename
    )
    handoff = DrawingHandoff(
        is_drawing_intent=True,
        subject=subject,
        item_type=item_type,
        b1_product_type=b1_product_type,
        dimensions=dimensions,
        translated_dims=translated_dims,
        missing=missing_legacy,
        missing_template_keys=missing_template_keys,
        views=views,
        source_image=image_filename,
        intent_mode=intent_mode,
    )

    # Migration: while the router is being updated for HOTFIX 4.0b,
    # surface BOTH the legacy missing list AND the template-key gap so
    # any callers reading either field still get a useful answer.
    #
    # HOTFIX 4.0b priority order:
    #   1. If b1_product_type resolved AND missing_template_keys
    #      non-empty: ONLY surface the template's missing keys (those
    #      are the truth). Drop the legacy bucket — it would be
    #      misleading (e.g. asking for "height" when the valance
    #      template wants "drop").
    #   2. If b1_product_type resolved and template is satisfied:
    #      ready=True, no missing.
    #   3. Else, fall back to the legacy gate (image / subject /
    #      enough).
    if b1_product_type and missing_template_keys:
        handoff.missing_template_keys = missing_template_keys
        handoff.missing = missing_template_keys
    elif image_filename and not dimensions:
        handoff.missing = [
            "real extracted dimensions",
            "confirmed item type" if not subject else "confirmed dimensions from source image",
        ]
    elif b1_product_type:
        # B1 product_type resolved and template satisfied — ready.
        # No missing.
        pass
    elif not subject:
        handoff.missing = ["subject/item", "dimensions or source image"]
    elif not enough:
        handoff.missing = missing_legacy

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
