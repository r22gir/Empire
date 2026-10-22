"""Drawing Studio job drawing / revision — generate an internal shop PDF.

Given a job (client / estimate), prior layout or takeoff, and spec changes
(channel width, back/seat fabric as V###-Color), produce a revised drawing.

Rules
-----
- Dimensions come from prior layout / takeoff when estimate lines lack them.
  Never refuse only because the estimate has no dims. Never invent dims.
- Printed sizes are fractions only.
- Wood / foam cut and fabric cut are separately labeled.
  Fabric = wood + 2 × allowance_in for the foam thickness
  (app.config.fabric_cut_allowance).
- Empire Workroom branding. No brand / supplier names on the sheet.
- INTERNAL ONLY — never send to clients.
- Flag conflicts with the estimate; do not silently change prices.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional

from app.config.fabric_cut_allowance import (
    CONFIRM_WITH_RAFAEL,
    NEEDS_FOAM_THICKNESS,
    fabric_dimension_in,
    lookup_fabric_allowance,
)
from app.services.drawing.inches import format_inches
from app.services.vision.bench_cut_list import WOOD_LABEL, FOAM_LABEL, FABRIC_LABEL, format_cut_inches
from app.services.max.job_drawing_intent import (
    DRAWING_DESK_ID,
    extract_job_hint,
    extract_spec_changes,
    is_layout_revision_request,
    merge_drawing_job_context,
)

INTERNAL_STAMP = "INTERNAL ONLY — never send to clients"
EMPIRE_BRAND = "EMPIRE WORKROOM"

_SUPPLIER_MARKERS = (
    "kravet", "robert allen", "fabricut", "schumacher", "duralee",
    "spradling", "apex", "softside", "designtex", "maharam", "knoll",
    "osborne", "little", "stroheim", "bernstein", "supplier",
)

_KNOWN_LAYOUT_PRESETS = {
    "marley": "marleys_u_and_l",
    "marleys": "marleys_u_and_l",
    "marley's": "marleys_u_and_l",
}

_KNOWN_JOB_SETS = {
    "marley": "marleys_u_and_l",
    "marleys": "marleys_u_and_l",
    "marley's": "marleys_u_and_l",
}


def _drawings_dir() -> Path:
    override = (os.getenv("MAX_DRAWINGS_OUTPUT_DIR") or "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    try:
        from app.services.drawing.canonical_path import canonical_drawings_dir
        path = Path(canonical_drawings_dir())
    except Exception:
        path = Path(os.getenv("TMPDIR") or "/tmp") / "empire-job-drawings"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_inches(raw: Any) -> Optional[float]:
    if raw in (None, ""):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if value > 0 else None
    text = str(raw).strip().replace('"', "").replace("in", "").strip()
    mixed = re.match(r"^(\d+)\s+(\d+)\s*/\s*(\d+)$", text)
    if mixed:
        try:
            return float(mixed.group(1)) + float(mixed.group(2)) / float(mixed.group(3))
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    frac = re.match(r"^(\d+)\s*/\s*(\d+)$", text)
    if frac:
        try:
            return float(frac.group(1)) / float(frac.group(2))
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _strip_supplier_names(text: str | None) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    low = cleaned.lower()
    if any(marker in low for marker in _SUPPLIER_MARKERS):
        return ""
    return cleaned


def resolve_internal_fabric(token: str | None, registry_rows: list[dict] | None = None) -> dict[str, Any]:
    """Resolve V###-Color or a color name. Never invent a code. Never expose brand."""
    raw = (token or "").strip()
    if not raw:
        return {"code": None, "color": None, "label": "TBC — CONFIRM BEFORE CUT"}
    rows = registry_rows
    if rows is None:
        try:
            from app.services.fabric_code_catalog import load_registry_rows
            rows = load_registry_rows()
        except Exception:
            rows = []
    from app.services.drawing.mockup_engine.finish import client_facing_label, color_hex_for_name

    code_match = re.match(r"^(V\d{3}-[A-Za-z0-9]+)$", raw, re.I)
    if code_match:
        code = code_match.group(1)
        for row in rows:
            if str(row.get("code") or "").lower() == code.lower():
                color = row.get("color") or code.split("-", 1)[-1]
                mat = row.get("material_type")
                return {
                    "code": row.get("code"),
                    "color": color,
                    "material_type": mat,
                    "hex": color_hex_for_name(str(color)),
                    "label": client_facing_label(code=row.get("code"), color=color, material_type=mat),
                }
        return {"code": None, "color": None, "label": raw, "unknown_code": code}
    color_key = raw.lower()
    hits = [r for r in rows if str(r.get("color") or "").lower() == color_key]
    if len(hits) == 1:
        row = hits[0]
        color = row.get("color")
        mat = row.get("material_type")
        return {
            "code": row.get("code"),
            "color": color,
            "material_type": mat,
            "hex": color_hex_for_name(str(color)),
            "label": client_facing_label(code=row.get("code"), color=color, material_type=mat),
        }
    return {
        "code": None,
        "color": raw,
        "hex": color_hex_for_name(raw),
        "label": client_facing_label(color=raw, material_type="vinyl"),
    }


