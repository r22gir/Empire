"""
MAX API Router - Endpoints for AI Assistant Manager.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import logging
import uuid

from app.services.max.ai_router import ai_router, AIMessage, AIModel
from app.services.max.desk_manager import desk_manager, TaskStatus
from app.services.max.telegram_bot import telegram_bot
from app.services.max.guardrails import check_input, sanitize_output, SAFE_REFUSAL
from app.services.max.tool_executor import parse_tool_blocks, strip_tool_blocks, execute_tool
from app.services.max.system_prompt import get_system_prompt_with_brain
from app.services.max.brain import ContextBuilder, ConversationTracker
from app.services.max.token_tracker import token_tracker

logger = logging.getLogger("max.api")
router = APIRouter(prefix="/max", tags=["MAX AI Assistant"])

# Brain instances (shared across requests)
conversation_tracker = ConversationTracker()


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    history: List[Dict[str, str]] = []
    image_filename: Optional[str] = None
    desk: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model_used: str
    fallback_used: bool = False


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    desk_id: Optional[str] = None
    domains: List[str] = []
    priority: int = 5


class TelegramMessageRequest(BaseModel):
    message: str
    urgent: bool = False


@router.post("/chat", response_model=ChatResponse)
async def chat_with_max(request: ChatRequest, background_tasks: BackgroundTasks):
    is_safe, reason = check_input(request.message)
    if not is_safe:
        logger.warning(f"Blocked input ({reason}): {request.message[:100]}")
        return ChatResponse(response=SAFE_REFUSAL, model_used="guardrail", fallback_used=False)

    for msg in request.history[-3:]:
        hist_safe, _ = check_input(msg.get("content", ""))
        if not hist_safe:
            return ChatResponse(response=SAFE_REFUSAL, model_used="guardrail", fallback_used=False)

    try:
        messages = [AIMessage(role=h["role"], content=h["content"]) for h in request.history]
        messages.append(AIMessage(role="user", content=request.message))
        model = None
        if request.model:
            try:
                model = AIModel(request.model)
            except ValueError:
                pass

        # Build brain-enriched system prompt (non-desk requests only)
        enriched_prompt = None
        if not request.desk:
            try:
                enriched_prompt = await get_system_prompt_with_brain(
                    user_message=request.message,
                    conversation_history=request.history,
                )
            except Exception as e:
                logger.warning(f"Brain context failed, using base prompt: {e}")

        response = await ai_router.chat(messages, model=model, image_filename=request.image_filename, desk=request.desk, system_prompt=enriched_prompt)

        # Track conversation in background
        conv_id = request.history[0].get("id", str(uuid.uuid4())) if request.history else str(uuid.uuid4())
        conversation_tracker.add_message(conv_id, "user", request.message)
        conversation_tracker.add_message(conv_id, "assistant", response.content)
        background_tasks.add_task(conversation_tracker.check_and_summarize, conv_id)

        # Log token usage
        input_text = request.message + "".join(h.get("content", "") for h in request.history[-10:])
        token_tracker.log_chat(response.model_used, input_text, response.content, "chat", conv_id)

        return ChatResponse(response=sanitize_output(response.content), model_used=response.model_used, fallback_used=response.fallback_used)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint for MAX chat with brain context."""
    is_safe, reason = check_input(request.message)
    if not is_safe:
        logger.warning(f"Blocked input ({reason}): {request.message[:100]}")
        async def refusal_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': SAFE_REFUSAL})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'guardrail'})}\n\n"
        return StreamingResponse(refusal_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    for msg in request.history[-3:]:
        hist_safe, _ = check_input(msg.get("content", ""))
        if not hist_safe:
            async def refusal_gen():
                yield f"data: {json.dumps({'type': 'text', 'content': SAFE_REFUSAL})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model_used': 'guardrail'})}\n\n"
            return StreamingResponse(refusal_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    messages = [AIMessage(role=h["role"], content=h["content"]) for h in request.history]
    messages.append(AIMessage(role="user", content=request.message))
    model = None
    if request.model:
        try:
            model = AIModel(request.model)
        except ValueError:
            pass

    # Auto-switch to local if budget threshold reached
    if model != AIModel.OLLAMA and token_tracker.should_switch_to_local():
        logger.info("Budget threshold reached — auto-switching to Ollama")
        model = AIModel.OLLAMA

    # Build brain-enriched system prompt before streaming (non-desk only)
    enriched_prompt = None
    if not request.desk:
        try:
            enriched_prompt = await get_system_prompt_with_brain(
                user_message=request.message,
                conversation_history=request.history,
            )
        except Exception as e:
            logger.warning(f"Brain context failed, using base prompt: {e}")

    # Conversation tracking ID
    conv_id = request.history[0].get("id", str(uuid.uuid4())) if request.history else str(uuid.uuid4())
    conversation_tracker.add_message(conv_id, "user", request.message)

    async def event_generator():
        model_used = "unknown"
        full_response = ""
        try:
            async for chunk, m_used in ai_router.chat_stream(messages, model=model, image_filename=request.image_filename, desk=request.desk, system_prompt=enriched_prompt):
                model_used = m_used
                safe_chunk = sanitize_output(chunk)
                full_response += safe_chunk
                yield f"data: {json.dumps({'type': 'text', 'content': safe_chunk})}\n\n"

            # Parse and execute tool blocks from completed response
            tool_calls = parse_tool_blocks(full_response)
            for tc in tool_calls:
                result = execute_tool(tc, desk=request.desk)
                yield f"data: {json.dumps({'type': 'tool_result', 'tool': result.tool, 'success': result.success, 'result': result.result, 'error': result.error})}\n\n"

            # Track assistant response and trigger summarization if needed
            conversation_tracker.add_message(conv_id, "assistant", full_response)
            try:
                await conversation_tracker.check_and_summarize(conv_id)
            except Exception as e:
                logger.warning(f"Conversation summarization failed: {e}")

            # Log token usage
            input_text = request.message + "".join(h.get("content", "") for h in request.history[-10:])
            token_tracker.log_chat(model_used, input_text, full_response, "chat/stream", conv_id)

            yield f"data: {json.dumps({'type': 'done', 'model_used': model_used})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@router.get("/models")
async def get_available_models():
    return {"models": ai_router.get_available_models()}


@router.get("/desks")
async def get_all_desks():
    return {"desks": desk_manager.get_all_desks()}


@router.get("/desks/{desk_id}")
async def get_desk(desk_id: str):
    desk = desk_manager.get_desk(desk_id)
    if not desk:
        raise HTTPException(status_code=404, detail=f"Desk {desk_id} not found")
    return desk


@router.post("/tasks")
async def create_task(request: TaskCreateRequest, background_tasks: BackgroundTasks):
    task = desk_manager.create_task(title=request.title, description=request.description, desk_id=request.desk_id, domains=request.domains, priority=request.priority)
    if telegram_bot.is_configured:
        background_tasks.add_task(telegram_bot.send_task_update, task.title, "started", task.description[:100], task.desk_id)
    return {"task": task.dict()}


@router.get("/tasks")
async def get_all_tasks(status: Optional[str] = None, desk_id: Optional[str] = None):
    task_status = TaskStatus(status) if status else None
    tasks = desk_manager.get_all_tasks(status=task_status, desk_id=desk_id)
    return {"tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = desk_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, background_tasks: BackgroundTasks):
    task = desk_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    success = desk_manager.complete_task(task_id)
    if telegram_bot.is_configured:
        background_tasks.add_task(telegram_bot.send_task_update, task["title"], "completed", "", task["desk_id"])
    return {"status": "completed", "task_id": task_id}


@router.post("/tasks/{task_id}/fail")
async def fail_task(task_id: str, error: str = "Unknown error", background_tasks: BackgroundTasks = None):
    task = desk_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    success = desk_manager.fail_task(task_id, error)
    if telegram_bot.is_configured and background_tasks:
        background_tasks.add_task(telegram_bot.send_task_update, task["title"], "failed", error, task["desk_id"])
    return {"status": "failed", "task_id": task_id, "error": error}


@router.get("/stats")
async def get_stats():
    return {"stats": desk_manager.get_stats(), "telegram_connected": telegram_bot.is_configured}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MAX AI Assistant Manager", "desks_online": len(desk_manager.get_all_desks()), "telegram_configured": telegram_bot.is_configured}


@router.post("/telegram/send")
async def send_telegram_message(request: TelegramMessageRequest):
    if not telegram_bot.is_configured:
        raise HTTPException(status_code=400, detail="Telegram not configured")
    if request.urgent:
        success = await telegram_bot.send_urgent_alert("Manual Alert", request.message)
    else:
        success = await telegram_bot.send_message(request.message)
    return {"success": success}


@router.get("/telegram/status")
async def telegram_status():
    return {"configured": telegram_bot.is_configured, "bot_token_set": bool(telegram_bot.bot_token), "chat_id_set": bool(telegram_bot.founder_chat_id)}


@router.get("/brain/status")
async def brain_status():
    """Get MAX Brain status — memory counts, drive status, Ollama health."""
    from app.services.max.brain.brain_config import get_brain_path, get_db_path, OLLAMA_BASE_URL
    from app.services.max.brain.memory_store import MemoryStore
    import httpx

    brain_path = get_brain_path()
    db_path = get_db_path()
    is_external = "/media/rg/BACKUP11" in str(brain_path)

    # Memory stats
    try:
        store = MemoryStore(db_path)
        memory_count = store.count()
    except Exception as e:
        memory_count = -1
        logger.warning(f"Brain DB error: {e}")

    # Ollama health
    ollama_ok = False
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
                ollama_models = [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass

    return {
        "brain_online": memory_count >= 0 and ollama_ok,
        "storage": {
            "path": str(brain_path),
            "external_drive": is_external,
            "db_path": db_path,
        },
        "memories": {
            "total": memory_count,
        },
        "ollama": {
            "online": ollama_ok,
            "url": OLLAMA_BASE_URL,
            "models": ollama_models,
        },
        "conversations": {
            "active": conversation_tracker.get_active_count(),
        },
    }


@router.get("/tokens/stats")
async def get_token_stats(days: int = 30):
    """Get token usage statistics and cost tracking."""
    return token_tracker.get_stats(days=days)


class BudgetUpdateRequest(BaseModel):
    monthly_budget: Optional[float] = None
    alert_threshold: Optional[float] = None
    auto_switch_to_local: Optional[bool] = None
    auto_switch_threshold: Optional[float] = None


@router.patch("/tokens/budget")
async def update_budget(request: BudgetUpdateRequest):
    """Update monthly budget configuration."""
    token_tracker.update_budget(
        monthly_budget=request.monthly_budget,
        alert_threshold=request.alert_threshold,
        auto_switch=request.auto_switch_to_local,
        auto_switch_threshold=request.auto_switch_threshold,
    )
    return {"status": "updated"}
