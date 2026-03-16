import os
import re
import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from enum import IntEnum

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

from app.db.database import get_db, dict_row

logger = logging.getLogger("max.access_control")

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(os.path.join(os.path.dirname(__file__), "../../db/empire.db"))
)


class AccessLevel(IntEnum):
    AUTO = 1
    CONFIRM = 2
    PIN = 3


TOOL_LEVELS = {
    "get_tasks": 1, "get_desk_status": 1, "search_quotes": 1,
    "get_quote": 1, "search_contacts": 1, "get_system_stats": 1,
    "get_weather": 1, "get_services_health": 1, "web_search": 1,
    "web_read": 1, "create_task": 1, "create_contact": 1,
    "create_quick_quote": 1, "photo_to_quote": 1, "present": 1,
    "search_images": 1, "open_quote_builder": 1, "select_proposal": 1,
    "send_telegram": 1, "send_email": 1, "send_quote_telegram": 1,
    "send_quote_email": 1, "run_desk_task": 1, "submit_desk_task": 1,
    "delete_task": 2, "bulk_update": 2, "modify_config": 2,
    "update_contact": 2, "delete_contact": 2, "clear_data": 2,
    "shell_execute": 3, "dispatch_to_openclaw": 3, "deploy": 3,
    "erase_dataset": 3, "drop_table": 3,
}

LEVEL_PATTERNS = {
    2: [r"delete_", r"remove_", r"bulk_", r"modify_", r"update_"],
    3: [r"deploy_", r"erase_", r"drop_", r"shell_", r"destroy_", r"reset_"],
}

ROLE_PERMISSIONS = {
    "founder":  {1: "auto", 2: "confirm", 3: "pin"},
    "admin":    {1: "auto", 2: "confirm", 3: "pin"},
    "manager":  {1: "auto", 2: "confirm", 3: "deny"},
    "operator": {1: "auto", 2: "confirm_own_desk", 3: "deny"},
    "viewer":   {1: "read_only", 2: "deny", 3: "deny"},
}

CONFIRM_TIMEOUT = 60
PIN_TIMEOUT = 120
MAX_PIN_ATTEMPTS = 3
LOCKOUT_MINUTES = 15