def _layout_from_mapping(data: dict[str, Any] | None) -> dict[str, Any]:
    src = data or {}
    layout: dict[str, Any] = {}
    aliases = {
        "width_in": ("width_in", "width", "length_in", "length", "overall_width_in"),
        "depth_in": ("depth_in", "depth", "seat_depth_in"),
        "height_in": ("height_in", "height", "overall_height_in"),
        "back_height_in": ("back_height_in", "back_height", "net_back_height_in"),
        "channel_width_in": ("channel_width_in", "channel_width"),
        "foam_thickness_in": ("foam_thickness_in", "foam_thickness", "foam_in"),
        "seat_height_in": ("seat_height_in", "seat_height"),
        "left_in": ("left_in", "left"),
        "right_in": ("right_in", "right"),
        "main_in": ("main_in", "main", "back_run_in"),
        "shape": ("shape", "footprint_shape"),
    }
    for dest, keys in aliases.items():
        for key in keys:
            if key in src and src[key] not in (None, ""):
                if dest == "shape":
                    layout[dest] = str(src[key])
                else:
                    parsed = _parse_inches(src[key])
                    if parsed is not None:
                        layout[dest] = parsed
                break
    return layout


def _preset_layout(job_hint: str | None) -> dict[str, Any]:
    """Prior layout baked into the drawing engine for a known job name."""
    key = (job_hint or "").strip().lower().rstrip("s")
    key = key.replace("'", "")
    preset_name = _KNOWN_LAYOUT_PRESETS.get(key) or _KNOWN_LAYOUT_PRESETS.get((job_hint or "").strip().lower())
    if not preset_name:
        return {}
    try:
        from app.services.drawing.mockup_engine.presets import marleys_u_and_l_preset
        spec = marleys_u_and_l_preset()["u_bench"]
    except Exception:
        return {}
    segs = {s.name.lower(): s.length_in for s in spec.footprint.segments}
    return {
        "source": "prior_layout_preset",
        "preset": preset_name,
        "width_in": segs.get("main"),
        "left_in": segs.get("left"),
        "right_in": segs.get("right"),
        "depth_in": spec.cushion.seat_depth_in,
        "back_height_in": spec.back.net_back_height_in,
        "channel_width_in": spec.back.channel_width_in,
        "seat_height_in": spec.cushion.seat_height_in,
        "foam_thickness_in": spec.footprint.back_thickness_in,
        "shape": spec.footprint.shape,
        "client_name": spec.client_name,
        "project_name": spec.project_name,
        "quote_number": spec.quote_number,
    }


def _quote_layout(quote: dict[str, Any] | None) -> dict[str, Any]:
    if not quote:
        return {}
    for key in ("layout", "takeoff", "drawing_layout", "prior_layout"):
        blob = quote.get(key)
        if isinstance(blob, str):
            try:
                blob = json.loads(blob)
            except (json.JSONDecodeError, TypeError):
                blob = None
        if isinstance(blob, dict) and blob:
            layout = _layout_from_mapping(blob)
            if layout:
                layout["source"] = key
                return layout
    meas = quote.get("measurements")
    if isinstance(meas, str):
        try:
            meas = json.loads(meas)
        except (json.JSONDecodeError, TypeError):
            meas = None
    if isinstance(meas, dict):
        layout = _layout_from_mapping(meas)
        if layout:
            layout["source"] = "measurements"
            return layout
    items = quote.get("line_items") or quote.get("items") or []
    for item in items:
        inp = item.get("inputs") if isinstance(item, dict) else {}
        layout = _layout_from_mapping(inp or item if isinstance(item, dict) else {})
        if layout.get("width_in") or layout.get("left_in") or layout.get("main_in"):
            layout["source"] = "estimate_line"
            return layout
    return {}


