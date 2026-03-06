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
import base64
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes", tags=["quotes"])

QUOTES_DIR = os.path.expanduser("~/empire-repo/backend/data/quotes")
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

    # Check if all windows are proposals (options — not cumulative)
    all_proposals = False
    rooms = data.get("rooms") or []
    if rooms:
        all_windows = [w for r in rooms for w in r.get("windows", [])]
        all_proposals = len(all_windows) > 0 and all(w.get("is_proposal") for w in all_windows)

    if all_proposals and rooms:
        # Proposals are OPTIONS — use price range of middle tier for financial summary
        proposals = [w for r in rooms for w in r.get("windows", [])]
        # Store range for PDF display
        data["price_range_low"] = sum(min(w.get("price_range_low", 0) for w in proposals) for _ in [1])
        data["price_range_high"] = sum(max(w.get("price_range_high", 0) for w in proposals) for _ in [1])
        # For the dollar total, use midpoint of middle tier
        mid_idx = min(1, len(proposals) - 1)
        mid_price = proposals[mid_idx].get("price", 0)
        subtotal = round(mid_price, 2)
        # Also include upholstery
        for room in rooms:
            for u in room.get("upholstery", []):
                subtotal += u.get("price", 0)
    else:
        subtotal = round(sum(i["amount"] for i in items), 2)
        # If no line_items but rooms exist, compute subtotal from room prices
        if subtotal == 0 and rooms:
            for room in rooms:
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


def _detect_hardware_color(hardware_name: str, explicit_color: str = "") -> tuple:
    """Detect hardware color from name or explicit selection. Returns (color_hex, color_name)."""
    if explicit_color:
        color_map = {
            "black": ("#1a1a1a", "Black"), "matte-black": ("#1a1a1a", "Matte Black"),
            "bronze": ("#6B4226", "Bronze"), "oil-rubbed-bronze": ("#3E2723", "Oil-Rubbed Bronze"),
            "brushed-nickel": ("#9E9E9E", "Brushed Nickel"), "nickel": ("#9E9E9E", "Nickel"),
            "polished-chrome": ("#C0C0C0", "Polished Chrome"), "chrome": ("#C0C0C0", "Chrome"),
            "brass": ("#D4AF37", "Brass"), "gold": ("#D4AF37", "Gold"), "antique-brass": ("#B5893A", "Antique Brass"),
            "satin-silver": ("#A8A8A8", "Satin Silver"), "silver": ("#A8A8A8", "Silver"),
            "white": ("#E8E8E8", "White"), "pewter": ("#8A8A8A", "Pewter"),
        }
        key = explicit_color.lower().strip().replace(" ", "-")
        if key in color_map:
            return color_map[key]
    # Auto-detect from hardware name
    hw = hardware_name.lower()
    if "black" in hw or "matte" in hw or "iron" in hw:
        return ("#1a1a1a", "Black")
    if "bronze" in hw or "oil" in hw:
        return ("#6B4226", "Bronze")
    if "nickel" in hw or "brushed" in hw:
        return ("#9E9E9E", "Brushed Nickel")
    if "chrome" in hw or "polish" in hw:
        return ("#C0C0C0", "Chrome")
    if "brass" in hw or "gold" in hw:
        return ("#D4AF37", "Brass")
    if "silver" in hw or "satin" in hw:
        return ("#A8A8A8", "Silver")
    if "white" in hw:
        return ("#E8E8E8", "White")
    if "pewter" in hw:
        return ("#8A8A8A", "Pewter")
    # Default: brushed nickel (industry standard)
    return ("#9E9E9E", "Brushed Nickel")


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
    hw_color_hex, hw_color_name = _detect_hardware_color(hardware, w.get("hardwareColor", ""))

    treatment_labels = {
        'ripplefold': 'Ripplefold', 'pinch-pleat': 'Pinch Pleat', 'rod-pocket': 'Rod Pocket',
        'grommet': 'Grommet', 'roman-shade': 'Roman Shade', 'roller-shade': 'Roller Shade',
        'Drapery': 'Drapery', 'drapery': 'Drapery',
    }
    ttype = treatment_labels.get(treatment, treatment.replace("-", " ").title())

    # Treatment-specific drape pattern
    is_shade = treatment.lower() in ('roman-shade', 'roller-shade', 'roman shade', 'roller shade')

    # Scale: 1.6px per inch for compact drawings
    scale = 1.6
    win_w = max(w_in * scale, 80)
    win_h = max(h_in * scale, 96)
    pad = 40
    svg_w = win_w + pad * 2
    info_h = 24
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
        # Roman/roller shade — headrail/cassette at top, horizontal fold lines, gathered bottom
        # Headrail cassette at top of window
        rail_h = 10
        svg += f'<rect x="{wx-2}" y="{wy-rail_h-2}" width="{win_w+4}" height="{rail_h}" fill="#888" stroke="#666" stroke-width="1" rx="2"/>'
        svg += f'<rect x="{wx}" y="{wy-rail_h}" width="{win_w}" height="{rail_h-2}" fill="#aaa" stroke="none" rx="1"/>'
        # End caps on headrail
        svg += f'<rect x="{wx-4}" y="{wy-rail_h-3}" width="6" height="{rail_h+4}" fill="#777" stroke="#555" stroke-width="0.5" rx="1"/>'
        svg += f'<rect x="{wx+win_w-2}" y="{wy-rail_h-3}" width="6" height="{rail_h+4}" fill="#777" stroke="#555" stroke-width="0.5" rx="1"/>'
        svg += f'<text x="{cx}" y="{wy-rail_h+7}" text-anchor="middle" font-size="6" fill="#fff" font-weight="600">HEADRAIL</text>'

        is_roman = 'roman' in treatment.lower()
        if is_roman:
            # Roman shade — horizontal fold lines with soft scalloped bottom
            folds = int(win_h / 25)
            for i in range(1, max(folds, 3)):
                fy = wy + (win_h * i / max(folds, 3))
                svg += f'<line x1="{wx+6}" y1="{fy}" x2="{wx+win_w-6}" y2="{fy}" stroke="#b0c4d8" stroke-width="0.8" stroke-dasharray="4 3"/>'
            # Gathered bottom folds (scalloped)
            bottom_y = wy + win_h - 20
            segments = 5
            path = f'M{wx+8},{bottom_y}'
            for s in range(segments):
                sx1 = wx + 8 + (win_w - 16) * s / segments
                sx2 = wx + 8 + (win_w - 16) * (s + 1) / segments
                smid = (sx1 + sx2) / 2
                path += f' Q{smid},{bottom_y + 14} {sx2},{bottom_y}'
            svg += f'<path d="{path}" fill="none" stroke="#8aa8c8" stroke-width="1.2"/>'
        else:
            # Roller shade — smooth fabric with pull cord/chain
            svg += f'<rect x="{wx+4}" y="{wy+2}" width="{win_w-8}" height="{win_h-6}" fill="#d8e4f0" opacity="0.4" rx="1"/>'
            # Bottom bar
            svg += f'<rect x="{wx+2}" y="{wy+win_h-6}" width="{win_w-4}" height="4" fill="#888" stroke="#666" stroke-width="0.5" rx="1"/>'
            # Pull cord on right side
            cord_x = wx + win_w + 4
            svg += f'<line x1="{cord_x}" y1="{wy-rail_h}" x2="{cord_x}" y2="{wy+win_h*0.6}" stroke="#888" stroke-width="1"/>'
            svg += f'<circle cx="{cord_x}" cy="{wy+win_h*0.6+4}" r="3" fill="#777" stroke="#555" stroke-width="0.5"/>'

        svg += f'<text x="{cx}" y="{cy-8}" text-anchor="middle" font-size="9" fill="#6a8caf" font-style="italic">{ttype}</text>'
    else:
        # Drapery / curtain panels — realistic gathered fabric with shading
        # Rod at top
        rod_y = wy + 4
        rod_extend = 12
        svg += f'<line x1="{wx - rod_extend}" y1="{rod_y}" x2="{wx + win_w + rod_extend}" y2="{rod_y}" stroke="{hw_color_hex}" stroke-width="3" stroke-linecap="round"/>'
        # Finials (end caps)
        svg += f'<circle cx="{wx - rod_extend}" cy="{rod_y}" r="4" fill="{hw_color_hex}"/>'
        svg += f'<circle cx="{wx + win_w + rod_extend}" cy="{rod_y}" r="4" fill="{hw_color_hex}"/>'
        # Rings/carriers on rod
        ring_count = max(int(win_w / 22), 5)
        for i in range(ring_count):
            rx = wx + 6 + (win_w - 12) * i / (ring_count - 1)
            svg += f'<circle cx="{rx}" cy="{rod_y}" r="2.5" fill="none" stroke="{hw_color_hex}" stroke-width="1"/>'

        # Fabric panels — left panel gathered to left, right panel gathered to right
        panel_gather = win_w * 0.15  # how much fabric gathers at sides
        left_edge = wx + 3
        right_edge = wx + win_w - 3
        mid = cx
        top = rod_y + 5
        bottom = wy + win_h - 4

        # Left panel: gathered at left, draping toward center
        for j in range(6):
            t = j / 5  # 0 to 1
            x_top = left_edge + panel_gather * (1 - t * 0.8)
            x_bottom = left_edge + (mid - left_edge - 8) * t
            offset = 3 * (1 if j % 2 == 0 else -1) * (1 - t * 0.3)
            svg += f'<path d="M{x_top},{top} C{x_top + offset},{top + win_h * 0.3} {x_bottom - offset},{top + win_h * 0.65} {x_bottom},{bottom}" fill="none" stroke="{"#8aa8c8" if j % 2 == 0 else "#a0bcd8"}" stroke-width="{"1.2" if j % 2 == 0 else "0.7"}"/>'

        # Right panel: gathered at right, draping toward center
        for j in range(6):
            t = j / 5
            x_top = right_edge - panel_gather * (1 - t * 0.8)
            x_bottom = right_edge - (right_edge - mid - 8) * t
            offset = 3 * (1 if j % 2 == 0 else -1) * (1 - t * 0.3)
            svg += f'<path d="M{x_top},{top} C{x_top - offset},{top + win_h * 0.3} {x_bottom + offset},{top + win_h * 0.65} {x_bottom},{bottom}" fill="none" stroke="{"#8aa8c8" if j % 2 == 0 else "#a0bcd8"}" stroke-width="{"1.2" if j % 2 == 0 else "0.7"}"/>'

        # Fabric body shading (subtle filled shapes for the gathered panels)
        svg += f'<path d="M{left_edge},{top} L{left_edge},{bottom} L{mid - 8},{bottom} L{left_edge + panel_gather},{top} Z" fill="#c8daea" opacity="0.25"/>'
        svg += f'<path d="M{right_edge},{top} L{right_edge},{bottom} L{mid + 8},{bottom} L{right_edge - panel_gather},{top} Z" fill="#c8daea" opacity="0.25"/>'

        # Treatment label in the window view area
        svg += f'<text x="{cx}" y="{cy+3}" text-anchor="middle" font-size="8" fill="#6a8caf" font-style="italic">window view</text>'
        # Hardware color label below rod
        svg += f'<text x="{cx}" y="{rod_y + 14}" text-anchor="middle" font-size="7" fill="{hw_color_hex}">{hw_color_name}</text>'

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

    # Mount indicator
    if mount.lower() == 'ceiling':
        svg += f'<line x1="{wx}" y1="{wy-3}" x2="{wx+win_w}" y2="{wy-3}" stroke="#666" stroke-width="3"/>'
        svg += f'<text x="{wx-2}" y="{wy-5}" font-size="7" fill="#888">CEIL</text>'
    elif mount.lower() == 'inside':
        svg += f'<rect x="{wx-3}" y="{wy-3}" width="{win_w+6}" height="{win_h+6}" fill="none" stroke="#999" stroke-width="1" stroke-dasharray="3 2" rx="1"/>'

    # Price below drawing
    spec_y = wy + win_h + 20
    svg += f'<text x="{svg_w/2}" y="{spec_y}" text-anchor="middle" font-size="10" fill="#D4AF37" font-weight="bold">${w.get("price", 0):,.2f}</text>'

    svg += "</svg>"

    # Full spec notes below the SVG
    fabric_grade = w.get("fabricGrade", "")
    fabric_color = w.get("fabricColor", "")
    draw_dir = w.get("drawDirection", "center")
    draw_labels = {"center": "Center (split)", "left": "Left Draw", "right": "Right Draw", "one-way-l": "One-Way Left", "one-way-r": "One-Way Right", "stationary": "Stationary"}
    draw_label = draw_labels.get(draw_dir, draw_dir.replace("-", " ").title())
    fullness = w.get("fullness", 2.5)
    notes_text = w.get("notes", "")
    yardage = w.get("yardage", {})
    total_yardage = yardage.get("total", 0)

    svg += f'<div style="margin-top:4px;padding:8px 10px;background:#f8f9fb;border:1px solid #e0e0e0;border-radius:5px;font-size:0.72em;max-width:{int(svg_w)}px;line-height:1.6">'
    svg += f'<div style="display:flex;justify-content:space-between;margin-bottom:3px"><strong style="color:#1a1a2e">{ttype}</strong><span style="color:#D4AF37;font-weight:700">{mount} Mount</span></div>'
    svg += f'<div style="color:#555">'
    svg += f'<strong>Lining:</strong> {lining}'
    if is_shade:
        # Shades use headrail/cassette, not rod hardware
        svg += f' · <strong>Control:</strong> {"Motorized" if motor.lower() != "none" else "Cordless"}'
    else:
        svg += f' · <strong>Hardware:</strong> {hardware} ({hw_color_name})'
        if motor.lower() != "none":
            svg += f' · <strong>Motor:</strong> {motor}'
    svg += '<br>'
    if fabric_color:
        svg += f'<strong>Fabric:</strong> {fabric_color} '
    if fabric_grade:
        svg += f'<strong>Grade:</strong> {fabric_grade} '
    if not is_shade:
        svg += f'<strong>Draw:</strong> {draw_label} · <strong>Fullness:</strong> {fullness}×'
    if total_yardage:
        svg += f' · <strong>Yardage:</strong> {total_yardage:.1f} yd'
    svg += '</div>'
    if notes_text:
        svg += f'<div style="margin-top:4px;padding-top:4px;border-top:1px solid #e0e0e0;color:#888;font-style:italic">{notes_text}</div>'
    svg += '</div>'

    # AI analysis notes below specs (if available)
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


