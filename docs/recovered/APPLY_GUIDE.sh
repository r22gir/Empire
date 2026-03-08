#!/usr/bin/env bash
# ============================================================
# MAX Memory Unification — Manual Apply Guide
# ============================================================
# 
# DO NOT run this script directly. Read each step and apply
# the changes manually or with Claude Code ONE AT A TIME.
#
# Back up first:
#   cp /data/Empire/backend/app/services/max/brain/memory_store.py ~/Empire/backend/data/brain/memory_store.py.bak
#   cp /data/Empire/backend/app/services/max/brain/conversation_tracker.py ~/Empire/backend/data/brain/conversation_tracker.py.bak
#
# ============================================================

echo "This is a GUIDE, not a script to run."
echo "Read the steps below and apply them carefully."
echo ""

cat << 'GUIDE'

STEP 1: BACKUP
──────────────
cp /data/Empire/backend/app/services/max/brain/memory_store.py \
   /data/Empire/backend/app/services/max/brain/memory_store.py.bak

cp /data/Empire/backend/app/services/max/brain/conversation_tracker.py \
   /data/Empire/backend/app/services/max/brain/conversation_tracker.py.bak


STEP 2: EDIT memory_store.py
─────────────────────────────
Open: /data/Empire/backend/app/services/max/brain/memory_store.py

A) Find the end of SCHEMA_SQL (the line with just:  """  after the tasks table)
   ADD this BEFORE that closing triple-quote:

-- Unified conversation history (cross-platform)
CREATE TABLE IF NOT EXISTS unified_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'web',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_unified_conv ON unified_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_unified_created ON unified_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_unified_source ON unified_messages(source);


B) Find the _update_access method at the bottom of the MemoryStore class.
   ADD these 3 methods AFTER _update_access (still inside the class):

    # ── Unified Conversation History ──────────────────────────

    def add_unified_message(self, conversation_id, role, content, source="web"):
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO unified_messages (conversation_id, source, role, content) VALUES (?, ?, ?, ?)",
                (conversation_id, source, role, content),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Failed to save unified message: {e}")
        finally:
            conn.close()

    def get_unified_history(self, conversation_id=None, limit=40, source=None):
        conn = self._conn()
        conditions, params = [], []
        if conversation_id:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)
        if source:
            conditions.append("source = ?")
            params.append(source)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            f"SELECT conversation_id, source, role, content, created_at "
            f"FROM unified_messages{where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    def get_recent_cross_platform_context(self, limit=20):
        conn = self._conn()
        rows = conn.execute(
            "SELECT conversation_id, source, role, content, created_at "
            "FROM unified_messages ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]


C) Add this import at the top of memory_store.py (after the existing imports):
   
   import logging
   logger = logging.getLogger("max.brain.memory")

   (Check if logging is already imported — if so, just add the logger line)


STEP 3: EDIT conversation_tracker.py
──────────────────────────────────────
Open: /data/Empire/backend/app/services/max/brain/conversation_tracker.py

A) REPLACE the add_message method with:

    def add_message(self, conversation_id: str, role: str, content: str):
        if conversation_id not in self.active_conversations:
            self.active_conversations[conversation_id] = []
        self.active_conversations[conversation_id].append(
            {"role": role, "content": content}
        )
        # Persist to unified cross-platform history
        source = "telegram" if conversation_id.startswith("telegram-") else "web"
        try:
            self.memory.add_unified_message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                source=source,
            )
        except Exception as e:
            logger.warning(f"Unified history write failed (non-fatal): {e}")

B) ADD this method at the bottom of the class (after get_active_count):

    def get_cross_platform_context(self, limit: int = 20) -> list[dict]:
        try:
            messages = self.memory.get_recent_cross_platform_context(limit=limit)
            formatted = []
            for msg in messages:
                source_tag = f"[{msg['source'].upper()}]"
                formatted.append({
                    "role": msg["role"],
                    "content": f"{source_tag} {msg['content']}" if msg["role"] == "user" else msg["content"],
                    "source": msg["source"],
                    "timestamp": msg.get("created_at", ""),
                })
            return formatted
        except Exception as e:
            logger.warning(f"Cross-platform context retrieval failed: {e}")
            return []


STEP 4: TEST
────────────
# Restart the backend
cd /data/Empire/backend
# (however you normally restart — systemctl, pm2, or just kill and relaunch)

# Verify the table was created:
sqlite3 ~/Empire/backend/data/brain/memories.db ".tables"
# Should now show: unified_messages (among others)

# Send a message via Telegram, then check:
sqlite3 ~/Empire/backend/data/brain/memories.db "SELECT * FROM unified_messages ORDER BY created_at DESC LIMIT 5;"

# Send a message via web UI, then check again — both should appear


STEP 5: WIRE INTO SYSTEM PROMPT (after testing)
────────────────────────────────────────────────
Once Steps 2-4 work, share the contents of:
  cat /data/Empire/backend/app/services/max/brain/context_builder.py
  cat /data/Empire/backend/app/services/max/system_prompt.py

I'll give you the exact edit to make MAX actually READ the cross-platform
history and include it in responses.

GUIDE
