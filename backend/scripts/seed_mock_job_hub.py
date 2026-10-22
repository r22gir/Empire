#!/usr/bin/env python3
"""Seed one mock job with an estimate, drawing, photo, and invoice.

Used for local screenshots and tests. Never writes live client data.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def seed(db_path: Path) -> str:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, address TEXT, business TEXT
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, customer_id TEXT, quote_id TEXT, job_number TEXT,
            client_name TEXT, client_email TEXT, client_phone TEXT, status TEXT DEFAULT 'in_progress',
            pipeline_stage TEXT, business_unit TEXT, quoted_amount REAL, metadata TEXT,
            photos TEXT, drawings TEXT, mockups TEXT, created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS quotes_v2 (
            id TEXT PRIMARY KEY, quote_number TEXT, job_id TEXT, customer_id TEXT,
            customer_name TEXT, project_name TEXT, status TEXT, total REAL, created_at TEXT, is_test INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY, invoice_number TEXT, job_id TEXT, quote_id TEXT, customer_id TEXT,
            client_name TEXT, status TEXT, total REAL, balance_due REAL, amount_paid REAL, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS job_documents (
            id TEXT PRIMARY KEY, job_id TEXT, quote_id TEXT, document_type TEXT,
            url TEXT, filename TEXT, revision INTEGER DEFAULT 1, source_channel TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS job_events (
            id TEXT PRIMARY KEY, job_id TEXT, event_type TEXT, summary TEXT, actor TEXT, created_at TEXT, metadata TEXT
        );
        """
    )
    job_id = "job-mock-hub"
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.execute("DELETE FROM quotes_v2 WHERE id = 'q-mock-hub'")
    conn.execute("DELETE FROM invoices WHERE id = 'inv-mock-hub'")
    conn.execute("DELETE FROM job_documents WHERE job_id = ?", (job_id,))
    conn.execute("DELETE FROM customers WHERE id = 'cust-mock-hub'")
    conn.execute(
        "INSERT INTO customers VALUES ('cust-mock-hub','Mock Hub Client','mock.hub@example.test','555-0199','1 Mock Lane','workroom')"
    )
    conn.execute(
        """INSERT INTO jobs (id,title,customer_id,quote_id,job_number,client_name,client_email,client_phone,status,pipeline_stage,business_unit,quoted_amount,metadata,photos,drawings,mockups)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job_id, "Mock banquettes", "cust-mock-hub", "q-mock-hub", "JOB-MOCK-HUB",
            "Mock Hub Client", "mock.hub@example.test", "555-0199", "in_progress", "in_production",
            "workroom", 2400,
            json.dumps({"job_folder_slug": "mock-hub", "source": "mock"}),
            json.dumps([{"url": "/api/v1/photos/serve/job/job-mock-hub/room.jpg", "filename": "room.jpg", "title": "Room photo"}]),
            json.dumps([{"url": "/api/v1/drawings/files/mock-hub.pdf", "filename": "mock-hub.pdf", "title": "Banquette drawing"}]),
            json.dumps([{"url": "/api/v1/drawings/files/mock-hub-mockup.pdf", "filename": "mock-hub-mockup.pdf"}]),
        ),
    )
    conn.execute(
        "INSERT INTO quotes_v2 VALUES ('q-mock-hub','EST-2026-0999','job-mock-hub','cust-mock-hub','Mock Hub Client','Mock banquettes','sent',2400,datetime('now'),1)"
    )
    conn.execute(
        "INSERT INTO invoices VALUES ('inv-mock-hub','INV-2026-0999','job-mock-hub','q-mock-hub','cust-mock-hub','Mock Hub Client','sent',2400,2400,0,datetime('now'))"
    )
    conn.execute(
        "INSERT INTO job_documents VALUES ('jd-mock-draw','job-mock-hub',NULL,'drawing','/api/v1/drawings/files/mock-hub.pdf','mock-hub.pdf',1,'mock',datetime('now'))"
    )
    conn.execute(
        "INSERT INTO job_documents VALUES ('jd-mock-photo','job-mock-hub',NULL,'photo','/api/v1/photos/serve/job/job-mock-hub/room.jpg','room.jpg',1,'mock',datetime('now'))"
    )
    conn.execute(
        "INSERT INTO job_events VALUES ('ev-mock-1','job-mock-hub','status_change','Status: estimate_sent -> in_production','founder',datetime('now'),?)",
        (json.dumps({"from": "estimate_sent", "to": "in_production"}),),
    )
    conn.commit()
    conn.close()
    return job_id


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    args = p.parse_args()
    job_id = seed(Path(args.db))
    print(f"Seeded mock job {job_id} into {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