def _fabric_color_hex(name: str) -> tuple[str, str]:
    """Map fabric color name to fill and stroke hex."""
    name_l = (name or "").lower()
    COLOR_MAP = {
        "blue":("#4a6fa5","#345080"), "denim":("#4a6fa5","#345080"), "navy":("#1e3a5f","#0f2740"),
        "red":("#b03030","#8a2020"), "burgundy":("#6b2030","#501020"), "wine":("#6b2030","#501020"),
        "green":("#4a7a5a","#356045"), "olive":("#6b6b3a","#505020"), "sage":("#8a9a7a","#6a7a5a"),
        "gold":("#c9a84c","#a08030"), "yellow":("#d4c060","#b0a040"), "cream":("#f0e8d0","#c8b890"),
        "beige":("#ddd0b8","#b8a888"), "tan":("#c8b090","#a89070"), "khaki":("#c8b878","#a89860"),
        "gray":("#8a8a8a","#666"), "grey":("#8a8a8a","#666"), "charcoal":("#4a4a4a","#333"),
        "black":("#2a2a2a","#111"), "white":("#f5f5f5","#ccc"), "ivory":("#f0ead8","#c8c0a8"),
        "brown":("#6b4c30","#503820"), "chocolate":("#4a3020","#301810"), "espresso":("#3a2010","#201005"),
        "orange":("#cc7030","#a05520"), "rust":("#8a4020","#603010"), "terracotta":("#b06040","#804030"),
        "purple":("#6a4c8a","#503870"), "plum":("#5a2858","#401840"), "lavender":("#8a7aaa","#6a5a8a"),
        "pink":("#cc7088","#a05068"), "blush":("#d8a8b0","#b88898"), "coral":("#d07060","#b05040"),
        "teal":("#3a7a7a","#205858"), "turquoise":("#4a9090","#307070"), "aqua":("#5aaa9a","#408878"),
        "linen":("#e8dcc8","#c0b498"), "natural":("#d8c8a8","#b0a080"),
    }
    for k, v in COLOR_MAP.items():
        if k in name_l:
            return v
    return ("#f0ebe0", "#8B7355")  # default warm beige


