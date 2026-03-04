"""
Empire Task Engine — Database initialization.
Creates tables and seeds desk configs from desks.json.
Run once on first startup, safe to re-run (uses IF NOT EXISTS).
"""
import json
import os
from pathlib import Path
from .database import get_db, DB_PATH

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

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_tasks_desk ON tasks(desk);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_activity_task ON task_activity(task_id);
CREATE INDEX IF NOT EXISTS idx_contacts_type ON contacts(type);
"""

DESKS_JSON_PATH = Path(__file__).resolve().parent.parent / "config" / "desks.json"


def init_database():
    """Create all tables and seed desk configs."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        print(f"✓ Task Engine database initialized at {DB_PATH}")

        # Seed desk configs from desks.json if table is empty
        count = conn.execute("SELECT COUNT(*) FROM desk_configs").fetchone()[0]
        if count == 0 and DESKS_JSON_PATH.exists():
            _seed_desks(conn)


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
