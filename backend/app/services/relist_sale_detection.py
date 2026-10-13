"""RelistApp Vendoo-style sale detection — sandbox only.

When a sandbox listing is marked sold, sibling listings (same source product,
other platforms) are queued for delist or auto-delisted inside the sandbox DB.

Guarantees:
- Never writes to ra_listings / ra_orders (live RelistApp tables).
- Never calls marketplace APIs.
- Owner-confirm defaults ON.
- Isolated SQLite file (EMPIRE_RELIST_SANDBOX_DB or <data>/relist_sandbox.db).
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from app.services.data_paths import data_root

SANDBOX_MODE = True  # This feature cannot leave sandbox in this release.


def sandbox_db_path() -> Path:
    override = os.getenv("EMPIRE_RELIST_SANDBOX_DB")
    if override:
        return Path(override)
    return data_root() / "relist_sandbox.db"


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = sandbox_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        _init(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ra_sbx_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            owner_confirm_required INTEGER NOT NULL DEFAULT 1,
            sandbox_mode INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT
        );
        INSERT OR IGNORE INTO ra_sbx_settings (id, owner_confirm_required, sandbox_mode)
        VALUES (1, 1, 1);

        CREATE TABLE IF NOT EXISTS ra_sbx_listings (
            id TEXT PRIMARY KEY,
            source_product_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            snapshot_from_listing_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            sold_at TEXT,
            delisted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS ra_sbx_sales (
            id TEXT PRIMARY KEY,
            listing_id TEXT NOT NULL,
            source_product_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            sale_price REAL DEFAULT 0,
            detected_at TEXT,
            note TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS ra_sbx_delist_events (
            id TEXT PRIMARY KEY,
            sale_id TEXT NOT NULL,
            listing_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            marketplace_write INTEGER NOT NULL DEFAULT 0,
            confirmed_by_owner INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            resolved_at TEXT
        );
        """
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row else None


def get_settings() -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM ra_sbx_settings WHERE id = 1").fetchone()
        data = _row(row) or {}
    return {
        "sandbox_mode": True,
        "owner_confirm_required": bool(data.get("owner_confirm_required", 1)),
        "live_marketplace_writes": False,
        "db": str(sandbox_db_path()),
        "note": "Sale detection is sandbox-only. Sibling delists never touch live marketplaces or ra_* tables.",
    }


def update_settings(owner_confirm_required: bool) -> dict[str, Any]:
    with _connect() as conn:
        conn.execute(
            "UPDATE ra_sbx_settings SET owner_confirm_required = ?, sandbox_mode = 1, updated_at = ? WHERE id = 1",
            (1 if owner_confirm_required else 0, _now()),
        )
    return get_settings()