def _build_upholstery_drawing(u: dict) -> str:
    """Generate type-specific SVG diagrams for upholstery pieces with fabric color and construction options."""
    name = u.get("name", "Piece")
    ftype_raw = u.get("furnitureType", "sofa").lower()
    ftype = ftype_raw.title()
    w_in = u.get("width", 72)
    d_in = u.get("depth", 36)
    h_in = u.get("height", 34)
    fabric_yards = u.get("fabricYards", 0)
    fabric_type = u.get("fabricType", "").title()
    fabric = f"{fabric_yards} yd {fabric_type}"
    labor = u.get("laborType", "standard").title()
    cushions = u.get("cushionCount", 0)
    source_photo = u.get("sourcePhoto")
    notes = u.get("notes", "")
    price = u.get("price", 0)

    # Detect fabric color from name, notes, or project context
    color_hint = ""
    for src in [name, notes, fabric_type]:
        if src:
            color_hint = src
            break
    fill, stroke = _fabric_color_hex(color_hint)
    fill_light = fill.replace("#", "")  # lighter variant for accents
    # Create a lighter shade for secondary elements
    fill_accent = stroke

    # Source photo
    photo_html = ""
    if source_photo:
        photo_html = f"""<div style="margin-bottom:8px;text-align:center;page-break-inside:avoid">
        <p style="font-size:0.75em;color:#666;margin-bottom:4px;font-weight:600">Reference Photo — {name}</p>
        <img src="{source_photo}" style="max-width:100%;max-height:250px;border-radius:8px;border:1px solid #ddd;object-fit:contain" />
        </div>"""

    svg_w = 240
    svg_h = 160

    # ── Detect furniture category ──
    is_pillow = any(k in ftype_raw for k in ("pillow", "cushion", "throw"))
    is_bolster = "bolster" in ftype_raw
    is_ottoman = any(k in ftype_raw for k in ("ottoman", "pouf", "footstool"))
    is_bench = "bench" in ftype_raw
    is_chair = any(k in ftype_raw for k in ("chair", "recliner"))
    is_headboard = "headboard" in ftype_raw

    # ── Detect construction details from AI analysis or notes ──
    ai = u.get("aiAnalysis") or {}
    has_welting = ai.get("hasWelting", False) or "welting" in notes.lower() or "piping" in notes.lower()
    has_tufting = ai.get("hasTufting", False) or "tuft" in notes.lower()
    has_flange = "flange" in notes.lower() or "flange" in name.lower()
    has_skirt = ai.get("has_skirt", False) or "skirt" in notes.lower()

    # ── Build SVG based on furniture type ──

    if is_bolster:
        svg_w, svg_h = 220, 130
        # Bolster pillow — cylindrical shape
        svg_body = f"""
          <ellipse cx="60" cy="65" rx="25" ry="30" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
          <rect x="60" y="35" width="100" height="60" fill="{fill}" stroke="none"/>
          <ellipse cx="160" cy="65" rx="25" ry="30" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
          <line x1="60" y1="35" x2="160" y2="35" stroke="{stroke}" stroke-width="1.5"/>
          <line x1="60" y1="95" x2="160" y2="95" stroke="{stroke}" stroke-width="1.5"/>
          <!-- Center seam -->
          <line x1="110" y1="36" x2="110" y2="94" stroke="{fill_accent}" stroke-width="0.5" stroke-dasharray="3,3"/>"""
        if has_welting:
            svg_body += f"""<line x1="60" y1="35" x2="160" y2="35" stroke="#D4AF37" stroke-width="2"/>
            <line x1="60" y1="95" x2="160" y2="95" stroke="#D4AF37" stroke-width="2"/>"""
        dims = f'{w_in}"L'

    elif is_pillow:
        svg_w, svg_h = 220, 150
        # Throw pillow — square/rectangle with rounded corners
        px, py, pw, ph = 55, 20, 110, 100
        svg_body = f"""
          <rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="8"/>"""
        # Diagonal crease lines for dimension
        svg_body += f"""<line x1="{px+15}" y1="{py+ph-5}" x2="{px+5}" y2="{py+ph-15}" stroke="{fill_accent}" stroke-width="0.5" opacity="0.6"/>
          <line x1="{px+pw-15}" y1="{py+ph-5}" x2="{px+pw-5}" y2="{py+ph-15}" stroke="{fill_accent}" stroke-width="0.5" opacity="0.6"/>"""
        if has_flange:
            # Flange border — outer rectangle
            svg_body += f"""<rect x="{px-6}" y="{py-6}" width="{pw+12}" height="{ph+12}" fill="none" stroke="{stroke}" stroke-width="1" rx="10" stroke-dasharray="none"/>
            <text x="{svg_w/2}" y="{py+ph+20}" text-anchor="middle" font-size="7" fill="#D4AF37" font-weight="600">WITH FLANGE (+$15)</text>"""
        if has_welting:
            svg_body += f"""<rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="none" stroke="#D4AF37" stroke-width="2.5" rx="8"/>"""
        dims = f'{w_in}"×{d_in}"'

    elif is_ottoman:
        svg_w, svg_h = 220, 140
        # Ottoman — cube-like with cushion top
        ox, oy, ow, oh = 50, 30, 120, 60
        svg_body = f"""
          <rect x="{ox}" y="{oy+10}" width="{ow}" height="{oh}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="4"/>
          <!-- Cushion top -->
          <rect x="{ox+3}" y="{oy}" width="{ow-6}" height="14" fill="{fill}" stroke="{stroke}" stroke-width="1" rx="5"/>"""
        if has_tufting:
            # Tufting buttons
            for r in range(2):
                for c in range(3):
                    tx = ox + 25 + c * 35
                    ty = oy + 25 + r * 25
                    svg_body += f'<circle cx="{tx}" cy="{ty}" r="3" fill="{fill_accent}" stroke="{stroke}" stroke-width="0.8"/>'
        if has_skirt:
            svg_body += f'<rect x="{ox-2}" y="{oy+oh+8}" width="{ow+4}" height="8" fill="{fill}" stroke="{stroke}" stroke-width="0.8" rx="1"/>'
        dims = f'{w_in}"W×{d_in}"D×{h_in}"H'

    elif is_bench:
        svg_w, svg_h = 240, 130
        bx, by, bw, bh = 30, 30, 180, 40
        svg_body = f"""
          <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="4"/>
          <!-- Legs -->
          <rect x="{bx+8}" y="{by+bh}" width="6" height="25" fill="{stroke}" stroke="none" rx="1"/>
          <rect x="{bx+bw-14}" y="{by+bh}" width="6" height="25" fill="{stroke}" stroke="none" rx="1"/>"""
        if has_tufting:
            for c in range(5):
                tx = bx + 20 + c * 35
                svg_body += f'<circle cx="{tx}" cy="{by+bh/2}" r="3" fill="{fill_accent}" stroke="{stroke}" stroke-width="0.8"/>'
        dims = f'{w_in}"W×{d_in}"D×{h_in}"H'

    elif is_headboard:
        svg_w, svg_h = 240, 150
        hx, hy, hw, hh = 30, 15, 180, 100
        svg_body = f"""
          <rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="6"/>
          <!-- Bed line -->
          <rect x="{hx-5}" y="{hy+hh}" width="{hw+10}" height="12" fill="#e8e0d0" stroke="#b8a888" stroke-width="1" rx="2"/>"""
        if has_tufting:
            for r in range(3):
                for c in range(4):
                    tx = hx + 25 + c * 42
                    ty = hy + 18 + r * 28
                    svg_body += f'<circle cx="{tx}" cy="{ty}" r="3" fill="{fill_accent}" stroke="{stroke}" stroke-width="0.8"/>'
        dims = f'{w_in}"W×{h_in}"H'

    elif is_chair:
        svg_w, svg_h = 220, 150
        bx, by, bw, bh = 50, 45, 120, 55
        svg_body = f"""
          <!-- Seat -->
          <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="4"/>
          <!-- Back -->
          <rect x="{bx+8}" y="{by-28}" width="{bw-16}" height="30" fill="{fill}" stroke="{stroke}" stroke-width="1" rx="5"/>
          <!-- Arms -->
          <rect x="{bx-10}" y="{by+5}" width="12" height="{bh-10}" fill="{fill}" stroke="{stroke}" stroke-width="1" rx="3"/>
          <rect x="{bx+bw-2}" y="{by+5}" width="12" height="{bh-10}" fill="{fill}" stroke="{stroke}" stroke-width="1" rx="3"/>
          <!-- Legs -->
          <rect x="{bx+5}" y="{by+bh}" width="5" height="12" fill="{stroke}" rx="1"/>
          <rect x="{bx+bw-10}" y="{by+bh}" width="5" height="12" fill="{stroke}" rx="1"/>"""
        # Cushion detail
        if cushions >= 1:
            svg_body += f'<rect x="{bx+6}" y="{by+4}" width="{bw-12}" height="{bh-8}" fill="none" stroke="{fill_accent}" stroke-width="0.7" rx="3"/>'
        if has_tufting:
            for r in range(2):
                for c in range(2):
                    tx = bx + 35 + c * 50
                    ty = by - 18 + r * 14
                    svg_body += f'<circle cx="{tx}" cy="{ty}" r="2.5" fill="{fill_accent}" stroke="{stroke}" stroke-width="0.6"/>'
        dims = f'{w_in}"W×{d_in}"D×{h_in}"H'

    else:
        # Default sofa
        svg_w, svg_h = 260, 150
        bx, by, bw, bh = 30, 45, 200, 55
        svg_body = f"""
          <!-- Seat -->
          <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="4"/>
          <!-- Back -->
          <rect x="{bx+6}" y="{by-16}" width="{bw-12}" height="18" fill="{fill}" stroke="{stroke}" stroke-width="1" rx="4"/>
          <!-- Arms -->
          <rect x="{bx-10}" y="{by+5}" width="12" height="{bh-10}" fill="{fill}" stroke="{stroke}" stroke-width="1" rx="3"/>
          <rect x="{bx+bw-2}" y="{by+5}" width="12" height="{bh-10}" fill="{fill}" stroke="{stroke}" stroke-width="1" rx="3"/>
          <!-- Legs -->
          <rect x="{bx+5}" y="{by+bh}" width="5" height="10" fill="{stroke}" rx="1"/>
          <rect x="{bx+bw-10}" y="{by+bh}" width="5" height="10" fill="{stroke}" rx="1"/>"""
        # Cushion dividers
        if cushions > 0:
            cw = (bw - 12) / min(cushions, 5)
            for i in range(min(cushions, 5)):
                cx = bx + 6 + i * cw
                svg_body += f'<rect x="{cx+1}" y="{by+4}" width="{cw-2}" height="{bh-8}" fill="none" stroke="{fill_accent}" stroke-width="0.7" rx="2"/>'
        if has_tufting:
            for r in range(2):
                for c in range(3):
                    tx = bx + 40 + c * 60
                    ty = by - 8 + r * 10
                    svg_body += f'<circle cx="{tx}" cy="{ty}" r="2.5" fill="{fill_accent}" stroke="{stroke}" stroke-width="0.6"/>'
        if has_skirt:
            svg_body += f'<rect x="{bx-12}" y="{by+bh+8}" width="{bw+24}" height="8" fill="{fill}" stroke="{stroke}" stroke-width="0.8" rx="1"/>'
        dims = f'{w_in}"W×{d_in}"D×{h_in}"H'

    # ── Welting indicator across all types (adds a bold seam line) ──
    welting_label = ""
    if has_welting and not is_pillow and not is_bolster:
        welting_label = '<tspan fill="#D4AF37" font-size="7"> + Welting</tspan>'

    # ── Assemble SVG ──
    svg = photo_html + f"""<div style="display:inline-block;vertical-align:top;margin:6px 8px 6px 0;page-break-inside:avoid">
    <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" style="max-width:100%;background:#fafbfd;border:1px solid #e0e0e0;border-radius:6px">
      <text x="{svg_w/2}" y="14" text-anchor="middle" font-size="9.5" fill="#1a1a2e" font-weight="700">{name}</text>
      <text x="{svg_w/2}" y="26" text-anchor="middle" font-size="7.5" fill="#888">{ftype} · {dims}{welting_label}</text>
      {svg_body}
      <text x="{svg_w/2}" y="{svg_h-20}" text-anchor="middle" font-size="7.5" fill="#555">{fabric} · {labor}{f" · {cushions} cushion" + ("s" if cushions != 1 else "") if cushions > 0 else ""}</text>
      <text x="{svg_w/2}" y="{svg_h-7}" text-anchor="middle" font-size="9" fill="#D4AF37" font-weight="bold">${price:,.2f}</text>
    </svg>"""

    # ── Construction options table (pricing variants) ──
    options = []
    base_price = price
    if is_pillow or is_bolster:
        flange_price = base_price + 15
        welting_price = base_price + 12
        both_price = base_price + 25
        options.append(("Standard (no trim)", f"${base_price:,.2f}"))
        if not has_welting:
            options.append(("+ Contrast Welting/Piping", f"${welting_price:,.2f}"))
        if not has_flange and is_pillow:
            options.append(("+ Decorative Flange", f"${flange_price:,.2f}"))
        if is_pillow:
            options.append(("+ Welting & Flange", f"${both_price:,.2f}"))
    elif not is_headboard:
        if not has_welting:
            options.append(("+ Contrast Welting", f"+$50–80"))
        if not has_tufting:
            options.append(("+ Diamond Tufting", f"+$100–150"))
        if not has_skirt:
            options.append(("+ Tailored Skirt", f"+$75–120"))

    if options:
        svg += f'<div style="margin-top:4px;font-size:0.7em;max-width:{svg_w}px">'
        svg += '<table style="width:100%;border-collapse:collapse">'
        svg += '<tr style="background:#f8f5ff"><td colspan="2" style="padding:3px 6px;font-weight:700;color:#8B5CF6;font-size:0.9em">Upgrade Options</td></tr>'
        for label, opt_price in options:
            svg += f'<tr><td style="padding:2px 6px;color:#555">{label}</td><td style="padding:2px 6px;text-align:right;color:#D4AF37;font-weight:600">{opt_price}</td></tr>'
        svg += '</table></div>'

    # AI analysis notes
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
            svg += f"""<div style="margin-top:12px;border:2px solid #D4AF37;border-radius:10px;overflow:hidden;background:white;page-break-inside:avoid">
            <div style="background:#D4AF37;color:white;padding:6px 16px;font-size:0.85em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">AI Upholstery Mockup — {name}</div>
            <img src="{gen_img}" style="width:100%;max-height:500px;object-fit:contain;display:block" />
            <div style="padding:10px 14px;border-top:1px solid #eee;font-size:0.82em;color:#555">
                <strong>{ftype}</strong> · {fabric} · {labor}{f" · {cushions} cushions" if cushions > 0 else ""}
                {f' · <em style="color:#888">{style}</em>' if style else ''}
            </div>
            </div>"""

    svg += "</div>"
    return svg


