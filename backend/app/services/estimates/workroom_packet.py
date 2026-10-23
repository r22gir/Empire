"""Build a draft estimate and presentation from openings. Nothing is sent."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold
from app.services.estimates.rafael_format import (
    AREA_MAIN_DRAPERY,
    AREA_SHEERS,
    FORMAT_ID,
    GROUP_INSTALLATION,
    GROUP_LABOR,
    GROUP_MATERIALS,
    GROUP_ORDER,
    apply_client,
    willard_metadata,
)
from app.services.pricing.dimensions import format_inches_plain
from app.services.pricing.workroom_rules import (
    ceil_yards,
    cut_length,
    lining_yards,
    new_fab_widths,
    panel_widths,
    rule,
    sheer_widths,
    track_feet,
)

_GROUP_ORDER = GROUP_ORDER
_PACKET_RE = re.compile(
    r"\b(estimate|quote)\b.{0,80}\bpresentation\b|\bpresentation\b.{0,80}\b(estimate|quote)\b",
    re.I | re.S,
)
_FOUNDER_RE = re.compile(r"\brafael(\s+giraldo)?\b", re.I)


def wants_packet(message: str | None) -> bool:
    return bool(_PACKET_RE.search(message or ""))


def _money(value: float) -> float:
    """Half-up cents (853.125 → 853.13). Avoids banker's 1-cent drift."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _widths_label(value: float) -> str:
    text = format_inches_plain(value)
    return text[:-1] if text.endswith('"') else text


def _inches(value, default: float | None = None) -> float:
    if value in (None, ""):
        if default is None:
            raise KeyError("width")
        return float(default)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    from app.services.workroom_quote_commerce import parse_fraction_inches
    parsed = parse_fraction_inches(value)
    if parsed == 0 and default is not None and str(value).strip() not in {"0", "0\"", "0.0"}:
        return float(default)
    return parsed


def is_new_fabrication(opening: dict) -> bool:
    """True for new lined drapery / sheers. Re-line stays the other path."""
    if opening.get("reline") in (True, "true", "True", 1, "1"):
        return False
    kind = str(
        opening.get("fabrication")
        or opening.get("job_type")
        or opening.get("work")
        or ""
    ).strip().lower().replace("-", "_").replace(" ", "_")
    if kind in {"new", "new_fab", "new_fabrication", "fabrication", "ripplefold"}:
        return True
    if opening.get("new_fabrication") in (True, "true", "True", 1, "1"):
        return True
    if opening.get("new_fab") in (True, "true", "True", 1, "1"):
        return True
    if opening.get("reline") in (False, "false", "False", 0, "0"):
        return True
    return False


def _line(
    group: str,
    description: str,
    qty: float,
    rate: float | None,
    unit: str = "ea",
    item: str = "",
    *,
    com: bool = False,
    area: str = "",
) -> dict:
    desc = _FOUNDER_RE.sub("", description).strip()
    if com or rate is None:
        return {
            "group": group,
            "item": item,
            "description": desc,
            "quantity": qty,
            "unit": unit,
            "rate": None,
            "base_rate": None,
            "amount": None,
            "base_amount": None,
            "client_amount": None,
            "com": True,
            "area": area,
        }
    amount = _money(float(qty) * float(rate))
    return {
        "group": group,
        "item": item,
        "description": desc,
        "quantity": qty,
        "unit": unit,
        "rate": float(rate),
        "base_rate": float(rate),
        "amount": amount,
        "base_amount": amount,
        "com": False,
        "area": area,
    }


