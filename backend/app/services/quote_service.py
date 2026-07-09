"""
Quote Service — SQL-backed CRUD for quotes_v2 + quote_line_items.
Replaces JSON file storage with proper database operations.
All financial writes logged to financial_audit_log.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from app.db.database import get_db, dict_row, dict_rows
from app.data.product_catalog import PRICING_SPECS
from app.services.pricing.engine import price_workroom_line, PricingInputError
from app.services.max.access_control import FOUNDER_APPROVAL_PIN, verify_founder_approval

logger = logging.getLogger(__name__)


def _require_founder_pin(founder_pin, op_name: str) -> None:
    """Sprint 1c-fix: defense-in-depth PIN check at service layer for level-0 ops.

    The primary gate lives in access_control.verify_founder_approval (called
    from the MAX tool wrapper and router); this service-layer check is a
    second line of defense in case a future caller bypasses the wrapper.
    Raises InvalidFounderPin if PIN is missing or doesn't match.
    """
    # If FOUNDER_APPROVAL_PIN env is unset, fail closed.
    if not FOUNDER_APPROVAL_PIN:
        raise InvalidFounderPin(
            f"{op_name} requires FOUNDER_APPROVAL_PIN env var to be set"
        )
    if not founder_pin or str(founder_pin) != FOUNDER_APPROVAL_PIN:
        raise InvalidFounderPin(
            f"{op_name} requires valid founder_pin (missing or wrong)"
        )


# ── Helpers ────────────────────────────────────────────────────

def _audit_log(conn, entity_type: str, entity_id: str, action: str,
               field_name: str = None, old_value=None, new_value=None,
               changed_by: str = "system", reason: str = None):
    conn.execute("""
        INSERT INTO financial_audit_log
        (entity_type, entity_id, action, field_name, old_value, new_value, changed_by, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (entity_type, entity_id, action, field_name,
          str(old_value) if old_value is not None else None,
          str(new_value) if new_value is not None else None,
          changed_by, reason))


def _price_line_item(category, inputs, business_unit, legacy):
    """Build the pricing columns for a line item.

    Sprint 1b behavior:
      - If `category` is one of the 12 catalog categories, route through the
        pricing engine so proposed_price = final_price = engine output and
        the computed breakdown is persisted. PricingInputError raises out
        (caller maps to HTTP 400) — never silently fall back to qty × rate
        for catalog categories.
      - If `category` is NOT in PRICING_SPECS, fall back to manual pricing
        (qty × rate) so existing free-form line items keep working.

    Returns a dict ready to merge into the INSERT/UPDATE column list.
    """
    bu = business_unit or "workroom"
    inputs = inputs or {}
    if category and str(category).lower() in PRICING_SPECS:
        # Fail loud — never silently fall back to qty × rate for catalog items.
        # Empty inputs produce a bogus $0.00 from the engine, which is exactly
        # the "wrong price reaching a customer" risk we're guarding against.
        if not inputs or not any(
            v is not None and v != "" and v != 0
            for v in inputs.values()
        ):
            raise PricingInputError(
                f"catalog category '{category}' requires non-empty 'inputs'"
            )
        result = price_workroom_line(category, inputs, business_unit=bu)
        # Belt-and-suspenders: if the engine still produced 0 with non-empty
        # inputs (e.g. all-zero measurements), refuse to persist it.
        if result["proposed_price"] <= 0:
            raise PricingInputError(
                f"catalog category '{category}' produced proposed_price=0 "
                f"with inputs={inputs}"
            )
        proposed = result["proposed_price"]
        return {
            "subtotal":         proposed,
            "unit_price":       proposed,
            "proposed_price":   proposed,
            "final_price":      result["final_price"],
            "price_overridden": 0,
            "business_unit":    result["business_unit"],
            "computed_json":    json.dumps(result["computed"], default=str),
        }

    # Legacy manual path — only for non-catalog items
    qty  = float(legacy.get("quantity", 1) or 1)
    rate = float(legacy.get("unit_price", legacy.get("rate", 0)) or 0)
    subtotal = round(qty * rate, 2)
    return {
        "subtotal":         subtotal,
        "unit_price":       rate,
        "proposed_price":   subtotal,
        "final_price":      subtotal,
        "price_overridden": 0,
        "business_unit":    bu,
        "computed_json":    json.dumps({
            "note": "manual pricing (category not in PRICING_SPECS)",
            "qty":  qty,
            "rate": rate,
        }, default=str),
    }