def _build_proposal_drawing(w: dict) -> str:
    """Generate SVG drawing for AI proposal window — treatment-aware (shades vs drapery)."""
    name = w.get("name", "Option")
    w_in = w.get("width", 48)
    h_in = w.get("height", 60)
    treatment = w.get("treatmentType", "Custom")
    hardware = w.get("hardwareType", "decorative")
    motor = w.get("motorization", "none")
    lining = w.get("liningType", "standard")
    price_low = w.get("price_range_low", 0)
    price_high = w.get("price_range_high", 0)
    has_motor = motor.lower() not in ("none", "")

    # Detect shade vs drapery from treatment type text
    treatment_lower = treatment.lower()
    is_shade = any(k in treatment_lower for k in ('roman', 'shade', 'roller', 'blind'))

    # Determine tier color
    name_lower = name.lower()
    if "essential" in name_lower or "budget" in name_lower:
        color = "#22c55e"
    elif "designer" in name_lower or "choice" in name_lower:
        color = "#D4AF37"
    elif "luxury" in name_lower or "premium" in name_lower or "ultimate" in name_lower:
        color = "#8B5CF6"
    else:
        color = "#333"

    # Scale: 2.5px per inch, min 100px
    scale = 2.5
    win_w = max(w_in * scale, 100)
    win_h = max(h_in * scale, 120)
    pad = 55
    svg_w = win_w + pad * 2
    info_h = 60
    svg_h = win_h + pad * 2 + info_h

    wx = pad
    wy = pad
    cx = wx + win_w / 2

    svg = f"""<div style="display:inline-block;vertical-align:top;margin:6px 8px 6px 0;page-break-inside:avoid">
    <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" style="max-width:100%;background:#fafbfd;border:2px solid {color};border-radius:8px">
      <!-- Title -->
      <text x="{svg_w/2}" y="16" text-anchor="middle" font-size="10" fill="{color}" font-weight="700">{name}</text>
      <!-- Window frame -->
      <rect x="{wx}" y="{wy}" width="{win_w}" height="{win_h}" fill="#f0f7ff" stroke="#1a1a2e" stroke-width="2" rx="2"/>"""

    if is_shade:
        # ── SHADE treatment: headrail + fabric + fold lines ──
        # Headrail cassette at top
        rail_h = 10
        svg += f'<rect x="{wx-2}" y="{wy-rail_h-2}" width="{win_w+4}" height="{rail_h}" fill="#888" stroke="#666" stroke-width="1" rx="2"/>'
        svg += f'<rect x="{wx}" y="{wy-rail_h}" width="{win_w}" height="{rail_h-2}" fill="#aaa" stroke="none" rx="1"/>'
        svg += f'<rect x="{wx-4}" y="{wy-rail_h-3}" width="6" height="{rail_h+4}" fill="#777" stroke="#555" stroke-width="0.5" rx="1"/>'
        svg += f'<rect x="{wx+win_w-2}" y="{wy-rail_h-3}" width="6" height="{rail_h+4}" fill="#777" stroke="#555" stroke-width="0.5" rx="1"/>'
        svg += f'<text x="{cx}" y="{wy-rail_h+7}" text-anchor="middle" font-size="6" fill="#fff" font-weight="600">HEADRAIL</text>'
        # Shade fabric body (partially raised — showing bottom third of window)
        shade_top = wy + 2
        shade_bottom = wy + win_h * 0.55
        svg += f'<rect x="{wx+3}" y="{shade_top}" width="{win_w-6}" height="{shade_bottom - shade_top}" fill="{color}" opacity="0.18" rx="1"/>'
        # Horizontal fold lines
        fold_count = max(int((shade_bottom - shade_top) / 22), 3)
        for i in range(1, fold_count):
            fy = shade_top + (shade_bottom - shade_top) * i / fold_count
            svg += f'<line x1="{wx+6}" y1="{fy}" x2="{wx+win_w-6}" y2="{fy}" stroke="{color}" stroke-width="0.7" opacity="0.35" stroke-dasharray="4 3"/>'
        # Scalloped gathered bottom
        segments = 5
        path = f'M{wx+6},{shade_bottom}'
        for s in range(segments):
            sx1 = wx + 6 + (win_w - 12) * s / segments
            sx2 = wx + 6 + (win_w - 12) * (s + 1) / segments
            smid = (sx1 + sx2) / 2
            path += f' Q{smid},{shade_bottom + 10} {sx2},{shade_bottom}'
        svg += f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1" opacity="0.5"/>'
        # Window view below shade
        svg += f'<rect x="{wx+4}" y="{shade_bottom+4}" width="{win_w-8}" height="{wy+win_h-shade_bottom-8}" fill="#e8f4fd" stroke="none" rx="1"/>'
        svg += f'<text x="{cx}" y="{shade_bottom + (wy+win_h-shade_bottom)/2 + 4}" text-anchor="middle" font-size="8" fill="#aac8e0" font-style="italic">window view</text>'
        # Motor icon if motorized
        if has_motor:
            svg += f'<rect x="{cx - 12}" y="{wy - rail_h - 12}" width="24" height="8" fill="#555" rx="2"/>'
            svg += f'<text x="{cx}" y="{wy - rail_h - 6}" text-anchor="middle" font-size="5" fill="white" font-weight="bold">MOTOR</text>'
    else:
        # ── DRAPERY treatment: rod + finials + retracted panels ──
        # Panel stack widths
        stack_w = max(win_w * 0.15, 18)
        # Glass/light area
        svg += f'<rect x="{wx + stack_w + 4}" y="{wy + 4}" width="{win_w - stack_w * 2 - 8}" height="{win_h - 8}" fill="#e8f4fd" stroke="none" rx="1"/>'
        svg += f'<text x="{cx}" y="{wy + win_h / 2}" text-anchor="middle" font-size="8" fill="#aac8e0" font-style="italic">window view</text>'
        # Hardware rod across top
        svg += f'<line x1="{wx - 8}" y1="{wy - 4}" x2="{wx + win_w + 8}" y2="{wy - 4}" stroke="#8B7355" stroke-width="3" stroke-linecap="round"/>'
        svg += f'<circle cx="{wx - 10}" cy="{wy - 4}" r="4" fill="#8B7355"/>'
        svg += f'<circle cx="{wx + win_w + 10}" cy="{wy - 4}" r="4" fill="#8B7355"/>'
        # LEFT retracted panel
        lx = wx
        for i in range(4):
            fold_x = lx + stack_w * i / 4
            opacity = 0.35 - i * 0.05
            svg += f'<rect x="{fold_x}" y="{wy}" width="{stack_w / 3 + 2}" height="{win_h}" fill="{color}" opacity="{opacity}" rx="1"/>'
        for i in range(1, 5):
            fx = lx + stack_w * i / 5
            svg += f'<line x1="{fx}" y1="{wy + 2}" x2="{fx}" y2="{wy + win_h - 2}" stroke="rgba(0,0,0,0.08)" stroke-width="0.7"/>'
        # RIGHT retracted panel
        rx = wx + win_w - stack_w
        for i in range(4):
            fold_x = rx + stack_w * (3 - i) / 4
            opacity = 0.35 - i * 0.05
            svg += f'<rect x="{fold_x}" y="{wy}" width="{stack_w / 3 + 2}" height="{win_h}" fill="{color}" opacity="{opacity}" rx="1"/>'
        for i in range(1, 5):
            fx = rx + stack_w * i / 5
            svg += f'<line x1="{fx}" y1="{wy + 2}" x2="{fx}" y2="{wy + win_h - 2}" stroke="rgba(0,0,0,0.08)" stroke-width="0.7"/>'
        # Tieback indicators
        tb_y = wy + win_h * 0.3
        svg += f'<path d="M{lx + stack_w},{tb_y} Q{lx + stack_w + 6},{tb_y + 8} {lx + stack_w},{tb_y + 16}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.5"/>'
        svg += f'<path d="M{rx},{tb_y} Q{rx - 6},{tb_y + 8} {rx},{tb_y + 16}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.5"/>'
        # Motor icon if motorized
        if has_motor:
            svg += f'<rect x="{cx - 12}" y="{wy - 10}" width="24" height="8" fill="#555" rx="2"/>'
            svg += f'<text x="{cx}" y="{wy - 4}" text-anchor="middle" font-size="5" fill="white" font-weight="bold">MOTOR</text>'

    # Width dimension (top)
    svg += f"""
      <line x1="{wx}" y1="{wy-15}" x2="{wx+win_w}" y2="{wy-15}" stroke="#D4AF37" stroke-width="1.2"/>
      <line x1="{wx}" y1="{wy-20}" x2="{wx}" y2="{wy-9}" stroke="#D4AF37" stroke-width="0.8"/>
      <line x1="{wx+win_w}" y1="{wy-20}" x2="{wx+win_w}" y2="{wy-9}" stroke="#D4AF37" stroke-width="0.8"/>
      <text x="{cx}" y="{wy-19}" text-anchor="middle" font-size="11" fill="#D4AF37" font-weight="bold">{w_in}"</text>"""

    # Height dimension (right)
    svg += f"""
      <line x1="{wx+win_w+15}" y1="{wy}" x2="{wx+win_w+15}" y2="{wy+win_h}" stroke="#D4AF37" stroke-width="1.2"/>
      <line x1="{wx+win_w+8}" y1="{wy}" x2="{wx+win_w+22}" y2="{wy}" stroke="#D4AF37" stroke-width="0.8"/>
      <line x1="{wx+win_w+8}" y1="{wy+win_h}" x2="{wx+win_w+22}" y2="{wy+win_h}" stroke="#D4AF37" stroke-width="0.8"/>
      <text x="{wx+win_w+28}" y="{wy+win_h/2+4}" text-anchor="start" font-size="11" fill="#D4AF37" font-weight="bold">{h_in}"</text>"""

    # Spec text below
    spec_y = wy + win_h + 18
    svg += f'<text x="{svg_w/2}" y="{spec_y}" text-anchor="middle" font-size="8.5" fill="#444">{treatment}</text>'
    if is_shade:
        svg += f'<text x="{svg_w/2}" y="{spec_y+13}" text-anchor="middle" font-size="8" fill="#777">Headrail · {"Motorized" if has_motor else "Cordless"}</text>'
    else:
        svg += f'<text x="{svg_w/2}" y="{spec_y+13}" text-anchor="middle" font-size="8" fill="#777">{hardware}{" · Motorized" if has_motor else ""}</text>'
    if price_low and price_high:
        svg += f'<text x="{svg_w/2}" y="{spec_y+27}" text-anchor="middle" font-size="10" fill="{color}" font-weight="bold">${price_low:,.0f} – ${price_high:,.0f}</text>'

    svg += "</svg>"

    svg += "</div>"
    return svg


