"""Bench quote → diagram params.

One policy for the quote-diagram path (POST /drawings/bench, Max
sketch_to_drawing, CraftForge furniture/bench). The sheet transmits the
quoted idea: category + parametric dims. It is not shop-final art.

Length
    Inches-first. A bare number is inches. Feet only when the caller
    sets length_unit/unit to ft (or the text itself says ft / feet / ').
    The old rule "≤40 means feet" is retired — a 36" bench stayed 36",
    it does not become 432".
    Exception: Max sketch_to_drawing's documented `lf` field is linear
    feet unless that call also sets unit/length_unit to inches.

Back height
    Quote-supplied BH wins on every caller.
    When BH is omitted and the bench has a back, every caller uses
    BENCH_BACK_HEIGHT_DEFAULT_IN (18). The sheet marks that line
    ASSUMED — CONFIRM BEFORE FABRICATION.
    The old Max sketch default of 34 is retired so it cannot disagree
    with the API.

Panel
    Explicit panel_style is never rewritten. `flat` stays flat.
    `has_back` false (or no_back / backless) draws no back.
    Omitted API panel_style stays flat. Omitted Max sketch panel_style
    stays vertical_channels (documented tool schema) — that is an
    omission default, not a rewrite of an explicit flat.

Chrome
    business_unit woodcraft / craftforge uses WoodCraft letterhead.
    Workroom letterhead is not stamped on those sheets.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.drawing.inches import format_inches

# Single omitted-BH fallback. Quote value always wins over this.
BENCH_BACK_HEIGHT_DEFAULT_IN = 18.0

ASSUMED_MARK = "ASSUMED — CONFIRM BEFORE FABRICATION"

_FT_UNITS = {"ft", "feet", "foot", "lf", "'"}
_NONE_PANELS = {"none", "no_back", "backless", "open", "no-back"}
_PANEL_ALIASES = {
    "channel": "vertical_channels",
    "channeled": "vertical_channels",
    "channels": "vertical_channels",
    "vertical": "vertical_channels",
    "vertical_channel": "vertical_channels",
    "vertical_channels": "vertical_channels",
    "horizontal": "horizontal_channels",
    "horizontal_channel": "horizontal_channels",
    "horizontal_channels": "horizontal_channels",
    "h_channel": "horizontal_channels",
    "tufted": "tufted",
    "button": "button_tufted",
    "button_tufted": "button_tufted",
    "plain": "flat",
    "flat": "flat",
    "flat_back": "flat",
    "none": "none",
    "no_back": "none",
    "backless": "none",
}

_WC_UNITS = {
    "wc", "woodcraft", "wood_craft", "craftforge", "craft_forge", "cf",
    "empire_woodcraft", "empire-woodcraft",
}
_WR_UNITS = {
    "wr", "workroom", "empire_workroom", "empire-workroom", "empire workroom",
}

WORKROOM_CHROME = {
    "company": "EMPIRE WORKROOM",
    "tagline": "CUSTOM UPHOLSTERY & FABRICATION",
    "address": "5124 Frolich Ln, Hyattsville, MD 20781",
    "contact": "(703) 213-6484 | workroom@empirebox.store",
    "drawn_by": "MAX AI / Empire Workroom",
    "module": "WR",
}

WOODCRAFT_CHROME = {
    "company": "WOODCRAFT BY EMPIRE",
    "tagline": "CUSTOM WOODWORK",
    "address": "5124 Frolich Ln, Hyattsville, MD 20781",
    "contact": "MODULE · WOODCRAFT",
    "drawn_by": "MAX AI / WoodCraft",
    "module": "WC",
}

_BENCH_WORDS = ("bench", "banquette", "booth", "window seat", "window_seat")


def normalize_length_unit(unit: Optional[str]) -> str:
    u = (unit or "in").strip().lower().replace("inches", "in").replace("inch", "in")
    if u in _FT_UNITS or u.startswith("ft"):
        return "ft"
    return "in"


def length_to_inches(value: Any, unit: Optional[str] = "in") -> float:
    """Convert one numeric length. Inches unless unit is feet.

    Does not apply the retired ≤40-as-feet heuristic.
    """
    if value is None or value == "":
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return length_to_inches_from_text(value, default=0.0)
    if number <= 0:
        return 0.0
    if normalize_length_unit(unit) == "ft":
        return number * 12.0
    return number


def length_to_inches_from_text(raw: Any, default: float = 0.0) -> float:
    """Parse a dimension string. Bare numbers and inch marks are inches.

    Foot marks (`'`, ft, feet, foot, lf) convert. A trailing inch mark
    never converts.
    """
    if raw is None:
        return default
    s = str(raw).strip().lower().replace("(est)", "").strip()
    if not s:
        return default
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if not match:
        return default
    number = float(match.group(1))
    if number <= 0:
        return default
    # Inch mark wins over a stray foot word ("36\" " is inches).
    if '"' in s or "in" in s and "ft" not in s and "feet" not in s and not s.endswith("'"):
        if re.search(r"\d\s*(?:\"|in\b|inch)", s) and not re.search(r"\d\s*(?:'|ft\b|feet|foot)", s):
            return number
    if (
        s.endswith("'")
        or s.endswith("lf")
        or re.search(r"\d\s*(?:'|ft\b|feet|foot|lf\b)", s)
    ):
        return number * 12.0
    return number


def resolve_back_height(explicit: Any) -> tuple[float, bool]:
    """Return (inches, assumed).

    A provided number is the quote value (not assumed).
    None / blank uses the single shared default and is assumed.
    """
    if explicit is None or explicit == "":
        return BENCH_BACK_HEIGHT_DEFAULT_IN, True
    try:
        return float(explicit), False
    except (TypeError, ValueError):
        parsed = length_to_inches_from_text(explicit, default=0.0)
        if parsed <= 0:
            return BENCH_BACK_HEIGHT_DEFAULT_IN, True
        return parsed, False


def normalize_panel_style(style: Optional[str], *, default: str = "flat") -> str:
    """Normalize a panel name. Never rewrite flat into channeled."""
    if style is None or str(style).strip() == "":
        return default
    key = str(style).strip().lower().replace("-", "_").replace(" ", "_")
    if key in _NONE_PANELS:
        return "none"
    return _PANEL_ALIASES.get(key, key)


def resolve_has_back(has_back: Optional[bool], panel_style: str) -> bool:
    if has_back is not None:
        return bool(has_back)
    return normalize_panel_style(panel_style, default="flat") != "none"


def is_woodcraft_unit(business_unit: Optional[str]) -> bool:
    key = (business_unit or "").strip().lower().replace(" ", "_")
    return key in _WC_UNITS


def canonical_business_unit(business_unit: Optional[str]) -> str:
    key = (business_unit or "").strip().lower().replace(" ", "_")
    if key in _WC_UNITS:
        return "woodcraft"
    if key in _WR_UNITS or not key:
        return "workroom"
    return key


def sheet_chrome(business_unit: Optional[str]) -> dict:
    if is_woodcraft_unit(business_unit):
        return dict(WOODCRAFT_CHROME)
    return dict(WORKROOM_CHROME)


def _back_chip(panel_style: str, has_back: bool) -> str:
    if not has_back or panel_style == "none":
        return "NO BACK"
    labels = {
        "vertical_channels": "CHANNELED",
        "horizontal_channels": "H-CHANNELED",
        "tufted": "TUFTED",
        "button_tufted": "TUFTED",
        "flat": "FLAT",
    }
    return labels.get(panel_style, panel_style.replace("_", " ").upper() or "FLAT")


def product_label(bench_type: str = "", product_type: str = "", name: str = "") -> str:
    blob = f"{product_type} {name}".lower().replace("-", " ").replace("_", " ")
    bt = (bench_type or "").lower().replace("-", "_")
    if "banquette" in blob:
        return "BANQUETTE"
    if bt in ("u", "u_shape") or "u shape" in blob or "u_shape" in blob or "booth" in blob:
        return "U-BOOTH"
    if bt in ("l", "l_shape") or "l shape" in blob or "l_shape" in blob:
        return "L-BENCH"
    if "freestanding" in blob or "straight" in blob or not blob.strip():
        return "FREESTANDING BENCH"
    if "bench" in blob:
        return "FREESTANDING BENCH"
    return "FREESTANDING BENCH"


def category_chip(
    *,
    business_unit: str = "",
    bench_type: str = "straight",
    product_type: str = "",
    name: str = "",
    panel_style: str = "flat",
    has_back: bool = True,
) -> str:
    """First-class category line, e.g. `WC · FREESTANDING BENCH · CHANNELED`."""
    module = sheet_chrome(business_unit)["module"]
    product = product_label(bench_type, product_type, name)
    back = _back_chip(panel_style, has_back)
    return f"{module} · {product} · {back}"


def back_style_label(panel_style: str, has_back: bool = True) -> str:
    if not has_back or panel_style == "none":
        return "NO BACK"
    labels = {
        "vertical_channels": "CHANNELED BACK",
        "horizontal_channels": "H-CHANNELED BACK",
        "tufted": "TUFTED BACK",
        "button_tufted": "BUTTON TUFTED BACK",
        "flat": "FLAT BACK",
    }
    return labels.get(panel_style, panel_style.replace("_", " ").upper())


@dataclass
class ResolvedBench:
    width_in: float
    long_in: float
    short_in: float
    back_run_in: float
    side_in: float
    seat_depth: float
    seat_height: float
    back_height: float
    back_height_assumed: bool
    panel_style: str
    has_back: bool
    cushion_width: float
    channel_count: int
    business_unit: str
    product_type: str
    category_chip: str
    chrome: dict
    assumptions: list[str] = field(default_factory=list)
    bench_type: str = "straight"
    name: str = "Bench"
    quote_num: str = ""

    def public_dict(self) -> dict:
        return {
            "width_in": self.width_in,
            "long_in": self.long_in,
            "short_in": self.short_in,
            "back_run_in": self.back_run_in,
            "side_in": self.side_in,
            "seat_depth": self.seat_depth,
            "seat_height": self.seat_height,
            "back_height": self.back_height,
            "back_height_assumed": self.back_height_assumed,
            "panel_style": self.panel_style,
            "has_back": self.has_back,
            "cushion_width": self.cushion_width,
            "channel_count": self.channel_count,
            "business_unit": self.business_unit,
            "product_type": self.product_type,
            "category_chip": self.category_chip,
            "assumptions": list(self.assumptions),
            "bench_type": self.bench_type,
        }


def resolve_bench_request(req: Any) -> ResolvedBench:
    """Resolve a BenchRequest (or any object with the same fields)."""
    unit = getattr(req, "unit", None) or getattr(req, "length_unit", None) or "in"
    width_override = getattr(req, "width_in", None)
    if width_override is not None and float(width_override) > 0:
        width = float(width_override)
    else:
        width = length_to_inches(getattr(req, "lf", 0) or 0, unit)

    long_in = length_to_inches(getattr(req, "leg1_length", 0) or 0, unit)
    short_in = length_to_inches(getattr(req, "leg2_length", 0) or 0, unit)
    back_run = length_to_inches(getattr(req, "back_length", 0) or 0, unit)
    side_in = length_to_inches(getattr(req, "left_depth", 0) or 0, unit)

    panel = normalize_panel_style(getattr(req, "panel_style", None), default="flat")
    has_back = resolve_has_back(getattr(req, "has_back", None), panel)
    if not has_back:
        panel_for_chip = "none"
        back_height, assumed = 0.0, False
    else:
        panel_for_chip = panel
        back_height, assumed = resolve_back_height(getattr(req, "back_height", None))

    business = canonical_business_unit(getattr(req, "business_unit", "") or "")
    product = getattr(req, "product_type", "") or ""
    name = getattr(req, "name", "") or "Bench"
    bench_type = getattr(req, "bench_type", "") or "straight"
    chip = category_chip(
        business_unit=business,
        bench_type=bench_type,
        product_type=product,
        name=name,
        panel_style=panel if has_back else "none",
        has_back=has_back,
    )
    assumptions: list[str] = []
    note = (getattr(req, "diagram_note", "") or "").strip()
    if note:
        assumptions.append(note)
    if assumed and has_back:
        assumptions.append(
            f'back height {format_inches(back_height)} {ASSUMED_MARK}'
        )

    cushion = getattr(req, "cushion_width", None)
    cushion_width = float(cushion) if cushion else 24.0
    channels = getattr(req, "channel_count", None)
    channel_count = int(channels) if channels else 6

    return ResolvedBench(
        width_in=width,
        long_in=long_in,
        short_in=short_in,
        back_run_in=back_run,
        side_in=side_in,
        seat_depth=float(getattr(req, "seat_depth", 20) or 20),
        seat_height=float(getattr(req, "seat_height", 18) or 18),
        back_height=back_height,
        back_height_assumed=assumed,
        panel_style=panel if has_back else "none",
        has_back=has_back,
        cushion_width=cushion_width,
        channel_count=channel_count,
        business_unit=business,
        product_type=product,
        category_chip=chip,
        chrome=sheet_chrome(business),
        assumptions=assumptions,
        bench_type=bench_type,
        name=name,
        quote_num=getattr(req, "quote_num", "") or "",
    )


def resolve_sketch_bench(params: Optional[dict], *, default_panel: str = "vertical_channels") -> dict:
    """Max sketch_to_drawing bench params → the same resolved idea.

    `lf` / `length_ft` stay linear feet (documented tool field) unless
    unit/length_unit is inches. `width` / `width_in` and dimension
    strings are inches-first. Omitted back_height uses the shared 18"
    default, not 34.
    """
    params = params or {}
    dims = params.get("dimensions") or {}
    unit = params.get("length_unit") or params.get("unit")

    width = None
    if isinstance(dims, dict):
        for key, raw in dims.items():
            lk = str(key).lower()
            if "width" in lk or lk in ("length", "w", "l"):
                width = length_to_inches_from_text(raw, default=0.0)
                break
    if not width:
        if params.get("width_in") not in (None, ""):
            width = length_to_inches(params.get("width_in"), unit or "in")
        elif params.get("width") not in (None, ""):
            width = length_to_inches(params.get("width"), unit or "in")
        elif params.get("lf") not in (None, "") or params.get("length_ft") not in (None, ""):
            lf_unit = unit or "ft"
            width = length_to_inches(params.get("lf", params.get("length_ft")), lf_unit)
        else:
            width = length_to_inches(10, "ft")

    seat_depth = _first_number(params.get("seat_depth"), params.get("depth"), default=18.0)
    seat_height = _first_number(params.get("seat_height"), default=18.0)
    explicit_bh = params.get("back_height", None)
    if explicit_bh in ("", None) and isinstance(dims, dict):
        explicit_bh = None
        for key, raw in dims.items():
            lk = str(key).lower()
            if "seat" in lk and "height" in lk:
                seat_height = length_to_inches_from_text(raw, default=seat_height)
            elif "depth" in lk or "seat_d" in lk:
                seat_depth = length_to_inches_from_text(raw, default=seat_depth)
            elif "back" in lk:
                explicit_bh = length_to_inches_from_text(raw, default=0.0) or None
            elif "width" in lk or lk in ("length",):
                parsed = length_to_inches_from_text(raw, default=0.0)
                if parsed:
                    width = parsed
    elif isinstance(dims, dict):
        for key, raw in dims.items():
            lk = str(key).lower()
            if "seat" in lk and "height" in lk:
                seat_height = length_to_inches_from_text(raw, default=seat_height)
            elif "depth" in lk or "seat_d" in lk:
                seat_depth = length_to_inches_from_text(raw, default=seat_depth)
            elif "back" in lk:
                explicit_bh = length_to_inches_from_text(raw, default=0.0)

    panel = normalize_panel_style(params.get("panel_style"), default=default_panel)
    has_back = resolve_has_back(params.get("has_back"), panel)
    if not has_back:
        back_height, assumed = 0.0, False
        panel_out = "none"
    else:
        back_height, assumed = resolve_back_height(explicit_bh)
        panel_out = panel

    business = canonical_business_unit(
        params.get("business_unit") or params.get("business") or ""
    )
    product = params.get("product_type") or ""
    name = params.get("name") or ""
    shape = (params.get("shape") or params.get("bench_type") or "straight").lower()
    chip = category_chip(
        business_unit=business,
        bench_type=shape,
        product_type=product,
        name=name,
        panel_style=panel_out,
        has_back=has_back,
    )
    assumptions = []
    if assumed and has_back:
        assumptions.append(f'back height {format_inches(back_height)} {ASSUMED_MARK}')

    cushion = params.get("cushion_width", 24)
    channels = params.get("channel_count", 6)
    return {
        "width_in": width,
        "seat_depth": seat_depth,
        "seat_height": seat_height,
        "back_height": back_height,
        "back_height_assumed": assumed,
        "panel_style": panel_out,
        "has_back": has_back,
        "cushion_width": float(cushion or 24),
        "channel_count": int(channels or 6),
        "business_unit": business,
        "product_type": product,
        "category_chip": chip,
        "chrome": sheet_chrome(business),
        "assumptions": assumptions,
        "shape": shape,
        "client": params.get("client") or "",
        "project": params.get("project") or "",
        "quote_num": params.get("quote_num") or "",
    }


def _first_number(*values, default: float) -> float:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            parsed = length_to_inches_from_text(value, default=0.0)
            if parsed:
                return parsed
    return default


@dataclass
class DiagramMap:
    """Category-first map from a quote/design record to diagram params."""

    connected: bool
    category: str
    reason: str
    params: dict = field(default_factory=dict)
    category_chip: str = ""

    def as_dict(self) -> dict:
        return {
            "connected": self.connected,
            "category": self.category,
            "reason": self.reason,
            "params": dict(self.params),
            "category_chip": self.category_chip,
        }


def _design_text(design: dict) -> str:
    parts = [
        design.get("name") or "",
        design.get("description") or "",
        design.get("notes") or "",
        design.get("style") or "",
        design.get("product_type") or "",
        design.get("catalog_id") or "",
    ]
    for item in design.get("line_items") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("description") or ""))
        else:
            parts.append(str(item))
    return " \n ".join(parts)


def _dim_bag(design: dict) -> dict:
    """Flatten DesignCreate fields and a nested dimensions object."""
    bag = {}
    nested = design.get("dimensions") or {}
    if isinstance(nested, dict):
        bag.update(nested)
    for key in (
        "width", "height", "depth", "unit", "width_in", "depth_in", "height_in",
        "seat_height", "seat_depth", "back_height", "panel_style", "has_back",
        "cushion_width", "channel_count", "bench_type", "product_type",
    ):
        if design.get(key) not in (None, ""):
            bag[key] = design.get(key)
    return bag


def _prose_number(text: str, patterns: list[str]) -> Optional[float]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return float(match.group(1))
    return None


def _is_bench_design(design: dict, text: str) -> bool:
    cat = (design.get("category") or "").strip().lower()
    blob = text.lower()
    if cat in ("bench", "banquette"):
        return True
    product = f"{design.get('product_type') or ''} {design.get('catalog_id') or ''}".lower()
    if "bench" in product or "banquette" in product:
        return True
    if cat == "furniture" and any(word in blob for word in _BENCH_WORDS):
        return True
    return False


def _infer_panel_from_text(text: str) -> str:
    t = text.lower()
    if "horizontal channel" in t or "h-channel" in t:
        return "horizontal_channels"
    if any(word in t for word in ("vertical channel", "channeled", "channel back", "channels")):
        return "vertical_channels"
    if "tuft" in t:
        return "tufted"
    if any(word in t for word in ("flat back", "plain back", "flat panel")):
        return "flat"
    return "flat"


def _infer_has_back(text: str, explicit: Any, back_height_present: bool) -> tuple[bool, str]:
    if explicit is not None and explicit != "":
        return bool(explicit), ""
    t = text.lower()
    if any(phrase in t for phrase in ("no back", "backless", "without a back", "without back")):
        return False, ""
    if "optional back" in t and not back_height_present:
        return False, "OPTIONAL BACK MENTIONED — NOT INCLUDED ON THIS DIAGRAM"
    if back_height_present:
        return True, ""
    if any(phrase in t for phrase in ("with back", "back rail", "back panel", "channeled back")):
        return True, ""
    # CF furniture stores W/D/H only. Do not invent a back the quote
    # never named.
    return False, ""


def map_craftforge_design(design: Optional[dict]) -> DiagramMap:
    """Best-effort CraftForge design → bench diagram params.

    Furniture/bench lines connect into the same BenchRequest the drawing
    API renders. Other CF categories (cornice, cabinet-door, sign, …)
    stay unconnected instead of being drawn as a bench.
    """
    design = design or {}
    category = (design.get("category") or "").strip().lower()
    text = _design_text(design)
    if not _is_bench_design(design, text):
        return DiagramMap(
            connected=False,
            category=category or "unknown",
            reason=(
                f"category {category or 'unknown'!r} is not a bench/banquette line; "
                "diagram stays on that category's own path"
            ),
        )

    bag = _dim_bag(design)
    unit = bag.get("unit") or design.get("unit") or "in"

    def _stored_inches(primary_key: str, fallback_key: str, prose_patterns: list[str]) -> float:
        """Structured fields honor `unit`. Prose numbers are already inches."""
        if bag.get(primary_key) not in (None, ""):
            return length_to_inches(bag.get(primary_key), "in")
        if bag.get(fallback_key) not in (None, ""):
            return length_to_inches(bag.get(fallback_key), unit)
        prose = _prose_number(text, prose_patterns)
        return float(prose or 0)

    width_in = _stored_inches("width_in", "width", [
        r"(\d+(?:\.\d+)?)\s*\"?\s*L\b",
        r"(\d+(?:\.\d+)?)\s*(?:\"|in)?\s*(?:wide|width|long)\b",
    ])
    seat_depth = _stored_inches("depth_in", "depth", [
        r"(\d+(?:\.\d+)?)\s*\"?\s*D\b",
        r"(\d+(?:\.\d+)?)\s*(?:\"|in)?\s*deep\b",
    ]) or _stored_inches("seat_depth", "seat_depth", []) or 20.0

    seat_height = 0.0
    if bag.get("seat_height") not in (None, ""):
        seat_height = length_to_inches(bag.get("seat_height"), "in")
    else:
        prose_seat = _prose_number(text, [
            r"(\d+(?:\.\d+)?)\s*\"?\s*H\s*seat",
            r"seat(?:\s*height)?\s*(?:of\s*)?(\d+(?:\.\d+)?)",
        ])
        if prose_seat:
            seat_height = prose_seat
        elif bag.get("height_in") not in (None, ""):
            seat_height = length_to_inches(bag.get("height_in"), "in")
        elif bag.get("height") not in (None, ""):
            # CF furniture H is the single height they typed. Bench quotes
            # use it as seat height (see CF-2026-011: 18" H seat).
            seat_height = length_to_inches(bag.get("height"), unit)
    if not seat_height:
        seat_height = 18.0

    explicit_bh = bag.get("back_height")
    if explicit_bh in (None, ""):
        explicit_bh = _prose_number(text, [
            r"(\d+(?:\.\d+)?)\s*\"?\s*BH\b",
            r"back\s*height\s*(?:of\s*)?(\d+(?:\.\d+)?)",
        ])
    back_present = explicit_bh not in (None, "")

    explicit_panel = bag.get("panel_style")
    panel = normalize_panel_style(explicit_panel, default=_infer_panel_from_text(text)) if explicit_panel else _infer_panel_from_text(text)
    has_back, back_note = _infer_has_back(text, bag.get("has_back"), back_present)

    bench_type = (bag.get("bench_type") or design.get("bench_type") or "straight").lower()
    blob = text.lower()
    if "u-shape" in blob or "u shape" in blob or "booth" in blob:
        bench_type = "u_shape"
    elif "l-shape" in blob or "l shape" in blob:
        bench_type = "l_shape"

    product = bag.get("product_type") or ""
    if "freestanding" in blob and not product:
        product = "freestanding_bench"
    elif "banquette" in blob and not product:
        product = "banquette"

    name = design.get("name") or design.get("project_name") or "Bench"
    quote_num = design.get("design_number") or design.get("quote_number") or design.get("linked_quote_number") or ""

    params = {
        "bench_type": bench_type,
        "name": name,
        "width_in": width_in,
        "length_unit": "in",
        "seat_depth": seat_depth,
        "seat_height": seat_height,
        "back_height": float(explicit_bh) if back_present and has_back else None,
        "panel_style": "none" if not has_back else panel,
        "has_back": has_back,
        "cushion_width": float(bag.get("cushion_width") or 24),
        "channel_count": int(bag.get("channel_count") or 6),
        "business_unit": "woodcraft",
        "product_type": product,
        "quote_num": quote_num,
        "diagram_note": back_note,
    }
    # Drop None back_height so BenchRequest treats it as omitted only
    # when we actually want the shared default. No-back keeps None and
    # resolve_bench_request ignores BH.
    chip = category_chip(
        business_unit="woodcraft",
        bench_type=bench_type,
        product_type=product,
        name=name,
        panel_style=params["panel_style"],
        has_back=has_back,
    )
    return DiagramMap(
        connected=True,
        category=category or "furniture",
        reason="mapped furniture/bench line to bench diagram params",
        params=params,
        category_chip=chip,
    )
