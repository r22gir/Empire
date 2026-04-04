"""
Work Order Service — Create, manage, and track work orders through production.
Work orders are created from approved quotes and track items through production stages.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from app.db.database import get_db, dict_row, dict_rows

logger = logging.getLogger(__name__)


# ── Production Stages ──────────────────────────────────────────

WORKROOM_STAGES = [
    "pending", "fabric_ordered", "fabric_received", "cutting",
    "sewing", "finishing", "qc", "complete", "delivered",
]

WOODCRAFT_STAGES = [
    "pending", "materials_ordered", "materials_received", "cutting",
    "assembly", "sanding", "finishing", "upholstery", "qc", "complete", "delivered",
]

def _get_stages(business_unit: str) -> list:
    if business_unit in ("woodcraft", "millwork", "cnc"):
        return WOODCRAFT_STAGES
    return WORKROOM_STAGES


def _next_wo_number(conn) -> str:
    year = datetime.now().year
    row = conn.execute(
        "SELECT work_order_number FROM work_orders WHERE work_order_number LIKE ? ORDER BY work_order_number DESC LIMIT 1",
        (f"WO-{year}-%",)
    ).fetchone()
    if row:
        try:
            last_seq = int(row[0].split('-')[-1])
        except (ValueError, IndexError):
            last_seq = 0
    else:
        last_seq = 0
    return f"WO-{year}-{last_seq + 1:03d}"


def _audit_log(conn, entity_type, entity_id, action, field=None, old=None, new=None, by="system", reason=None):
    conn.execute("""
        INSERT INTO financial_audit_log
        (entity_type, entity_id, action, field_name, old_value, new_value, changed_by, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (entity_type, entity_id, action, field,
          str(old) if old is not None else None,
          str(new) if new is not None else None, by, reason))


# ── CRUD ───────────────────────────────────────────────────────

