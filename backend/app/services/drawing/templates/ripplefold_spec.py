"""Kirsch Ripplefold spec.

Carrier spacing is the Kirsch snap-carrier set:

  92140  1-7/8"  120% fullness
  92141  2-1/8"  100% fullness
  92142  2-3/8"   80% fullness
  92143  2-5/8"   60% fullness

Carrier count comes from the butt-master and overlap-master charts
(Kirsch fabrication guide / Hollis stack guide). A center draw looks
up each half of the track. Ceiling height and mount are never filled
in when the request leaves them out.
"""
from __future__ import annotations

from dataclasses import dataclass, field


CARRIERS: dict[str, dict] = {
    "92140": {"spacing": 1.875, "fullness": 120, "name": "No. 92140"},
    "92141": {"spacing": 2.125, "fullness": 100, "name": "No. 92141"},
    "92142": {"spacing": 2.375, "fullness": 80, "name": "No. 92142"},
    "92143": {"spacing": 2.625, "fullness": 60, "name": "No. 92143"},
}

# Max panel coverage at 8 snaps, then +spacing per extra snap.
# Butt master 1047140/1047141 and overlap master one-way charts.
_CHART_BASE = {
    "butt": {120: 13.25, 100: 14.875, 80: 16.125, 60: 17.63},
    "overlap": {120: 17.75, 100: 19.5, 80: 21.125, 60: 22.875},
}
_SPACING = {120: 1.875, 100: 2.125, 80: 2.375, 60: 2.625}

# Published butt-master stackback (inches) by factory-snap count.
_BUTT_STACK = {
    8: 7.25, 10: 8.5, 12: 9.5, 14: 10.75, 16: 11.75, 18: 13.0,
    20: 14.0, 22: 15.0, 24: 16.25, 26: 17.25, 28: 18.5, 30: 19.5,
    32: 20.5, 34: 21.75, 36: 22.75, 38: 24.0, 40: 25.0, 42: 26.25,
    44: 27.25, 46: 28.25, 48: 29.5, 50: 30.5,
}


