"""Maxine reservation package on ConstructionForge.

Lot status changes only when the caller passes confirm=True and a legal next status.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from app.services.voice_doc.plans import format_cop
from app.services.voice_doc.templates import WATERMARK, attachment_manifest, render_package_attachments

LOT_FLOW = ("available", "reservado", "separado", "vendido")
_ALIASES = {"reserved": "reservado", "sold": "vendido"}


class DealError(Exception):
    pass


def normalize_lot_status(status: str | None) -> str:
    raw = (status or "").strip().lower()
    return _ALIASES.get(raw, raw)


def can_transition(current: str | None, target: str | None) -> bool:
    current_n = normalize_lot_status(current)
    target_n = normalize_lot_status(target)
    if current_n not in LOT_FLOW or target_n not in LOT_FLOW:
        return False
    return LOT_FLOW.index(target_n) == LOT_FLOW.index(current_n) + 1


def transition_lot_status(current: str | None, target: str | None, *, confirmed: bool) -> str:
    if not confirmed:
        raise DealError("El estado del lote solo cambia cuando confirmas")
    if not can_transition(current, target):
        raise DealError(
            f"No se puede pasar de {normalize_lot_status(current) or 'sin estado'} "
            f"a {normalize_lot_status(target) or 'sin estado'}"
        )
    return normalize_lot_status(target)


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(start.day, days[month - 1])
    return date(year, month, day)


def placeholder_values(fields: dict, schedule: dict | None = None) -> dict:
    price = fields.get("price")
    return {
        "comprador": fields.get("buyer_name") or "",
        "lote": fields.get("lot_number") or "",
        "proyecto": fields.get("project_name") or "",
        "precio": format_cop(int(price)) if price else "",
        "fecha": date.today().isoformat(),
        "separacion": format_cop(int(fields.get("separacion") or 0)),
        "cuota_inicial": format_cop(int(schedule["cuota_inicial"])) if schedule else "",
        "saldo": format_cop(int(schedule["balance"])) if schedule else "",
        "contenido_abogado": "",
    }


def recibo_text(payment: dict, fields: dict) -> str:
    amount = int(payment.get("amount") or 0)
    kind = payment.get("kind") or "pago"
    return (
        f"{WATERMARK}\n"
        f"RECIBO BORRADOR\n"
        f"Concepto: {kind}\n"
        f"Valor: {format_cop(amount)} COP\n"
        f"Fecha: {payment.get('date') or date.today().isoformat()}\n"
        f"Pagador: {fields.get('buyer_name') or ''}\n"
        f"Lote: {fields.get('lot_number') or ''}\n"
        "Este recibo no se envía solo.\n"
    )


def overdue_payments(today: str | None = None) -> list[dict]:
    today = today or date.today().isoformat()
    from app.routers.construction import get_db

    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT p.amount, p.due_date, p.status, p.installment_number, p.notes,
                   b.first_name, b.last_name, l.lot_number
            FROM cf_payments p
            JOIN cf_buyers b ON p.buyer_id = b.id
            JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE p.status IN ('pending', 'overdue')
              AND p.due_date IS NOT NULL
              AND p.due_date < ?
            ORDER BY p.due_date
            """,
            (today,),
        ).fetchall()
        found = []
        for row in rows:
            buyer = " ".join(part for part in (row["first_name"], row["last_name"]) if part)
            found.append({
                "amount": row["amount"],
                "due_date": row["due_date"],
                "status": row["status"],
                "lot_number": row["lot_number"],
                "buyer": buyer,
                "installment_number": row["installment_number"],
                "notes": row["notes"],
            })
        return found
    finally:
        conn.close()


def overdue_brief_text(today: str | None = None) -> str:
    rows = overdue_payments(today)
    if not rows:
        return ""
    lines = ["Pagos vencidos (ConstructionForge):"]
    for row in rows[:8]:
        lines.append(
            f"- Lote {row['lot_number']}: {format_cop(int(row['amount']))} COP, "
            f"venció {row['due_date']}, {row['buyer']}"
        )
    if len(rows) > 8:
        lines.append(f"- y {len(rows) - 8} más")
    return "\n".join(lines)


def _find_lot(conn, lot_number: str, project_id: str | None = None):
    if project_id:
        row = conn.execute(
            "SELECT * FROM cf_lots WHERE project_id = ? AND lot_number = ?",
            (project_id, str(lot_number)),
        ).fetchone()
        if row:
            return row
    return conn.execute("SELECT * FROM cf_lots WHERE lot_number = ?", (str(lot_number),)).fetchone()


