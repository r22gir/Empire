#!/usr/bin/env python3
"""Proof: Max compare_install_prices on mock Willard / Le Midi vs EST-xxxx.

Uses execute_tool (the same door Max chat uses). Mock data only. No send.
Writes PDF + PNG under reports/ and prints the job_documents row.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Isolate from any live DB before app imports.
_tmp = Path(tempfile.mkdtemp(prefix="install_compare_proof_"))
os.environ["EMPIRE_TASK_DB"] = str(_tmp / "empire.db")
os.environ["EMPIRE_DATA_DIR"] = str(_tmp / "data")
os.environ["EMPIRE_DB_PATH"] = str(_tmp / "empire.db")


def main() -> int:
    from app.db.unified_business_migration import create_all_tables
    from app.db.database import get_db
    from app.services.max.tool_executor import execute_tool
    from app.services.quote_service import create_quote

    conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
    create_all_tables(conn)
    conn.close()
    try:
        from app.routers.jobs_unified import init_schema
        init_schema()
    except Exception:
        pass

    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO customers (id, name, business) VALUES ('cust-w','Willard Mock','workroom')")
        db.execute("INSERT OR IGNORE INTO customers (id, name, business) VALUES ('cust-m','Le Midi Mock','workroom')")
        jcols = {r[1] for r in db.execute("PRAGMA table_info(jobs)")}
        fields = ["id", "title", "customer_id"]
        w = ["job-willard", "Willard Est 838", "cust-w"]
        m = ["job-midi", "Le Midi banquettes", "cust-m"]
        n = ["job-new", "New install quote", "cust-w"]
        if "client_name" in jcols:
            fields.append("client_name")
            w.append("Willard"); m.append("Le Midi"); n.append("Willard")
        ph = ", ".join("?" * len(fields))
        for vals in (w, m, n):
            db.execute(f"INSERT OR IGNORE INTO jobs ({', '.join(fields)}) VALUES ({ph})", vals)

    willard = create_quote({
        "customer_name": "Willard Mock",
        "project_name": "Willard Est 838",
        "issued_document": "838",
        "line_items": [{"category": "manual_line", "description": 'Install 10 windows — 160" wall', "unit_price": 1450, "quantity": 1}],
    })
    midi = create_quote({
        "customer_name": "Le Midi Mock",
        "project_name": "Le Midi",
        "line_items": [{"category": "manual_line", "description": "Removal and installation — 8 windows — 20 lf", "unit_price": 2000, "quantity": 1}],
    })
    new_q = create_quote({
        "customer_name": "Willard Mock",
        "project_name": "New install compare",
        "line_items": [{"category": "manual_line", "description": "Install 9 windows — 16 lf", "unit_price": 1800, "quantity": 1}],
    })
    with get_db() as db:
        db.execute("UPDATE quotes_v2 SET job_id=?, customer_id=? WHERE id=?", ("job-willard", "cust-w", willard["id"]))
        db.execute("UPDATE quotes_v2 SET job_id=?, customer_id=? WHERE id=?", ("job-midi", "cust-m", midi["id"]))
        db.execute("UPDATE quotes_v2 SET job_id=?, customer_id=? WHERE id=?", ("job-new", "cust-w", new_q["id"]))

    res = execute_tool({
        "tool": "compare_install_prices",
        "quote_numbers": ["Willard", "Le Midi"],
        "job_ids": ["job-willard", "job-midi"],
        "new_quote": new_q["quote_number"],
    })
    if not res.success:
        print("TOOL FAILED:", res.error)
        return 1
    body = res.result
    print("sent=", body.get("sent"), "used_present=", body.get("used_present_tool"))
    print("telegram=", body.get("telegram_sent"), "email=", body.get("email_sent"), "whatsapp=", body.get("whatsapp_sent"))
    print("pdf_path=", body.get("pdf_path"))
    print("document=", body.get("document"))
    print("new_quote=", new_q["quote_number"])

    pdf_path = Path(body["pdf_path"])
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    artifacts = Path("/opt/cursor/artifacts")
    artifacts.mkdir(parents=True, exist_ok=True)
    dest_pdf = reports / "2026-10-23_install_price_compare.pdf"
    shutil.copy2(pdf_path, dest_pdf)
    shutil.copy2(pdf_path, artifacts / "install-price-compare.pdf")

    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf_path))
    page = doc[0]
    pil = page.render(scale=2).to_pil()
    dest_png = reports / "2026-10-23_install_price_compare.png"
    pil.save(dest_png)
    pil.save(artifacts / "install-price-compare.png")
    print("proof_pdf=", dest_pdf)
    print("proof_png=", dest_png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
