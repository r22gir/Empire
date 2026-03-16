"""
Empire Task Engine — Database initialization.
Creates tables and seeds desk configs from desks.json.
Run once on first startup, safe to re-run (uses IF NOT EXISTS).
"""
import json
import os
import hashlib
import secrets
from pathlib import Path
from .database import get_db, DB_PATH

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

SCHEMA_SQL = """
-- Tasks: The core unit of work across all desks
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo', 'in_progress', 'waiting', 'done', 'cancelled')),
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('urgent', 'high', 'normal', 'low')),
    desk TEXT NOT NULL,
    assigned_to TEXT,
    created_by TEXT DEFAULT 'founder',
    due_date TEXT,
    tags TEXT,
    metadata TEXT,
    parent_task_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id)
);

-- Task comments/activity log
CREATE TABLE IF NOT EXISTS task_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Desk configurations
CREATE TABLE IF NOT EXISTS desk_configs (
    desk_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    system_prompt TEXT,
    tools TEXT,
    layout TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Quick contacts (for Clients, Contractors desks)
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('client', 'contractor', 'vendor', 'other')),
    phone TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Customers (consolidated from quotes)
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    company TEXT,
    type TEXT DEFAULT 'residential' CHECK (type IN ('residential', 'commercial', 'designer', 'contractor')),
    tags TEXT, -- JSON array
    notes TEXT,
    total_revenue REAL DEFAULT 0,
    lifetime_quotes INTEGER DEFAULT 0,
    source TEXT DEFAULT 'direct', -- direct, referral, website, marketplace
    business TEXT DEFAULT 'empire', -- empire, workroom, woodcraft
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    invoice_number TEXT UNIQUE,
    customer_id TEXT,
    quote_id TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'paid', 'partial', 'overdue', 'cancelled')),
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 0.06,
    tax_amount REAL DEFAULT 0,
    total REAL DEFAULT 0,
    amount_paid REAL DEFAULT 0,
    balance_due REAL DEFAULT 0,
    line_items TEXT, -- JSON array
    notes TEXT,
    terms TEXT DEFAULT 'Net 30',
    due_date TEXT,
    sent_at TEXT,
    paid_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    invoice_id TEXT,
    customer_id TEXT,
    amount REAL NOT NULL,
    method TEXT DEFAULT 'check' CHECK (method IN ('cash', 'check', 'card', 'zelle', 'venmo', 'wire', 'other')),
    reference TEXT, -- check number, transaction ID, etc.
    notes TEXT,
    payment_date TEXT DEFAULT (date('now')),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Expenses
CREATE TABLE IF NOT EXISTS expenses (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    category TEXT NOT NULL CHECK (category IN ('fabric', 'hardware', 'labor', 'shipping', 'rent', 'utilities', 'marketing', 'tools', 'vehicle', 'insurance', 'other')),
    vendor TEXT,
    description TEXT,
    amount REAL NOT NULL,
    receipt_path TEXT,
    expense_date TEXT DEFAULT (date('now')),
    created_at TEXT DEFAULT (datetime('now'))
);

-- Inventory items
CREATE TABLE IF NOT EXISTS inventory_items (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name TEXT NOT NULL,
    sku TEXT UNIQUE,
    category TEXT NOT NULL CHECK (category IN ('fabric', 'hardware', 'motors', 'lining', 'thread', 'trim', 'wood', 'tools', 'other')),
    quantity REAL DEFAULT 0,
    unit TEXT DEFAULT 'yards',
    min_stock REAL DEFAULT 0,
    cost_per_unit REAL DEFAULT 0,
    sell_price REAL DEFAULT 0,
    vendor TEXT,
    location TEXT,
    notes TEXT,
    business TEXT DEFAULT 'workroom' CHECK (business IN ('workroom', 'craftforge')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Vendors
CREATE TABLE IF NOT EXISTS vendors (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    account_number TEXT,
    lead_time_days INTEGER DEFAULT 7,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Jobs / Production
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    title TEXT NOT NULL,
    customer_id TEXT,
    quote_id TEXT,
    invoice_id TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'scheduled', 'in_progress', 'on_hold', 'completed', 'cancelled')),
    job_type TEXT DEFAULT 'fabrication' CHECK (job_type IN ('fabrication', 'installation', 'repair', 'consultation', 'delivery')),
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('urgent', 'high', 'normal', 'low')),
    assigned_to TEXT,
    scheduled_date TEXT,
    due_date TEXT,
    completed_date TEXT,
    estimated_hours REAL,
    actual_hours REAL,
    materials_cost REAL DEFAULT 0,
    labor_cost REAL DEFAULT 0,
    notes TEXT,
    address TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_tasks_desk ON tasks(desk);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_activity_task ON task_activity(task_id);
CREATE INDEX IF NOT EXISTS idx_contacts_type ON contacts(type);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items(category);
CREATE INDEX IF NOT EXISTS idx_inventory_business ON inventory_items(business);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_customer ON jobs(customer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON jobs(scheduled_date);

-- Access control: users
CREATE TABLE IF NOT EXISTS access_users (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('founder', 'admin', 'manager', 'operator', 'viewer')),
    telegram_chat_id TEXT UNIQUE,
    desk TEXT,
    pin_hash TEXT,
    failed_pin_attempts INTEGER DEFAULT 0,
    locked_until TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Access control: pending confirmation/PIN sessions
CREATE TABLE IF NOT EXISTS access_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_params TEXT,
    desk TEXT,
    channel TEXT,
    chat_id TEXT,
    level INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'confirmed', 'denied', 'expired')),
    expires_at TEXT NOT NULL,
    confirmed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES access_users(id)
);

-- Access control: audit trail
CREATE TABLE IF NOT EXISTS access_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    tool_name TEXT NOT NULL,
    level INTEGER,
    result TEXT NOT NULL,
    detail TEXT,
    channel TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_access_users_telegram ON access_users(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_access_sessions_chat ON access_sessions(chat_id, status);
CREATE INDEX IF NOT EXISTS idx_access_audit_user ON access_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_access_audit_created ON access_audit(created_at);
"""