def confirm_reservation(
    *,
    fields: dict,
    schedule: dict,
    draft_id: str,
    confirm: bool,
    lot_status: str | None = None,
    payment: dict | None = None,
) -> dict:
    """Write cf_sales and cf_payments only when confirm is true. Never sends."""
    if not confirm:
        return {"ok": False, "sent": False, "emailed": False, "sale_id": None, "lot_changed": False,
                "reason": "Confirmación explícita requerida. No se registró la venta ni se envió nada."}
    if not fields.get("price"):
        raise DealError("Falta el precio. No registro la venta.")
    if not fields.get("lot_number"):
        raise DealError("Falta el lote.")
    if not fields.get("buyer_name"):
        raise DealError("Falta el comprador.")

    from app.routers.construction import get_db
    from app.services.construction_bridge import upsert_buyer

    conn = get_db()
    try:
        lot = _find_lot(conn, str(fields["lot_number"]), fields.get("project_id"))
        if lot is None:
            raise DealError("Ese lote no existe. No creo lotes nuevos.")
        before = lot["status"] or "available"
        new_status = before
        if lot_status:
            new_status = transition_lot_status(before, lot_status, confirmed=True)

        buyer = upsert_buyer(name=fields["buyer_name"], email=fields.get("buyer_email") or "", phone=fields.get("buyer_phone") or "", source="voz")
        values = placeholder_values(fields, schedule)
        attachments = render_package_attachments(values)
        sale_id = str(uuid.uuid4())
        contract_type = "compraventa" if normalize_lot_status(lot_status) == "vendido" else "separacion"
        conn.execute(
            """
            INSERT INTO cf_sales (
                id, lot_id, buyer_id, sale_price, currency, payment_plan,
                contract_type, contract_date, contract_document,
                down_payment, down_payment_received, status, notes
            ) VALUES (?, ?, ?, ?, 'COP', ?, ?, ?, ?, ?, ?, 'confirmed', ?)
            """,
            (
                sale_id,
                lot["id"],
                buyer["id"],
                int(fields["price"]),
                json.dumps(schedule, ensure_ascii=False),
                contract_type,
                date.today().isoformat(),
                attachment_manifest(attachments),
                int(schedule.get("cuota_inicial") or 0),
                1 if payment else 0,
                f"borrador {draft_id}",
            ),
        )
        buyer_id = buyer["id"]
        payments = []
        if schedule.get("separacion"):
            payments.append(("separacion", int(schedule["separacion"]), date.today().isoformat(), 0))
        restante = int(schedule.get("cuota_inicial_restante") or 0)
        if restante:
            payments.append(("cuota_inicial", restante, date.today().isoformat(), 0))
        start = date.today()
        for row in schedule.get("installments") or []:
            payments.append(("cuota", int(row["amount"]), _add_months(start, int(row["installment_number"])).isoformat(), row["installment_number"]))
        if schedule.get("balloon"):
            payments.append(("cuota_final", int(schedule["balloon"]), _add_months(start, int(schedule.get("installment_count") or 1) + 1).isoformat(), None))

        recorded_receipt = None
        for kind, amount, due, number in payments:
            payment_id = str(uuid.uuid4())
            status = "pending"
            paid_on = None
            if payment and payment.get("kind") == kind and int(payment.get("amount") or 0) == amount:
                status = "paid"
                paid_on = payment.get("date") or date.today().isoformat()
                recorded_receipt = recibo_text({"amount": amount, "kind": kind, "date": paid_on}, fields)
            conn.execute(
                """
                INSERT INTO cf_payments (
                    id, sale_id, buyer_id, amount, currency, due_date, payment_date,
                    installment_number, status, notes
                ) VALUES (?, ?, ?, ?, 'COP', ?, ?, ?, ?, ?)
                """,
                (payment_id, sale_id, buyer_id, amount, due, paid_on, number, status, kind),
            )
        lot_changed = False
        if lot_status:
            updates = {"status": new_status, "updated_at": datetime.utcnow().isoformat()}
            if new_status == "reservado":
                updates["reserved_at"] = updates["updated_at"]
                updates["reserved_by"] = fields["buyer_name"]
            elif new_status == "separado":
                updates["reserved_at"] = lot["reserved_at"] or updates["updated_at"]
                updates["reserved_by"] = fields["buyer_name"]
            elif new_status == "vendido":
                updates["sold_at"] = updates["updated_at"]
                updates["sold_to"] = fields["buyer_name"]
            clause = ", ".join(f"{key} = ?" for key in updates)
            conn.execute(f"UPDATE cf_lots SET {clause} WHERE id = ?", list(updates.values()) + [lot["id"]])
            lot_changed = True
        conn.commit()
        return {
            "ok": True,
            "sent": False,
            "emailed": False,
            "sale_id": sale_id,
            "lot_id": lot["id"],
            "lot_status": new_status if lot_changed else before,
            "lot_changed": lot_changed,
            "contract_type": contract_type,
            "recibo": recorded_receipt,
            "attachments": [{"key": item["key"], "watermark": item["watermark"]} for item in attachments],
        }
    finally:
        conn.close()
