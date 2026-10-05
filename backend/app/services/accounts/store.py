"""SQLite store for the SocialForge account hub. No secrets in list rows."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.services.accounts.catalog import BUSINESSES, OWNER, PLATFORMS, provider_keys_ready


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def accounts_db_path() -> str:
    for key in ("EMPIRE_DB", "EMPIRE_TASK_DB"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    from app.services.data_paths import data_root
    return str(Path(data_root()) / "empire.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS online_accounts (
    id TEXT PRIMARY KEY,
    business_key TEXT NOT NULL,
    platform TEXT NOT NULL,
    kind TEXT NOT NULL,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    last_sync_at TEXT,
    auto_publish INTEGER NOT NULL DEFAULT 0,
    external_account_id TEXT,
    vault_secret_id TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(business_key, platform)
);

CREATE TABLE IF NOT EXISTS credential_vault (
    secret_id TEXT PRIMARY KEY,
    ciphertext TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    business_key TEXT NOT NULL,
    platform TEXT NOT NULL,
    code_verifier TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduled_posts (
    id TEXT PRIMARY KEY,
    business_key TEXT NOT NULL,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    media_url TEXT,
    scheduled_for TEXT,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    external_post_id TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or accounts_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _seed(conn)
    return conn


def _seed(conn: sqlite3.Connection) -> None:
    now = _now()
    for business_key, business_name in BUSINESSES:
        for spec in PLATFORMS:
            account_id = f"{business_key}:{spec.key}"
            conn.execute(
                """
                INSERT INTO online_accounts (
                    id, business_key, platform, kind, display_name, status,
                    owner, auto_publish, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'not_connected', ?, 0, ?)
                ON CONFLICT(business_key, platform) DO NOTHING
                """,
                (account_id, business_key, spec.key, spec.kind, f"{business_name} — {spec.label}", OWNER, now),
            )
    conn.execute(
        "INSERT INTO account_settings (key, value) VALUES ('publish_paused', '0') ON CONFLICT(key) DO NOTHING"
    )
    conn.commit()


def _status_for(spec, has_credentials: bool, stored: str) -> str:
    ready = provider_keys_ready(spec) if spec else None
    if ready is False:
        return "needs_keys"
    if has_credentials and ready is not False:
        return "connected"
    if spec and spec.oauth:
        return "not_connected"
    if stored in {"connected", "paused", "error"}:
        return stored
    return "not_connected"


def refresh_statuses(conn: sqlite3.Connection) -> None:
    from app.services.accounts.catalog import platform_spec
    rows = conn.execute("SELECT * FROM online_accounts").fetchall()
    now = _now()
    for row in rows:
        spec = platform_spec(row["platform"])
        status = _status_for(spec, bool(row["vault_secret_id"]), row["status"] or "")
        if status != row["status"]:
            conn.execute(
                "UPDATE online_accounts SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, row["id"]),
            )
    conn.commit()


def public_row(row: sqlite3.Row) -> dict:
    """Account fields safe for the frontend. Never includes a secret."""
    return {
        "id": row["id"],
        "business_key": row["business_key"],
        "platform": row["platform"],
        "kind": row["kind"],
        "display_name": row["display_name"],
        "status": row["status"],
        "owner": row["owner"],
        "last_sync_at": row["last_sync_at"],
        "auto_publish": bool(row["auto_publish"]),
        "has_credentials": bool(row["vault_secret_id"]),
        "external_account_id": row["external_account_id"] or "",
    }


def list_hub(conn: sqlite3.Connection) -> dict:
    refresh_statuses(conn)
    rows = conn.execute(
        "SELECT * FROM online_accounts ORDER BY business_key, kind, platform"
    ).fetchall()
    accounts = [public_row(row) for row in rows]
    return {
        "owner": OWNER,
        "businesses": [{"key": key, "name": name} for key, name in BUSINESSES],
        "accounts": accounts,
    }


def mark_connected(conn: sqlite3.Connection, business_key: str, platform: str, secret_id: str, external_id: str = "") -> None:
    now = _now()
    conn.execute(
        """
        UPDATE online_accounts
        SET vault_secret_id = ?, external_account_id = ?, last_sync_at = ?, updated_at = ?
        WHERE business_key = ? AND platform = ?
        """,
        (secret_id, external_id, now, now, business_key, platform),
    )
    conn.commit()


def set_auto_publish(conn: sqlite3.Connection, business_key: str, platform: str, enabled: bool) -> bool:
    cur = conn.execute(
        "UPDATE online_accounts SET auto_publish = ?, updated_at = ? WHERE business_key = ? AND platform = ?",
        (1 if enabled else 0, _now(), business_key, platform),
    )
    conn.commit()
    return cur.rowcount > 0


def publish_paused(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT value FROM account_settings WHERE key = 'publish_paused'").fetchone()
    return bool(row and row["value"] == "1")


def set_publish_paused(conn: sqlite3.Connection, paused: bool) -> None:
    conn.execute(
        "INSERT INTO account_settings (key, value) VALUES ('publish_paused', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("1" if paused else "0",),
    )
    conn.commit()