def resolve_job_quote(job_hint: str | None) -> Optional[dict[str, Any]]:
    """Look up a quote by number or customer. Isolated test DBs only hold temp rows."""
    hint = (job_hint or "").strip()
    if not hint:
        return None
    try:
        from app.services.quote_service import resolve_quote, list_quotes
    except Exception:
        return None
    quote = resolve_quote(hint)
    if quote:
        return quote
    try:
        listing = list_quotes(limit=200, include_test=True)
    except TypeError:
        listing = list_quotes(limit=200)
    except Exception:
        return None
    rows = listing.get("quotes") if isinstance(listing, dict) else listing
    needle = hint.lower()
    for row in rows or []:
        name = str(row.get("customer_name") or "").lower()
        project = str(row.get("project_name") or "").lower()
        number = str(row.get("quote_number") or "").lower()
        if needle in name or needle in project or needle in number:
            return row
    return None


def _estimate_channel_width(quote: dict[str, Any] | None) -> Optional[float]:
    if not quote:
        return None
    for item in quote.get("line_items") or quote.get("items") or []:
        if not isinstance(item, dict):
            continue
        inp = item.get("inputs") or item
        for key in ("channel_width_in", "channel_width"):
            parsed = _parse_inches(inp.get(key))
            if parsed is not None:
                return parsed
        blob = " ".join(str(item.get(k) or "") for k in ("description", "name", "notes"))
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\"|in)?\s*channel", blob, re.I)
        if match:
            return _parse_inches(match.group(1))
    return None


def build_cut_list(
    *,
    width_in: float,
    depth_in: float,
    back_height_in: float,
    channel_width_in: float,
    foam_thickness_in: Optional[float],
) -> dict[str, Any]:
    """Wood / foam (same size) and fabric (wood + 2× allowance) as labeled sizes."""
    allowance = lookup_fabric_allowance(foam_thickness_in)
    extra = allowance.get("allowance_in")
    wood_channel = {
        "part": "Channel back",
        "kind": "wood",
        "label": WOOD_LABEL,
        "width": channel_width_in,
        "length": back_height_in,
        "size": f"{format_cut_inches(channel_width_in)} × {format_cut_inches(back_height_in)}",
    }
    foam_channel = {
        "part": "Channel back",
        "kind": "foam",
        "label": FOAM_LABEL,
        "width": channel_width_in,
        "length": back_height_in,
        "size": f"{format_cut_inches(channel_width_in)} × {format_cut_inches(back_height_in)}",
    }
    wood_seat = {
        "part": "Seat cushion",
        "kind": "wood",
        "label": WOOD_LABEL,
        "width": depth_in,
        "length": width_in,
        "size": f"{format_cut_inches(depth_in)} × {format_cut_inches(width_in)}",
    }
    foam_seat = {
        "part": "Seat cushion",
        "kind": "foam",
        "label": FOAM_LABEL,
        "width": depth_in,
        "length": width_in,
        "size": f"{format_cut_inches(depth_in)} × {format_cut_inches(width_in)}",
    }
    if extra is None:
        fabric_channel = {
            "part": "Channel back",
            "kind": "fabric",
            "label": FABRIC_LABEL,
            "width": None,
            "length": None,
            "size": NEEDS_FOAM_THICKNESS,
            "note": allowance.get("label") or NEEDS_FOAM_THICKNESS,
        }
        fabric_seat = {
            "part": "Seat cushion",
            "kind": "fabric",
            "label": FABRIC_LABEL,
            "width": None,
            "length": None,
            "size": NEEDS_FOAM_THICKNESS,
            "note": allowance.get("label") or NEEDS_FOAM_THICKNESS,
        }
    else:
        fab_ch_w = fabric_dimension_in(channel_width_in, extra)
        fab_ch_l = fabric_dimension_in(back_height_in, extra)
        fab_seat_w = fabric_dimension_in(depth_in, extra)
        fab_seat_l = fabric_dimension_in(width_in, extra)
        note = ""
        if allowance.get("status") == CONFIRM_WITH_RAFAEL:
            note = "(allowance unconfirmed)"
        fabric_channel = {
            "part": "Channel back",
            "kind": "fabric",
            "label": FABRIC_LABEL,
            "width": fab_ch_w,
            "length": fab_ch_l,
            "size": f"{format_cut_inches(fab_ch_w)} × {format_cut_inches(fab_ch_l)}",
            "note": note,
        }
        fabric_seat = {
            "part": "Seat cushion",
            "kind": "fabric",
            "label": FABRIC_LABEL,
            "width": fab_seat_w,
            "length": fab_seat_l,
            "size": f"{format_cut_inches(fab_seat_w)} × {format_cut_inches(fab_seat_l)}",
            "note": note,
        }
    return {
        "wood": [wood_channel, wood_seat],
        "foam": [foam_channel, foam_seat],
        "fabric": [fabric_channel, fabric_seat],
        "allowance": allowance,
        "foam_thickness_in": foam_thickness_in,
    }


