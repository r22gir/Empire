"""
Quote PDF Service — Generate branded PDF quotes using reportlab.
Includes: header, client info, line items with details, totals, terms, footer.
"""
import io
import os
import json
import logging
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from app.services.quote_service import get_quote

logger = logging.getLogger(__name__)

# ── Brand colors ───────────────────────────────────────────────
BRAND_PRIMARY = colors.HexColor("#1a1a2e")
BRAND_ACCENT = colors.HexColor("#e94560")
BRAND_LIGHT = colors.HexColor("#f5f5f5")
BRAND_TEXT = colors.HexColor("#333333")
BRAND_MUTED = colors.HexColor("#888888")

# ── Business info ──────────────────────────────────────────────
COMPANY_NAME = "Empire Workroom"
COMPANY_ADDRESS = "Washington, DC"
COMPANY_PHONE = "(202) 555-0100"
COMPANY_EMAIL = "info@empirebox.store"
COMPANY_WEBSITE = "empirebox.store"


def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'BrandTitle', parent=styles['Title'],
        fontSize=24, textColor=BRAND_PRIMARY, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'],
        fontSize=13, textColor=BRAND_PRIMARY, spaceBefore=12, spaceAfter=6,
        borderWidth=0, borderColor=BRAND_ACCENT, borderPadding=4,
    ))
    styles.add(ParagraphStyle(
        'ItemDesc', parent=styles['Normal'],
        fontSize=9, textColor=BRAND_TEXT, leading=12,
    ))
    styles.add(ParagraphStyle(
        'SmallMuted', parent=styles['Normal'],
        fontSize=8, textColor=BRAND_MUTED, leading=10,
    ))
    styles.add(ParagraphStyle(
        'RightAlign', parent=styles['Normal'],
        fontSize=10, alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=BRAND_MUTED, alignment=TA_CENTER,
    ))
    return styles