# ── State machine (Sprint 1c approval gate) ─────────────────────────

VALID_TRANSITIONS = {
    'draft':          ['founder_review', 'cancelled'],
    'founder_review': ['sent', 'draft', 'cancelled'],
    'sent':           ['accepted', 'cancelled'],
    'accepted':       ['in_production', 'cancelled'],
    'in_production':  ['completed', 'cancelled'],
    'completed':      ['cancelled'],
    'cancelled':      ['draft'],
    # Legacy state from MAX's create_quick_quote (pre-1c). Read-only.
    # Surface in the review list as "legacy — pending migration" and
    # block all transitions until 1d migrates them.
    'proposal':       [],
}

# Once a quote is sent (or beyond), prices are immutable. The customer
# sees the snapshot we sent — editing it later would silently rewrite
# the customer's contract.
IMMUTABLE_STATUSES = {'sent', 'accepted', 'in_production', 'completed'}


class InvalidTransition(ValueError):
    """Raised when a quote status transition is not allowed."""


class ImmutableQuoteError(ValueError):
    """Raised when a mutation is attempted on a quote whose status is final."""


class InvalidFounderPin(PermissionError):
    """Sprint 1c-fix: raised when a level-0 tool/service call lacks a
    valid founder_pin. Defense-in-depth check at the service layer —
    the access controller (verify_founder_approval) is the primary gate."""


