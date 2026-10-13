"""Isolated supplier-cart / job-PO tables. Safe to re-run."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS supplier_carts (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    supplier_name TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'prepared'
        CHECK (status IN ('prepared', 'awaiting_owner', 'approved', 'rejected', 'po_created')),
    checked_out INTEGER NOT NULL DEFAULT 0,
    paid INTEGER NOT NULL DEFAULT 0,
    owner_yes INTEGER NOT NULL DEFAULT 0,
    live_charge INTEGER NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS supplier_cart_lines (
    id TEXT PRIMARY KEY,
    cart_id TEXT NOT NULL,
    title TEXT NOT NULL,
    qty TEXT NOT NULL DEFAULT '1',
    unit TEXT DEFAULT 'ea',
    sku TEXT DEFAULT '',
    note TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (cart_id) REFERENCES supplier_carts(id)
);

CREATE TABLE IF NOT EXISTS job_purchase_orders (
    id TEXT PRIMARY KEY,
    po_number TEXT UNIQUE NOT NULL,
    cart_id TEXT,
    job_id TEXT NOT NULL,
    supplier_name TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    owner_approved INTEGER NOT NULL DEFAULT 0,
    checked_out INTEGER NOT NULL DEFAULT 0,
    paid INTEGER NOT NULL DEFAULT 0,
    live_charge INTEGER NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (cart_id) REFERENCES supplier_carts(id)
);

CREATE INDEX IF NOT EXISTS idx_supplier_carts_job ON supplier_carts(job_id);
CREATE INDEX IF NOT EXISTS idx_supplier_cart_lines_cart ON supplier_cart_lines(cart_id);
CREATE INDEX IF NOT EXISTS idx_job_pos_job ON job_purchase_orders(job_id);
CREATE INDEX IF NOT EXISTS idx_job_pos_cart ON job_purchase_orders(cart_id);
"""
