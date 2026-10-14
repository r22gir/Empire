"""Build a viewer scene from a job/quote's measurements + cut list.

Covers banquettes/booths, benches, furniture, and woodwork. Workroom is
not required — woodcraft and mixed jobs generate the same viewer.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable

from app.services.job_viewer.fabrics import resolve_swatch, viewer_swatches
from app.services.job_viewer.fractions import dims_label, inches_label
from app.services.job_viewer.privacy import scrub_text

SEAT_H = 18.0
PLY = 0.5
FOAM = 2.0
BACK_FOAM = 2.0
CHANNEL = 12.0

UPHOLSTERY_TYPES = {
    "banquette", "booth", "u_banquette", "l_banquette", "u_booth", "l_booth",
    "channel_back", "banquettes", "booths", "seat", "cushion",
    "bench", "bench_l_shaped", "bench_u_shaped", "l_bench", "u_bench",
    "sofa", "loveseat", "settee", "chair", "ottoman", "headboard",
    "furniture", "daybed", "chaise",
}
WOOD_TYPES = {
    "woodwork", "cabinet", "table", "frame", "panel", "millwork",
    "base", "apron", "carcass", "shelf", "door", "box",
}
L_TYPES = {"l_banquette", "l_booth", "bench_l_shaped", "l_bench", "l"}
U_TYPES = {"u_banquette", "u_booth", "bench_u_shaped", "u_bench", "u"}


def _f(value, default=None):
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace('"', "").replace("in", "").replace("'", "")
    text = text.replace("½", " 1/2").replace("¼", " 1/4").replace("¾", " 3/4")
    text = re.sub(r"\s+", " ", text)
    if " " in text and "/" in text:
        whole, frac = text.split(" ", 1)
        try:
            num, den = frac.split("/", 1)
            return float(whole) + float(num) / float(den)
        except ValueError:
            pass
    if "/" in text:
        try:
            num, den = text.split("/", 1)
            return float(num) / float(den)
        except ValueError:
            pass
    try:
        return float(text)
    except ValueError:
        return default


def _meas(item: dict) -> dict:
    raw = item.get("measurements") or item.get("dimensions") or item.get("dims") or {}
    if isinstance(raw, str):
        raw = {}
    out = dict(raw) if isinstance(raw, dict) else {}
    for key in ("width", "height", "depth", "A", "B", "C", "seat_height",
                "channel_width", "foam", "ply"):
        if key not in out:
            for alt in (key, key.lower(), f"{key}_inches", key[0].lower() if len(key) == 1 else None):
                if alt and item.get(alt) not in (None, ""):
                    out[key] = item[alt]
                    break
    return out


def _shape_of(item: dict, meas: dict) -> str:
    explicit = str(meas.get("shape") or item.get("shape") or "").lower().strip()
    if explicit in {"u", "l", "straight"}:
        return explicit
    itype = str(item.get("item_type") or item.get("type") or "").lower()
    if itype in U_TYPES or "u-shape" in itype or "u_shape" in itype:
        return "u"
    if itype in L_TYPES or "l-shape" in itype or "l_shape" in itype:
        return "l"
    notes = str(item.get("notes") or meas.get("notes") or "").lower()
    if re.search(r"\bu[\s-]?shap", notes) or "u booth" in notes or "u banquette" in notes:
        return "u"
    if re.search(r"\bl[\s-]?shap", notes) or "l booth" in notes or "l banquette" in notes:
        return "l"
    if _f(meas.get("C")) and _f(meas.get("A")) and _f(meas.get("B")):
        return "u"
    if _f(meas.get("B")) and _f(meas.get("A")):
        return "l"
    return "straight"


def _kind_of(item: dict) -> str:
    itype = str(item.get("item_type") or item.get("type") or "").lower()
    if itype in WOOD_TYPES:
        return "wood"
    if any(k in itype for k in ("banquette", "booth", "channel")):
        return "banquette"
    if "bench" in itype:
        return "bench"
    if itype in UPHOLSTERY_TYPES:
        return "furniture"
    notes = str(item.get("notes") or "").lower()
    if any(k in notes for k in ("banquette", "booth", "channel back")):
        return "banquette"
    if "bench" in notes:
        return "bench"
    fabric = item.get("fabric_code") or item.get("fabric") or (item.get("measurements") or {}).get("fabric_code")
    if fabric:
        return "furniture"
    return "wood" if itype in WOOD_TYPES else "furniture"


def _part(
    *,
    name: str,
    group: str,
    run: str,
    layer: str,
    kind: str,
    mn: list[float],
    mx: list[float],
    dims: list[float],
    explode: list[float],
    pillow: dict | None = None,
    fabric_role: str | None = None,
):
    rec = {
        "n": scrub_text(name),
        "g": group,
        "r": run,
        "l": layer,
        "k": kind,
        "min": [round(v, 4) for v in mn],
        "max": [round(v, 4) for v in mx],
        "dims": [round(v, 4) for v in dims],
        "dimsLabel": dims_label(dims),
        "e": explode,
        "locked": layer == "base",
    }
    if pillow:
        rec["pillow"] = pillow
    if fabric_role:
        rec["fabricRole"] = fabric_role
    return rec


def _seat_stack(x0, z0, length, depth, y0, run, group, name, along="x", foam=FOAM, ply=PLY):
    """Seat ply + foam + fabric along X (along='x') or Z (along='z')."""
    parts = []
    if along == "x":
        x1, z1 = x0 + length, z0 + depth
        long, deep = length, depth
    else:
        x1, z1 = x0 + depth, z0 + length
        long, deep = length, depth
    y_ply0, y_ply1 = y0, y0 + ply
    y_foam1 = y_ply1 + foam
    y_fab1 = y_foam1 + 0.07
    parts.append(_part(
        name=f"{name} seat ply", group=group, run=run, layer="seat_ply", kind="seat",
        mn=[x0, y_ply0, z0], mx=[x1, y_ply1, z1], dims=[long, deep, ply],
        explode=[0, 1, 0, 1],
    ))
    parts.append(_part(
        name=f"{name} seat foam", group=group, run=run, layer="seat_foam", kind="seat",
        mn=[x0, y_ply1, z0], mx=[x1, y_foam1, z1], dims=[long, deep, foam],
        explode=[0, 1, 0, 2],
    ))
    pad = 0.07
    parts.append(_part(
        name=f"{name} seat fabric", group=group, run=run, layer="seat_fabric", kind="seat",
        mn=[x0 - pad, y_ply0 - 0.01, z0 - pad], mx=[x1 + pad, y_fab1, z1 + pad],
        dims=[long, deep, foam + ply + 0.08], explode=[0, 1, 0, 3], fabric_role="seat",
    ))
    return parts, y_foam1


def _base_box(x0, z0, length, depth, height, run, group, name, along="x"):
    if along == "x":
        x1, z1 = x0 + length, z0 + depth
        dims = [length, height, 0.75]
    else:
        x1, z1 = x0 + depth, z0 + length
        dims = [length, height, 0.75]
    return _part(
        name=f"{name} base", group=group, run=run, layer="base", kind="base",
        mn=[x0, 0, z0], mx=[x1, height, z1], dims=dims, explode=[0, 0, 0, 0],
    )


def _channel_backs(x0, z0, length, depth, y_seat, run, group, name, along="x",
                   channel=CHANNEL, back_h=None, foam=BACK_FOAM, ply=PLY):
    back_h = back_h or 26.75
    n = max(1, int(round(length / channel)))
    # Odd leftover channel sits at the open (start) end, matching the reference.
    leftover = length - (n - 1) * channel if n > 1 else length
    if leftover <= 0.25:
        leftover = channel
        n = max(1, n - 1)
    widths = [leftover] + [channel] * (n - 1) if n > 1 else [length]
    parts = []
    cursor = 0.0
    rear = depth - ply if along == "x" else depth - ply
    for i, w in enumerate(widths, start=1):
        tag = f"{name}-C{i:02d}"
        wide = inches_label(w).rstrip('"')
        if along == "x":
            cx, cz = x0 + cursor + w / 2, z0 + rear + ply / 2
            mn = [x0 + cursor, y_seat, z0 + rear]
            mx = [x0 + cursor + w, y_seat + back_h, z0 + rear + ply]
            d_dir, nn = [0, 0, 1], [1, 0, 0]
            ex = [0, 0, 1, 1]
        else:
            cx, cz = x0 + rear + ply / 2, z0 + cursor + w / 2
            mn = [x0 + rear, y_seat, z0 + cursor]
            mx = [x0 + rear + ply, y_seat + back_h, z0 + cursor + w]
            d_dir, nn = [1, 0, 0], [0, 0, 1]
            ex = [1, 0, 0, 1]
        pillow_c = [cx if along == "x" else mn[0], y_seat, cz if along == "x" else (z0 + cursor + w / 2)]
        if along != "x":
            pillow_c = [x0 + rear, y_seat, z0 + cursor + w / 2]
        parts.append(_part(
            name=f'{tag} back ply — {wide}" wide', group=group, run=run,
            layer="back_ply", kind="back", mn=mn, mx=mx, dims=[w, back_h, ply],
            explode=ex,
        ))
        pillow = {"w": w + 1.5, "sh": 0.0, "c": pillow_c, "d": d_dir, "nn": nn, "h": back_h}
        parts.append({
            **_part(
                name=f'{tag} back foam — {wide}" wide', group=group, run=run,
                layer="back_foam", kind="back", mn=mn, mx=mx, dims=[w, back_h, foam],
                explode=[ex[0], ex[1], ex[2], 1],
            ),
            "pillow": {**pillow, "sh": 0.0},
        })
        parts.append({
            **_part(
                name=f'{tag} back fabric — {wide}" wide', group=group, run=run,
                layer="back_fabric", kind="back", mn=mn, mx=mx, dims=[w, back_h, foam + 0.5],
                explode=[ex[0], ex[1], ex[2], 2], fabric_role="back",
            ),
            "pillow": {**pillow, "sh": 0.07},
        })
        cursor += w
    return parts


def _apply_cut_list(item: dict, group: str, run: str, origin: tuple[float, float]) -> list[dict]:
    cuts = item.get("cut_list") or (item.get("measurements") or {}).get("cut_list") or []
    if not isinstance(cuts, list) or not cuts:
        return []
    ox, oz = origin
    parts = []
    cursor = 0.0
    for i, cut in enumerate(cuts):
        if not isinstance(cut, dict):
            continue
        layer = str(cut.get("layer") or cut.get("l") or "seat_ply")
        kind = "base" if layer == "base" else (
            "back" if "back" in layer else "seat" if "seat" in layer else "wood"
        )
        name = scrub_text(cut.get("name") or cut.get("n") or f"{run} part {i + 1}")
        if cut.get("min") and cut.get("max"):
            mn = [float(v) for v in cut["min"]]
            mx = [float(v) for v in cut["max"]]
            dims = cut.get("dims") or [
                abs(mx[0] - mn[0]), abs(mx[1] - mn[1]), abs(mx[2] - mn[2]),
            ]
        else:
            w = _f(cut.get("width") or cut.get("w"), 12) or 12
            h = _f(cut.get("height") or cut.get("h"), 18) or 18
            t = _f(cut.get("thickness") or cut.get("t") or cut.get("depth"), PLY) or PLY
            y0 = _f(cut.get("y"), 0) or 0
            mn = [ox + cursor, y0, oz]
            mx = [ox + cursor + w, y0 + h, oz + t]
            dims = [w, h, t]
            cursor += w + 0.25
        explode = cut.get("e") or ([0, 0, 0, 0] if layer == "base" else [0, 1, 0, 1])
        rec = _part(
            name=name, group=group, run=cut.get("run") or run, layer=layer, kind=kind,
            mn=mn, mx=mx, dims=[_f(d, 0) or 0 for d in dims], explode=list(explode),
            fabric_role="back" if "back_fabric" in layer else ("seat" if "seat_fabric" in layer else None),
        )
        if cut.get("pillow"):
            rec["pillow"] = cut["pillow"]
        parts.append(rec)
    return parts


def _wood_box(x0, z0, w, d, h, run, group, name):
    return [_part(
        name=name, group=group, run=run, layer="base", kind="base",
        mn=[x0, 0, z0], mx=[x0 + w, h, z0 + d],
        dims=[w, h, d], explode=[0, 0, 0, 0],
    )]


def build_item_parts(item: dict, *, origin=(0.0, 0.0), group=None, gap=8.0) -> dict:
    meas = _meas(item)
    name = scrub_text(item.get("name") or item.get("title") or item.get("item_key") or "Piece")
    group = group or scrub_text(item.get("room") or item.get("group") or name)[:24] or "G1"
    run = scrub_text(item.get("item_key") or item.get("run") or re.sub(r"[^A-Za-z0-9]+", "", name)[:6] or "R1")
    kind = _kind_of(item)
    shape = _shape_of(item, meas)
    ox, oz = origin

    cut_parts = _apply_cut_list(item, group, run, origin)
    if cut_parts:
        return {"parts": cut_parts, "group": group, "runs": [[run, name, group]], "kind": kind}

    ply = _f(meas.get("ply"), PLY) or PLY
    foam = _f(meas.get("foam") or meas.get("seat_foam"), FOAM) or FOAM
    seat_h = _f(meas.get("seat_height") or meas.get("height"), SEAT_H) or SEAT_H
    if kind == "wood":
        seat_h = _f(meas.get("height"), 30) or 30
    channel = _f(meas.get("channel_width") or meas.get("channel"), CHANNEL) or CHANNEL
    depth = _f(meas.get("depth") or meas.get("D"), 22) or 22
    has_back = kind in {"banquette", "furniture"} or bool(meas.get("has_back", kind != "wood"))
    if kind == "bench":
        has_back = bool(meas.get("has_back", False)) or "back" in str(item.get("notes") or "").lower()
    if kind == "wood":
        has_back = False
    back_h = _f(meas.get("back_height"), 26.75) or 26.75
    base_h = max(4.0, seat_h - foam - ply) if kind != "wood" else seat_h

    parts: list[dict] = []
    runs: list[list] = []

    def add_run(run_id, label, length, along, x0, z0):
        runs.append([run_id, label, group])
        if kind == "wood":
            parts.extend(_wood_box(x0, z0, length if along == "x" else depth,
                                   depth if along == "x" else length, base_h, run_id, group, label))
            return
        parts.append(_base_box(x0, z0, length, depth, base_h, run_id, group, label, along=along))
        stack, y_top = _seat_stack(x0, z0, length, depth, base_h, run_id, group, label,
                                   along=along, foam=foam, ply=ply)
        parts.extend(stack)
        if has_back:
            parts.extend(_channel_backs(
                x0, z0, length, depth, y_top - 0.07, run_id, group, label,
                along=along, channel=channel, back_h=back_h, foam=_f(meas.get("back_foam"), BACK_FOAM) or BACK_FOAM,
                ply=ply,
            ))

    if shape == "u":
        a = _f(meas.get("A") or meas.get("width"), 84) or 84
        b = _f(meas.get("B"), 40) or 40
        c = _f(meas.get("C"), b) or b
        add_run(f"{run}L", f"{name} left", b, "z", ox, oz)
        add_run(f"{run}M", f"{name} main", a, "x", ox, oz)
        add_run(f"{run}R", f"{name} right", c, "z", ox + a - depth, oz)
    elif shape == "l":
        a = _f(meas.get("A") or meas.get("width"), 84) or 84
        b = _f(meas.get("B"), 48) or 48
        add_run(f"{run}A", f"{name} long", a, "x", ox, oz)
        add_run(f"{run}B", f"{name} short", b, "z", ox, oz)
    else:
        width = _f(meas.get("width") or meas.get("A"), 60) or 60
        add_run(run, name, width, "x", ox, oz)

    return {"parts": parts, "group": group, "runs": runs, "kind": kind}


def _items_from_job(job: dict) -> list[dict]:
    items = list(job.get("items") or [])
    if items:
        return items
    meas = job.get("measurements") or {}
    if meas:
        return [{
            "name": job.get("title") or "Piece",
            "item_type": job.get("job_type") or job.get("type") or "furniture",
            "measurements": meas,
            "cut_list": job.get("cut_list"),
            "fabric_code": (job.get("fabric_selections") or [{}])[0].get("selection_code")
            if job.get("fabric_selections") else job.get("fabric_code"),
            "notes": job.get("notes") or "",
        }]
    return []


def _items_from_quote(quote: dict) -> list[dict]:
    items: list[dict] = []
    for room in quote.get("rooms") or []:
        room_name = room.get("name") or "Room"
        for it in room.get("items") or []:
            rec = dict(it)
            rec.setdefault("room", room_name)
            rec.setdefault("name", it.get("name") or it.get("type") or room_name)
            items.append(rec)
    if items:
        return items
    for li in quote.get("line_items") or quote.get("items") or []:
        meas = li.get("measurements") or li.get("dimensions") or {}
        if not meas and not li.get("cut_list"):
            # Still include if the description looks like furniture we can size.
            desc = str(li.get("description") or li.get("name") or "")
            if not any(k in desc.lower() for k in (
                "banquette", "booth", "bench", "sofa", "chair", "ottoman",
                "headboard", "cabinet", "table", "wood",
            )):
                continue
        rec = dict(li)
        rec.setdefault("name", li.get("name") or li.get("description") or "Piece")
        rec.setdefault("item_type", li.get("item_type") or li.get("category") or li.get("type") or "furniture")
        rec.setdefault("measurements", meas)
        items.append(rec)
    return items


def _job_title(source: dict) -> str:
    title = source.get("title") or source.get("project_name") or source.get("project_description")
    if not title:
        items = source.get("items") or []
        if items:
            title = items[0].get("name") or items[0].get("type")
    title = scrub_text(str(title or "Custom piece"), extra_forbidden=[
        source.get("client_address") or "",
        source.get("customer_address") or "",
        source.get("address") or "",
        source.get("project_address") or "",
    ])
    # Never put a client street on the title. Prefer a short shop name.
    return title or "Custom piece"


def _pick_fabric(source: dict, items: Iterable[dict], swatches: list[dict]) -> tuple[str, str]:
    codes = []
    for bag in (source, *items):
        if not isinstance(bag, dict):
            continue
        for key in ("fabric_code", "seat_fabric", "back_fabric", "fabric"):
            val = bag.get(key)
            if val:
                codes.append(str(val))
        meas = bag.get("measurements") if isinstance(bag.get("measurements"), dict) else {}
        for key in ("fabric_code", "seat_fabric", "back_fabric"):
            if meas.get(key):
                codes.append(str(meas[key]))
        for sel in bag.get("fabric_selections") or []:
            if isinstance(sel, dict) and sel.get("selection_code"):
                codes.append(str(sel["selection_code"]))
    seat = back = None
    for code in codes:
        sw = resolve_swatch(code, swatches)
        if sw:
            seat = seat or sw["code"]
            back = back or sw["code"]
    if not swatches:
        return "V003-Cognac", "V003-Cognac"
    fallback = swatches[0]["code"]
    # Prefer a cognac-like swatch when the job did not name one.
    for row in swatches:
        if "cognac" in row["color"].lower() or "cognac" in row["code"].lower():
            fallback = row["code"]
            break
    return seat or fallback, back or fallback


def build_scene(source: dict, *, draft: bool = True, source_kind: str = "job") -> dict:
    """Return the DATA payload embedded in the self-contained HTML viewer."""
    extra_forbidden = [
        source.get("client_address"),
        source.get("customer_address"),
        source.get("address"),
        source.get("project_address"),
        source.get("client_email"),
        source.get("customer_email"),
    ]
    items = _items_from_job(source) if source_kind != "quote" else _items_from_quote(source)
    if not items:
        items = _items_from_quote(source) or _items_from_job(source)
    swatches = viewer_swatches()
    parts: list[dict] = []
    runs: list[list] = []
    groups: list[list] = []
    seen_groups: set[str] = set()
    cursor_x = 0.0
    kinds: set[str] = set()

    for item in items:
        built = build_item_parts(item, origin=(cursor_x, 0.0))
        parts.extend(built["parts"])
        runs.extend(built["runs"])
        kinds.add(built["kind"])
        g = built["group"]
        if g not in seen_groups:
            seen_groups.add(g)
            groups.append([g, g])
        xs = [p["max"][0] for p in built["parts"] if p.get("max")]
        cursor_x = (max(xs) if xs else cursor_x + 60) + 18.0

    if not parts:
        # Always produce something measurable so preview is never a blank page.
        built = build_item_parts({
            "name": "Piece",
            "item_type": "bench",
            "measurements": {"width": 60, "depth": 22, "height": 18},
        })
        parts, runs, groups = built["parts"], built["runs"], [[built["group"], built["group"]]]
        kinds.add("bench")

    seat_code, back_code = _pick_fabric(source, items, swatches)
    title = _job_title(source)
    kind_label = ", ".join(sorted(kinds)) if kinds else "custom"
    subtitle = scrub_text(
        source.get("description") or f"{kind_label}. Inches. Click a part to identify; hover for size.",
        extra_forbidden=extra_forbidden,
    )
    xs = [p["min"][0] for p in parts if p.get("min")] + [p["max"][0] for p in parts if p.get("max")]
    zs = [p["min"][2] for p in parts if p.get("min")] + [p["max"][2] for p in parts if p.get("max")]
    cx = (min(xs) + max(xs)) / 2 if xs else 40
    cz = (min(zs) + max(zs)) / 2 if zs else 20
    span = max((max(xs) - min(xs)) if xs else 80, (max(zs) - min(zs)) if zs else 40, 40)

    views = {
        "all": {"tgt": [round(cx, 2), 18, round(cz, 2)], "th": 0.55, "ph": 0.42, "dist": max(140, span * 1.35)},
        "top": {"tgt": [round(cx, 2), 0, round(cz, 2)], "th": 0, "ph": 1.55, "dist": max(180, span * 1.7)},
        "front": {"tgt": [round(cx, 2), 16, round(cz, 2)], "th": 0, "ph": 0.16, "dist": max(130, span * 1.25)},
        "end": {"tgt": [round(cx, 2), 16, round(cz, 2)], "th": math.pi / 2, "ph": 0.2, "dist": max(120, span * 1.15)},
    }
    # Per-group close-ups
    for g, _label in groups:
        gp = [p for p in parts if p.get("g") == g and p.get("min")]
        if not gp:
            continue
        gxs = [p["min"][0] for p in gp] + [p["max"][0] for p in gp]
        gzs = [p["min"][2] for p in gp] + [p["max"][2] for p in gp]
        views[g.lower()[:12] or "g"] = {
            "tgt": [round((min(gxs) + max(gxs)) / 2, 2), 22, round((min(gzs) + max(gzs)) / 2, 2)],
            "th": 0.5, "ph": 0.34, "dist": max(160, (max(gxs) - min(gxs) + 40) * 1.8),
        }

    layers = [
        ["base", "Base / frame (locked)", "#1c1c1c"],
        ["seat_ply", 'Seat ply 1/2"', "#d9b86a"],
        ["seat_foam", 'Seat foam 2"', "#f4efc0"],
        ["seat_fabric", "Seat fabric", "#9a5225"],
        ["back_ply", 'Back ply 1/2"', "#e3c892"],
        ["back_foam", "Back foam", "#f6f0c8"],
        ["back_fabric", "Back fabric", "#9a5225"],
    ]
    used_layers = {p["l"] for p in parts}
    layers = [row for row in layers if row[0] in used_layers] or layers[:1]

    return {
        "title": title,
        "subtitle": subtitle,
        "draft": bool(draft),
        "brand": "EMPIRE WORKROOM",
        "units": "in",
        "tileInches": 6,
        "fabrics": swatches,
        "defaultSeat": seat_code,
        "defaultBack": back_code,
        "groups": groups,
        "runs": runs,
        "layers": layers,
        "views": views,
        "parts": parts,
    }