def _conflicts(layout: dict[str, Any], spec_changes: dict[str, Any], quote: dict[str, Any] | None) -> list[str]:
    flags: list[str] = []
    requested = spec_changes.get("channel_width_in")
    estimate_ch = _estimate_channel_width(quote)
    if requested is not None and estimate_ch is not None and abs(float(requested) - float(estimate_ch)) > 0.01:
        flags.append(
            f"Channel width {format_inches(requested)} conflicts with estimate "
            f"{format_inches(estimate_ch)} — flagged, prices not changed."
        )
    prior_ch = layout.get("channel_width_in")
    if requested is not None and prior_ch is not None and abs(float(requested) - float(prior_ch)) > 0.01:
        flags.append(
            f"Channel width revised from {format_inches(prior_ch)} to {format_inches(requested)} "
            "(layout only; estimate prices unchanged)."
        )
    return flags


def _has_dims(layout: dict[str, Any]) -> bool:
    return bool(
        layout.get("width_in")
        or layout.get("main_in")
        or (layout.get("left_in") and layout.get("right_in"))
    )


def resolve_layout(
    *,
    job_hint: str | None,
    quote: dict[str, Any] | None,
    layout_data: dict[str, Any] | None,
    takeoff: dict[str, Any] | None,
) -> dict[str, Any]:
    """Pick dimensions from explicit layout, takeoff, quote, then known prior layout."""
    for source, blob in (
        ("caller_layout", layout_data),
        ("takeoff", takeoff),
    ):
        layout = _layout_from_mapping(blob)
        if _has_dims(layout):
            layout["source"] = source
            return layout
    quoted = _quote_layout(quote)
    if _has_dims(quoted):
        return quoted
    preset = _preset_layout(job_hint)
    if _has_dims(preset):
        return preset
    if quoted:
        return quoted
    return preset or {}