def _build_proposal_notes(w: dict) -> str:
    """Build AI notes HTML for a proposal — rendered separately so it gets full page width."""
    ai = w.get("aiAnalysis")
    if not ai:
        return ""
    recs = ai.get("recommendations") or []
    window_type = ai.get("windowType", "")
    confidence = ai.get("confidence", 0)
    name = w.get("name", "Option")

    name_lower = name.lower()
    if "essential" in name_lower or "budget" in name_lower:
        color = "#22c55e"
    elif "designer" in name_lower or "choice" in name_lower:
        color = "#D4AF37"
    elif "luxury" in name_lower or "premium" in name_lower or "ultimate" in name_lower:
        color = "#8B5CF6"
    else:
        color = "#333"

    if not recs and not window_type:
        return ""

    html = f'<div style="margin:8px 0 12px;padding:10px 14px;background:#f8f5ff;border-left:3px solid {color};border-radius:0 6px 6px 0;font-size:0.82em;page-break-inside:avoid">'
    html += f'<span style="color:{color};font-weight:700">{name}</span>'
    if window_type:
        html += f' <span style="color:#666">· {window_type}</span>'
    if confidence:
        html += f' <span style="color:#22c55e">({confidence}%)</span>'
    for rec in recs[:2]:
        if rec:
            html += f'<p style="margin:4px 0 0;color:#555;line-height:1.5">→ {rec}</p>'
    html += '</div>'
    return html


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

        # Detect if this room has AI proposal windows (options, not cumulative)
        has_proposals = any(w.get("is_proposal") for w in windows)
        proposal_windows = [w for w in windows if w.get("is_proposal")]
        regular_windows = [w for w in windows if not w.get("is_proposal")]

        room_total = sum(w.get("price", 0) for w in regular_windows) + sum(u.get("price", 0) for u in upholstery)

        html += f'<h3 style="color:#D4AF37;margin:16px 0 6px;border-bottom:2px solid #D4AF37;padding-bottom:3px">{room["name"]}</h3>'

        # Regular (non-proposal) windows — standard table
        if regular_windows:
            html += """<table style="margin-bottom:12px"><thead><tr>
                <th>Window</th><th>Size</th><th>Treatment</th><th>Lining</th>
                <th>Hardware</th><th>Motor</th><th>Mount</th><th>Qty</th><th style="text-align:right">Price</th>
            </tr></thead><tbody>"""
            for w in regular_windows:
                ttype = treatment_labels.get(w.get("treatmentType", ""), w.get("treatmentType", "").replace("-", " ").title())
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

            html += '<div style="margin:8px 0 16px;page-break-inside:avoid">'
            for w in regular_windows:
                html += _build_window_drawing(w)
            html += '</div>'

        # AI Proposal windows — present as OPTIONS (choose one)
        if proposal_windows:
            tier_colors = ['#22c55e', '#D4AF37', '#8B5CF6']
            html += '<p style="font-size:0.85em;color:#666;margin-bottom:8px;font-style:italic">Choose one of the following treatment options:</p>'

            html += """<table style="margin-bottom:12px"><thead><tr>
                <th>Option</th><th>Treatment</th><th>Fabric & Lining</th>
                <th>Hardware</th><th>Extras</th><th style="text-align:right">Price Range</th>
            </tr></thead><tbody>"""
            for idx, w in enumerate(proposal_windows):
                color = tier_colors[idx % 3]
                low = w.get("price_range_low", 0)
                high = w.get("price_range_high", 0)
                extras = ", ".join(w.get("extras", []))
                html += f"""<tr>
                    <td style="padding:8px;border-bottom:1px solid #eee"><span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:700">{w.get('name', '')}</span></td>
                    <td style="padding:8px;border-bottom:1px solid #eee;font-weight:600">{w.get('treatmentType', '')}</td>
                    <td style="padding:8px;border-bottom:1px solid #eee;font-size:0.85em">{w.get('notes', '').split('.')[0]}<br><em style="color:#888">{w.get('liningType', '')}</em></td>
                    <td style="padding:8px;border-bottom:1px solid #eee;font-size:0.85em">{w.get('hardwareType', '')}</td>
                    <td style="padding:8px;border-bottom:1px solid #eee;font-size:0.85em">{extras or '—'}</td>
                    <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;font-weight:700;color:{color};white-space:nowrap">${low:,.0f} – ${high:,.0f}</td>
                </tr>"""
            html += "</tbody></table>"

            # Proposal SVGs with retracted drapes
            html += '<div style="margin:8px 0 4px;page-break-inside:avoid">'
            for w in proposal_windows:
                html += _build_proposal_drawing(w)
            html += '</div>'

            # AI notes for each proposal — full-width below the drawings row
            for w in proposal_windows:
                html += _build_proposal_notes(w)

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

            html += '<div style="margin:8px 0 16px;page-break-inside:avoid">'
            for u in upholstery:
                html += _build_upholstery_drawing(u)
            html += '</div>'

        if regular_windows or upholstery:
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