def _check_immutable(conn, quote_id: str, op: str) -> None:
    """Raise ImmutableQuoteError if quote is in a terminal-after-send state."""
    row = conn.execute("SELECT status FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
    if not row:
        raise InvalidTransition(f"quote {quote_id} not found")
    if row["status"] in IMMUTABLE_STATUSES:
        raise ImmutableQuoteError(
            f"quote {quote_id} is in status '{row['status']}' — "
            f"{op} is forbidden (prices are immutable after sent)"
        )


def _check_transition(conn, quote_id: str, target_status: str) -> str:
    """Raise InvalidTransition if the requested transition is illegal.
    Returns the prior status if the transition is allowed."""
    row = conn.execute("SELECT status FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
    if not row:
        raise InvalidTransition(f"quote {quote_id} not found")
    current = row["status"]
    allowed = VALID_TRANSITIONS.get(current, [])
    if target_status not in allowed:
        raise InvalidTransition(
            f"quote {quote_id} cannot transition '{current}' → '{target_status}' "
            f"(allowed: {allowed})"
        )
    return current


def _next_quote_number(conn) -> str:
    """Generate sequential quote number EST-YYYY-NNN."""
    year = datetime.now().year
    row = conn.execute(
        "SELECT quote_number FROM quotes_v2 WHERE quote_number LIKE ? ORDER BY quote_number DESC LIMIT 1",
        (f"EST-{year}-%",)
    ).fetchone()
    if row:
        try:
            last_seq = int(row[0].split('-')[-1])
        except (ValueError, IndexError):
            last_seq = 0
    else:
        last_seq = 0
    return f"EST-{year}-{last_seq + 1:03d}"


def _recalculate_totals(conn, quote_id: str, changed_by: str = "system"):
    """Recalculate quote totals from line items. Log changes to audit.

    Sprint 1b fix: sum final_price (honoring price_overridden=1 rows),
    fall back to subtotal only when final_price is NULL (defensive —
    legacy rows should already have been backfilled).
    """
    items = conn.execute(
        "SELECT subtotal, final_price, price_overridden "
        "FROM quote_line_items WHERE quote_id = ?",
        (quote_id,),
    ).fetchall()
    items_subtotal = round(
        sum(
            (r["final_price"] if r["final_price"] is not None else r["subtotal"]) or 0
            for r in items
        ),
        2,
    )

    q = conn.execute(
        "SELECT subtotal, tax_rate, discount_amount, discount_type, total, deposit_percent FROM quotes_v2 WHERE id = ?",
        (quote_id,)
    ).fetchone()
    if not q:
        return

    old_subtotal = q[0] or 0
    tax_rate = q[1] or 0
    discount_amount = q[2] or 0
    discount_type = q[3] or 'dollar'
    old_total = q[4] or 0
    deposit_percent = q[5] or 50

    # Use items_subtotal if we have items, else keep existing
    subtotal = items_subtotal if items else old_subtotal

    if discount_type == 'percent' and discount_amount > 0:
        discount = round(subtotal * (discount_amount / 100), 2)
    else:
        discount = discount_amount

    tax_amount = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax_amount - discount, 2)
    deposit_required = round(total * deposit_percent / 100, 2)
    balance_due = round(total - (conn.execute(
        "SELECT deposit_paid FROM quotes_v2 WHERE id = ?", (quote_id,)
    ).fetchone()[0] or 0), 2)

    if abs(old_total - total) > 0.01:
        _audit_log(conn, 'quote', quote_id, 'recalculate', 'total',
                   old_total, total, changed_by, 'Auto-recalculated from line items')

    conn.execute("""
        UPDATE quotes_v2 SET subtotal=?, tax_amount=?, total=?,
        deposit_required=?, balance_due=?, updated_at=? WHERE id=?
    """, (subtotal, tax_amount, total, deposit_required, balance_due,
          datetime.now().isoformat(), quote_id))


def _quote_to_dict(row) -> dict:
    """Convert a quotes_v2 row to API-friendly dict."""
    d = dict(row)
    # Parse JSON fields
    for jf in ['rooms_json', 'tiers_json', 'design_proposals_json', 'ai_mockups_json',
               'ai_outlines_json', 'photos_json', 'measurements_json', 'metadata_json']:
        key = jf.replace('_json', '')
        if d.get(jf):
            try:
                d[key] = json.loads(d[jf])
            except (json.JSONDecodeError, TypeError):
                d[key] = d[jf]
        else:
            d[key] = None
        del d[jf]
    return d


def _item_to_dict(row) -> dict:
    d = dict(row)
    for jf in ['photo_ids_json', 'pricing_snapshot_json']:
        key = jf.replace('_json', '')
        if d.get(jf):
            try:
                d[key] = json.loads(d[jf])
            except (json.JSONDecodeError, TypeError):
                d[key] = d[jf]
        else:
            d[key] = None
        del d[jf]
    # Frontend (QuoteReviewScreen) reads item.rate / item.amount; DB stores
    # unit_price / subtotal. Emit aliases so the review editor and verification
    # panel show real values (symmetric with the write side accepting both).
    if d.get("rate") is None:
        d["rate"] = d.get("unit_price")
    if d.get("amount") is None:
        d["amount"] = d.get("subtotal")
    return d


# ── CRUD ───────────────────────────────────────────────────────

def list_quotes(status: str = None, business_unit: str = None,
                search: str = None, limit: int = 50, offset: int = 0) -> dict:
    with get_db() as conn:
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        if business_unit:
            where.append("business_unit = ?")
            params.append(business_unit)
        if search:
            where.append("(customer_name LIKE ? OR project_name LIKE ? OR quote_number LIKE ? OR id LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s, s, s])

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        total = conn.execute(f"SELECT COUNT(*) FROM quotes_v2 {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM quotes_v2 {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

        quotes = [_quote_to_dict(r) for r in rows]
        # Attach item counts
        for q in quotes:
            cnt = conn.execute("SELECT COUNT(*) FROM quote_line_items WHERE quote_id = ?", (q['id'],)).fetchone()[0]
            q['item_count'] = cnt

        return {"quotes": quotes, "total": total, "limit": limit, "offset": offset}


def get_quote(quote_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not row:
            return None
        q = _quote_to_dict(row)
        items = conn.execute(
            "SELECT * FROM quote_line_items WHERE quote_id = ? ORDER BY line_number",
            (quote_id,)
        ).fetchall()
        q['line_items'] = [_item_to_dict(i) for i in items]
        photos = conn.execute(
            "SELECT * FROM quote_photos WHERE quote_id = ?", (quote_id,)
        ).fetchall()
        q['quote_photos'] = dict_rows(photos)
        return q


def create_quote(data: dict) -> dict:
    with get_db() as conn:
        import uuid
        quote_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        quote_number = _next_quote_number(conn)

        dep = data.get('deposit', {})
        deposit_percent = dep.get('deposit_percent', 50) if isinstance(dep, dict) else 50

        conn.execute("""
            INSERT INTO quotes_v2 (
                id, quote_number, customer_name, customer_email, customer_phone,
                customer_address, business_unit, project_name, project_description,
                status, tax_rate, discount_amount, discount_type, deposit_percent,
                valid_days, terms, notes, pricing_mode, location, lining_preference,
                rooms_json, ai_mockups_json, ai_outlines_json, measurements_json,
                expires_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            quote_id, quote_number,
            data.get('customer_name', ''),
            data.get('customer_email', ''),
            data.get('customer_phone', ''),
            data.get('customer_address', ''),
            data.get('business_unit', 'workroom'),
            data.get('project_name', ''),
            data.get('project_description', ''),
            'draft',
            data.get('tax_rate', 0.0),
            data.get('discount_amount', 0.0),
            data.get('discount_type', 'dollar'),
            deposit_percent,
            data.get('valid_days', 30),
            data.get('terms', ''),
            data.get('notes', ''),
            data.get('pricing_mode', ''),
            data.get('location', ''),
            data.get('lining_preference', ''),
            json.dumps(data.get('rooms', []), default=str) if data.get('rooms') else None,
            json.dumps(data.get('ai_mockups', []), default=str) if data.get('ai_mockups') else None,
            json.dumps(data.get('ai_outlines', []), default=str) if data.get('ai_outlines') else None,
            json.dumps(data.get('measurements', {}), default=str) if data.get('measurements') else None,
            (datetime.now() + timedelta(days=data.get('valid_days', 30))).isoformat(),
            now, now,
        ))

        # Insert line items — sprint 1b routes through _price_line_item
        # (catalog categories → engine; non-catalog → manual qty × rate)
        for idx, li in enumerate(data.get('line_items', data.get('items', []))):
            if not isinstance(li, dict):
                continue
            pricing = _price_line_item(
                category=li.get('category'),
                inputs=li.get('inputs') or li,  # engine reads from li itself if no separate inputs
                business_unit=data.get('business_unit'),
                legacy=li,
            )
            qty = float(li.get('quantity', pricing["unit_price"] and 1) or 1)
            conn.execute("""
                INSERT INTO quote_line_items (
                    quote_id, line_number, description, quantity, unit, unit_price, subtotal,
                    category, pricing_snapshot_json,
                    proposed_price, final_price, price_overridden, business_unit, computed_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quote_id, idx + 1,
                li.get('description', ''),
                qty,
                li.get('unit', 'ea'),
                pricing["unit_price"],
                pricing["subtotal"],
                li.get('category', 'labor'),
                json.dumps(li.get('pricing_snapshot_json') or li.get('pricing_snapshot'), default=str)
                if (li.get('pricing_snapshot_json') or li.get('pricing_snapshot')) else None,
                pricing["proposed_price"],
                pricing["final_price"],
                pricing["price_overridden"],
                pricing["business_unit"],
                pricing["computed_json"],
            ))

        _recalculate_totals(conn, quote_id, 'api')
        _audit_log(conn, 'quote', quote_id, 'created', None, None, quote_number, 'api')

    # Return OUTSIDE the with block so the commit happens before get_quote's
    # separate connection tries to read the freshly-inserted row.
    return get_quote(quote_id)


def update_quote(quote_id: str, data: dict) -> dict:
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not existing:
            return None

        updatable = [
            'customer_name', 'customer_email', 'customer_phone', 'customer_address',
            'business_unit', 'project_name', 'project_description', 'status',
            'tax_rate', 'discount_amount', 'discount_type', 'deposit_percent',
            'valid_days', 'terms', 'notes', 'pricing_mode', 'location',
            'lining_preference', 'job_id', 'customer_id',
        ]
        json_fields = {
            'rooms': 'rooms_json', 'ai_mockups': 'ai_mockups_json',
            'ai_outlines': 'ai_outlines_json', 'measurements': 'measurements_json',
            'photos': 'photos_json',
        }

        sets, params = ["updated_at = ?"], [datetime.now().isoformat()]
        for field in updatable:
            if field in data and data[field] is not None:
                old_val = existing[field] if field in existing.keys() else None
                if str(old_val) != str(data[field]):
                    _audit_log(conn, 'quote', quote_id, 'updated', field, old_val, data[field], 'api')
                sets.append(f"{field} = ?")
                params.append(data[field])

        for src, dest in json_fields.items():
            if src in data and data[src] is not None:
                sets.append(f"{dest} = ?")
                params.append(json.dumps(data[src], default=str))

        params.append(quote_id)
        conn.execute(f"UPDATE quotes_v2 SET {', '.join(sets)} WHERE id = ?", params)
        _recalculate_totals(conn, quote_id, 'api')

    return get_quote(quote_id)


def delete_quote(quote_id: str) -> bool:
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM quote_line_items WHERE quote_id = ?", (quote_id,))
        conn.execute("DELETE FROM quote_photos WHERE quote_id = ?", (quote_id,))
        conn.execute("DELETE FROM quotes_v2 WHERE id = ?", (quote_id,))
        _audit_log(conn, 'quote', quote_id, 'deleted', None, None, None, 'api')
    return True


# ── Line Item CRUD ─────────────────────────────────────────────

def add_line_item(quote_id: str, data: dict) -> dict:
    with get_db() as conn:
        q = conn.execute("SELECT id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not q:
            return None

        max_ln = conn.execute(
            "SELECT COALESCE(MAX(line_number), 0) FROM quote_line_items WHERE quote_id = ?",
            (quote_id,)
        ).fetchone()[0]

        # Sprint 1b: route catalog categories through the engine; non-catalog → manual.
        # For catalog categories, PricingInputError raises out (router maps to 400).
        pricing = _price_line_item(
            category=data.get('category'),
            inputs=data.get('inputs') or data,
            business_unit=data.get('business_unit'),
            legacy=data,
        )
        qty = float(data.get('quantity', 1) or 1)

        conn.execute("""
            INSERT INTO quote_line_items (
                quote_id, line_number, item_type, item_style, description, room,
                width, height, depth, dimension_unit,
                fabric_name, fabric_price_per_yard, yards_needed, fabric_total,
                lining_type, lining_cost,
                labor_description, labor_hours, labor_rate, labor_total,
                hardware_description, hardware_cost,
                quantity, unit, unit_price, subtotal, category, pricing_snapshot_json,
                proposed_price, final_price, price_overridden, business_unit, computed_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            quote_id, max_ln + 1,
            data.get('item_type', ''),
            data.get('item_style', ''),
            data.get('description', ''),
            data.get('room', ''),
            data.get('width'), data.get('height'), data.get('depth'),
            data.get('dimension_unit', 'in'),
            data.get('fabric_name', ''),
            data.get('fabric_price_per_yard'),
            data.get('yards_needed'),
            data.get('fabric_total'),
            data.get('lining_type', ''),
            data.get('lining_cost'),
            data.get('labor_description', ''),
            data.get('labor_hours'),
            data.get('labor_rate', pricing["unit_price"]),
            data.get('labor_total'),
            data.get('hardware_description', ''),
            data.get('hardware_cost'),
            qty,
            data.get('unit', 'ea'),
            pricing["unit_price"],
            pricing["subtotal"],
            data.get('category', 'labor'),
            json.dumps(data.get('pricing_snapshot_json') or data.get('pricing_snapshot'), default=str)
            if (data.get('pricing_snapshot_json') or data.get('pricing_snapshot')) else None,
            pricing["proposed_price"],
            pricing["final_price"],
            pricing["price_overridden"],
            pricing["business_unit"],
            pricing["computed_json"],
        ))

        _recalculate_totals(conn, quote_id, 'api')
        _audit_log(conn, 'quote', quote_id, 'item_added', 'line_items', None,
                   data.get('description', ''), 'api')

    return get_quote(quote_id)


def update_final_price(quote_id: str, item_id: int, final_price,
                       changed_by: str = "founder",
                       reason: Optional[str] = None) -> Optional[dict]:
    """Override a line item's final_price. Sprint 1b / 1c.

    - Sets final_price and price_overridden=1
    - Writes a financial_audit_log row (action='final_price_override',
      old_value=prior final_price, new_value=new final_price)
    - Recalculates the quote's totals (which now sum final_price, not subtotal)
    - Returns the updated line item dict, or None if the line item doesn't exist

    Sprint 1c: raises ImmutableQuoteError if quote status is sent/accepted/
    in_production/completed — the customer-visible snapshot is locked.
    """
    with get_db() as conn:
        # Sprint 1c: immutability check first — refuse mutation if locked.
        _check_immutable(conn, quote_id, "final_price override")
        row = conn.execute(
            "SELECT id, final_price, business_unit FROM quote_line_items "
            "WHERE id = ? AND quote_id = ?",
            (item_id, quote_id),
        ).fetchone()
        if not row:
            return None
        try:
            new_final = round(float(final_price), 2)
        except (TypeError, ValueError):
            return None
        old_final = row["final_price"]
        conn.execute(
            "UPDATE quote_line_items "
            "SET final_price = ?, price_overridden = 1, updated_at = datetime('now') "
            "WHERE id = ?",
            (new_final, item_id),
        )
        _audit_log(
            conn, "quote_line_item", str(item_id), "final_price_override",
            "final_price", old_final, new_final, changed_by, reason,
        )
        _recalculate_totals(conn, quote_id, changed_by)
        updated = conn.execute(
            "SELECT * FROM quote_line_items WHERE id = ?", (item_id,),
        ).fetchone()
        return _item_to_dict(updated)


# ── Sprint 1c: approval gate state transitions ─────────────────────

def submit_for_review(quote_id: str, changed_by: str = "api",
                      reason: Optional[str] = None) -> Optional[dict]:
    """Move a draft into the founder_review queue.

    Allowed transition: draft → founder_review.
    Agents (level 1) can call this. Founder (level 0) can also call it.
    """
    with get_db() as conn:
        prior = _check_transition(conn, quote_id, "founder_review")
        conn.execute(
            "UPDATE quotes_v2 SET status='founder_review', updated_at=datetime('now') "
            "WHERE id = ?",
            (quote_id,),
        )
        _audit_log(
            conn, "quote", quote_id, "submit_for_review", "status",
            prior, "founder_review", changed_by, reason,
        )
    return get_quote(quote_id)


def approve_quote(quote_id: str, changed_by: str = "founder",
                  reason: Optional[str] = None,
                  founder_pin: Optional[str] = None) -> Optional[dict]:
    """Founder-only transition: founder_review → sent.

    Does NOT auto-send the quote. Sending the customer-facing PDF/email
    remains an explicit action via the existing /send route.
    Raises InvalidTransition if the quote is not in founder_review.
    Sprint 1c-fix: raises InvalidFounderPin if founder_pin missing/wrong.
    """
    _require_founder_pin(founder_pin, "approve_quote")
    with get_db() as conn:
        prior = _check_transition(conn, quote_id, "sent")
        conn.execute(
            "UPDATE quotes_v2 SET status='sent', sent_at=datetime('now'), "
            "updated_at=datetime('now') WHERE id = ?",
            (quote_id,),
        )
        _audit_log(
            conn, "quote", quote_id, "approve", "status",
            prior, "sent", changed_by, reason,
        )
    return get_quote(quote_id)


def reject_quote(quote_id: str, changed_by: str = "founder",
                 reason: Optional[str] = None,
                 founder_pin: Optional[str] = None) -> Optional[dict]:
    """Founder-only transition: founder_review → draft.

    Rejection means "needs changes" — the founder can iterate further
    and re-submit. A true kill is a separate cancel action.
    Raises InvalidTransition if the quote is not in founder_review.
    Sprint 1c-fix: raises InvalidFounderPin if founder_pin missing/wrong.
    """
    _require_founder_pin(founder_pin, "reject_quote")
    with get_db() as conn:
        prior = _check_transition(conn, quote_id, "draft")
        conn.execute(
            "UPDATE quotes_v2 SET status='draft', updated_at=datetime('now') "
            "WHERE id = ?",
            (quote_id,),
        )
        _audit_log(
            conn, "quote", quote_id, "reject", "status",
            prior, "draft", changed_by, reason,
        )
    return get_quote(quote_id)


def list_quotes_awaiting_review(business_unit: Optional[str] = None) -> dict:
    """List quotes in founder_review status PLUS legacy 'proposal' quotes
    (tagged with pending_migration=True so the founder sees them but
    the approve/reject endpoints will reject legacy quotes with 409
    until 1d migrates them).

    Returns: {"quotes": [...], "legacy_count": N}
    Each item carries state_metadata = {legacy: bool, pending_migration: bool}.
    """
    with get_db() as conn:
        where = ["status = 'founder_review'"]
        params = []
        if business_unit:
            where.append("business_unit = ?")
            params.append(business_unit)
        rows = conn.execute(
            f"SELECT * FROM quotes_v2 WHERE {' AND '.join(where)} "
            f"ORDER BY updated_at DESC LIMIT 100",
            params,
        ).fetchall()
        awaiting = []
        for r in rows:
            q = _quote_to_dict(r)
            q["state_metadata"] = {"legacy": False, "pending_migration": False}
            awaiting.append(q)

        legacy_where = ["status = 'proposal'"]
        legacy_params = []
        if business_unit:
            legacy_where.append("business_unit = ?")
            legacy_params.append(business_unit)
        legacy_rows = conn.execute(
            f"SELECT * FROM quotes_v2 WHERE {' AND '.join(legacy_where)} "
            f"ORDER BY updated_at DESC LIMIT 100",
            legacy_params,
        ).fetchall()
        legacy = []
        for r in legacy_rows:
            q = _quote_to_dict(r)
            q["state_metadata"] = {
                "legacy": True,
                "pending_migration": True,
                "note": "Legacy 'proposal' status — read-only. Will be migrated to "
                        "quotes_v2 with state mapping in sprint 1d. Approve/reject "
                        "endpoints will return 409 until migrated.",
            }
            legacy.append(q)

    return {
        "awaiting_review": awaiting,
        "legacy_pending_migration": legacy,
        "total_awaiting": len(awaiting),
        "total_legacy": len(legacy),
    }


def update_line_item(quote_id: str, item_id: int, data: dict) -> dict:
    with get_db() as conn:
        # Sprint 1c: refuse line-item mutation if quote is in an immutable
        # status (sent/accepted/in_production/completed).
        _check_immutable(conn, quote_id, "line-item edit")
        existing = conn.execute(
            "SELECT * FROM quote_line_items WHERE id = ? AND quote_id = ?",
            (item_id, quote_id)
        ).fetchone()
        if not existing:
            return None

        updatable = [
            'item_type', 'item_style', 'description', 'room',
            'width', 'height', 'depth', 'dimension_unit',
            'fabric_name', 'fabric_price_per_yard', 'yards_needed', 'fabric_total',
            'lining_type', 'lining_cost',
            'labor_description', 'labor_hours', 'labor_rate', 'labor_total',
            'hardware_description', 'hardware_cost',
            'quantity', 'unit', 'unit_price', 'subtotal', 'category',
            'manual_price_override', 'price_is_manual',
            'pricing_snapshot_json',
        ]
        sets, params = ["updated_at = ?"], [datetime.now().isoformat()]
        for f in updatable:
            if f in data and data[f] is not None:
                sets.append(f"{f} = ?")
                if f == 'pricing_snapshot_json' and not isinstance(data[f], str):
                    params.append(json.dumps(data[f], default=str))
                else:
                    params.append(data[f])

        # Auto-compute subtotal if qty/rate changed
        qty = float(data.get('quantity', existing['quantity'] or 1))
        rate = float(data.get('unit_price', data.get('rate', existing['unit_price'] or 0)))
        if 'subtotal' not in data:
            sets.append("subtotal = ?")
            params.append(round(qty * rate, 2))

        params.append(item_id)
        conn.execute(f"UPDATE quote_line_items SET {', '.join(sets)} WHERE id = ?", params)
        _recalculate_totals(conn, quote_id, 'api')

    return get_quote(quote_id)


def delete_line_item(quote_id: str, item_id: int) -> dict:
    with get_db() as conn:
        conn.execute("DELETE FROM quote_line_items WHERE id = ? AND quote_id = ?", (item_id, quote_id))
        _recalculate_totals(conn, quote_id, 'api')
        _audit_log(conn, 'quote', quote_id, 'item_deleted', 'line_items', item_id, None, 'api')
    return get_quote(quote_id)


# ── Status Transitions ─────────────────────────────────────────
# NOTE: LEGACY_VALID_TRANSITIONS and transition_quote() were removed
# in sprint 1d Phase C. They implemented a draft→sent→approved→ordered
# state machine that has been superseded by the new VALID_TRANSITIONS
# map above (with founder_review state, per sprint 1c). The legacy
# routes /send, /approve, /order in quotes_v2.py that called
# transition_quote() have also been removed (they were dead code).


# ── Stats ──────────────────────────────────────────────────────

def get_quote_stats() -> dict:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM quotes_v2").fetchone()[0]
        by_status = {}
        for row in conn.execute("SELECT status, COUNT(*) FROM quotes_v2 GROUP BY status").fetchall():
            by_status[row[0]] = row[1]
        total_value = conn.execute("SELECT COALESCE(SUM(total), 0) FROM quotes_v2").fetchone()[0]
        avg_value = conn.execute("SELECT COALESCE(AVG(total), 0) FROM quotes_v2 WHERE total > 0").fetchone()[0]
        return {
            "total_quotes": total,
            "by_status": by_status,
            "total_value": round(total_value, 2),
            "average_value": round(avg_value, 2),
        }


def search_quotes(q: str, limit: int = 20) -> list:
    with get_db() as conn:
        s = f"%{q}%"
        rows = conn.execute("""
            SELECT * FROM quotes_v2
            WHERE customer_name LIKE ? OR project_name LIKE ? OR quote_number LIKE ?
            OR notes LIKE ? OR customer_email LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (s, s, s, s, s, limit)).fetchall()
        return [_quote_to_dict(r) for r in rows]
