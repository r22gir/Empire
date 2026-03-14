from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
import uuid

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
    
    entry = {
        "id": str(uuid.uuid4()),
        "source": notif.source,
        "type": notif.type,
        "title": notif.title,
        "message": notif.message,
        "priority": notif.priority,
        "context": notif.context or {},
        "read": False,
        "created_at": datetime.now().isoformat()
    }
    notifications_db.insert(0, entry)
    return {"status": "sent", "notification": entry}

@router.get("/notifications")
async def get_notifications(unread_only: bool = False):
    """Founder dashboard reads notifications"""
    if unread_only:
        return {"notifications": [n for n in notifications_db if not n["read"]]}
    return {"notifications": notifications_db}

@router.patch("/notifications/{notif_id}/read")
async def mark_read(notif_id: str):
    for n in notifications_db:
        if n["id"] == notif_id:
            n["read"] = True
            return {"status": "marked_read"}
    return {"error": "not found"}

@router.delete("/notifications/{notif_id}")
async def dismiss_notification(notif_id: str):
    global notifications_db
    notifications_db = [n for n in notifications_db if n["id"] != notif_id]
    return {"status": "dismissed"}

@router.post("/notifications/respond/{notif_id}")
async def respond_to_notification(notif_id: str, action: str, response: Optional[str] = None):
    """Founder takes action on a notification (approve, reject, defer, etc.)"""
    for n in notifications_db:
        if n["id"] == notif_id:
            n["read"] = True
            n["response"] = {"action": action, "message": response, "at": datetime.now().isoformat()}
            # TODO: Route response back to originating desk/MAX
            return {"status": "responded", "action": action}
    return {"error": "not found"}

# ============ INTERNAL HELPER FUNCTIONS ============
# Other Empire modules import and call these directly

def notify_founder(source: str, type: str, title: str, message: str, priority: str = "medium", context: dict = None):
    """Call from any Empire module to alert founder"""
    if source not in VALID_SOURCES:
        source = "System"
    entry = {
        "id": str(uuid.uuid4()),
        "source": source,
        "type": type,
        "title": title,
        "message": message,
        "priority": priority,
        "context": context or {},
        "read": False,
        "created_at": datetime.now().isoformat()
    }
    notifications_db.insert(0, entry)
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
