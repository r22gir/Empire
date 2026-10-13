"""
QuickBooks Online sandbox connector — Studio/Empire line.

Pull-only: invoices and payments from QBO sandbox into local staging tables.
Never POSTs, PUTs, or DELETEs against QuickBooks (live or sandbox).
Never writes into Empire invoices/payments production tables.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional
from urllib import error, request

from app.db.database import dict_row, dict_rows
from app.services.accounting.guards import (
    LiveWriteBlocked,
    SandboxOnlyError,
    assert_sandbox_credentials,
    qbo_sandbox_base,
    refuse_live_write,
)
from app.services.feature_flags import get_edition, qbo_sync_enabled

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS acct_sync_runs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    connector TEXT NOT NULL,
    edition TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'sandbox_pull',
    live_writes INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    invoices_pulled INTEGER DEFAULT 0,
    payments_pulled INTEGER DEFAULT 0,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS acct_qbo_invoices (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    remote_id TEXT NOT NULL UNIQUE,
    customer_name TEXT,
    doc_number TEXT,
    amount REAL DEFAULT 0,
    balance REAL DEFAULT 0,
    status TEXT,
    txn_date TEXT,
    payload TEXT,
    synced_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS acct_qbo_payments (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    remote_id TEXT NOT NULL UNIQUE,
    invoice_remote_id TEXT,
    customer_name TEXT,
    amount REAL DEFAULT 0,
    method TEXT,
    txn_date TEXT,
    payload TEXT,
    synced_at TEXT DEFAULT (datetime('now'))
);
"""

SANDBOX_FIXTURE = {
    "invoices": [
        {
            "Id": "sandbox-inv-1001",
            "DocNumber": "QBO-SAND-1001",
            "TotalAmt": 480.0,
            "Balance": 180.0,
            "TxnDate": "2026-10-01",
            "CustomerRef": {"name": "Sandbox Studio Client"},
        },
        {
            "Id": "sandbox-inv-1002",
            "DocNumber": "QBO-SAND-1002",
            "TotalAmt": 1250.0,
            "Balance": 0.0,
            "TxnDate": "2026-10-05",
            "CustomerRef": {"name": "Empire Sandbox Workroom"},
        },
    ],
    "payments": [
        {
            "Id": "sandbox-pmt-2001",
            "TotalAmt": 300.0,
            "TxnDate": "2026-10-03",
            "PaymentMethodRef": {"name": "ACH"},
            "CustomerRef": {"name": "Sandbox Studio Client"},
            "Line": [{"LinkedTxn": [{"TxnId": "sandbox-inv-1001", "TxnType": "Invoice"}]}],
        },
        {
            "Id": "sandbox-pmt-2002",
            "TotalAmt": 1250.0,
            "TxnDate": "2026-10-06",
            "PaymentMethodRef": {"name": "Card"},
            "CustomerRef": {"name": "Empire Sandbox Workroom"},
            "Line": [{"LinkedTxn": [{"TxnId": "sandbox-inv-1002", "TxnType": "Invoice"}]}],
        },
    ],
}


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)


def require_enabled() -> None:
    if not qbo_sync_enabled():
        raise SandboxOnlyError(
            "QuickBooks Online sync is disabled. Enable FEATURE_QBO_SYNC "
            "on the Studio/Empire line (EMPIRE_EDITION=studio|empire).",
            403,
        )


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _http_get_sandbox(path: str) -> Optional[dict]:
    """
    Optional live-sandbox GET. Missing creds → None (fixture mode).
    Any write method is impossible here — GET only.
    """
    creds = assert_sandbox_credentials(
        prefix="QBO",
        required=("CLIENT_ID", "CLIENT_SECRET", "REALM_ID", "ACCESS_TOKEN"),
    )
    if not creds.get("access_token") or not creds.get("realm_id"):
        return None
    base = qbo_sandbox_base()
    url = f"{base}/v3/company/{creds['realm_id']}/{path.lstrip('/')}"
    req = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {creds['access_token']}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _invoice_rows(payload: dict) -> list[dict]:
    query = payload.get("QueryResponse") or payload
    items = query.get("Invoice") or payload.get("invoices") or []
    rows = []
    for item in items:
        rows.append(
            {
                "remote_id": str(item.get("Id") or item.get("remote_id")),
                "customer_name": (item.get("CustomerRef") or {}).get("name")
                or item.get("customer_name"),
                "doc_number": item.get("DocNumber") or item.get("doc_number"),
                "amount": float(item.get("TotalAmt") or item.get("amount") or 0),
                "balance": float(item.get("Balance") or item.get("balance") or 0),
                "status": "paid"
                if float(item.get("Balance") or item.get("balance") or 0) == 0
                else "open",
                "txn_date": item.get("TxnDate") or item.get("txn_date"),
                "payload": json.dumps(item),
            }
        )
    return [r for r in rows if r["remote_id"]]