def _build_design_proposals_html(proposals: list) -> str:
    """Build 3-tier design option cards for the PDF — Essential / Designer / Premium."""
    if not proposals or len(proposals) < 2:
        return ""

    tier_styles = [
        {"color": "#22c55e", "bg": "#f0fdf4", "border": "#bbf7d0", "badge": "OPTION A"},
        {"color": "#D4AF37", "bg": "#fffcf0", "border": "#fde68a", "badge": "OPTION B"},
        {"color": "#8B5CF6", "bg": "#f5f3ff", "border": "#c4b5fd", "badge": "OPTION C"},
    ]

    html = """<div style="margin:24px 0;page-break-inside:avoid">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;border-bottom:2px solid #D4AF37;padding-bottom:8px">
      <div style="width:24px;height:24px;border-radius:6px;background:linear-gradient(135deg,#D4AF37,#8B5CF6);display:flex;align-items:center;justify-content:center;color:white;font-weight:900;font-size:11px">M</div>
      <div>
        <strong style="color:#1a1a2e;font-size:1.05em">Design Options</strong>
        <span style="font-size:0.75em;color:#888;margin-left:8px">AI-curated proposals tailored to your project</span>
      </div>
    </div>"""

    for i, prop in enumerate(proposals[:3]):
        s = tier_styles[i] if i < len(tier_styles) else tier_styles[-1]
        label = prop.get("label", f"Option {chr(65+i)}")
        grade = prop.get("fabric_grade", "A")
        lining = (prop.get("lining_type") or "standard").replace("-", " ").title()
        subtotal = prop.get("subtotal", 0)
        tax = prop.get("tax_amount", 0)
        total = prop.get("total", 0)
        comment = prop.get("ai_comment", "")
        items = prop.get("line_items", [])

        grade_labels = {"A": "Grade A — Quality Basics", "B": "Grade B — Designer Collection", "C": "Grade C — Luxury Premium"}
        grade_label = grade_labels.get(grade, f"Grade {grade}")

        # Build condensed line items
        items_rows = ""
        for item in items[:8]:
            desc = item.get("description", "")
            item_total = item.get("total", 0)
            items_rows += f"""<tr>
              <td style="padding:3px 6px;font-size:0.78em;color:#444;border-bottom:1px solid #f0f0f0">{desc}</td>
              <td style="padding:3px 6px;font-size:0.78em;color:#444;text-align:right;border-bottom:1px solid #f0f0f0">${item_total:,.2f}</td>
            </tr>"""
        if len(items) > 8:
            items_rows += f'<tr><td colspan="2" style="padding:3px 6px;font-size:0.72em;color:#999;font-style:italic">+ {len(items)-8} more items</td></tr>'

        html += f"""<div style="margin-bottom:14px;border:2px solid {s['border']};border-radius:10px;overflow:hidden;background:white;page-break-inside:avoid">
          <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:{s['bg']}">
            <div style="display:flex;align-items:center;gap:10px">
              <span style="background:{s['color']};color:white;padding:4px 12px;border-radius:5px;font-size:0.72em;font-weight:700;letter-spacing:0.5px">{s['badge']}</span>
              <div>
                <strong style="color:#1a1a2e;font-size:0.95em">{label.split('—')[-1].strip() if '—' in label else label}</strong>
                <p style="margin:1px 0 0;font-size:0.75em;color:#888">{grade_label} · {lining} Lining</p>
              </div>
            </div>
            <div style="text-align:right">
              <strong style="font-size:1.2em;color:{s['color']}">${total:,.2f}</strong>
              <p style="margin:1px 0 0;font-size:0.7em;color:#888">incl. tax</p>
            </div>
          </div>"""

        if comment:
            html += f"""<div style="padding:10px 16px;border-bottom:1px solid #f0f0f0;background:#fafbfd">
              <p style="margin:0;font-size:0.82em;color:#444;line-height:1.5;font-style:italic">{comment}</p>
            </div>"""

        if items_rows:
            html += f"""<div style="padding:8px 16px 10px">
              <table style="width:100%;border-collapse:collapse;margin:0">
                <thead><tr>
                  <th style="padding:3px 6px;font-size:0.7em;text-transform:uppercase;letter-spacing:0.5px;color:#999;text-align:left;border-bottom:1px solid #eee;background:transparent">Item</th>
                  <th style="padding:3px 6px;font-size:0.7em;text-transform:uppercase;letter-spacing:0.5px;color:#999;text-align:right;border-bottom:1px solid #eee;background:transparent">Price</th>
                </tr></thead>
                <tbody>{items_rows}</tbody>
                <tfoot>
                  <tr><td style="padding:4px 6px;font-size:0.78em;color:#666;text-align:right">Subtotal</td>
                    <td style="padding:4px 6px;font-size:0.78em;color:#666;text-align:right">${subtotal:,.2f}</td></tr>
                  <tr><td style="padding:4px 6px;font-size:0.78em;color:#666;text-align:right">Tax</td>
                    <td style="padding:4px 6px;font-size:0.78em;color:#666;text-align:right">${tax:,.2f}</td></tr>
                  <tr><td style="padding:4px 6px;font-size:0.85em;font-weight:700;color:#1a1a2e;text-align:right;border-top:2px solid {s['color']}">Total</td>
                    <td style="padding:4px 6px;font-size:0.85em;font-weight:700;color:{s['color']};text-align:right;border-top:2px solid {s['color']}">${total:,.2f}</td></tr>
                </tfoot>
              </table>
            </div>"""

        html += "</div>"

    html += "</div>"
    return html


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

    # Proposal cards — only show text-only cards if NO AI images exist (avoids duplicate info)
    tier_colors = {'budget': '#22c55e', 'mid-range': '#D4AF37', 'premium': '#8B5CF6',
                   'elegant essential': '#22c55e', "designer's choice": '#D4AF37', 'ultimate luxury': '#8B5CF6'}
    gen_images = mockup.get("generated_images") or []
    has_images = len(gen_images) > 0

    if proposals and not has_images:
        # Text-only proposal cards (fallback when no AI images)
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

    # AI-Generated Mockup Images — each full-width with matching proposal notes below
    if has_images:
        html += '<div style="margin-top:16px">'
        html += '<p style="font-size:0.85em;font-weight:700;color:#ec4899;margin-bottom:12px">AI-Generated Treatment Mockups</p>'
        for img in gen_images[:3]:
            tier = img.get("tier", "Mockup")
            url = img.get("url", "")
            if not url:
                continue
            # Find matching proposal by tier name
            matching = next((p for p in proposals if p.get("tier", "").lower() == tier.lower()), None)
            tier_lower = tier.lower()
            color = tier_colors.get(tier_lower, '#333')
            html += f"""<div style="margin-bottom:12px;page-break-inside:avoid;border:2px solid {color};border-radius:8px;overflow:hidden;background:white">
                <div style="background:{color};color:white;padding:4px 12px;font-size:0.8em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">{tier}</div>
                <img src="{url}" style="width:100%;max-height:360px;object-fit:contain;display:block" />"""
            if matching:
                price_low = matching.get("price_range_low", 0)
                price_high = matching.get("price_range_high", 0)
                html += f"""<div style="padding:14px 16px;border-top:1px solid #eee">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                        <p style="font-weight:700;font-size:1em;margin:0;color:#1a1a2e">{matching.get('treatment_type', '')} — {matching.get('style', '')}</p>
                        <p style="font-weight:700;color:{color};font-size:1.1em;margin:0">${price_low:,.0f} – ${price_high:,.0f}</p>
                    </div>
                    <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:0.82em;color:#555;margin-bottom:6px">
                        <span><strong>Fabric:</strong> {matching.get('fabric', '')}</span>
                        <span><strong>Lining:</strong> {matching.get('lining', '')}</span>
                        <span><strong>Hardware:</strong> {matching.get('hardware', '')}</span>
                        {f"<span><strong>Extras:</strong> {', '.join(matching.get('extras', []))}</span>" if matching.get('extras') else ""}
                    </div>
                    <p style="font-size:0.82em;color:#666;font-style:italic;margin:4px 0;line-height:1.5">{matching.get('visual_description', '')}</p>
                    {f"<p style='font-size:0.78em;color:#888;margin:4px 0'>{matching.get('design_rationale', '')}</p>" if matching.get('design_rationale') else ""}
                </div>"""
            else:
                html += f'<div style="padding:8px 16px;border-top:1px solid #eee"><p style="font-weight:600;font-size:0.85em;color:#666">{tier}</p></div>'
            html += '</div>'
        html += '</div>'

    # General recommendations
    if recs:
        html += '<div style="margin-top:12px;padding:10px;background:#f8f8f8;border-radius:6px;font-size:0.85em"><strong>Recommendations:</strong><ul style="margin:4px 0;padding-left:20px">'
        for r in recs:
            html += f'<li>{r}</li>'
        html += '</ul></div>'

    html += '</div>'
    return html


