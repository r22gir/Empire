"""
Empire Unified Business System — Database Migration
Creates all tables for the unified business flow:
  - financial_audit_log
  - quotes_v2, quote_line_items, quote_photos
  - work_orders, work_order_items, production_log
  - payments_v2, chart_of_accounts

All migrations are idempotent (CREATE IF NOT EXISTS, INSERT OR IGNORE).
"""
import sqlite3
import json
import glob
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path(__file__).resolve().parent.parent.parent / "data" / "empire.db")
)

QUOTES_DIR = os.path.expanduser("~/empire-repo/backend/data/quotes")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Table Creation ─────────────────────────────────────────────

def create_all_tables(conn: sqlite3.Connection):
    """Create all unified business tables. Idempotent."""

    conn.executescript("""
    -- Financial Audit Log (created FIRST — everything else logs to it)
    CREATE TABLE IF NOT EXISTS financial_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        action TEXT NOT NULL,
        field_name TEXT,
        old_value TEXT,
        new_value TEXT,
        changed_by TEXT DEFAULT 'system',
        reason TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_audit_entity ON financial_audit_log(entity_type, entity_id);
    CREATE INDEX IF NOT EXISTS idx_audit_created ON financial_audit_log(created_at);

    -- Quotes v2 (SQL-backed)
    CREATE TABLE IF NOT EXISTS quotes_v2 (
        id TEXT PRIMARY KEY,
        quote_number TEXT UNIQUE,
        customer_id TEXT,
        customer_name TEXT,
        customer_email TEXT,
        customer_phone TEXT,
        customer_address TEXT,
        business_unit TEXT DEFAULT 'workroom',
        job_id TEXT,
        project_name TEXT,
        project_description TEXT,
        status TEXT DEFAULT 'draft',
        subtotal REAL DEFAULT 0.0,
        tax_rate REAL DEFAULT 0.0,
        tax_amount REAL DEFAULT 0.0,
        discount_amount REAL DEFAULT 0.0,
        discount_type TEXT DEFAULT 'dollar',
        total REAL DEFAULT 0.0,
        deposit_percent REAL DEFAULT 50.0,
        deposit_required REAL DEFAULT 0.0,
        deposit_paid REAL DEFAULT 0.0,
        balance_due REAL DEFAULT 0.0,
        valid_days INTEGER DEFAULT 30,
        expires_at TEXT,
        payment_terms TEXT,
        terms TEXT,
        source TEXT,
        source_json_path TEXT,
        notes TEXT,
        max_analysis TEXT,
        pricing_mode TEXT,
        location TEXT,
        lining_preference TEXT,
        rooms_json TEXT,
        tiers_json TEXT,
        design_proposals_json TEXT,
        ai_mockups_json TEXT,
        ai_outlines_json TEXT,
        photos_json TEXT,
        measurements_json TEXT,
        metadata_json TEXT,
        pdf_path TEXT,
        sent_at TEXT,
        accepted_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_quotes_v2_customer ON quotes_v2(customer_id);
    CREATE INDEX IF NOT EXISTS idx_quotes_v2_status ON quotes_v2(status);
    CREATE INDEX IF NOT EXISTS idx_quotes_v2_business ON quotes_v2(business_unit);
    CREATE INDEX IF NOT EXISTS idx_quotes_v2_created ON quotes_v2(created_at);
    CREATE INDEX IF NOT EXISTS idx_quotes_v2_job ON quotes_v2(job_id);

    -- Quote Line Items
    CREATE TABLE IF NOT EXISTS quote_line_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_id TEXT NOT NULL REFERENCES quotes_v2(id),
        line_number INTEGER DEFAULT 0,
        item_type TEXT,
        item_style TEXT,
        description TEXT,
        room TEXT,
        width REAL,
        height REAL,
        depth REAL,
        dimension_unit TEXT DEFAULT 'in',
        fabric_name TEXT,
        fabric_code TEXT,
        fabric_width REAL,
        fabric_price_per_yard REAL,
        yards_needed REAL,
        yards_override INTEGER DEFAULT 0,
        fabric_total REAL,
        pattern_repeat REAL,
        lining_type TEXT,
        lining_yards REAL,
        lining_price_per_yard REAL,
        lining_cost REAL,
        labor_description TEXT,
        labor_hours REAL,
        labor_hours_override INTEGER DEFAULT 0,
        labor_rate REAL,
        labor_total REAL,
        hardware_description TEXT,
        hardware_cost REAL,
        materials_description TEXT,
        materials_cost REAL,
        quantity REAL DEFAULT 1.0,
        unit TEXT DEFAULT 'ea',
        unit_price REAL DEFAULT 0.0,
        subtotal REAL DEFAULT 0.0,
        manual_price_override REAL,
        price_is_manual INTEGER DEFAULT 0,
        category TEXT DEFAULT 'labor',
        drawing_id TEXT,
        drawing_svg TEXT,
        photo_ids_json TEXT,
        item_status TEXT DEFAULT 'pending',
        pricing_snapshot_json TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_qli_quote ON quote_line_items(quote_id);

    -- Quote Photos
    CREATE TABLE IF NOT EXISTS quote_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_id TEXT NOT NULL REFERENCES quotes_v2(id),
        line_item_id INTEGER REFERENCES quote_line_items(id),
        filename TEXT,
        filepath TEXT,
        file_type TEXT,
        description TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_qp_quote ON quote_photos(quote_id);

    -- Work Orders
    CREATE TABLE IF NOT EXISTS work_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_number TEXT UNIQUE,
        quote_id TEXT REFERENCES quotes_v2(id),
        job_id TEXT,
        customer_id TEXT,
        customer_name TEXT,
        business_unit TEXT DEFAULT 'workroom',
        assigned_to TEXT,
        priority TEXT DEFAULT 'normal',
        status TEXT DEFAULT 'pending',
        due_date TEXT,
        instructions TEXT,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_wo_quote ON work_orders(quote_id);
    CREATE INDEX IF NOT EXISTS idx_wo_status ON work_orders(status);

    -- Work Order Items
    CREATE TABLE IF NOT EXISTS work_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id INTEGER NOT NULL REFERENCES work_orders(id),
        quote_line_item_id INTEGER REFERENCES quote_line_items(id),
        item_type TEXT,
        description TEXT,
        room TEXT,
        dimensions TEXT,
        fabric_info TEXT,
        quantity REAL DEFAULT 1.0,
        production_status TEXT DEFAULT 'pending',
        special_instructions TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_woi_wo ON work_order_items(work_order_id);

    -- Production Log
    CREATE TABLE IF NOT EXISTS production_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id INTEGER REFERENCES work_orders(id),
        work_order_item_id INTEGER REFERENCES work_order_items(id),
        from_status TEXT,
        to_status TEXT,
        changed_by TEXT DEFAULT 'system',
        notes TEXT,
        photo_path TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_pl_wo ON production_log(work_order_id);

    -- Payments v2
    CREATE TABLE IF NOT EXISTS payments_v2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_number TEXT UNIQUE,
        invoice_id TEXT,
        customer_id TEXT,
        quote_id TEXT,
        amount REAL NOT NULL,
        payment_method TEXT,
        payment_reference TEXT,
        payment_type TEXT DEFAULT 'payment',
        status TEXT DEFAULT 'completed',
        account_code TEXT,
        notes TEXT,
        payment_date TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_pv2_invoice ON payments_v2(invoice_id);
    CREATE INDEX IF NOT EXISTS idx_pv2_customer ON payments_v2(customer_id);

    -- Chart of Accounts
    CREATE TABLE IF NOT EXISTS chart_of_accounts (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    logger.info("All unified business tables created successfully")


# ── Quote JSON Migration ───────────────────────────────────────

def _is_actual_quote(data: dict) -> bool:
    """Filter out verification files and non-quote JSONs."""
    if 'verified_at' in data and 'checks' in data and 'customer_name' not in data:
        return False
    if not any(k in data for k in ['customer_name', 'customer_email', 'tiers', 'line_items', 'items', 'rooms', 'project_name']):
        return False
    return True


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _extract_line_items(data: dict) -> list:
    """Extract line items from various JSON formats."""
    items = []

    # Direct line_items
    for li in data.get('line_items', []):
        if isinstance(li, dict):
            items.append(li)

    # items key (different format)
    if not items:
        for li in data.get('items', []):
            if isinstance(li, dict):
                items.append(li)

    # rooms → windows/upholstery
    for room in data.get('rooms', []):
        if not isinstance(room, dict):
            continue
        room_name = room.get('name', room.get('room', ''))
        for w in room.get('windows', []):
            if isinstance(w, dict):
                item = {**w, 'room': room_name, 'item_type': w.get('type', w.get('treatment_type', 'drapery'))}
                items.append(item)
        for u in room.get('upholstery', []):
            if isinstance(u, dict):
                item = {**u, 'room': room_name, 'item_type': u.get('type', 'upholstery')}
                items.append(item)

    # tiers → items (take first tier as primary)
    if not items and isinstance(data.get('tiers'), dict):
        tiers = data['tiers']
        # Try tier keys like 'good', 'better', 'best' or 'A', 'B', 'C'
        first_tier = None
        for k in ['good', 'A', 'standard', 'basic']:
            if k in tiers:
                first_tier = tiers[k]
                break
        if first_tier is None and tiers:
            first_tier = next(iter(tiers.values()))
        if isinstance(first_tier, dict):
            for li in first_tier.get('items', first_tier.get('line_items', [])):
                if isinstance(li, dict):
                    items.append(li)
        elif isinstance(first_tier, list):
            for li in first_tier:
                if isinstance(li, dict):
                    items.append(li)

    return items


def migrate_quotes_json_to_sql(conn: sqlite3.Connection) -> dict:
    """Migrate all JSON quote files into quotes_v2 + quote_line_items.
    Returns migration stats."""

    stats = {'total_files': 0, 'migrated': 0, 'skipped': 0, 'failed': [],
             'items_migrated': 0, 'already_exists': 0}

    json_files = sorted(glob.glob(os.path.join(QUOTES_DIR, '*.json')))

    for fpath in json_files:
        fname = os.path.basename(fpath)
        if fname.startswith('_') or '_verification' in fname:
            continue

        try:
            with open(fpath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            stats['failed'].append((fname, str(e)))
            continue

        if not _is_actual_quote(data):
            stats['skipped'] += 1
            continue

        stats['total_files'] += 1
        quote_id = data.get('id', fname.replace('.json', ''))

        # Check if already migrated
        existing = conn.execute("SELECT id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if existing:
            stats['already_exists'] += 1
            continue

        # Handle duplicate quote numbers — append ID suffix
        quote_number = data.get('quote_number', '')
        if quote_number:
            dup = conn.execute("SELECT id FROM quotes_v2 WHERE quote_number = ?", (quote_number,)).fetchone()
            if dup:
                quote_number = f"{quote_number}-{quote_id[:4]}"

        # Extract fields
        customer_name = data.get('customer_name', '')
        customer_email = data.get('customer_email', '')
        customer_phone = data.get('customer_phone', '')
        customer_address = data.get('customer_address', '')

        # Deposit handling
        dep = data.get('deposit', {})
        if isinstance(dep, dict):
            deposit_percent = _safe_float(dep.get('deposit_percent', 50))
            deposit_required = _safe_float(dep.get('deposit_amount', 0))
        else:
            deposit_percent = 50.0
            deposit_required = 0.0

        subtotal = _safe_float(data.get('subtotal', 0))
        tax_rate = _safe_float(data.get('tax_rate', 0))
        tax_amount = _safe_float(data.get('tax_amount', 0))
        discount_amount = _safe_float(data.get('discount_amount', 0))
        total = _safe_float(data.get('total', 0))
        balance_due = total - _safe_float(data.get('deposit_paid', 0))

        try:
            conn.execute("""
                INSERT OR IGNORE INTO quotes_v2 (
                    id, quote_number, customer_name, customer_email, customer_phone,
                    customer_address, business_unit, job_id, project_name, project_description,
                    status, subtotal, tax_rate, tax_amount, discount_amount, discount_type,
                    total, deposit_percent, deposit_required, deposit_paid, balance_due,
                    valid_days, expires_at, terms, source, source_json_path,
                    notes, max_analysis, pricing_mode, location, lining_preference,
                    rooms_json, tiers_json, design_proposals_json, ai_mockups_json,
                    ai_outlines_json, photos_json, measurements_json, metadata_json,
                    sent_at, accepted_at, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                quote_id,
                quote_number,
                customer_name,
                customer_email or '',
                customer_phone or '',
                customer_address or '',
                data.get('business_unit', 'workroom'),
                data.get('job_id'),
                data.get('project_name', ''),
                data.get('project_description', ''),
                data.get('status', 'draft'),
                subtotal,
                tax_rate,
                tax_amount,
                discount_amount,
                data.get('discount_type', 'dollar'),
                total,
                deposit_percent,
                deposit_required,
                0.0,  # deposit_paid
                balance_due,
                int(data.get('valid_days', 30)),
                data.get('expires_at'),
                data.get('terms', ''),
                data.get('source', 'migrated'),
                fpath,
                data.get('notes', ''),
                data.get('max_analysis', ''),
                data.get('pricing_mode', ''),
                data.get('location', ''),
                data.get('lining_preference', ''),
                json.dumps(data.get('rooms', []), default=str) if data.get('rooms') else None,
                json.dumps(data.get('tiers', {}), default=str) if data.get('tiers') else None,
                json.dumps(data.get('design_proposals', []), default=str) if data.get('design_proposals') else None,
                json.dumps(data.get('ai_mockups', []), default=str) if data.get('ai_mockups') else None,
                json.dumps(data.get('ai_outlines', []), default=str) if data.get('ai_outlines') else None,
                json.dumps(data.get('photos', []), default=str) if data.get('photos') else None,
                json.dumps(data.get('measurements', {}), default=str) if data.get('measurements') else None,
                json.dumps({k: v for k, v in data.items() if k not in {
                    'id','quote_number','customer_name','customer_email','customer_phone',
                    'customer_address','business_unit','job_id','project_name','project_description',
                    'status','subtotal','tax_rate','tax_amount','discount_amount','discount_type',
                    'total','deposit','valid_days','expires_at','terms','source','notes',
                    'max_analysis','pricing_mode','location','lining_preference','rooms','tiers',
                    'design_proposals','ai_mockups','ai_outlines','photos','measurements',
                    'line_items','items','sent_at','accepted_at','created_at','updated_at'
                }}, default=str),
                data.get('sent_at'),
                data.get('accepted_at'),
                data.get('created_at', datetime.now(tz=None).isoformat()),
                data.get('updated_at', datetime.now(tz=None).isoformat()),
            ))

            # Migrate line items
            line_items = _extract_line_items(data)
            for idx, li in enumerate(line_items):
                conn.execute("""
                    INSERT INTO quote_line_items (
                        quote_id, line_number, item_type, item_style, description,
                        room, width, height, depth, dimension_unit,
                        fabric_name, fabric_price_per_yard, yards_needed, fabric_total,
                        lining_type, lining_yards, lining_cost,
                        labor_description, labor_hours, labor_rate, labor_total,
                        hardware_description, hardware_cost,
                        quantity, unit, unit_price, subtotal, category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    quote_id,
                    idx + 1,
                    li.get('type', li.get('item_type', li.get('treatment_type', ''))),
                    li.get('style', li.get('construction', '')),
                    li.get('description', li.get('name', '')),
                    li.get('room', ''),
                    _safe_float(li.get('width', li.get('dimensions', {}).get('width') if isinstance(li.get('dimensions'), dict) else None)),
                    _safe_float(li.get('height', li.get('dimensions', {}).get('height') if isinstance(li.get('dimensions'), dict) else None)),
                    _safe_float(li.get('depth', li.get('dimensions', {}).get('depth') if isinstance(li.get('dimensions'), dict) else None)),
                    li.get('unit', 'in') if li.get('unit') in ('in', 'ft', 'cm', 'm') else 'in',
                    li.get('fabric_name', li.get('fabric_id', '')),
                    _safe_float(li.get('fabric_price_per_yard', li.get('rate', 0))),
                    _safe_float(li.get('yardage', li.get('yards_needed', 0))),
                    _safe_float(li.get('fabric_total', 0)),
                    li.get('lining_type', ''),
                    _safe_float(li.get('lining_yards', 0)),
                    _safe_float(li.get('lining_cost', 0)),
                    li.get('labor_description', ''),
                    _safe_float(li.get('labor_hours', 0)),
                    _safe_float(li.get('labor_rate', li.get('rate', 0))),
                    _safe_float(li.get('labor_total', 0)),
                    li.get('hardware_description', ''),
                    _safe_float(li.get('hardware_cost', 0)),
                    _safe_float(li.get('quantity', 1)),
                    li.get('unit', 'ea') if li.get('unit') not in ('in', 'ft', 'cm', 'm') else 'ea',
                    _safe_float(li.get('unit_price', li.get('rate', li.get('amount', li.get('price', li.get('total', 0)))))),
                    _safe_float(li.get('amount', li.get('total', li.get('price', _safe_float(li.get('quantity', 1)) * _safe_float(li.get('rate', li.get('unit_price', 0))))))),
                    li.get('category', 'labor'),
                ))
                stats['items_migrated'] += 1

            # Log to audit
            conn.execute("""
                INSERT INTO financial_audit_log (entity_type, entity_id, action, field_name, new_value, changed_by, reason)
                VALUES ('quote', ?, 'migrated', 'source_json', ?, 'migration', 'JSON to SQL migration')
            """, (quote_id, fname))

            stats['migrated'] += 1

        except Exception as e:
            stats['failed'].append((fname, str(e)))
            logger.error(f"Failed to migrate {fname}: {e}")

    conn.commit()
    return stats


# ── Seed Chart of Accounts ─────────────────────────────────────

def seed_chart_of_accounts(conn: sqlite3.Connection):
    """Seed 24 workroom-specific accounts."""
    accounts = [
        # Assets (1xxx)
        ('1000', 'Cash', 'asset', 'current_asset', 'Operating cash account'),
        ('1100', 'Accounts Receivable', 'asset', 'current_asset', 'Customer balances owed'),
        ('1200', 'Inventory - Fabric', 'asset', 'current_asset', 'Fabric stock on hand'),
        ('1300', 'Inventory - Hardware', 'asset', 'current_asset', 'Hardware and supplies'),
        # Liabilities (2xxx)
        ('2000', 'Accounts Payable', 'liability', 'current_liability', 'Vendor balances owed'),
        ('2100', 'Sales Tax Payable', 'liability', 'current_liability', 'Collected sales tax'),
        ('2200', 'Customer Deposits', 'liability', 'current_liability', 'Deposits received not yet earned'),
        # Revenue (4xxx)
        ('4000', 'Drapery Revenue', 'revenue', 'revenue', 'Drapery fabrication and installation'),
        ('4100', 'Upholstery Revenue', 'revenue', 'revenue', 'Upholstery and re-upholstery'),
        ('4200', 'Millwork Revenue', 'revenue', 'revenue', 'CNC and woodwork (WoodCraft)'),
        ('4300', 'Installation Revenue', 'revenue', 'revenue', 'Installation labor'),
        ('4400', 'Retail Revenue', 'revenue', 'revenue', 'Retail product sales'),
        ('4500', 'Design Consultation Revenue', 'revenue', 'revenue', 'Design consultation fees'),
        # COGS (5xxx)
        ('5000', 'Fabric Cost', 'expense', 'cogs', 'Fabric purchased for jobs'),
        ('5100', 'Lining Cost', 'expense', 'cogs', 'Lining materials'),
        ('5200', 'Hardware Cost', 'expense', 'cogs', 'Rods, rings, tracks, hardware'),
        ('5300', 'Subcontractor Cost', 'expense', 'cogs', 'Outsourced labor'),
        ('5400', 'Shipping Cost', 'expense', 'cogs', 'Inbound freight and shipping'),
        # Operating Expenses (6xxx)
        ('6000', 'Rent', 'expense', 'opex', 'Shop/studio rent'),
        ('6100', 'Utilities', 'expense', 'opex', 'Electric, water, internet'),
        ('6200', 'Insurance', 'expense', 'opex', 'Business insurance'),
        ('6300', 'Vehicle', 'expense', 'opex', 'Vehicle and fuel'),
        ('6400', 'Marketing', 'expense', 'opex', 'Advertising, campaigns, LeadForge'),
        ('6500', 'Software', 'expense', 'opex', 'Software subscriptions and tools'),
        ('6600', 'Office Supplies', 'expense', 'opex', 'Office and shop supplies'),
        ('6700', 'Professional Services', 'expense', 'opex', 'Legal, accounting, consulting'),
    ]

    for code, name, acct_type, category, desc in accounts:
        conn.execute("""
            INSERT OR IGNORE INTO chart_of_accounts (code, name, type, category, description)
            VALUES (?, ?, ?, ?, ?)
        """, (code, name, acct_type, category, desc))

    conn.commit()
    logger.info(f"Seeded {len(accounts)} chart of accounts entries")


# ── Run All Migrations ─────────────────────────────────────────

def run_all_migrations():
    """Run all migrations. Called on startup or manually."""
    conn = get_conn()
    try:
        # Backup check
        backup_path = os.path.expanduser(
            f"~/empire-repo/backend/data/empire_pre_block1_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
        )
        if not any('empire_pre_' in f for f in os.listdir(os.path.dirname(DB_PATH))):
            import shutil
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"Backup created: {backup_path}")

        # Create tables
        create_all_tables(conn)

        # Migrate quotes
        stats = migrate_quotes_json_to_sql(conn)

        # Seed chart of accounts
        seed_chart_of_accounts(conn)

        # Verify
        q_count = conn.execute("SELECT COUNT(*) FROM quotes_v2").fetchone()[0]
        li_count = conn.execute("SELECT COUNT(*) FROM quote_line_items").fetchone()[0]
        audit_count = conn.execute("SELECT COUNT(*) FROM financial_audit_log").fetchone()[0]
        coa_count = conn.execute("SELECT COUNT(*) FROM chart_of_accounts").fetchone()[0]

        print(f"\n{'='*60}")
        print(f"MIGRATION COMPLETE")
        print(f"{'='*60}")
        print(f"  JSON quote files found: {stats['total_files']}")
        print(f"  Migrated to SQL:        {stats['migrated']}")
        print(f"  Already existed:        {stats['already_exists']}")
        print(f"  Skipped (non-quote):    {stats['skipped']}")
        print(f"  Failed:                 {len(stats['failed'])}")
        print(f"  Line items migrated:    {stats['items_migrated']}")
        print(f"  quotes_v2 rows:         {q_count}")
        print(f"  quote_line_items rows:  {li_count}")
        print(f"  audit_log entries:      {audit_count}")
        print(f"  chart_of_accounts:      {coa_count}")
        if stats['failed']:
            print(f"\n  FAILED FILES:")
            for fname, err in stats['failed']:
                print(f"    {fname}: {err}")
        print(f"{'='*60}\n")

        return stats
    finally:
        conn.close()


if __name__ == "__main__":
    run_all_migrations()