def upsert_listing(
    *,
    source_product_id: str,
    platform: str,
    title: str = "",
    status: str = "active",
    listing_id: Optional[str] = None,
    snapshot_from_listing_id: Optional[int] = None,
) -> dict[str, Any]:
    lid = listing_id or uuid.uuid4().hex[:12]
    now = _now()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO ra_sbx_listings
               (id, source_product_id, platform, title, status, snapshot_from_listing_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 source_product_id = excluded.source_product_id,
                 platform = excluded.platform,
                 title = excluded.title,
                 status = excluded.status,
                 updated_at = excluded.updated_at
            """,
            (lid, str(source_product_id), platform, title, status, snapshot_from_listing_id, now, now),
        )
        row = conn.execute("SELECT * FROM ra_sbx_listings WHERE id = ?", (lid,)).fetchone()
    return _row(row)  # type: ignore[return-value]


def list_listings(source_product_id: Optional[str] = None) -> list[dict[str, Any]]:
    with _connect() as conn:
        if source_product_id:
            rows = conn.execute(
                "SELECT * FROM ra_sbx_listings WHERE source_product_id = ? ORDER BY created_at DESC",
                (str(source_product_id),),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM ra_sbx_listings ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def list_events(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM ra_sbx_delist_events ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_pending_confirmations() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT e.*, l.title, l.source_product_id
               FROM ra_sbx_delist_events e
               LEFT JOIN ra_sbx_listings l ON l.id = e.listing_id
               WHERE e.status = 'pending_owner'
               ORDER BY e.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def record_sale(
    listing_id: str,
    sale_price: float = 0.0,
    note: str = "",
) -> dict[str, Any]:
    """Mark a sandbox listing sold and delist (or queue) siblings."""
    settings = get_settings()
    confirm = bool(settings["owner_confirm_required"])
    now = _now()

    with _connect() as conn:
        listing = conn.execute("SELECT * FROM ra_sbx_listings WHERE id = ?", (listing_id,)).fetchone()
        if not listing:
            raise KeyError(f"Sandbox listing '{listing_id}' not found")

        sale_id = uuid.uuid4().hex[:12]
        conn.execute(
            """UPDATE ra_sbx_listings
               SET status = 'sold', sold_at = ?, updated_at = ?
               WHERE id = ?""",
            (now, now, listing_id),
        )
        conn.execute(
            """INSERT INTO ra_sbx_sales (id, listing_id, source_product_id, platform, sale_price, detected_at, note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sale_id, listing_id, listing["source_product_id"], listing["platform"], sale_price, now, note),
        )

        siblings = conn.execute(
            """SELECT * FROM ra_sbx_listings
               WHERE source_product_id = ?
                 AND id != ?
                 AND platform != ?
                 AND status IN ('active', 'listed')""",
            (listing["source_product_id"], listing_id, listing["platform"]),
        ).fetchall()

        events: list[dict[str, Any]] = []
        for sib in siblings:
            event_id = uuid.uuid4().hex[:12]
            if confirm:
                action = "awaiting_owner_confirm"
                status = "pending_owner"
                conn.execute(
                    """INSERT INTO ra_sbx_delist_events
                       (id, sale_id, listing_id, platform, action, status, marketplace_write, confirmed_by_owner, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)""",
                    (event_id, sale_id, sib["id"], sib["platform"], action, status, now),
                )
            else:
                action = "sandbox_auto_delist"
                status = "delisted_sandbox"
                conn.execute(
                    """UPDATE ra_sbx_listings
                       SET status = 'delisted', delisted_at = ?, updated_at = ?
                       WHERE id = ?""",
                    (now, now, sib["id"]),
                )
                conn.execute(
                    """INSERT INTO ra_sbx_delist_events
                       (id, sale_id, listing_id, platform, action, status, marketplace_write, confirmed_by_owner, created_at, resolved_at)
                       VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?)""",
                    (event_id, sale_id, sib["id"], sib["platform"], action, status, now, now),
                )
            events.append({
                "id": event_id,
                "listing_id": sib["id"],
                "platform": sib["platform"],
                "title": sib["title"],
                "action": action,
                "status": status,
                "marketplace_write": False,
            })

        sold = conn.execute("SELECT * FROM ra_sbx_listings WHERE id = ?", (listing_id,)).fetchone()

    return {
        "sandbox": True,
        "marketplace_write": False,
        "live_tables_written": False,
        "sale_id": sale_id,
        "sold_listing": dict(sold) if sold else None,
        "owner_confirm_required": confirm,
        "siblings": events,
        "message": (
            "Sale recorded in sandbox. Sibling delists waiting for owner confirm."
            if confirm and events
            else "Sale recorded in sandbox. Matching sibling listings delisted in sandbox only."
            if events
            else "Sale recorded in sandbox. No active sibling listings on other platforms."
        ),
    }


def resolve_confirmation(event_id: str, approve: bool) -> dict[str, Any]:
    now = _now()
    with _connect() as conn:
        event = conn.execute("SELECT * FROM ra_sbx_delist_events WHERE id = ?", (event_id,)).fetchone()
        if not event:
            raise KeyError(f"Delist event '{event_id}' not found")
        if event["status"] != "pending_owner":
            raise ValueError(f"Event '{event_id}' is not pending owner confirm")

        if approve:
            conn.execute(
                """UPDATE ra_sbx_listings
                   SET status = 'delisted', delisted_at = ?, updated_at = ?
                   WHERE id = ?""",
                (now, now, event["listing_id"]),
            )
            conn.execute(
                """UPDATE ra_sbx_delist_events
                   SET status = 'delisted_sandbox', action = 'owner_confirmed_sandbox_delist',
                       confirmed_by_owner = 1, resolved_at = ?
                   WHERE id = ?""",
                (now, event_id),
            )
            result_status = "delisted_sandbox"
        else:
            conn.execute(
                """UPDATE ra_sbx_delist_events
                   SET status = 'rejected', action = 'owner_rejected',
                       confirmed_by_owner = 1, resolved_at = ?
                   WHERE id = ?""",
                (now, event_id),
            )
            result_status = "rejected"

        updated = conn.execute("SELECT * FROM ra_sbx_delist_events WHERE id = ?", (event_id,)).fetchone()

    return {
        "sandbox": True,
        "marketplace_write": False,
        "event": dict(updated) if updated else None,
        "status": result_status,
    }


def snapshot_from_live_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy listing dicts into the sandbox. Caller supplies already-read rows.

    This function never queries ra_listings itself.
    """
    created = []
    for row in rows:
        source_id = row.get("source_product_id")
        platform = row.get("platform")
        if not source_id or not platform:
            continue
        created.append(
            upsert_listing(
                source_product_id=str(source_id),
                platform=str(platform),
                title=str(row.get("title") or ""),
                status=str(row.get("status") or "active"),
                snapshot_from_listing_id=int(row["id"]) if row.get("id") is not None else None,
            )
        )
    return created


def export_state() -> dict[str, Any]:
    return {
        "settings": get_settings(),
        "listings": list_listings(),
        "events": list_events(),
        "pending": list_pending_confirmations(),
        "sandbox": True,
    }
