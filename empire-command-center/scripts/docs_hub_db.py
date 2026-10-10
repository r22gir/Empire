#!/usr/bin/env python3
"""Read-only snapshot of the records the Docs hub needs (quotes, invoices,
jobs, drawing versions, job documents). Opens the live SQLite DB with
mode=ro so it can never write. Prints one JSON object on stdout.

Used by app/lib/docs-hub/server.ts. DB path: $EMPIRE_DB_PATH or
~/empire-data/empire.db (same default as backend/app/db/database.py).
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

DB = os.getenv("EMPIRE_DB_PATH") or str(Path.home() / "empire-data" / "empire.db")


def rows(conn, sql, cols=None):
    try:
        cur = conn.execute(sql)
    except sqlite3.Error as exc:  # table missing on this box: return nothing
        return {"error": str(exc), "rows": []}
    names = [d[0] for d in cur.description]
    return {"rows": [dict(zip(names, r)) for r in cur.fetchall()]}


def main():
    if not os.path.exists(DB):
        print(json.dumps({"error": f"db not found: {DB}"}))
        return 0
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
    out = {
        "db": DB,
        "quotes": rows(conn, """SELECT id, quote_number, customer_id, customer_name, customer_email, customer_phone,
              customer_address, project_address, project_name, business_unit, job_id, status, total,
              deposit_percent, deposit_required, deposit_paid, balance_due, sent_at, accepted_at,
              created_at, updated_at, is_test FROM quotes_v2"""),
        "invoices": rows(conn, """SELECT id, invoice_number, quote_id, job_id, client_name, client_phone, client_email,
              status, payment_status, total, amount_paid, balance_due, deposit_required, deposit_received,
              due_date, created_at, updated_at, business_unit FROM invoices"""),
        "jobs": rows(conn, """SELECT id, job_number, title, quote_id, invoice_id, client_name, client_phone, client_email,
              client_address, address, status, pipeline_stage, install_date, scheduled_date, due_date,
              paid_amount, quoted_amount, invoiced_amount, business_unit, updated_at FROM jobs"""),
        "drawings": rows(conn, """SELECT id, item_type, item_name, quote_id, job_id, version, file_path, file_format,
              created_at FROM drawing_versions"""),
        "job_documents": rows(conn, """SELECT id, job_id, quote_id, document_type, url, filename, revision,
              visible_to_client, source_channel, created_at FROM job_documents"""),
    }
    conn.close()
    json.dump(out, sys.stdout, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
