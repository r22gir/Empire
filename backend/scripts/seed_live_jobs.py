#!/usr/bin/env python3
"""
Seed script for Empire Workroom live jobs (idempotent).
Creates or updates the 6 approved live jobs:
  1. Dahlia Design / Nehal Elrefai
  2. Emma Vita / Wells
  3. Lisa Klein
  4. Whittington Design
  5. Marley's Bar & Grill
  6. Willard InterContinental (Splendor Styling)

RULES & GUARD:
  - Idempotent: checks for existing job by job_number or client_name before creating.
  - Safe by default: DOES NOT run against live data unless explicitly approved via --approve flag.
  - Dry run mode: --dry-run prints actions without modifying the database.
"""

import sys
import os
import json
import uuid
import argparse
import sqlite3
from pathlib import Path

# Adjust python path to find app package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import get_db, dict_row


STATUS_BASE_MAP = {
    "lead": "pending",
    "intake": "pending",
    "measuring": "pending",
    "designing": "pending",
    "estimate_sent": "pending",
    "quoting": "pending",
    "quoted": "pending",
    "deposit_paid": "scheduled",
    "approved": "scheduled",
    "fabric_ordered": "scheduled",
    "fabric_picked_up": "in_progress",
    "in_production": "in_progress",
    "cutting": "in_progress",
    "sewing": "in_production",
    "ready": "in_progress",
    "scheduled": "scheduled",
    "installed": "completed",
    "installing": "in_progress",
    "delivered": "completed",
    "final_invoice": "completed",
    "invoiced": "completed",
    "paid_closed": "completed",
    "paid": "completed",
    "closed": "completed",
    "completed": "completed",
    "pending": "pending",
    "in_progress": "in_progress",
    "on_hold": "on_hold",
    "cancelled": "cancelled",
}


