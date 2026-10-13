"""Spanish COP estimate / quote / invoice PDFs for Max-e and Maxine.

Each company letterhead comes from its EMPIRE_DATA_DIR profile (name, logo,
NIT, IVA). Founder Workroom chrome is not used.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.edition_pdf_branding import (
    EditionPdfBrand,
    client_nit,
    document_iva_rate,
    format_document_cop,
    resolve_edition_pdf_brand,
)
from app.services.voice_doc.plans import cop_round
from app.services.pricing.dimensions import quote_item_dimension_text

logger = logging.getLogger(__name__)

INK = colors.HexColor("#1a1a2e")
GOLD = colors.HexColor("#b08a2e")
MUTE = colors.HexColor("#666666")
RULE = colors.HexColor("#d8d0c4")
PANEL = colors.HexColor("#f7f4ee")

LABELS = {
    "cotizacion": "Cotización",
    "factura": "Factura",
    "subtotal": "Subtotal",
    "iva": "IVA",
    "total": "Total",
    "nit": "NIT",
    "cliente": "Cliente",
    "fecha": "Fecha",
    "validez": "Validez",
    "descripcion": "Descripción",
    "cant": "Cant.",
    "unidad": "Unid.",
    "precio": "Precio",
    "importe": "Importe",
    "medidas": "Medidas",
}

_UNICODE_FONT = "DejaVuSans"
_UNICODE_BOLD = "DejaVuSans-Bold"
_FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def _fonts() -> tuple[str, str]:
    names = pdfmetrics.getRegisteredFontNames()
    if _UNICODE_FONT in names and _UNICODE_BOLD in names:
        return _UNICODE_FONT, _UNICODE_BOLD
    regular = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
    bold = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")
    try:
        if os.path.isfile(regular) and _UNICODE_FONT not in names:
            pdfmetrics.registerFont(TTFont(_UNICODE_FONT, regular))
        if os.path.isfile(bold) and _UNICODE_BOLD not in names:
            pdfmetrics.registerFont(TTFont(_UNICODE_BOLD, bold))
    except Exception:
        return "Helvetica", "Helvetica-Bold"
    names = pdfmetrics.getRegisteredFontNames()
    body = _UNICODE_FONT if _UNICODE_FONT in names else "Helvetica"
    heavy = _UNICODE_BOLD if _UNICODE_BOLD in names else "Helvetica-Bold"
    return body, heavy


def _styles():
    body, heavy = _fonts()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "EdName", parent=styles["Title"], fontName=heavy,
        fontSize=18, textColor=INK, spaceAfter=2, alignment=TA_LEFT, leading=22,
    ))
    styles.add(ParagraphStyle(
        "EdMuted", parent=styles["Normal"], fontName=body,
        fontSize=8, textColor=MUTE, leading=11,
    ))
    styles.add(ParagraphStyle(
        "EdBody", parent=styles["Normal"], fontName=body,
        fontSize=9, textColor=INK, leading=12,
    ))
    styles.add(ParagraphStyle(
        "EdRight", parent=styles["Normal"], fontName=body,
        fontSize=10, alignment=TA_RIGHT, textColor=INK,
    ))
    styles.add(ParagraphStyle(
        "EdDoc", parent=styles["Normal"], fontName=heavy,
        fontSize=18, alignment=TA_RIGHT, textColor=GOLD, leading=22,
    ))
    styles.add(ParagraphStyle(
        "EdCenter", parent=styles["Normal"], fontName=body,
        fontSize=8, textColor=MUTE, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "EdHead", parent=styles["Normal"], fontName=heavy,
        fontSize=8, textColor=colors.white, leading=10,
    ))
    return styles


def _fmt_date(raw: Any) -> str:
    if not raw:
        return datetime.now().strftime("%d/%m/%Y")
    text = str(raw)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:26].rstrip("Z"), fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text[:10]


def _money(value: Any) -> str:
    return format_document_cop(value)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _line_amount(item: dict) -> float:
    for key in ("subtotal", "total", "amount"):
        if item.get(key) not in (None, ""):
            return _num(item.get(key))
    qty = _num(item.get("quantity", 1), 1) or 1
    rate = _num(item.get("unit_price", item.get("rate", 0)))
    return round(qty * rate, 2)


def _line_description(item: dict) -> str:
    desc = (
        item.get("client_description")
        or item.get("description")
        or item.get("item_type")
        or "Ítem"
    )
    desc = str(desc).strip()
    dims = quote_item_dimension_text(item)
    if dims:
        return f"{desc}<br/>{LABELS['medidas']}: {dims}"
    return desc


def _header_flowables(brand: EditionPdfBrand, title: str, number: str, styles) -> list:
    identity = [f"<b>{brand.name}</b>"]
    if brand.legal_name and brand.legal_name != brand.name:
        identity.append(brand.legal_name)
    if brand.nit:
        identity.append(f"{LABELS['nit']}: {brand.nit}")
    for bit in (brand.address, brand.phone, brand.email, brand.website):
        if bit:
            identity.append(bit)
    left_cell = Paragraph("<br/>".join(identity), styles["EdBody"])
    if brand.logo_path and brand.logo_path.is_file():
        try:
            logo = Image(str(brand.logo_path), width=1.1 * inch, height=0.62 * inch)
            logo.hAlign = "LEFT"
            left_cell = Table([[logo], [left_cell]], colWidths=[4.4 * inch])
            left_cell.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 6),
            ]))
        except Exception as exc:
            logger.warning("PDF logo skipped: %s", exc)
    right_cell = Paragraph(
        f"<b>{title.upper()}</b><br/>{number}",
        styles["EdDoc"],
    )
    table = Table([[left_cell, right_cell]], colWidths=[4.4 * inch, 2.6 * inch])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [table, Spacer(1, 8), HRFlowable(width="100%", thickness=2, color=GOLD), Spacer(1, 12)]


def _party_block(
    brand: EditionPdfBrand,
    document: dict,
    *,
    customer: Optional[dict],
    styles,
    valid_label: str,
    valid_value: str,
) -> Table:
    customer = customer if isinstance(customer, dict) else {}
    client_name = (
        document.get("customer_name")
        or document.get("client_name")
        or customer.get("name")
        or "Cliente"
    )
    nit = client_nit(document, customer)
    client_lines = [f"<b>{LABELS['cliente']}</b>", str(client_name)]
    if nit:
        client_lines.append(f"{LABELS['nit']}: {nit}")
    for key in ("customer_email", "client_email", "email"):
        val = document.get(key) or customer.get(key if key == "email" else "email")
        if val:
            client_lines.append(str(val))
            break
    for key in ("customer_phone", "client_phone", "phone"):
        val = document.get(key) or customer.get("phone")
        if val:
            client_lines.append(str(val))
            break
    addr = document.get("customer_address") or document.get("client_address") or customer.get("address")
    if addr:
        client_lines.append(str(addr))

    created = _fmt_date(document.get("created_at") or document.get("invoice_date") or document.get("updated_at"))
    meta_lines = [
        f"<b>{LABELS['fecha']}:</b> {created}",
        f"<b>{valid_label}:</b> {valid_value}",
    ]
    if brand.nit:
        meta_lines.append(f"<b>{LABELS['nit']} emisor:</b> {brand.nit}")
    if nit:
        meta_lines.append(f"<b>{LABELS['nit']} cliente:</b> {nit}")

    table = Table(
        [[
            Paragraph("<br/>".join(client_lines), styles["EdBody"]),
            Paragraph("<br/>".join(meta_lines), styles["EdBody"]),
        ]],
        colWidths=[3.6 * inch, 3.4 * inch],
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.4, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _items_table(items: list[dict], styles) -> Table:
    body, heavy = _fonts()
    header = [
        Paragraph(f"<b>#</b>", styles["EdHead"]),
        Paragraph(f"<b>{LABELS['descripcion']}</b>", styles["EdHead"]),
        Paragraph(f"<b>{LABELS['cant']}</b>", styles["EdHead"]),
        Paragraph(f"<b>{LABELS['precio']}</b>", styles["EdHead"]),
        Paragraph(f"<b>{LABELS['importe']}</b>", styles["EdHead"]),
    ]
    rows = [header]
    if not items:
        rows.append(["", Paragraph("Sin ítems", styles["EdBody"]), "", "", ""])
    for idx, item in enumerate(items, 1):
        qty = _num(item.get("quantity", 1), 1) or 1
        qty_text = str(int(qty)) if float(qty).is_integer() else f"{qty:g}"
        amount = _line_amount(item)
        rate = _num(item.get("unit_price", item.get("rate", 0)))
        if rate == 0 and qty:
            rate = amount / qty
        rows.append([
            str(idx),
            Paragraph(_line_description(item), styles["EdBody"]),
            qty_text,
            _money(rate),
            _money(amount),
        ])
    table = Table(rows, colWidths=[0.4 * inch, 3.9 * inch, 0.6 * inch, 1.05 * inch, 1.05 * inch], repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), heavy),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), body),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE),
    ]
    for i in range(2, len(rows), 2):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    table.setStyle(TableStyle(style_cmds))
    return table


def _totals(document: dict, brand: EditionPdfBrand, styles) -> Table:
    items = list(document.get("line_items") or [])
    subtotal = _num(document.get("subtotal"))
    if subtotal == 0 and items:
        subtotal = round(sum(_line_amount(item) for item in items), 2)
    iva_rate = document_iva_rate(document, brand)
    if document.get("tax_amount") not in (None, ""):
        iva_amount = cop_round(document.get("tax_amount"))
    else:
        iva_amount = cop_round(subtotal * iva_rate)
    total = _num(document.get("total"))
    if total == 0:
        total = subtotal + iva_amount
    iva_pct = int(round(iva_rate * 100))
    rows = [
        ["", f"{LABELS['subtotal']}:", _money(subtotal)],
        ["", f"{LABELS['iva']} ({iva_pct}%):", _money(iva_amount)],
        ["", Paragraph(f"<b>{LABELS['total']}:</b>", styles["EdRight"]),
         Paragraph(f"<b>{_money(total)}</b>", styles["EdRight"])],
    ]
    table = Table(rows, colWidths=[3.5 * inch, 2.0 * inch, 1.5 * inch])
    table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEABOVE", (1, -1), (-1, -1), 1, INK),
    ]))
    return table


def render_edition_document_pdf(
    document: dict,
    *,
    kind: str = "cotizacion",
    customer: Optional[dict] = None,
) -> bytes:
    kind = "factura" if kind == "factura" else "cotizacion"
    brand = resolve_edition_pdf_brand(document)
    title = LABELS[kind]
    number = str(
        document.get("quote_number")
        or document.get("invoice_number")
        or document.get("id")
        or title
    )
    if kind == "factura":
        valid_label = "Vence"
        valid_value = _fmt_date(document.get("due_date")) if document.get("due_date") else "—"
    else:
        valid_label = LABELS["validez"]
        if document.get("expires_at"):
            valid_value = _fmt_date(document.get("expires_at"))
        else:
            days = int(document.get("valid_days") or 30)
            valid_value = f"{days} días"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.65 * inch, bottomMargin=0.65 * inch,
        title=f"{title} {number}",
        author=brand.name,
        creator=brand.name,
    )
    styles = _styles()
    story = []
    story.extend(_header_flowables(brand, title, number, styles))
    story.append(_party_block(
        brand, document, customer=customer, styles=styles,
        valid_label=valid_label, valid_value=valid_value,
    ))
    story.append(Spacer(1, 14))
    story.append(_items_table(list(document.get("line_items") or []), styles))
    story.append(Spacer(1, 14))
    story.append(_totals(document, brand, styles))
    terms = document.get("terms") or document.get("payment_terms") or document.get("notes")
    if terms:
        story.append(Spacer(1, 16))
        story.append(Paragraph(str(terms), styles["EdBody"]))
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.4, color=RULE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"{brand.name} · {LABELS['nit']} {brand.nit or '—'}",
        styles["EdCenter"],
    ))
    doc.build(story)
    return buf.getvalue()


def _maybe_save(pdf_bytes: bytes, filename: str, save: bool) -> None:
    """Write under EMPIRE_DATA_DIR only. Never touch a live Workroom path."""
    if not save:
        return
    from app.edition import data_root_or_none
    from app.services.data_paths import quote_pdf_dir

    root = data_root_or_none()
    if root is None:
        return
    pdf_dir = quote_pdf_dir().resolve()
    try:
        pdf_dir.relative_to(root.resolve())
    except ValueError:
        logger.warning("Skipped PDF save outside EMPIRE_DATA_DIR: %s", pdf_dir)
        return
    os.makedirs(pdf_dir, exist_ok=True)
    path = pdf_dir / filename
    path.write_bytes(pdf_bytes)


def generate_edition_quote_pdf(
    quote_id: str,
    *,
    quote: Optional[dict] = None,
    save: bool = False,
) -> bytes:
    if quote is None:
        from app.services.quote_service import get_quote

        quote = get_quote(quote_id)
    if not quote:
        raise FileNotFoundError(f"Quote {quote_id} not found")
    pdf_bytes = render_edition_document_pdf(quote, kind="cotizacion")
    number = quote.get("quote_number") or quote_id
    _maybe_save(pdf_bytes, f"{number}.pdf", save)
    return pdf_bytes


def generate_edition_invoice_pdf_bytes(
    invoice: dict,
    *,
    customer: Optional[dict] = None,
    save: bool = False,
) -> bytes:
    pdf_bytes = render_edition_document_pdf(invoice, kind="factura", customer=customer)
    number = invoice.get("invoice_number") or invoice.get("id") or "factura"
    _maybe_save(pdf_bytes, f"{number}.pdf", save)
    return pdf_bytes
