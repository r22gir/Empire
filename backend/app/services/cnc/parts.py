"""Cut parts: wood is true size, foam equals wood, fabric is a separate label."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.cnc.inches import format_inches, parse_inches


def _size_pair(data: Any, default_w: Optional[int] = None, default_l: Optional[int] = None) -> tuple[int, int]:
    if data is None:
        if default_w is None or default_l is None:
            raise ValueError("size is required")
        return default_w, default_l
    if isinstance(data, dict):
        width = data.get("width")
        length = data.get("length") or data.get("height")
        if width is None or length is None:
            raise ValueError("size needs width and length")
        return parse_inches(width), parse_inches(length)
    raise ValueError(f"unsupported size payload: {data!r}")


def normalize_grain(value: Any) -> str:
    text = (value or "with").strip().lower()
    if text in {"free", "none", "any", "rotate"}:
        return "free"
    if text in {"with", "length", "width", "locked", "grain"}:
        return "with"
    return "with"


@dataclass
class CutPart:
    """One shop part with wood / foam / fabric sizes."""

    id: str
    name: str
    wood_w: int
    wood_l: int
    foam_w: int
    foam_l: int
    fabric_w: Optional[int]
    fabric_l: Optional[int]
    grain: str = "with"
    qty: int = 1
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, data: dict[str, Any], index: int = 0) -> "CutPart":
        wood_w, wood_l = _size_pair(data.get("wood") or data.get("size") or data)
        foam = data.get("foam")
        if foam is None:
            foam_w, foam_l = wood_w, wood_l
        else:
            foam_w, foam_l = _size_pair(foam, wood_w, wood_l)
        fabric = data.get("fabric")
        fabric_w = fabric_l = None
        if fabric is not None:
            fabric_w, fabric_l = _size_pair(fabric)
        qty = int(data.get("qty") or data.get("quantity") or 1)
        if qty < 1:
            raise ValueError("qty must be at least 1")
        return cls(
            id=str(data.get("id") or f"part-{index + 1}"),
            name=str(data.get("name") or data.get("title") or f"Part {index + 1}"),
            wood_w=wood_w,
            wood_l=wood_l,
            foam_w=foam_w,
            foam_l=foam_l,
            fabric_w=fabric_w,
            fabric_l=fabric_l,
            grain=normalize_grain(data.get("grain")),
            qty=qty,
            notes=str(data.get("notes") or data.get("note") or ""),
            extra={k: v for k, v in data.items() if k not in {
                "id", "name", "title", "wood", "foam", "fabric", "size",
                "width", "length", "height", "grain", "qty", "quantity",
                "notes", "note",
            }},
        )

    def labeled_sizes(self) -> dict[str, Optional[str]]:
        return {
            "wood_width": format_inches(self.wood_w),
            "wood_length": format_inches(self.wood_l),
            "foam_width": format_inches(self.foam_w),
            "foam_length": format_inches(self.foam_l),
            "fabric_width": format_inches(self.fabric_w) if self.fabric_w is not None else None,
            "fabric_length": format_inches(self.fabric_l) if self.fabric_l is not None else None,
            "grain": self.grain,
        }

    def foam_matches_wood(self) -> bool:
        return self.foam_w == self.wood_w and self.foam_l == self.wood_l
