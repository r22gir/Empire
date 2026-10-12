from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import uuid

from app.db.max_ops_schema import ensure_max_ops_schema
from app.services.max.channel_text import strip_telegram_html

router = APIRouter()

notifications_db = []

# Internal sources only - no external access
VALID_SOURCES = ["MAX", "CodeDesk", "ResearchDesk", "SupportDesk", "System", "Business"]
VALID_TYPES = [
    "decision_needed",   # MAX needs founder input
    "idea",              # MAX has a suggestion
    "task_complete",     # AI Desk finished work
    "review_needed",     # Code/content needs approval
    "error",             # Something failed
    "system_alert",      # Hardware/service issue
    "business_event"     # Order, payment, etc.
]


def _persist_notification(entry: dict) -> None:
    """Write a notification to SQLite. Failures never drop the in-memory copy."""
    try:
        from app.db.database import get_db

        with get_db() as conn:
            ensure_max_ops_schema(conn)
            conn.execute(
                """INSERT OR REPLACE INTO founder_notifications
                   (id, source, type, title, message, message_plain, priority, context, read, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["id"],
                    entry.get("source"),
                    entry.get("type"),
                    entry.get("title"),
                    entry.get("message"),
                    entry.get("message_plain") or strip_telegram_html(entry.get("message")),
                    entry.get("priority"),
                    json.dumps(entry.get("context") or {}),
                    1 if entry.get("read") else 0,
                    entry.get("created_at"),
                ),
            )
    except Exception:
        pass


def _load_notifications_from_db() -> list[dict]:
    try:
        from app.db.database import get_db

        with get_db() as conn:
            ensure_max_ops_schema(conn)
            rows = conn.execute(
                "SELECT id, source, type, title, message, message_plain, priority, context, read, created_at "
                "FROM founder_notifications ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r) if hasattr(r, "keys") else {
                "id": r[0], "source": r[1], "type": r[2], "title": r[3],
                "message": r[4], "message_plain": r[5], "priority": r[6],
                "context": r[7], "read": r[8], "created_at": r[9],
            }
            try:
                d["context"] = json.loads(d.get("context") or "{}")
            except (TypeError, json.JSONDecodeError):
                d["context"] = {}
            d["read"] = bool(d.get("read"))
            # App clients see plain text; raw HTML stays in message_html.
            d["message_html"] = d.get("message")
            d["message"] = d.get("message_plain") or strip_telegram_html(d.get("message"))
            out.append(d)
        return out
    except Exception:
        return []


def _sync_memory_from_db() -> None:
    global notifications_db
    loaded = _load_notifications_from_db()
    if loaded:
        notifications_db = loaded


class InternalNotification(BaseModel):
    source: str  # Must be internal Empire source
    type: str
    title: str
    message: str
    priority: str = "medium"
    context: Optional[dict] = None  # Extra data (task_id, desk_id, etc.)

@router.post("/notifications/internal")
async def create_internal_notification(notif: InternalNotification):
    """INTERNAL ONLY - Empire services call this to notify founder"""
    if notif.source not in VALID_SOURCES:
        return {"error": f"Invalid source. Must be one of: {VALID_SOURCES}"}

    entry = notify_founder(
        notif.source, notif.type, notif.title, notif.message, notif.priority, notif.context
    )
    return {"status": "sent", "notification": entry}

@router.get("/notifications")
async def get_notifications(unread_only: bool = False):
    """Founder dashboard reads notifications (plain text, history from DB)."""
    _sync_memory_from_db()
    items = notifications_db
    if unread_only:
        items = [n for n in items if not n.get("read")]
    return {"notifications": items}

@router.patch("/notifications/{notif_id}/read")
async def mark_read(notif_id: str):
    _sync_memory_from_db()
    for n in notifications_db:
        if n["id"] == notif_id:
            n["read"] = True
            _persist_notification(n)
            return {"status": "marked_read"}
    return {"error": "not found"}

@router.delete("/notifications/{notif_id}")
async def dismiss_notification(notif_id: str):
    global notifications_db
    _sync_memory_from_db()
    notifications_db = [n for n in notifications_db if n["id"] != notif_id]
    try:
        from app.db.database import get_db
        with get_db() as conn:
            ensure_max_ops_schema(conn)
            conn.execute("DELETE FROM founder_notifications WHERE id = ?", (notif_id,))
    except Exception:
        pass
    return {"status": "dismissed"}

@router.post("/notifications/respond/{notif_id}")
async def respond_to_notification(notif_id: str, action: str, response: Optional[str] = None):
    """Founder takes action on a notification (approve, reject, defer, etc.)"""
    _sync_memory_from_db()
    for n in notifications_db:
        if n["id"] == notif_id:
            n["read"] = True
            n["response"] = {"action": action, "message": response, "at": datetime.now().isoformat()}
            _persist_notification(n)
            return {"status": "responded", "action": action}
    return {"error": "not found"}

# ============ INTERNAL HELPER FUNCTIONS ============
# Other Empire modules import and call these directly

def notify_founder(source: str, type: str, title: str, message: str, priority: str = "medium", context: dict = None):
    """Call from any Empire module to alert founder. Persisted to DB."""
    if source not in VALID_SOURCES:
        source = "System"
    plain = strip_telegram_html(message)
    entry = {
        "id": str(uuid.uuid4()),
        "source": source,
        "type": type,
        "title": title,
        "message": plain,  # app / API see plain text
        "message_plain": plain,
        "message_html": message,  # Telegram / email can use HTML
        "priority": priority,
        "context": context or {},
        "read": False,
        "created_at": datetime.now().isoformat()
    }
    notifications_db.insert(0, entry)
    _persist_notification({**entry, "message": message})
    return entry

def max_needs_decision(title: str, message: str, options: list = None):
    """MAX calls this when it needs founder input"""
    return notify_founder("MAX", "decision_needed", title, message, "high", {"options": options or ["Approve", "Reject", "Defer"]})

def desk_task_complete(desk: str, task_id: str, title: str, summary: str):
    """AI Desk calls when task is done"""
    return notify_founder(desk, "task_complete", title, summary, "medium", {"task_id": task_id})

def desk_needs_review(desk: str, title: str, message: str, item_url: str = ""):
    """AI Desk needs founder to review something"""
    return notify_founder(desk, "review_needed", title, message, "high", {"item_url": item_url})

def system_alert(title: str, message: str, severity: str = "medium"):
    """System monitoring alerts"""
    return notify_founder("System", "system_alert", title, message, severity)

def business_event(title: str, message: str, event_type: str = ""):
    """Business events (orders, payments, etc.)"""
    return notify_founder("Business", "business_event", title, message, "medium", {"event_type": event_type})


# ============ NOTIFICATION LOG & EMERGENCY ============

@router.get("/notifications/log")
async def get_notification_log(limit: int = 50):
    """Founder checks this on demand — last N notifications (newest first)."""
    _sync_memory_from_db()
    return {"notifications": notifications_db[:limit], "total": len(notifications_db)}


class EmergencyAlert(BaseModel):
    title: str
    message: str
    source: str = "System"

# Emergency types that justify Telegram
EMERGENCY_TYPES = [
    "server_down",        # Service on port 8000 unreachable 3+ min
    "payment_failure",    # Failed payment webhook
    "security_breach",    # Security scan critical finding
]

@router.post("/notifications/emergency")
async def send_emergency(alert: EmergencyAlert):
    """ONLY endpoint that sends Telegram. For genuine emergencies only."""
    import httpx as _httpx

    # Log it
    entry = notify_founder(alert.source, "system_alert", f"EMERGENCY: {alert.title}", alert.message, "critical")

    # Send via Telegram
    sent = False
    try:
        from app.services.max.telegram_bot import telegram_bot
        if telegram_bot.is_configured:
            sent = await telegram_bot.send_urgent_alert(alert.title, alert.message)
    except Exception as e:
        entry["telegram_error"] = str(e)

    return {"status": "sent" if sent else "logged_only", "notification": entry, "telegram_sent": sent}