def _download_image_as_data_uri(url: str) -> str:
    """Download an external image URL and return a base64 data URI for reliable PDF embedding."""
    if not url or url.startswith("data:"):
        return url
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "image/png")
        b64 = base64.b64encode(resp.content).decode()
        return f"data:{ct};base64,{b64}"
    except Exception as e:
        logger.warning(f"Failed to download image for PDF: {e}")
        return url  # Fallback to URL — WeasyPrint may still fetch it


def _embed_external_images(quote: dict) -> dict:
    """Pre-download all external AI-generated image URLs and convert to base64 data URIs."""
    # Mockup generated_images
    for mockup in (quote.get("ai_mockups") or []):
        for img in (mockup.get("generated_images") or []):
            if img.get("url") and not img["url"].startswith("data:"):
                img["url"] = _download_image_as_data_uri(img["url"])

    # Upholstery generated_image in rooms
    for room in (quote.get("rooms") or []):
        for u in room.get("upholstery", []):
            ai = u.get("aiAnalysis")
            if ai and ai.get("generated_image") and not ai["generated_image"].startswith("data:"):
                ai["generated_image"] = _download_image_as_data_uri(ai["generated_image"])

    return quote


# ── Category icons for line item breakdown ─────────────────────────
_CAT_ICONS = {
    "fabric": "🧵", "lining": "🪡", "labor": "⚙️",
    "hardware": "🔩", "installation": "📐", "product": "📦", "upholstery": "🛋️",
}
_CAT_ORDER = ["fabric", "lining", "labor", "hardware", "installation", "product", "upholstery"]


