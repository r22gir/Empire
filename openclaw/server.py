"""
OpenClaw AI Server — EmpireBox Command Center
FastAPI backend providing /chat, /health, and /skills endpoints.
Integrates with Ollama for AI responses and exposes EmpireBox skills.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

import aiohttp
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("openclaw")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="OpenClaw AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.yaml"
SKILLS_DIR = Path(__file__).parent / "skills"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

MAX_HISTORY_CONTEXT = 8

# ---------------------------------------------------------------------------
# Load skills
# ---------------------------------------------------------------------------
def _load_skills() -> list[dict]:
    skills: list[dict] = []
    if not SKILLS_DIR.exists():
        return skills
    for yaml_file in SKILLS_DIR.glob("*.yaml"):
        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict) and "skills" in data:
                skills.extend(data["skills"])
        except Exception as exc:
            logger.warning("Failed to load skill file %s: %s", yaml_file, exc)
    return skills


ALL_SKILLS: list[dict] = _load_skills()


def _match_skill(message: str) -> Optional[dict]:
    """Score skills by keyword matches — best match wins, not first match."""
    lower = message.lower()
    best_skill = None
    best_score = 0
    for skill in ALL_SKILLS:
        score = 0
        for kw in skill.get("keywords", []):
            if kw.lower() in lower:
                score += len(kw)
        if skill.get("name", "").replace("_", " ") in lower:
            score += 10
        if score > best_score:
            best_score = score
            best_skill = skill
    return best_skill


def _run_skill(skill: dict) -> str:
    cmd = skill.get("command", "")
    if not cmd:
        return ""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as exc:
        logger.error("Skill execution error: %s", exc)
        return f"Error running skill: {exc}"


# ---------------------------------------------------------------------------
# Ollama integration
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are MAX, the AI Assistant Manager for Empire — a founder's command center "
    "and reselling/e-commerce management platform. You serve one founder (RG). "
    "You coordinate 8 specialized AI desks: DevBot, OpsBot, SalesBot, SupportBot, "
    "FinanceBot, ContentBot, ProductBot, QABot. You help RG manage sales, shipments, "
    "listings, support tickets, custom window treatments, and AI agents across eBay, "
    "Poshmark, Mercari, and Etsy. Your engine is OpenClaw (skills-augmented local AI). "
    "Be concise, practical, and friendly. Use emojis sparingly."
)


async def _ask_ollama(message: str, history: list[dict], system_prompt: str | None = None) -> str:
    messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}]
    for h in history[-MAX_HISTORY_CONTEXT:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("message", {}).get("content", "No response from model.")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    response: str
    skill_used: Optional[str] = None
    source: str = "ollama"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "openclaw", "version": "1.0.0"}


@app.get("/skills")
async def list_skills():
    return {
        "count": len(ALL_SKILLS),
        "skills": [
            {"name": s.get("name"), "description": s.get("description")}
            for s in ALL_SKILLS
        ],
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    skill = _match_skill(req.message)
    skill_output = ""
    skill_name = None

    if skill:
        skill_name = skill.get("name")
        skill_output = _run_skill(skill)
        logger.info("Skill matched: %s → %s", skill_name, skill_output[:80])

    augmented_message = req.message
    if skill_output:
        augmented_message = (
            f"{req.message}\n\n"
            f"[EmpireBox system data for context — do not repeat verbatim]:\n{skill_output}"
        )

    try:
        ai_response = await _ask_ollama(augmented_message, req.history, req.system_prompt)
    except Exception as exc:
        logger.warning("Ollama unavailable: %s", exc)
        if skill_output:
            ai_response = skill_output
        else:
            ai_response = "⚠️ AI model (Ollama) is not reachable."

    return ChatResponse(
        response=ai_response,
        skill_used=skill_name,
        source="ollama" if skill_output == "" else "skill+ollama",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7878, reload=False, log_level="info")