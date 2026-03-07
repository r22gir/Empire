"""
MAX API Router - Endpoints for AI Assistant Manager.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
import logging
import uuid
from datetime import datetime
from pathlib import Path

from app.services.max.ai_router import ai_router, AIMessage, AIModel
from app.services.max.telegram_bot import telegram_bot
from app.services.max.guardrails import check_input, sanitize_output, SAFE_REFUSAL
from app.services.max.tool_executor import parse_tool_blocks, strip_tool_blocks, execute_tool
from app.services.max.system_prompt import get_system_prompt_with_brain
from app.services.max.brain import ContextBuilder, ConversationTracker
from app.services.max.brain.brain_config import (
    REALTIME_LEARNING_ENABLED,
    BATCH_LEARNING_ENABLED,
    BATCH_LEARNING_INTERVAL,
)
from app.services.max.token_tracker import token_tracker
from app.services.max.desks import AIDeskManager, TaskStatus

logger = logging.getLogger("max.api")
router = APIRouter(prefix="/max", tags=["MAX AI Assistant"])


async def _safe_background(coro, label: str):
    """Run a coroutine in background, logging any errors without crashing."""
    try:
        await coro
    except Exception as e:
        logger.warning(f"Background {label} failed: {e}")

# Brain instances (shared across requests)
conversation_tracker = ConversationTracker()

# Unified desk manager (replaces both legacy DeskManager and AIDeskManager)
from app.services.max.desks.desk_manager import desk_manager
ai_desk_manager = desk_manager


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    history: List[Dict[str, str]] = []
    image_filename: Optional[str] = None
    desk: Optional[str] = None
    conversation_id: Optional[str] = None
    channel: Optional[str] = None  # "telegram", "web", etc.


TELEGRAM_DIRECTIVE = (
    "\n\n## CHANNEL: TELEGRAM\n"
    "This message is from Telegram. Respond ultra-short and direct.\n"
    "- No markdown headers, no bullet points unless specifically needed.\n"
    "- No greetings, no filler, no sign-offs.\n"
    "- Keep responses under 3 sentences when possible.\n"
    "- If the answer is a single fact or number, just say it.\n"
    "- IMPORTANT: You MUST still use ```tool blocks when actions are needed (web_search, quotes, etc). "
    "Tool blocks are the ONLY exception to the plain text rule — they are required for execution."
)


class ChatResponse(BaseModel):
    response: str
    model_used: str
    fallback_used: bool = False
    tool_results: Optional[List[Dict[str, Any]]] = None


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    desk_id: Optional[str] = None
    domains: List[str] = []
    priority: int = 5


class TelegramMessageRequest(BaseModel):
    message: str
    urgent: bool = False


class PresentRequest(BaseModel):
    topic: str
    source_content: Optional[str] = None
    image_count: int = 3


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

        # Append channel-specific directives
        if request.channel == "telegram" and enriched_prompt:
            enriched_prompt += TELEGRAM_DIRECTIVE

        response = await ai_router.chat(messages, model=model, image_filename=request.image_filename, desk=request.desk, system_prompt=enriched_prompt)

        # Multi-turn tool loop: execute tools, feed results back, allow follow-up tools (max 3 rounds)
        tool_results_list = []
        final_content = response.content
        loop_messages = list(messages)
        current_response = response

        for _tool_round in range(3):
            tool_calls = parse_tool_blocks(current_response.content)
            if not tool_calls:
                break

            round_results = []
            for tc in tool_calls:
                # Inject image_filename into quote tools so uploaded photos flow through
                if request.image_filename and tc.get("tool") in ("create_quick_quote", "photo_to_quote") and "image_filename" not in tc:
                    tc["image_filename"] = request.image_filename
                result = execute_tool(tc, desk=request.desk)
                entry = {"tool": result.tool, "success": result.success, "result": result.result, "error": result.error}
                round_results.append(entry)
                tool_results_list.append(entry)

            # Build tool summary and ask AI for follow-up
            tool_summary_parts = []
            for r in round_results:
                if r["success"] and r["result"]:
                    tool_summary_parts.append(f"[{r['tool']}] Result:\n{json.dumps(r['result'], indent=2, default=str)[:3000]}")
                else:
                    tool_summary_parts.append(f"[{r['tool']}] Error: {r.get('error', 'Unknown')}")
            tool_summary = "\n\n".join(tool_summary_parts)

            is_last_round = _tool_round >= 2
            followup_instruction = (
                "[SYSTEM: Tool results below — use this data to give a complete, accurate answer. Do NOT output more tool blocks.]"
                if is_last_round else
                "[SYSTEM: Tool results below. You may call additional tools if needed to complete the task, or give a final answer.]"
            )

            loop_messages.append(AIMessage(role="assistant", content=strip_tool_blocks(current_response.content)))
            loop_messages.append(AIMessage(role="user", content=f"{followup_instruction}\n\n{tool_summary}"))

            current_response = await ai_router.chat(loop_messages, model=model, desk=request.desk, system_prompt=enriched_prompt)
            final_content = strip_tool_blocks(final_content) + "\n\n" + current_response.content

        # Track conversation in background
        conv_id = request.conversation_id or str(uuid.uuid4())
        conversation_tracker.add_message(conv_id, "user", request.message)
        conversation_tracker.add_message(conv_id, "assistant", strip_tool_blocks(final_content))
        background_tasks.add_task(conversation_tracker.check_and_summarize, conv_id)

        # Learning: real-time (every exchange) or batch (every N messages)
        if REALTIME_LEARNING_ENABLED:
            background_tasks.add_task(
                conversation_tracker.learn_from_exchange,
                conv_id, request.message, response.content
            )
        elif BATCH_LEARNING_ENABLED:
            msg_count = conversation_tracker.get_message_count(conv_id)
            if msg_count > 0 and msg_count % BATCH_LEARNING_INTERVAL == 0:
                background_tasks.add_task(
                    conversation_tracker.learn_from_exchange,
                    conv_id, request.message, response.content
                )

        # Log token usage
        input_text = request.message + "".join(h.get("content", "") for h in request.history[-10:])
        token_tracker.log_chat(response.model_used, input_text, final_content, "chat", conv_id)

        resp = ChatResponse(
            response=sanitize_output(final_content),
            model_used=response.model_used,
            fallback_used=response.fallback_used,
            tool_results=tool_results_list if tool_results_list else None,
        )
        return resp
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

    # Append channel-specific directives
    if request.channel == "telegram" and enriched_prompt:
        enriched_prompt += TELEGRAM_DIRECTIVE

    # Conversation tracking ID
    conv_id = request.conversation_id or str(uuid.uuid4())
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

            # Multi-turn tool loop: execute tools, allow follow-up tools (max 3 rounds)
            tool_results_list = []
            loop_messages = list(messages)
            current_text = full_response

            for _tool_round in range(3):
                tool_calls = parse_tool_blocks(current_text)
                if not tool_calls:
                    break

                round_results = []
                for tc in tool_calls:
                    # Inject image_filename into quote tools so uploaded photos flow through
                    if request.image_filename and tc.get("tool") in ("create_quick_quote", "photo_to_quote") and "image_filename" not in tc:
                        tc["image_filename"] = request.image_filename
                    result = execute_tool(tc, desk=request.desk)
                    round_results.append(result)
                    tool_results_list.append(result)
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': result.tool, 'success': result.success, 'result': result.result, 'error': result.error})}\n\n"

                tool_summary_parts = []
                for r in round_results:
                    if r.success and r.result:
                        tool_summary_parts.append(f"[{r.tool}] Result:\n{json.dumps(r.result, indent=2, default=str)[:3000]}")
                    else:
                        tool_summary_parts.append(f"[{r.tool}] Error: {r.error}")
                tool_summary = "\n\n".join(tool_summary_parts)

                is_last_round = _tool_round >= 2
                followup_instruction = (
                    "[SYSTEM: Tool results below — use this data to give a complete, accurate answer. Do NOT output more tool blocks.]"
                    if is_last_round else
                    "[SYSTEM: Tool results below. You may call additional tools if needed to complete the task, or give a final answer.]"
                )

                loop_messages.append(AIMessage(role="assistant", content=strip_tool_blocks(current_text)))
                loop_messages.append(AIMessage(role="user", content=f"{followup_instruction}\n\n{tool_summary}"))

                yield f"data: {json.dumps({'type': 'text', 'content': chr(10) + chr(10)})}\n\n"
                followup_text = ""
                async for chunk, m_used in ai_router.chat_stream(loop_messages, model=model, desk=request.desk, system_prompt=enriched_prompt):
                    model_used = m_used
                    safe_chunk = sanitize_output(chunk)
                    followup_text += safe_chunk
                    yield f"data: {json.dumps({'type': 'text', 'content': safe_chunk})}\n\n"

                current_text = followup_text
                full_response = strip_tool_blocks(full_response) + "\n\n" + followup_text

            # Track assistant response — fire-and-forget background tasks
            conversation_tracker.add_message(conv_id, "assistant", strip_tool_blocks(full_response))
            asyncio.create_task(_safe_background(
                conversation_tracker.check_and_summarize(conv_id),
                "summarization"
            ))
            # Learning: real-time (every exchange) or batch (every N messages)
            if REALTIME_LEARNING_ENABLED:
                asyncio.create_task(_safe_background(
                    conversation_tracker.learn_from_exchange(conv_id, request.message, full_response),
                    "real-time learning"
                ))
            elif BATCH_LEARNING_ENABLED:
                msg_count = conversation_tracker.get_message_count(conv_id)
                if msg_count > 0 and msg_count % BATCH_LEARNING_INTERVAL == 0:
                    asyncio.create_task(_safe_background(
                        conversation_tracker.learn_from_exchange(conv_id, request.message, full_response),
                        "batch learning"
                    ))

            # Log token usage
            input_text = request.message + "".join(h.get("content", "") for h in request.history[-10:])
            token_tracker.log_chat(model_used, input_text, full_response, "chat/stream", conv_id)

            yield f"data: {json.dumps({'type': 'done', 'model_used': model_used, 'conversation_id': conv_id})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@router.post("/present")
async def generate_presentation(request: PresentRequest):
    """Generate a structured presentation for a given topic."""
    from app.services.max.presentation_builder import build_presentation

    try:
        result = await build_presentation(
            topic=request.topic,
            source_content=request.source_content,
            image_count=request.image_count,
        )
        return result
    except Exception as e:
        logger.error(f"Presentation generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/present/pdf")
async def presentation_to_pdf(data: dict):
    """Render presentation data as PDF and return the file."""
    from app.services.max.tool_executor import _render_presentation_pdf
    from fastapi.responses import FileResponse

    try:
        pdf_path = _render_presentation_pdf(data)
        filename = os.path.basename(pdf_path)
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except Exception as e:
        logger.error(f"Presentation PDF error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presentations")
async def list_presentations():
    """List all saved presentation PDFs with metadata."""
    pres_dir = Path.home() / "empire-repo" / "backend" / "data" / "presentations"
    pres_dir.mkdir(parents=True, exist_ok=True)
    presentations = []
    for f in sorted(pres_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = f.stat()
        # Parse title from filename: YYMMDD_HHMM_slug.pdf
        stem = f.stem
        parts = stem.split("_", 2)
        title_slug = parts[2] if len(parts) >= 3 else stem
        title = title_slug.replace("-", " ").title()
        presentations.append({
            "filename": f.name,
            "title": title,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "url": f"/api/v1/max/presentations/{f.name}",
        })
    return {"presentations": presentations}


@router.get("/presentations/{filename}")
async def serve_presentation(filename: str):
    """Serve a saved presentation PDF."""
    from fastapi.responses import FileResponse
    pres_dir = Path.home() / "empire-repo" / "backend" / "data" / "presentations"
    file_path = pres_dir / filename
    if not file_path.exists() or not file_path.name.endswith(".pdf"):
        raise HTTPException(404, "Presentation not found")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)


@router.delete("/presentations/{filename}")
async def delete_presentation(filename: str):
    """Delete a saved presentation PDF."""
    pres_dir = Path.home() / "empire-repo" / "backend" / "data" / "presentations"
    file_path = pres_dir / filename
    if not file_path.exists():
        raise HTTPException(404, "Presentation not found")
    file_path.unlink()
    return {"status": "deleted", "filename": filename}


@router.post("/present/telegram")
async def presentation_to_telegram(data: dict):
    """Render presentation as PDF and send via Telegram."""
    from app.services.max.tool_executor import _render_presentation_pdf

    try:
        pdf_path = _render_presentation_pdf(data)
        # Send via Telegram
        from app.services.max.telegram_bot import TelegramBot
        bot = TelegramBot()
        telegram_sent = False
        if bot.is_configured:
            title = data.get("title", "Presentation")
            section_count = len(data.get("sections", []))
            caption = f"\U0001f4ca <b>{title}</b>\n{section_count} sections \u00b7 {data.get('model_used', 'AI')}"
            await bot.send_document(pdf_path, caption=caption)
            telegram_sent = True
        return {"success": True, "pdf_path": pdf_path, "telegram_sent": telegram_sent}
    except Exception as e:
        logger.error(f"Presentation Telegram error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_available_models():
    return {"models": ai_router.get_available_models()}


@router.get("/desks")
async def get_all_desks():
    return {"desks": desk_manager.get_all_desks()}


@router.get("/desks/status")
async def get_desk_statuses():
    """Get status of all AI desks (ForgeDesk, MarketDesk, SocialDesk, SupportDesk).
    Alias for /ai-desks/status — kept for convenience.
    """
    statuses = await ai_desk_manager.get_all_statuses()
    return {"desks": statuses}


@router.get("/desks/{desk_id}")
async def get_desk(desk_id: str):
    desk = desk_manager.get_desk_legacy(desk_id)
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


@router.get("/telegram/history")
async def get_telegram_history(chat_id: Optional[str] = None, limit: int = 50):
    """Get Telegram conversation history (persisted to disk)."""
    from app.services.max.telegram_bot import _TELEGRAM_CHAT_DIR, _get_history
    target = chat_id or (telegram_bot.founder_chat_id if telegram_bot.founder_chat_id else None)
    if not target:
        # Return list of all chat files
        chats = []
        for f in sorted(_TELEGRAM_CHAT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                import json as _j
                data = _j.loads(f.read_text())
                msgs = data.get("messages", [])
                chats.append({
                    "chat_id": f.stem,
                    "message_count": len(msgs),
                    "updated_at": data.get("updated_at"),
                    "last_message": msgs[-1]["content"][:100] if msgs else "",
                })
            except Exception:
                pass
        return {"chats": chats}
    messages = _get_history(str(target))
    return {"chat_id": str(target), "messages": messages[-limit:], "total": len(messages)}


@router.get("/brain/status")
async def brain_status():
    """Get MAX Brain status — memory counts, drive status, Ollama health."""
    from app.services.max.brain.brain_config import get_brain_path, get_db_path, OLLAMA_BASE_URL
    from app.services.max.brain.memory_store import MemoryStore
    import httpx

    brain_path = get_brain_path()
    db_path = get_db_path()
    is_external = False  # brain is local-only now (NVMe primary)

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


# ── AI Desk Delegation System ────────────────────────────────────────────


class DeskTaskRequest(BaseModel):
    title: str
    description: str
    priority: str = "normal"
    customer_name: Optional[str] = None
    source: str = "founder"
    conversation_id: Optional[str] = None


@router.post("/ai-desks/tasks")
async def submit_desk_task(request: DeskTaskRequest):
    """Submit a task to the AI desk delegation system.
    Task is routed to the appropriate desk automatically.
    """
    task = await ai_desk_manager.submit_task(
        title=request.title,
        description=request.description,
        priority=request.priority,
        customer_name=request.customer_name,
        source=request.source,
        conversation_id=request.conversation_id,
    )
    return {
        "task_id": task.id,
        "title": task.title,
        "state": task.state.value,
        "escalation_reason": task.escalation_reason,
        "result": task.result,
        "actions": [{"action": a.action, "detail": a.detail, "timestamp": a.timestamp} for a in task.actions],
    }


@router.get("/ai-desks/status")
async def get_ai_desk_statuses():
    """Get status of all AI desks."""
    statuses = await ai_desk_manager.get_all_statuses()
    return {"desks": statuses}


@router.get("/ai-desks/{desk_id}/detail")
async def get_ai_desk_detail(desk_id: str):
    """Get detailed status and task history for a single AI desk."""
    desk = ai_desk_manager.get_desk(desk_id)
    if not desk:
        raise HTTPException(404, f"Desk '{desk_id}' not found")
    status = await desk.report_status()
    # Also include brain memory logs for this desk
    try:
        from app.services.max.brain.memory_store import MemoryStore
        store = MemoryStore()
        memories = store.search(query=desk.desk_name, category="desk_action", limit=20)
        status["brain_logs"] = [
            {"content": m.get("content", ""), "created_at": m.get("created_at", ""), "importance": m.get("importance", 5)}
            for m in memories
        ]
    except Exception:
        status["brain_logs"] = []
    return status


@router.get("/ai-desks/briefing")
async def get_desk_briefing():
    """Get morning briefing from all AI desks."""
    briefing = await ai_desk_manager.generate_briefing()
    return {"briefing": briefing}


@router.get("/ai-desks/report")
async def get_desk_daily_report():
    """Get end-of-day desk report."""
    report = await ai_desk_manager.generate_daily_report()
    return {"report": report}


# ── TTS (Text-to-Speech) ─────────────────────────────────────────────


class TTSRequest(BaseModel):
    text: str
    voice: str = "rex"  # Available: ara, rex, sal, eve, leo


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech audio (MP3) via xAI Grok TTS. Voice: Rex (default)."""
    from app.services.max.tts_service import tts_service

    if not tts_service.is_configured:
        raise HTTPException(status_code=503, detail="TTS not configured — XAI_API_KEY missing")

    audio_bytes = await tts_service.synthesize_for_web(request.text)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS synthesis failed")

    from fastapi.responses import Response
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=max_speech.mp3"},
    )