def _piece_spec(layout: dict[str, Any], spec_changes: dict[str, Any], fabrics: dict[str, Any], quote: dict[str, Any] | None):
    from app.services.drawing.mockup_engine.spec import (
        PieceSpec, FootprintSpec, SegmentSpec, BackStyleSpec, CushionSpec, MaterialFinishSpec,
    )

    width = layout.get("width_in") or layout.get("main_in") or 0.0
    left = layout.get("left_in")
    right = layout.get("right_in")
    depth = layout.get("depth_in") or 16.0
    back_h = layout.get("back_height_in") or 26.75
    channel = spec_changes.get("channel_width_in") or layout.get("channel_width_in") or 12.0
    shape = str(layout.get("shape") or ("u_shape" if left and right else "straight"))
    if shape in ("u_shape", "u") and left and right:
        footprint = FootprintSpec(
            shape="u_shape",
            segments=[
                SegmentSpec(name="left", length_in=float(left)),
                SegmentSpec(name="main", length_in=float(width or layout.get("main_in") or 0)),
                SegmentSpec(name="right", length_in=float(right)),
            ],
            back_thickness_in=float(layout.get("foam_thickness_in") or 2.0),
        )
    else:
        footprint = FootprintSpec(
            shape="straight",
            segments=[SegmentSpec(name="main", length_in=float(width or 0))],
            overall_width_in=float(width or 0),
            back_thickness_in=float(layout.get("foam_thickness_in") or 2.0),
        )
    from app.services.drawing.mockup_engine.finish import apply_seat_back_finish, color_hex_for_name

    back_label = fabrics.get("back", {}).get("label") or "TBC"
    seat_label = fabrics.get("seat", {}).get("label") or "TBC"
    back_color = str(fabrics.get("back", {}).get("color") or back_label)
    seat_color = str(fabrics.get("seat", {}).get("color") or "")
    client = (quote or {}).get("customer_name") or layout.get("client_name") or "Client"
    project = (quote or {}).get("project_name") or layout.get("project_name") or "Job drawing"
    number = (quote or {}).get("quote_number") or layout.get("quote_number") or ""
    material = MaterialFinishSpec(
        material_type="vinyl",
        name=back_label,
        color_name=back_color,
        color_hex=fabrics.get("back", {}).get("hex") or color_hex_for_name(back_color),
        seat_color_name=seat_color,
        seat_color_hex=(
            fabrics.get("seat", {}).get("hex")
            or (color_hex_for_name(seat_color) if seat_color else "#A8693A")
        ),
        fabric_code=fabrics.get("back", {}).get("code"),
        seat_fabric_code=fabrics.get("seat", {}).get("code"),
    )
    apply_seat_back_finish(material, back=fabrics.get("back") or {}, seat=fabrics.get("seat") or {})
    return PieceSpec(
        name=project or f"{client} drawing",
        piece_type="banquette",
        client_name=client,
        project_name=project,
        quote_number=number or "INTERNAL",
        status="INTERNAL ONLY",
        business_unit="workroom",
        footprint=footprint,
        back=BackStyleSpec(
            style="channel",
            channel_width_in=float(channel),
            net_back_height_in=float(back_h),
        ),
        cushion=CushionSpec(
            seat_depth_in=float(depth),
            seat_height_in=float(layout.get("seat_height_in") or 18.0),
            cushion_thickness_in=float(layout.get("cushion_thickness_in") or 4.0),
        ),
        material=material,
        notes=[
            INTERNAL_STAMP,
            f"Back fabric: {back_label}",
            f"Seat fabric: {seat_label}",
            "Wood / foam cut and fabric cut are labeled separately.",
        ],
    )


def _write_shop_pdf(
    *,
    path: Path,
    spec_notes: list[str],
    layout: dict[str, Any],
    cuts: dict[str, Any],
    fabrics: dict[str, Any],
    conflicts: list[str],
    client: str,
    project: str,
) -> None:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas

    W, H = landscape(letter)
    c = canvas.Canvas(str(path), pagesize=landscape(letter))
    try:
        c._doc.compression = 0
    except Exception:
        pass
    ink = HexColor("#20241f")
    paper = HexColor("#f7f3ea")
    gold = HexColor("#b8912f")
    c.setFillColor(paper)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(ink)
    c.rect(0, H - 36, W, 36, fill=1, stroke=0)
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(24, H - 24, f"{EMPIRE_BRAND}  ·  SHOP DRAWING")
    c.setFillColor(HexColor("#f7f3ea"))
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(W - 24, H - 24, INTERNAL_STAMP)
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(24, H - 60, project or "Job drawing")
    c.setFont("Helvetica", 10)
    c.drawString(24, H - 76, f"Client: {client}    {INTERNAL_STAMP}")
    y = H - 100
    c.setFont("Helvetica-Bold", 10)
    c.drawString(24, y, "Dimensions (fractions only — from prior layout / takeoff)")
    y -= 16
    c.setFont("Helvetica", 9)
    dim_lines = [
        ("Channel width", layout.get("channel_width_in")),
        ("Seat depth", layout.get("depth_in")),
        ("Back height", layout.get("back_height_in")),
        ("Main / width", layout.get("width_in") or layout.get("main_in")),
        ("Left", layout.get("left_in")),
        ("Right", layout.get("right_in")),
        ("Foam thickness", layout.get("foam_thickness_in")),
    ]
    for label, value in dim_lines:
        if value in (None, ""):
            continue
        c.drawString(32, y, f"{label}: {format_inches(float(value))}")
        y -= 13
    y -= 8
    c.setFont("Helvetica-Bold", 10)
    c.drawString(24, y, "Fabrics (internal codes only)")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(32, y, f"Seat backs: {fabrics.get('back', {}).get('label')}")
    y -= 13
    c.drawString(32, y, f"Seat cushion: {fabrics.get('seat', {}).get('label')}")
    y -= 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(24, y, "Cut list — wood / foam vs fabric (separately labeled)")
    y -= 14
    c.setFont("Helvetica", 8)
    for group in ("wood", "foam", "fabric"):
        for part in cuts.get(group) or []:
            note = f"  {part.get('note')}" if part.get("note") else ""
            line = f"{part.get('label')}: {part.get('part')}  {part.get('size')}{note}"
            c.drawString(32, y, line[:110])
            y -= 12
    if conflicts:
        y -= 8
        c.setFont("Helvetica-Bold", 10)
        c.drawString(24, y, "Estimate conflicts (prices not changed)")
        y -= 14
        c.setFont("Helvetica", 8)
        for flag in conflicts:
            c.drawString(32, y, flag[:110])
            y -= 12
    for note in spec_notes:
        if y < 48:
            break
        cleaned = _strip_supplier_names(note) or note
        if any(m in cleaned.lower() for m in _SUPPLIER_MARKERS):
            continue
        c.drawString(32, y, cleaned[:110])
        y -= 11
    c.setFillColor(ink)
    c.rect(0, 0, W, 28, fill=1, stroke=0)
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(24, 12, f"{EMPIRE_BRAND}  ·  {INTERNAL_STAMP}")
    c.setTitle(f"{EMPIRE_BRAND} SHOP DRAWING {INTERNAL_STAMP}")
    c.save()


