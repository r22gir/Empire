"""
Persistent memory store for MAX Brain.
SQLite-backed, lives on external drive for portability.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional
from .brain_config import get_db_path

SCHEMA_SQL = """
-- Core memories table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    subcategory TEXT,
    subject TEXT,
    content TEXT NOT NULL,
    source TEXT,
    importance INTEGER DEFAULT 5,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    expires_at TIMESTAMP,
    tags TEXT,
    related_ids TEXT,
    customer_id TEXT,
    conversation_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_subject ON memories(subject);
CREATE INDEX IF NOT EXISTS idx_memories_customer ON memories(customer_id);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags);

-- Conversation summaries
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_decisions TEXT,
    tasks_created TEXT,
    customers_mentioned TEXT,
    topics TEXT,
    mood TEXT,
    message_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer profiles
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    source TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT,
    preferences TEXT,
    total_revenue REAL DEFAULT 0,
    job_count INTEGER DEFAULT 0,
    first_contact TIMESTAMP,
    last_contact TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer interactions log
CREATE TABLE IF NOT EXISTS customer_interactions (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    type TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT,
    outcome TEXT,
    follow_up_date TIMESTAMP,
    follow_up_action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Business knowledge
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    business TEXT NOT NULL,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT,
    verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks and action items
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    assigned_to TEXT DEFAULT 'founder',
    customer_id TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    due_date TIMESTAMP,
    source TEXT,
    source_message TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class MemoryStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA_SQL)
        conn.close()

    def add_memory(
        self,
        category: str,
        content: str,
        subject: str = "",
        subcategory: str = "",
        importance: int = 5,
        source: str = "auto",
        tags: list = None,
        customer_id: str = None,
        conversation_id: str = None,
        expires_at: str = None,
    ) -> str:
        """Add a new memory. Returns memory ID."""
        memory_id = str(uuid.uuid4())[:8]
        conn = self._conn()
        conn.execute(
            """INSERT INTO memories
               (id, category, subcategory, subject, content,
                source, importance, tags, customer_id, conversation_id, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory_id, category, subcategory, subject, content,
                source, importance, json.dumps(tags or []),
                customer_id, conversation_id, expires_at,
            ),
        )
        conn.commit()
        conn.close()
        return memory_id

    def search_memories(
        self,
        query: str = None,
        category: str = None,
        customer_id: str = None,
        limit: int = 20,
        min_importance: int = 1,
    ) -> list[dict]:
        """Search memories by keyword, category, or customer."""
        conn = self._conn()
        conditions = ["importance >= ?"]
        params: list = [min_importance]

        if category:
            conditions.append("category = ?")
            params.append(category)
        if customer_id:
            conditions.append("customer_id = ?")
            params.append(customer_id)
        if query:
            conditions.append("(content LIKE ? OR subject LIKE ? OR tags LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q])

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM memories WHERE {where} ORDER BY importance DESC, created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()

        ids = [r["id"] for r in rows]
        if ids:
            self._update_access(ids)
        return [dict(r) for r in rows]

    def get_recent(self, category: str = None, limit: int = 10) -> list[dict]:
        """Get most recent memories."""
        conn = self._conn()
        if category:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_memory(self, memory_id: str, **kwargs) -> bool:
        """Update fields on an existing memory."""
        if not kwargs:
            return False
        conn = self._conn()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [memory_id]
        conn.execute(f"UPDATE memories SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", vals)
        conn.commit()
        conn.close()
        return True

    def delete_memory(self, memory_id: str) -> bool:
        conn = self._conn()
        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()
        return True

    def count(self, category: str = None) -> int:
        conn = self._conn()
        if category:
            row = conn.execute("SELECT COUNT(*) FROM memories WHERE category = ?", (category,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        conn.close()
        return row[0] if row else 0

    def save_conversation_summary(
        self,
        conversation_id: str,
        summary: str,
        key_decisions: list = None,
        tasks_created: list = None,
        customers_mentioned: list = None,
        topics: list = None,
        mood: str = "productive",
        message_count: int = 0,
    ) -> str:
        """Save a conversation summary."""
        summary_id = str(uuid.uuid4())[:8]
        date = datetime.now().strftime("%Y-%m-%d")
        conn = self._conn()
        conn.execute(
            """INSERT INTO conversation_summaries
               (id, conversation_id, date, summary, key_decisions, tasks_created,
                customers_mentioned, topics, mood, message_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                summary_id, conversation_id, date, summary,
                json.dumps(key_decisions or []),
                json.dumps(tasks_created or []),
                json.dumps(customers_mentioned or []),
                json.dumps(topics or []),
                mood, message_count,
            ),
        )
        conn.commit()
        conn.close()
        return summary_id

    def add_customer(self, name: str, **kwargs) -> str:
        """Add or update a customer profile."""
        customer_id = str(uuid.uuid4())[:8]
        conn = self._conn()
        # Check if customer exists by name
        existing = conn.execute("SELECT id FROM customers WHERE name = ?", (name,)).fetchone()
        if existing:
            conn.close()
            return existing["id"]
        cols = ["id", "name"] + list(kwargs.keys())
        vals = [customer_id, name] + list(kwargs.values())
        placeholders = ", ".join(["?"] * len(vals))
        conn.execute(f"INSERT INTO customers ({', '.join(cols)}) VALUES ({placeholders})", vals)
        conn.commit()
        conn.close()
        return customer_id

    def add_knowledge(self, business: str, category: str, key: str, value: str, source: str = "manual") -> str:
        """Add a business knowledge entry."""
        kid = str(uuid.uuid4())[:8]
        conn = self._conn()
        conn.execute(
            "INSERT INTO knowledge (id, business, category, key, value, source) VALUES (?, ?, ?, ?, ?, ?)",
            (kid, business, category, key, value, source),
        )
        conn.commit()
        conn.close()
        return kid

    def get_knowledge(self, business: str = None, category: str = None) -> list[dict]:
        """Retrieve business knowledge."""
        conn = self._conn()
        conditions, params = [], []
        if business:
            conditions.append("business = ?")
            params.append(business)
        if category:
            conditions.append("category = ?")
            params.append(category)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(f"SELECT * FROM knowledge{where} ORDER BY created_at DESC", params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _update_access(self, memory_ids: list):
        """Update access count and timestamp for retrieved memories."""
        if not memory_ids:
            return
        conn = sqlite3.connect(self.db_path)
        for mid in memory_ids:
            conn.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                (mid,),
            )
        conn.commit()
        conn.close()
