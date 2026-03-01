"""
Quote/Estimate CRUD router.
Stores quotes as JSON files (same pattern as chat history).
PDF generation via POST /api/v1/quotes/{id}/pdf.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
import json
import uuid
import os

router = APIRouter(prefix="/quotes", tags=["quotes"])

QUOTES_DIR = os.path.expanduser("~/Empire/data/quotes")
os.makedirs(QUOTES_DIR, exist_ok=True)

COUNTER_FILE = os.path.join(QUOTES_DIR, "_counter.json")


# ── Pydantic schemas ──────────────────────────────────────────

class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit: str = "ea"            # ea, hr, sqft, width, fixture
    rate: float = 0.0
    amount: float = 0.0         # quantity * rate (computed)
    category: str = "labor"     # labor, materials, other

class Measurements(BaseModel):
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    unit: str = "in"
    room: Optional[str] = None
    window_type: Optional[str] = None
    notes: Optional[str] = None

class DepositSchedule(BaseModel):
    deposit_percent: float = 50.0
    deposit_amount: float = 0.0
    deposit_due: Optional[str] = None   # ISO date
    balance_due: Optional[str] = None   # ISO date

class QuoteCreate(BaseModel):
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    desk_id: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    measurements: Optional[Measurements] = None
    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    total: float = 0.0
    deposit: Optional[DepositSchedule] = None
    terms: Optional[str] = None
    valid_days: int = 30
    install_date: Optional[str] = None
    notes: Optional[str] = None
    business_name: Optional[str] = None
    business_logo_url: Optional[str] = None
    rooms: Optional[list] = None           # Full room/window/upholstery hierarchy
    ai_outlines: Optional[list] = None     # AI outline analysis results
    ai_mockups: Optional[list] = None      # AI mockup proposal results
    max_analysis: Optional[str] = None     # MAX's professional analysis text

class QuoteUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    desk_id: Optional[str] = None
    line_items: Optional[list[LineItem]] = None
    measurements: Optional[Measurements] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total: Optional[float] = None
    deposit: Optional[DepositSchedule] = None
    terms: Optional[str] = None
    valid_days: Optional[int] = None
    install_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    business_name: Optional[str] = None
    business_logo_url: Optional[str] = None
    rooms: Optional[list] = None
    ai_outlines: Optional[list] = None
    ai_mockups: Optional[list] = None
    max_analysis: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────

def _next_quote_number() -> str:
    """Generate sequential quote number: EST-YYYY-001."""
    year = datetime.utcnow().year
    counter = {"year": year, "seq": 0}
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE) as f:
            counter = json.load(f)
        if counter.get("year") != year:
            counter = {"year": year, "seq": 0}
    counter["seq"] += 1
    with open(COUNTER_FILE, "w") as f:
        json.dump(counter, f)
    return f"EST-{year}-{counter['seq']:03d}"


def _quote_path(quote_id: str) -> str:
    return os.path.join(QUOTES_DIR, f"{quote_id}.json")


def _load_quote(quote_id: str) -> dict:
    path = _quote_path(quote_id)
    if not os.path.exists(path):
        raise HTTPException(404, f"Quote {quote_id} not found")
    with open(path) as f:
        return json.load(f)


def _save_quote(quote: dict):
    with open(_quote_path(quote["id"]), "w") as f:
        json.dump(quote, f, indent=2, default=str)


def _compute_financials(data: dict) -> dict:
    """Recalculate line item amounts, subtotal, tax, total."""
    items = data.get("line_items", [])
    for item in items:
        item["amount"] = round(item.get("quantity", 1) * item.get("rate", 0), 2)
    subtotal = round(sum(i["amount"] for i in items), 2)

    # If no line_items but rooms exist, compute subtotal from room prices
    if subtotal == 0 and data.get("rooms"):
        for room in data["rooms"]:
            for w in room.get("windows", []):
                subtotal += w.get("price", 0)
            for u in room.get("upholstery", []):
                subtotal += u.get("price", 0)
        subtotal = round(subtotal, 2)

    tax_rate = data.get("tax_rate", 0.0)
    tax_amount = round(subtotal * tax_rate, 2)
    discount = data.get("discount_amount", 0.0)
    total = round(subtotal + tax_amount - discount, 2)

    data["line_items"] = items
    data["subtotal"] = subtotal
    data["tax_amount"] = tax_amount
    data["total"] = total

    # Update deposit amount if percent-based
    dep = data.get("deposit")
    if dep and dep.get("deposit_percent"):
        dep["deposit_amount"] = round(total * dep["deposit_percent"] / 100, 2)
        data["deposit"] = dep

    return data


# ── CRUD Endpoints ────────────────────────────────────────────

@router.post("")
async def create_quote(payload: QuoteCreate):
    """Create a new quote/estimate."""
    quote_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    quote = {
        "id": quote_id,
        "quote_number": _next_quote_number(),
        "status": "draft",
        **payload.model_dump(),
        "created_at": now,
        "updated_at": now,
        "sent_at": None,
        "accepted_at": None,
        "expires_at": (datetime.utcnow() + timedelta(days=payload.valid_days)).isoformat(),
    }

    # Convert nested models to dicts
    if quote.get("measurements") and hasattr(quote["measurements"], "model_dump"):
        quote["measurements"] = quote["measurements"].model_dump()
    if quote.get("deposit") and hasattr(quote["deposit"], "model_dump"):
        quote["deposit"] = quote["deposit"].model_dump()
    quote["line_items"] = [
        i.model_dump() if hasattr(i, "model_dump") else i
        for i in quote.get("line_items", [])
    ]

    quote = _compute_financials(quote)
    _save_quote(quote)
    return {"status": "created", "quote": quote}


@router.get("")
async def list_quotes(status: Optional[str] = None):
    """List all quotes, optionally filtered by status."""
    quotes = []
    for fname in os.listdir(QUOTES_DIR):
        if not fname.endswith(".json") or fname.startswith("_"):
            continue
        with open(os.path.join(QUOTES_DIR, fname)) as f:
            q = json.load(f)
        if status and q.get("status") != status:
            continue
        quotes.append(q)
    quotes.sort(key=lambda q: q.get("created_at", ""), reverse=True)
    return {"quotes": quotes, "count": len(quotes)}


@router.get("/{quote_id}")
async def get_quote(quote_id: str):
    """Get a single quote by ID."""
    return _load_quote(quote_id)


@router.patch("/{quote_id}")
async def update_quote(quote_id: str, payload: QuoteUpdate):
    """Update an existing quote."""
    quote = _load_quote(quote_id)
    updates = payload.model_dump(exclude_unset=True)

    # Convert nested models
    if "line_items" in updates and updates["line_items"] is not None:
        updates["line_items"] = [
            i.model_dump() if hasattr(i, "model_dump") else i
            for i in updates["line_items"]
        ]
    if "measurements" in updates and updates["measurements"] is not None:
        updates["measurements"] = (
            updates["measurements"].model_dump()
            if hasattr(updates["measurements"], "model_dump")
            else updates["measurements"]
        )
    if "deposit" in updates and updates["deposit"] is not None:
        updates["deposit"] = (
            updates["deposit"].model_dump()
            if hasattr(updates["deposit"], "model_dump")
            else updates["deposit"]
        )

    quote.update(updates)
    quote["updated_at"] = datetime.utcnow().isoformat()

    # Recalculate if line items or tax changed
    if any(k in updates for k in ("line_items", "tax_rate", "discount_amount")):
        quote = _compute_financials(quote)

    # Update expiry if valid_days changed
    if "valid_days" in updates:
        created = datetime.fromisoformat(quote["created_at"])
        quote["expires_at"] = (created + timedelta(days=updates["valid_days"])).isoformat()

    _save_quote(quote)
    return {"status": "updated", "quote": quote}


@router.delete("/{quote_id}")
async def delete_quote(quote_id: str):
    """Delete a quote."""
    path = _quote_path(quote_id)
    if not os.path.exists(path):
        raise HTTPException(404, f"Quote {quote_id} not found")
    os.remove(path)
    return {"status": "deleted", "id": quote_id}


@router.post("/{quote_id}/send")
async def send_quote(quote_id: str):
    """Mark quote as sent."""
    quote = _load_quote(quote_id)
    quote["status"] = "sent"
    quote["sent_at"] = datetime.utcnow().isoformat()
    quote["updated_at"] = datetime.utcnow().isoformat()
    _save_quote(quote)
    return {"status": "sent", "quote": quote}


@router.post("/{quote_id}/accept")
async def accept_quote(quote_id: str):
    """Mark quote as accepted."""
    quote = _load_quote(quote_id)
    quote["status"] = "accepted"
    quote["accepted_at"] = datetime.utcnow().isoformat()
    quote["updated_at"] = datetime.utcnow().isoformat()
    _save_quote(quote)
    return {"status": "accepted", "quote": quote}


def _build_window_drawing(w: dict) -> str:
    """Generate an inline SVG dimensional drawing for a single window from its specs."""
    name = w.get("name", "Window")
    w_in = w.get("width", 48)
    h_in = w.get("height", 60)
    mount = w.get("mountType", "wall").title()
    treatment = w.get("treatmentType", "")
    lining = w.get("liningType", "standard").replace("-", " ").title()
    hardware = w.get("hardwareType", "none").replace("-", " ").title()
    motor = w.get("motorization", "none").title()
    qty = w.get("quantity", 1)

    treatment_labels = {
        'ripplefold': 'Ripplefold', 'pinch-pleat': 'Pinch Pleat', 'rod-pocket': 'Rod Pocket',
        'grommet': 'Grommet', 'roman-shade': 'Roman Shade', 'roller-shade': 'Roller Shade',
    }
    ttype = treatment_labels.get(treatment, treatment.replace("-", " ").title())

    # Treatment-specific drape pattern (decorative lines inside window)
    is_shade = treatment in ('roman-shade', 'roller-shade')

    # Scale: 2.5px per inch, min 100px
    scale = 2.5
    win_w = max(w_in * scale, 100)
    win_h = max(h_in * scale, 120)
    pad = 55
    svg_w = win_w + pad * 2
    info_h = 60  # space for spec text below
    svg_h = win_h + pad * 2 + info_h

    wx = pad
    wy = pad
    cx = wx + win_w / 2
    cy = wy + win_h / 2

    svg = f"""<div style="display:inline-block;vertical-align:top;margin:6px 8px 6px 0;page-break-inside:avoid">
    <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" style="max-width:100%;background:#fafbfd;border:1px solid #e0e0e0;border-radius:6px">
      <!-- Title -->
      <text x="{svg_w/2}" y="16" text-anchor="middle" font-size="10" fill="#1a1a2e" font-weight="700">{name}{f' (×{qty})' if qty > 1 else ''}</text>
      <!-- Window frame -->
      <rect x="{wx}" y="{wy}" width="{win_w}" height="{win_h}" fill="#e8f4fd" stroke="#1a1a2e" stroke-width="2" rx="2"/>"""

    # Treatment decoration inside the window
    if is_shade:
        # Horizontal fold lines for shades
        folds = int(win_h / 25)
        for i in range(1, max(folds, 3)):
            fy = wy + (win_h * i / max(folds, 3))
            svg += f'<line x1="{wx+6}" y1="{fy}" x2="{wx+win_w-6}" y2="{fy}" stroke="#b0c4d8" stroke-width="0.8" stroke-dasharray="4 3"/>'
        svg += f'<text x="{cx}" y="{cy+3}" text-anchor="middle" font-size="9" fill="#6a8caf" font-style="italic">{ttype}</text>'
    else:
        # Vertical drape lines for curtains
        panels = max(int(win_w / 18), 4)
        for i in range(panels):
            dx = wx + 8 + (win_w - 16) * i / (panels - 1)
            # Slight wave using 2 control points
            svg += f'<path d="M{dx},{wy+8} Q{dx+3},{wy+win_h*0.35} {dx-2},{wy+win_h*0.65} Q{dx+2},{wy+win_h*0.85} {dx},{wy+win_h-6}" fill="none" stroke="#b0c4d8" stroke-width="0.7"/>'
        svg += f'<text x="{cx}" y="{cy+3}" text-anchor="middle" font-size="9" fill="#6a8caf" font-style="italic">{ttype}</text>'

    # Width dimension (top)
    svg += f"""
      <line x1="{wx}" y1="{wy-12}" x2="{wx+win_w}" y2="{wy-12}" stroke="#D4AF37" stroke-width="1.2"/>
      <line x1="{wx}" y1="{wy-18}" x2="{wx}" y2="{wy-6}" stroke="#D4AF37" stroke-width="0.8"/>
      <line x1="{wx+win_w}" y1="{wy-18}" x2="{wx+win_w}" y2="{wy-6}" stroke="#D4AF37" stroke-width="0.8"/>
      <text x="{cx}" y="{wy-17}" text-anchor="middle" font-size="11" fill="#D4AF37" font-weight="bold">{w_in}"</text>"""

    # Height dimension (right)
    svg += f"""
      <line x1="{wx+win_w+12}" y1="{wy}" x2="{wx+win_w+12}" y2="{wy+win_h}" stroke="#D4AF37" stroke-width="1.2"/>
      <line x1="{wx+win_w+6}" y1="{wy}" x2="{wx+win_w+18}" y2="{wy}" stroke="#D4AF37" stroke-width="0.8"/>
      <line x1="{wx+win_w+6}" y1="{wy+win_h}" x2="{wx+win_w+18}" y2="{wy+win_h}" stroke="#D4AF37" stroke-width="0.8"/>
      <text x="{wx+win_w+26}" y="{cy+4}" text-anchor="start" font-size="11" fill="#D4AF37" font-weight="bold">{h_in}"</text>"""

    # Mount indicator (small triangle/bracket at top)
    if mount.lower() == 'ceiling':
        svg += f'<line x1="{wx}" y1="{wy-3}" x2="{wx+win_w}" y2="{wy-3}" stroke="#666" stroke-width="3"/>'
        svg += f'<text x="{wx-2}" y="{wy-5}" font-size="7" fill="#888">CEIL</text>'
    elif mount.lower() == 'inside':
        svg += f'<rect x="{wx-3}" y="{wy-3}" width="{win_w+6}" height="{win_h+6}" fill="none" stroke="#999" stroke-width="1" stroke-dasharray="3 2" rx="1"/>'

    # Spec text below drawing
    spec_y = wy + win_h + 18
    svg += f'<text x="{svg_w/2}" y="{spec_y}" text-anchor="middle" font-size="8.5" fill="#444">{ttype} · {lining} · {mount} Mount</text>'
    svg += f'<text x="{svg_w/2}" y="{spec_y+13}" text-anchor="middle" font-size="8" fill="#777">{hardware}{" · " + motor + " Motor" if motor.lower() != "none" else ""}</text>'
    svg += f'<text x="{svg_w/2}" y="{spec_y+26}" text-anchor="middle" font-size="9" fill="#D4AF37" font-weight="bold">${w.get("price", 0):,.2f}</text>'

    svg += "</svg>"

    # AI analysis notes below the SVG (if available)
    ai = w.get("aiAnalysis")
    if ai:
        recs = ai.get("recommendations") or []
        window_type = ai.get("windowType", "")
        confidence = ai.get("confidence", 0)
        if recs or window_type:
            svg += f'<div style="margin-top:4px;padding:6px 8px;background:#f8f5ff;border:1px solid rgba(139,92,246,0.2);border-radius:5px;font-size:0.7em;max-width:{int(svg_w)}px">'
            svg += f'<span style="color:#8B5CF6;font-weight:700">AI Notes</span>'
            if window_type:
                svg += f' <span style="color:#666">· {window_type}</span>'
            if confidence:
                svg += f' <span style="color:#22c55e">({confidence}%)</span>'
            for rec in recs[:3]:
                if rec:
                    svg += f'<br><span style="color:#555">→ {rec}</span>'
            svg += '</div>'

    svg += "</div>"
    return svg


