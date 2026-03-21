"""
Unified cross-channel message store.
All messages from Web, Telegram, and CC go into ONE shared SQLite table.
"""
import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("max.unified_messages")

DB_PATH = Path(os.path.expanduser("~/empire-repo/backend/data/brain/unified_messages.db"))


class UnifiedMessageStore:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unified_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                tool_results TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_conv ON unified_messages(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_channel ON unified_messages(channel)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_created ON unified_messages(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_channel_created ON unified_messages(channel, created_at)")
        conn.commit()
        conn.close()
        logger.info(f"Unified message store initialized at {DB_PATH}")

    def add_message(self, conversation_id: str, channel: str, role: str, content: str,
                    model: str = None, tool_results: list = None, metadata: dict = None):
        """Add a message from any channel."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO unified_messages (conversation_id, channel, role, content, model, tool_results, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (conversation_id, channel, role, content, model,
             json.dumps(tool_results) if tool_results else None,
             json.dumps(metadata) if metadata else None)
        )
        conn.commit()
        conn.close()

    def get_conversation(self, conversation_id: str, limit: int = 50) -> list[dict]:
        """Get all messages for a conversation."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM unified_messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_recent_by_channel(self, channel: str, limit: int = 4, hours: int = 2) -> list[dict]:
        """Get recent messages from a specific channel (for cross-channel context)."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM unified_messages WHERE channel = ? AND created_at > ? ORDER BY created_at DESC LIMIT ?",
            (channel, cutoff, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]  # chronological order

    def get_cross_channel_context(self, exclude_channel: str = None, limit_per_channel: int = 4, hours: int = 2) -> dict[str, list[dict]]:
        """Get recent messages from ALL channels for cross-channel context injection."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM unified_messages WHERE created_at > ? ORDER BY created_at DESC",
            (cutoff,)
        ).fetchall()
        conn.close()

        by_channel = {}
        for r in rows:
            ch = r["channel"]
            if ch == exclude_channel:
                continue
            if ch not in by_channel:
                by_channel[ch] = []
            if len(by_channel[ch]) < limit_per_channel:
                by_channel[ch].append(dict(r))

        # Reverse each channel's messages to chronological order
        for ch in by_channel:
            by_channel[ch] = list(reversed(by_channel[ch]))

        return by_channel

    def search_messages(self, query: str, channel: str = None, limit: int = 20) -> list[dict]:
        """Search across all channels."""
        conn = self._get_conn()
        if channel:
            rows = conn.execute(
                "SELECT * FROM unified_messages WHERE channel = ? AND content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (channel, f"%{query}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM unified_messages WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Get message counts by channel."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT channel, COUNT(*) as count FROM unified_messages GROUP BY channel"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM unified_messages").fetchone()[0]
        conn.close()
        return {"total": total, "by_channel": {r["channel"]: r["count"] for r in rows}}

    def migrate_json_chats(self):
        """One-time migration: import existing JSON chat files into unified store."""
        chats_dir = Path(os.path.expanduser("~/empire-repo/backend/data/chats"))
        migrated = 0

        for channel_dir in ["founder", "telegram"]:
            channel_path = chats_dir / channel_dir
            if not channel_path.exists():
                continue

            channel_name = "web" if channel_dir == "founder" else "telegram"

            for chat_file in channel_path.glob("*.json"):
                try:
                    with open(chat_file) as f:
                        data = json.load(f)

                    conv_id = data.get("id", chat_file.stem)
                    messages = data.get("messages", [])

                    if not messages:
                        continue

                    # Check if already migrated
                    conn = self._get_conn()
                    existing = conn.execute(
                        "SELECT COUNT(*) FROM unified_messages WHERE conversation_id = ?",
                        (conv_id,)
                    ).fetchone()[0]

                    if existing > 0:
                        conn.close()
                        continue

                    # Get file modification time for approximate timestamps
                    file_mtime = datetime.fromtimestamp(chat_file.stat().st_mtime)

                    for i, msg in enumerate(messages):
                        role = msg.get("role", "user")
                        content = msg.get("content", "")

                        if not content:
                            continue

                        # Use message timestamp if available, else estimate from file mtime
                        timestamp = msg.get("timestamp", "")
                        created = timestamp if timestamp and "T" in timestamp else (file_mtime - timedelta(minutes=len(messages) - i)).isoformat()

                        conn.execute(
                            "INSERT INTO unified_messages (conversation_id, channel, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                            (conv_id, channel_name, role, content, created)
                        )

                    conn.commit()
                    conn.close()
                    migrated += 1

                except Exception as e:
                    logger.warning(f"Failed to migrate {chat_file}: {e}")

        logger.info(f"Migrated {migrated} chat files to unified store")
        return migrated


# Singleton
unified_store = UnifiedMessageStore()

# Auto-migrate on first import (idempotent — checks for existing data)
try:
    unified_store.migrate_json_chats()
except Exception as e:
    logger.warning(f"Migration failed (will retry next restart): {e}")
