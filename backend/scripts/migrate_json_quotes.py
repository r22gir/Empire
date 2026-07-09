"""
Sprint 1d — Migrate legacy JSON quotes (create_quick_quote output) into
quotes_v2 + quote_line_items. Idempotent and re-runnable (keyed on
quotes_v2.id which matches the JSON file stem).

Reads:    /home/rg/empire-data/quotes/*.json  (legacy JSON store)
Writes:   quotes_v2 + quote_line_items (canonical SQL store)
Audit:    every migration writes a financial_audit_log row tagged
          action='migrated_from_json' so it's auditable.

State mapping (per Phase A spec):
    proposal -> proposal (legacy read-only; proposal:[] in VALID_TRANSITIONS)
    draft    -> draft
    accepted -> accepted

business_name mapping (Option B):
    "Empire" -> "workroom"; missing -> "workroom"; logged in audit.

Line-item price semantics (per Amendment A):
    proposed_price = final_price = line total (subtotal) — NOT unit_price.
    For qty=2 unit=$10: line.total=$20 → proposed=final=20. No phantom
    override deltas.

Re-run: scripts/migrate_json_quotes.py is idempotent. Skips rows whose
id already exists in quotes_v2. New JSON quotes created after 1d (via
photo_to_quote → create_quick_quote) get migrated on the next run.
"""
import json
import logging
import os
import sqlite3
import sys
import glob
from datetime import datetime
from pathlib import Path

# Make backend.app importable when running this script directly
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import get_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("migrate_json_quotes")

EMPIRE_DATA_DIR = os.getenv("EMPIRE_DATA_DIR", str(Path.home() / "empire-data"))
JSON_DIR = os.path.join(EMPIRE_DATA_DIR, "quotes")
ARCHIVE_DIR = os.path.join(EMPIRE_DATA_DIR, "archives", "quotes-json-migrated-20260708")

# State machine mapping (per Phase A decision)
STATUS_MAP = {
    "proposal": "proposal",   # read-only in VALID_TRANSITIONS
    "draft":    "draft",
    "accepted": "accepted",
    "sent":     "sent",
    # legacy statuses we'd map if present:
    "approved": "accepted",
    "ordered":  "accepted",
    "in_production": "accepted",
    "completed": "completed",
    "cancelled": "cancelled",
}

# business_name mapping (Option B)
BUSINESS_MAP = {
    "empire":     "workroom",
    "workroom":   "workroom",
    "woodcraft":  "woodcraft",
    "craftforge": "woodcraft",
}


def _norm_status(s):
    if not s:
        return "proposal"
    return STATUS_MAP.get(s.lower(), "proposal")


def _norm_business(name):
    if not name:
        return "workroom", "missing → default workroom"
    key = name.strip().lower()
    mapped = BUSINESS_MAP.get(key)
    if mapped:
        return mapped, f"{name!r} → {mapped}"
    return "workroom", f"{name!r} unrecognized → default workroom"


def _norm_business_unit(name):
    """Same logic as _norm_business but for the per-line business_unit."""
    bu, _ = _norm_business(name)
    return bu


