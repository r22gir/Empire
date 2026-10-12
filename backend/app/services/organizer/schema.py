"""Additive SQLite migrations for the Empire Organizer. Safe to re-run."""

from __future__ import annotations

import sqlite3


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    names = set()
    for row in rows:
        names.add(row[1] if not isinstance(row, sqlite3.Row) else row["name"])
    return names


def _add_column(conn: sqlite3.Connection, table: str, name: str, decl: str) -> None:
    if name in _column_names(conn, table):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def migrate_organizer_tables(conn: sqlite3.Connection) -> None:
    """Create organizer tables and add columns on schedule_events. Additive only."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_resources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            availability_json TEXT,
            notes TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            source_id TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_assignments (
            id TEXT PRIMARY KEY,
            event_id TEXT,
            item_id TEXT,
            resource_id TEXT NOT NULL,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_items (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            job_id TEXT,
            customer_id TEXT,
            resource_id TEXT,
            due_at TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            followup_kind TEXT,
            phone TEXT,
            location_address TEXT,
            material_eta TEXT,
            order_ref TEXT,
            reminder_draft TEXT,
            outbound_blocked INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            schedule_event_id TEXT,
            created_by TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_ics_tokens (
            id TEXT PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            label TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_res_role ON organizer_resources(role)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_res_source ON organizer_resources(source, source_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_asg_event ON organizer_assignments(event_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_asg_item ON organizer_assignments(item_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_asg_res ON organizer_assignments(resource_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_items_job ON organizer_items(job_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_items_due ON organizer_items(due_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_items_kind ON organizer_items(kind)"
    )

    # schedule_events lives in init_db; only add columns if the table exists.
    tables = {
        r[0] if not isinstance(r, sqlite3.Row) else r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_day_plans (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL DEFAULT 'workroom',
            plan_date TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0,
            approved_at TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_captures (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL DEFAULT 'workroom',
            source TEXT NOT NULL,
            source_ref TEXT,
            filename TEXT,
            mime TEXT,
            bytes INTEGER,
            sha256 TEXT,
            relpath TEXT,
            job_id TEXT,
            resource_id TEXT,
            event_id TEXT,
            item_id TEXT,
            caption TEXT,
            public_url_blocked INTEGER NOT NULL DEFAULT 1,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_crew_tokens (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL DEFAULT 'workroom',
            resource_id TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            label TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_checkins (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL DEFAULT 'workroom',
            resource_id TEXT NOT NULL,
            event_id TEXT,
            item_id TEXT,
            kind TEXT NOT NULL,
            note TEXT,
            capture_id TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_spaces (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            slug TEXT NOT NULL,
            label TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'life',
            sort_order INTEGER NOT NULL DEFAULT 0,
            icon TEXT,
            accent_color TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_org_spaces_ed_slug ON organizer_spaces(edition, slug)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_usage (
            edition TEXT NOT NULL,
            day TEXT NOT NULL,
            items INTEGER NOT NULL DEFAULT 0,
            captures INTEGER NOT NULL DEFAULT 0,
            actions INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (edition, day)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_mail_state (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            source TEXT NOT NULL,
            message_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            snooze_until TEXT,
            space_id TEXT,
            job_id TEXT,
            resource_id TEXT,
            approval_id TEXT,
            item_id TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_org_mail_ed_src_id ON organizer_mail_state(edition, source, message_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_reminders (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            item_id TEXT,
            event_id TEXT,
            due_at TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            channel TEXT NOT NULL DEFAULT 'max',
            status TEXT NOT NULL DEFAULT 'pending',
            notified_at TEXT,
            notification_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_rem_due ON organizer_reminders(status, due_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_rem_item ON organizer_reminders(item_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_cap_job ON organizer_captures(job_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_cap_ed ON organizer_captures(edition)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_crew_tok ON organizer_crew_tokens(token)")

    if "schedule_events" in tables:
        _add_column(conn, "schedule_events", "phone", "TEXT")
        _add_column(conn, "schedule_events", "customer_id", "TEXT")
        _add_column(conn, "schedule_events", "event_kind", "TEXT")
        _add_column(conn, "schedule_events", "travel_minutes", "INTEGER")
        _add_column(conn, "schedule_events", "reminder_draft", "TEXT")
        _add_column(conn, "schedule_events", "all_day", "INTEGER DEFAULT 0")
        _add_column(conn, "schedule_events", "edition", "TEXT DEFAULT 'main'")
        _add_column(conn, "schedule_events", "space_id", "TEXT")

    for table in (
        "organizer_resources",
        "organizer_items",
        "organizer_assignments",
        "organizer_ics_tokens",
        "organizer_captures",
    ):
        try:
            _add_column(conn, table, "edition", "TEXT DEFAULT 'main'")
        except Exception:
            pass
        try:
            _add_column(conn, table, "space_id", "TEXT")
        except Exception:
            pass

    try:
        _add_column(conn, "organizer_spaces", "icon", "TEXT")
        _add_column(conn, "organizer_spaces", "accent_color", "TEXT")
    except Exception:
        pass
    for name, decl in (
        ("quote_id", "TEXT"),
        ("reminder_at", "TEXT"),
        ("capture_id", "TEXT"),
        ("project_id", "TEXT"),
        ("waiting_on", "TEXT"),
        ("nudge_after_days", "INTEGER"),
        ("last_nudge_at", "TEXT"),
        ("last_moved_at", "TEXT"),
        ("recurrence_freq", "TEXT"),
        ("template_id", "TEXT"),
        ("parent_id", "TEXT"),
        ("invoice_id", "TEXT"),
    ):
        try:
            _add_column(conn, "organizer_items", name, decl)
        except Exception:
            pass

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_suggestions (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            source TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            kind TEXT NOT NULL DEFAULT 'todo',
            space_id TEXT,
            job_id TEXT,
            quote_id TEXT,
            capture_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            payload_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_org_sug_ed_src ON organizer_suggestions(edition, source, source_ref)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_templates (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            space_id TEXT,
            slug TEXT NOT NULL,
            label TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'checklist',
            steps_json TEXT NOT NULL,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_org_tpl_ed_slug ON organizer_templates(edition, slug)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organizer_recurrence (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            item_id TEXT,
            template_id TEXT,
            freq TEXT NOT NULL DEFAULT 'weekly',
            next_due TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT
        )
        """
    )
