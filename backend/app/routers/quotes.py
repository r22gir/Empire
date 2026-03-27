"""
Quote/Estimate CRUD router.
Stores quotes as JSON files (same pattern as chat history).
PDF generation via POST /api/v1/quotes/{id}/pdf.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime, timedelta
import json
import uuid
import os
from pathlib import Path
import base64
import httpx
import logging

from app.services.max.response_quality_engine import quality_engine, Channel

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

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data):
        """Accept qty/unit_price as aliases for quantity/rate."""
        if isinstance(data, dict):
            if "qty" in data and "quantity" not in data:
                data["quantity"] = data.pop("qty")
            if "unit_price" in data and "rate" not in data:
                data["rate"] = data.pop("unit_price")
            if "price" in data and "rate" not in data:
                data["rate"] = data.pop("price")
        return data

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

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data):
        """Accept 'items' as alias for 'line_items'."""
        if isinstance(data, dict):
            if "items" in data and "line_items" not in data:
                data["line_items"] = data.pop("items")
        return data
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
    pricing_mode: Optional[str] = None     # "flat" = skip tier engine, use line_items as-is
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
    photos: Optional[list] = None
    rooms: Optional[list] = None
    pricing_mode: Optional[str] = None     # "flat" = skip tier engine
    ai_outlines: Optional[list] = None
    ai_mockups: Optional[list] = None
    max_analysis: Optional[str] = None
    scan_3d_files: Optional[list] = None


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

    # Quality gate: validate quote before saving
    qr = quality_engine.validate(
        json.dumps(quote, default=str),
        channel=Channel.QUOTE,
        context={"quote_data": quote},
    )
    if qr.blocked:
        # Log to accuracy monitor
        try:
            from app.services.max.accuracy_monitor import accuracy_monitor
            accuracy_monitor.log_audit(
                user_query=f"Create quote for {quote.get('customer_name', 'unknown')}",
                response_text=json.dumps(quote, default=str)[:3000],
                verification=type('V', (), {'claims_found': len(qr.issues), 'claims_verified': 0, 'claims_stripped': len(qr.issues), 'phantom_citations_removed': 0})(),
                model_used="quality_engine",
                channel="quote",
                output_type="quote_create",
                quality_severity=qr.severity,
                fixed_by_engine=qr.fixed_count,
            )
        except Exception:
            pass
        # Alert founder via Telegram
        try:
            import asyncio
            from app.services.max.telegram_bot import telegram_bot
            issues_text = "\n".join(f"• {i.message}" for i in qr.issues[:5])
            asyncio.create_task(telegram_bot.send_message(
                f"🚨 <b>QUOTE BLOCKED</b>\n\nQuote for {quote.get('customer_name', 'unknown')} — ${quote.get('total', 0):,.2f}\n\n<b>Issues:</b>\n{issues_text}"
            ))
        except Exception:
            pass
        raise HTTPException(422, detail={
            "message": "Quote blocked by quality engine",
            "issues": [{"check": i.check, "severity": i.severity.value, "message": i.message} for i in qr.issues],
        })

    # Log quality check (even if passed)
    if qr.issues:
        try:
            from app.services.max.accuracy_monitor import accuracy_monitor
            accuracy_monitor.log_audit(
                user_query=f"Create quote for {quote.get('customer_name', 'unknown')}",
                response_text=json.dumps(quote, default=str)[:3000],
                verification=type('V', (), {'claims_found': len(qr.issues), 'claims_verified': len(qr.issues) - qr.fixed_count, 'claims_stripped': qr.fixed_count, 'phantom_citations_removed': 0})(),
                model_used="quality_engine",
                channel="quote",
                output_type="quote_create",
                quality_severity=qr.severity,
                fixed_by_engine=qr.fixed_count,
            )
        except Exception:
            pass

    _save_quote(quote)
    return {"status": "created", "quote": quote}


@router.get("")
async def list_quotes(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    business: Optional[str] = None,
    summary: bool = True,
):
    """List quotes with pagination.  When summary=true (default) strips
    heavy tier/item data to keep the response small for list views."""
    quotes = []
    for fname in os.listdir(QUOTES_DIR):
        if not fname.endswith(".json") or fname.startswith("_") or "_verification" in fname:
            continue
        with open(os.path.join(QUOTES_DIR, fname)) as f:
            q = json.load(f)
        if status and q.get("status") != status:
            continue
        quotes.append(q)
    quotes.sort(key=lambda q: q.get("created_at", ""), reverse=True)

    total = len(quotes)
    quotes = quotes[offset:offset + limit]

    if summary:
        # Strip heavy nested data — keep only what the list view needs
        light = []
        for q in quotes:
            # Flat-priced quotes: use the stored total directly
            if q.get("pricing_mode") == "flat" and q.get("total") is not None:
                display_total = q["total"]
            else:
                # Compute total from tier A (or first tier)
                display_total = 0
                tiers = q.get("tiers", {})
                if isinstance(tiers, dict):
                    first = tiers.get("A") or next(iter(tiers.values()), {})
                    display_total = first.get("total", 0)
                elif isinstance(tiers, list) and tiers:
                    display_total = tiers[0].get("total", 0)
                # Fallback: if no tiers but total exists, use it
                if display_total == 0 and q.get("total"):
                    display_total = q["total"]

            light.append({
                "id": q.get("id"),
                "quote_number": q.get("quote_number"),
                "customer_name": q.get("customer_name"),
                "customer_email": q.get("customer_email"),
                "customer_phone": q.get("customer_phone"),
                "project_name": q.get("project_name"),
                "status": q.get("status"),
                "total": display_total,
                "pricing_mode": q.get("pricing_mode"),
                "item_count": len(q.get("items", q.get("line_items", []))),
                "intake_code": q.get("intake_code"),
                "created_at": q.get("created_at"),
                "updated_at": q.get("updated_at"),
                "location": q.get("location"),
            })
        return {"quotes": light, "count": len(light), "total": total}

    return {"quotes": quotes, "count": len(quotes), "total": total}


# ── QIS (Quote Intelligence System) endpoints ──────────────────
# These MUST be above /{quote_id} catch-all route

@router.post("/analyze-photo")
async def analyze_photo_for_quote(body: dict):
    """Run full QIS pipeline on a photo. Returns analyzed items with pricing for all 3 tiers."""
    from app.services.quote_engine.item_analyzer import analyze_photo_items
    from app.services.quote_engine.quote_assembler import assemble_quote

    image = body.get("image", "")
    customer_name = body.get("customer_name", "Customer")
    customer_notes = body.get("notes", "")
    location = body.get("location", "DC")
    lining = body.get("lining", "standard")

    if not image:
        raise HTTPException(400, "Image data required")

    analysis = await analyze_photo_items(image, customer_notes)

    quote = assemble_quote(
        analyzed_items=analysis.get("items", []),
        customer_name=customer_name,
        location=location,
        lining=lining,
    )

    # Save to disk (assemble_quote no longer saves)
    os.makedirs(QUOTES_DIR, exist_ok=True)
    with open(os.path.join(QUOTES_DIR, f"{quote['id']}.json"), "w") as f:
        json.dump(quote, f, indent=2, default=str)

    # ── GATE 1: Post-analysis verification ──
    from app.services.quote_engine.verification import verify_quote, save_verification

    verification = verify_quote(quote)
    save_verification(quote.get("id", ""), verification)

    return {
        "analysis": analysis,
        "quote": quote,
        "verification": verification,
    }


@router.post("/from-rooms")
async def create_quote_from_rooms(body: dict):
    """Create a priced quote from rooms data (frontend Quote Builder).

    Converts rooms with items+dimensions into analyzed_items format,
    runs through the full QIS pricing pipeline (yardage, tiers, line items).

    If the existing quote has pricing_mode="flat", skip the tier engine
    entirely and preserve the flat line_items/totals as-is.
    """
    # ── FLAT PRICING GUARD ──────────────────────────────────────
    # If editing an existing flat-priced quote, skip tier calculations.
    existing_quote_id = body.get("quote_id")
    if existing_quote_id:
        old_path = _quote_path(existing_quote_id)
        if os.path.exists(old_path):
            with open(old_path) as f:
                old_quote = json.load(f)
            if old_quote.get("pricing_mode") == "flat":
                # Update customer/room info but preserve flat pricing
                old_quote["customer_name"] = body.get("customer_name", old_quote.get("customer_name"))
                old_quote["customer_email"] = body.get("customer_email", old_quote.get("customer_email"))
                old_quote["customer_phone"] = body.get("customer_phone", old_quote.get("customer_phone"))
                old_quote["customer_address"] = body.get("customer_address", old_quote.get("customer_address"))
                if body.get("rooms"):
                    old_quote["rooms"] = body["rooms"]
                old_quote["photos"] = body.get("photos", old_quote.get("photos", []))
                old_quote["options"] = body.get("options", old_quote.get("options", {}))
                old_quote["updated_at"] = datetime.utcnow().isoformat()
                # Recompute flat financials from line_items
                old_quote = _compute_financials(old_quote)
                _save_quote(old_quote)
                return {"status": "success", "quote": old_quote}

    from app.services.quote_engine.quote_assembler import assemble_quote

    customer_name = body.get("customer_name", "Customer")
    customer_email = body.get("customer_email", "")
    customer_phone = body.get("customer_phone", "")
    customer_address = body.get("customer_address", "")
    rooms = body.get("rooms", [])
    options = body.get("options", {})
    photos = body.get("photos", [])

    if not rooms:
        raise HTTPException(400, "At least one room with items is required")

    location = body.get("location", "DC")
    lining = options.get("lining_type", "standard")
    fabric_grade = options.get("fabric_grade", "A")
    # Support both flat options (frontend sends options.tufting) and nested (options.features.tufting)
    features = options.get("features", options)

    # Convert rooms data to analyzed_items format for pricing engine
    analyzed_items = []
    for room in rooms:
        room_name = room.get("name", "Room")
        for item in room.get("items", []):
            dims = item.get("dimensions", {})
            width = _parse_dim(dims.get("width", item.get("width", 0)))
            height = _parse_dim(dims.get("height", item.get("height", 0)))
            depth = _parse_dim(dims.get("depth", item.get("depth", 0)))

            item_type = item.get("type", "accent_chair")
            quantity = int(item.get("quantity", 1))
            notes = item.get("notes", "")

            special_features = []
            if features.get("tufting") and features.get("tufting") != "none": special_features.append("tufting")
            if features.get("welting") and features.get("welting") != "none": special_features.append("welting")
            if features.get("nailhead_finish") and features.get("nailhead_finish") != "none": special_features.append("nailhead trim")
            if features.get("skirt_style") and features.get("skirt_style") != "none": special_features.append("skirt")
            if features.get("contrast_piping"): special_features.append("contrast piping")
            if features.get("pattern_match"): special_features.append("pattern match")

            cushion_count = 0
            if "3cushion" in item_type: cushion_count = 3
            elif "2cushion" in item_type: cushion_count = 2
            elif "cushion" in item_type.lower() or "seat" in item_type.lower(): cushion_count = 1

            analyzed_items.append({
                "name": f"{room_name} - {item_type.replace('_', ' ').title()}",
                "type": item_type,
                "dimensions": {"width": width, "height": height, "depth": depth},
                "quantity": quantity,
                "construction": "",
                "condition": "",
                "special_features": special_features,
                "cushion_count": cushion_count,
            })

    if not analyzed_items:
        raise HTTPException(400, "No items found in rooms data")

    quote = assemble_quote(
        analyzed_items=analyzed_items,
        customer_name=customer_name,
        location=location,
        lining=lining,
    )

    # If editing an existing quote, reuse its ID and quote_number
    existing_quote_id = body.get("quote_id")
    if existing_quote_id:
        old_path = _quote_path(existing_quote_id)
        if os.path.exists(old_path):
            with open(old_path) as f:
                old_quote = json.load(f)
            quote["id"] = existing_quote_id
            quote["quote_number"] = old_quote.get("quote_number", quote.get("quote_number"))
            quote["created_at"] = old_quote.get("created_at", quote.get("created_at"))
            # Remove the new auto-generated file if different ID
            new_path = _quote_path(quote["id"])
            if new_path != old_path and os.path.exists(new_path):
                os.remove(new_path)

    # Enrich with customer info and options
    quote["customer_email"] = customer_email
    quote["customer_phone"] = customer_phone
    quote["customer_address"] = customer_address
    quote["fabric_grade"] = fabric_grade
    quote["photos"] = photos
    quote["rooms"] = rooms
    quote["options"] = options

    if options.get("rush_order"):
        for tier_key in quote.get("tiers", {}):
            tier = quote["tiers"][tier_key]
            rush_amount = round(tier.get("subtotal", 0) * 0.20, 2)
            # Add rush surcharge to last item's line_items (line_items live inside items, not at tier level)
            if tier.get("items"):
                tier["items"][-1].get("line_items", []).append({
                    "category": "surcharge",
                    "description": "Rush Order Surcharge (20%)",
                    "quantity": 1, "unit": "ea",
                    "rate": rush_amount, "amount": rush_amount,
                })
            tier["subtotal"] = round(tier["subtotal"] + rush_amount, 2)
            tier["tax"] = round(tier["subtotal"] * tier.get("tax_rate", 0.06), 2)
            tier["total"] = round(tier["subtotal"] + tier["tax"], 2)
            tier["deposit"] = round(tier["total"] * 0.5, 2)

    # Save
    os.makedirs(QUOTES_DIR, exist_ok=True)
    with open(os.path.join(QUOTES_DIR, f"{quote['id']}.json"), "w") as f:
        json.dump(quote, f, indent=2, default=str)

    return {"status": "success", "quote": quote}


def _parse_dim(val) -> float:
    """Parse dimension to float (handles strings, ints, empty)."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val) if val.strip() else 0.0
        except ValueError:
            return 0.0
    return 0.0