def _build_line_items_html(line_items: list) -> str:
    """Build an itemized cost breakdown table grouped by room, with category labels."""
    if not line_items or not any(item.get("category") for item in line_items):
        return ""  # Old-style quotes without categories — skip

    rooms_seen = []
    rooms_items = {}
    for item in line_items:
        r = item.get("room", "General")
        if r not in rooms_items:
            rooms_seen.append(r)
            rooms_items[r] = []
        rooms_items[r].append(item)

    html = """<div style="margin-top:20px;page-break-inside:avoid">
    <h3 style="color:#1a1a2e;margin:0 0 10px;font-size:1em;text-transform:uppercase;letter-spacing:0.5px">
      Itemized Cost Breakdown</h3>
    <table><thead><tr>
      <th style="width:5%"></th><th style="width:50%">Description</th>
      <th style="width:10%;text-align:center">Qty</th>
      <th style="width:17%;text-align:right">Unit Price</th>
      <th style="width:18%;text-align:right">Amount</th>
    </tr></thead><tbody>"""

    for room_name in rooms_seen:
        items = rooms_items[room_name]
        room_total = sum((i.get("total", 0) or i.get("amount", 0) or (i.get("unit_price", 0) or i.get("rate", 0)) * i.get("quantity", 1)) for i in items)
        html += f"""<tr><td colspan="5" style="padding:10px 8px 4px;font-weight:700;color:#1a1a2e;
            border-bottom:2px solid #D4AF37;font-size:0.9em">{room_name}</td></tr>"""
        for item in items:
            cat = item.get("category", "")
            icon = _CAT_ICONS.get(cat, "")
            cat_label = f'<span style="color:#999;font-size:0.75em;text-transform:uppercase">{cat}</span>' if cat else ""
            html += f"""<tr>
                <td style="padding:5px 4px;border-bottom:1px solid #f0f0f0;text-align:center;font-size:0.9em">{icon}</td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0">
                    <span style="font-size:0.85em">{item['description']}</span><br>{cat_label}</td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:center;font-size:0.85em">{item['quantity']}</td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:right;font-size:0.85em">${item.get('unit_price', 0) or item.get('rate', 0):,.2f}</td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:right;font-size:0.85em;font-weight:600">${item.get('total', 0) or item.get('amount', 0) or (item.get('unit_price', 0) or item.get('rate', 0)) * item.get('quantity', 1):,.2f}</td>
            </tr>"""
        html += f"""<tr><td colspan="4" style="padding:6px 8px;text-align:right;font-size:0.82em;color:#666">
            Room Subtotal</td>
            <td style="padding:6px 8px;text-align:right;font-weight:700;font-size:0.9em;border-bottom:2px solid #eee">
            ${room_total:,.2f}</td></tr>"""

    html += "</tbody></table></div>"
    return html


@router.post("/{quote_id}/pdf")
async def generate_pdf(quote_id: str):
    """Generate PDF for a quote with room-level detail, drawings, and mockups."""
    quote = _load_quote(quote_id)

    rooms = quote.get("rooms") or []
    ai_mockups = quote.get("ai_mockups") or []

    # ── Auto-generate mockup images if none exist ──
    xai_key = os.environ.get("XAI_API_KEY")
    if not ai_mockups and xai_key and rooms:
        treatment_labels = {
            'ripplefold': 'Ripplefold', 'pinch-pleat': 'Pinch Pleat', 'rod-pocket': 'Rod Pocket',
            'grommet': 'Grommet Top', 'roman-shade': 'Roman Shade', 'roller-shade': 'Roller Shade',
        }
        try:
            for room in rooms:
                room_name = room.get("name", "Room")
                windows = room.get("windows", [])
                if not windows:
                    continue
                gen_images = []
                async with httpx.AsyncClient(timeout=30) as client:
                    for win in windows[:3]:
                        treatment = win.get("treatmentType", "ripplefold")
                        label = treatment_labels.get(treatment, treatment.replace('-', ' ').title())
                        w = win.get("width", 48)
                        h = win.get("height", 60)
                        hardware = (win.get("hardwareType") or "decorative rod").replace('-', ' ')
                        mount = win.get("mountType", "wall")
                        prompt = (
                            f"Professional interior design photo: a {room_name.lower()} with a "
                            f"{w}-inch wide by {h}-inch tall window. "
                            f"Installed: {label} drapery panels in elegant fabric. "
                            f"The panels hang from {hardware} hardware, {mount}-mounted. "
                            f"Clean, bright natural light. Magazine-quality architectural photography."
                        )
                        try:
                            resp = await client.post(
                                "https://api.x.ai/v1/images/generations",
                                headers={"Content-Type": "application/json", "Authorization": f"Bearer {xai_key}"},
                                json={"model": "grok-imagine-image", "prompt": prompt, "n": 1, "response_format": "url"},
                            )
                            if resp.status_code == 200:
                                img_url = resp.json().get("data", [{}])[0].get("url")
                                if img_url:
                                    gen_images.append({"tier": f"{label} — {win.get('name', 'Window')}", "url": img_url})
                        except Exception as img_err:
                            logger.warning(f"PDF mockup gen failed for {room_name}/{win.get('name')}: {img_err}")
                if gen_images:
                    ai_mockups.append({
                        "roomName": room_name,
                        "generated_images": gen_images,
                        "proposals": [],
                        "generalRecommendations": [],
                    })
            if ai_mockups:
                quote["ai_mockups"] = ai_mockups
                # Save back so next PDF doesn't regenerate
                _save_quote(quote)
                logger.info(f"Auto-generated {sum(len(m['generated_images']) for m in ai_mockups)} mockup images for PDF")
        except Exception as e:
            logger.warning(f"Auto-mockup generation failed: {e}")

    # Pre-download external AI images as base64 for reliable PDF embedding
    quote = _embed_external_images(quote)

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

    # Design Proposals (3-tier options: Essential / Designer / Premium)
    design_proposals = quote.get("design_proposals") or []
    proposals_html = _build_design_proposals_html(design_proposals)

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
  @page {{ size: letter; margin: 0.5in 0.6in; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; max-width: 800px; margin: 0 auto; padding: 0; font-size: 12px; line-height: 1.45; }}
  h1 {{ color: #1a1a2e; margin: 0; font-size: 28px; letter-spacing: -0.5px; }}
  h3 {{ page-break-after: avoid; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  th {{ background: #1a1a2e; color: #D4AF37; padding: 8px 6px; text-align: left; font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ font-size: 0.85em; }}
</style></head><body>

<!-- ═══ HEADER / LETTERHEAD ═══ -->
<div style="border-bottom:3px solid #D4AF37;padding-bottom:14px;margin-bottom:16px">
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
<div style="display:flex;gap:16px;margin-bottom:16px">
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

<!-- ═══ DESIGN OPTIONS (3-TIER) ═══ -->
{proposals_html}

<!-- ═══ ITEMIZED COST BREAKDOWN ═══ -->
{_build_line_items_html(quote.get("line_items", [])) if not design_proposals else ""}

<!-- ═══ TOTALS ═══ -->
{f'''<table style="margin-top:16px"><tbody>
  <tr><td colspan="8" style="padding:10px 8px;text-align:right;color:#666;font-style:italic">
    Treatment options range from</td>
  <td style="padding:10px 8px;text-align:right;font-weight:700;color:#D4AF37;font-size:1.15em;white-space:nowrap">
    ${min(p["total"] for p in design_proposals):,.0f} &ndash; ${max(p["total"] for p in design_proposals):,.0f}</td></tr>
</tbody></table>''' if design_proposals else f'''<table style="margin-top:16px"><tbody>
  {f"<tr><td colspan='8' style='padding:10px 8px;text-align:right;color:#666;font-style:italic'>Treatment options range from</td><td style='padding:10px 8px;text-align:right;font-weight:700;color:#D4AF37;font-size:1.1em;white-space:nowrap'>${quote['price_range_low']:,.0f} &ndash; ${quote['price_range_high']:,.0f}</td></tr>" if quote.get("price_range_low") else f"""
  <tr><td colspan='8' style='padding:8px;text-align:right;color:#666'>Subtotal</td>
  <td style='padding:8px;text-align:right;color:#666'>${quote["subtotal"]:.2f}</td></tr>
  {"<tr><td colspan='8' style='padding:8px;text-align:right;color:#c00'>Discount</td><td style='padding:8px;text-align:right;color:#c00'>-$" + f"{quote['discount_amount']:.2f}</td></tr>" if quote.get('discount_amount') else ""}
  <tr><td colspan='8' style='padding:8px;text-align:right;color:#666'>Tax ({quote.get('tax_rate', 0) * 100:.1f}%)</td>
  <td style='padding:8px;text-align:right;color:#666'>${quote.get('tax_amount', 0):.2f}</td></tr>
  <tr><td colspan='8' style='padding:14px 8px;text-align:right;border-top:3px solid #D4AF37'><strong style='font-size:1.15em;color:#1a1a2e'>Total</strong></td>
  <td style='padding:14px 8px;text-align:right;border-top:3px solid #D4AF37'><strong style='font-size:1.2em;color:#D4AF37'>${quote["total"]:.2f}</strong></td></tr>"""}
  {deposit_html}
</tbody></table>'''}

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
    pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
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
        os.path.expanduser("~/empire-repo/backend/data/quotes/pdf"),
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