def _build_upholstery_drawing(u: dict) -> str:
    """Generate a simple inline SVG diagram for an upholstery piece."""
    name = u.get("name", "Piece")
    ftype = u.get("furnitureType", "sofa").title()
    w_in = u.get("width", 72)
    d_in = u.get("depth", 36)
    h_in = u.get("height", 34)
    fabric = f"{u.get('fabricYards', 0)} yd {u.get('fabricType', '').title()}"
    labor = u.get("laborType", "standard").title()
    cushions = u.get("cushionCount", 0)

    svg_w = 200
    svg_h = 140
    # Simple front-view rectangle with cushion indicators
    bx, by, bw, bh = 30, 35, 140, 55
    cx_mid = bx + bw / 2

    svg = f"""<div style="display:inline-block;vertical-align:top;margin:6px 8px 6px 0;page-break-inside:avoid">
    <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" style="max-width:100%;background:#fafbfd;border:1px solid #e0e0e0;border-radius:6px">
      <text x="{svg_w/2}" y="14" text-anchor="middle" font-size="10" fill="#1a1a2e" font-weight="700">{name}</text>
      <text x="{svg_w/2}" y="26" text-anchor="middle" font-size="8" fill="#888">{ftype} · {w_in}"W × {d_in}"D × {h_in}"H</text>
      <!-- Body -->
      <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="#f0ebe0" stroke="#8B7355" stroke-width="1.5" rx="4"/>
      <!-- Back -->
      <rect x="{bx+4}" y="{by-12}" width="{bw-8}" height="14" fill="#e8e0d0" stroke="#8B7355" stroke-width="1" rx="3"/>"""

    # Cushion lines
    if cushions > 0:
        cw = (bw - 10) / min(cushions, 5)
        for i in range(min(cushions, 5)):
            cx = bx + 5 + i * cw
            svg += f'<rect x="{cx+1}" y="{by+4}" width="{cw-2}" height="{bh-8}" fill="none" stroke="#a89070" stroke-width="0.7" rx="2"/>'

    # Arms
    svg += f'<rect x="{bx-8}" y="{by+5}" width="10" height="{bh-10}" fill="#e8e0d0" stroke="#8B7355" stroke-width="1" rx="3"/>'
    svg += f'<rect x="{bx+bw-2}" y="{by+5}" width="10" height="{bh-10}" fill="#e8e0d0" stroke="#8B7355" stroke-width="1" rx="3"/>'

    # Specs below
    svg += f'<text x="{svg_w/2}" y="{by+bh+16}" text-anchor="middle" font-size="8" fill="#555">{fabric} · {labor} · {cushions} cushion{"s" if cushions != 1 else ""}</text>'
    svg += f'<text x="{svg_w/2}" y="{by+bh+29}" text-anchor="middle" font-size="9" fill="#D4AF37" font-weight="bold">${u.get("price", 0):,.2f}</text>'

    svg += "</svg>"

    # AI analysis notes
    ai = u.get("aiAnalysis")
    if ai:
        style = ai.get("style", "")
        suggested = ai.get("suggestedLaborType", "")
        questions = ai.get("questions") or []
        if style or questions:
            svg += f'<div style="margin-top:4px;padding:6px 8px;background:#fffcf0;border:1px solid rgba(212,175,55,0.2);border-radius:5px;font-size:0.7em;max-width:{svg_w}px">'
            svg += f'<span style="color:#D4AF37;font-weight:700">AI Notes</span>'
            if style:
                svg += f' <span style="color:#666">· {style}</span>'
            if suggested:
                svg += f'<br><span style="color:#555">→ Suggested: {suggested} labor</span>'
            if ai.get("newFoamRecommended"):
                svg += f'<br><span style="color:#e67e22">→ New foam recommended</span>'
            for q in questions[:2]:
                svg += f'<br><span style="color:#888;font-style:italic">? {q}</span>'
            svg += '</div>'

        # AI-Generated Upholstery Illustration
        gen_img = ai.get("generated_image")
        if gen_img:
            svg += f"""<div style="margin-top:8px;text-align:center">
            <p style="font-size:0.75em;color:#D4AF37;font-weight:700;margin-bottom:4px">AI Before/After Illustration</p>
            <img src="{gen_img}" style="max-width:100%;max-height:250px;border-radius:8px;border:1px solid #ddd;object-fit:contain" />
            </div>"""

    svg += "</div>"
    return svg


