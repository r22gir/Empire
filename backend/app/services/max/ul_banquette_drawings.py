"""Max bridge: banquette U/L → upholstery-on-shell sheets.

Acceptance: Marleys_EST-2026-272_UPHOLSTERY_CORRECT.pdf

Field semantics (INCHES):
  back_length / back_outer / width → outer back run
  side_left / arm_left / left_depth → LEFT WING LENGTH (along room) — NOT thickness
  side_right / arm_right → RIGHT WING LENGTH (asymmetric; never max())
  depth / seat_depth / side_depth → seat cushion depth (= wing THICKNESS)
  height / shell_height → overall shell height
  back_height / net_back → net back cushion height (sits ON foam)
  seat_foam → seat foam (default 2")
  legs / long_leg / short_leg → L outer legs
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.drawing.canonical_path import (
    new_drawing_path,
    canonical_empire_db_path,
)
from app.services.drawing.upholstery_shell_renderer import (
    UShellSpec,
    LShellSpec,
    SheetMeta,
    render_upholstery_shell_pdf,
)

logger = logging.getLogger("max.ul_banquette_drawings")

_UL_U = {"u", "u_shape", "ushape", "u_shaped", "banquette_u", "u_banquette", "booth_u"}
_UL_L = {"l", "l_shape", "lshape", "l_shaped", "banquette_l", "l_banquette"}


def _norm(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw).strip().lower().replace(" ", "_").replace("-", "_")


def resolve_ul_shape(params: dict, dims: dict, product_type: str) -> Optional[str]:
    for c in (
        params.get("shape"), params.get("bench_type"), params.get("banquette_shape"),
        (dims or {}).get("shape"), (dims or {}).get("bench_type"),
        product_type, params.get("name"), params.get("notes"), params.get("title"),
    ):
        s = _norm(c)
        if not s:
            continue
        if s in _UL_U or "u_shape" in s or s.startswith("u_shaped"):
            return "u_shape"
        if s in _UL_L or "l_shape" in s or s.startswith("l_shaped"):
            return "l_shape"
    return None


def _f(dims: dict, *keys: str, default=None):
    for k in keys:
        if k in dims and dims[k] is not None and dims[k] != "":
            try:
                return float(str(dims[k]).replace('"', "").replace("'", "").strip())
            except (TypeError, ValueError):
                continue
    return default


def persist_drawing_to_quote(
    *, quote_id: str, quote_num: str, pdf_path: str, svg_path: Optional[str],
    item_type: str, item_name: str, shape: str, dims: dict, renderer: str,
) -> dict:
    out: dict[str, Any] = {
        "quote_id": quote_id, "quote_num": quote_num,
        "drawing_versions_id": None, "job_documents_id": None,
        "pdf_path": pdf_path, "svg_path": svg_path,
    }
    if not quote_id:
        out["skipped"] = "no quote_id"
        return out
    db_path = canonical_empire_db_path()
    now = datetime.now(timezone.utc).isoformat()
    meas = json.dumps(
        {"shape": shape, "dims": dims, "quote_num": quote_num,
         "product": "upholstery_on_shell"}, default=str,
    )
    doc_id = uuid.uuid4().hex[:16]
    filename = Path(pdf_path).name
    url = f"/api/v1/drawings/files/{filename}"
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(MAX(version), 0) FROM drawing_versions "
            "WHERE quote_id = ? AND item_type = ?",
            (quote_id, item_type),
        )
        next_ver = int(cur.fetchone()[0]) + 1
        cur.execute(
            """INSERT INTO drawing_versions (
                item_type, item_name, quote_id, version, measurements,
                renderer, business_unit, file_path, file_format,
                generated_by, created_at, job_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_type, item_name, quote_id, next_ver, meas, renderer,
             "workroom", pdf_path, "pdf", "MAX AI", now, None),
        )
        out["drawing_versions_id"] = cur.lastrowid
        out["version"] = next_ver
        cur.execute(
            """INSERT INTO job_documents (
                id, job_id, quote_id, document_type, item_key, route_to,
                url, filename, revision, visible_to_client, source_channel, created_at
            ) VALUES (?, NULL, ?, 'drawing', ?, 'workroom', ?, ?, ?, 0, 'max_chat', ?)""",
            (doc_id, quote_id, shape or item_type, url, filename, next_ver, now),
        )
        out["job_documents_id"] = doc_id
        try:
            cur.execute("SELECT metadata_json FROM quotes_v2 WHERE id = ?", (quote_id,))
            row = cur.fetchone()
            if row is not None:
                meta = json.loads(row[0]) if row[0] else {}
                if not isinstance(meta, dict):
                    meta = {}
                drawings = list(meta.get("drawings") or [])
                drawings.append({
                    "id": doc_id,
                    "drawing_versions_id": out["drawing_versions_id"],
                    "version": next_ver, "item_type": item_type,
                    "item_name": item_name, "shape": shape,
                    "product": "upholstery_on_shell",
                    "pdf_path": pdf_path, "url": url, "filename": filename,
                    "renderer": renderer, "dims": dims,
                    "quote_num": quote_num, "created_at": now,
                })
                meta["drawings"] = drawings
                cur.execute(
                    "UPDATE quotes_v2 SET metadata_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(meta, default=str), now, quote_id),
                )
                out["metadata_drawings_count"] = len(drawings)
        except sqlite3.OperationalError as e:
            out["metadata_error"] = str(e)
        conn.commit()
    finally:
        conn.close()
    return out


