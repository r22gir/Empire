"""Guillotine nest with kerf, grain, and X-Carve tiling."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.cnc.constants import (
    DEFAULT_FABRIC_USABLE_WIDTH,
    DEFAULT_FOAM_SHEET_LENGTH,
    DEFAULT_FOAM_SHEET_WIDTH,
    DEFAULT_KERF,
    DEFAULT_SHEET_LENGTH,
    DEFAULT_SHEET_WIDTH,
    MACHINE_NAME,
    REG_MARK_INSET,
    REG_MARK_SIZE,
    XCARVE_MAX_WIDTH,
    XCARVE_TILE_LENGTH,
)
from app.services.cnc.inches import (
    assert_no_decimal_measurements,
    format_inches,
    parse_inches,
    yield_fraction,
)
from app.services.cnc.parts import CutPart


class NestError(ValueError):
    """A part or sheet cannot be cut on the X-Carve as specified."""


@dataclass
class PlacedRect:
    part_id: str
    name: str
    x: int
    y: int
    w: int
    l: int
    rotated: bool
    grain: str
    tile_index: int = 0
    tile_count: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "name": self.name,
            "x": format_inches(self.x),
            "y": format_inches(self.y),
            "width": format_inches(self.w),
            "length": format_inches(self.l),
            "rotated": self.rotated,
            "grain": self.grain,
            "tile_index": self.tile_index,
            "tile_count": self.tile_count,
        }


@dataclass
class RegistrationMark:
    name: str
    x: int
    y: int
    size: int
    seam_along: str  # "length" means the seam is across the width (slide along length)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "x": format_inches(self.x),
            "y": format_inches(self.y),
            "mark_size": format_inches(self.size),
            "seam_along": self.seam_along,
        }


@dataclass
class NestedSheet:
    index: int
    material: str
    width: int
    length: int
    kerf: int
    parts: list[PlacedRect] = field(default_factory=list)
    marks: list[RegistrationMark] = field(default_factory=list)
    tiled: bool = False
    tile_index: int = 1
    tile_count: int = 1
    parent_panel: Optional[str] = None

    @property
    def used_area(self) -> int:
        return sum(p.w * p.l for p in self.parts)

    @property
    def total_area(self) -> int:
        return self.width * self.length

    def as_dict(self) -> dict[str, Any]:
        leftover = max(0, self.total_area - self.used_area)
        return {
            "index": self.index,
            "material": self.material,
            "sheet_width": format_inches(self.width),
            "sheet_length": format_inches(self.length),
            "kerf": format_inches(self.kerf),
            "yield": yield_fraction(self.used_area, self.total_area),
            "used_area_label": f"{yield_fraction(self.used_area, self.total_area)} of sheet",
            "leftover_fraction": yield_fraction(leftover, self.total_area) if self.total_area else "0/1",
            "parts": [p.as_dict() for p in self.parts],
            "registration_marks": [m.as_dict() for m in self.marks],
            "tiled": self.tiled,
            "tile_index": self.tile_index,
            "tile_count": self.tile_count,
            "parent_panel": self.parent_panel,
        }


@dataclass
class FreeRect:
    x: int
    y: int
    w: int
    h: int


class GuillotinePacker:
    def __init__(self, sheet_w: int, sheet_l: int, kerf: int):
        self.sheet_w = sheet_w
        self.sheet_l = sheet_l
        self.kerf = kerf

    def pack(self, items: list[tuple[CutPart, int, int, str]]) -> list[NestedSheet]:
        """items: (part, width, length, material)."""
        ordered = sorted(items, key=lambda it: (it[1] * it[2], max(it[1], it[2])), reverse=True)
        sheets: list[NestedSheet] = []
        for part, w, l, material in ordered:
            placed = False
            for sheet in sheets:
                if self._place(sheet, part, w, l):
                    placed = True
                    break
            if not placed:
                sheet = NestedSheet(
                    index=len(sheets) + 1,
                    material=material,
                    width=self.sheet_w,
                    length=self.sheet_l,
                    kerf=self.kerf,
                )
                sheet._free = [FreeRect(0, 0, self.sheet_w, self.sheet_l)]  # type: ignore[attr-defined]
                if not self._place(sheet, part, w, l):
                    raise NestError(
                        f"{part.name} ({format_inches(w)} x {format_inches(l)}) "
                        f"does not fit a {format_inches(self.sheet_w)} x {format_inches(self.sheet_l)} sheet"
                    )
                sheets.append(sheet)
        return sheets

    def _orientations(self, part: CutPart, w: int, l: int) -> list[tuple[int, int, bool]]:
        opts = [(w, l, False)]
        if part.grain == "free" and w != l:
            opts.append((l, w, True))
        return opts

    def _place(self, sheet: NestedSheet, part: CutPart, w: int, l: int) -> bool:
        free: list[FreeRect] = sheet._free  # type: ignore[attr-defined]
        best_i = -1
        best_rot = False
        best_pw = best_ph = 0
        best_waste = None
        for i, fr in enumerate(free):
            for pw, ph, rot in self._orientations(part, w, l):
                if pw <= fr.w and ph <= fr.h:
                    waste = fr.w * fr.h - pw * ph
                    if best_waste is None or waste < best_waste:
                        best_waste = waste
                        best_i = i
                        best_rot = rot
                        best_pw, best_ph = pw, ph
        if best_i < 0:
            return False
        fr = free.pop(best_i)
        sheet.parts.append(PlacedRect(
            part_id=part.id,
            name=part.name,
            x=fr.x,
            y=fr.y,
            w=best_pw,
            l=best_ph,
            rotated=best_rot,
            grain=part.grain,
        ))
        right_w = fr.w - best_pw - self.kerf
        top_h = fr.h - best_ph - self.kerf
        if right_w > 0:
            free.append(FreeRect(fr.x + best_pw + self.kerf, fr.y, right_w, best_ph))
        if top_h > 0:
            free.append(FreeRect(fr.x, fr.y + best_ph + self.kerf, fr.w, top_h))
        return True


def _parse_opt(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    return parse_inches(value)


def _expand_qty(parts: list[CutPart]) -> list[CutPart]:
    out: list[CutPart] = []
    for part in parts:
        for i in range(part.qty):
            if part.qty == 1:
                out.append(part)
            else:
                clone = CutPart(
                    id=f"{part.id}-{i + 1}",
                    name=f"{part.name} ({i + 1}/{part.qty})",
                    wood_w=part.wood_w,
                    wood_l=part.wood_l,
                    foam_w=part.foam_w,
                    foam_l=part.foam_l,
                    fabric_w=part.fabric_w,
                    fabric_l=part.fabric_l,
                    grain=part.grain,
                    qty=1,
                    notes=part.notes,
                    extra=part.extra,
                )
                out.append(clone)
    return out


def _fits_machine(w: int, l: int, grain: str, max_w: int) -> tuple[int, int, bool]:
    """Return (placed_w, placed_l, rotated) so width ≤ machine max."""
    if w <= max_w:
        return w, l, False
    if grain == "free" and l <= max_w:
        return l, w, True
    raise NestError(
        f"Part {format_inches(w)} x {format_inches(l)} exceeds X-Carve width "
        f"{format_inches(max_w)}. Rotate is blocked by grain={grain}."
    )


def _tile_long_panel(
    part: CutPart,
    w: int,
    l: int,
    *,
    material: str,
    tile_length: int,
    max_width: int,
    kerf: int,
    start_index: int,
) -> list[NestedSheet]:
    """Split a panel longer than one machine pass. Registration marks on each seam."""
    placed_w, placed_l, _ = _fits_machine(w, l, part.grain, max_width)
    if placed_l <= tile_length:
        return []
    remaining = placed_l
    tiles: list[NestedSheet] = []
    tile_count = (placed_l + tile_length - 1) // tile_length
    tile_no = 0
    while remaining > 0:
        tile_no += 1
        this_l = min(tile_length, remaining)
        sheet = NestedSheet(
            index=start_index + tile_no,
            material=material,
            width=placed_w,
            length=this_l,
            kerf=kerf,
            tiled=True,
            tile_index=tile_no,
            tile_count=tile_count,
            parent_panel=part.name,
        )
        sheet.parts.append(PlacedRect(
            part_id=part.id,
            name=f"{part.name} tile {tile_no}/{tile_count}",
            x=0,
            y=0,
            w=placed_w,
            l=this_l,
            rotated=False,
            grain=part.grain,
            tile_index=tile_no,
            tile_count=tile_count,
        ))
        # Seams: after this tile (except the last) and before this tile (except the first).
        if tile_no < tile_count:
            sheet.marks.extend(_seam_marks(placed_w, this_l, f"{part.id}-T{tile_no}-END"))
        if tile_no > 1:
            sheet.marks.extend(_seam_marks(placed_w, 0, f"{part.id}-T{tile_no}-START", at_origin=True))
        tiles.append(sheet)
        remaining -= this_l
    return tiles


def _seam_marks(width: int, y: int, prefix: str, at_origin: bool = False) -> list[RegistrationMark]:
    inset = min(REG_MARK_INSET, max(0, width // 4))
    y_pos = 0 if at_origin else y
    return [
        RegistrationMark(name=f"{prefix}-L", x=inset, y=y_pos, size=REG_MARK_SIZE, seam_along="length"),
        RegistrationMark(name=f"{prefix}-R", x=max(0, width - inset), y=y_pos, size=REG_MARK_SIZE, seam_along="length"),
    ]


def nest_cut_list(payload: dict[str, Any]) -> dict[str, Any]:
    """Nest wood (true size), foam (= wood), and separately labeled fabric.

    All public measurements are fractions. X-Carve width is capped at 29 1/2"
    with any length via tiling and registration marks.
    """
    raw_parts = payload.get("parts") or payload.get("cut_list") or []
    if not raw_parts:
        raise NestError("cut list has no parts")
    parts = _expand_qty([CutPart.from_payload(p, i) for i, p in enumerate(raw_parts)])

    kerf = _parse_opt(payload.get("kerf") or payload.get("blade_width"), DEFAULT_KERF)
    machine_width = _parse_opt(payload.get("machine_width"), XCARVE_MAX_WIDTH)
    tile_length = _parse_opt(payload.get("tile_length"), XCARVE_TILE_LENGTH)
    sheet_w = _parse_opt(payload.get("sheet_width"), DEFAULT_SHEET_WIDTH)
    sheet_l = _parse_opt(payload.get("sheet_length"), DEFAULT_SHEET_LENGTH)
    foam_w = _parse_opt(payload.get("foam_sheet_width"), DEFAULT_FOAM_SHEET_WIDTH)
    foam_l = _parse_opt(payload.get("foam_sheet_length"), DEFAULT_FOAM_SHEET_LENGTH)
    fabric_w = _parse_opt(payload.get("fabric_usable_width"), DEFAULT_FABRIC_USABLE_WIDTH)

    if sheet_w > machine_width:
        sheet_w = machine_width

    wood_items: list[tuple[CutPart, int, int, str]] = []
    foam_items: list[tuple[CutPart, int, int, str]] = []
    fabric_items: list[tuple[CutPart, int, int, str]] = []
    tiled_sheets: list[NestedSheet] = []
    errors: list[str] = []

    for part in parts:
        if not part.foam_matches_wood():
            errors.append(
                f"{part.name}: foam must equal wood cut "
                f"({format_inches(part.wood_w)} x {format_inches(part.wood_l)})"
            )
            # Still nest the declared wood; foam is forced equal for cutting.
            part.foam_w, part.foam_l = part.wood_w, part.wood_l
        try:
            pw, pl, _ = _fits_machine(part.wood_w, part.wood_l, part.grain, machine_width)
        except NestError as exc:
            errors.append(str(exc))
            continue
        if pl > tile_length:
            tiled_sheets.extend(_tile_long_panel(
                part, pw, pl,
                material="wood",
                tile_length=tile_length,
                max_width=machine_width,
                kerf=kerf,
                start_index=len(tiled_sheets),
            ))
        else:
            wood_items.append((part, pw, pl, "wood"))
        foam_items.append((part, part.foam_w, part.foam_l, "foam"))
        if part.fabric_w is not None and part.fabric_l is not None:
            fabric_items.append((part, part.fabric_w, part.fabric_l, "fabric"))

    wood_sheets = GuillotinePacker(sheet_w, sheet_l, kerf).pack(wood_items) if wood_items else []
    # Re-index tiled wood panels after packed sheets.
    for i, sheet in enumerate(tiled_sheets, start=len(wood_sheets) + 1):
        sheet.index = i
    wood_sheets.extend(tiled_sheets)

    foam_sheets = GuillotinePacker(foam_w, foam_l, 0).pack(foam_items) if foam_items else []
    fabric_sheets = GuillotinePacker(fabric_w, max((p[2] for p in fabric_items), default=fabric_w), 0).pack(fabric_items) if fabric_items else []
    # Fabric packer above uses a single tall roll strip: rebuild as roll length = max y+l.
    if fabric_items:
        fabric_sheets = _pack_fabric_roll(fabric_items, fabric_w)

    cut_list = []
    for part in parts:
        row = {
            "id": part.id,
            "name": part.name,
            "qty": "1",
            "grain": part.grain,
            "notes": part.notes,
            **part.labeled_sizes(),
            "wood_is_true_size": True,
            "foam_equals_wood": True,
            "fabric_is_separate": part.fabric_w is not None,
        }
        cut_list.append(row)

    result = {
        "machine": MACHINE_NAME,
        "machine_width": format_inches(machine_width),
        "tile_length": format_inches(tile_length),
        "kerf": format_inches(kerf),
        "blade_width": format_inches(kerf),
        "job_id": payload.get("job_id"),
        "title": payload.get("title") or "CNC cut list",
        "notes": payload.get("notes") or "",
        "cut_list": cut_list,
        "wood_sheets": [s.as_dict() for s in wood_sheets],
        "foam_sheets": [s.as_dict() for s in foam_sheets],
        "fabric_sheets": [s.as_dict() for s in fabric_sheets],
        "yields": {
            "wood": [_sheet_yield(s) for s in wood_sheets],
            "foam": [_sheet_yield(s) for s in foam_sheets],
            "fabric": [_sheet_yield(s) for s in fabric_sheets],
        },
        "sheet_counts": {
            "wood": str(len(wood_sheets)),
            "foam": str(len(foam_sheets)),
            "fabric": str(len(fabric_sheets)),
        },
        "warnings": errors,
        "checked_out": False,
        "paid": False,
    }
    assert_no_decimal_measurements(result)
    return result


def _sheet_yield(sheet: NestedSheet) -> dict[str, Any]:
    return {
        "index": sheet.index,
        "material": sheet.material,
        "sheet_width": format_inches(sheet.width),
        "sheet_length": format_inches(sheet.length),
        "yield": yield_fraction(sheet.used_area, sheet.total_area),
        "tiled": sheet.tiled,
        "parent_panel": sheet.parent_panel,
    }


def _pack_fabric_roll(items: list[tuple[CutPart, int, int, str]], usable_w: int) -> list[NestedSheet]:
    """Shelf-pack fabric along a roll. Length grows as needed. Grain stays labeled."""
    y = 0
    kerf = 0
    placed: list[PlacedRect] = []
    row_h = 0
    row_x = 0
    for part, w, l, _ in sorted(items, key=lambda it: it[2], reverse=True):
        pw, pl = w, l
        if pw > usable_w and part.grain == "free" and pl <= usable_w:
            pw, pl = pl, w
        if pw > usable_w:
            raise NestError(
                f"Fabric {part.name} width {format_inches(w)} exceeds usable "
                f"{format_inches(usable_w)}"
            )
        if row_x and row_x + pw > usable_w:
            y += row_h
            row_x = 0
            row_h = 0
        placed.append(PlacedRect(
            part_id=part.id,
            name=f"{part.name} FABRIC",
            x=row_x,
            y=y,
            w=pw,
            l=pl,
            rotated=False,
            grain=part.grain,
        ))
        row_x += pw
        row_h = max(row_h, pl)
    total_l = y + row_h
    sheet = NestedSheet(
        index=1,
        material="fabric",
        width=usable_w,
        length=max(total_l, 1),
        kerf=kerf,
    )
    sheet.parts = placed
    return [sheet]