def _inches(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace('"', "").replace("inches", "").replace("inch", "")
    text = text.replace(" ", "")
    if not text:
        return None
    if "-" in text and "/" in text:
        whole, frac = text.split("-", 1)
        num, den = frac.split("/", 1)
        return float(whole or 0) + float(num) / float(den)
    if "/" in text:
        num, den = text.split("/", 1)
        return float(num) / float(den)
    return float(text)


def _fullness_percent(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip().endswith("%"):
        value = value.strip()[:-1]
    number = float(value)
    if number in (60, 80, 100, 120):
        return int(number)
    # Kirsch multipliers: 1.6 / 1.8 / 2.0 / 2.2 → 60 / 80 / 100 / 120.
    for percent, factor in ((60, 1.6), (80, 1.8), (100, 2.0), (120, 2.2)):
        if abs(number - factor) < 0.05:
            return percent
    return None


def chart_coverage(snaps: int, fullness: int, masters: str) -> float:
    """Largest panel coverage the chart lists for this snap count."""
    base = _CHART_BASE[masters][fullness]
    return base + (snaps - 8) * _SPACING[fullness]


def carriers_for_panel(coverage: float, fullness: int, masters: str) -> int:
    """Smallest even snap count whose chart coverage reaches the panel."""
    snaps = 8
    while snaps <= 400:
        if chart_coverage(snaps, fullness, masters) + 1e-6 >= coverage:
            return snaps
        snaps += 2
    raise ValueError(f"panel coverage {coverage} exceeds the Kirsch chart")


@dataclass
class RipplefoldJob:
    window_width: float
    window_height: float
    coverage_width: float
    track_length: float
    track_equals_coverage: bool
    align: str | None
    offset: float | None
    fullness: int | None
    carrier: str | None
    carrier_spacing: float | None
    control: str | None
    masters: str | None
    carriers_per_panel: int | None
    carrier_count: int | None
    full_spaces_per_panel: int | None
    stack: float | None
    stack_source: str | None
    mount: str | None
    ceiling_height: float | None
    mount_height: float | None
    layer: str
    layered: bool
    side_panels: int = 0
    side_widths: float | None = None
    fabric_image: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return "RIPPLEFOLD"


def _text(source: dict, *keys: str) -> str | None:
    for key in keys:
        raw = source.get(key)
        if raw is None or raw == "":
            continue
        return str(raw).strip()
    return None


def _norm_control(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.lower().replace("_", "-").replace(" ", "-")
    if text in {"center", "centre", "center-draw", "two-way", "two-way-draw", "split"}:
        return "center"
    if text in {
        "one-way", "oneway", "one-way-draw", "left", "right",
        "one-way-l", "one-way-r", "one-way-left", "one-way-right",
    }:
        return "one-way"
    return None


def _norm_masters(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.lower()
    if "butt" in text:
        return "butt"
    if "overlap" in text:
        return "overlap"
    return None


def _norm_align(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.lower().replace("_", "-")
    if text in {"center", "centre", "centered", "re-centered", "recentered", "re-center"}:
        return "center"
    if text in {"left", "offset-left"}:
        return "left"
    if text in {"right", "offset-right"}:
        return "right"
    if text in {"offset", "given"}:
        return "offset"
    return None


def _norm_layer(raw: str | None, layered_flag) -> str:
    text = (raw or "").lower().replace("_", " ").replace("-", " ")
    if layered_flag in (True, "true", "yes", "1", 1):
        return "sheer behind drapery"
    if "behind" in text:
        return "sheer behind drapery"
    if "sheer" in text:
        return "sheer"
    if not text:
        return "drapery"
    return text


def resolve_ripplefold(spec: dict) -> RipplefoldJob:
    """Build a ripplefold job. Missing mount and ceiling stay missing."""
    dims = dict(spec.get("dims") or {})
    dims.update({k: spec[k] for k in spec if k not in {"dims", "product_type"}})
    window_width = _inches(dims.get("window_width", dims.get("width")))
    window_height = _inches(dims.get("window_height", dims.get("height")))
    if window_width is None or window_height is None:
        raise ValueError("ripplefold requires window width and height")
    coverage = _inches(dims.get("coverage_width", dims.get("coverage")))
    coverage_given = coverage is not None
    if coverage is None:
        coverage = window_width
    if coverage <= 0 or coverage > window_width + 1e-6:
        raise ValueError("coverage width must be within the window width")
    track = _inches(dims.get("track_length", dims.get("track")))
    track_equals = track is None
    if track is None:
        track = coverage

    align = _norm_align(_text(dims, "coverage_align", "align", "track_align"))
    offset_given = _inches(dims.get("coverage_offset", dims.get("offset")))
    offset: float | None
    if align == "center":
        offset = (window_width - coverage) / 2.0
    elif align == "left":
        offset = 0.0
    elif align == "right":
        offset = window_width - coverage
    elif align == "offset":
        offset = offset_given
    elif offset_given is not None:
        align = "offset"
        offset = offset_given
    elif not coverage_given or abs(coverage - window_width) < 1e-6:
        align = "full"
        offset = 0.0
    else:
        align = None
        offset = None

    carrier = _text(dims, "carrier", "carrier_no", "carrier_number")
    if carrier:
        if carrier.endswith(".0"):
            carrier = carrier[:-2]
        carrier = "".join(ch for ch in carrier if ch.isdigit()) or carrier
    catalog = CARRIERS.get(carrier or "")
    fullness = _fullness_percent(dims.get("fullness_pct", dims.get("fullness_percent")))
    if fullness is None:
        fullness = _fullness_percent(dims.get("fullness"))
    spacing = _inches(dims.get("carrier_spacing", dims.get("spacing")))
    notes: list[str] = []
    if catalog:
        if fullness is None:
            fullness = catalog["fullness"]
        if spacing is None:
            spacing = catalog["spacing"]
        if fullness != catalog["fullness"] or (
            spacing is not None and abs(spacing - catalog["spacing"]) > 0.02
        ):
            notes.append(
                f"{carrier} chart is {catalog['fullness']}% at "
                f"{catalog['spacing']}\"; request overrides that pair"
            )
    control = _norm_control(_text(dims, "control", "draw", "draw_direction"))
    masters = _norm_masters(_text(dims, "masters", "master"))
    carriers_per_panel = None
    carrier_count = None
    full_spaces = None
    if fullness in _SPACING and masters and coverage:
        panel = coverage if control == "one-way" else coverage / 2.0 if control == "center" else None
        if panel is not None:
            carriers_per_panel = carriers_for_panel(panel, fullness, masters)
            panels = 1 if control == "one-way" else 2
            carrier_count = carriers_per_panel * panels
            full_spaces = carriers_per_panel - 1

    stack = _inches(dims.get("stack", dims.get("stack_width", dims.get("stackback"))))
    stack_source = "given" if stack is not None else None
    if stack is None and carriers_per_panel and masters == "butt":
        stack = _BUTT_STACK.get(carriers_per_panel)
        if stack is not None:
            stack_source = "kirsch chart"

    mount = _text(dims, "mount", "mount_type")
    if mount:
        mount = mount.lower()
    ceiling = _inches(dims.get("ceiling_height", dims.get("ceiling")))
    mount_height = _inches(dims.get("mount_height"))
    layer = _norm_layer(_text(dims, "layer", "fabric_layer"), dims.get("layered"))
    side_panels = 0
    raw_sides = dims.get("side_panels")
    if raw_sides not in (None, ""):
        try:
            side_panels = max(0, int(float(raw_sides)))
        except (TypeError, ValueError):
            side_panels = 0
    side_widths = _inches(dims.get("side_widths", dims.get("widths_per_panel")))
    fabric_image = _text(dims, "fabric_image", "fabric_crop")
    if track_equals:
        notes.append("track length not given; track equals coverage")
    return RipplefoldJob(
        window_width=window_width,
        window_height=window_height,
        coverage_width=coverage,
        track_length=track,
        track_equals_coverage=track_equals,
        align=align,
        offset=offset,
        fullness=fullness,
        carrier=carrier,
        carrier_spacing=spacing if spacing is not None else (catalog["spacing"] if catalog else None),
        control=control,
        masters=masters,
        carriers_per_panel=carriers_per_panel,
        carrier_count=carrier_count,
        full_spaces_per_panel=full_spaces,
        stack=stack,
        stack_source=stack_source,
        mount=mount,
        ceiling_height=ceiling,
        mount_height=mount_height,
        layer=layer,
        layered=layer == "sheer behind drapery",
        side_panels=side_panels,
        side_widths=side_widths,
        fabric_image=fabric_image,
        notes=notes,
    )


def enrich_ripplefold_message(message: str, dims: dict) -> dict:
    """Pull ripplefold words out of a chat request. Does not invent mount or ceiling."""
    import re
    text = message.lower()
    out = dict(dims)
    sheer = re.search(r"sheer[s]?\s+covering\s+(\d+(?:\.\d+)?)", text)
    cover = re.search(r"(?:covering|coverage(?:\s+width)?)\s+(\d+(?:\.\d+)?)", text)
    if sheer:
        out["coverage_width"] = sheer.group(1)
        out.setdefault("layer", "sheer")
    elif cover:
        out["coverage_width"] = cover.group(1)
    percent = re.search(r"\b(60|80|100|120)\s*%", text)
    if percent:
        out["fullness_pct"] = percent.group(1)
    for number in ("92140", "92141", "92142", "92143"):
        if number in text:
            out["carrier"] = number
            break
    if "butt" in text:
        out["masters"] = "butt"
    elif "overlap" in text:
        out["masters"] = "overlap"
    if "one-way" in text or "one way" in text:
        out["control"] = "one-way"
    elif "center draw" in text or "centre draw" in text or "two-way" in text or "two way" in text:
        out["control"] = "center"
    if "re-center" in text or "recentered" in text or "re-centred" in text or "centered" in text:
        out["coverage_align"] = "center"
    if "sheer behind" in text or "sheer-behind" in text:
        out["layer"] = "sheer behind drapery"
    return out