def _build_rooms_html(rooms: list) -> str:
    """Build rich room-by-room HTML for PDF with spec tables + dimensional drawings."""
    html = ""
    treatment_labels = {
        'ripplefold': 'Ripplefold', 'pinch-pleat': 'Pinch Pleat', 'rod-pocket': 'Rod Pocket',
        'grommet': 'Grommet', 'roman-shade': 'Roman Shade', 'roller-shade': 'Roller Shade',
    }
    for room in rooms:
        windows = room.get("windows", [])
        upholstery = room.get("upholstery", [])
        room_total = sum(w.get("price", 0) for w in windows) + sum(u.get("price", 0) for u in upholstery)

        html += f'<h3 style="color:#D4AF37;margin:24px 0 8px;border-bottom:2px solid #D4AF37;padding-bottom:4px">{room["name"]}</h3>'

        if windows:
            html += """<table style="margin-bottom:12px"><thead><tr>
                <th>Window</th><th>Size</th><th>Treatment</th><th>Lining</th>
                <th>Hardware</th><th>Motor</th><th>Mount</th><th>Qty</th><th style="text-align:right">Price</th>
            </tr></thead><tbody>"""
            for w in windows:
                ttype = treatment_labels.get(w.get("treatmentType", ""), w.get("treatmentType", ""))
                html += f"""<tr>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{w.get('name', '')}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{w.get('width', 0)}" × {w.get('height', 0)}"</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{ttype}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{w.get('liningType', 'standard').replace('-', ' ').title()}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{w.get('hardwareType', 'none').replace('-', ' ').title()}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{w.get('motorization', 'none').title()}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{w.get('mountType', 'wall').title()}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{w.get('quantity', 1)}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">${w.get('price', 0):,.2f}</td>
                </tr>"""
            html += "</tbody></table>"

            # Dimensional drawings for each window
            html += '<div style="margin:8px 0 16px;page-break-inside:avoid">'
            html += '<p style="font-size:0.75em;color:#888;margin-bottom:4px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Dimensional Drawings</p>'
            for w in windows:
                html += _build_window_drawing(w)
            html += '</div>'

        if upholstery:
            html += """<table style="margin-bottom:12px"><thead><tr>
                <th>Piece</th><th>Type</th><th>Fabric</th><th>Labor</th>
                <th>Cushions</th><th style="text-align:right">Price</th>
            </tr></thead><tbody>"""
            for u in upholstery:
                html += f"""<tr>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{u.get('name', '')}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{u.get('furnitureType', '').title()}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{u.get('fabricYards', 0)} yd {u.get('fabricType', '').title()}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee">{u.get('laborType', '').title()}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{u.get('cushionCount', 0)}</td>
                    <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">${u.get('price', 0):,.2f}</td>
                </tr>"""
            html += "</tbody></table>"

            # Upholstery drawings
            html += '<div style="margin:8px 0 16px;page-break-inside:avoid">'
            for u in upholstery:
                html += _build_upholstery_drawing(u)
            html += '</div>'

        html += f'<p style="text-align:right;font-weight:600;color:#333">Room Subtotal: ${room_total:,.2f}</p>'

    return html