@router.post("/preview-pricing")
async def preview_pricing(body: dict):
    """Preview tier pricing for items without creating/saving a quote.

    Accepts the same item format as /from-rooms but returns only the tier
    breakdown — no quote ID or persistence.
    """
    from app.services.quote_engine.tier_generator import generate_tiers
    from app.services.quote_engine.yardage_calculator import calculate_yardage

    items = body.get("items", [])
    location = body.get("location", "DC")
    lining = body.get("lining", "standard")

    if not items:
        raise HTTPException(400, "At least one item is required")

    # Ensure each item has yardage calculated
    for item in items:
        if "yardage" not in item:
            dims = item.get("dimensions", {})
            opts = {}
            if item.get("cushion_count"):
                opts["cushion_count"] = item["cushion_count"]
            yardage = calculate_yardage(item.get("type", "accent_chair"), dims, opts)
            item["yardage"] = yardage

    tiers = generate_tiers(items, location=location, lining_preference=lining)
    return {"tiers": tiers}


@router.get("/pricing-tables")
async def get_pricing_tables():
    """Get all pricing tables for the founder pricing editor."""
    from app.services.quote_engine.pricing_tables import get_all_tables

    return get_all_tables()


@router.put("/pricing-tables/{table_name}")
async def update_pricing_table(table_name: str, body: dict):
    """Update a pricing table entry."""
    from app.services.quote_engine.pricing_tables import update_table

    key = body.get("key")
    value = body.get("value")
    if not key:
        raise HTTPException(400, "key required")
    success = update_table(table_name, key, value)
    if not success:
        raise HTTPException(404, f"Table {table_name} or key {key} not found")
    return {"status": "updated", "table": table_name, "key": key}