def _payment_rows(payload: dict) -> list[dict]:
    query = payload.get("QueryResponse") or payload
    items = query.get("Payment") or payload.get("payments") or []
    rows = []
    for item in items:
        invoice_id = None
        for line in item.get("Line") or []:
            for linked in line.get("LinkedTxn") or []:
                if linked.get("TxnType") == "Invoice":
                    invoice_id = str(linked.get("TxnId"))
                    break
        rows.append(
            {
                "remote_id": str(item.get("Id") or item.get("remote_id")),
                "invoice_remote_id": invoice_id or item.get("invoice_remote_id"),
                "customer_name": (item.get("CustomerRef") or {}).get("name")
                or item.get("customer_name"),
                "amount": float(item.get("TotalAmt") or item.get("amount") or 0),
                "method": (item.get("PaymentMethodRef") or {}).get("name")
                or item.get("method")
                or "unknown",
                "txn_date": item.get("TxnDate") or item.get("txn_date"),
                "payload": json.dumps(item),
            }
        )
    return [r for r in rows if r["remote_id"]]


def _upsert_invoices(conn, rows: list[dict]) -> int:
    count = 0
    for row in rows:
        conn.execute(
            """INSERT INTO acct_qbo_invoices
               (id, remote_id, customer_name, doc_number, amount, balance, status, txn_date, payload, synced_at)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(remote_id) DO UPDATE SET
                 customer_name=excluded.customer_name,
                 doc_number=excluded.doc_number,
                 amount=excluded.amount,
                 balance=excluded.balance,
                 status=excluded.status,
                 txn_date=excluded.txn_date,
                 payload=excluded.payload,
                 synced_at=excluded.synced_at""",
            (
                row["remote_id"],
                row.get("customer_name"),
                row.get("doc_number"),
                row.get("amount") or 0,
                row.get("balance") or 0,
                row.get("status"),
                row.get("txn_date"),
                row.get("payload"),
                _now(),
            ),
        )
        count += 1
    return count


def _upsert_payments(conn, rows: list[dict]) -> int:
    count = 0
    for row in rows:
        conn.execute(
            """INSERT INTO acct_qbo_payments
               (id, remote_id, invoice_remote_id, customer_name, amount, method, txn_date, payload, synced_at)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(remote_id) DO UPDATE SET
                 invoice_remote_id=excluded.invoice_remote_id,
                 customer_name=excluded.customer_name,
                 amount=excluded.amount,
                 method=excluded.method,
                 txn_date=excluded.txn_date,
                 payload=excluded.payload,
                 synced_at=excluded.synced_at""",
            (
                row["remote_id"],
                row.get("invoice_remote_id"),
                row.get("customer_name"),
                row.get("amount") or 0,
                row.get("method"),
                row.get("txn_date"),
                row.get("payload"),
                _now(),
            ),
        )
        count += 1
    return count


def sync_invoices_and_payments(conn) -> dict:
    """Pull invoices + payments from QBO sandbox (or offline fixture). No writes out."""
    require_enabled()
    ensure_schema(conn)
    qbo_sandbox_base()

    source = "sandbox_fixture"
    invoices_payload: dict[str, Any] = SANDBOX_FIXTURE
    payments_payload: dict[str, Any] = SANDBOX_FIXTURE
    remote = _http_get_sandbox("query?query=select%20%2A%20from%20Invoice")
    if remote:
        invoices_payload = remote
        source = "sandbox_api"
    remote_pmt = _http_get_sandbox("query?query=select%20%2A%20from%20Payment")
    if remote_pmt:
        payments_payload = remote_pmt
        source = "sandbox_api"

    inv_count = _upsert_invoices(conn, _invoice_rows(invoices_payload))
    pmt_count = _upsert_payments(conn, _payment_rows(payments_payload))
    conn.execute(
        """INSERT INTO acct_sync_runs
           (id, connector, edition, mode, live_writes, status, invoices_pulled, payments_pulled)
           VALUES (lower(hex(randomblob(8))), 'qbo', ?, 'sandbox_pull', 0, 'ok', ?, ?)""",
        (get_edition(), inv_count, pmt_count),
    )
    return {
        "connector": "qbo",
        "edition": get_edition(),
        "mode": "sandbox_pull",
        "source": source,
        "live_writes": False,
        "invoices_pulled": inv_count,
        "payments_pulled": pmt_count,
        "wrote_to_empire_invoices": False,
        "wrote_to_qbo": False,
    }


def list_staged_invoices(conn) -> list[dict]:
    ensure_schema(conn)
    rows = dict_rows(
        conn.execute(
            "SELECT id, remote_id, customer_name, doc_number, amount, balance, status, txn_date, synced_at "
            "FROM acct_qbo_invoices ORDER BY txn_date DESC"
        ).fetchall()
    )
    return rows


def list_staged_payments(conn) -> list[dict]:
    ensure_schema(conn)
    rows = dict_rows(
        conn.execute(
            "SELECT id, remote_id, invoice_remote_id, customer_name, amount, method, txn_date, synced_at "
            "FROM acct_qbo_payments ORDER BY txn_date DESC"
        ).fetchall()
    )
    return rows


def push_invoice_to_qbo(_invoice: dict) -> None:
    refuse_live_write("create_or_update_invoice", "qbo")


def push_payment_to_qbo(_payment: dict) -> None:
    refuse_live_write("create_or_update_payment", "qbo")