def _build_outline_svg(outline: dict) -> str:
    """Build SVG dimensional drawing from AI outline data, with photo if available."""
    wo = outline.get("windowOpening") or {}
    cl = outline.get("clearances") or {}
    mt = outline.get("mounting") or {}
    obs = outline.get("obstructions") or []
    room_name = outline.get("roomName", "")
    photo = outline.get("photo")  # base64 data URL from uploaded image

    w_in = wo.get("width", 48)
    h_in = wo.get("height", 60)
    above = cl.get("above_window", 0)
    below = cl.get("below_window", 0)
    left = cl.get("left_wall", 0)
    right = cl.get("right_wall", 0)

    # Scale: 1 inch = 3px, minimum 400px wide
    scale = 3
    win_w = max(w_in * scale, 120)
    win_h = max(h_in * scale, 150)
    pad = 80
    svg_w = win_w + pad * 2
    svg_h = win_h + pad * 2 + 50

    # Positions
    wx = pad
    wy = pad
    cx = wx + win_w / 2
    cy = wy + win_h / 2

    svg = f"""<div style="margin:16px 0;page-break-inside:avoid">
    <h4 style="color:#1a1a2e;margin-bottom:8px">Dimensional Plan{f' — {room_name}' if room_name else ''}</h4>"""

    # Embed uploaded photo if available
    if photo:
        svg += f"""<div style="margin-bottom:12px;text-align:center">
        <p style="font-size:0.8em;color:#666;margin-bottom:6px;font-weight:600">Site Photo</p>
        <img src="{photo}" style="max-width:100%;max-height:400px;border-radius:8px;border:1px solid #ddd;object-fit:contain" />
        </div>"""

    svg += """<div style="background:#f5f7fa;border:1px solid #ddd;border-radius:8px;padding:16px;text-align:center">
    <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" style="max-width:100%">
      <!-- Window opening -->
      <rect x="{wx}" y="{wy}" width="{win_w}" height="{win_h}" fill="#e8f4fd" stroke="#1a1a2e" stroke-width="2"/>
      <text x="{cx}" y="{cy}" text-anchor="middle" font-size="11" fill="#1a1a2e" font-weight="600">WINDOW OPENING</text>
      <!-- Width dimension -->
      <line x1="{wx}" y1="{wy - 15}" x2="{wx + win_w}" y2="{wy - 15}" stroke="#D4AF37" stroke-width="1.5"/>
      <line x1="{wx}" y1="{wy - 22}" x2="{wx}" y2="{wy - 8}" stroke="#D4AF37" stroke-width="1"/>
      <line x1="{wx + win_w}" y1="{wy - 22}" x2="{wx + win_w}" y2="{wy - 8}" stroke="#D4AF37" stroke-width="1"/>
      <text x="{cx}" y="{wy - 20}" text-anchor="middle" font-size="12" fill="#D4AF37" font-weight="bold">{w_in}"</text>
      <!-- Height dimension -->
      <line x1="{wx + win_w + 15}" y1="{wy}" x2="{wx + win_w + 15}" y2="{wy + win_h}" stroke="#D4AF37" stroke-width="1.5"/>
      <line x1="{wx + win_w + 8}" y1="{wy}" x2="{wx + win_w + 22}" y2="{wy}" stroke="#D4AF37" stroke-width="1"/>
      <line x1="{wx + win_w + 8}" y1="{wy + win_h}" x2="{wx + win_w + 22}" y2="{wy + win_h}" stroke="#D4AF37" stroke-width="1"/>
      <text x="{wx + win_w + 30}" y="{cy + 4}" text-anchor="start" font-size="12" fill="#D4AF37" font-weight="bold">{h_in}"</text>"""

    # Clearances
    if above:
        svg += f'<text x="{cx}" y="{wy - 35}" text-anchor="middle" font-size="10" fill="#666">↑ {above}" to ceiling</text>'
    if below:
        svg += f'<text x="{cx}" y="{wy + win_h + 20}" text-anchor="middle" font-size="10" fill="#666">↓ {below}" to floor</text>'
    if left:
        svg += f'<text x="{wx - 5}" y="{cy}" text-anchor="end" font-size="10" fill="#666">{left}"</text>'
    if right:
        svg += f'<text x="{wx + win_w + 50}" y="{cy}" text-anchor="start" font-size="10" fill="#666">{right}"</text>'

    # Obstructions
    for i, obs_item in enumerate(obs[:3]):
        oy = wy + win_h + 30 + (i * 14)
        svg += f'<text x="{wx}" y="{oy}" font-size="9" fill="#c00">⚠ {obs_item.get("type", "Obstruction")}: {obs_item.get("location", "")}</text>'

    svg += "</svg></div>"

    # Mounting recommendation
    if mt:
        mount_type = mt.get("mount_type", "wall").title()
        rod_w = mt.get("rod_width", "")
        mount_h = mt.get("mounting_height", "")
        notes = mt.get("notes", "")
        svg += f"""<div style="margin-top:8px;padding:10px;background:#fffcf0;border:1px solid #D4AF37;border-radius:6px;font-size:0.85em">
            <strong>Mounting:</strong> {mount_type} mount
            {f' · Rod width: {rod_w}"' if rod_w else ''}
            {f' · Height: {mount_h}"' if mount_h else ''}
            {f'<br><em>{notes}</em>' if notes else ''}
        </div>"""

    svg += "</div>"
    return svg


