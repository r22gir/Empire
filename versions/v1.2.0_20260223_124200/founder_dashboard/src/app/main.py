
# ============ NOTIFICATIONS SYSTEM ============
notifications_db = []

class Notification(BaseModel):
    source: str  # "MAX", "CodeDesk", "ResearchDesk", etc.
    type: str    # "review_needed", "task_complete", "error", "idea", "approval_needed"
    title: str
    message: str
    priority: str = "medium"  # low, medium, high
    action_url: str = ""  # optional link to PR, task, etc.

@app.post("/api/v1/notifications")
async def create_notification(notif: Notification):
    """AI Desks and MAX call this to alert the founder"""
    entry = {
        "id": str(uuid.uuid4()),
        "source": notif.source,
        "type": notif.type,
        "title": notif.title,
        "message": notif.message,
        "priority": notif.priority,
        "action_url": notif.action_url,
        "read": False,
        "created_at": datetime.now().isoformat()
    }
    notifications_db.insert(0, entry)  # newest first
    return {"status": "sent", "notification": entry}

@app.get("/api/v1/notifications")
async def get_notifications(unread_only: bool = False):
    """Founder dashboard polls this"""
    if unread_only:
        return {"notifications": [n for n in notifications_db if not n["read"]]}
    return {"notifications": notifications_db}

@app.patch("/api/v1/notifications/{notif_id}/read")
async def mark_read(notif_id: str):
    for n in notifications_db:
        if n["id"] == notif_id:
            n["read"] = True
            return {"status": "marked_read"}
    return {"error": "not found"}

@app.delete("/api/v1/notifications/{notif_id}")
async def delete_notification(notif_id: str):
    global notifications_db
    notifications_db = [n for n in notifications_db if n["id"] != notif_id]
    return {"status": "deleted"}

# Helper: MAX can auto-notify when it needs approval
def notify_founder(source: str, type: str, title: str, message: str, priority: str = "medium"):
    """Internal helper for agents to send notifications"""
    entry = {
        "id": str(uuid.uuid4()),
        "source": source,
        "type": type,
        "title": title,
        "message": message,
        "priority": priority,
        "action_url": "",
        "read": False,
        "created_at": datetime.now().isoformat()
    }
    notifications_db.insert(0, entry)
    return entry
