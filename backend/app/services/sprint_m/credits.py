"""Credit memos and overpayment tracking on the client account, applied to invoices."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.services.sprint_m.store import audit, get_store, now_iso, row_to_dict


def _next_memo_number(conn) -> str:
    year = datetime.now().year
    row = conn.execute(
        "SELECT memo_number FROM sm_credit_memos WHERE memo_number LIKE ? ORDER BY memo_number DESC LIMIT 1",
        (f"CM-{year}-%",),
    ).fetchone()
    last = 0
    if row:
        try:
            last = int(str(row[0]).split("-")[-1])
        except (ValueError, IndexError):
            last = 0
    return f"CM-{year}-{last + 1:03d}"


def _ensure_account(conn, customer_id: str, customer_name: str | None = None) -> None:
    conn.execute(
        """INSERT INTO sm_account_credits (customer_id, customer_name, credit_balance, overpayment_balance)
           VALUES (?, ?, 0, 0)
           ON CONFLICT(customer_id) DO UPDATE SET
             customer_name = COALESCE(excluded.customer_name, sm_account_credits.customer_name)""",
        (customer_id, customer_name),
    )


def get_account(customer_id: str) -> dict:
    with get_store() as conn:
        _ensure_account(conn, customer_id)
        row = conn.execute(
            "SELECT * FROM sm_account_credits WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        memos = conn.execute(
            "SELECT * FROM sm_credit_memos WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()
        apps = conn.execute(
            "SELECT * FROM sm_credit_applications WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()
    account = row_to_dict(row)
    account["available"] = round(
        float(account["credit_balance"] or 0) + float(account["overpayment_balance"] or 0), 2
    )
    account["memos"] = [row_to_dict(m) for m in memos]
    account["applications"] = [row_to_dict(a) for a in apps]
    return account


def create_credit_memo(
    *,
    customer_id: str,
    amount: float,
    reason: str,
    customer_name: str | None = None,
    invoice_id: str | None = None,
    job_id: str | None = None,
    actor: str = "owner",
) -> dict:
    if amount <= 0:
        raise ValueError("credit memo amount must be positive")
    memo_id = str(uuid.uuid4())[:12]
    now = now_iso()
    with get_store() as conn:
        _ensure_account(conn, customer_id, customer_name)
        number = _next_memo_number(conn)
        conn.execute(
            """INSERT INTO sm_credit_memos
               (id, memo_number, customer_id, customer_name, amount, reason, status,
                source, invoice_id, job_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'open', 'credit_memo', ?, ?, ?, ?)""",
            (memo_id, number, customer_id, customer_name, amount, reason, invoice_id, job_id, now, now),
        )
        conn.execute(
            """UPDATE sm_account_credits
               SET credit_balance = credit_balance + ?, updated_at = ?
               WHERE customer_id = ?""",
            (amount, now, customer_id),
        )
        audit(conn, "credit_memo", memo_id, "created", actor, str(amount))
    return get_account(customer_id)


def record_overpayment(
    *,
    customer_id: str,
    amount: float,
    invoice_id: str | None = None,
    customer_name: str | None = None,
    actor: str = "system",
) -> dict:
    if amount <= 0:
        raise ValueError("overpayment amount must be positive")
    now = now_iso()
    memo_id = str(uuid.uuid4())[:12]
    with get_store() as conn:
        _ensure_account(conn, customer_id, customer_name)
        number = _next_memo_number(conn)
        conn.execute(
            """INSERT INTO sm_credit_memos
               (id, memo_number, customer_id, customer_name, amount, reason, status,
                source, invoice_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'open', 'overpayment', ?, ?, ?)""",
            (
                memo_id,
                number,
                customer_id,
                customer_name,
                amount,
                f"Overpayment on invoice {invoice_id or 'unspecified'}",
                invoice_id,
                now,
                now,
            ),
        )
        conn.execute(
            """UPDATE sm_account_credits
               SET overpayment_balance = overpayment_balance + ?, updated_at = ?
               WHERE customer_id = ?""",
            (amount, now, customer_id),
        )
        audit(conn, "overpayment", memo_id, "recorded", actor, str(amount))
    return get_account(customer_id)


def apply_credit_to_invoice(
    *,
    customer_id: str,
    invoice_id: str,
    amount: float | None = None,
    actor: str = "owner",
) -> dict:
    account = get_account(customer_id)
    available = account["available"]
    apply_amount = float(amount if amount is not None else available)
    if apply_amount <= 0:
        raise ValueError("nothing to apply")
    if apply_amount - available > 1e-9:
        raise ValueError(f"requested {apply_amount} exceeds available credit {available}")

    now = now_iso()
    remaining = apply_amount
    # Draw overpayments first, then credit memos.
    with get_store() as conn:
        row = conn.execute(
            "SELECT credit_balance, overpayment_balance FROM sm_account_credits WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        over = float(row["overpayment_balance"] or 0)
        credit = float(row["credit_balance"] or 0)
        from_over = min(over, remaining)
        remaining -= from_over
        from_credit = min(credit, remaining)
        remaining -= from_credit
        conn.execute(
            """UPDATE sm_account_credits
               SET overpayment_balance = overpayment_balance - ?,
                   credit_balance = credit_balance - ?,
                   updated_at = ?
               WHERE customer_id = ?""",
            (from_over, from_credit, now, customer_id),
        )
        app_id = str(uuid.uuid4())[:12]
        conn.execute(
            """INSERT INTO sm_credit_applications
               (id, customer_id, invoice_id, amount, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (app_id, customer_id, invoice_id, apply_amount, "account_credit", now),
        )
        # Close memos FIFO while we still have applied amount to attribute.
        left = apply_amount
        memos = conn.execute(
            "SELECT id, amount, status FROM sm_credit_memos WHERE customer_id = ? AND status = 'open' ORDER BY created_at",
            (customer_id,),
        ).fetchall()
        for memo in memos:
            if left <= 0:
                break
            memo_amt = float(memo["amount"] or 0)
            if memo_amt <= left + 1e-9:
                conn.execute(
                    "UPDATE sm_credit_memos SET status = 'applied', updated_at = ? WHERE id = ?",
                    (now, memo["id"]),
                )
                left = round(left - memo_amt, 2)
            else:
                conn.execute(
                    "UPDATE sm_credit_memos SET status = 'partial', updated_at = ? WHERE id = ?",
                    (now, memo["id"]),
                )
                left = 0
        audit(conn, "credit_application", app_id, "applied", actor, f"{apply_amount}->{invoice_id}")
    result = get_account(customer_id)
    result["last_application"] = {
        "id": app_id,
        "invoice_id": invoice_id,
        "amount": apply_amount,
        "from_overpayment": from_over,
        "from_credit_memos": from_credit,
    }
    return result
