"""
MAX API Router - Endpoints for AI Assistant Manager.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from app.services.max.ai_router import ai_router, AIMessage, AIModel
from app.services.max.desk_manager import desk_manager, TaskStatus
from app.services.max.telegram_bot import telegram_bot

logger = logging.getLogger("max.api")
router = APIRouter(prefix="/max", tags=["MAX AI Assistant"])


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    history: List[Dict[str, str]] = []


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
async def chat_with_max(request: ChatRequest):
    try:
        messages = [AIMessage(role=h["role"], content=h["content"]) for h in request.history]
        messages.append(AIMessage(role="user", content=request.message))
        model = None
        if request.model:
            try:
                model = AIModel(request.model)
            except ValueError:
                pass
        response = await ai_router.chat(messages, model=model)
        return ChatResponse(response=response.content, model_used=response.model_used, fallback_used=response.fallback_used)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