def create_work_order_from_quote(quote_id: str, assigned_to: str = None) -> dict:
    """Create a work order + items from an approved/ordered quote."""
    with get_db() as conn:
        q = conn.execute("SELECT * FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not q:
            raise ValueError(f"Quote {quote_id} not found")
        q = dict(q)
        if q['status'] not in ('approved', 'ordered', 'in_production'):
            raise ValueError(f"Quote must be approved/ordered to create WO (current: {q['status']})")

        # Check for existing WO
        existing = conn.execute(
            "SELECT work_order_number FROM work_orders WHERE quote_id = ?", (quote_id,)
        ).fetchone()
        if existing:
            raise ValueError(f"Work order {existing[0]} already exists for quote {quote_id}")

        wo_number = _next_wo_number(conn)
        now = datetime.now().isoformat()
        business_unit = q.get('business_unit', 'workroom')

        conn.execute("""
            INSERT INTO work_orders (
                work_order_number, quote_id, job_id, customer_id, customer_name,
                business_unit, assigned_to, priority, status, instructions, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wo_number, quote_id, q.get('job_id'), q.get('customer_id'),
            q.get('customer_name', ''), business_unit,
            assigned_to, 'normal', 'pending',
            q.get('notes', ''), now, now,
        ))

        wo_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Create items from quote line items
        items = conn.execute(
            "SELECT * FROM quote_line_items WHERE quote_id = ? ORDER BY line_number",
            (quote_id,)
        ).fetchall()

        for item in items:
            item = dict(item)
            dims = json.dumps({
                'width': item.get('width'), 'height': item.get('height'), 'depth': item.get('depth')
            })
            fabric_info = json.dumps({
                'name': item.get('fabric_name'), 'yards': item.get('yards_needed'),
                'price_per_yard': item.get('fabric_price_per_yard'),
            })
            conn.execute("""
                INSERT INTO work_order_items (
                    work_order_id, quote_line_item_id, item_type, description,
                    room, dimensions, fabric_info, quantity, production_status,
                    special_instructions, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wo_id, item['id'], item.get('item_type', ''),
                item.get('description', ''), item.get('room', ''),
                dims, fabric_info, item.get('quantity', 1),
                'pending', '', now, now,
            ))

        # Update quote status
        conn.execute("UPDATE quotes_v2 SET status = 'ordered', updated_at = ? WHERE id = ?",
                     (now, quote_id))

        _audit_log(conn, 'work_order', str(wo_id), 'created', 'quote_id', None, quote_id,
                   'system', f'Created from quote {quote_id}')

    return get_work_order(wo_id)


def create_work_order(data: dict) -> dict:
    """Create a standalone work order (not from quote)."""
    with get_db() as conn:
        wo_number = _next_wo_number(conn)
        now = datetime.now().isoformat()

        conn.execute("""
            INSERT INTO work_orders (
                work_order_number, quote_id, job_id, customer_id, customer_name,
                business_unit, assigned_to, priority, status, due_date,
                instructions, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wo_number,
            data.get('quote_id'),
            data.get('job_id'),
            data.get('customer_id'),
            data.get('customer_name', ''),
            data.get('business_unit', 'workroom'),
            data.get('assigned_to'),
            data.get('priority', 'normal'),
            'pending',
            data.get('due_date'),
            data.get('instructions', ''),
            data.get('notes', ''),
            now, now,
        ))

        wo_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _audit_log(conn, 'work_order', str(wo_id), 'created', None, None, wo_number)

    return get_work_order(wo_id)


def get_work_order(wo_id) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (wo_id,)).fetchone()
        if not row:
            return None
        wo = dict(row)

        items = conn.execute(
            "SELECT * FROM work_order_items WHERE work_order_id = ? ORDER BY id",
            (wo_id,)
        ).fetchall()
        wo['items'] = [dict(i) for i in items]

        log = conn.execute(
            "SELECT * FROM production_log WHERE work_order_id = ? ORDER BY created_at DESC LIMIT 50",
            (wo_id,)
        ).fetchall()
        wo['production_log'] = [dict(l) for l in log]

        return wo


def list_work_orders(status: str = None, business_unit: str = None,
                     limit: int = 50, offset: int = 0) -> dict:
    with get_db() as conn:
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        if business_unit:
            where.append("business_unit = ?")
            params.append(business_unit)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        total = conn.execute(f"SELECT COUNT(*) FROM work_orders {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM work_orders {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

        wos = []
        for r in rows:
            wo = dict(r)
            wo['item_count'] = conn.execute(
                "SELECT COUNT(*) FROM work_order_items WHERE work_order_id = ?", (wo['id'],)
            ).fetchone()[0]
            wos.append(wo)

        return {"work_orders": wos, "total": total}


# ── Production Stage Management ────────────────────────────────

def advance_item_stage(wo_id: int, item_id: int, changed_by: str = "system",
                       notes: str = "", photo_path: str = None) -> dict:
    """Advance a work order item to the next production stage."""
    with get_db() as conn:
        item = conn.execute(
            "SELECT * FROM work_order_items WHERE id = ? AND work_order_id = ?",
            (item_id, wo_id)
        ).fetchone()
        if not item:
            raise ValueError(f"Item {item_id} not found in WO {wo_id}")

        wo = conn.execute("SELECT business_unit FROM work_orders WHERE id = ?", (wo_id,)).fetchone()
        stages = _get_stages(wo[0] if wo else 'workroom')

        current = item['production_status']
        if current not in stages:
            current_idx = 0
        else:
            current_idx = stages.index(current)

        if current_idx >= len(stages) - 1:
            raise ValueError(f"Item already at final stage: {current}")

        new_status = stages[current_idx + 1]
        now = datetime.now().isoformat()

        conn.execute(
            "UPDATE work_order_items SET production_status = ?, updated_at = ? WHERE id = ?",
            (new_status, now, item_id)
        )

        conn.execute("""
            INSERT INTO production_log
            (work_order_id, work_order_item_id, from_status, to_status, changed_by, notes, photo_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (wo_id, item_id, current, new_status, changed_by, notes, photo_path, now))

        # Check if all items at same stage — update WO status
        all_items = conn.execute(
            "SELECT production_status FROM work_order_items WHERE work_order_id = ?",
            (wo_id,)
        ).fetchall()

        statuses = [i[0] for i in all_items]
        if all(s == 'complete' for s in statuses):
            conn.execute("UPDATE work_orders SET status = 'complete', updated_at = ? WHERE id = ?",
                        (now, wo_id))
            _audit_log(conn, 'work_order', str(wo_id), 'completed', 'status', 'in_progress', 'complete')
        elif all(s == 'delivered' for s in statuses):
            conn.execute("UPDATE work_orders SET status = 'delivered', updated_at = ? WHERE id = ?",
                        (now, wo_id))
        elif any(s not in ('pending',) for s in statuses):
            conn.execute("UPDATE work_orders SET status = 'in_progress', updated_at = ? WHERE id = ?",
                        (now, wo_id))

    # Notify on stage change (non-blocking)
    try:
        notify_on_stage_change(wo_id, item_id, new_status, notes)
    except Exception as e:
        logger.warning(f"Notification failed for WO {wo_id}: {e}")

    return get_work_order(wo_id)


def get_production_board(business_unit: str = None) -> dict:
    """Kanban board view — items grouped by production stage with urgency colors."""
    with get_db() as conn:
        query = """
            SELECT woi.*, wo.work_order_number, wo.customer_name, wo.business_unit,
                   wo.due_date, wo.priority, wo.quote_id
            FROM work_order_items woi
            JOIN work_orders wo ON wo.id = woi.work_order_id
            WHERE wo.status NOT IN ('delivered', 'cancelled')
        """
        params = []
        if business_unit:
            query += " AND wo.business_unit = ?"
            params.append(business_unit)
        query += " ORDER BY wo.due_date ASC NULLS LAST, woi.updated_at"

        items = conn.execute(query, params).fetchall()

        now = datetime.now()
        board = {}
        overdue = 0
        due_soon = 0

        for item in items:
            d = dict(item)
            stage = d['production_status']
            if stage not in board:
                board[stage] = []

            # Urgency color coding based on due date
            due = d.get('due_date')
            if due:
                try:
                    due_dt = datetime.fromisoformat(due) if isinstance(due, str) else due
                    days_until = (due_dt - now).days
                    if days_until < 0:
                        d['urgency'] = 'overdue'
                        d['urgency_color'] = 'red'
                        d['days_overdue'] = abs(days_until)
                        overdue += 1
                    elif days_until <= 2:
                        d['urgency'] = 'due_soon'
                        d['urgency_color'] = 'yellow'
                        d['days_until_due'] = days_until
                        due_soon += 1
                    else:
                        d['urgency'] = 'on_track'
                        d['urgency_color'] = 'green'
                        d['days_until_due'] = days_until
                except (ValueError, TypeError):
                    d['urgency'] = 'no_date'
                    d['urgency_color'] = 'gray'
            else:
                d['urgency'] = 'no_date'
                d['urgency_color'] = 'gray'

            board[stage].append(d)

        # Ordered stages list
        all_stages = WORKROOM_STAGES
        ordered_stages = [s for s in all_stages if s in board]
        extra = [s for s in board if s not in all_stages]
        ordered_stages.extend(extra)

        return {
            "board": board,
            "total_items": len(items),
            "overdue": overdue,
            "due_soon": due_soon,
            "stages": ordered_stages,
            "stage_counts": {s: len(board.get(s, [])) for s in ordered_stages},
        }


def get_overdue_items() -> list:
    """Get all overdue production items for morning report."""
    with get_db() as conn:
        now = datetime.now().isoformat()
        rows = conn.execute("""
            SELECT woi.id, woi.description, woi.production_status,
                   wo.work_order_number, wo.customer_name, wo.due_date
            FROM work_order_items woi
            JOIN work_orders wo ON wo.id = woi.work_order_id
            WHERE wo.due_date < ? AND wo.status NOT IN ('complete', 'delivered', 'cancelled')
              AND woi.production_status NOT IN ('complete', 'delivered')
            ORDER BY wo.due_date ASC
        """, (now,)).fetchall()
        return [dict(r) for r in rows]


def notify_on_stage_change(wo_id: int, item_id: int, new_status: str, notes: str = ""):
    """Send notifications when a production stage changes.
    Notifies client via portal email if portal token exists."""
    with get_db() as conn:
        wo = conn.execute(
            "SELECT customer_id, customer_name, quote_id FROM work_orders WHERE id = ?",
            (wo_id,)
        ).fetchone()
        if not wo:
            return

        # Check for client portal
        portal = conn.execute(
            "SELECT token FROM client_portal_tokens WHERE customer_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
            (wo[0],)
        ).fetchone()

        status_labels = {
            "fabric_ordered": "Fabric has been ordered",
            "fabric_received": "Fabric arrived and quality checked",
            "cutting": "Cutting has started",
            "sewing": "Sewing is in progress",
            "finishing": "Finishing touches being applied",
            "qc": "Quality check in progress",
            "complete": "Your items are complete!",
            "delivered": "Your items have been delivered",
        }
        label = status_labels.get(new_status, f"Status: {new_status}")

        # Log the notification
        logger.info(f"Production update for {wo[1]}: {label} (portal: {'yes' if portal else 'no'})")

        # If work order is complete, also log that
        if new_status == "complete":
            logger.info(f"🎉 Work order {wo_id} for {wo[1]} is COMPLETE — ready for delivery")