DESKS_JSON_PATH = Path(__file__).resolve().parent.parent / "config" / "desks.json"


def init_database():
    """Create all tables and seed desk configs."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        print(f"✓ Task Engine database initialized at {DB_PATH}")

        # v6.0 Pipeline columns (additive migration — safe to re-run)
        _migrate_pipeline_columns(conn)

        # Access control tables migration
        _migrate_access_control(conn)

        # Seed desk configs from desks.json if table is empty
        count = conn.execute("SELECT COUNT(*) FROM desk_configs").fetchone()[0]
        if count == 0 and DESKS_JSON_PATH.exists():
            _seed_desks(conn)


def _migrate_pipeline_columns(conn):
    """Add pipeline columns to tasks table (v6.0). Safe to re-run."""
    migrations = [
        ("pipeline_id", "TEXT"),
        ("subtask_order", "INTEGER DEFAULT 0"),
        ("acceptance_criteria", "TEXT"),
        ("channel", "TEXT DEFAULT 'system'"),
        ("result_summary", "TEXT"),
        ("resume_state", "TEXT"),
    ]
    added = 0
    for col_name, col_type in migrations:
        try:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            added += 1
        except Exception:
            pass  # Column already exists
    if added:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_pipeline ON tasks(pipeline_id)")
        print(f"✓ Pipeline migration: added {added} column(s) to tasks table")


def _hash_pin(pin):
    if HAS_BCRYPT:
        return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{pin}".encode()).hexdigest()
    return f"sha256:{salt}:{h}"


def _migrate_access_control(conn):
    for table in ("access_users", "access_sessions", "access_audit"):
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone()
        if not exists:
            return

    count = conn.execute("SELECT COUNT(*) FROM access_users").fetchone()[0]
    if count == 0:
        founder_chat_id = os.environ.get("TELEGRAM_FOUNDER_CHAT_ID")
        if founder_chat_id:
            pin_hash = None
            founder_pin = os.environ.get("FOUNDER_PIN")
            if founder_pin:
                pin_hash = _hash_pin(founder_pin)
            conn.execute(
                """INSERT INTO access_users (name, role, telegram_chat_id, pin_hash)
                   VALUES (?, 'founder', ?, ?)""",
                ("Founder", founder_chat_id, pin_hash)
            )
            print(f"✓ Seeded founder access user (chat_id={founder_chat_id})")


def _seed_desks(conn):
    """Seed desk_configs table from desks.json."""
    with open(DESKS_JSON_PATH) as f:
        desks = json.load(f)

    for i, desk in enumerate(desks):
        conn.execute(
            """INSERT INTO desk_configs
               (desk_id, name, icon, color, system_prompt, tools, layout, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                desk["id"],
                desk["name"],
                desk.get("icon"),
                desk.get("color"),
                desk.get("systemPrompt"),
                json.dumps(desk.get("tools", [])),
                json.dumps(desk.get("widgets", [])),
                i,
            ),
        )
    print(f"✓ Seeded {len(desks)} desk configs from desks.json")


if __name__ == "__main__":
    init_database()
