"""Deterministic drawing-intent routing for MAX chat.

This keeps drawing/CAD requests out of generic LLM completion unless MAX needs
to ask for missing structured inputs first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


DRAWING_KEYWORDS = (
    "drawing",
    "draw",
    "render",
    "sketch",
    "elevation",
    "plan",
    "isometric",
    "section",
    "4-view",
    "four-view",
    "pdf drawing",
    "bench drawing",
    "cad",
)

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
    "long": "width",
    "length": "width",
    "l": "width",
    "deep": "depth",
    "depth": "depth",
    "d": "depth",
    "high": "height",
    "height": "height",
    "h": "height",
    "overall height": "height",
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

    @property
    def ready(self) -> bool:
        return self.tool_payload is not None and not self.missing


def is_drawing_intent(text: str) -> bool:
    lowered = text.lower()
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


def _extract_dimensions(text: str) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    # 96" wide, 22 in deep, 36 high, 8 ft long
    value_first = re.compile(
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>\"|in(?:ch(?:es)?)?|ft|feet|')?\s+"
        r"(?P<label>overall height|seat height|seat h|back height|back h|wide|width|long|length|deep|depth|high|height)\b",
        re.IGNORECASE,
    )
    # width 96", seat height 18
    label_first = re.compile(
        r"(?P<label>overall height|seat height|seat h|back height|back h|width|length|depth|height)\s*[:=]?\s*"
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
        return DrawingHandoff(is_drawing_intent=False)

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
        handoff.response = (
            "I need drawing inputs before I generate anything. "
            f"Missing: {', '.join(dict.fromkeys(handoff.missing))}. "
            "Send the item type plus real dimensions, or attach/source an image from Drawing Studio."
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
        payload.update({
            "shape": _shape_for_text(message),
            "width": dimensions.get("width", "120\"").rstrip('"'),
            "depth": dimensions.get("depth", "22\"").rstrip('"'),
            "seat_height": dimensions.get("seat_height", "18\"").rstrip('"'),
            "back_height": dimensions.get("back_height", dimensions.get("height", "36\"")).rstrip('"'),
        })
    if image_filename:
        payload["source_image"] = image_filename

    handoff.tool_payload = payload
    handoff.response = "Starting the drawing workflow. I will return the generated drawing artifact here."
    return handoff
