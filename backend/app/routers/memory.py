"""
Memory API — REST endpoints for MAX Brain MemoryStore.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.services.max.brain.memory_store import MemoryStore

router = APIRouter()
_store = MemoryStore()


# ── Pydantic models ──────────────────────────────────────────

class AddMemoryRequest(BaseModel):
    category: str
    content: str
    subject: str = ""
    subcategory: str = ""
    importance: int = 5
    source: str = "api"
    tags: list[str] = Field(default_factory=list)
    customer_id: Optional[str] = None
    conversation_id: Optional[str] = None
    expires_at: Optional[str] = None


class UpdateMemoryRequest(BaseModel):
    category: Optional[str] = None
    content: Optional[str] = None
    subject: Optional[str] = None
    subcategory: Optional[str] = None
    importance: Optional[int] = None
    source: Optional[str] = None
    tags: Optional[list[str]] = None


class ConversationSummaryRequest(BaseModel):
    conversation_id: str
    summary: str
    key_decisions: list[str] = Field(default_factory=list)
    tasks_created: list[str] = Field(default_factory=list)
    customers_mentioned: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    mood: str = "productive"
    message_count: int = 0
    source: str = "api"


class AddKnowledgeRequest(BaseModel):
    business: str
    category: str
    key: str
    value: str
    source: str = "api"


# ── Endpoints ────────────────────────────────────────────────

@router.get("/memory/search")
def search_memories(
    q: Optional[str] = None,
    category: Optional[str] = None,
    customer_id: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    results = _store.search_memories(query=q, category=category, customer_id=customer_id, limit=limit)
    return {"memories": results, "count": len(results)}


@router.get("/memory/recent")
def recent_memories(
    category: Optional[str] = None,
    limit: int = Query(default=10, le=100),
):
    results = _store.get_recent(category=category, limit=limit)
    return {"memories": results, "count": len(results)}


@router.post("/memory/add")
def add_memory(req: AddMemoryRequest):
    memory_id = _store.add_memory(
        category=req.category,
        content=req.content,
        subject=req.subject,
        subcategory=req.subcategory,
        importance=req.importance,
        source=req.source,
        tags=req.tags,
        customer_id=req.customer_id,
        conversation_id=req.conversation_id,
        expires_at=req.expires_at,
    )
    return {"id": memory_id, "status": "created"}


@router.put("/memory/{memory_id}")
def update_memory(memory_id: str, req: UpdateMemoryRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if "tags" in updates:
        import json
        updates["tags"] = json.dumps(updates["tags"])
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    _store.update_memory(memory_id, **updates)
    return {"id": memory_id, "status": "updated"}


@router.delete("/memory/{memory_id}")
def delete_memory(memory_id: str):
    _store.delete_memory(memory_id)
    return {"id": memory_id, "status": "deleted"}


@router.get("/memory/stats")
def memory_stats():
    conn = _store._conn()
    rows = conn.execute(
        "SELECT category, COUNT(*) as count FROM memories GROUP BY category ORDER BY count DESC"
    ).fetchall()
    conn.close()
    total = sum(r["count"] for r in rows)
    return {"total": total, "by_category": {r["category"]: r["count"] for r in rows}}


@router.get("/memory/context-pack")
def context_pack():
    top_memories = _store.search_memories(limit=20)
    conn = _store._conn()
    summaries = conn.execute(
        "SELECT * FROM conversation_summaries ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority DESC, created_at DESC"
    ).fetchall()
    conn.close()
    return {
        "top_memories": top_memories,
        "recent_summaries": [dict(s) for s in summaries],
        "pending_tasks": [dict(t) for t in tasks],
    }


@router.post("/memory/conversation-summary")
def save_conversation_summary(req: ConversationSummaryRequest):
    summary_id = _store.save_conversation_summary(
        conversation_id=req.conversation_id,
        summary=req.summary,
        key_decisions=req.key_decisions,
        tasks_created=req.tasks_created,
        customers_mentioned=req.customers_mentioned,
        topics=req.topics,
        mood=req.mood,
        message_count=req.message_count,
    )
    return {"id": summary_id, "status": "created"}


@router.get("/memory/knowledge")
def get_knowledge(
    business: Optional[str] = None,
    category: Optional[str] = None,
):
    results = _store.get_knowledge(business=business, category=category)
    return {"knowledge": results, "count": len(results)}


@router.post("/memory/knowledge")
def add_knowledge(req: AddKnowledgeRequest):
    kid = _store.add_knowledge(
        business=req.business,
        category=req.category,
        key=req.key,
        value=req.value,
        source=req.source,
    )
    return {"id": kid, "status": "created"}
