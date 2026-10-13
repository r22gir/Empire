from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
from pathlib import Path

from app.services.chat_history_store import (
    ChatHistoryIdError,
    ChatHistoryOwnerError,
    chats_dir as store_chats_dir,
    list_chats_for_owner,
    load_chat_for_owner,
    preview_from as _get_preview,
    title_from as _auto_title,
    update_meta,
    upsert_chat,
    user_dir,
)

router = APIRouter(prefix="/chats", tags=["chats"])

# Founder/Workroom checkout path. Tests may monkeypatch this. Family
# editions never mkdir or read it — they use EMPIRE_DATA_DIR/chats.
CHATS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "chats"


def _chats_dir() -> Path:
    return store_chats_dir(workroom_dir=CHATS_DIR)


def _workroom_dir() -> Path:
    return CHATS_DIR


def _owner_or_403(request: Optional[Request], claimed: Optional[str] = None) -> str:
    from app.services.chat_history_store import owner_key_for_request

    try:
        return owner_key_for_request(request, claimed)
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")


class SaveChatRequest(BaseModel):
    user_id: str = "founder"
    id: Optional[str] = None
    messages: List[Dict]
    title: Optional[str] = None


class UpdateChatRequest(BaseModel):
    messages: List[Dict]


class RenameChatRequest(BaseModel):
    title: str


class PinChatRequest(BaseModel):
    pinned: bool = True


# ── CRUD Endpoints ───────────────────────────────────────────


@router.post("/save")
async def save_chat(req: SaveChatRequest, request: Request):
    try:
        data, _status = upsert_chat(
            chat_id=req.id,
            messages=req.messages,
            title=req.title,
            request=request,
            claimed_user_id=req.user_id,
            workroom_dir=_workroom_dir(),
            generate_id=True,
        )
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")
    except ChatHistoryIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "saved", "chat_id": data["id"], "title": data["title"]}


@router.put("/{chat_id}")
async def update_chat(chat_id: str, req: UpdateChatRequest, request: Request = None, user_id: str = "founder"):
    try:
        data, status = upsert_chat(
            chat_id=chat_id,
            messages=req.messages,
            request=request,
            claimed_user_id=user_id,
            workroom_dir=_workroom_dir(),
        )
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")
    except ChatHistoryIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": status, "chat_id": data["id"]}


@router.get("/list")
async def list_chats(request: Request = None, user_id: str = "founder", limit: int = 200, offset: int = 0):
    """Newest chats first (pinned on top), one page at a time.

    2026-10-04: the full list had grown to 2,812 chats / 687KB and was fetched on every
    studio page load (a suspect in the iPhone Safari tab crash). Default page = 200;
    pass limit=0 for everything. ``count`` is still the total.

    Family editions isolate by allowlisted session (not everyone under founder)
    and read EMPIRE_DATA_DIR/chats so Max-e and Maxine never list Rafael's
    Workroom history.
    """
    try:
        chats = list_chats_for_owner(
            request=request,
            claimed_user_id=user_id,
            workroom_dir=_workroom_dir(),
        )
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")
    total = len(chats)
    offset = max(0, int(offset or 0))
    page = chats[offset:offset + limit] if limit and limit > 0 else chats[offset:]
    return {"chats": page, "count": total, "offset": offset, "has_more": offset + len(page) < total}


@router.get("/search")
async def search_chats(q: str, request: Request = None, user_id: str = "founder"):
    """Search chat history by keyword across titles and message content."""
    try:
        owner = _owner_or_403(request, user_id)
        folder = user_dir(owner, workroom_dir=_workroom_dir())
    except ChatHistoryIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not folder.exists():
        return {"results": [], "count": 0, "query": q}

    q_lower = q.lower()
    results = []

    for f in folder.glob("*.json"):
        try:
            data = load_chat_for_owner(
                f.stem,
                request=request,
                claimed_user_id=user_id,
                workroom_dir=_workroom_dir(),
            )
            if not data:
                continue
        except (ChatHistoryOwnerError, ChatHistoryIdError):
            continue

        title_match = q_lower in data.get("title", "").lower()
        matching_messages = []
        for i, msg in enumerate(data.get("messages", [])):
            content = msg.get("content", "")
            if isinstance(content, str) and q_lower in content.lower():
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
                    "matching_messages": matching_messages[:5],
                    "total_matches": len(matching_messages),
                }
            )

    results.sort(key=lambda x: (not x["title_match"], -x["total_matches"]))
    return {"results": results, "count": len(results), "query": q}


# ── Cross-Channel Unified Store Endpoints ─────────────────────
# These MUST be defined before /{chat_id} to avoid route conflicts


