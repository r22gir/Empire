"""
Persistent conversation mode tracker.
Modes: design, quote, general, support, code, review
Mode persists across turns. Changes only on high-confidence intent detection.
"""
import sqlite3, os
from datetime import datetime

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")

def _ensure_tables():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS conversation_modes (
        conversation_id TEXT PRIMARY KEY,
        current_mode TEXT DEFAULT 'general',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS max_mode_transitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        prior_mode TEXT,
        new_mode TEXT,
        trigger TEXT,
        user_message_excerpt TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

_ensure_tables()

MODE_KEYWORDS = {
    "design": ["draw", "design", "sketch", "render", "drawing", "shade", "drapery", "window treatment", "bench", "bookcase", "roman shade", "cornice"],
    "quote": ["quote", "price", "estimate", "cost", "how much", "pricing", "invoice", "proposal"],
    "code": ["code mode", "shell", "git", "deploy", "fix the", "patch", "debug", "heal yourself"],
    "support": ["help", "support", "issue", "broken", "not working"],
    "review": ["review", "check", "audit", "verify", "status", "what's done", "update", "newest"],
}

def detect_mode(user_message: str, current_mode: str) -> tuple:
    msg = user_message.lower().strip()
    scores = {}
    for mode, keywords in MODE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg)
        if score > 0:
            scores[mode] = score
    if not scores:
        return current_mode, 0.0, "no_keywords"
    best_mode = max(scores, key=scores.get)
    best_score = scores[best_mode]
    if best_score >= 2 or best_mode == "code":
        return best_mode, 0.9, f"keywords matched: {best_score}"
    if best_score == 1 and best_mode != current_mode:
        return best_mode, 0.6, f"weak signal: {best_mode}"
    return current_mode, 0.3, "staying in current mode"

def get_mode(conversation_id: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT current_mode FROM conversation_modes WHERE conversation_id = ?",
                       (conversation_id,)).fetchone()
    conn.close()
    return row[0] if row else "general"

def set_mode(conversation_id: str, new_mode: str, prior_mode: str, trigger: str, excerpt: str = ""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO conversation_modes (conversation_id, current_mode, updated_at)
        VALUES (?, ?, ?) ON CONFLICT(conversation_id) DO UPDATE SET current_mode=?, updated_at=?""",
        (conversation_id, new_mode, datetime.utcnow(), new_mode, datetime.utcnow()))
    conn.execute("""INSERT INTO max_mode_transitions (conversation_id, prior_mode, new_mode, trigger, user_message_excerpt)
        VALUES (?, ?, ?, ?, ?)""", (conversation_id, prior_mode, new_mode, trigger, excerpt[:200]))
    conn.commit()
    conn.close()

def process_mode(conversation_id: str, user_message: str) -> str:
    current = get_mode(conversation_id)
    new_mode, confidence, trigger = detect_mode(user_message, current)
    if new_mode != current and confidence >= 0.6:
        set_mode(conversation_id, new_mode, current, trigger, user_message)
        return new_mode
    return current

MODE_INSTRUCTIONS = {
    "design": "DESIGN MODE: Focus on drawings, dimensions, fabric, visual output. Do NOT auto-quote unless explicitly asked.",
    "quote": "QUOTE MODE: Focus on pricing, estimates, materials, quote assembly.",
    "code": "CODE MODE: Execute code tasks, read files, run commands. Full founder access.",
    "support": "SUPPORT MODE: Help with issues, troubleshoot, explain.",
    "review": "REVIEW MODE: Show status, updates, audit results.",
    "general": "GENERAL MODE: Normal conversation. Follow user's lead.",
}
