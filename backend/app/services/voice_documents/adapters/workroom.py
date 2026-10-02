"""Workroom outputs: saved-rate quotes and the existing bench drawing engine.

No prices are written here. Labor comes from pricing_tables.get_labor_cost,
COM fabric from the pricing engine's com_fabric line, and welt add-ons from
pricing_tables.get_upgrade_cost. Drawings come from bench_renderer.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.config.workroom_billing import billed_by_for_storage, get_workroom_billing
from app.services.drawing.bench_fabrication_params import resolve_bench_fabrication
from app.services.drawing.bench_quote_bridge import WORKROOM_CHROME
from app.services.invoice_pdf_service import client_visible_line_description
from app.services.voice_documents.edition import FORBIDDEN_CLIENT_NAMES, EditionConfig
from app.services.voice_documents.extract import ExtractedItem, Extraction
from app.services.voice_documents.kinds import DraftDocument

logger = logging.getLogger("voice_documents.workroom")

_SEATING = {"bench", "banquette"}
_FABRIC_BOTH = "Supplied fabric, plain seats/backs"
_FABRIC_SEATS = "Supplied fabric, plain seats"
_FABRIC_BACKS = "Supplied fabric, plain backs"


def scrub_client_text(text: str) -> str:
    out = text or ""
    for token in FORBIDDEN_CLIENT_NAMES:
        if len(token) < 2:
            continue
        out = re.sub(rf"\b{re.escape(token)}\b", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,.-")
    return out


def fabric_phrase(item: ExtractedItem) -> str:
    if item.item_type == "back_cushion":
        phrase = _FABRIC_BACKS
    elif item.has_back:
        phrase = _FABRIC_BOTH
    else:
        phrase = _FABRIC_SEATS
    visible = client_visible_line_description({"description": phrase})
    return visible or phrase


def apply_overrides(item: Optional[ExtractedItem], overrides: dict) -> Optional[ExtractedItem]:
    if item is None:
        return None
    fabric = overrides.get("fabric")
    if fabric in ("com", "workroom"):
        item.fabric_mode = fabric
        if fabric == "com" and not item.fabric_name:
            item.fabric_name = "supplied"
    welt = overrides.get("welt")
    if welt in ("none", "self", "contrast"):
        item.welt = welt
    sections = overrides.get("seat_sections")
    if sections:
        item.seat_sections = int(sections)
    back_sections = overrides.get("back_sections")
    if back_sections:
        item.back_sections = int(back_sections)
    return item


def _rate_key(item: ExtractedItem) -> str:
    if item.item_type == "banquette":
        return "banquette"
    if item.item_type == "bench":
        width = float(item.width_in or 0)
        if width and width <= 48:
            return "bench_small"
        if width > 96:
            return "bench_large"
        return "bench_medium"
    mapping = {
        "seat_cushion": "seat_cushion",
        "back_cushion": "back_cushion",
        "roman_shade": "roman_shade",
        "drapery": "drapery_panel",
        "throw_pillow": "throw_pillow",
    }
    return mapping.get(item.item_type, "")


def _labor_dims(item: ExtractedItem, rate_key: str) -> dict:
    dims: dict[str, float] = {}
    if item.width_in:
        dims["width"] = float(item.width_in)
        dims["linear_ft"] = float(item.width_in) / 12.0
    if item.seat_height_in and item.back_height_in:
        dims["height"] = float(item.back_height_in)
    if rate_key in ("seat_cushion", "back_cushion"):
        count = item.seat_sections or item.back_sections or 1
        dims["cushion_count"] = float(count)
    return dims


def quote_lines(item: ExtractedItem) -> tuple[list[dict], list[dict]]:
    """Return (line item payloads for quote_service, missing info)."""
    from app.services.quote_engine.pricing_tables import (
        LABOR_RATES,
        get_labor_cost,
        get_upgrade_cost,
    )

    missing: list[dict] = []
    lines: list[dict] = []
    rate_key = _rate_key(item)
    needs_width = rate_key in {
        "banquette", "bench_small", "bench_medium", "bench_large",
        "roman_shade", "drapery_panel",
    }
    if needs_width and not item.width_in:
        missing.append({"id": "width", "label": "Overall length"})
    elif rate_key and rate_key in LABOR_RATES and (item.width_in or rate_key.endswith("cushion") or rate_key == "throw_pillow"):
        dims = _labor_dims(item, rate_key)
        amount = float(get_labor_cost(rate_key, dims))
        description = scrub_client_text(item.name or rate_key.replace("_", " "))
        if item.width_in:
            description = f"{description}, {item.width_in:g} in"
        lines.append({
            "category": "manual_line",
            "description": description,
            "item_type": item.item_type,
            "quantity": 1,
            "unit": "ea",
            "unit_price": amount,
            "width": item.width_in,
            "height": item.back_height_in or item.seat_height_in,
            "depth": item.depth_in,
            "inputs": {
                "description": description,
                "unit_price": amount,
                "quantity": 1,
            },
            "rate_source": f"pricing_tables.LABOR_RATES:{rate_key}",
            "pricing_snapshot": {
                "rate_table": "pricing_tables.LABOR_RATES",
                "rate_key": rate_key,
                "rates": LABOR_RATES[rate_key],
                "dimensions": dims,
            },
        })

    if item.fabric_mode == "com":
        phrase = fabric_phrase(item)
        lines.append({
            "category": "com_fabric",
            "description": phrase,
            "item_type": "com_fabric",
            "quantity": 1,
            "unit": "ea",
            "inputs": {
                "customer_supplied": True,
                "fabric_name": item.fabric_name or "supplied",
                "quantity": 1,
            },
            "rate_source": "pricing_engine.com_fabric",
        })
    elif item.fabric_mode == "workroom":
        missing.append({
            "id": "fabric_grade",
            "label": "Workroom fabric grade (A–D) before a fabric price is taken from the saved grade table",
        })

    if item.welt == "contrast":
        amount = float(get_upgrade_cost("contrast_welting", 1))
        lines.append({
            "category": "manual_line",
            "description": "Contrast welt",
            "item_type": "welt",
            "quantity": 1,
            "unit": "ea",
            "unit_price": amount,
            "inputs": {
                "description": "Contrast welt",
                "unit_price": amount,
                "quantity": 1,
            },
            "rate_source": "pricing_tables.UPGRADES:contrast_welting",
        })
    return lines, missing


def fabrication_for(item: ExtractedItem, notes: str) -> dict:
    width = float(item.width_in or 0)
    depth = float(item.depth_in or 0)
    seat_h = float(item.seat_height_in or 18)
    dims = {}
    if item.seat_sections is not None:
        dims["seat_sections"] = item.seat_sections
    if item.back_sections is not None:
        dims["back_sections"] = item.back_sections
    if item.seat_cushion_thickness is not None:
        dims["seat_cushion_thickness"] = item.seat_cushion_thickness
    if item.back_thickness is not None:
        dims["back_thickness"] = item.back_thickness
    if item.back_angle_deg is not None:
        dims["back_angle_deg"] = item.back_angle_deg
    if item.overhang_in is not None:
        dims["seat_cushion_overhang"] = item.overhang_in
    fab = resolve_bench_fabrication(
        width_in=width or 1,
        overall_depth_in=depth or 20,
        seat_height_in=seat_h,
        dims=dims,
        notes=notes,
        seat_sections_default=1,
    )
    usable = fab.seat_frame_depth_in(depth or 20)
    return {
        "overall_depth_in": depth or None,
        "usable_seat_in": usable if depth else None,
        "back_thickness_in": fab.back_thickness_in,
        "seat_cushion_thickness_in": fab.seat_cushion_thickness_in,
        "seat_deck_height_in": fab.seat_deck_height_in(),
        "overhang_in": fab.seat_cushion_overhang_in,
        "back_angle_deg": fab.back_angle_deg,
        "seat_sections": fab.seat_sections,
        "back_sections": fab.back_sections,
        "vertical_back": fab.back_angle_deg <= 0,
    }


def _chrome(billed_by: str | None) -> dict:
    billing = get_workroom_billing(billed_by)
    chrome = dict(WORKROOM_CHROME)
    chrome["company"] = billing.letterhead_upper
    chrome["address"] = billing.address
    chrome["contact"] = f"{billing.phone} | {billing.email}"
    chrome["drawn_by"] = "MAX AI"
    if billing.billed_by == "nelmas_workroom":
        chrome["tagline"] = "POWERED BY EMPIRE WORKROOM"
    else:
        chrome["tagline"] = (billing.tagline or "CUSTOM UPHOLSTERY & FABRICATION").upper()
    return chrome


def render_item_drawing(
    item: ExtractedItem,
    *,
    notes: str,
    quote_number: str,
    client_name: str,
    billed_by: str | None,
) -> dict:
    """Render through bench_renderer and return svg plus fabrication facts."""
    facts = fabrication_for(item, notes)
    if item.item_type not in _SEATING or not item.width_in:
        return {"attached": False, "reason": "drawing needs a bench or banquette length", "fabrication": facts, "svg": ""}
    from app.services.vision.bench_renderer import render_l_shape, render_straight, render_u_shape

    kwargs = dict(
        panel_style=item.panel_style or "flat",
        quote_num=quote_number,
        client=scrub_client_text(client_name),
        description=notes,
        include_side_elevation=True,
        sheet_kind="shop",
        chrome=_chrome(billed_by),
        business_unit="workroom",
        product_type=item.item_type,
        has_back=item.has_back,
    )
    if item.seat_sections is not None:
        kwargs["seat_sections"] = item.seat_sections
    if item.back_sections is not None:
        kwargs["back_sections"] = item.back_sections
    if item.seat_cushion_thickness is not None:
        kwargs["seat_cushion_thickness"] = item.seat_cushion_thickness
    if item.back_thickness is not None:
        kwargs["back_thickness"] = item.back_thickness
    if item.back_angle_deg is not None:
        kwargs["back_angle_deg"] = item.back_angle_deg
    if item.overhang_in is not None:
        kwargs["seat_cushion_overhang"] = item.overhang_in
    depth = float(item.depth_in or 20)
    seat_h = float(item.seat_height_in or 18)
    back_h = float(item.back_height_in if item.back_height_in is not None else 18)
    if item.shape == "l_shape":
        svg = render_l_shape(item.name, float(item.width_in), depth_in=depth, seat_h_in=seat_h, back_h_in=back_h, **kwargs)
    elif item.shape == "u_shape":
        svg = render_u_shape(
            item.name, float(item.width_in), depth_in=depth, seat_h_in=seat_h, back_h_in=back_h, **kwargs,
        )
    else:
        svg = render_straight(
            item.name, float(item.width_in), depth_in=depth, seat_h_in=seat_h, back_h_in=back_h, **kwargs,
        )
    return {"attached": False, "svg": svg, "fabrication": facts, "renderer": "bench_renderer"}


def _replace_lines(quote_id: str, lines: list[dict]) -> dict:
    from app.services.quote_service import add_line_item, delete_line_item, get_quote

    current = get_quote(quote_id)
    for row in list(current.get("line_items") or []):
        delete_line_item(quote_id, row["id"])
    for line in lines:
        add_line_item(quote_id, line)
    return get_quote(quote_id)


def _set_billed_by(quote_id: str, billed_by: str | None) -> None:
    from app.config.workroom_billing import ensure_billed_by_schema
    from app.db.database import get_db

    with get_db() as conn:
        ensure_billed_by_schema(conn)
        conn.execute(
            "UPDATE quotes_v2 SET billed_by = ? WHERE id = ?",
            (billed_by_for_storage(billed_by), quote_id),
        )


def persist_drawing(quote: dict, drawing: dict, item: ExtractedItem) -> dict:
    svg = drawing.get("svg") or ""
    if not svg:
        return drawing
    from app.services.drawing.canonical_path import new_drawing_path

    path = new_drawing_path(prefix="voice_bench", suffix=".svg")
    path.write_text(svg)
    drawing = dict(drawing)
    drawing["path"] = str(path)
    drawing["attached"] = False
    try:
        from app.services.max.ul_banquette_drawings import persist_drawing_to_quote

        attached = persist_drawing_to_quote(
            quote_id=quote.get("id") or "",
            quote_num=quote.get("quote_number") or "",
            pdf_path=str(path),
            svg_path=str(path),
            item_type=item.item_type or "bench",
            item_name=item.name or "Bench",
            shape=item.shape or "straight",
            dims=drawing.get("fabrication") or {},
            renderer="bench_renderer",
        )
        drawing["attached"] = True
        drawing["persist"] = {k: v for k, v in attached.items() if k != "pdf_path"}
    except Exception as exc:
        logger.warning("voice drawing attach failed: %s", exc)
        drawing["persist_error"] = str(exc)[:300]
    return drawing


def build_quote_draft(
    extraction: Extraction,
    edition: EditionConfig,
    session_quote_id: str,
) -> tuple[DraftDocument, str]:
    item = extraction.items[0] if extraction.items else None
    client = scrub_client_text(extraction.client_name)
    billed_by = "nelmas_workroom" if extraction.bill_as_nelmas else None
    billing = get_workroom_billing(billed_by)
    if item is None:
        return DraftDocument(
            kind="quote",
            status="needs_info",
            persisted=False,
            summary="No item yet.",
            payload={"client_brand": billing.name, "billed_by": billing.billed_by},
        ), ""

    lines, price_missing = quote_lines(item)
    notes = extraction.transcript
    quote: dict[str, Any] = {}
    quote_id = session_quote_id
    if lines:
        from app.services.quote_service import create_quote, get_quote, update_quote

        body_common = {
            "customer_name": client,
            "project_name": scrub_client_text(item.name or "Voice draft"),
            "project_description": scrub_client_text(item.name or ""),
            "business_unit": edition.business_unit if edition.business_unit == "workroom" else "workroom",
            "notes": "voice draft — not sent",
            "billed_by": billed_by,
        }
        if quote_id:
            update_quote(quote_id, {
                "customer_name": client,
                "project_name": body_common["project_name"],
                "project_description": body_common["project_description"],
            })
            _set_billed_by(quote_id, billed_by)
            quote = _replace_lines(quote_id, lines)
        else:
            quote = create_quote({**body_common, "line_items": lines})
            quote_id = quote.get("id") or ""
        if quote_id and not quote:
            quote = get_quote(quote_id)
    drawing = {"attached": False, "svg": "", "fabrication": fabrication_for(item, notes)}
    if quote_id and item.item_type in _SEATING and item.width_in:
        try:
            drawing = render_item_drawing(
                item,
                notes=notes,
                quote_number=quote.get("quote_number") or "",
                client_name=client,
                billed_by=billed_by,
            )
            drawing = persist_drawing(quote, drawing, item)
        except Exception as exc:
            logger.warning("voice drawing failed: %s", exc)
            drawing["error"] = str(exc)[:300]
    public_lines = []
    for row in quote.get("line_items") or []:
        public_lines.append({
            "description": client_visible_line_description(row),
            "amount": row.get("amount", row.get("final_price")),
            "category": row.get("category"),
            "rate_source": row.get("rate_source"),
        })
    return DraftDocument(
        kind="quote",
        status="draft" if quote_id else "needs_info",
        persisted=bool(quote_id),
        sent=False,
        summary=quote.get("quote_number") or "draft",
        payload={
            "quote_id": quote.get("id"),
            "quote_number": quote.get("quote_number"),
            "quote_status": quote.get("status") or "draft",
            "total": quote.get("total"),
            "subtotal": quote.get("subtotal"),
            "line_items": public_lines,
            "billed_by": billing.billed_by,
            "client_brand": billing.name,
            "drawing": drawing,
            "price_missing": price_missing,
            "customer_name": quote.get("customer_name") or client,
        },
    ), quote_id or ""


def missing_and_options(extraction: Extraction) -> tuple[list[dict], list[dict]]:
    item = extraction.items[0] if extraction.items else None
    missing: list[dict] = []
    options: list[dict] = []
    if not scrub_client_text(extraction.client_name):
        missing.append({"id": "client", "label": "Client name"})
    if item is None:
        missing.append({"id": "item", "label": "What to make (bench, banquette, cushions)"})
        return missing, options
    if item.item_type in _SEATING and not item.width_in:
        missing.append({"id": "width", "label": "Overall length"})
    if item.item_type in _SEATING and not item.depth_in:
        missing.append({
            "id": "depth",
            "label": "Overall depth (usable seat is depth minus the back cushion inside it)",
        })
    if item.item_type in _SEATING and not item.seat_height_in:
        missing.append({
            "id": "seat_height",
            "label": "Seat height (cushion thickness is its own layer inside it)",
        })
    if item.has_back and item.item_type in _SEATING and not item.back_height_in:
        missing.append({"id": "back_height", "label": "Back height"})
    if item.back_thickness is None and item.item_type in _SEATING:
        missing.append({
            "id": "back_thickness",
            "label": "Back cushion thickness not stated — shop standard is 2 in, inside the stated depth",
        })
    if item.seat_cushion_thickness is None and item.item_type in _SEATING:
        missing.append({
            "id": "cushion_thickness",
            "label": "Seat cushion thickness not stated — shop standard is 2 in, marked as its own layer",
        })
    if item.fabric_mode is None:
        missing.append({"id": "fabric", "label": "Fabric: COM or workroom-supplied"})
        options.append({
            "id": "fabric",
            "prompt": "Fabric",
            "choices": [
                {"id": "com", "label": "COM — supplied fabric, plain seats/backs"},
                {"id": "workroom", "label": "Workroom-supplied fabric"},
            ],
        })
    if item.welt is None and item.item_type in _SEATING | {"seat_cushion"}:
        options.append({
            "id": "welt",
            "prompt": "Welt",
            "choices": [
                {"id": "none", "label": "No welt"},
                {"id": "self", "label": "Self welt"},
                {"id": "contrast", "label": "Contrast welt"},
            ],
        })
    if item.seat_sections is None and item.item_type in _SEATING:
        options.append({
            "id": "seat_sections",
            "prompt": "Seat cushion count",
            "choices": [
                {"id": "1", "label": "1 seat cushion"},
                {"id": "2", "label": "2 seat cushions"},
                {"id": "3", "label": "3 seat cushions"},
            ],
        })
    return missing, options[:3]