def _build_mockup_html(mockup: dict) -> str:
    """Build design proposal cards from AI mockup data, with photo if available."""
    ra = mockup.get("roomAssessment") or {}
    proposals = mockup.get("proposals") or []
    recs = mockup.get("generalRecommendations") or []
    room_name = mockup.get("roomName", "")
    photo = mockup.get("photo")  # base64 data URL from uploaded image

    html = f'<div style="margin:24px 0;page-break-inside:avoid">'
    html += f'<h4 style="color:#1a1a2e;margin-bottom:8px">Design Proposals{f" — {room_name}" if room_name else ""}</h4>'

    # Embed uploaded photo if available
    if photo:
        html += f"""<div style="margin-bottom:12px;text-align:center">
        <p style="font-size:0.8em;color:#666;margin-bottom:6px;font-weight:600">Reference Photo</p>
        <img src="{photo}" style="max-width:100%;max-height:400px;border-radius:8px;border:1px solid #ddd;object-fit:contain" />
        </div>"""

    # Room assessment
    if ra:
        palette = ", ".join(ra.get("color_palette", [])) if ra.get("color_palette") else ""
        html += f"""<div style="padding:10px;background:#f5f7fa;border-radius:6px;margin-bottom:12px;font-size:0.85em">
            <strong>Room:</strong> {ra.get('room_type', '')} · <strong>Style:</strong> {ra.get('style', '')}
            · <strong>Light:</strong> {ra.get('light_level', '')} · <strong>Privacy:</strong> {ra.get('privacy_need', '')}
            {f'<br><strong>Colors:</strong> {palette}' if palette else ''}
        </div>"""

    # Proposal cards
    tier_colors = {'budget': '#22c55e', 'mid-range': '#D4AF37', 'premium': '#8B5CF6'}
    if proposals:
        html += '<div style="display:flex;gap:12px;flex-wrap:wrap">'
        for p in proposals[:3]:
            tier = p.get("tier", "").lower()
            color = tier_colors.get(tier, '#333')
            price_low = p.get("price_range_low", 0)
            price_high = p.get("price_range_high", 0)
            html += f"""<div style="flex:1;min-width:200px;border:2px solid {color};border-radius:8px;padding:12px;background:white">
                <div style="background:{color};color:white;padding:4px 10px;border-radius:4px;display:inline-block;font-size:0.75em;font-weight:700;text-transform:uppercase;margin-bottom:8px">{p.get('tier', 'Option')}</div>
                <p style="font-weight:600;margin:4px 0;font-size:0.95em">{p.get('treatment_type', '')}</p>
                <p style="font-size:0.8em;color:#666;margin:2px 0"><strong>Fabric:</strong> {p.get('fabric', '')}</p>
                <p style="font-size:0.8em;color:#666;margin:2px 0"><strong>Lining:</strong> {p.get('lining', '')}</p>
                <p style="font-size:0.8em;color:#666;margin:2px 0"><strong>Hardware:</strong> {p.get('hardware', '')}</p>
                {f"<p style='font-size:0.8em;color:#666;margin:2px 0'><strong>Extras:</strong> {', '.join(p.get('extras', []))}</p>" if p.get('extras') else ""}
                <p style="font-weight:700;color:{color};margin:8px 0 4px;font-size:1.05em">${price_low:,.0f} – ${price_high:,.0f}</p>
                <p style="font-size:0.8em;color:#888;font-style:italic;margin:4px 0">{p.get('visual_description', '')}</p>
                {f"<p style='font-size:0.75em;color:#999;margin:4px 0'>{p.get('design_rationale', '')}</p>" if p.get('design_rationale') else ""}
            </div>"""
        html += '</div>'

    # AI-Generated Mockup Images
    gen_images = mockup.get("generated_images") or []
    if gen_images:
        html += '<div style="margin-top:16px">'
        html += '<p style="font-size:0.85em;font-weight:700;color:#ec4899;margin-bottom:8px">AI-Generated Treatment Mockups</p>'
        html += '<div style="display:flex;gap:12px;flex-wrap:wrap">'
        for img in gen_images[:3]:
            tier = img.get("tier", "Mockup")
            url = img.get("url", "")
            if url:
                html += f"""<div style="flex:1;min-width:200px;text-align:center">
                    <img src="{url}" style="max-width:100%;max-height:300px;border-radius:8px;border:1px solid #ddd;object-fit:contain" />
                    <p style="font-size:0.75em;color:#666;margin-top:4px;font-weight:600">{tier}</p>
                </div>"""
        html += '</div></div>'

    # General recommendations
    if recs:
        html += '<div style="margin-top:12px;padding:10px;background:#f8f8f8;border-radius:6px;font-size:0.85em"><strong>Recommendations:</strong><ul style="margin:4px 0;padding-left:20px">'
        for r in recs:
            html += f'<li>{r}</li>'
        html += '</ul></div>'

    html += '</div>'
    return html


