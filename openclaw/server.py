"""
OpenClaw - Standalone AI Assistant Server

FastAPI server exposing chat, voice, skills management, and agent control APIs.

Start with:
    uvicorn openclaw.server:app --host 0.0.0.0 --port 7878
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel

from .agents.memory import AgentMemory
from .agents.orchestrator import Orchestrator
from .skills import (
    CalendarSkill,
    CodeSkill,
    EmpireBoxSkill,
    FileSkill,
    SearchSkill,
    Skill,
    SmartHomeSkill,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenClaw",
    description="Standalone AI assistant with plugin skills and autonomous agents",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_skills: Dict[str, Skill] = {}
_skill_enabled: Dict[str, bool] = {}
_orchestrator = Orchestrator()
_memory = AgentMemory(session_id="default")


def _register_default_skills() -> None:
    for skill_cls in [SearchSkill, CodeSkill, FileSkill, CalendarSkill, EmpireBoxSkill, SmartHomeSkill]:
        instance = skill_cls()
        _skills[instance.name] = instance
        _skill_enabled[instance.name] = instance.name in ("search", "code", "files", "calendar")


_register_default_skills()


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    use_skill: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    skill_used: Optional[str] = None
    session_id: str


class TaskRequest(BaseModel):
    task: Dict[str, Any]
    priority: int = 5


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"service": "OpenClaw", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok", "skills_loaded": len(_skills), "agents_registered": len(_orchestrator.list_agents())}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the AI assistant and receive a reply."""
    memory = AgentMemory(session_id=req.session_id or "default")
    memory.add("user", req.message)

    # Try to match a skill
    skill_used: Optional[str] = None
    reply: str = ""

    if req.use_skill and req.use_skill in _skills and _skill_enabled.get(req.use_skill):
        skill = _skills[req.use_skill]
        reply = await skill.execute(req.message, {"query": req.message})
        skill_used = req.use_skill
    else:
        for name, skill in _skills.items():
            if _skill_enabled.get(name) and skill.matches(req.message):
                reply = await skill.execute(req.message, {"query": req.message})
                skill_used = name
                break

    if not reply:
        reply = _fallback_ai_reply(req.message, memory)

    memory.add("assistant", reply)
    return ChatResponse(reply=reply, skill_used=skill_used, session_id=req.session_id or "default")


def _fallback_ai_reply(message: str, memory: AgentMemory) -> str:
    """Simple fallback when no AI provider is configured."""
    provider = os.getenv("AI_PROVIDER", "ollama")
    if provider == "ollama":
        return _ollama_chat(message, memory)
    # For other providers a proper SDK call would go here.
    return f"[OpenClaw] Received: '{message}'. Configure an AI provider in config.yaml for real responses."


def _ollama_chat(message: str, memory: AgentMemory) -> str:
    try:
        import httpx  # already in requirements
        ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        history = [{"role": m["role"], "content": m["content"]} for m in memory.get_recent(10)]
        payload = {"model": model, "messages": history, "stream": False}
        resp = httpx.post(f"{ollama_url}/api/chat", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama chat failed: %s", exc)
        return f"[OpenClaw] Ollama unavailable: {exc}. Start Ollama or configure another provider."


@app.post("/voice")
async def voice_input(file: UploadFile = File(...)):
    """Accept an audio upload, transcribe via Whisper, and return chat response."""
    from .voice.stt import WhisperSTT

    suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        stt = WhisperSTT()
        text = stt.transcribe(tmp_path)
        if not text:
            raise HTTPException(status_code=422, detail="Could not transcribe audio")
        req = ChatRequest(message=text)
        return await chat(req)
    finally:
        os.unlink(tmp_path)


@app.get("/skills")
async def list_skills():
    """List all available skills and their enabled state."""
    return [
        {
            "name": name,
            "description": skill.description,
            "enabled": _skill_enabled.get(name, False),
            "triggers": skill.triggers,
        }
        for name, skill in _skills.items()
    ]


@app.post("/skills/{name}/enable")
async def enable_skill(name: str):
    """Enable a skill by name."""
    if name not in _skills:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    _skill_enabled[name] = True
    return {"skill": name, "enabled": True}


@app.post("/skills/{name}/disable")
async def disable_skill(name: str):
    """Disable a skill by name."""
    if name not in _skills:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    _skill_enabled[name] = False
    return {"skill": name, "enabled": False}


@app.get("/agents")
async def list_agents():
    """List all registered agents."""
    return _orchestrator.list_agents()


@app.get("/agents/{name}/status")
async def agent_status(name: str):
    """Get status and stats for a named agent."""
    agents = {a["name"]: a for a in _orchestrator.list_agents()}
    if name not in agents:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    return agents[name]


@app.post("/agents/{name}/task")
async def assign_task(name: str, req: TaskRequest):
    """Assign a task to the named agent."""
    result = await _orchestrator.assign_task(name, req.task, req.priority)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Task failed"))
    return result


@app.post("/agents/{name}/pause")
async def pause_agent(name: str):
    """Pause the named agent."""
    from .agents.base import AgentStatus
    agent = _orchestrator.get_agent(name)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    agent.status = AgentStatus.PAUSED
    return {"agent": name, "status": "paused"}


@app.post("/agents/{name}/resume")
async def resume_agent(name: str):
    """Resume a paused agent."""
    from .agents.base import AgentStatus
    agent = _orchestrator.get_agent(name)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    agent.status = AgentStatus.IDLE
    return {"agent": name, "status": "idle"}


@app.get("/agents/queue")
async def view_queue():
    """View the current task queue."""
    return {"queue": _orchestrator.get_queue(), "metrics": _orchestrator.get_metrics()}
