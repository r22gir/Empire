"""
Quote Service — SQL-backed CRUD for quotes_v2 + quote_line_items.
Replaces JSON file storage with proper database operations.
All financial writes logged to financial_audit_log.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from app.db.database import get_db, dict_row, dict_rows

logger = logging.getLogger(__name__)


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
    """Recalculate quote totals from line items. Log changes to audit."""
    items = conn.execute(
        "SELECT subtotal FROM quote_line_items WHERE quote_id = ?", (quote_id,)
    ).fetchall()
    items_subtotal = round(sum(r[0] or 0 for r in items), 2)

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

        # Insert line items
        for idx, li in enumerate(data.get('line_items', data.get('items', []))):
            if not isinstance(li, dict):
                continue
            qty = float(li.get('quantity', 1))
            rate = float(li.get('rate', li.get('unit_price', 0)))
            subtotal = round(qty * rate, 2)
            li_amount = float(li.get('amount', subtotal))

            conn.execute("""
                INSERT INTO quote_line_items (
                    quote_id, line_number, description, quantity, unit, unit_price, subtotal, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quote_id, idx + 1,
                li.get('description', ''),
                qty,
                li.get('unit', 'ea'),
                rate,
                li_amount if li_amount else subtotal,
                li.get('category', 'labor'),
            ))

        _recalculate_totals(conn, quote_id, 'api')
        _audit_log(conn, 'quote', quote_id, 'created', None, None, quote_number, 'api')

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

        qty = float(data.get('quantity', 1))
        rate = float(data.get('rate', data.get('unit_price', 0)))
        subtotal = round(qty * rate, 2)

        conn.execute("""
            INSERT INTO quote_line_items (
                quote_id, line_number, item_type, item_style, description, room,
                width, height, depth, dimension_unit,
                fabric_name, fabric_price_per_yard, yards_needed, fabric_total,
                lining_type, lining_cost,
                labor_description, labor_hours, labor_rate, labor_total,
                hardware_description, hardware_cost,
                quantity, unit, unit_price, subtotal, category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get('labor_rate', rate),
            data.get('labor_total'),
            data.get('hardware_description', ''),
            data.get('hardware_cost'),
            qty,
            data.get('unit', 'ea'),
            rate,
            data.get('amount', subtotal),
            data.get('category', 'labor'),
        ))

        _recalculate_totals(conn, quote_id, 'api')
        _audit_log(conn, 'quote', quote_id, 'item_added', 'line_items', None,
                   data.get('description', ''), 'api')

    return get_quote(quote_id)


def update_line_item(quote_id: str, item_id: int, data: dict) -> dict:
    with get_db() as conn:
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
        ]
        sets, params = ["updated_at = ?"], [datetime.now().isoformat()]
        for f in updatable:
            if f in data and data[f] is not None:
                sets.append(f"{f} = ?")
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

VALID_TRANSITIONS = {
    'draft': ['sent', 'cancelled'],
    'sent': ['approved', 'cancelled', 'draft'],
    'approved': ['ordered', 'cancelled'],
    'ordered': ['in_production', 'cancelled'],
    'in_production': ['completed', 'cancelled'],
    'completed': ['cancelled'],
    'cancelled': ['draft'],
}


def transition_quote(quote_id: str, new_status: str, changed_by: str = 'api') -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT status FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not row:
            return None
        current = row[0]
        if new_status not in VALID_TRANSITIONS.get(current, []):
            raise ValueError(f"Cannot transition from {current} to {new_status}")

        now = datetime.now().isoformat()
        extra = {}
        if new_status == 'sent':
            extra['sent_at'] = now
        elif new_status == 'approved':
            extra['accepted_at'] = now

        sets = ["status = ?", "updated_at = ?"]
        params = [new_status, now]
        for k, v in extra.items():
            sets.append(f"{k} = ?")
            params.append(v)
        params.append(quote_id)

        conn.execute(f"UPDATE quotes_v2 SET {', '.join(sets)} WHERE id = ?", params)
        _audit_log(conn, 'quote', quote_id, 'status_change', 'status', current, new_status, changed_by)

    return get_quote(quote_id)


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