def load_seed_template(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_jobs(conn: sqlite3.Connection, jobs_data: list, dry_run: bool = False) -> dict:
    summary = {
        "created_jobs": 0,
        "updated_jobs": 0,
        "created_invoices": 0,
        "created_payments": 0,
        "created_documents": 0,
    }

    for item in jobs_data:
        client_name = item["client_name"]
        job_number = item["job_number"]
        title = item.get("title", client_name)
        description = item.get("description", "")
        business_unit = item.get("business_unit", "workroom")
        pipeline_stage = item.get("pipeline_stage", "lead")
        base_status = STATUS_BASE_MAP.get(pipeline_stage, "pending")
        estimated_value = float(item.get("estimated_value", 0.0))
        quote_id = item.get("quote_id")
        next_action = item.get("next_action")
        meta = json.dumps({"next_action": next_action}) if next_action else None

        # Ensure customer exists
        cust_row = conn.execute(
            "SELECT id FROM customers WHERE name = ?",
            (client_name,),
        ).fetchone()
        if cust_row:
            customer_id = cust_row[0]
        else:
            customer_id = str(uuid.uuid4())[:16]
            if not dry_run:
                conn.execute(
                    """INSERT INTO customers (id, name, business, created_at)
                       VALUES (?, ?, ?, datetime('now'))""",
                    (customer_id, client_name, business_unit),
                )

        # Check existing job
        existing = conn.execute(
            "SELECT id, job_number FROM jobs WHERE job_number = ? OR client_name = ?",
            (job_number, client_name),
        ).fetchone()

        if existing:
            job_id = existing[0]
            if not dry_run:
                conn.execute(
                    """UPDATE jobs
                       SET title = ?, description = ?, pipeline_stage = ?,
                           status = ?, estimated_value = ?, quote_id = COALESCE(?, quote_id),
                           metadata = COALESCE(?, metadata), customer_id = COALESCE(customer_id, ?), updated_at = datetime('now')
                       WHERE id = ?""",
                    (title, description, pipeline_stage, base_status, estimated_value, quote_id, meta, customer_id, job_id),
                )
            summary["updated_jobs"] += 1
            print(f"[{'DRY-RUN' if dry_run else 'UPDATED'}] Job {job_number}: {client_name}")
        else:
            job_id = str(uuid.uuid4())[:16]
            if not dry_run:
                conn.execute(
                    """INSERT INTO jobs (
                           id, job_number, customer_id, client_name, title, description,
                           business_unit, pipeline_stage, status, estimated_value,
                           quote_id, metadata, created_at, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                    (job_id, job_number, customer_id, client_name, title, description, business_unit, pipeline_stage, base_status, estimated_value, quote_id, meta),
                )
            summary["created_jobs"] += 1
            print(f"[{'DRY-RUN' if dry_run else 'CREATED'}] Job {job_number}: {client_name}")

        # Invoices and payments
        for inv in item.get("invoices", []):
            inv_number = inv["invoice_number"]
            inv_total = float(inv.get("total", 0.0))
            inv_balance = float(inv.get("balance_due", 0.0))
            inv_status = inv.get("status", "sent")
            if inv_status == "unpaid":
                inv_status = "sent"

            inv_row = conn.execute(
                "SELECT id FROM invoices WHERE invoice_number = ?",
                (inv_number,),
            ).fetchone()

            if inv_row:
                invoice_id = inv_row[0]
                if not dry_run:
                    conn.execute(
                        """UPDATE invoices
                           SET job_id = ?, total = ?, balance_due = ?, status = ?
                           WHERE id = ?""",
                        (job_id, inv_total, inv_balance, inv_status, invoice_id),
                    )
            else:
                invoice_id = str(uuid.uuid4())[:16]
                if not dry_run:
                    conn.execute(
                        """INSERT INTO invoices (
                               id, invoice_number, job_id, customer_id, client_name, total,
                               balance_due, status, business_unit, created_at
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                        (invoice_id, inv_number, job_id, customer_id, client_name, inv_total, inv_balance, inv_status, business_unit),
                    )
                summary["created_invoices"] += 1

            # Payments
            for p in inv.get("payments", []):
                p_amount = float(p.get("amount", 0.0))
                p_method = p.get("method", "card")
                p_notes = p.get("notes", "")
                p_ref = p.get("reference", "")

                p_exists = conn.execute(
                    "SELECT id FROM payments WHERE invoice_id = ? AND amount = ? AND notes = ?",
                    (invoice_id, p_amount, p_notes),
                ).fetchone()

                if not p_exists and not dry_run:
                    p_id = str(uuid.uuid4())[:16]
                    conn.execute(
                        """INSERT INTO payments (
                               id, invoice_id, amount, method, notes, reference, payment_date, created_at
                           ) VALUES (?, ?, ?, ?, ?, ?, date('now'), datetime('now'))""",
                        (p_id, invoice_id, p_amount, p_method, p_notes, p_ref),
                    )
                    summary["created_payments"] += 1

        # Documents
        for doc in item.get("documents", []):
            doc_type = doc.get("document_type", "file")
            filename = doc.get("filename", "")
            url = doc.get("url", "")

            d_exists = conn.execute(
                "SELECT id FROM job_documents WHERE job_id = ? AND filename = ?",
                (job_id, filename),
            ).fetchone()

            if not d_exists and not dry_run:
                doc_id = str(uuid.uuid4())[:16]
                conn.execute(
                    """INSERT INTO job_documents (
                           id, job_id, document_type, filename, url, created_at
                       ) VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                    (doc_id, job_id, doc_type, filename, url),
                )
                summary["created_documents"] += 1

    return summary


def main():
    parser = argparse.ArgumentParser(description="Seed live jobs into Empire Workroom database.")
    parser.add_argument("--approve", action="store_true", help="Explicit founder/Max approval required to write live database")
    parser.add_argument("--dry-run", action="store_true", help="Preview seed execution without writing changes")
    parser.add_argument("--file", type=str, default=str(Path(__file__).parent.parent / "data" / "seeds" / "live_jobs.json"), help="Path to seed JSON template")
    args = parser.parse_args()

    seed_file = Path(args.file)
    if not seed_file.exists():
        print(f"Error: seed file not found: {seed_file}")
        sys.exit(1)

    if not args.approve and not args.dry_run:
        print("=" * 60)
        print("LIVE DATA SAFETY NOTICE:")
        print("This seed script contains real jobs (Dahlia, Emma Vita, Lisa Klein, Whittington, Marley's, Willard).")
        print("To preview actions without writing to DB, run with: --dry-run")
        print("To approve and commit changes to the database, run with: --approve")
        print("=" * 60)
        sys.exit(0)

    jobs_data = load_seed_template(seed_file)
    print(f"Loaded {len(jobs_data)} job templates from {seed_file.name}")

    # Ensure schema initialized
    from app.db.init_db import init_database
    from app.routers.jobs_unified import init_schema
    init_database()
    init_schema()

    with get_db() as conn:
        summary = seed_jobs(conn, jobs_data, dry_run=args.dry_run)
        if not args.dry_run:
            conn.commit()

    print("\n--- Seed Execution Summary ---")
    for k, v in summary.items():
        print(f"{k}: {v}")
    if args.dry_run:
        print("\nDry-run complete. No changes were written to the database.")
    else:
        print("\nSeed applied successfully with approval.")


if __name__ == "__main__":
    main()
