from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
from pathlib import Path
from datetime import datetime
import uuid

router = APIRouter(prefix="/chats", tags=["chats"])

CHATS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "chats"
CHATS_DIR.mkdir(parents=True, exist_ok=True)


class SaveChatRequest(BaseModel):
    user_id: str = "founder"
    messages: List[Dict]
    title: Optional[str] = None


class UpdateChatRequest(BaseModel):
    messages: List[Dict]


class RenameChatRequest(BaseModel):
    title: str


class PinChatRequest(BaseModel):
    pinned: bool = True


# ── Helpers ──────────────────────────────────────────────────


def _get_preview(messages: List[Dict], max_len: int = 120) -> str:
    """Extract a short preview from the first user message."""
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")
            if isinstance(text, str) and text.strip():
                return text.strip()[:max_len]
    return ""


def _auto_title(messages: List[Dict]) -> str:
    """Generate a title from the first user message."""
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")
            if isinstance(text, str) and text.strip():
                # Take first sentence or first 60 chars
                first_line = text.strip().split("\n")[0]
                if len(first_line) > 60:
                    return first_line[:57] + "..."
                return first_line
    return f"Chat {datetime.now().strftime('%m/%d %H:%M')}"


# ── CRUD Endpoints ───────────────────────────────────────────


@router.post("/save")
async def save_chat(req: SaveChatRequest):
    chat_id = str(uuid.uuid4())[:8]
    title = req.title or _auto_title(req.messages)

    user_dir = CHATS_DIR / req.user_id
    user_dir.mkdir(exist_ok=True)

    chat_data = {
        "id": chat_id,
        "title": title,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "pinned": False,
        "preview": _get_preview(req.messages),
        "messages": req.messages,
    }

    with open(user_dir / f"{chat_id}.json", "w") as f:
        json.dump(chat_data, f, indent=2)

    return {"status": "saved", "chat_id": chat_id, "title": title}


@router.put("/{chat_id}")
async def update_chat(chat_id: str, req: UpdateChatRequest, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat not found")

    with open(chat_file, "r") as f:
        chat_data = json.load(f)

    chat_data["messages"] = req.messages
    chat_data["updated_at"] = datetime.now().isoformat()
    chat_data["preview"] = _get_preview(req.messages)

    with open(chat_file, "w") as f:
        json.dump(chat_data, f, indent=2)

    return {"status": "updated", "chat_id": chat_id}


@router.get("/list")
async def list_chats(user_id: str = "founder"):
    user_dir = CHATS_DIR / user_id
    if not user_dir.exists():
        return {"chats": [], "count": 0}

    chats = []
    for f in user_dir.glob("*.json"):
        try:
            with open(f, "r") as file:
                data = json.load(file)
                chats.append(
                    {
                        "id": data["id"],
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", ""),
                        "created_at": data.get("created_at", ""),
                        "message_count": len(data.get("messages", [])),
                        "preview": data.get("preview", _get_preview(data.get("messages", []))),
                        "pinned": data.get("pinned", False),
                    }
                )
        except (json.JSONDecodeError, KeyError):
            continue

    # Pinned first, then by updated_at descending (newest on top)
    chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    chats.sort(key=lambda x: x.get("pinned", False), reverse=True)

    return {"chats": chats, "count": len(chats)}


@router.get("/search")
async def search_chats(q: str, user_id: str = "founder"):
    """Search chat history by keyword across titles and message content."""
    user_dir = CHATS_DIR / user_id
    if not user_dir.exists():
        return {"results": [], "count": 0, "query": q}

    q_lower = q.lower()
    results = []

    for f in user_dir.glob("*.json"):
        try:
            with open(f, "r") as file:
                data = json.load(file)

            # Search in title
            title_match = q_lower in data.get("title", "").lower()

            # Search in messages
            matching_messages = []
            for i, msg in enumerate(data.get("messages", [])):
                content = msg.get("content", "")
                if isinstance(content, str) and q_lower in content.lower():
                    # Extract snippet around the match
                    idx = content.lower().index(q_lower)
                    start = max(0, idx - 40)
                    end = min(len(content), idx + len(q) + 40)
                    snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
                    matching_messages.append(
                        {
                            "message_index": i,
                            "role": msg.get("role", ""),
                            "snippet": snippet,
                        }
                    )

            if title_match or matching_messages:
                results.append(
                    {
                        "id": data["id"],
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": len(data.get("messages", [])),
                        "title_match": title_match,
                        "matching_messages": matching_messages[:5],  # Cap at 5 snippets
                        "total_matches": len(matching_messages),
                    }
                )
        except (json.JSONDecodeError, KeyError):
            continue

    # Sort by relevance: title matches first, then by match count
    results.sort(key=lambda x: (not x["title_match"], -x["total_matches"]))

    return {"results": results, "count": len(results), "query": q}


# ── Cross-Channel Unified Store Endpoints ─────────────────────
# These MUST be defined before /{chat_id} to avoid route conflicts


@router.get("/cross-channel")
async def cross_channel_messages(channel: str = None, hours: int = 24, limit: int = 50):
    """Get messages across all channels from unified store."""
    from app.services.max.unified_message_store import unified_store
    if channel:
        msgs = unified_store.get_recent_by_channel(channel, limit=limit, hours=hours)
    else:
        ctx = unified_store.get_cross_channel_context(limit_per_channel=limit, hours=hours)
        msgs = []
        for ch_msgs in ctx.values():
            msgs.extend(ch_msgs)
        msgs.sort(key=lambda m: m.get("created_at", ""))
    return {"messages": msgs, "count": len(msgs)}


@router.get("/cross-channel/stats")
async def cross_channel_stats():
    """Get message counts by channel from unified store."""
    from app.services.max.unified_message_store import unified_store
    return unified_store.get_stats()


@router.get("/cross-channel/search")
async def cross_channel_search(q: str, channel: str = None, limit: int = 20):
    """Search messages across all channels."""
    from app.services.max.unified_message_store import unified_store
    results = unified_store.search_messages(q, channel=channel, limit=limit)
    return {"results": results, "count": len(results), "query": q}


@router.get("/{chat_id}")
async def load_chat(chat_id: str, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat not found")

    with open(chat_file, "r") as f:
        return json.load(f)


@router.patch("/{chat_id}/title")
async def rename_chat(chat_id: str, req: RenameChatRequest, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat not found")
    with open(chat_file, "r") as f:
        chat_data = json.load(f)
    chat_data["title"] = req.title
    chat_data["updated_at"] = datetime.now().isoformat()
    with open(chat_file, "w") as f:
        json.dump(chat_data, f, indent=2)
    return {"status": "renamed", "title": req.title}


@router.patch("/{chat_id}/pin")
async def pin_chat(chat_id: str, req: PinChatRequest, user_id: str = "founder"):
    """Pin or unpin a chat conversation."""
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat not found")
    with open(chat_file, "r") as f:
        chat_data = json.load(f)
    chat_data["pinned"] = req.pinned
    chat_data["updated_at"] = datetime.now().isoformat()
    with open(chat_file, "w") as f:
        json.dump(chat_data, f, indent=2)
    return {"status": "pinned" if req.pinned else "unpinned", "chat_id": chat_id}


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if chat_file.exists():
        os.remove(chat_file)
    return {"status": "deleted"}
