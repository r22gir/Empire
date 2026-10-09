"""Guillotine 2D bin packing and roll strip packing algorithms.

Implements:
1. GuillotineSheetPacker:
   - Packs rectangular parts onto standard fixed-size sheets (e.g., 48" x 96" plywood, 54" x 82" foam).
   - Supports configurable kerf (blade thickness, e.g., 1/8" = 0.125").
   - Supports grain / rotation constraints (can_rotate=True/False).
   - Uses Best Area Fit (BAF) / Best Short Side Fit with guillotine split (shorter axis split).
2. RollStripPacker:
   - Packs parts onto continuous roll materials (e.g., 54" roll with 53" usable width).
   - Minimizes total roll length used.
   - Respects grain / nap constraints (e.g., fabric pieces upright along length).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class RectPart:
    """A part to be placed."""
    id: str
    name: str
    width: float   # width in inches (X dimension by default)
    length: float  # length in inches (Y dimension by default)
    material_type: str = "board"  # board, foam, fabric, dacron
    thickness_in: Optional[float] = None
    can_rotate: bool = True
    color_hex: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlacedPart:
    """A part placed onto a sheet or roll."""
    part_id: str
    name: str
    x: float
    y: float
    width: float
    length: float
    rotated: bool
    material_type: str
    thickness_in: Optional[float] = None
    color_hex: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FreeRect:
    x: float
    y: float
    w: float
    h: float


class GuillotineSheetPacker:
    """2D Guillotine Bin Packer for fixed-dimension rectangular sheets."""

    def __init__(
        self,
        sheet_width: float = 48.0,
        sheet_length: float = 96.0,
        kerf: float = 0.125,
        can_rotate: bool = True,
    ):
        self.sheet_width = sheet_width
        self.sheet_length = sheet_length
        self.kerf = kerf
        self.can_rotate = can_rotate

    def pack(self, parts: List[RectPart]) -> List[Dict[str, Any]]:
        """Pack parts onto minimum number of sheets using Best Area Fit guillotine."""
        # Sort parts descending by area, then max dimension
        sorted_parts = sorted(
            parts,
            key=lambda p: (p.width * p.length, max(p.width, p.length)),
            reverse=True,
        )

        sheets: List[Dict[str, Any]] = []

        for part in sorted_parts:
            placed = False
            # Try placing in existing sheets
            for sheet_idx, sheet in enumerate(sheets):
                free_rects = sheet["free_rects"]
                best_fit_idx = -1
                best_fit_rotated = False
                best_area_fit = float("inf")

                for idx, fr in enumerate(free_rects):
                    # Normal orientation
                    if part.width <= fr.w and part.length <= fr.h:
                        rem_area = fr.w * fr.h - part.width * part.length
                        if rem_area < best_area_fit:
                            best_area_fit = rem_area
                            best_fit_idx = idx
                            best_fit_rotated = False

                    # Rotated orientation
                    if (self.can_rotate and part.can_rotate) and (part.length <= fr.w and part.width <= fr.h):
                        rem_area = fr.w * fr.h - part.length * part.width
                        if rem_area < best_area_fit:
                            best_area_fit = rem_area
                            best_fit_idx = idx
                            best_fit_rotated = True

                if best_fit_idx >= 0:
                    fr = free_rects.pop(best_fit_idx)
                    pw = part.length if best_fit_rotated else part.width
                    ph = part.width if best_fit_rotated else part.length

                    placed_item = PlacedPart(
                        part_id=part.id,
                        name=part.name,
                        x=fr.x,
                        y=fr.y,
                        width=pw,
                        length=ph,
                        rotated=best_fit_rotated,
                        material_type=part.material_type,
                        thickness_in=part.thickness_in,
                        color_hex=part.color_hex,
                        extra=part.extra,
                    )
                    sheet["placed"].append(placed_item)

                    # Guillotine split remaining space of fr:
                    # Account for saw kerf between parts and offcuts
                    # Split along shorter axis
                    w_rem = fr.w - pw - self.kerf
                    h_rem = fr.h - ph - self.kerf

                    if w_rem > 0 and h_rem > 0:
                        # Shorter axis split rule (guillotine)
                        if fr.w <= fr.h:
                            # Horizontal cut first
                            free_rects.append(FreeRect(fr.x, fr.y + ph + self.kerf, fr.w, h_rem))
                            free_rects.append(FreeRect(fr.x + pw + self.kerf, fr.y, w_rem, ph))
                        else:
                            # Vertical cut first
                            free_rects.append(FreeRect(fr.x + pw + self.kerf, fr.y, w_rem, fr.h))
                            free_rects.append(FreeRect(fr.x, fr.y + ph + self.kerf, pw, h_rem))
                    elif w_rem > 0:
                        free_rects.append(FreeRect(fr.x + pw + self.kerf, fr.y, w_rem, fr.h))
                    elif h_rem > 0:
                        free_rects.append(FreeRect(fr.x, fr.y + ph + self.kerf, fr.w, h_rem))

                    placed = True
                    break

            if not placed:
                # Open a new sheet
                new_sheet_idx = len(sheets) + 1
                free_rects = [FreeRect(0.0, 0.0, self.sheet_width, self.sheet_length)]
                fr = free_rects.pop(0)

                # Check if it fits
                fit_normal = part.width <= fr.w and part.length <= fr.h
                fit_rot = (self.can_rotate and part.can_rotate) and (part.length <= fr.w and part.width <= fr.h)

                if not fit_normal and not fit_rot:
                    raise ValueError(
                        f"Part {part.name} ({part.width}\" x {part.length}\") is larger than sheet "
                        f"({self.sheet_width}\" x {self.sheet_length}\"). Cannot nest on single sheet."
                    )

                rot = fit_rot if not fit_normal else False
                # If both fit, prefer orientation that preserves wider continuous remainder
                if fit_normal and fit_rot:
                    # Prefer fitting with part length along sheet length
                    if part.length > part.width and self.sheet_length > self.sheet_width:
                        rot = False
                    elif part.width > part.length and self.sheet_length > self.sheet_width:
                        rot = True

                pw = part.length if rot else part.width
                ph = part.width if rot else part.length

                placed_item = PlacedPart(
                    part_id=part.id,
                    name=part.name,
                    x=fr.x,
                    y=fr.y,
                    width=pw,
                    length=ph,
                    rotated=rot,
                    material_type=part.material_type,
                    thickness_in=part.thickness_in,
                    color_hex=part.color_hex,
                    extra=part.extra,
                )

                w_rem = fr.w - pw - self.kerf
                h_rem = fr.h - ph - self.kerf

                if w_rem > 0 and h_rem > 0:
                    if fr.w <= fr.h:
                        free_rects.append(FreeRect(fr.x, fr.y + ph + self.kerf, fr.w, h_rem))
                        free_rects.append(FreeRect(fr.x + pw + self.kerf, fr.y, w_rem, ph))
                    else:
                        free_rects.append(FreeRect(fr.x + pw + self.kerf, fr.y, w_rem, fr.h))
                        free_rects.append(FreeRect(fr.x, fr.y + ph + self.kerf, pw, h_rem))
                elif w_rem > 0:
                    free_rects.append(FreeRect(fr.x + pw + self.kerf, fr.y, w_rem, fr.h))
                elif h_rem > 0:
                    free_rects.append(FreeRect(fr.x, fr.y + ph + self.kerf, fr.w, h_rem))

                sheets.append({
                    "sheet_index": new_sheet_idx,
                    "sheet_width": self.sheet_width,
                    "sheet_length": self.sheet_length,
                    "placed": [placed_item],
                    "free_rects": free_rects,
                })

        # Calculate metrics per sheet
        sheet_results = []
        for s in sheets:
            placed = s["placed"]
            used_area = sum(p.width * p.length for p in placed)
            total_area = self.sheet_width * self.sheet_length
            yield_pct = round((used_area / total_area) * 100.0, 1)

            # Filter offcuts / usable free rects (e.g. area >= 48 sq in)
            offcuts = []
            for fr in s["free_rects"]:
                if fr.w >= 4.0 and fr.h >= 4.0:
                    offcuts.append({
                        "x": round(fr.x, 3),
                        "y": round(fr.y, 3),
                        "width": round(fr.w, 3),
                        "length": round(fr.h, 3),
                        "area_sq_in": round(fr.w * fr.h, 1),
                    })

            sheet_results.append({
                "sheet_index": s["sheet_index"],
                "sheet_width": self.sheet_width,
                "sheet_length": self.sheet_length,
                "placed_parts": placed,
                "used_area_sq_in": round(used_area, 2),
                "total_area_sq_in": round(total_area, 2),
                "yield_pct": yield_pct,
                "offcuts": offcuts,
            })

        return sheet_results


class RollStripPacker:
    """1D/2D continuous roll packer for fabric and dacron.

    Minimizes total roll length used while honoring:
    - Roll width and usable width (after selvage, e.g. 54" roll -> 53" usable)
    - Grain / nap direction (can_rotate)
    - Waste % configurable (default 10%)
    - Round totals UP to nearest 1/2 yd
    """

    def __init__(
        self,
        roll_width: float = 54.0,
        usable_width: float = 53.0,
        kerf: float = 0.25,  # 1/4" cut spacing
        can_rotate: bool = False,  # nap/grain usually prevents rotation for channel upholstery
    ):
        self.roll_width = roll_width
        self.usable_width = usable_width
        self.kerf = kerf
        self.can_rotate = can_rotate

    def pack(
        self,
        parts: List[RectPart],
        waste_pct: float = 10.0,
        round_up_half_yard: bool = True,
    ) -> Dict[str, Any]:
        """Pack parts onto continuous roll using skyline / level strip algorithm."""
        if not parts:
            return {
                "roll_width": self.roll_width,
                "usable_width": self.usable_width,
                "placed_parts": [],
                "net_length_in": 0.0,
                "net_yards": 0.0,
                "total_length_in": 0.0,
                "total_yards": 0.0,
                "yield_pct": 0.0,
                "offcuts": [],
            }

        # Skyline segments: list of [x_start, x_end, current_y]
        skyline: List[Tuple[float, float, float]] = [(0.0, self.usable_width, 0.0)]
        placed_parts: List[PlacedPart] = []

        # Sort parts descending by length (height along roll), then width
        sorted_parts = sorted(
            parts,
            key=lambda p: (p.length, p.width),
            reverse=True,
        )

        for part in sorted_parts:
            # Determine orientation
            rot = False
            pw, ph = part.width, part.length

            # Check if part fits across usable width
            if pw > self.usable_width:
                if self.can_rotate and part.can_rotate and ph <= self.usable_width:
                    rot = True
                    pw, ph = part.length, part.width
                else:
                    raise ValueError(
                        f"Part {part.name} ({part.width}\" wide) exceeds usable roll width {self.usable_width}\"."
                    )

            # Find position along skyline that minimizes the resulting y + ph
            best_y = float("inf")
            best_x = 0.0
            best_skyline_idx = -1

            # Check every possible x position where part could start
            # Feasible x positions are skyline segment starts that have enough width
            for i in range(len(skyline)):
                x_start = skyline[i][0]
                x_end = x_start + pw
                if x_end > self.usable_width:
                    continue

                # Find max skyline y across [x_start, x_end]
                max_y = 0.0
                for seg in skyline:
                    # Overlaps?
                    if not (seg[1] <= x_start or seg[0] >= x_end):
                        max_y = max(max_y, seg[2])

                if max_y < best_y:
                    best_y = max_y
                    best_x = x_start

            # Place part at (best_x, best_y)
            placed_parts.append(PlacedPart(
                part_id=part.id,
                name=part.name,
                x=best_x,
                y=best_y,
                width=pw,
                length=ph,
                rotated=rot,
                material_type=part.material_type,
                thickness_in=part.thickness_in,
                color_hex=part.color_hex,
                extra=part.extra,
            ))

            # Update skyline with new level
            new_y = best_y + ph + self.kerf
            new_x_start = best_x
            new_x_end = best_x + pw

            # Rebuild skyline
            new_skyline: List[Tuple[float, float, float]] = []
            for seg in skyline:
                s_x0, s_x1, s_y = seg
                if s_x1 <= new_x_start or s_x0 >= new_x_end:
                    new_skyline.append(seg)
                else:
                    if s_x0 < new_x_start:
                        new_skyline.append((s_x0, new_x_start, s_y))
                    if s_x1 > new_x_end:
                        new_skyline.append((new_x_end, s_x1, s_y))
            new_skyline.append((new_x_start, new_x_end, new_y))

            # Sort skyline by x and merge adjacent segments with same y
            new_skyline.sort(key=lambda s: s[0])
            merged_skyline: List[Tuple[float, float, float]] = []
            for seg in new_skyline:
                if not merged_skyline:
                    merged_skyline.append(seg)
                else:
                    prev = merged_skyline[-1]
                    if abs(prev[1] - seg[0]) < 1e-6 and abs(prev[2] - seg[2]) < 1e-6:
                        merged_skyline[-1] = (prev[0], seg[1], prev[2])
                    else:
                        merged_skyline.append(seg)
            skyline = merged_skyline

        # Calculate overall bounding length
        net_length_in = max(p.y + p.length for p in placed_parts) if placed_parts else 0.0
        net_yards = net_length_in / 36.0

        # Apply configurable waste percentage (e.g. 10%)
        waste_factor = 1.0 + (waste_pct / 100.0)
        total_yards_raw = net_yards * waste_factor

        # Round UP to nearest 1/2 yard
        if round_up_half_yard:
            total_yards = math.ceil(total_yards_raw * 2.0) / 2.0
        else:
            total_yards = round(total_yards_raw, 2)

        total_length_in = total_yards * 36.0
        used_area = sum(p.width * p.length for p in placed_parts)
        total_roll_area = self.usable_width * net_length_in if net_length_in > 0 else 1.0
        yield_pct = round((used_area / total_roll_area) * 100.0, 1) if net_length_in > 0 else 0.0

        return {
            "roll_width": self.roll_width,
            "usable_width": self.usable_width,
            "placed_parts": placed_parts,
            "net_length_in": round(net_length_in, 3),
            "net_yards": round(net_yards, 3),
            "waste_pct": waste_pct,
            "total_length_in": round(total_length_in, 3),
            "total_yards": total_yards,
            "yield_pct": yield_pct,
            "offcuts": [],
        }