@router.post("/{quote_id}/pdf")
async def generate_pdf(quote_id: str):
    """Generate PDF for a quote with room-level detail, drawings, and mockups."""
    quote = _load_quote(quote_id)

    rooms = quote.get("rooms") or []
    ai_outlines = quote.get("ai_outlines") or []
    ai_mockups = quote.get("ai_mockups") or []

    # Build room-level content or fallback to flat line items
    if rooms:
        body_html = _build_rooms_html(rooms)
    else:
        items_html = ""
        for item in quote.get("line_items", []):
            items_html += f"""<tr>
                <td style="padding:8px;border-bottom:1px solid #eee">{item['description']}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:center">{item['quantity']} {item['unit']}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">${item['rate']:.2f}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">${item['amount']:.2f}</td>
            </tr>"""
        body_html = f"""<table><thead><tr>
            <th>Description</th><th>Qty</th><th>Rate</th><th style="text-align:right">Amount</th>
        </tr></thead><tbody>{items_html}</tbody></table>"""

    # AI Outline drawings
    outlines_html = ""
    for outline in ai_outlines:
        outlines_html += _build_outline_svg(outline)

    # AI Mockup proposals
    mockups_html = ""
    for mockup in ai_mockups:
        mockups_html += _build_mockup_html(mockup)

    # MAX's Analysis summary — collect all AI notes into one fun section
    max_notes = []
    if rooms:
        for room in rooms:
            for w in room.get("windows", []):
                ai = w.get("aiAnalysis")
                if ai:
                    recs = ai.get("recommendations") or []
                    wtype = ai.get("windowType", "")
                    conf = ai.get("confidence", 0)
                    label = f"<strong>{room['name']} → {w.get('name', 'Window')}</strong>"
                    detail = f"{wtype}" if wtype else ""
                    if conf:
                        detail += f" (AI confidence: {conf}%)"
                    max_notes.append({"label": label, "detail": detail, "recs": recs})
            for u in room.get("upholstery", []):
                ai = u.get("aiAnalysis")
                if ai:
                    style = ai.get("style", "")
                    ftype = ai.get("furnitureType", "")
                    questions = ai.get("questions") or []
                    label = f"<strong>{room['name']} → {u.get('name', 'Piece')}</strong>"
                    detail = f"{ftype}" + (f" · {style}" if style else "")
                    max_notes.append({"label": label, "detail": detail, "recs": questions})

    max_section_html = ""
    if max_notes:
        max_section_html = """<div style="margin:24px 0;page-break-inside:avoid;padding:16px;background:linear-gradient(135deg,#f8f5ff,#fffcf0);border:2px solid #D4AF37;border-radius:12px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
          <div style="width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#D4AF37,#8B5CF6);display:flex;align-items:center;justify-content:center;color:white;font-weight:900;font-size:12px">M</div>
          <div><strong style="color:#1a1a2e;font-size:1.05em">MAX's Analysis</strong><br><span style="font-size:0.75em;color:#888">AI-powered insights from photo analysis</span></div>
        </div>"""
        for note in max_notes:
            max_section_html += f"""<div style="margin-bottom:10px;padding:10px;background:white;border-radius:8px;border:1px solid #eee">
            <p style="margin:0 0 4px;font-size:0.9em">{note['label']}</p>
            <p style="margin:0 0 4px;font-size:0.8em;color:#666">{note['detail']}</p>"""
            for rec in note.get("recs", [])[:4]:
                if rec:
                    max_section_html += f'<p style="margin:1px 0;font-size:0.78em;color:#555;padding-left:10px">→ {rec}</p>'
            max_section_html += "</div>"
        max_section_html += "</div>"

    # MAX's initial analysis text from chat
    max_analysis = quote.get("max_analysis") or ""
    max_analysis_html = ""
    if max_analysis:
        # Convert line breaks to <br> for HTML
        analysis_formatted = max_analysis.replace("\n", "<br>")
        max_analysis_html = f"""<div style="margin:0 0 24px;padding:16px 20px;background:linear-gradient(135deg,#fafbfd,#f8f5ff);border-left:4px solid #D4AF37;border-radius:0 8px 8px 0;page-break-inside:avoid">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
          <div style="width:24px;height:24px;border-radius:6px;background:linear-gradient(135deg,#D4AF37,#8B5CF6);display:flex;align-items:center;justify-content:center;color:white;font-weight:900;font-size:11px">M</div>
          <span style="font-weight:700;color:#1a1a2e;font-size:0.95em">Professional Assessment</span>
        </div>
        <div style="font-size:0.85em;color:#444;line-height:1.6">{analysis_formatted}</div>
        </div>"""

    # Deposit
    deposit = quote.get("deposit") or {}
    deposit_html = ""
    if deposit.get("deposit_amount"):
        deposit_html = f"""<tr><td colspan="3" style="padding:8px;text-align:right"><strong>Deposit ({deposit.get('deposit_percent', 50)}%)</strong></td>
        <td style="padding:8px;text-align:right"><strong>${deposit['deposit_amount']:.2f}</strong></td></tr>"""

    install_date = ""
    if quote.get("install_date"):
        install_date = f"<p><strong>Estimated Install Date:</strong> {quote['install_date']}</p>"

    logo_html = ""
    biz_name = quote.get("business_name") or "Empire"
    if quote.get("business_logo_url"):
        logo_html = f'<img src="{quote["business_logo_url"]}" style="max-height:60px;margin-bottom:8px" /><br>'

    created_date = quote['created_at'][:10]
    expires_date = quote.get('expires_at', '')[:10] if quote.get('expires_at') else ''
    quote_number = quote['quote_number']

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{quote_number}</title>
<style>
  @page {{ size: letter; margin: 0.6in 0.7in; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; max-width: 800px; margin: 0 auto; padding: 0; font-size: 12.5px; line-height: 1.5; }}
  h1 {{ color: #1a1a2e; margin: 0; font-size: 28px; letter-spacing: -0.5px; }}
  h3 {{ page-break-after: avoid; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  th {{ background: #1a1a2e; color: #D4AF37; padding: 8px 6px; text-align: left; font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ font-size: 0.85em; }}
</style></head><body>

<!-- ═══ HEADER / LETTERHEAD ═══ -->
<div style="border-bottom:3px solid #D4AF37;padding-bottom:20px;margin-bottom:24px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      {logo_html}
      <h1>{biz_name}</h1>
      <p style="margin:4px 0 0;color:#888;font-size:0.85em">Custom Window Treatments &amp; Upholstery</p>
    </div>
    <div style="text-align:right;padding-top:4px">
      <div style="background:#1a1a2e;color:#D4AF37;padding:8px 16px;border-radius:6px;font-weight:700;font-size:1.1em;letter-spacing:1px;display:inline-block;margin-bottom:8px">ESTIMATE</div>
      <p style="margin:3px 0;color:#333;font-size:0.9em;font-weight:600">{quote_number}</p>
      <p style="margin:3px 0;color:#666;font-size:0.82em">Date: {created_date}</p>
      <p style="margin:3px 0;color:#666;font-size:0.82em">Valid until: {expires_date}</p>
    </div>
  </div>
</div>

<!-- ═══ CLIENT INFO ═══ -->
<div style="display:flex;gap:24px;margin-bottom:24px">
  <div style="flex:1;padding:14px 18px;background:#f8f8f8;border-radius:8px;border:1px solid #eee">
    <p style="margin:0 0 6px;font-size:0.75em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Prepared For</p>
    <p style="margin:0;font-weight:700;font-size:1.05em;color:#1a1a2e">{quote['customer_name']}</p>
    {f'<p style="margin:3px 0 0;color:#555;font-size:0.88em">{quote["customer_email"]}</p>' if quote.get('customer_email') else ''}
    {f'<p style="margin:2px 0 0;color:#555;font-size:0.88em">{quote["customer_phone"]}</p>' if quote.get('customer_phone') else ''}
    {f'<p style="margin:2px 0 0;color:#555;font-size:0.88em">{quote["customer_address"]}</p>' if quote.get('customer_address') else ''}
  </div>
  {f'<div style="flex:1;padding:14px 18px;background:#fffcf0;border-radius:8px;border:1px solid #f0e6c0"><p style="margin:0 0 6px;font-size:0.75em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Project</p><p style="margin:0;font-weight:600;color:#1a1a2e">{quote["project_name"]}</p></div>' if quote.get('project_name') else ''}
</div>

{f"<p style='color:#555;margin-bottom:20px'>{quote['project_description']}</p>" if quote.get('project_description') else ""}

<!-- ═══ MAX ANALYSIS ═══ -->
{max_analysis_html}

<!-- ═══ QUOTE DETAILS ═══ -->
{body_html}

<!-- ═══ TOTALS ═══ -->
<table style="margin-top:16px"><tbody>
  <tr><td colspan="8" style="padding:8px;text-align:right;color:#666">Subtotal</td>
  <td style="padding:8px;text-align:right;color:#666">${quote['subtotal']:.2f}</td></tr>
  {"<tr><td colspan='8' style='padding:8px;text-align:right;color:#c00'>Discount</td><td style='padding:8px;text-align:right;color:#c00'>-$" + f"{quote['discount_amount']:.2f}</td></tr>" if quote.get('discount_amount') else ""}
  <tr><td colspan="8" style="padding:8px;text-align:right;color:#666">Tax ({quote.get('tax_rate', 0) * 100:.1f}%)</td>
  <td style="padding:8px;text-align:right;color:#666">${quote.get('tax_amount', 0):.2f}</td></tr>
  <tr><td colspan="8" style="padding:14px 8px;text-align:right;border-top:3px solid #D4AF37"><strong style="font-size:1.15em;color:#1a1a2e">Total</strong></td>
  <td style="padding:14px 8px;text-align:right;border-top:3px solid #D4AF37"><strong style="font-size:1.2em;color:#D4AF37">${quote['total']:.2f}</strong></td></tr>
  {deposit_html}
</tbody></table>

{install_date}

<!-- ═══ DRAWINGS & PROPOSALS ═══ -->
{outlines_html}
{mockups_html}
{max_section_html}

<!-- ═══ TERMS & CONDITIONS ═══ -->
{f'''<div style="margin-top:24px;padding:16px 20px;border:1px solid #ddd;border-radius:8px;background:#fafafa">
  <p style="margin:0 0 8px;font-size:0.78em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Terms &amp; Conditions</p>
  <p style="margin:0;font-size:0.88em;color:#555;line-height:1.6">{quote["terms"]}</p>
</div>''' if quote.get('terms') else ""}
{f"<div style='margin-top:10px;padding:12px 16px;background:#f8f8f8;border-radius:8px;font-size:0.88em;color:#666'><strong>Notes:</strong> {quote['notes']}</div>" if quote.get('notes') else ""}

<!-- ═══ ACCEPTANCE / SIGNATURE ═══ -->
<div style="margin-top:36px;padding:24px 20px;border:2px solid #D4AF37;border-radius:10px;page-break-inside:avoid">
  <p style="margin:0 0 12px;font-size:0.78em;text-transform:uppercase;letter-spacing:0.5px;color:#D4AF37;font-weight:700">Acceptance</p>
  <p style="margin:0 0 20px;font-size:0.85em;color:#555">By signing below, I accept this estimate and authorize {biz_name} to proceed with the work described above.</p>
  <div style="display:flex;gap:40px;margin-top:16px">
    <div style="flex:1">
      <div style="border-bottom:1px solid #333;height:40px"></div>
      <p style="margin:6px 0 0;font-size:0.78em;color:#888">Client Signature</p>
    </div>
    <div style="width:160px">
      <div style="border-bottom:1px solid #333;height:40px"></div>
      <p style="margin:6px 0 0;font-size:0.78em;color:#888">Date</p>
    </div>
  </div>
</div>

<!-- ═══ FOOTER ═══ -->
<div style="margin-top:28px;padding-top:12px;border-top:1px solid #eee;text-align:center">
  <p style="margin:0;color:#aaa;font-size:0.72em">{biz_name} &middot; Custom Window Treatments &amp; Upholstery</p>
  <p style="margin:2px 0 0;color:#ccc;font-size:0.65em">Estimate {quote_number} &middot; Generated {created_date}</p>
</div>
</body></html>"""

    # Convert HTML to PDF using weasyprint
    from weasyprint import HTML as WeasyHTML
    pdf_bytes = WeasyHTML(string=html).write_pdf()

    # Save PDF file
    pdf_dir = os.path.expanduser("~/Empire/data/quotes/pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{quote['quote_number']}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{quote["quote_number"]}.pdf"'
        },
    )


@router.get("/{quote_id}/pdf")
async def download_pdf(quote_id: str):
    """Download a previously generated PDF."""
    quote = _load_quote(quote_id)
    pdf_path = os.path.join(
        os.path.expanduser("~/Empire/data/quotes/pdf"),
        f"{quote['quote_number']}.pdf",
    )
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF not yet generated. POST to generate first.")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{quote["quote_number"]}.pdf"'
        },
    )
