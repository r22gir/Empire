"""
Inbox CRUD router — stores and manages Telegram/incoming messages
with AI-classified intents (task, question, instruction, note).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import uuid
import os

router = APIRouter(prefix="/inbox", tags=["inbox"])

INBOX_DIR = os.path.expanduser("~/Empire/data/inbox")
os.makedirs(INBOX_DIR, exist_ok=True)


class InboxCreate(BaseModel):
    text: str
    source: str = "telegram"
    telegram_message_id: Optional[int] = None
    intent: str = "note"
    desk_target: Optional[str] = None
    priority: int = 5
    ai_summary: Optional[str] = None
    ai_response: Optional[str] = None
    status: str = "received"
    linked_task_id: Optional[str] = None


class InboxUpdate(BaseModel):
    intent: Optional[str] = None
    desk_target: Optional[str] = None
    priority: Optional[int] = None
    ai_summary: Optional[str] = None
    ai_response: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None
    linked_task_id: Optional[str] = None


def _msg_path(msg_id: str) -> str:
    return os.path.join(INBOX_DIR, f"{msg_id}.json")


def _load_msg(msg_id: str) -> dict:
    path = _msg_path(msg_id)
    if not os.path.exists(path):
        raise HTTPException(404, f"Inbox message {msg_id} not found")
    with open(path) as f:
        return json.load(f)


def _save_msg(msg: dict):
    with open(_msg_path(msg["id"]), "w") as f:
        json.dump(msg, f, indent=2, default=str)


@router.post("")
async def create_inbox_message(payload: InboxCreate):
    """Create a new inbox message."""
    msg_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    msg = {
        "id": msg_id,
        **payload.model_dump(),
        "result": None,
        "created_at": now,
        "processed_at": None,
        "reviewed_at": None,
    }
    _save_msg(msg)
    return {"status": "created", "message": msg}


@router.get("")
async def list_inbox(status: Optional[str] = None, intent: Optional[str] = None):
    """List inbox messages, optionally filtered."""
    messages = []
    for fname in os.listdir(INBOX_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(INBOX_DIR, fname)) as f:
            m = json.load(f)
        if status and m.get("status") != status:
            continue
        if intent and m.get("intent") != intent:
            continue
        messages.append(m)
    messages.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return {"messages": messages, "count": len(messages)}


@router.get("/pending")
async def pending_review():
    """Get all messages needing founder review (not yet 'reviewed' or 'done')."""
    messages = []
    for fname in os.listdir(INBOX_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(INBOX_DIR, fname)) as f:
            m = json.load(f)
        if m.get("status") not in ("reviewed",):
            messages.append(m)
    messages.sort(key=lambda m: m.get("priority", 5), reverse=True)
    return {"messages": messages, "count": len(messages)}


@router.get("/summary")
async def inbox_summary():
    """Summary stats for morning briefing."""
    all_msgs = []
    for fname in os.listdir(INBOX_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(INBOX_DIR, fname)) as f:
            all_msgs.append(json.load(f))

    by_intent = {}
    by_status = {}
    for m in all_msgs:
        by_intent[m.get("intent", "note")] = by_intent.get(m.get("intent", "note"), 0) + 1
        by_status[m.get("status", "received")] = by_status.get(m.get("status", "received"), 0) + 1

    return {
        "total": len(all_msgs),
        "by_intent": by_intent,
        "by_status": by_status,
        "pending_review": sum(1 for m in all_msgs if m.get("status") not in ("reviewed",)),
    }


@router.get("/{msg_id}")
async def get_inbox_message(msg_id: str):
    """Get a single inbox message."""
    return _load_msg(msg_id)


@router.patch("/{msg_id}")
async def update_inbox_message(msg_id: str, payload: InboxUpdate):
    """Update an inbox message."""
    msg = _load_msg(msg_id)
    updates = payload.model_dump(exclude_unset=True)
    msg.update(updates)
    if "status" in updates:
        if updates["status"] == "done":
            msg["processed_at"] = datetime.utcnow().isoformat()
        elif updates["status"] == "reviewed":
            msg["reviewed_at"] = datetime.utcnow().isoformat()
    _save_msg(msg)
    return {"status": "updated", "message": msg}


@router.post("/{msg_id}/review")
async def mark_reviewed(msg_id: str):
    """Mark a message as reviewed by the founder."""
    msg = _load_msg(msg_id)
    msg["status"] = "reviewed"
    msg["reviewed_at"] = datetime.utcnow().isoformat()
    _save_msg(msg)
    return {"status": "reviewed", "message": msg}


@router.delete("/{msg_id}")
async def delete_inbox_message(msg_id: str):
    """Delete an inbox message."""
    path = _msg_path(msg_id)
    if not os.path.exists(path):
        raise HTTPException(404, f"Inbox message {msg_id} not found")
    os.remove(path)
    return {"status": "deleted", "id": msg_id}
