"""
Quote/Estimate CRUD router.
Stores quotes as JSON files (same pattern as chat history).
PDF generation via POST /api/v1/quotes/{id}/pdf.
"""
from fastapi import APIRouter, HTTPException
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


@router.post("/{quote_id}/pdf")
async def generate_pdf(quote_id: str):
    """Generate PDF for a quote. Returns HTML for now (PDF lib can be added)."""
    quote = _load_quote(quote_id)

    # Build HTML document
    items_html = ""
    for item in quote.get("line_items", []):
        items_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee">{item['description']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:center">{item['quantity']} {item['unit']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">${item['rate']:.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">${item['amount']:.2f}</td>
        </tr>"""

    measurements = quote.get("measurements") or {}
    meas_html = ""
    if measurements.get("width") or measurements.get("height"):
        dims = []
        if measurements.get("width"):
            dims.append(f"W: {measurements['width']}{measurements.get('unit', 'in')}")
        if measurements.get("height"):
            dims.append(f"H: {measurements['height']}{measurements.get('unit', 'in')}")
        if measurements.get("depth"):
            dims.append(f"D: {measurements['depth']}{measurements.get('unit', 'in')}")
        meas_html = f"""
        <div style="margin:16px 0;padding:12px;background:#f8f8f8;border-radius:8px">
            <strong>Measurements:</strong> {' × '.join(dims)}
            {f"<br>Room: {measurements['room']}" if measurements.get('room') else ""}
            {f"<br>Notes: {measurements['notes']}" if measurements.get('notes') else ""}
        </div>"""

    deposit = quote.get("deposit") or {}
    deposit_html = ""
    if deposit.get("deposit_amount"):
        deposit_html = f"""
        <tr><td colspan="3" style="padding:8px;text-align:right"><strong>Deposit ({deposit.get('deposit_percent', 50)}%)</strong></td>
        <td style="padding:8px;text-align:right"><strong>${deposit['deposit_amount']:.2f}</strong></td></tr>"""

    install_date = ""
    if quote.get("install_date"):
        install_date = f"<p><strong>Estimated Install Date:</strong> {quote['install_date']}</p>"

    logo_html = ""
    biz_name = quote.get("business_name") or "Empire"
    if quote.get("business_logo_url"):
        logo_html = f'<img src="{quote["business_logo_url"]}" style="max-height:60px;margin-bottom:8px" /><br>'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{quote['quote_number']}</title>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; max-width: 800px; margin: 0 auto; padding: 40px; }}
  h1 {{ color: #D4AF37; margin-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #1a1a2e; color: #D4AF37; padding: 10px 8px; text-align: left; }}
  th:nth-child(2), th:nth-child(3), th:nth-child(4) {{ text-align: center; }}
  th:last-child {{ text-align: right; }}
</style></head><body>
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:32px">
  <div>{logo_html}<h1>{biz_name}</h1></div>
  <div style="text-align:right">
    <h2 style="margin:0;color:#333">ESTIMATE</h2>
    <p style="margin:4px 0;color:#666">{quote['quote_number']}</p>
    <p style="margin:4px 0;color:#666">Date: {quote['created_at'][:10]}</p>
    <p style="margin:4px 0;color:#666">Valid: {quote.get('valid_days', 30)} days</p>
  </div>
</div>

<div style="margin-bottom:24px;padding:16px;background:#f0f0f0;border-radius:8px">
  <strong>Bill To:</strong><br>
  {quote['customer_name']}<br>
  {quote.get('customer_email') or ''}<br>
  {quote.get('customer_phone') or ''}<br>
  {quote.get('customer_address') or ''}
</div>

{f"<p><strong>Project:</strong> {quote['project_name']}</p>" if quote.get('project_name') else ""}
{f"<p>{quote['project_description']}</p>" if quote.get('project_description') else ""}
{meas_html}

<table>
  <thead><tr>
    <th>Description</th><th>Qty</th><th>Rate</th><th style="text-align:right">Amount</th>
  </tr></thead>
  <tbody>
    {items_html}
    <tr><td colspan="3" style="padding:8px;text-align:right">Subtotal</td>
    <td style="padding:8px;text-align:right">${quote['subtotal']:.2f}</td></tr>
    {"<tr><td colspan='3' style='padding:8px;text-align:right'>Discount</td><td style='padding:8px;text-align:right;color:#c00'>-$" + f"{quote['discount_amount']:.2f}</td></tr>" if quote.get('discount_amount') else ""}
    <tr><td colspan="3" style="padding:8px;text-align:right">Tax ({quote.get('tax_rate', 0) * 100:.1f}%)</td>
    <td style="padding:8px;text-align:right">${quote['tax_amount']:.2f}</td></tr>
    <tr style="font-size:1.1em"><td colspan="3" style="padding:12px 8px;text-align:right;border-top:2px solid #D4AF37"><strong>Total</strong></td>
    <td style="padding:12px 8px;text-align:right;border-top:2px solid #D4AF37"><strong>${quote['total']:.2f}</strong></td></tr>
    {deposit_html}
  </tbody>
</table>

{install_date}

{f"<div style='margin-top:24px;padding:16px;background:#fffcf0;border:1px solid #D4AF37;border-radius:8px'><strong>Terms:</strong><br>{quote['terms']}</div>" if quote.get('terms') else ""}
{f"<div style='margin-top:12px;padding:12px;background:#f8f8f8;border-radius:8px;font-size:0.9em;color:#666'><strong>Notes:</strong> {quote['notes']}</div>" if quote.get('notes') else ""}

<div style="margin-top:40px;text-align:center;color:#999;font-size:0.8em">
  Generated by {biz_name} · Powered by EmpireBox
</div>
</body></html>"""

    # Save HTML file
    pdf_dir = os.path.expanduser("~/Empire/data/quotes/pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    html_path = os.path.join(pdf_dir, f"{quote['quote_number']}.html")
    with open(html_path, "w") as f:
        f.write(html)

    return {
        "status": "generated",
        "format": "html",
        "path": html_path,
        "quote_number": quote["quote_number"],
        "html": html,
    }