@router.get("/cross-channel")
async def cross_channel_messages(channel: str = None, hours: int = 24, limit: int = 50):
    """Legacy unified-message API. Founder UI canonical view is /chats/memory-bank."""
    from app.services.max.unified_message_store import unified_store
    if channel:
        msgs = unified_store.get_recent_by_channel(channel, limit=limit, hours=hours)
    else:
        ctx = unified_store.get_cross_channel_context(limit_per_channel=limit, hours=hours)
        msgs = []
        for ch_msgs in ctx.values():
            msgs.extend(ch_msgs)
        msgs.sort(key=lambda m: m.get("created_at", ""))
    return {
        "scope": "legacy_unified_messages",
        "canonical_history_route": "/api/v1/chats/memory-bank?channel=all",
        "note": "Legacy API surface; use Memory Bank / All Channels for founder-visible unified history.",
        "messages": msgs,
        "count": len(msgs),
    }


@router.get("/cross-channel/stats")
async def cross_channel_stats():
    """Legacy stats API for unified store; Memory Bank remains canonical history."""
    from app.services.max.unified_message_store import unified_store
    return {
        "scope": "legacy_unified_messages_stats",
        "canonical_history_route": "/api/v1/chats/memory-bank?channel=all",
        "stats": unified_store.get_stats(),
    }


@router.get("/cross-channel/search")
async def cross_channel_search(q: str, channel: str = None, limit: int = 20):
    """Legacy unified-message search. Founder UI canonical view is Memory Bank."""
    from app.services.max.unified_message_store import unified_store
    results = unified_store.search_messages(q, channel=channel, limit=limit)
    return {
        "scope": "legacy_unified_messages_search",
        "canonical_history_route": "/api/v1/chats/memory-bank?channel=all",
        "results": results,
        "count": len(results),
        "query": q,
    }


@router.get("/memory-bank")
async def memory_bank(
    channel: str = "all",
    q: Optional[str] = None,
    thread_id: Optional[str] = None,
    founder_only: bool = False,
    attachments_only: bool = False,
    limit: int = 100,
):
    """Founder-visible MAX Memory Bank over the canonical communications ledger."""
    from app.services.max.unified_message_store import unified_store
    messages = unified_store.list_memory_bank(
        channel=channel,
        query=q,
        thread_id=thread_id,
        founder_only=founder_only,
        has_attachments=attachments_only or channel == "attachments",
        limit=limit,
    )
    stats = unified_store.get_stats()
    return {
        "messages": messages,
        "count": len(messages),
        "stats": stats,
        "filters": {
            "channel": channel,
            "q": q,
            "thread_id": thread_id,
            "founder_only": founder_only,
            "attachments_only": attachments_only or channel == "attachments",
        },
    }


@router.get("/memory-bank/threads")
async def memory_bank_threads(limit: int = 100):
    """List Memory Bank threads for founder navigation."""
    from app.services.max.unified_message_store import unified_store
    threads = unified_store.get_memory_threads(limit=limit)
    return {"threads": threads, "count": len(threads)}


@router.get("/{chat_id}")
async def load_chat(chat_id: str, request: Request = None, user_id: str = "founder"):
    try:
        data = load_chat_for_owner(
            chat_id,
            request=request,
            claimed_user_id=user_id,
            workroom_dir=_workroom_dir(),
        )
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")
    except ChatHistoryIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not data:
        raise HTTPException(status_code=404, detail="Chat not found")
    return data


@router.patch("/{chat_id}/title")
async def rename_chat(chat_id: str, req: RenameChatRequest, request: Request = None, user_id: str = "founder"):
    try:
        existing = load_chat_for_owner(
            chat_id,
            request=request,
            claimed_user_id=user_id,
            workroom_dir=_workroom_dir(),
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Chat not found")
        update_meta(
            chat_id,
            title=req.title,
            request=request,
            claimed_user_id=user_id,
            workroom_dir=_workroom_dir(),
        )
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")
    except ChatHistoryIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "renamed", "title": req.title}


@router.patch("/{chat_id}/pin")
async def pin_chat(chat_id: str, req: PinChatRequest, request: Request = None, user_id: str = "founder"):
    """Pin or unpin a chat conversation."""
    try:
        existing = load_chat_for_owner(
            chat_id,
            request=request,
            claimed_user_id=user_id,
            workroom_dir=_workroom_dir(),
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Chat not found")
        update_meta(
            chat_id,
            pinned=req.pinned,
            request=request,
            claimed_user_id=user_id,
            workroom_dir=_workroom_dir(),
        )
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")
    except ChatHistoryIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "pinned" if req.pinned else "unpinned", "chat_id": chat_id}


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, request: Request = None, user_id: str = "founder"):
    try:
        from app.services.chat_history_store import chat_path, owner_key_for_request
        owner = owner_key_for_request(request, user_id)
        chat_file = chat_path(owner, chat_id, workroom_dir=_workroom_dir())
    except ChatHistoryOwnerError:
        raise HTTPException(status_code=403, detail="Se requiere una sesión válida.")
    except ChatHistoryIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if chat_file.exists():
        os.remove(chat_file)
    return {"status": "deleted"}