@router.post("/recalculate/{quote_id}")
async def recalculate_quote_endpoint(quote_id: str):
    """Recalculate an existing quote with current pricing tables."""
    from app.services.quote_engine.quote_assembler import recalculate_quote as recalc

    result = recalc(quote_id)
    if not result:
        raise HTTPException(404, "Quote not found")
    return result


# ── Quote Verification endpoints ──────────────────────────────

@router.post("/verify/{quote_id}")
async def verify_quote_endpoint(quote_id: str):
    """Run verification checks on a quote. Returns score, errors, warnings."""
    from app.services.quote_engine.verification import verify_quote, save_verification

    quote = _load_quote(quote_id)
    result = verify_quote(quote)
    save_verification(quote_id, result)
    return result


@router.get("/verify/{quote_id}")
async def get_verification(quote_id: str):
    """Get the last verification result for a quote."""
    from app.services.quote_engine.verification import load_verification

    result = load_verification(quote_id)
    if not result:
        raise HTTPException(404, "No verification found. Run POST /verify/{id} first.")
    return result


@router.get("/market-ranges")
async def get_market_ranges():
    """Get market price ranges per item type (for reference)."""
    from app.services.quote_engine.verification import MARKET_RANGES

    return {"market_ranges": MARKET_RANGES}


# ── v6.0 Quick Quote & Phase Pipeline ────────────────────────

class QuickQuoteRequest(BaseModel):
    item_type: str = "accent_chair"
    width: float = 0
    height: float = 0
    depth: float = 0
    material_grade: str = "B"
    complexity: str = "moderate"    # simple, moderate, complex, luxury
    quantity: int = 1
    notes: str = ""

class PromoteQuickQuoteRequest(BaseModel):
    customer_name: str
    quick_quote_data: dict

class PhaseApprovalRequest(BaseModel):
    notes: str = ""

class PhaseRejectionRequest(BaseModel):
    reason: str = ""

class PhaseItemEditRequest(BaseModel):
    """Edit an item's measurements/details within the phase pipeline."""
    item_index: int = 0
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    quantity: Optional[int] = None
    item_type: Optional[str] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    construction: Optional[str] = None
    condition: Optional[str] = None
    special_features: Optional[List[str]] = None


