"""Build a draft estimate and presentation from openings. Nothing is sent."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.services.drawing.inches import format_inches
from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold
from app.services.pricing.workroom_rules import (
    cut_length,
    install_price,
    lining_yards,
    panel_widths,
    rule,
    sheer_widths,
)

_GROUP_ORDER = ("Installation", "Preparation", "Construction", "Materials")
_PACKET_RE = re.compile(
    r"\b(estimate|quote)\b.{0,80}\bpresentation\b|\bpresentation\b.{0,80}\b(estimate|quote)\b",
    re.I | re.S,
)
_FOUNDER_RE = re.compile(r"\brafael(\s+giraldo)?\b", re.I)


def wants_packet(message: str | None) -> bool:
    return bool(_PACKET_RE.search(message or ""))


def _widths_label(value: float) -> str:
    text = format_inches(value)
    return text[:-1] if text.endswith('"') else text


def _line(group: str, description: str, qty: float, rate: float, unit: str = "ea") -> dict:
    amount = round(float(qty) * float(rate), 2)
    return {
        "group": group,
        "description": _FOUNDER_RE.sub("", description).strip(),
        "quantity": qty,
        "unit": unit,
        "rate": round(float(rate), 2),
        "amount": amount,
    }


def price_opening(opening: dict) -> dict:
    """Price one opening into the four groups. Does not invent a mount or ceiling."""
    room = str(opening.get("room") or "Room")
    width = float(opening["width"])
    height = float(opening["height"])
    panels = int(opening.get("panels") or 2)
    cloth = panel_widths(width, panels)
    finished = height
    cut = cut_length(finished)
    yards = lining_yards(cloth["total"], finished)
    lines: list[dict] = []

    install = install_price(width, opening.get("install_flat"))
    if install["method"] == "flat":
        install_desc = (
            f"Removal and installation · {format_inches(width)} window · "
            f"flat ${install['amount']:,.0f} per section"
        )
    else:
        install_desc = (
            f"Removal and installation · {format_inches(width)} window · "
            f"${rule('install_per_window'):,.0f} up to {rule('install_included_ft'):.0f} ft"
            f" + ${rule('install_overage_per_ft'):,.0f}/ft over"
        )
    lines.append(_line("Installation", install_desc, 1, install["amount"]))
    hours = opening.get("track_hours")
    if hours:
        rate = rule("track_labor_per_hour")
        lines.append(_line(
            "Installation",
            f"Track re-center and reinstall · {hours:g} hr @ ${rate:,.0f}",
            float(hours),
            rate,
            "hr",
        ))

    if opening.get("lining_removal", True):
        rate = rule("lining_removal_per_panel")
        lines.append(_line(
            "Preparation",
            f"Drapery lining removal · {panels} panels @ ${rate:,.0f}",
            panels,
            rate,
        ))

    if opening.get("reline", True):
        rate = rule("reline_per_width")
        lines.append(_line(
            "Construction",
            (
                f"Re-line with lining and bump · {panels} panels x "
                f"{_widths_label(cloth['per_panel'])} widths = "
                f"{_widths_label(cloth['total'])} widths @ ${rate:,.0f}"
            ),
            cloth["total"],
            rate,
            "widths",
        ))

    sheer = opening.get("sheers") or None
    sheer_job = None
    if sheer:
        coverage = float(sheer.get("coverage") or sheer.get("coverage_width"))
        sw = sheer_widths(coverage)
        rate = rule("sheer_fabrication_per_width")
        gap = width - coverage
        lines.append(_line(
            "Construction",
            (
                f"Ripplefold sheers · {format_inches(coverage)} "
                f"({format_inches(width)} - {format_inches(gap)}) · "
                f"{format_inches(sw['fabric_in'])} / {format_inches(rule('fabric_width_in'))} = "
                f"{sw['full_raw']:.2f} → {_widths_label(sw['full'])}, "
                f"halved (double width) = {sw['halved_raw']:.2f} → "
                f"{_widths_label(sw['charged'])} widths @ ${rate:,.0f}"
            ),
            sw["charged"],
            rate,
            "widths",
        ))
        sheer_meta = {
            "coverage": coverage,
            "widths": sw,
            "rate": rate,
        }
        sheer_job = resolve_ripplefold({
            "width": width,
            "height": height,
            "coverage_width": coverage,
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
    else:
        sheer_meta = None
        sheer_job = None

    if opening.get("reline", True):
        lines.append(_line(
            "Materials",
            (
                f"Lining · {yards:.1f} yd @ ${rule('lining_per_yard'):,.2f} "
                f"({_widths_label(cloth['total'])} widths x {format_inches(cut)} cut)"
            ),
            yards,
            rule("lining_per_yard"),
            "yd",
        ))
        lines.append(_line(
            "Materials",
            f"Bump interlining · {yards:.1f} yd @ ${rule('bump_per_yard'):,.2f}",
            yards,
            rule("bump_per_yard"),
            "yd",
        ))
    if sheer_meta and sheer_job and sheer_job.carrier_count:
        rate = rule("ripplefold_carrier_each")
        lines.append(_line(
            "Materials",
            (
                f"Ripplefold carriers · Kirsch {sheer_job.carrier} chart, "
                f"{format_inches(sheer_meta['coverage'])} at {sheer_job.fullness}% · "
                f"{sheer_job.carrier_count} @ ${rate:,.2f}"
            ),
            sheer_job.carrier_count,
            rate,
        ))
    if sheer_meta and (sheer or {}).get("com", True):
        lines.append(_line(
            "Materials",
            "Sheer fabric · COM (customer's own material) · no charge",
            1,
            0,
        ))

    batons = int(opening.get("batons") or 0)
    if batons:
        rate = rule("baton_each")
        lines.append(_line("Materials", f"Batons · {batons} @ ${rate:,.2f}", batons, rate))

    groups = []
    for name in _GROUP_ORDER:
        grouped = [row for row in lines if row["group"] == name]
        if not grouped:
            continue
        groups.append({
            "name": name,
            "lines": grouped,
            "subtotal": round(sum(row["amount"] for row in grouped), 2),
        })
    return {
        "room": room,
        "mark": opening.get("mark") or "",
        "width": width,
        "height": height,
        "panels": panels,
        "widths": cloth,
        "cut_length": cut,
        "yards": yards,
        "sheer": sheer_job,
        "groups": groups,
        "subtotal": round(sum(g["subtotal"] for g in groups), 2),
        "opening": opening,
    }


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
    return {
        "quote_number": spec.get("quote_number") or "EST-DRAFT",
        "date": str(created)[:10],
        "valid_until": valid,
        "valid_days": valid_days,
        "billed_by": spec.get("billed_by"),
        "prepared_for": dict(spec.get("prepared_for") or {}),
        "project": dict(spec.get("project") or {}),
        "notes": notes,
        "rooms": openings,
        "subtotal": subtotal,
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
    from app.services.estimates.header_b_estimate import render_header_b_estimate
    from app.services.estimates.workroom_presentation import (
        render_opening_sheet,
        render_schedule_sheet,
    )

    estimate = render_header_b_estimate(packet)
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
    result = {
        "packet": packet,
        "estimate_pdf": estimate_pdf,
        "presentation_pdf": presentation_pdf,
        "status": "draft",
        "sent": False,
    }
    if not save_quote:
        return result
    from app.services.quote_service import create_quote

    project = packet.get("project") or {}
    party = packet.get("prepared_for") or {}
    items = []
    for opening in packet["rooms"]:
        for group in opening["groups"]:
            for line in group["lines"]:
                items.append({
                    "description": f"{opening['room']}: {line['description']}",
                    "quantity": line["quantity"],
                    "unit": line["unit"],
                    "unit_price": line["rate"],
                    "category": "job_line",
                    "room": opening["room"],
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