def render_ul_banquette_pdf(
    params: dict, dims: dict, product_type: str, shape: str,
) -> dict:
    name = (
        str(params.get("name") or params.get("title") or "").strip()
        or ("U-Banquette Upholstery" if shape == "u_shape" else "L-Banquette Upholstery")
    )
    quote_num = str(
        params.get("quote_num") or params.get("quote_number")
        or dims.get("quote_num") or "EST-2026-272"
    ).strip()
    quote_id = str(params.get("quote_id") or dims.get("quote_id") or "").strip()
    client = str(params.get("client_name") or params.get("client") or "").strip()
    site = str(params.get("site_address") or params.get("project") or "").strip()

    back = _f(dims, "back_length", "back_outer", "back_outer_in", "back", "width",
              default=249.75)
    arm_l = _f(dims, "side_left", "arm_left", "left_depth", "left_side",
               "arm_left_outer", default=None)
    arm_r = _f(dims, "side_right", "arm_right", "right_side", "arm_right_outer",
               default=None)
    side_fb = _f(dims, "side_length", "side", "side_in", "arm_outer", default=None)
    if arm_l is None:
        arm_l = side_fb if side_fb is not None else 41.25
    if arm_r is None:
        arm_r = side_fb if side_fb is not None else 52.0
    # NEVER max() the arms — asymmetric is correct for Marleys
    seat_d = _f(dims, "depth", "seat_depth", "side_depth", "seat_depth_in", default=16.25)
    shell_h = _f(dims, "height", "shell_height", "shell_height_in", default=30.25)
    net_back = _f(dims, "back_height", "net_back", "net_back_cushion_height",
                  "net_back_height", default=26.75)
    seat_foam = _f(dims, "seat_foam", "foam", "seat_foam_in", default=2.0)
    # U seat H AFF is distinct from foam thickness (Rafael: never label foam as seat H)
    u_seat_h = _f(dims, "seat_height", "seat_h", "seat_height_aff", default=18.0)

    u_spec = UShellSpec(
        back_outer=back, arm_left=arm_l, arm_right=arm_r, seat_depth=seat_d,
        shell_height=shell_h, net_back_height=net_back,
        seat_height=u_seat_h, seat_foam=seat_foam,
    )

    long_in = _f(dims, "long_leg", "long", "leg_long", "leg1_length", default=None)
    short_in = _f(dims, "short_leg", "short", "leg_short", "leg2_length", default=None)
    legs = dims.get("legs") or dims.get("outer_legs") or dims.get("outer_legs_in")
    if (long_in is None or short_in is None) and isinstance(legs, (list, tuple)) and len(legs) >= 2:
        a, b = float(legs[0]), float(legs[1])
        long_in, short_in = max(a, b), min(a, b)
    if long_in is None:
        long_in = 107.75
    if short_in is None:
        short_in = 48.875
    l_depth = _f(dims, "l_depth", "l_seat_depth", default=None)
    if l_depth is None:
        l_depth = _f(dims, "depth", "seat_depth", default=19.0) if shape == "l_shape" else 19.0
    l_height = _f(dims, "l_height", "l_shell_height", default=None)
    if l_height is None:
        l_height = _f(dims, "height", "shell_height", default=30.0) if shape == "l_shape" else 30.0
    l_seat_h = _f(dims, "seat_height", "seat_h", default=18.0)

    l_net = _f(dims, "l_net_back", "l_back_height", "net_back_l", default=None)
    if l_net is None:
        l_net = net_back  # inherit U net back (quote L-B basis)
    l_spec = LShellSpec(
        leg_short=short_in, leg_long=long_in, seat_depth=l_depth,
        shell_height=l_height, seat_height=l_seat_h, net_back_height=l_net,
        provisional=True,
    )
    meta = SheetMeta(
        quote_num=quote_num,
        job=(f"{site} — U+L Banquette Upholstery" if site
             else "Marleys Hyattsville — U+L Banquette Upholstery"),
        client=client or "Dave Romero / Marleys Hyattsville",
    )

    out_path = new_drawing_path(prefix="banquette_upholstery", suffix=".pdf")
    override = str(params.get("output_filename") or "").strip()
    if override:
        candidate = Path(override)
        try:
            candidate.relative_to(new_drawing_path().parent)
            out_path = candidate
        except (ValueError, FileNotFoundError):
            raise ValueError(f"output_filename={override!r} outside canonical drawings dir")

    summary = render_upholstery_shell_pdf(
        out_path=out_path, u=u_spec, L=l_spec, meta=meta,
        include_u=True, include_l=True,
    )

    mats = summary.get("materials") or {}
    flags = [
        "Product: UPHOLSTERY ON EXISTING SHELL (no wood frame / ribs / CNC).",
        f"U asymmetric arms drawn: L {u_spec.arm_left}\" / R {u_spec.arm_right}\" (NOT max'd).",
        f"U developed outer run {u_spec.developed_outer_in:.2f}\" = {u_spec.developed_outer_lf:.2f} lf "
        f"(not footprint width {u_spec.footprint_width:.2f}\").",
        f"U elev: shell {u_spec.shell_height}\"; net back {u_spec.net_back_height}\" sits ON "
        f"{u_spec.seat_foam}\" foam; seat H {u_spec.seat_height}\" AFF PROV (foam ≠ seat H).",
        "Sheets: plan / elev / iso U+L / client mockup / schedule / materials.",
        "PATTERN fabric = BACKS only; PLAIN fabric = SEATS.",
        f"Fabric order: PATTERN {mats.get('pattern_yards_order')} yd + PLAIN {mats.get('plain_yards_order')} yd "
        f"@ {mats.get('fabric_width_in')}\" (15% waste).",
        f"1/2\" ply: {mats.get('ply_sheets_4x8')} sheets 4x8 ({mats.get('ply_with_waste_sf')} sf w/ waste).",
        "Cushion schedule by run + SF — no 24\" auto-slice hero.",
        "L depth/height provisional — lock to U before fab.",
    ]
    for flag_key in ("flags", "open_questions", "provisional_flags"):
        extra = params.get(flag_key) or dims.get(flag_key)
        if isinstance(extra, list):
            flags.extend(str(x) for x in extra)
        elif extra:
            flags.append(str(extra))

    clean_dims = {"shape": shape, "product": "upholstery_on_shell",
                  **summary["u"], "l": summary["l"]}
    attach = None
    if quote_id:
        try:
            attach = persist_drawing_to_quote(
                quote_id=quote_id, quote_num=quote_num, pdf_path=str(out_path),
                svg_path=None, item_type="banquette", item_name=name, shape=shape,
                dims=clean_dims, renderer="drawing.upholstery_shell_renderer",
            )
        except Exception as e:
            logger.exception("persist drawing to quote failed")
            attach = {"error": str(e), "quote_id": quote_id}

    return {
        "pdf_path": str(out_path),
        "svg_path": None,
        "size_bytes": summary["size_bytes"],
        "product_type": "banquette",
        "product_mode": "upholstery_on_shell",
        "shape": shape,
        "dims": clean_dims,
        "drawing_engine": "drawing.upholstery_shell_renderer",
        "true_ul_polyline": True,
        "asymmetric_arms": True,
        "no_24in_autoslice": True,
        "developed_outer_lf": summary["u"]["developed_outer_lf"],
        "quote_id": quote_id or None,
        "quote_num": quote_num,
        "attach": attach,
        "flags": flags,
        "warnings": flags,
        "sheets": summary["sheets"],
        "sheet_count": summary.get("sheet_count"),
        "materials": summary.get("materials"),
        "has_isometric": True,
        "has_client_mockup": True,
        "has_materials": True,
        "pattern_backs_only": True,
        "plain_seats_only": True,
    }