# ── Agent Code of Conduct ─────────────────────────────────────────────


@router.get("/conduct")
async def get_all_agent_conducts():
    """Get all agent codes of conduct."""
    from app.services.max.conduct import get_all_conducts
    return get_all_conducts()


@router.get("/conduct/{agent_id}")
async def get_agent_conduct(agent_id: str):
    """Get code of conduct for a specific agent."""
    from app.services.max.conduct import get_conduct
    conduct = get_conduct(agent_id)
    if not conduct:
        raise HTTPException(status_code=404, detail=f"No conduct defined for agent '{agent_id}'")
    return conduct


# ── Security Scanner ──────────────────────────────────────────────────


@router.get("/security/scan")
async def run_security_scan():
    """Run the security scanner on the Empire codebase."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))
    from pathlib import Path as P
    from security_scan import SecurityScanner

    empire_root = P(__file__).parent.parent.parent.parent.parent
    scanner = SecurityScanner(empire_root)
    # Quick scan (no npm audit — that's slow)
    for scan_dir in scanner.__class__.__dict__.get("SCAN_DIRS", []) or ["backend", "founder_dashboard/src"]:
        dir_path = empire_root / scan_dir
        if dir_path.exists():
            scanner.scan_directory(dir_path)

    return {
        "scan_time": datetime.utcnow().isoformat(),
        "stats": scanner.stats,
        "findings_count": len(scanner.findings),
        "critical": [f for f in scanner.findings if f["severity"] == "CRITICAL"][:10],
        "high": [f for f in scanner.findings if f["severity"] == "HIGH"][:20],
        "medium": [f for f in scanner.findings if f["severity"] == "MEDIUM"][:10],
    }
