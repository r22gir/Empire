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
from app.services.max.guardrails import check_input, sanitize_output, SAFE_REFUSAL, is_founder_message
from app.services.max.security.sanitizer import sanitizer as input_sanitizer
from app.services.max.tool_executor import parse_tool_blocks, strip_tool_blocks, execute_tool
from app.services.max.grounding_verifier import verify_web_response, log_to_audit
from app.services.max.response_quality_engine import quality_engine, Channel
from app.services.max.system_prompt import get_system_prompt_with_brain
from app.services.max.brain import ContextBuilder, ConversationTracker
from app.services.max.brain.brain_config import (
    REALTIME_LEARNING_ENABLED,
    BATCH_LEARNING_ENABLED,
    BATCH_LEARNING_INTERVAL,
)
from app.services.max.token_tracker import token_tracker
from app.services.max.desks import AIDeskManager, TaskStatus

try:
    from app.services.max.access_control import access_controller
except ImportError:
    access_controller = None

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
    chat_id: Optional[str] = None  # Telegram chat ID for founder detection


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
    msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
    founder = is_founder_message(msg_ctx)
    if founder:
        logger.info(f"Founder message detected via chat_id={request.chat_id}")

    is_safe, reason = check_input(request.message, message_context=msg_ctx)
    if not is_safe:
        logger.warning(f"Blocked input ({reason}): {request.message[:100]}")
        return ChatResponse(response=SAFE_REFUSAL, model_used="guardrail", fallback_used=False)

    # v6.0 unified sanitizer — audit logging + SQL/XSS checks
    sec_result = input_sanitizer.check(request.message, channel="chat", session_id=request.conversation_id or "")
    if not sec_result["safe"]:
        logger.warning(f"Sanitizer blocked ({sec_result['threat_type']}): {request.message[:100]}")
        return ChatResponse(response=SAFE_REFUSAL, model_used="guardrail", fallback_used=False)

    for msg in request.history[-3:]:
        content = msg.get("content", "")
        # Skip guardrail check on system-injected context-pack messages
        if content.startswith("[Context from previous sessions]") or content == "Context loaded. Ready.":
            continue
        hist_safe, _ = check_input(content)
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

        # Resolve access control user
        _ac_context = None
        if access_controller:
            try:
                _ac_user = access_controller.resolve_user(request.chat_id or request.conversation_id or "", request.channel or "web")
                if _ac_user:
                    _ac_context = {"user": _ac_user}
            except Exception as _ac_err:
                logger.debug(f"Access control resolve failed: {_ac_err}")

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
                result = execute_tool(tc, desk=request.desk, access_context=_ac_context)
                entry = {"tool": result.tool, "success": result.success, "result": result.result, "error": result.error}
                round_results.append(entry)
                tool_results_list.append(entry)

            # Build tool summary and ask AI for follow-up
            tool_summary_parts = []
            for r in round_results:
                if r["success"] and r["result"]:
                    # Give web_read more room so AI has enough content to cite accurately
                    limit = 5000 if r['tool'] == 'web_read' else 3000
                    tool_summary_parts.append(f"[{r['tool']}] Result:\n{json.dumps(r['result'], indent=2, default=str)[:limit]}")
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
            # Only keep the FINAL round's response — previous rounds are context for the AI, not for the user
            final_content = current_response.content

        # Grounding verification: strip hallucinated citations from web-sourced responses
        if tool_results_list:
            has_web_tools = any(tr.get("tool") in ("web_search", "web_read") for tr in tool_results_list)
            if has_web_tools:
                try:
                    verification = verify_web_response(final_content, tool_results_list)
                    if verification.claims_stripped > 0:
                        logger.info(f"Grounding: {verification.claims_verified} verified, {verification.claims_stripped} stripped, {verification.phantom_citations_removed} phantom citations removed")
                    final_content = verification.verified
                    log_to_audit(
                        user_query=request.message,
                        verification=verification,
                        model_used=response.model_used,
                    )
                except Exception as e:
                    logger.warning(f"Grounding verification failed: {e}")

        # Universal quality check on final response
        chat_channel = Channel.TELEGRAM if (hasattr(request, 'channel') and request.channel == 'telegram') else Channel.CHAT
        qr = quality_engine.validate(final_content, channel=chat_channel, founder_override=founder)
        if qr.fixed_count > 0:
            logger.info(f"Quality engine fixed {qr.fixed_count} issues in {chat_channel.value} response")
            final_content = qr.cleaned

        # Log to accuracy monitor (all channels, not just web-sourced)
        if qr.issues or not tool_results_list:
            try:
                from app.services.max.accuracy_monitor import accuracy_monitor
                accuracy_monitor.log_audit(
                    user_query=request.message,
                    response_text=final_content,
                    verification=type('V', (), {
                        'claims_found': len(qr.issues),
                        'claims_verified': len(qr.issues) - len([i for i in qr.issues if i.severity.value == 'critical']),
                        'claims_stripped': qr.fixed_count,
                        'phantom_citations_removed': 0,
                    })(),
                    model_used=response.model_used,
                    channel=chat_channel.value,
                    output_type="chat",
                    quality_severity=qr.severity,
                    fixed_by_engine=qr.fixed_count,
                )
            except Exception as e:
                logger.debug(f"Quality audit log failed: {e}")

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
    msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
    founder = is_founder_message(msg_ctx)
    if founder:
        logger.info(f"Founder message (stream) detected via chat_id={request.chat_id}")

    is_safe, reason = check_input(request.message, message_context=msg_ctx)
    if not is_safe:
        logger.warning(f"Blocked input ({reason}): {request.message[:100]}")
        async def refusal_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': SAFE_REFUSAL})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'guardrail'})}\n\n"
        return StreamingResponse(refusal_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    # v6.0 — unified sanitizer check on streaming endpoint
    sec_result = input_sanitizer.check(request.message, channel="chat", session_id=request.conversation_id or "")
    if not sec_result["safe"]:
        logger.warning(f"Sanitizer blocked stream ({sec_result['threat_type']}): {request.message[:100]}")
        async def refusal_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': SAFE_REFUSAL})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'guardrail'})}\n\n"
        return StreamingResponse(refusal_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    for msg in request.history[-3:]:
        content = msg.get("content", "")
        if content.startswith("[Context from previous sessions]") or content == "Context loaded. Ready.":
            continue
        hist_safe, _ = check_input(content)
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

    # Resolve access control user for streaming
    _stream_ac_context = None
    if access_controller:
        try:
            _stream_ac_user = access_controller.resolve_user(request.chat_id or request.conversation_id or "", request.channel or "web")
            if _stream_ac_user:
                _stream_ac_context = {"user": _stream_ac_user}
        except Exception as _ac_err:
            logger.debug(f"Access control resolve failed (stream): {_ac_err}")

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
                    result = execute_tool(tc, desk=request.desk, access_context=_stream_ac_context)
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
                # Only keep the FINAL round's response — previous rounds are context for the AI, not for the user
                full_response = followup_text

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


# ── v6.0 Pipeline Endpoints ─────────────────────────────────────────

class PipelineCreateRequest(BaseModel):
    title: str
    description: str = ""
    source: str = "api"
    channel: str = "web"


class PipelineApprovalRequest(BaseModel):
    reason: str = ""


@router.post("/pipeline")
async def create_pipeline(request: PipelineCreateRequest, background_tasks: BackgroundTasks):
    """Create a new pipeline — AI decomposes task into ordered subtasks."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.submit_pipeline(
        title=request.title,
        description=request.description or request.title,
        source=request.source,
        channel=request.channel,
    )
    if telegram_bot.is_configured:
        count = len(result.get("subtasks", []))
        background_tasks.add_task(
            telegram_bot.send_message,
            f"🚀 <b>New Pipeline</b>\n\n<b>{request.title}</b>\n{count} subtask(s) created\nSource: {request.source}",
        )
    return result


@router.get("/pipeline")
async def list_pipelines(active_only: bool = False, limit: int = 20):
    """List pipelines with progress summaries."""
    from app.services.max.pipeline import pipeline_engine
    if active_only:
        return {"pipelines": pipeline_engine.get_active_pipelines()}
    return {"pipelines": pipeline_engine.get_all_pipelines(limit=limit)}


@router.get("/pipeline/review")
async def get_review_tasks():
    """Get all subtasks awaiting founder approval."""
    from app.services.max.pipeline import pipeline_engine
    return {"tasks": pipeline_engine.get_review_tasks()}


@router.get("/pipeline/precheck")
async def pipeline_precheck():
    """Check API key dependencies and notify of blockers."""
    from app.services.max.pipeline import pipeline_engine
    return await pipeline_engine.pre_check_dependencies()


@router.get("/pipeline/audit")
async def pipeline_audit():
    """Audit ecosystem for unwired endpoints, missing frontends, and backlog items."""
    from app.services.max.pipeline import pipeline_engine
    return await pipeline_engine.audit_ecosystem()


@router.get("/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get a pipeline with all subtasks and progress."""
    from app.services.max.pipeline import pipeline_engine
    result = pipeline_engine.get_pipeline(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.post("/pipeline/{pipeline_id}/cancel")
async def cancel_pipeline(pipeline_id: str):
    """Cancel an active pipeline and all pending subtasks."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.cancel_pipeline(pipeline_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/pipeline/task/{task_id}/approve")
async def approve_pipeline_task(task_id: str):
    """Founder approves a subtask in review state."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.approve_subtask(task_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/pipeline/task/{task_id}/reject")
async def reject_pipeline_task(task_id: str, request: PipelineApprovalRequest = PipelineApprovalRequest()):
    """Founder rejects a subtask — sends back for re-execution."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.reject_subtask(task_id, request.reason)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/security/stats")
async def security_stats():
    """Get security layer stats — blocked inputs, rate limits, audit counts."""
    stats = input_sanitizer.get_stats()
    # Count audit log entries
    audit_path = Path.home() / "empire-repo" / "backend" / "data" / "security" / "audit_log.jsonl"
    audit_count = 0
    if audit_path.exists():
        with open(audit_path) as f:
            audit_count = sum(1 for _ in f)
    stats["audit_log_entries"] = audit_count
    return stats


@router.get("/security/audit")
async def security_audit(limit: int = 50):
    """Get recent security audit log entries."""
    audit_path = Path.home() / "empire-repo" / "backend" / "data" / "security" / "audit_log.jsonl"
    if not audit_path.exists():
        return {"entries": [], "total": 0}
    entries = []
    with open(audit_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(__import__("json").loads(line))
                except Exception:
                    pass
    # Return most recent first
    entries.reverse()
    return {"entries": entries[:limit], "total": len(entries)}


@router.get("/intelligence/brief")
async def get_morning_brief():
    """Get the latest morning brief (or generate on-demand)."""
    import json as _json
    brief_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "morning_brief.json"
    if brief_path.exists():
        with open(brief_path) as f:
            return _json.load(f)
    # Generate on-demand if none exists
    from app.services.max.desks.desk_scheduler import desk_scheduler
    await desk_scheduler._generate_morning_brief()
    if brief_path.exists():
        with open(brief_path) as f:
            return _json.load(f)
    return {"date": None, "html": "No brief available yet.", "generated_at": None}


@router.get("/intelligence/weekly")
async def get_weekly_report():
    """Get the latest weekly report."""
    import json as _json
    report_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "weekly_report.json"
    if report_path.exists():
        with open(report_path) as f:
            return _json.load(f)
    return {"week_of": None, "html": "No weekly report available yet.", "generated_at": None}


@router.post("/intelligence/brief/generate")
async def generate_morning_brief():
    """Force-generate a fresh morning brief now."""
    from app.services.max.desks.desk_scheduler import desk_scheduler
    await desk_scheduler._generate_morning_brief()
    import json as _json
    brief_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "morning_brief.json"
    if brief_path.exists():
        with open(brief_path) as f:
            return _json.load(f)
    return {"status": "generated"}


@router.post("/intelligence/weekly/generate")
async def generate_weekly_report():
    """Force-generate a fresh weekly report now."""
    from app.services.max.desks.desk_scheduler import desk_scheduler
    await desk_scheduler._generate_weekly_report()
    import json as _json
    report_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "weekly_report.json"
    if report_path.exists():
        with open(report_path) as f:
            return _json.load(f)
    return {"status": "generated"}


@router.get("/intelligence/cost-per-desk")
async def cost_per_desk():
    """Get AI cost breakdown per desk from token tracker logs."""
    try:
        from app.services.max.token_tracker import token_tracker
        from app.db.database import get_db
        import json as _json

        # Query token usage grouped by desk/caller
        costs_by_desk = {}
        with get_db() as conn:
            rows = conn.execute(
                """SELECT metadata, cost_usd FROM token_usage
                   WHERE date(timestamp) >= date('now', '-30 days')"""
            ).fetchall()
            for row in rows:
                cost = row[1] if len(row) > 1 else 0
                meta = {}
                try:
                    meta = _json.loads(row[0]) if row[0] else {}
                except Exception:
                    pass
                desk = meta.get("desk_id") or meta.get("caller") or "general"
                costs_by_desk[desk] = costs_by_desk.get(desk, 0) + (cost or 0)

        # Sort by cost descending
        sorted_desks = sorted(costs_by_desk.items(), key=lambda x: x[1], reverse=True)
        return {
            "period": "30d",
            "desks": [{"desk_id": d, "cost_usd": round(c, 4)} for d, c in sorted_desks],
            "total_usd": round(sum(c for _, c in sorted_desks), 4),
        }
    except Exception as e:
        # Fallback: return empty if token_usage table doesn't have the right columns
        return {"period": "30d", "desks": [], "total_usd": 0, "note": str(e)}


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


@router.get("/telegram/image/{filename}")
async def serve_telegram_image(filename: str):
    """Serve a Telegram-uploaded image."""
    from fastapi.responses import FileResponse
    img_path = Path.home() / "empire-repo" / "backend" / "data" / "uploads" / "images" / filename
    if not img_path.exists() or not img_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    # Prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = img_path.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(str(img_path), media_type=media_types.get(ext, "image/jpeg"))


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


class AccessConfirmRequest(BaseModel):
    session_id: str


class AccessPinRequest(BaseModel):
    session_id: str
    pin: str


@router.post("/access/confirm")
async def access_confirm(request: AccessConfirmRequest):
    if not access_controller:
        raise HTTPException(status_code=501, detail="Access control not available")
    result = access_controller.confirm_session(request.session_id)
    if not result:
        raise HTTPException(status_code=400, detail="Session expired or not found")
    tr = execute_tool({"tool": result["tool_name"], **result["tool_params"]}, desk=result.get("desk"))
    access_controller.audit_log(result.get("user_id", ""), result["tool_name"], 2, "confirmed", channel="web")
    return {"tool": tr.tool, "success": tr.success, "result": tr.result, "error": tr.error}


@router.post("/access/pin")
async def access_pin(request: AccessPinRequest):
    if not access_controller:
        raise HTTPException(status_code=501, detail="Access control not available")
    result = access_controller.authorize_pin_session(request.session_id, request.pin)
    if not result:
        raise HTTPException(status_code=403, detail="Invalid PIN or session expired")
    tr = execute_tool({"tool": result["tool_name"], **result["tool_params"]}, desk=result.get("desk"))
    access_controller.audit_log(result.get("user_id", ""), result["tool_name"], 3, "pin_authorized", channel="web")
    return {"tool": tr.tool, "success": tr.success, "result": tr.result, "error": tr.error}


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


@router.post("/ai-desks/trigger")
async def trigger_desk_task(request: DeskTaskRequest):
    """Manually trigger a desk task immediately (bypasses schedule).
    Executes with AI, stores result, sends Telegram notification."""
    from app.services.max.desks.desk_scheduler import desk_scheduler
    import asyncio

    # Determine desk from title/description keywords, or use source as desk hint
    desk_id = request.source if request.source in [
        "forge", "sales", "marketing", "support", "finance", "it",
        "market", "clients", "contractors", "website", "legal", "lab",
    ] else None

    if not desk_id:
        # Route automatically
        task = await ai_desk_manager.submit_task(
            title=request.title,
            description=request.description,
            priority=request.priority,
            source="manual_trigger",
        )
        return {
            "task_id": task.id,
            "title": task.title,
            "desk": "auto-routed",
            "state": task.state.value,
            "result": task.result,
        }

    # Direct desk execution with AI + Telegram
    asyncio.create_task(
        desk_scheduler.trigger_now(desk_id, request.title, request.description)
    )
    return {
        "status": "triggered",
        "desk": desk_id,
        "title": request.title,
        "message": f"Task sent to {desk_id} desk. Result will be sent to Telegram.",
    }


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


# ── Speech-to-Text (STT) ─────────────────────────────────────────────────────

from fastapi import UploadFile, File

@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = "es"):
    """
    Transcribe uploaded audio to text using Groq Whisper.
    Accepts: mp3, mp4, m4a, wav, ogg, flac, webm (max 25MB).
    Default language: Spanish.
    """
    from app.services.max.stt_service import stt_service

    if not stt_service.is_configured:
        raise HTTPException(status_code=503, detail="STT not configured — GROQ_API_KEY missing")

    # Save temp file
    import tempfile
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        transcript = await stt_service.transcribe(tmp_path, language=language)
        return {"text": transcript, "language": language, "filename": file.filename}
    finally:
        tmp_path.unlink(missing_ok=True)



# ── System Report & Change Log ──────────────────────────────────────────────

@router.get("/system-report")
async def get_system_report():
    """
    Comprehensive system report for MAX: modules, connectivity, recent changes,
    desk statuses, and actionable insights. Serves as a tutorial guide and
    continuous update feed.
    """
    import psutil
    import subprocess

    report: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "system": {},
        "modules": [],
        "recent_changes": [],
        "desk_reports": [],
        "connectivity": [],
        "suggestions": [],
        "bugs": [],
    }

    # ── System Stats ──
    try:
        from app.routers.system_monitor import _get_disk_summary
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = _get_disk_summary()
        report["system"] = {
            "cpu_percent": cpu,
            "memory_used_gb": round(mem.used / (1024**3), 1),
            "memory_total_gb": round(mem.total / (1024**3), 1),
            "memory_percent": mem.percent,
            "disk_used_gb": disk["used_gb"],
            "disk_total_gb": disk["total_gb"],
            "disk_percent": disk["percent"],
            "disk_drives": disk["drives"],
            "uptime": _get_uptime(),
        }
    except Exception as e:
        report["system"]["error"] = str(e)

    # ── Module Inventory ──
    modules = [
        {"name": "MAX Chat (SSE)", "endpoint": "/max/chat/stream", "frontend": True, "status": "active"},
        {"name": "MAX Desks", "endpoint": "/max/desks", "frontend": True, "status": "active"},
        {"name": "Chat History", "endpoint": "/chats/*", "frontend": True, "status": "active"},
        {"name": "Quotes", "endpoint": "/quotes/*", "frontend": True, "status": "active"},
        {"name": "Files", "endpoint": "/files/*", "frontend": True, "status": "active"},
        {"name": "System Monitor", "endpoint": "/system/stats", "frontend": True, "status": "active"},
        {"name": "Memory/Brain", "endpoint": "/memory/*", "frontend": True, "status": "active"},
        {"name": "TTS (Voice)", "endpoint": "/max/tts", "frontend": True, "status": "active"},
        {"name": "STT (Speech)", "endpoint": "/api/transcribe", "frontend": True, "status": "active"},
        {"name": "Notifications", "endpoint": "/notifications/*", "frontend": "partial", "status": "active"},
        {"name": "CraftForge", "endpoint": "/craftforge/*", "frontend": False, "status": "backend_only"},
        {"name": "SupportForge", "endpoint": "/tickets/*", "frontend": False, "status": "backend_only"},
        {"name": "Finance/Economic", "endpoint": "/economic/*", "frontend": False, "status": "backend_only"},
        {"name": "Tasks", "endpoint": "/tasks/*", "frontend": False, "status": "backend_only"},
        {"name": "Contacts/CRM", "endpoint": "/contacts/*", "frontend": False, "status": "backend_only"},
        {"name": "Vision/Mockups", "endpoint": "/vision/*", "frontend": False, "status": "backend_only"},
        {"name": "Shipping", "endpoint": "/shipping/*", "frontend": False, "status": "backend_only"},
        {"name": "Docker Manager", "endpoint": "/docker/*", "frontend": False, "status": "backend_only"},
        {"name": "Ollama Manager", "endpoint": "/ollama/*", "frontend": False, "status": "backend_only"},
        {"name": "Intake Portal", "endpoint": "/intake/*", "frontend": True, "status": "active"},
    ]
    report["modules"] = modules

    # ── Recent Git Changes ──
    try:
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-decorate", "-20"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.strip().split(" ", 1)
                    report["recent_changes"].append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else "",
                    })

        # Recent file changes (last 48h)
        diff_result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~5", "HEAD"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if diff_result.returncode == 0:
            report["recent_diff_summary"] = diff_result.stdout.strip().split("\n")[-1] if diff_result.stdout.strip() else ""
    except Exception as e:
        report["recent_changes"].append({"error": str(e)})

    # ── AI Desk Reports ──
    try:
        desks = ai_desk_manager.list_desks()
        for d in desks:
            desk_info = {
                "id": d.get("id", ""),
                "name": d.get("name", ""),
                "status": d.get("status", "idle"),
                "persona": d.get("persona", ""),
                "domains": d.get("domains", []),
                "can_report": [
                    "Generate daily summary",
                    "List pending tasks",
                    "Report on recent activity",
                    "Analyze performance metrics",
                ],
            }
            report["desk_reports"].append(desk_info)
    except Exception as e:
        report["desk_reports"].append({"error": str(e)})

    # ── Connectivity Check ──
    import aiohttp
    services_to_check = [
        ("Backend API", "http://localhost:8000/health"),
        ("Command Center", "http://localhost:3009"),
        ("AMP Portal", "http://localhost:3003"),
        ("Ollama", "http://localhost:11434/api/version"),
    ]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
        for name, url in services_to_check:
            try:
                async with session.get(url) as resp:
                    report["connectivity"].append({
                        "service": name, "url": url,
                        "status": "online" if resp.status < 500 else "error",
                        "code": resp.status,
                    })
            except Exception:
                report["connectivity"].append({
                    "service": name, "url": url,
                    "status": "offline", "code": 0,
                })

    # ── Known Bugs ──
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        env_content = env_path.read_text()
        if "GROQ_API_KEY=\n" in env_content or "GROQ_API_KEY=" == env_content.strip().split("\n")[-1]:
            report["bugs"].append({"severity": "medium", "desc": "GROQ_API_KEY is empty — STT/transcription won't work"})
    report["bugs"].append({"severity": "low", "desc": "Ollama running but no models downloaded"})
    report["bugs"].append({"severity": "medium", "desc": "CraftForge frontend shows hardcoded data despite 15 real backend endpoints"})
    report["bugs"].append({"severity": "low", "desc": "Video Call screen is a UI mockup only"})

    # ── Suggestions ──
    connected = sum(1 for m in modules if m["frontend"] is True)
    backend_only = sum(1 for m in modules if m["frontend"] is False)
    report["suggestions"] = [
        f"{backend_only} modules have backend endpoints but no frontend wiring — biggest gaps: CraftForge, Tasks, Finance",
        "Add a live Activity Feed to Command Center showing desk completions, quote updates, file uploads",
        "Wire CraftForge dashboard to real /craftforge/* endpoints (designs, jobs, inventory)",
        "Add Tasks panel to DesksScreen — show active tasks per desk from /tasks/* endpoints",
        "Enable daily auto-reports from each AI desk via scheduler",
    ]

    return report


def _get_uptime():
    """Get system uptime as human-readable string."""
    try:
        import psutil
        boot = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        mins = rem // 60
        if days > 0:
            return f"{days}d {hours}h {mins}m"
        return f"{hours}h {mins}m"
    except Exception:
        return "--"


@router.get("/changelog")
async def get_changelog():
    """Get recent system changes — git commits, file modifications, new features."""
    import subprocess
    repo_root = Path(__file__).parent.parent.parent.parent.parent

    result = {
        "generated_at": datetime.utcnow().isoformat(),
        "commits": [],
        "new_features": [],
        "modified_files": [],
    }

    try:
        # Last 30 commits with dates
        log = subprocess.run(
            ["git", "log", "--format=%H|%ai|%s", "-30"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if log.returncode == 0:
            for line in log.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 2)
                    result["commits"].append({
                        "hash": parts[0][:8],
                        "date": parts[1].strip(),
                        "message": parts[2] if len(parts) > 2 else "",
                    })

        # Files changed in last 5 commits
        diff = subprocess.run(
            ["git", "diff", "--name-status", "HEAD~5", "HEAD"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if diff.returncode == 0:
            for line in diff.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.strip().split("\t", 1)
                    if len(parts) == 2:
                        status_map = {"A": "added", "M": "modified", "D": "deleted"}
                        result["modified_files"].append({
                            "status": status_map.get(parts[0], parts[0]),
                            "file": parts[1],
                        })

        # Detect new features from commit messages
        for c in result["commits"][:10]:
            msg = c["message"].lower()
            if any(kw in msg for kw in ["add", "new", "feature", "build", "create", "implement"]):
                result["new_features"].append({
                    "date": c["date"],
                    "description": c["message"],
                })

    except Exception as e:
        result["error"] = str(e)

    return result
