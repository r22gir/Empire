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
from typing import Any, Optional

logger = logging.getLogger("max.unified_messages")

DB_PATH = Path(os.path.expanduser("~/empire-repo/backend/data/brain/unified_messages.db"))


class UnifiedMessageStore:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
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
                direction TEXT,
                sender TEXT,
                recipient TEXT,
                thread_id TEXT,
                source_message_id TEXT,
                subject TEXT,
                attachment_refs TEXT,
                extracted_content TEXT,
                summary TEXT,
                founder_verified INTEGER DEFAULT 0,
                linked_refs TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(unified_messages)").fetchall()}
        for name, ddl in {
            "direction": "TEXT",
            "sender": "TEXT",
            "recipient": "TEXT",
            "thread_id": "TEXT",
            "source_message_id": "TEXT",
            "subject": "TEXT",
            "attachment_refs": "TEXT",
            "extracted_content": "TEXT",
            "summary": "TEXT",
            "founder_verified": "INTEGER DEFAULT 0",
            "linked_refs": "TEXT",
        }.items():
            if name not in existing_cols:
                conn.execute(f"ALTER TABLE unified_messages ADD COLUMN {name} {ddl}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_conv ON unified_messages(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_channel ON unified_messages(channel)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_created ON unified_messages(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_channel_created ON unified_messages(channel, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_thread ON unified_messages(thread_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_um_direction ON unified_messages(direction)")
        conn.commit()
        conn.close()
        logger.info(f"Unified message store initialized at {self.db_path}")

    def add_message(self, conversation_id: str, channel: str, role: str, content: str,
                    model: str = None, tool_results: list = None, metadata: dict = None,
                    direction: str = None, sender: str = None, recipient: str = None,
                    thread_id: str = None, source_message_id: str = None, subject: str = None,
                    attachment_refs: list | dict | str = None, extracted_content: str = None,
                    summary: str = None, founder_verified: bool = False,
                    linked_refs: list | dict | str = None):
        """Add a message from any channel."""
        normalized_channel = self._normalize_channel(channel)
        direction = direction or ("outbound" if role == "assistant" else "inbound")
        sender = sender or ("MAX" if direction == "outbound" else ("Founder" if founder_verified else channel or "unknown"))
        recipient = recipient or ("Founder" if direction == "outbound" else "MAX")
        thread_id = thread_id or conversation_id
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO unified_messages
               (conversation_id, channel, role, content, model, tool_results, metadata,
                direction, sender, recipient, thread_id, source_message_id, subject,
                attachment_refs, extracted_content, summary, founder_verified, linked_refs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, normalized_channel, role, content, model,
             json.dumps(tool_results) if tool_results else None,
             json.dumps(metadata) if metadata else None,
             direction, sender, recipient, thread_id, source_message_id, subject,
             self._json_or_text(attachment_refs), extracted_content, summary,
             1 if founder_verified else 0, self._json_or_text(linked_refs))
        )
        conn.commit()
        conn.close()

    def _normalize_channel(self, channel: str | None) -> str:
        if channel in {"web", "web_cc", "dashboard"}:
            return "web_chat"
        return channel or "system"

    def _channel_aliases(self, channel: str | None) -> list[str]:
        normalized = self._normalize_channel(channel)
        if normalized == "web_chat":
            return ["web_chat", "web", "web_cc", "dashboard"]
        return [normalized]

    def _json_or_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value, default=str)

    def _decode_jsonish(self, value: Any) -> Any:
        if not value:
            return [] if value is None else value
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return value

    def _memory_row(self, row: sqlite3.Row) -> dict:
        data = dict(row)
        metadata = self._decode_jsonish(data.get("metadata")) or {}
        attachments = self._decode_jsonish(data.get("attachment_refs"))
        if not attachments and isinstance(metadata, dict):
            attachments = metadata.get("attachments") or metadata.get("attachment_refs") or []
            if metadata.get("image_filename"):
                attachments = list(attachments) if isinstance(attachments, list) else [attachments]
                attachments.append({"type": "upload", "ref": metadata.get("image_filename")})
        linked_refs = self._decode_jsonish(data.get("linked_refs")) or (metadata.get("linked_refs") if isinstance(metadata, dict) else None) or []
        body = data.get("content") or ""
        return {
            "id": str(data.get("id")),
            "channel": data.get("channel") or "system",
            "direction": data.get("direction") or ("outbound" if data.get("role") == "assistant" else "inbound"),
            "sender": data.get("sender") or ("MAX" if data.get("role") == "assistant" else "unknown"),
            "recipient": data.get("recipient") or ("Founder" if data.get("role") == "assistant" else "MAX"),
            "thread_id": data.get("thread_id") or data.get("conversation_id"),
            "conversation_id": data.get("conversation_id"),
            "source_message_id": data.get("source_message_id"),
            "subject": data.get("subject") or "",
            "body": body,
            "message_text": body,
            "attachment_refs": attachments or [],
            "extracted_content": data.get("extracted_content") or "",
            "summary": data.get("summary") or (body[:180] + ("..." if len(body) > 180 else "")),
            "created_at": data.get("created_at"),
            "founder_verified": bool(data.get("founder_verified")),
            "linked_refs": linked_refs,
            "model": data.get("model"),
            "role": data.get("role"),
            "metadata": metadata,
            "tool_results": self._decode_jsonish(data.get("tool_results")) or [],
        }

    def list_memory_bank(
        self,
        channel: str | None = None,
        query: str | None = None,
        thread_id: str | None = None,
        founder_only: bool = False,
        has_attachments: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        limit = max(1, min(limit, 500))
        clauses = []
        params: list[Any] = []
        if channel and channel != "all":
            if channel == "attachments":
                has_attachments = True
            else:
                aliases = self._channel_aliases(channel)
                clauses.append(f"channel IN ({','.join('?' for _ in aliases)})")
                params.extend(aliases)
        if query:
            like = f"%{query}%"
            clauses.append("(content LIKE ? OR subject LIKE ? OR summary LIKE ? OR extracted_content LIKE ?)")
            params.extend([like, like, like, like])
        if thread_id:
            clauses.append("(thread_id = ? OR conversation_id = ?)")
            params.extend([thread_id, thread_id])
        if founder_only:
            clauses.append("founder_verified = 1")
        if has_attachments:
            clauses.append("COALESCE(attachment_refs, '') <> ''")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        conn = self._get_conn()
        rows = conn.execute(
            f"SELECT * FROM unified_messages {where} ORDER BY datetime(created_at) DESC, id DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        conn.close()
        return [self._memory_row(r) for r in rows]

    def get_memory_threads(self, limit: int = 100) -> list[dict]:
        limit = max(1, min(limit, 500))
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT COALESCE(thread_id, conversation_id) AS thread_id,
                      MIN(created_at) AS created_at,
                      MAX(created_at) AS updated_at,
                      COUNT(*) AS message_count,
                      GROUP_CONCAT(DISTINCT channel) AS channels
                 FROM unified_messages
                GROUP BY COALESCE(thread_id, conversation_id)
                ORDER BY datetime(updated_at) DESC
                LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

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
        aliases = self._channel_aliases(channel)
        conn = self._get_conn()
        rows = conn.execute(
            f"""SELECT * FROM unified_messages
                WHERE channel IN ({','.join('?' for _ in aliases)})
                  AND datetime(created_at) > datetime(?)
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?""",
            (*aliases, cutoff, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]  # chronological order

    def get_cross_channel_context(self, exclude_channel: str = None, limit_per_channel: int = 4, hours: int = 2) -> dict[str, list[dict]]:
        """Get recent messages from ALL channels for cross-channel context injection."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        excluded_channels = set(self._channel_aliases(exclude_channel)) if exclude_channel else set()
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM unified_messages
               WHERE datetime(created_at) > datetime(?)
               ORDER BY datetime(created_at) DESC, id DESC""",
            (cutoff,)
        ).fetchall()
        conn.close()

        by_channel = {}
        for r in rows:
            ch = r["channel"]
            if ch in excluded_channels:
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
            aliases = self._channel_aliases(channel)
            rows = conn.execute(
                f"SELECT * FROM unified_messages WHERE channel IN ({','.join('?' for _ in aliases)}) AND content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (*aliases, f"%{query}%", limit)
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