def generate_quote_pdf(quote_id: str) -> bytes:
    """Generate a branded PDF for a quote. Returns PDF bytes."""
    quote = get_quote(quote_id)
    if not quote:
        raise FileNotFoundError(f"Quote {quote_id} not found")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = _get_styles()
    story = []

    # ── Header ─────────────────────────────────────────────────
    header_data = [
        [Paragraph(f"<b>{COMPANY_NAME}</b>", styles['BrandTitle']),
         Paragraph(f"<b>QUOTE</b><br/><font size=10 color='#888888'>#{quote.get('quote_number', quote_id)}</font>",
                   ParagraphStyle('QNum', parent=styles['Normal'], fontSize=18,
                                  alignment=TA_RIGHT, textColor=BRAND_PRIMARY))],
    ]
    header_table = Table(header_data, colWidths=[4 * inch, 3 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)

    # Company details
    story.append(Paragraph(
        f"{COMPANY_ADDRESS} | {COMPANY_PHONE} | {COMPANY_WEBSITE}",
        styles['SmallMuted']
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_ACCENT))
    story.append(Spacer(1, 12))

    # ── Client + Quote Info ────────────────────────────────────
    created = (quote.get('created_at') or '')[:10]
    expires = (quote.get('expires_at') or '')[:10]

    info_left = f"""<b>Prepared For:</b><br/>
{quote.get('customer_name', 'Customer')}<br/>
{quote.get('customer_email', '') or ''}<br/>
{quote.get('customer_phone', '') or ''}<br/>
{quote.get('customer_address', '') or ''}"""

    info_right = f"""<b>Date:</b> {created}<br/>
<b>Valid Until:</b> {expires}<br/>
<b>Status:</b> {quote.get('status', 'draft').upper()}<br/>
<b>Project:</b> {quote.get('project_name', '') or ''}"""

    info_data = [[Paragraph(info_left, styles['ItemDesc']),
                  Paragraph(info_right, styles['ItemDesc'])]]
    info_table = Table(info_data, colWidths=[3.5 * inch, 3.5 * inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), BRAND_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, BRAND_MUTED),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    # ── Line Items ─────────────────────────────────────────────
    story.append(Paragraph("Line Items", styles['SectionHeader']))

    items = quote.get('line_items', [])
    if items:
        # Header row
        item_data = [['#', 'Description', 'Qty', 'Unit Price', 'Subtotal']]

        for idx, item in enumerate(items, 1):
            desc_parts = []
            desc = item.get('description', '') or item.get('item_type', '')
            if desc:
                desc_parts.append(f"<b>{desc}</b>")
            if item.get('room'):
                desc_parts.append(f"Room: {item['room']}")
            if item.get('item_type') and item.get('item_style'):
                desc_parts.append(f"{item['item_type']} — {item['item_style']}")
            if item.get('width') or item.get('height'):
                w = item.get('width', 0) or 0
                h = item.get('height', 0) or 0
                if w or h:
                    desc_parts.append(f"Dimensions: {w}\" × {h}\"")
            if item.get('fabric_name'):
                desc_parts.append(f"Fabric: {item['fabric_name']}")
            if item.get('yards_needed') and float(item.get('yards_needed', 0) or 0) > 0:
                yds = item['yards_needed']
                ppyd = item.get('fabric_price_per_yard', 0) or 0
                desc_parts.append(f"Yardage: {yds} yds @ ${ppyd:.2f}/yd")
            if item.get('labor_hours') and float(item.get('labor_hours', 0) or 0) > 0:
                desc_parts.append(f"Labor: {item['labor_hours']}hrs @ ${item.get('labor_rate', 0) or 0:.2f}/hr")

            desc_text = Paragraph("<br/>".join(desc_parts) if desc_parts else "Item",
                                  styles['ItemDesc'])

            qty = item.get('quantity', 1) or 1
            unit_price = float(item.get('unit_price', 0) or 0)
            subtotal = float(item.get('subtotal', 0) or 0)
            if subtotal == 0:
                subtotal = round(qty * unit_price, 2)

            item_data.append([
                str(idx),
                desc_text,
                str(qty),
                f"${unit_price:,.2f}",
                f"${subtotal:,.2f}",
            ])

        col_widths = [0.4 * inch, 4.1 * inch, 0.5 * inch, 1 * inch, 1 * inch]
        item_table = Table(item_data, colWidths=col_widths, repeatRows=1)
        item_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            # Alternating rows
            *[('BACKGROUND', (0, i), (-1, i), BRAND_LIGHT)
              for i in range(2, len(item_data), 2)],
            # Grid
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, BRAND_MUTED),
            # Alignment
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ]))
        story.append(item_table)
    else:
        story.append(Paragraph("<i>No line items</i>", styles['ItemDesc']))

    story.append(Spacer(1, 16))

    # ── Totals ─────────────────────────────────────────────────
    subtotal = float(quote.get('subtotal', 0) or 0)
    discount = float(quote.get('discount_amount', 0) or 0)
    tax_rate = float(quote.get('tax_rate', 0) or 0)
    tax_amount = float(quote.get('tax_amount', 0) or 0)
    total = float(quote.get('total', 0) or 0)
    deposit_required = float(quote.get('deposit_required', 0) or 0)
    deposit_paid = float(quote.get('deposit_paid', 0) or 0)
    balance_due = float(quote.get('balance_due', 0) or 0)

    totals_data = []
    totals_data.append(['', 'Subtotal:', f"${subtotal:,.2f}"])
    if discount > 0:
        dtype = quote.get('discount_type', 'dollar')
        dlabel = f"Discount ({discount}%)" if dtype == 'percent' else "Discount"
        totals_data.append(['', dlabel + ':', f"-${discount:,.2f}"])
    if tax_rate > 0:
        totals_data.append(['', f'Tax ({tax_rate*100:.1f}%):', f"${tax_amount:,.2f}"])
    totals_data.append(['', Paragraph("<b>TOTAL:</b>", styles['RightAlign']),
                        Paragraph(f"<b>${total:,.2f}</b>", styles['RightAlign'])])
    if deposit_required > 0:
        pct = quote.get('deposit_percent', 50) or 50
        totals_data.append(['', f'Deposit Required ({pct:.0f}%):', f"${deposit_required:,.2f}"])
    if deposit_paid > 0:
        totals_data.append(['', 'Deposit Paid:', f"-${deposit_paid:,.2f}"])
    if balance_due > 0:
        totals_data.append(['', Paragraph("<b>Balance Due:</b>", styles['RightAlign']),
                            Paragraph(f"<b>${balance_due:,.2f}</b>", styles['RightAlign'])])

    totals_table = Table(totals_data, colWidths=[3.5 * inch, 2 * inch, 1.5 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (1, -1), (-1, -1), 1, BRAND_PRIMARY),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 20))

    # ── Terms ──────────────────────────────────────────────────
    terms = quote.get('terms') or quote.get('payment_terms') or \
        "50% deposit required to begin fabrication. Balance due upon installation. All sales are final."
    if terms:
        story.append(Paragraph("Terms & Conditions", styles['SectionHeader']))
        story.append(Paragraph(terms, styles['ItemDesc']))
        story.append(Spacer(1, 12))

    # ── Approval ───────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_MUTED))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "To approve this quote, please sign below and return, or reply to this email with your approval.",
        styles['ItemDesc']
    ))
    story.append(Spacer(1, 24))

    sig_data = [
        [f"{'_' * 40}", '', f"{'_' * 20}"],
        ['Signature', '', 'Date'],
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 1 * inch, 2.5 * inch])
    sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), BRAND_MUTED),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 20))

    # ── Footer ─────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_MUTED))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Thank you for choosing {COMPANY_NAME}! | {COMPANY_PHONE} | {COMPANY_WEBSITE}",
        styles['Footer']
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    # Save PDF to disk
    pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{quote.get('quote_number', quote_id)}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Update quote with pdf_path
    try:
        from app.db.database import get_db
        with get_db() as conn:
            conn.execute("UPDATE quotes_v2 SET pdf_path = ? WHERE id = ?",
                        (pdf_path, quote_id))
    except Exception:
        pass

    logger.info(f"Generated PDF for quote {quote_id}: {pdf_path}")
    return pdf_bytes