def _try_mockup_pdf(spec, path: Path) -> bool:
    try:
        from app.services.drawing.mockup_engine.generator import render_piece_mockup_pdf
        render_piece_mockup_pdf(spec, str(path))
        return path.exists() and path.stat().st_size > 80
    except Exception:
        return False


def _normalize_job_key(job_hint: str | None) -> str:
    key = (job_hint or "").strip().lower().rstrip("s")
    return key.replace("'", "")


def _job_set_name(job_hint: str | None) -> Optional[str]:
    raw = (job_hint or "").strip().lower()
    key = _normalize_job_key(job_hint)
    return _KNOWN_JOB_SETS.get(key) or _KNOWN_JOB_SETS.get(raw)


def _apply_revision_to_preset(spec, spec_changes: dict[str, Any], fabrics: dict[str, Any], *, revision: str, sheet_date: str):
    from app.services.drawing.mockup_engine.finish import apply_seat_back_finish

    piece = spec.model_copy(deep=True)
    channel = spec_changes.get("channel_width_in")
    if channel is not None:
        piece.back.channel_width_in = float(channel)
        piece.back.style = "channel"
    apply_seat_back_finish(piece.material, back=fabrics.get("back") or {}, seat=fabrics.get("seat") or {})
    piece.revision = revision
    piece.sheet_date = sheet_date
    back_label = (fabrics.get("back") or {}).get("label")
    seat_label = (fabrics.get("seat") or {}).get("label")
    notes = list(piece.notes or [])
    if back_label:
        notes.append(f"Back fabric: {back_label}")
    if seat_label:
        notes.append(f"Seat fabric: {seat_label}")
    piece.notes = notes
    return piece


def _job_piece_specs(
    *,
    job_hint: str | None,
    layout: dict[str, Any],
    spec_changes: dict[str, Any],
    fabrics: dict[str, Any],
    quote: dict[str, Any] | None,
    revision: str,
    sheet_date: str,
) -> list:
    set_name = _job_set_name(job_hint)
    if set_name == "marleys_u_and_l":
        from app.services.drawing.mockup_engine.presets import marleys_u_and_l_preset
        presets = marleys_u_and_l_preset()
        return [
            _apply_revision_to_preset(presets["u_bench"], spec_changes, fabrics, revision=revision, sheet_date=sheet_date),
            _apply_revision_to_preset(presets["l_bench"], spec_changes, fabrics, revision=revision, sheet_date=sheet_date),
        ]
    spec = _piece_spec(layout, spec_changes, fabrics, quote)
    spec.revision = revision
    spec.sheet_date = sheet_date
    return [spec]


def _next_revision(out_dir: Path, slug: str) -> int:
    highest = 0
    if out_dir.exists():
        for path in out_dir.glob(f"*{slug}*"):
            match = re.search(r"rev(\d+)", path.name, re.I)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def _revision_filename(slug: str, revision: int, sheet_date: str, nonce: str) -> str:
    day = sheet_date.replace("-", "")
    return f"mockup_{slug}_rev{revision}_{day}_{nonce}.pdf"