def _audit_log(conn, entity_type, entity_id, action, field_name, old_value, new_value,
               changed_by, reason):
    conn.execute(
        """INSERT INTO financial_audit_log
           (entity_type, entity_id, action, field_name, old_value, new_value, changed_by, reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (entity_type, entity_id, action, field_name,
         str(old_value) if old_value is not None else None,
         str(new_value) if new_value is not None else None,
         changed_by, reason),
    )


def migrate_one(conn, json_path):
    """Migrate a single JSON file. Returns (status, quote_id) where
    status is one of: 'migrated', 'skipped_exists', 'broken'."""
    with open(json_path) as f:
        q = json.load(f)

    qid = q.get("id")
    if not qid or len(qid) != 8:
        return "broken", None

    # Skip if already migrated
    existing = conn.execute("SELECT id, status FROM quotes_v2 WHERE id = ?", (qid,)).fetchone()
    if existing:
        return "skipped_exists", qid

    quote_number = q.get("quote_number") or q.get("qis_quote_number")
    if not quote_number:
        return "broken", None

    business, business_note = _norm_business(q.get("business_name") or q.get("business_unit"))
    new_status = _norm_status(q.get("status"))

    # Resolve selected_proposal_idx (0-based index in design_proposals array)
    design_proposals = q.get("design_proposals") or []
    selected_proposal_idx = q.get("selected_proposal")
    if selected_proposal_idx is None or not design_proposals:
        sp_idx = None
    else:
        # JSON stores selected_proposal as 1-based (per Option A2 convention);
        # convert to 0-based for our column.
        try:
            sp_idx = int(selected_proposal_idx) - 1
            if sp_idx < 0 or sp_idx >= len(design_proposals):
                sp_idx = None
        except (TypeError, ValueError):
            sp_idx = None

    # Resolve quote-level totals
    now = datetime.utcnow().isoformat()
    customer_name = q.get("customer_name") or ""
    subtotal = float(q.get("subtotal") or 0)
    tax_amount = float(q.get("tax_amount") or 0)
    total = float(q.get("total") or 0)
    if not total and subtotal:
        total = round(subtotal + tax_amount, 2)

    # INSERT quote header
    conn.execute(
        """INSERT INTO quotes_v2 (
            id, quote_number, customer_name, customer_email, customer_phone,
            customer_address, business_unit, project_name, project_description,
            status, tax_rate, tax_amount, discount_amount, discount_type,
            subtotal, total, deposit_percent,
            valid_days, expires_at, terms, notes, max_analysis, source,
            rooms_json, ai_mockups_json, ai_outlines_json, photos_json,
            design_proposals_json, selected_proposal_idx,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            qid, quote_number,
            customer_name,
            q.get("customer_email", ""),
            q.get("customer_phone", ""),
            q.get("customer_address", ""),
            business,
            q.get("project_name", ""),
            q.get("max_analysis", ""),  # store max_analysis as project_description-ish blob
            new_status,
            float(q.get("tax_rate") or 0),
            tax_amount,
            0.0,
            "dollar",
            subtotal,
            total,
            50.0,
            int(q.get("valid_days") or 30),
            q.get("expires_at") or now,
            q.get("terms", ""),
            "",  # notes
            q.get("max_analysis", ""),
            q.get("source", "max_quick_quote"),
            json.dumps(q.get("rooms") or [], default=str),
            json.dumps(q.get("ai_mockups") or [], default=str),
            json.dumps(q.get("ai_outlines") or [], default=str),
            json.dumps(q.get("photos") or [], default=str),
            json.dumps(design_proposals, default=str),
            sp_idx,
            q.get("created_at") or now,
            q.get("updated_at") or now,
        ),
    )

    # INSERT line items (Amendment A: proposed = final = line total)
    items = q.get("line_items") or q.get("items") or []
    for idx, li in enumerate(items):
        if not isinstance(li, dict):
            continue
        qty = float(li.get("quantity") or 1)
        unit_price = float(li.get("unit_price") or 0)
        line_total = float(li.get("total") or 0) or round(qty * unit_price, 2)
        # Map JSON category -> our PRICING_SPECS taxonomy where possible
        raw_cat = (li.get("category") or li.get("treatment_type") or "labor").lower()
        cat = raw_cat.replace("-", "_").replace(" ", "_")

        # We DO NOT include design_proposals' per-line items here — those
        # are pricing variants; only the root selected line_items migrate
        # into quote_line_items.
        conn.execute(
            """INSERT INTO quote_line_items (
                quote_id, line_number, description, room,
                quantity, unit, unit_price, subtotal, category,
                proposed_price, final_price, price_overridden,
                business_unit, computed_json,
                item_style, item_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                qid,
                idx + 1,
                li.get("description", ""),
                li.get("room", ""),
                qty,
                "ea",
                unit_price,
                line_total,
                cat,
                line_total,           # proposed_price = line total (Amendment A)
                line_total,           # final_price = line total (Amend A)
                0,                   # price_overridden = false
                business,
                json.dumps({
                    "legacy_qis": True,
                    "migrated_from": "json_quote",
                    "qis_quote_id": q.get("qis_quote_id"),
                    "source_json_path": str(json_path),
                    "original_category": raw_cat,
                }, default=str),
                li.get("treatment_type", ""),
                raw_cat,
            ),
        )

    # Audit log entry — visible to the founder in any audit query
    _audit_log(
        conn, "quote", qid, "migrated_from_json", "status,business_unit,pricing_engine",
        f"json:status={q.get('status')!r},business_name={q.get('business_name')!r}",
        f"v2:status={new_status},business_unit={business}",
        "1d-migration",
        f"{business_note}; qis_quote_number={quote_number}",
    )

    return "migrated", qid


def main():
    if not os.path.isdir(JSON_DIR):
        log.error("JSON quote dir not found: %s", JSON_DIR)
        sys.exit(1)

    # Idempotent ALTER (in case this script runs against a fresh DB)
    with get_db() as conn:
        for sql in [
            "ALTER TABLE quotes_v2 ADD COLUMN selected_proposal_idx INTEGER",
        ]:
            try:
                conn.execute(sql)
                log.info("applied: %s", sql)
            except sqlite3.OperationalError:
                pass  # already exists
        conn.commit()

    json_files = sorted(glob.glob(os.path.join(JSON_DIR, "*.json")))
    json_files = [f for f in json_files if not os.path.basename(f).startswith("_")]
    log.info("found %d JSON quote files", len(json_files))

    summary = {"migrated": 0, "skipped_exists": 0, "broken": 0}
    with get_db() as conn:
        for jf in json_files:
            try:
                status, qid = migrate_one(conn, jf)
                summary[status] += 1
                log.info("  %s: %s (id=%s)", status, os.path.basename(jf), qid)
            except sqlite3.IntegrityError as e:
                # Probably a quote_number uniqueness collision; skip but don't crash
                log.warning("  integrity error for %s: %s", os.path.basename(jf), e)
                summary["broken"] += 1
            except Exception as e:
                log.error("  broken: %s: %s", os.path.basename(jf), e)
                summary["broken"] += 1
        conn.commit()

    log.info("SUMMARY: %s", summary)
    print("\nFINAL COUNTS:")
    cur = conn.execute(
        "SELECT status, COUNT(*) FROM quotes_v2 GROUP BY status ORDER BY status"
    )
    for row in cur.fetchall():
        print(f"  quotes_v2.{row[0]:15s} = {row[1]}")


if __name__ == "__main__":
    main()