class AccessController:

    def _get_conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def resolve_user(self, chat_id, channel="telegram"):
        with get_db() as conn:
            if channel == "telegram":
                row = conn.execute(
                    "SELECT * FROM access_users WHERE telegram_chat_id = ?",
                    (str(chat_id),)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM access_users WHERE id = ?",
                    (str(chat_id),)
                ).fetchone()
            return dict_row(row)

    def classify_tool(self, tool_name):
        if tool_name in TOOL_LEVELS:
            return AccessLevel(TOOL_LEVELS[tool_name])
        for level in (3, 2):
            for pattern in LEVEL_PATTERNS[level]:
                if re.search(pattern, tool_name):
                    return AccessLevel(level)
        return AccessLevel.AUTO

    def check_permission(self, user, tool_name, desk=None):
        if not user:
            return ("deny", None)

        role = user.get("role", "viewer")
        level = int(self.classify_tool(tool_name))
        perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"])
        action = perms.get(level, "deny")

        if user.get("locked_until"):
            locked_until = datetime.fromisoformat(user["locked_until"])
            if datetime.utcnow() < locked_until:
                return ("locked", None)

        if action == "read_only":
            return ("auto", None) if level == 1 else ("deny", None)

        if action == "confirm_own_desk":
            if desk and desk == user.get("desk"):
                return ("confirm", None)
            return ("deny", None)

        return (action, None)

    def create_pending_session(self, user_id, tool_name, tool_params, desk, channel, chat_id, level):
        import json
        session_id = secrets.token_hex(16)
        expires_at = datetime.utcnow() + timedelta(
            seconds=PIN_TIMEOUT if level == 3 else CONFIRM_TIMEOUT
        )
        with get_db() as conn:
            conn.execute(
                """INSERT INTO access_sessions
                   (id, user_id, tool_name, tool_params, desk, channel, chat_id, level, status, expires_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (session_id, user_id, tool_name, json.dumps(tool_params or {}),
                 desk, channel, str(chat_id), level,
                 expires_at.isoformat(), datetime.utcnow().isoformat())
            )
        return session_id

    def confirm_session(self, session_id):
        import json
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM access_sessions WHERE id = ? AND status = 'pending'",
                (session_id,)
            ).fetchone()
            if not row:
                return None
            row = dict(row)
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.utcnow() > expires_at:
                conn.execute(
                    "UPDATE access_sessions SET status = 'expired' WHERE id = ?",
                    (session_id,)
                )
                return None
            conn.execute(
                "UPDATE access_sessions SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), session_id)
            )
            return {
                "tool_name": row["tool_name"],
                "tool_params": json.loads(row["tool_params"]),
                "desk": row["desk"],
                "user_id": row["user_id"],
            }

    def _hash_pin(self, pin):
        if HAS_BCRYPT:
            return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
        salt = secrets.token_hex(16)
        h = hashlib.sha256(f"{salt}{pin}".encode()).hexdigest()
        return f"sha256:{salt}:{h}"

    def _verify_pin_hash(self, pin, stored_hash):
        if HAS_BCRYPT and not stored_hash.startswith("sha256:"):
            return bcrypt.checkpw(pin.encode(), stored_hash.encode())
        if stored_hash.startswith("sha256:"):
            _, salt, h = stored_hash.split(":", 2)
            return hashlib.sha256(f"{salt}{pin}".encode()).hexdigest() == h
        return False

    def verify_pin(self, user_id, pin):
        with get_db() as conn:
            row = conn.execute(
                "SELECT pin_hash, failed_pin_attempts, locked_until FROM access_users WHERE id = ?",
                (user_id,)
            ).fetchone()
            if not row:
                return False
            user = dict(row)

            if user.get("locked_until"):
                locked_until = datetime.fromisoformat(user["locked_until"])
                if datetime.utcnow() < locked_until:
                    return False
                conn.execute(
                    "UPDATE access_users SET failed_pin_attempts = 0, locked_until = NULL WHERE id = ?",
                    (user_id,)
                )

            if not user.get("pin_hash"):
                return False

            if self._verify_pin_hash(pin, user["pin_hash"]):
                conn.execute(
                    "UPDATE access_users SET failed_pin_attempts = 0 WHERE id = ?",
                    (user_id,)
                )
                return True

            attempts = (user.get("failed_pin_attempts") or 0) + 1
            if attempts >= MAX_PIN_ATTEMPTS:
                locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                conn.execute(
                    "UPDATE access_users SET failed_pin_attempts = ?, locked_until = ? WHERE id = ?",
                    (attempts, locked_until.isoformat(), user_id)
                )
            else:
                conn.execute(
                    "UPDATE access_users SET failed_pin_attempts = ? WHERE id = ?",
                    (attempts, user_id)
                )
            return False

    def authorize_pin_session(self, session_id, pin):
        with get_db() as conn:
            row = conn.execute(
                "SELECT user_id FROM access_sessions WHERE id = ? AND status = 'pending'",
                (session_id,)
            ).fetchone()
            if not row:
                return None
            user_id = row["user_id"]

        if not self.verify_pin(user_id, pin):
            return None
        return self.confirm_session(session_id)

    def set_pin(self, user_id, new_pin):
        if not re.match(r"^\d{4,6}$", new_pin):
            raise ValueError("PIN must be 4-6 digits")
        pin_hash = self._hash_pin(new_pin)
        with get_db() as conn:
            conn.execute(
                "UPDATE access_users SET pin_hash = ? WHERE id = ?",
                (pin_hash, user_id)
            )

    def audit_log(self, user_id, tool_name, level, result, detail=None, channel=None):
        with get_db() as conn:
            conn.execute(
                """INSERT INTO access_audit
                   (user_id, tool_name, level, result, detail, channel, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, tool_name, level, result, detail, channel,
                 datetime.utcnow().isoformat())
            )

    def expire_stale_sessions(self):
        with get_db() as conn:
            conn.execute(
                "UPDATE access_sessions SET status = 'expired' WHERE status = 'pending' AND expires_at < ?",
                (datetime.utcnow().isoformat(),)
            )

    def get_pending_session(self, chat_id):
        with get_db() as conn:
            row = conn.execute(
                """SELECT * FROM access_sessions
                   WHERE chat_id = ? AND status = 'pending' AND expires_at > ?
                   ORDER BY created_at DESC LIMIT 1""",
                (str(chat_id), datetime.utcnow().isoformat())
            ).fetchone()
            return dict_row(row)


access_controller = AccessController()