def generate_job_drawing(
    *,
    message: str = "",
    history: Any = None,
    job_hint: str | None = None,
    quote: dict[str, Any] | None = None,
    layout_data: dict[str, Any] | None = None,
    takeoff: dict[str, Any] | None = None,
    spec_changes: dict[str, Any] | None = None,
    output_dir: str | Path | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Build a revised drawing PDF for a job. Always a new file. Temp data only in tests."""
    from datetime import date as _date
    import time as _time
    from app.services.max.drawing_share import (
        attach_share_proof,
        is_drawing_ready_followup,
        last_drawing,
        remember_drawing,
        remember_key,
        verify_generated_file,
    )

    ctx = merge_drawing_job_context(message, history)
    hint = job_hint or ctx.get("job_hint") or extract_job_hint(message)
    store_key = remember_key(conversation_id, hint, history)
    if is_drawing_ready_followup(message, history) and not is_layout_revision_request(message):
        remembered = last_drawing(store_key)
        if remembered and remembered.get("pdf_path"):
            proof = verify_generated_file(
                remembered["pdf_path"],
                min_mtime=float(remembered.get("pdf_mtime") or 0) - 0.5,
            )
            if proof.get("ok"):
                remembered = dict(remembered)
                remembered["reused_just_generated"] = True
                return remembered
    changes = dict(ctx.get("spec_changes") or {})
    if spec_changes:
        changes.update(spec_changes)
    if quote is None:
        quote = resolve_job_quote(hint)
    layout = resolve_layout(
        job_hint=hint,
        quote=quote,
        layout_data=layout_data,
        takeoff=takeoff,
    )
    if changes.get("channel_width_in") is not None:
        layout = dict(layout)
        layout["channel_width_in"] = changes["channel_width_in"]
    if not _has_dims(layout):
        return {
            "success": False,
            "error": (
                "No layout or takeoff dimensions for this job. "
                "Estimate lines also lack dims — I will not invent sizes."
            ),
            "missing": ["prior_layout_or_takeoff"],
            "desk": DRAWING_DESK_ID,
            "internal_only": True,
        }
    width = float(layout.get("width_in") or layout.get("main_in") or 0)
    depth = float(layout.get("depth_in") or 0)
    back_h = float(layout.get("back_height_in") or 0)
    channel = float(changes.get("channel_width_in") or layout.get("channel_width_in") or 0)
    foam = layout.get("foam_thickness_in")
    if not width or not depth or not back_h or not channel:
        # Prior layout may be a U with left/right and no single width — still usable.
        if not width and layout.get("left_in") and layout.get("right_in") and layout.get("main_in"):
            width = float(layout["main_in"])
        if not depth or not back_h or not channel:
            return {
                "success": False,
                "error": (
                    "Prior layout is incomplete "
                    f"(width={width}, depth={depth}, back={back_h}, channel={channel}). "
                    "Will not invent the missing size."
                ),
                "missing": [k for k, v in (
                    ("width_in", width), ("depth_in", depth),
                    ("back_height_in", back_h), ("channel_width_in", channel),
                ) if not v],
                "desk": DRAWING_DESK_ID,
                "internal_only": True,
            }

    back_token = changes.get("back_fabric")
    seat_token = changes.get("seat_fabric")
    codes = list(changes.get("fabric_codes") or [])
    if codes and not back_token:
        back_token = codes[0]
    if len(codes) > 1 and not seat_token:
        seat_token = codes[1]
    fabrics = {
        "back": resolve_internal_fabric(back_token),
        "seat": resolve_internal_fabric(seat_token),
    }
    cuts = build_cut_list(
        width_in=width,
        depth_in=depth,
        back_height_in=back_h,
        channel_width_in=channel,
        foam_thickness_in=foam,
    )
    conflicts = _conflicts(layout, changes, quote)
    client = (quote or {}).get("customer_name") or layout.get("client_name") or hint or "Client"
    project = (quote or {}).get("project_name") or layout.get("project_name") or f"{client} drawing"
    out_dir = Path(output_dir) if output_dir else _drawings_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_date = _date.today().isoformat()
    job_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (hint or "job")).strip("_").lower() or "job"
    revision = _next_revision(out_dir, job_slug)
    nonce = uuid.uuid4().hex[:8]
    pdf_name = _revision_filename(job_slug, revision, sheet_date, nonce)
    pdf_path = out_dir / pdf_name
    if pdf_path.exists():
        nonce = uuid.uuid4().hex[:10]
        pdf_name = _revision_filename(job_slug, revision, sheet_date, nonce)
        pdf_path = out_dir / pdf_name

    pieces = _job_piece_specs(
        job_hint=hint,
        layout=layout,
        spec_changes=changes,
        fabrics=fabrics,
        quote=quote,
        revision=str(revision),
        sheet_date=sheet_date,
    )
    t0 = _time.time()
    mockup_ok = False
    try:
        from app.services.drawing.mockup_engine.generator import render_job_set_mockup_pdf
        render_job_set_mockup_pdf(
            pieces, str(pdf_path), date_str=sheet_date, revision=str(revision),
        )
        mockup_ok = pdf_path.exists() and pdf_path.stat().st_size > 80
    except Exception:
        mockup_ok = False
    if not mockup_ok:
        shop_path = out_dir / f"job_drawing_{job_slug}_rev{revision}_{nonce}.pdf"
        _write_shop_pdf(
            path=shop_path,
            spec_notes=[INTERNAL_STAMP],
            layout={**layout, "channel_width_in": channel, "depth_in": depth, "back_height_in": back_h, "width_in": width},
            cuts=cuts,
            fabrics=fabrics,
            conflicts=conflicts,
            client=client,
            project=project,
        )
        pdf_path = shop_path

    size = pdf_path.stat().st_size if pdf_path.exists() else 0
    if size < 80:
        return {
            "success": False,
            "error": "Drawing engine did not write a PDF.",
            "desk": DRAWING_DESK_ID,
            "internal_only": True,
        }
    result = {
        "success": True,
        "desk": DRAWING_DESK_ID,
        "desk_label": "Kai (ForgeDesk / Drawing Studio)",
        "internal_only": True,
        "never_send_to_clients": True,
        "job_hint": hint,
        "client_name": client,
        "project_name": project,
        "quote_number": (quote or {}).get("quote_number"),
        "layout_source": layout.get("source"),
        "revision": revision,
        "sheet_date": sheet_date,
        "piece_count": len(pieces),
        "piece_names": [getattr(p, "name", "") for p in pieces],
        "dimensions": {
            "width": format_inches(width),
            "depth": format_inches(depth),
            "back_height": format_inches(back_h),
            "channel_width": format_inches(channel),
        },
        "fabrics": fabrics,
        "cut_list": cuts,
        "estimate_conflicts": conflicts,
        "pdf_path": str(pdf_path.resolve()),
        "pdf_filename": pdf_path.name,
        "generated_at": t0,
        "branding": EMPIRE_BRAND,
        "stamp": INTERNAL_STAMP,
    }
    attach_share_proof(result, pdf_path, min_mtime=t0)
    link = result.get("share_url") or result.get("markdown_link") or pdf_path.name
    result["message"] = (
        f"New drawing for {client}: {link}. "
        f"REV {revision} · {sheet_date}. {INTERNAL_STAMP}"
        + (f" Conflicts: {'; '.join(conflicts)}" if conflicts else "")
    )
    remember_drawing(store_key, result)
    return result


def founder_drawing_reply(result: dict[str, Any]) -> str:
    """Short founder-facing line with the just-generated share URL. Never a pipeline dump."""
    if not result:
        return "Drawing desk failed: no result."
    if result.get("success"):
        url = result.get("share_url") or ""
        name = result.get("pdf_filename") or "drawing.pdf"
        if url:
            return result.get("message") or f"New drawing: [{name}]({url})"
        return result.get("message") or f"New drawing: {name}"
    return f"Drawing desk could not finish: {result.get('error') or 'unknown error'}."


def run_job_drawing_turn(
    message: str,
    history: Any = None,
    job_hint: str | None = None,
    conversation_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Chat / stream entry: classify then generate. Used by both /chat doors."""
    from app.services.max.job_drawing_intent import should_route_to_drawing_desk
    from app.services.max.drawing_share import is_drawing_ready_followup

    if not should_route_to_drawing_desk(message, history) and not is_drawing_ready_followup(message, history):
        return {"handled": False}
    result = generate_job_drawing(
        message=message,
        history=history,
        job_hint=job_hint,
        conversation_id=conversation_id,
        **kwargs,
    )
    return {
        "handled": True,
        "success": bool(result.get("success")),
        "response": founder_drawing_reply(result),
        "result": result,
        "model_used": "drawing-desk",
        "desk": DRAWING_DESK_ID,
    }