@router.post("/quick")
async def quick_quote_endpoint(payload: QuickQuoteRequest):
    """Track 1 — Instant ballpark quote from dimensions + material + complexity.
    Founder-only. Returns price ranges for 3 tiers."""
    from app.services.quote_engine.quote_phases import quick_quote

    result = quick_quote(
        item_type=payload.item_type,
        width=payload.width,
        height=payload.height,
        depth=payload.depth,
        material_grade=payload.material_grade,
        complexity=payload.complexity,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    return result


@router.post("/quick/promote")
async def promote_quick_quote(payload: PromoteQuickQuoteRequest):
    """Promote a quick quote to a full phase-pipeline quote."""
    from app.services.quote_engine.quote_phases import promote_quick_to_full

    quote = promote_quick_to_full(payload.quick_quote_data, payload.customer_name)
    return {"status": "promoted", "quote": quote}


@router.post("/phase/init/{quote_id}")
async def init_phase_pipeline_endpoint(quote_id: str):
    """Initialize the multi-phase pipeline on an existing quote."""
    from app.services.quote_engine.quote_phases import init_phase_pipeline

    try:
        quote = init_phase_pipeline(quote_id)
        return {"status": "initialized", "quote": quote}
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")


@router.post("/phase/advance/{quote_id}")
async def advance_phase_endpoint(quote_id: str):
    """Advance to the next phase. Auto-populates phase data for founder review."""
    from app.services.quote_engine.quote_phases import advance_phase

    try:
        quote = advance_phase(quote_id)
        return {"status": "advanced", "quote": quote}
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/phase/approve/{quote_id}")
async def approve_phase_endpoint(quote_id: str, payload: PhaseApprovalRequest = PhaseApprovalRequest()):
    """Founder approves the current phase."""
    from app.services.quote_engine.quote_phases import approve_phase

    try:
        quote = approve_phase(quote_id, founder_notes=payload.notes)
        return {"status": "approved", "quote": quote}
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/phase/reject/{quote_id}")
async def reject_phase_endpoint(quote_id: str, payload: PhaseRejectionRequest = PhaseRejectionRequest()):
    """Founder rejects the current phase — stays for revision."""
    from app.services.quote_engine.quote_phases import reject_phase

    try:
        quote = reject_phase(quote_id, reason=payload.reason)
        return {"status": "rejected", "quote": quote}
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/phase/retry/{quote_id}")
async def retry_phase_endpoint(quote_id: str):
    """Re-run current phase after revision."""
    from app.services.quote_engine.quote_phases import retry_phase

    try:
        quote = retry_phase(quote_id)
        return {"status": "retried", "quote": quote}
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/phase/item/{quote_id}")
async def edit_phase_item(quote_id: str, payload: PhaseItemEditRequest):
    """Edit an item's measurements/details within the phase pipeline.

    Allows the founder to correct AI-detected dimensions, change item type,
    update quantities, or add notes during the review phase.
    Automatically recalculates yardage and pricing after edits.
    """
    from app.services.quote_engine.quote_phases import edit_item_in_pipeline

    try:
        updates = payload.model_dump(exclude_unset=True)
        item_index = updates.pop("item_index", 0)
        quote = edit_item_in_pipeline(quote_id, item_index, updates)
        return {"status": "updated", "quote": quote}
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")
    except (ValueError, IndexError) as e:
        raise HTTPException(400, str(e))


@router.get("/phase/status/{quote_id}")
async def get_phase_status_endpoint(quote_id: str):
    """Get phase pipeline status for a quote."""
    from app.services.quote_engine.quote_phases import get_phase_status

    try:
        return get_phase_status(quote_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")


@router.get("/{quote_id}/intake-photos")
async def get_quote_intake_photos(quote_id: str):
    """Return the photos array from a quote's JSON file, with proper URLs.
    If the quote has an intake_project_id, also look up that project's photos from intake.db.
    """
    quote = _load_quote(quote_id)
    photos = quote.get("photos", [])
    intake_project_id = quote.get("intake_project_id")

    # If the quote has an intake_project_id, also look up photos from intake.db
    if intake_project_id:
        try:
            import sqlite3
            db_path = os.path.expanduser("~/empire-repo/backend/data/intake.db")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT photos FROM intake_projects WHERE id = ?",
                (intake_project_id,),
            ).fetchone()
            conn.close()

            if row:
                import json as _json
                db_photos_raw = _json.loads(row["photos"] or "[]")
                # Build a set of filenames already in the quote photos
                existing = {p.get("filename") for p in photos}
                for p in db_photos_raw:
                    fname = p.get("filename", "")
                    if fname and fname not in existing:
                        photos.append({
                            "filename": fname,
                            "url": f"/intake_uploads/{intake_project_id}/{fname}",
                            "original_name": p.get("original_name", fname),
                            "uploaded_at": p.get("uploaded_at", ""),
                        })
        except Exception as e:
            logger.warning(f"Could not load intake photos for project {intake_project_id}: {e}")

    return {"quote_id": quote_id, "intake_project_id": intake_project_id, "photos": photos, "count": len(photos)}


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
    # Also remove associated verification file if it exists
    ver_path = os.path.join(QUOTES_DIR, f"{quote_id}_verification.json")
    if os.path.exists(ver_path):
        os.remove(ver_path)
    return {"status": "deleted", "id": quote_id}


class SendQuoteRequest(BaseModel):
    to_email: Optional[str] = None  # Override recipient; defaults to customer_email


@router.post("/{quote_id}/send")
async def send_quote(quote_id: str, body: Optional[SendQuoteRequest] = None):
    """Generate PDF, email it to client, and mark quote as sent.

    If no to_email is provided, uses the customer_email from the quote.
    If no email address is available, marks as sent without emailing.
    """
    quote = _load_quote(quote_id)

    # Quality gate: final check before marking as sent
    qr = quality_engine.validate(
        json.dumps(quote, default=str),
        channel=Channel.QUOTE,
        context={"quote_data": quote},
    )
    if qr.blocked:
        raise HTTPException(422, detail={
            "message": "Quote blocked by quality engine — cannot send",
            "issues": [{"check": i.check, "severity": i.severity.value, "message": i.message} for i in qr.issues],
        })

    # Determine recipient
    to_email = (body.to_email if body and body.to_email else None) or quote.get("customer_email", "")

    # Generate PDF
    pdf_bytes = None
    try:
        from weasyprint import HTML as WeasyHTML
        pdf_response = await generate_pdf(quote_id, skip_verification=True)
        if hasattr(pdf_response, 'body'):
            pdf_bytes = pdf_response.body
        else:
            # Read from saved file
            pdf_path = os.path.join(
                os.path.expanduser("~/empire-repo/backend/data/quotes/pdf"),
                f"{quote['quote_number']}.pdf"
            )
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
    except Exception as e:
        logger.warning(f"PDF generation failed during send: {e}")

    # Email the quote with PDF attachment
    email_sent = False
    if to_email:
        try:
            from app.services.email.sender import send_email, SENDGRID_API_KEY, SENDGRID_FROM_EMAIL
            from app.services.email.templates import render_quote_sent

            # Build line items for email
            line_items = []
            for item in quote.get("line_items", []):
                line_items.append({
                    "description": item.get("description", ""),
                    "qty": item.get("quantity", 1),
                    "unit_price": item.get("rate", 0),
                    "total": item.get("amount", 0),
                })
            # If no line items but rooms exist, build from rooms
            if not line_items:
                for room in (quote.get("rooms") or []):
                    for w in room.get("windows", []):
                        line_items.append({
                            "description": f"{room.get('name', 'Room')} - {w.get('name', 'Window')}",
                            "qty": 1,
                            "unit_price": w.get("total", w.get("price", 0)),
                            "total": w.get("total", w.get("price", 0)),
                        })

            html_body = render_quote_sent({
                "customer_name": quote.get("customer_name", "Valued Customer"),
                "quote_number": quote.get("quote_number", ""),
                "project_description": quote.get("project_description", quote.get("project_name", "")),
                "line_items": line_items,
                "total": quote.get("total", 0),
                "quote_url": f"https://studio.empirebox.store/quote/{quote_id}",
            })

            subject = f"Your Quote #{quote['quote_number']} from Empire Workroom"

            # Send with PDF attachment if available
            if pdf_bytes and SENDGRID_API_KEY:
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

                message = Mail(
                    from_email=SENDGRID_FROM_EMAIL,
                    to_emails=to_email,
                    subject=subject,
                    html_content=html_body,
                )
                attachment = Attachment(
                    FileContent(base64.b64encode(pdf_bytes).decode()),
                    FileName(f"{quote['quote_number']}.pdf"),
                    FileType("application/pdf"),
                    Disposition("attachment"),
                )
                message.attachment = attachment
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                response = sg.send(message)
                email_sent = response.status_code < 300
            else:
                # Fallback: send without attachment
                email_sent = await send_email(to_email, subject, html_body)
        except Exception as e:
            logger.error(f"Email send failed for quote {quote_id}: {e}")

    # Mark as sent
    quote["status"] = "sent"
    quote["sent_at"] = datetime.utcnow().isoformat()
    quote["updated_at"] = datetime.utcnow().isoformat()
    _save_quote(quote)

    return {
        "status": "sent",
        "email_sent": email_sent,
        "to_email": to_email or "(no email address)",
        "pdf_generated": pdf_bytes is not None,
        "quote": quote,
    }


@router.post("/{quote_id}/accept")
async def accept_quote(quote_id: str):
    """Mark quote as accepted."""
    quote = _load_quote(quote_id)
    quote["status"] = "accepted"
    quote["accepted_at"] = datetime.utcnow().isoformat()
    quote["updated_at"] = datetime.utcnow().isoformat()
    _save_quote(quote)
    return {"status": "accepted", "quote": quote}


class PhotoAttach(BaseModel):
    filename: str
    room_index: Optional[int] = None
    item_type: Optional[str] = None   # "window" or "upholstery"
    item_index: Optional[int] = None
    photo_type: str = "site"          # "original", "site", "detail", "reference"


@router.post("/{quote_id}/photos")
async def attach_photos(quote_id: str, photos: list[PhotoAttach]):
    """Attach photos to specific rooms/windows/upholstery items in a quote."""
    quote = _load_quote(quote_id)
    uploads_dir = os.path.expanduser("~/empire-repo/backend/data/uploads/images")

    if "photos" not in quote or not isinstance(quote.get("photos"), list):
        quote["photos"] = []

    rooms = quote.get("rooms") or []
    attached = []

    for photo in photos:
        img_path = os.path.join(uploads_dir, photo.filename)
        if not os.path.exists(img_path):
            continue

        # Build base64 data URI
        data_uri = ""
        try:
            with open(img_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            ext = photo.filename.rsplit(".", 1)[-1].lower()
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
            data_uri = f"data:{mime};base64,{img_data}"
        except Exception:
            pass

        photo_entry = {
            "filename": photo.filename,
            "path": img_path,
            "type": photo.photo_type,
            "data_uri": data_uri,
            "room_index": photo.room_index,
            "item_type": photo.item_type,
            "item_index": photo.item_index,
        }
        quote["photos"].append(photo_entry)

        # Also embed directly into the room/window/upholstery item
        if photo.room_index is not None and photo.room_index < len(rooms):
            room = rooms[photo.room_index]
            if photo.item_type == "window" and photo.item_index is not None:
                windows = room.get("windows", [])
                if photo.item_index < len(windows):
                    windows[photo.item_index]["sourcePhoto"] = data_uri or img_path
            elif photo.item_type == "upholstery" and photo.item_index is not None:
                upholstery = room.get("upholstery", [])
                if photo.item_index < len(upholstery):
                    upholstery[photo.item_index]["sourcePhoto"] = data_uri or img_path

        attached.append(photo.filename)

    quote["updated_at"] = datetime.utcnow().isoformat()
    _save_quote(quote)
    return {"status": "attached", "count": len(attached), "filenames": attached}


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
    has_welting = ai.get("hasWelting", False) or ai.get("has_welting", False) or "welting" in notes.lower() or "piping" in notes.lower()
    has_tufting = ai.get("hasTufting", False) or ai.get("has_tufting", False) or "tuft" in notes.lower()
    has_flange = "flange" in notes.lower() or "flange" in name.lower()
    has_skirt = ai.get("has_skirt", False) or "skirt" in notes.lower()
    has_channeling = ai.get("has_channeling", False) or "channel" in notes.lower()
    has_nailhead = ai.get("has_nailhead", False) or "nailhead" in notes.lower()

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
        if has_channeling:
            # Vertical channel lines on back
            ch_count = 5
            ch_spacing = (bw - 24) / ch_count
            for ci in range(1, ch_count):
                cx_ch = bx + 12 + ci * ch_spacing
                svg_body += f'<line x1="{cx_ch}" y1="{by-14}" x2="{cx_ch}" y2="{by}" stroke="{fill_accent}" stroke-width="0.8" opacity="0.7"/>'
        if has_nailhead:
            # Nailhead dots along arm tops
            for nx in range(bx - 8, bx + 2, 4):
                svg_body += f'<circle cx="{nx}" cy="{by+6}" r="1.2" fill="#D4AF37" opacity="0.8"/>'
            for nx in range(bx + bw, bx + bw + 10, 4):
                svg_body += f'<circle cx="{nx}" cy="{by+6}" r="1.2" fill="#D4AF37" opacity="0.8"/>'
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
        if not has_channeling:
            options.append(("+ Channel Back", f"+$75–120"))
        if not has_nailhead:
            options.append(("+ Nailhead Trim", f"+$100–200"))
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
        suggested = ai.get("suggestedLaborType", "") or ai.get("suggested_labor_type", "")
        questions = ai.get("questions") or []
        if style or questions:
            svg += f'<div style="margin-top:4px;padding:6px 8px;background:#fffcf0;border:1px solid rgba(212,175,55,0.2);border-radius:5px;font-size:0.7em;max-width:{svg_w}px">'
            svg += f'<span style="color:#D4AF37;font-weight:700">AI Notes</span>'
            if style:
                svg += f' <span style="color:#666">· {style}</span>'
            if suggested:
                svg += f'<br><span style="color:#555">→ Suggested: {suggested} labor</span>'
            if ai.get("newFoamRecommended") or ai.get("new_foam_recommended"):
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


def _build_rooms_html(rooms: list, has_design_proposals: bool = False) -> str:
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

        html += f'<h3 style="color:#b8960c;margin:16px 0 6px;border-bottom:2px solid #b8960c;padding-bottom:3px">{room.get("name", "Room")}</h3>'

        # Regular (non-proposal) windows — standard table
        if regular_windows:
            price_label = "Est. Price" if not has_design_proposals else "Est. (Designer)"
            html += f"""<table style="margin-bottom:12px"><thead><tr>
                <th>Window</th><th>Size</th><th>Treatment</th><th>Lining</th>
                <th>Hardware</th><th>Motor</th><th>Mount</th><th>Qty</th><th style="text-align:right">{price_label}</th>
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
                # Per-item photo inline — skip if design_proposals exist (shown in proposals section as "Current — Before")
                src_photo = w.get("sourcePhoto", "")
                if src_photo and not proposal_windows and not has_design_proposals:
                    html += f"""<div style="margin-bottom:10px;text-align:center;page-break-inside:avoid">
                      <p style="font-size:0.75em;color:#666;margin-bottom:4px;font-weight:600">Site Photo — {w.get('name', 'Window')}</p>
                      <img src="{src_photo}" style="max-width:100%;max-height:250px;border-radius:8px;border:1px solid #ddd;object-fit:contain" />
                    </div>"""
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
                # Per-item photo inline with the upholstery drawing
                src_photo = u.get("sourcePhoto", "")
                if src_photo:
                    html += f"""<div style="margin-bottom:10px;text-align:center;page-break-inside:avoid">
                      <p style="font-size:0.75em;color:#666;margin-bottom:4px;font-weight:600">Reference Photo — {u.get('name', 'Piece')}</p>
                      <img src="{src_photo}" style="max-width:100%;max-height:250px;border-radius:8px;border:1px solid #ddd;object-fit:contain" />
                    </div>"""
                html += _build_upholstery_drawing(u)
            html += '</div>'

        # Items table (new Quote Builder format — items[] instead of windows[]/upholstery[])
        items = room.get("items", [])
        if items and not regular_windows and not upholstery:
            # Check if items have rate/unit (detailed pricing) or just basic info
            has_pricing = any(it.get("rate") or it.get("unit") for it in items)
            if has_pricing:
                html += """<table style="margin-bottom:12px"><thead><tr>
                    <th>Description</th><th style="text-align:center">Qty</th><th style="text-align:center">Unit</th>
                    <th style="text-align:right">Rate</th><th style="text-align:right">Amount</th>
                </tr></thead><tbody>"""
                room_subtotal = 0
                for it in items:
                    desc = it.get("notes", "") or it.get("type", "item").replace("_", " ").title()
                    qty = it.get("quantity", 1)
                    unit = it.get("unit", "ea")
                    rate = it.get("rate", 0)
                    amount = qty * rate
                    room_subtotal += amount
                    html += f"""<tr>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:0.88em">{desc}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{qty}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{unit}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">${rate:,.2f}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:600">${amount:,.2f}</td>
                    </tr>"""
                html += f"""<tr><td colspan="4" style="padding:8px;text-align:right;font-weight:600;color:#333">
                    Area Subtotal</td><td style="padding:8px;text-align:right;font-weight:700;color:#b8960c">
                    ${room_subtotal:,.2f}</td></tr>"""
                html += "</tbody></table>"
            else:
                html += """<table style="margin-bottom:12px"><thead><tr>
                    <th>Item</th><th>Size</th><th>Fabric</th><th>Yardage</th><th>Qty</th>
                </tr></thead><tbody>"""
                for it in items:
                    dims = it.get("dimensions", {})
                    size_parts = [f'{dims.get("width", "")}' if dims.get("width") else '',
                                  f'{dims.get("height", "")}' if dims.get("height") else '',
                                  f'{dims.get("depth", "")}' if dims.get("depth") else '']
                    size_str = ' x '.join(p for p in size_parts if p)
                    if size_str:
                        size_str += '"'

                    fabric_name = it.get("fabric_name", "")
                    backing_name = it.get("backing_fabric_name", "")
                    fabric_display = fabric_name
                    if backing_name:
                        fabric_display += f"<br><span style='font-size:0.8em;color:#666'>Backing: {backing_name}</span>"

                    yards = it.get("fabric_yards_needed", 0)
                    backing_yards = it.get("backing_yards_needed", 0)
                    yard_display = f"{yards} yd" if yards else ""
                    if backing_yards:
                        yard_display += f"<br><span style='font-size:0.8em;color:#666'>+ {backing_yards} yd backing</span>"

                    item_label = it.get("type", "item").replace("_", " ").title()
                    html += f"""<tr>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee">{item_label}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{size_str}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee">{fabric_display or '—'}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{yard_display or '—'}</td>
                        <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{it.get('quantity', 1)}</td>
                    </tr>"""
                html += "</tbody></table>"

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


def _build_design_proposals_html(proposals: list, original_photo: str = "") -> str:
    """Build 3-tier design option cards for the PDF with side-by-side mockup images."""
    if not proposals:
        return ""

    tier_styles = [
        {"color": "#22c55e", "bg": "#f0fdf4", "border": "#bbf7d0", "badge": "OPTION A", "label": "Essential"},
        {"color": "#D4AF37", "bg": "#fffcf0", "border": "#fde68a", "badge": "OPTION B", "label": "Designer"},
        {"color": "#8B5CF6", "bg": "#f5f3ff", "border": "#c4b5fd", "badge": "OPTION C", "label": "Premium"},
    ]

    html = """<div style="margin:24px 0">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;border-bottom:2px solid #D4AF37;padding-bottom:8px">
      <div style="width:24px;height:24px;border-radius:6px;background:linear-gradient(135deg,#D4AF37,#8B5CF6);display:flex;align-items:center;justify-content:center;color:white;font-weight:900;font-size:11px">M</div>
      <div>
        <strong style="color:#1a1a2e;font-size:1.05em">Design Options</strong>
        <span style="font-size:0.75em;color:#888;margin-left:8px">AI-curated proposals tailored to your project</span>
      </div>
    </div>"""

    # Original photo — "Current / Before" reference
    if original_photo:
        html += f"""<div style="margin-bottom:18px;page-break-inside:avoid;text-align:center">
          <p style="font-size:0.8em;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">Your Space — Current</p>
          <img src="{original_photo}" style="max-width:80%;max-height:260px;border-radius:8px;border:2px solid #ddd;object-fit:contain;display:inline-block" />
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
        # Mockup URLs — inpainted (customer photo) + clean (aspirational)
        inpainted_url = prop.get("inpainted_image_url") or prop.get("mockup_image", "")
        clean_url = prop.get("clean_mockup_url", "")
        provider = prop.get("mockup_provider", "")

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

        html += f"""<div style="margin-bottom:16px;border:2px solid {s['border']};border-radius:10px;overflow:hidden;background:white;page-break-inside:avoid">
          <!-- Proposal header -->
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 14px;background:{s['bg']}">
            <div style="display:flex;align-items:center;gap:10px">
              <span style="background:{s['color']};color:white;padding:3px 10px;border-radius:5px;font-size:0.7em;font-weight:700;letter-spacing:0.5px">{s['badge']}</span>
              <div>
                <strong style="color:#1a1a2e;font-size:0.92em">{label.split('—')[-1].strip() if '—' in label else label}</strong>
                <p style="margin:1px 0 0;font-size:0.72em;color:#888">{grade_label} · {lining} Lining</p>
              </div>
            </div>
            <div style="text-align:right">
              <strong style="font-size:1.15em;color:{s['color']}">${total:,.2f}</strong>
              <p style="margin:1px 0 0;font-size:0.68em;color:#888">incl. tax</p>
            </div>
          </div>"""

        # Side-by-side mockup images: inpainted (Your Room) + clean (Inspiration)
        has_inpainted = bool(inpainted_url)
        has_clean = bool(clean_url)
        if has_inpainted or has_clean:
            html += f'<div style="display:flex;gap:8px;padding:10px 14px;background:#fafafa;border-bottom:1px solid #f0f0f0">'
            if has_inpainted and has_clean:
                # Both images — 50/50 side by side
                html += f"""<div style="flex:1;text-align:center">
                  <p style="font-size:0.68em;font-weight:700;color:{s['color']};text-transform:uppercase;letter-spacing:0.8px;margin:0 0 6px">Your Room</p>
                  <img src="{inpainted_url}" style="max-width:100%;max-height:200px;border-radius:6px;border:1px solid #eee;object-fit:contain" />
                </div>
                <div style="flex:1;text-align:center">
                  <p style="font-size:0.68em;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 6px">Inspiration</p>
                  <img src="{clean_url}" style="max-width:100%;max-height:200px;border-radius:6px;border:1px solid #eee;object-fit:contain" />
                </div>"""
            elif has_inpainted:
                html += f"""<div style="flex:1;text-align:center">
                  <p style="font-size:0.68em;font-weight:700;color:{s['color']};text-transform:uppercase;letter-spacing:0.8px;margin:0 0 6px">Your Room — {s['label']}</p>
                  <img src="{inpainted_url}" style="max-width:100%;max-height:220px;border-radius:6px;border:1px solid #eee;object-fit:contain" />
                </div>"""
            else:
                html += f"""<div style="flex:1;text-align:center">
                  <p style="font-size:0.68em;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 6px">Inspiration — {s['label']}</p>
                  <img src="{clean_url}" style="max-width:100%;max-height:220px;border-radius:6px;border:1px solid #eee;object-fit:contain" />
                </div>"""
            html += '</div>'

        # AI commentary
        if comment:
            html += f"""<div style="padding:8px 14px;border-bottom:1px solid #f0f0f0;background:#fafbfd">
              <p style="margin:0;font-size:0.8em;color:#444;line-height:1.4;font-style:italic">{comment}</p>
            </div>"""

        # Line items table
        if items_rows:
            html += f"""<div style="padding:6px 14px 8px">
              <table style="width:100%;border-collapse:collapse;margin:0">
                <thead><tr>
                  <th style="padding:3px 6px;font-size:0.68em;text-transform:uppercase;letter-spacing:0.5px;color:#999;text-align:left;border-bottom:1px solid #eee;background:transparent">Item</th>
                  <th style="padding:3px 6px;font-size:0.68em;text-transform:uppercase;letter-spacing:0.5px;color:#999;text-align:right;border-bottom:1px solid #eee;background:transparent">Price</th>
                </tr></thead>
                <tbody>{items_rows}</tbody>
                <tfoot>
                  <tr><td style="padding:3px 6px;font-size:0.76em;color:#666;text-align:right">Subtotal</td>
                    <td style="padding:3px 6px;font-size:0.76em;color:#666;text-align:right">${subtotal:,.2f}</td></tr>
                  <tr><td style="padding:3px 6px;font-size:0.76em;color:#666;text-align:right">Tax</td>
                    <td style="padding:3px 6px;font-size:0.76em;color:#666;text-align:right">${tax:,.2f}</td></tr>
                  <tr><td style="padding:3px 6px;font-size:0.85em;font-weight:700;color:#1a1a2e;text-align:right;border-top:2px solid {s['color']}">Total</td>
                    <td style="padding:3px 6px;font-size:0.85em;font-weight:700;color:{s['color']};text-align:right;border-top:2px solid {s['color']}">${total:,.2f}</td></tr>
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
    # Handle local API paths — read directly from disk
    if url.startswith("/api/v1/vision/images/"):
        fname = url.split("/")[-1]
        local_path = os.path.expanduser(f"~/empire-repo/backend/data/generated/{fname}")
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{b64}"
            except Exception as e:
                logger.warning(f"Failed to read local image {fname}: {e}")
        # Fallback to localhost fetch
        url = f"http://localhost:8000{url}"
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

    # Design proposal mockup images (legacy + new inpainted/clean)
    for dp in (quote.get("design_proposals") or []):
        for key in ("mockup_image", "inpainted_image_url", "clean_mockup_url", "furniture_inpainted_url", "furniture_clean_url"):
            if dp.get(key) and not dp[key].startswith("data:"):
                dp[key] = _download_image_as_data_uri(dp[key])

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
        r = item.get("room") or item.get("area") or "General"
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


def _discount_html(quote: dict) -> str:
    """Build discount row HTML showing percentage and dollar amount."""
    amt = quote.get("discount_amount", 0)
    dtype = quote.get("discount_type", "dollar")
    subtotal = quote.get("subtotal", 0)
    if dtype == "percent" and amt > 0:
        dollar = round(subtotal * (amt / 100), 2)
        label = f"Discount ({amt:g}%)"
    else:
        dollar = amt
        pct = round(amt / subtotal * 100, 1) if subtotal > 0 and amt > 0 else 0
        label = f"Discount ({pct:g}%)" if pct > 0 else "Discount"
    return (
        f"<tr><td colspan='8' style='padding:8px;text-align:right;color:#c00'>{label}</td>"
        f"<td style='padding:8px;text-align:right;color:#c00'>-${dollar:,.2f}</td></tr>"
    )


@router.post("/{quote_id}/pdf")
async def generate_pdf(quote_id: str, skip_verification: bool = False):
    """Generate PDF for a quote with room-level detail, drawings, and mockups.

    Gate 2: Runs verification before PDF generation.
    If errors exist, blocks PDF unless skip_verification=True.
    """
    quote = _load_quote(quote_id)

    # ── GATE 2: Pre-PDF verification ──
    if not skip_verification:
        from app.services.quote_engine.verification import verify_quote, save_verification

        verification = verify_quote(quote)
        save_verification(quote_id, verification)

        if not verification["passed"]:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Quote failed verification — fix errors before generating PDF",
                    "score": verification["score"],
                    "grade": verification["grade"],
                    "errors": verification["errors"],
                    "warnings": verification["warnings"],
                    "summary": verification["summary"],
                    "hint": "Fix errors and re-verify, or pass ?skip_verification=true to override",
                },
            )

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

    design_proposals = quote.get("design_proposals") or []

    # Build room-level content or fallback to flat line items
    if rooms:
        body_html = _build_rooms_html(rooms, has_design_proposals=bool(design_proposals))
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
    # If a proposal was selected, only show that one in the PDF
    selected_idx = quote.get("selected_proposal")
    proposal_selected = selected_idx is not None and 0 <= selected_idx < len(design_proposals)
    if proposal_selected:
        design_proposals = [design_proposals[selected_idx]]
    # Find original customer photo for "before" reference
    original_photo = ""
    photos = quote.get("photos") or []
    for p in photos:
        if p.get("type") == "original":
            if p.get("data_uri"):
                original_photo = p["data_uri"]
            elif p.get("path") and os.path.exists(p["path"]):
                try:
                    with open(p["path"], "rb") as _pf:
                        _pdata = base64.b64encode(_pf.read()).decode()
                    ext = p.get("filename", "jpg").rsplit(".", 1)[-1].lower()
                    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                    original_photo = f"data:{mime};base64,{_pdata}"
                except Exception:
                    pass
            break
    proposals_html = _build_design_proposals_html(design_proposals, original_photo)

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
        <td style="padding:8px;text-align:right"><strong>${deposit['deposit_amount']:,.2f}</strong></td></tr>"""

    install_date = ""
    if quote.get("install_date"):
        install_date = f"<p><strong>Estimated Install Date:</strong> {quote['install_date']}</p>"

    # Load business config for contact info on PDF
    import json as _json
    _biz_cfg_path = Path(__file__).resolve().parent.parent / "config" / "business.json"
    _biz_cfg = {}
    try:
        _biz_cfg = _json.loads(_biz_cfg_path.read_text())
    except Exception:
        pass

    logo_html = ""
    biz_name = quote.get("business_name") or _biz_cfg.get("business_name", "Empire Workroom")
    biz_phone = _biz_cfg.get("business_phone", "")
    biz_email = _biz_cfg.get("business_email", "")
    biz_address = _biz_cfg.get("business_address", "")
    biz_website = _biz_cfg.get("business_website", "")
    if quote.get("business_logo_url"):
        logo_html = f'<img src="{quote["business_logo_url"]}" style="max-height:60px;margin-bottom:8px" /><br>'

    biz_contact_lines = [l for l in [biz_phone, biz_email, biz_address, biz_website] if l]
    biz_contact_html = "<br>".join(f'<span style="font-size:0.82em;color:#555">{l}</span>' for l in biz_contact_lines)

    created_date = quote['created_at'][:10]
    expires_date = quote.get('expires_at', '')[:10] if quote.get('expires_at') else ''
    quote_number = quote['quote_number']

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{quote_number}</title>
<style>
  @page {{ size: letter; margin: 0.5in 0.6in; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; max-width: 800px; margin: 0 auto; padding: 0; font-size: 12px; line-height: 1.45; background: #f5f3ef; }}
  h1 {{ color: #1a1a2e; margin: 0; font-size: 28px; letter-spacing: -0.5px; }}
  h3 {{ page-break-after: avoid; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  th {{ background: #2c2416; color: #b8960c; padding: 8px 6px; text-align: left; font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ font-size: 0.85em; }}
</style></head><body>

<!-- ═══ HEADER / LETTERHEAD ═══ -->
<div style="border-bottom:3px solid #b8960c;padding-bottom:14px;margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      {logo_html}
      <h1>{biz_name}</h1>
      <p style="margin:4px 0 0;color:#888;font-size:0.85em">Custom Window Treatments &amp; Upholstery</p>
      <p style="margin:6px 0 0;line-height:1.6">{biz_contact_html}</p>
    </div>
    <div style="text-align:right;padding-top:4px">
      <div style="background:#2c2416;color:#b8960c;padding:8px 16px;border-radius:6px;font-weight:700;font-size:1.1em;letter-spacing:1px;display:inline-block;margin-bottom:8px">ESTIMATE</div>
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
{_build_line_items_html(quote.get("line_items", [])) if (not design_proposals or proposal_selected) and not any(it.get("rate") or it.get("unit") for r in rooms for it in r.get("items", [])) else ""}

<!-- ═══ TOTALS ═══ -->
{f'''<table style="margin-top:16px"><tbody>
  <tr><td colspan="8" style="padding:10px 8px;text-align:right;color:#666;font-style:italic">
    Treatment options range from</td>
  <td style="padding:10px 8px;text-align:right;font-weight:700;color:#b8960c;font-size:1.15em;white-space:nowrap">
    ${min(p["total"] for p in design_proposals):,.0f} &ndash; ${max(p["total"] for p in design_proposals):,.0f}</td></tr>
</tbody></table>''' if design_proposals and not proposal_selected else f'''<table style="margin-top:16px"><tbody>
  {f"<tr><td colspan='8' style='padding:10px 8px;text-align:right;color:#666;font-style:italic'>Treatment options range from</td><td style='padding:10px 8px;text-align:right;font-weight:700;color:#b8960c;font-size:1.1em;white-space:nowrap'>${quote['price_range_low']:,.0f} &ndash; ${quote['price_range_high']:,.0f}</td></tr>" if quote.get("price_range_low") else f"""
  <tr><td colspan='8' style='padding:8px;text-align:right;color:#666'>Subtotal</td>
  <td style='padding:8px;text-align:right;color:#666'>${quote.get("subtotal", 0):,.2f}</td></tr>
  {_discount_html(quote) if quote.get('discount_amount') else ""}
  <tr><td colspan='8' style='padding:8px;text-align:right;color:#666'>Tax ({quote.get('tax_rate', 0) * 100:.1f}%)</td>
  <td style='padding:8px;text-align:right;color:#666'>${quote.get('tax_amount', 0):,.2f}</td></tr>
  <tr><td colspan='8' style='padding:14px 8px;text-align:right;border-top:3px solid #b8960c'><strong style='font-size:1.15em;color:#1a1a2e'>Total</strong></td>
  <td style='padding:14px 8px;text-align:right;border-top:3px solid #b8960c'><strong style='font-size:1.2em;color:#b8960c'>${quote.get("total", 0):,.2f}</strong></td></tr>"""}
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
<div style="margin-top:36px;padding:24px 20px;border:2px solid #b8960c;border-radius:10px;page-break-inside:avoid">
  <p style="margin:0 0 12px;font-size:0.78em;text-transform:uppercase;letter-spacing:0.5px;color:#b8960c;font-weight:700">Acceptance</p>
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
    try:
        from weasyprint import HTML as WeasyHTML
        pdf_bytes = WeasyHTML(string=html).write_pdf()
    except Exception as e:
        logger.error(f"WeasyPrint PDF generation failed: {e}")
        raise HTTPException(500, f"PDF generation failed: {str(e)}")

    # Save PDF file
    pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{quote['quote_number']}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    logger.info(f"PDF generated: {quote['quote_number']} ({len(pdf_bytes)} bytes) -> {pdf_path}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{quote["quote_number"]}.pdf"'
        },
    )


@router.get("/{quote_id}/pdf")
async def download_pdf(quote_id: str):
    """Download a previously generated PDF. Auto-generates if not yet created."""
    quote = _load_quote(quote_id)
    pdf_path = os.path.join(
        os.path.expanduser("~/empire-repo/backend/data/quotes/pdf"),
        f"{quote['quote_number']}.pdf",
    )
    if not os.path.exists(pdf_path):
        # Auto-generate on first GET request (skip verification for convenience)
        return await generate_pdf(quote_id, skip_verification=True)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{quote["quote_number"]}.pdf"'
        },
    )