def _track_install_lines(
    *,
    width_in: float,
    area: str,
    layer: str,
    include_track: bool,
    include_install: bool,
    install_flat=None,
) -> list[dict]:
    """Complete track per ft (carriers included) + prorated install. Never hourly."""
    lines: list[dict] = []
    feet = track_feet(width_in)
    track_rate = rule("track_per_8ft") / rule("install_section_ft")
    install_rate = rule("install_per_8ft") / rule("install_section_ft")
    if include_track:
        lines.append(_line(
            GROUP_MATERIALS,
            (
                f"Complete ripplefold track, {feet:g} ft prorated"
                f" - parts, overlap master carriers included"
            ),
            feet,
            track_rate,
            "ft",
            item="Track",
            area=area,
        ))
    if include_install:
        if install_flat not in (None, ""):
            lines.append(_line(
                GROUP_INSTALLATION,
                f"Removal and installation - {layer} track, flat",
                1,
                float(install_flat),
                item="Install",
                area=area,
            ))
        else:
            lines.append(_line(
                GROUP_INSTALLATION,
                f"Removal and installation - {layer} track, {feet:g} ft prorated",
                feet,
                install_rate,
                "ft",
                item="Install",
                area=area,
            ))
    return lines


def wants_bump(opening: dict) -> bool:
    """Re-line with bump is the default. ``bump: false`` (or ``reline_type`` "no_bump" /
    "lining_only") prices "Re-line with lining (no bump)": lining only, no bump material,
    labor at ``reline_no_bump_per_width``. Widths are counted exactly as for the standard re-line."""
    kind = str(opening.get("reline_type") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if kind in {"no_bump", "lining_only", "without_bump", "lining_no_bump"}:
        return False
    return opening.get("bump", True) not in (False, "false", "no", 0, "0")


def _groups_for(area_lines: list[dict]) -> list[dict]:
    groups = []
    for name in _GROUP_ORDER:
        grouped = [row for row in area_lines if row["group"] == name]
        if not grouped:
            continue
        groups.append({
            "name": name,
            "lines": grouped,
            "subtotal": round(sum(float(row.get("amount") or 0) for row in grouped), 2),
        })
    return groups


def _finish_opening(opening: dict, lines: list[dict], *, cloth: dict, cut: float, yards: float,
                    bump: bool, sheer_job, width: float, height: float, panels: int,
                    main_area: str, sheer_area: str, room: str) -> dict:
    for row in lines:
        if not row.get("area"):
            desc = str(row.get("description") or "")
            row["area"] = sheer_area if re.search(r"\bsheer", desc, re.I) else main_area
        row["room"] = room
        if row.get("com") or row.get("amount") is None:
            row["client_amount"] = None
        else:
            row["client_amount"] = apply_client(row["amount"], opening)
    main_lines = [row for row in lines if row["area"] != sheer_area and "sheer" not in str(row.get("area") or "").lower()]
    sheer_lines = [row for row in lines if row not in main_lines]
    # Prefer explicit area tags
    main_lines = [row for row in lines if row.get("area") == main_area]
    sheer_lines = [row for row in lines if row.get("area") == sheer_area]
    leftover = [row for row in lines if row not in main_lines and row not in sheer_lines]
    for row in leftover:
        (sheer_lines if re.search(r"\bsheer", str(row.get("description") or ""), re.I) else main_lines).append(row)
    areas = []
    if main_lines:
        groups = _groups_for(main_lines)
        areas.append({
            "name": main_area,
            "room": room,
            "groups": groups,
            "subtotal": round(sum(g["subtotal"] for g in groups), 2),
        })
    if sheer_lines:
        groups = _groups_for(sheer_lines)
        areas.append({
            "name": sheer_area,
            "room": room,
            "groups": groups,
            "subtotal": round(sum(g["subtotal"] for g in groups), 2),
        })
    groups = _groups_for(lines)
    return {
        "room": room,
        "mark": opening.get("mark") or "",
        "width": width,
        "height": height,
        "panels": panels,
        "widths": cloth,
        "cut_length": cut,
        "yards": yards,
        "bump": bump,
        "sheer": sheer_job,
        "areas": areas,
        "groups": groups,
        "subtotal": round(sum(a["subtotal"] for a in areas), 2),
        "opening": opening,
        "new_fabrication": is_new_fabrication(opening),
    }


def _price_new_fabrication(opening: dict) -> dict:
    """Lined main drapery + sheers: 2.5× fullness / 54\" (or 110\" sheer) goods."""
    room = str(opening.get("room") or "Room")
    width = _inches(opening["width"])
    height = _inches(opening.get("height") or opening.get("finished_length") or opening.get("fl") or 0)
    finished = _inches(opening.get("finished_length") or opening.get("fl"), height)
    panels = int(opening.get("panels") or 2)
    control = str(opening.get("control") or opening.get("draw") or "center")
    fullness = opening.get("fullness", rule("new_fab_fullness"))
    goods = _inches(opening.get("goods_width") or opening.get("goods"), rule("new_fab_goods_width_in"))
    cloth = new_fab_widths(width, fullness=fullness, goods_in=goods, panels=panels)
    cut = finished + rule("hem_allowance_in")
    yards = ceil_yards(cloth["total"], cut)
    labor_rate = rule("new_fab_per_width")
    baton_rate = rule("baton_fiberglass_each")
    main_area = str(opening.get("area") or "").strip() or (
        f"A. MAIN DRAPERY ({format_inches_plain(width)} opening)"
    )
    sheer = opening.get("sheers") or None
    sheer_cov = 0.0
    if sheer:
        sheer_cov = _inches(sheer.get("coverage") or sheer.get("coverage_width") or 0)
    sheer_area = str((sheer or {}).get("area") or opening.get("sheer_area") or "").strip() or (
        f"B. SHEERS ({format_inches_plain(sheer_cov)} coverage)" if sheer else AREA_SHEERS
    )
    lines: list[dict] = []
    per_panel = cloth["per_panel"]
    per_panel_label = int(per_panel) if abs(per_panel - int(per_panel)) < 1e-6 else per_panel
    lines.append(_line(
        GROUP_LABOR,
        (
            f"Main ripplefold drapery fabrication, lined, {control} draw, "
            f"FL {format_inches_plain(finished)} - {panels} panels x {per_panel_label} widths"
        ),
        cloth["total"],
        labor_rate,
        "widths",
        item="Drapes",
        area=main_area,
    ))
    if opening.get("com", True):
        lines.append(_line(
            GROUP_MATERIALS,
            f"Face fabric - {yards:g} yd - COM - customer-owned material, provided by client",
            yards,
            None,
            "yd",
            item="Fabric",
            com=True,
            area=main_area,
        ))
    lining_label = str(opening.get("lining_label") or "Light white satin lining, premium")
    lines.append(_line(
        GROUP_MATERIALS,
        f"{lining_label} - {cloth['total']:g} widths x {format_inches_plain(cut)} cut",
        yards,
        rule("lining_per_yard"),
        "yd",
        item="Lining",
        area=main_area,
    ))
    want_track = opening.get("track", True) not in (False, "false", 0, "0")
    want_install = opening.get("install", True) not in (False, "false", 0, "0")
    lines.extend(_track_install_lines(
        width_in=width,
        area=main_area,
        layer="main",
        include_track=want_track,
        include_install=want_install,
        install_flat=opening.get("install_flat"),
    ))
    batons = int(opening.get("batons") if opening.get("batons") not in (None, "") else 2)
    if batons:
        lines.append(_line(
            GROUP_MATERIALS,
            'Fiberglass batons, 48" long',
            batons,
            baton_rate,
            item="Batons",
            area=main_area,
        ))
    if opening.get("hem") or opening.get("soil_hem") or opening.get("optional_hem"):
        lines.append(_line(
            GROUP_MATERIALS,
            "OPTIONAL - soil-resistant hem - COM - customer-owned material, provided by client",
            1,
            None,
            item="Hem",
            com=True,
            area=main_area,
        ))

    sheer_job = None
    if sheer:
        s_fullness = sheer.get("fullness", fullness)
        s_goods = _inches(sheer.get("goods_width") or sheer.get("goods"), rule("sheer_goods_width_in"))
        sw = new_fab_widths(sheer_cov, fullness=s_fullness, goods_in=s_goods, panels=1)
        sheer_cut = finished + rule("sheer_hem_allowance_in")
        sheer_yd = ceil_yards(sw["total"], sheer_cut)
        lines.append(_line(
            GROUP_LABOR,
            (
                f"Ripplefold sheer fabrication, {format_inches_plain(sheer_cov)} coverage, "
                f"{str(sheer.get('control') or control)} draw, FL {format_inches_plain(finished)} - "
                f"{sw['total']:g} widths, {s_goods:g}\" goods"
            ),
            sw["total"],
            labor_rate,
            "widths",
            item="Sheers",
            area=sheer_area,
        ))
        if sheer.get("com", True):
            lines.append(_line(
                GROUP_MATERIALS,
                (
                    f"Sheer fabric - {sheer_yd:g} yd ({sw['total']:g} widths x "
                    f"{format_inches_plain(sheer_cut)} cut) - COM - customer-owned material, "
                    f"provided by client"
                ),
                sheer_yd,
                None,
                "yd",
                item="Fabric",
                com=True,
                area=sheer_area,
            ))
        sheer_track = sheer.get("track", want_track) not in (False, "false", 0, "0")
        sheer_install = sheer.get("install", opening.get("sheer_install", want_install))
        sheer_install = sheer_install not in (False, "false", 0, "0")
        lines.extend(_track_install_lines(
            width_in=sheer_cov,
            area=sheer_area,
            layer="sheer",
            include_track=sheer_track,
            include_install=sheer_install,
        ))
        sheer_batons = int(sheer.get("batons") if sheer.get("batons") not in (None, "") else 2)
        if sheer_batons:
            lines.append(_line(
                GROUP_MATERIALS,
                'Fiberglass batons, 48" long',
                sheer_batons,
                baton_rate,
                item="Batons",
                area=sheer_area,
            ))
        fullness_pct = s_fullness * 100 if float(s_fullness) <= 10 else float(s_fullness)
        sheer_job = resolve_ripplefold({
            "width": width,
            "height": height,
            "coverage_width": sheer_cov,
            "fullness_pct": fullness_pct,
            "carrier": sheer.get("carrier") or "92141",
            "masters": sheer.get("masters") or "overlap",
            "control": sheer.get("control") or control,
            "coverage_align": sheer.get("align") or sheer.get("coverage_align") or "center",
            "layer": "sheer",
            "side_panels": panels,
            "side_widths": cloth["per_panel"],
            "fabric_image": opening.get("fabric_crop") or opening.get("fabric_image"),
        })

    return _finish_opening(
        opening, lines,
        cloth=cloth, cut=cut, yards=yards, bump=False, sheer_job=sheer_job,
        width=width, height=height, panels=panels,
        main_area=main_area, sheer_area=sheer_area, room=room,
    )


def _price_reline(opening: dict) -> dict:
    """Existing re-line path. Track is a complete per-ft line, never hourly."""
    room = str(opening.get("room") or "Room")
    width = _inches(opening["width"])
    height = _inches(opening["height"])
    panels = int(opening.get("panels") or 2)
    cloth = panel_widths(width, panels)
    finished = height
    cut = cut_length(finished)
    yards = lining_yards(cloth["total"], finished)
    bump = wants_bump(opening)
    main_area = str(opening.get("area") or opening.get("room") or AREA_MAIN_DRAPERY).strip()
    sheer = opening.get("sheers") or None
    sheer_cov = _inches((sheer or {}).get("coverage") or (sheer or {}).get("coverage_width"), 0) if sheer else 0.0
    sheer_area = str((sheer or {}).get("area") or "").strip() or AREA_SHEERS
    lines: list[dict] = []

    if opening.get("lining_removal", True):
        rate = rule("lining_removal_per_panel")
        lines.append(_line(
            GROUP_LABOR,
            f"Drapery lining removal · {panels} panels @ ${rate:,.0f}",
            panels,
            rate,
            item="Prep",
            area=main_area,
        ))

    if opening.get("reline", True):
        rate = rule("reline_per_width") if bump else rule("reline_no_bump_per_width")
        label = "Re-line with lining and bump" if bump else "Re-line with lining (no bump)"
        lines.append(_line(
            GROUP_LABOR,
            (
                f"{label} · {panels} panels x "
                f"{_widths_label(cloth['per_panel'])} widths = "
                f"{_widths_label(cloth['total'])} widths @ ${rate:,.0f}"
            ),
            cloth["total"],
            rate,
            "widths",
            item="Drapes",
            area=main_area,
        ))

    sheer_job = None
    if sheer:
        sw = sheer_widths(sheer_cov)
        rate = rule("sheer_fabrication_per_width")
        gap = width - sheer_cov
        lines.append(_line(
            GROUP_LABOR,
            (
                f"Ripplefold sheers · {format_inches_plain(sheer_cov)} "
                f"({format_inches_plain(width)} - {format_inches_plain(gap)}) · "
                f"{format_inches_plain(sw['fabric_in'])} / {format_inches_plain(rule('fabric_width_in'))} = "
                f"{_widths_label(sw['full'])} full, "
                f"halved (double width) = {_widths_label(sw['charged'])} widths @ ${rate:,.0f}"
            ),
            sw["charged"],
            rate,
            "widths",
            item="Sheers",
            area=sheer_area,
        ))
        sheer_job = resolve_ripplefold({
            "width": width,
            "height": height,
            "coverage_width": sheer_cov,
            "fullness_pct": sheer.get("fullness", 100),
            "carrier": sheer.get("carrier") or "92141",
            "masters": sheer.get("masters") or "butt",
            "control": sheer.get("control") or sheer.get("draw") or "center",
            "coverage_align": sheer.get("align") or sheer.get("coverage_align") or "center",
            "layer": "sheer",
            "side_panels": panels,
            "side_widths": cloth["per_panel"],
            "fabric_image": opening.get("fabric_crop") or opening.get("fabric_image"),
        })

    if opening.get("reline", True):
        lines.append(_line(
            GROUP_MATERIALS,
            (
                f"Lining · {yards:.1f} yd @ ${rule('lining_per_yard'):,.2f} "
                f"({_widths_label(cloth['total'])} widths x {format_inches_plain(cut)} cut)"
            ),
            yards,
            rule("lining_per_yard"),
            "yd",
            item="Lining",
            area=main_area,
        ))
        if bump:
            lines.append(_line(
                GROUP_MATERIALS,
                f"Bump interlining · {yards:.1f} yd @ ${rule('bump_per_yard'):,.2f}",
                yards,
                rule("bump_per_yard"),
                "yd",
                item="Bump",
                area=main_area,
            ))
    if sheer and (sheer or {}).get("com", True):
        lines.append(_line(
            GROUP_MATERIALS,
            "Sheer fabric - COM - customer-owned material, provided by client",
            1,
            None,
            item="Fabric",
            com=True,
            area=sheer_area,
        ))

    batons = int(opening.get("batons") or 0)
    if batons:
        rate = rule("baton_each")
        lines.append(_line(
            GROUP_MATERIALS,
            f"Batons · {batons} @ ${rate:,.2f}",
            batons,
            rate,
            item="Batons",
            area=main_area,
        ))

    # Complete track for main + sheers. track_hours is treated as "include
    # track", never as an hourly line.
    track_wanted = opening.get("track") not in (False, "false", 0, "0") and (
        opening.get("include_track")
        or opening.get("track")
        or opening.get("track_hours") not in (None, "", False)
        or opening.get("track_flat") not in (None, "")
    )
    install_wanted = opening.get("install", True) not in (False, "false", 0, "0")
    lines.extend(_track_install_lines(
        width_in=width,
        area=main_area,
        layer="main",
        include_track=bool(track_wanted),
        include_install=install_wanted,
        install_flat=opening.get("install_flat"),
    ))
    if sheer:
        sheer_track = opening.get("sheer_track", opening.get("include_track", track_wanted))
        sheer_install = opening.get("sheer_install", sheer_track)
        lines.extend(_track_install_lines(
            width_in=sheer_cov or width,
            area=sheer_area,
            layer="sheer",
            include_track=sheer_track not in (False, "false", 0, "0") and bool(sheer_track),
            include_install=sheer_install not in (False, "false", 0, "0") and bool(sheer_install),
        ))

    return _finish_opening(
        opening, lines,
        cloth=cloth, cut=cut, yards=yards, bump=bump, sheer_job=sheer_job,
        width=width, height=height, panels=panels,
        main_area=main_area, sheer_area=sheer_area, room=room,
    )


def price_opening(opening: dict) -> dict:
    """Price one opening. New fabrication or re-line. Never emits hourly track."""
    if is_new_fabrication(opening):
        return _price_new_fabrication(opening)
    return _price_reline(opening)


def build_packet(spec: dict) -> dict:
    openings = [price_opening(op) for op in spec.get("openings") or []]
    subtotal = round(sum(op["subtotal"] for op in openings), 2)
    tax_rate = float(spec.get("tax_rate") or 0)
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    deposit_pct = float(spec.get("deposit_percent") or rule("deposit_percent"))
    deposit = round(total * deposit_pct / 100.0, 2)
    created = spec.get("date") or datetime.now().date().isoformat()
    valid_days = int(spec.get("valid_days") or 30)
    try:
        start = datetime.strptime(str(created)[:10], "%Y-%m-%d")
    except ValueError:
        start = datetime.now()
    valid = (start + timedelta(days=valid_days)).date().isoformat()
    notes = _FOUNDER_RE.sub("", str(spec.get("notes") or "")).strip()
    areas: list[dict] = []
    area_index: dict[str, int] = {}
    for opening in openings:
        for area in opening.get("areas") or []:
            key = area["name"]
            if key in area_index:
                dest = areas[area_index[key]]
                dest_groups = {g["name"]: g for g in dest["groups"]}
                for group in area.get("groups") or []:
                    existing = dest_groups.get(group["name"])
                    if existing:
                        existing["lines"].extend(group["lines"])
                        existing["subtotal"] = round(
                            existing["subtotal"] + group["subtotal"], 2
                        )
                    else:
                        dest["groups"].append({
                            "name": group["name"],
                            "lines": list(group["lines"]),
                            "subtotal": group["subtotal"],
                        })
                        dest_groups[group["name"]] = dest["groups"][-1]
                dest["groups"].sort(key=lambda g: GROUP_ORDER.index(g["name"]))
                dest["subtotal"] = round(sum(g["subtotal"] for g in dest["groups"]), 2)
            else:
                area_index[key] = len(areas)
                areas.append({
                    "name": area["name"],
                    "room": area.get("room") or opening.get("room"),
                    "groups": [
                        {
                            "name": g["name"],
                            "lines": list(g["lines"]),
                            "subtotal": g["subtotal"],
                        }
                        for g in area.get("groups") or []
                    ],
                    "subtotal": area["subtotal"],
                })
    packet = {
        "quote_number": spec.get("quote_number") or "EST-DRAFT",
        "date": str(created)[:10],
        "valid_until": valid,
        "valid_days": valid_days,
        "billed_by": spec.get("billed_by"),
        "prepared_for": dict(spec.get("prepared_for") or {}),
        "project": dict(spec.get("project") or {}),
        "notes": notes,
        "rooms": openings,
        "areas": areas,
        "estimate_format": FORMAT_ID,
        "client_factor": spec.get("client_factor"),
        "designer_name": spec.get("designer_name"),
        "designer_markup_factor": spec.get("designer_markup_factor"),
        "subtotal": subtotal,
        "base_total": subtotal,
        "client_total": apply_client(total, spec),
        "designer_share_20pct": round(apply_client(total, spec) - total, 2),
        "tax_rate": tax_rate,
        "tax": tax,
        "total": total,
        "deposit_percent": deposit_pct,
        "deposit": deposit,
        "payment_line": "Pay deposit online: [Square payment link]",
        "terms": spec.get("terms") or (
            "50% deposit to begin · balance due on completion. "
            f"Estimate valid {valid_days} days."
        ),
        "status": "draft",
        "sent": False,
    }
    packet["metadata"] = willard_metadata(packet, designer=spec.get("designer_name"))
    return packet


def sample_phase1(**overrides) -> dict:
    """The EST-2026-297 shape: two openings, Nelma's billing, drafts only."""
    spec = {
        "quote_number": "EST-2026-297",
        "date": "2026-10-02",
        "billed_by": "nelmas_workroom",
        "prepared_for": {
            "company": "Dahlia Design",
            "attn": "Dahlia Mahmood",
            "email": "Dahlia@dahliadesign.net",
            "phone": "(571) 212-6755",
            "address": "44710 Cape Court, Ashburn, VA 20147",
        },
        "project": {
            "name": "Nehal Elrefai",
            "phase": "Phase 1 · Living Room & Office",
            "address": "9408 Old Courthouse Rd, Tysons, VA",
            "sidemark": "Nehal Elrefai",
            "scope": "Re-line draperies · new ripplefold sheers (LR)",
        },
        "notes": (
            "Phase 2 (upstairs) quoted separately · Sheer fabric is COM · "
            "Widths and carriers confirmed on site."
        ),
        "openings": [
            {
                "room": "Living Room",
                "mark": "LR",
                "width": 160,
                "height": 119.75,
                "panels": 2,
                "stationary": True,
                "control": "center",
                "install_flat": 245,
                "track_hours": 1,
                "reline": True,
                "lining_removal": True,
                "batons": 2,
                "sheers": {
                    "coverage": 96,
                    "fullness": 100,
                    "carrier": "92141",
                    "masters": "butt",
                    "control": "center",
                    "align": "center",
                    "com": True,
                },
                "field_notes": [
                    "Remove existing panels, take apart and strip the existing plastic-like lining.",
                    "Resize to finished length; re-line with regular lining and bump interlining.",
                    "Reinstall as a stationary pair, center draw.",
                    "New ripplefold sheers covering 96\", 100%, butt masters, same track; COM.",
                    "Materials include carriers and 2 batons.",
                    "Track re-centered and reinstalled.",
                ],
            },
            {
                "room": "Office",
                "mark": "OF",
                "width": 143.75,
                "height": 119.75,
                "panels": 2,
                "stationary": True,
                "control": "center",
                "install_flat": 245,
                "reline": True,
                "lining_removal": True,
                "batons": 2,
                "pair_assumed": True,
                "field_notes": [
                    "Remove existing panels, take apart and strip the existing plastic-like lining.",
                    "Resize to finished length; re-line with regular lining and bump interlining.",
                    "Reinstall as a stationary pair, center draw.",
                    "Materials include 2 batons.",
                    "Pair assumed — confirm panel count on site.",
                ],
            },
        ],
    }
    spec.update(overrides)
    return spec


def _layered_spec(packet: dict, opening: dict, sheet_no: int, total: int) -> dict:
    src = opening["opening"]
    sheer = src.get("sheers") or {}
    return {
        "product_type": "ripplefold",
        "client_name": opening["room"],
        "project": packet.get("quote_number") or "DRAPERY",
        "sheet_title": "LAYERED",
        "sheet_no": sheet_no,
        "sheet_total": total,
        "width": opening["width"],
        "height": opening["height"],
        "coverage_width": sheer.get("coverage") or sheer.get("coverage_width"),
        "fullness_pct": sheer.get("fullness", 100),
        "carrier": sheer.get("carrier") or "92141",
        "masters": sheer.get("masters") or "butt",
        "control": sheer.get("control") or "center",
        "coverage_align": sheer.get("align") or "center",
        "layer": "sheer",
        "side_panels": opening["panels"],
        "side_widths": opening["widths"]["per_panel"],
        "fabric_image": src.get("fabric_crop") or src.get("fabric_image"),
    }


def render_packet_pdfs(packet: dict) -> tuple[bytes, bytes]:
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter

    from app.services.drawing.templates.ripplefold_render import render_ripplefold_pdf
    from app.services.estimates.willard_estimate import render_willard_pair
    from app.services.estimates.workroom_presentation import (
        render_opening_sheet,
        render_schedule_sheet,
    )

    estimate, internal_estimate = render_willard_pair(packet)
    plan: list[tuple[str, dict | None]] = []
    for opening in packet.get("rooms") or []:
        plan.append(("opening", opening))
        if opening.get("sheer"):
            plan.append(("layered", opening))
    plan.append(("schedule", None))
    total = len(plan)
    writer = PdfWriter()
    for index, (kind, opening) in enumerate(plan, start=1):
        if kind == "opening":
            blob = render_opening_sheet(packet, opening, index, total)
        elif kind == "layered":
            blob = render_ripplefold_pdf(_layered_spec(packet, opening, index, total))
        else:
            blob = render_schedule_sheet(packet, index, total)
        writer.add_page(PdfReader(BytesIO(blob)).pages[0])
    out = BytesIO()
    writer.write(out)
    return estimate, out.getvalue()


def draft_packet(spec: dict, *, save_quote: bool = True) -> dict:
    """Create the two PDFs and, when asked, a draft quote. Never sends."""
    packet = build_packet(spec)
    estimate_pdf, presentation_pdf = render_packet_pdfs(packet)
    from app.services.estimates.willard_estimate import render_willard_estimate
    from app.services.estimates.rafael_format import VARIANT_INTERNAL
    internal_pdf = render_willard_estimate(packet, variant=VARIANT_INTERNAL)
    result = {
        "packet": packet,
        "estimate_pdf": estimate_pdf,
        "estimate_internal_pdf": internal_pdf,
        "presentation_pdf": presentation_pdf,
        "status": "draft",
        "sent": False,
        "estimate_format": FORMAT_ID,
    }
    if not save_quote:
        return result
    from app.services.quote_service import create_quote

    project = packet.get("project") or {}
    party = packet.get("prepared_for") or {}
    items = []
    for opening in packet["rooms"]:
        area_rows = opening.get("areas") or [{
            "name": opening.get("room") or AREA_MAIN_DRAPERY,
            "groups": opening.get("groups") or [],
        }]
        for area in area_rows:
            for group in area.get("groups") or []:
                for line in group.get("lines") or []:
                    items.append({
                        "description": f"{opening['room']}: {line['description']}",
                        "quantity": line["quantity"],
                        "unit": line["unit"],
                        "unit_price": line["rate"] if line.get("rate") is not None else 0,
                        "category": "willard_line",
                        "room": area["name"],
                        "area": area["name"],
                        "group": group["name"],
                        "pricing_snapshot": {
                            "base_rate": line.get("rate"),
                            "base_amount": line.get("amount"),
                            "area": area["name"],
                            "group": group["name"],
                            "estimate_format": FORMAT_ID,
                            "com": bool(line.get("com")),
                        },
                    })
    quote = create_quote({
        "customer_name": party.get("company") or party.get("attn") or "Client",
        "customer_email": party.get("email") or "",
        "customer_phone": party.get("phone") or "",
        "customer_address": party.get("address") or "",
        "project_name": project.get("name") or "",
        "project_description": project.get("scope") or "",
        "project_address": project.get("address") or "",
        "billed_by": packet.get("billed_by"),
        "notes": packet.get("notes") or "",
        "tax_rate": packet.get("tax_rate") or 0,
        "valid_days": packet.get("valid_days") or 30,
        "line_items": items,
        "pricing_mode": "flat",
        "business_unit": "workroom",
        "metadata": packet.get("metadata") or willard_metadata(packet),
    })
    result["quote"] = {
        "id": quote.get("id"),
        "quote_number": quote.get("quote_number"),
        "status": quote.get("status"),
        "project_address": quote.get("project_address"),
        "total": quote.get("total"),
    }
    result["sent"] = False
    return result
