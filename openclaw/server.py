"""
OpenClaw AI Server — EmpireBox Command Center
FastAPI backend providing /chat, /health, and /skills endpoints.
Integrates with Ollama for AI responses and exposes EmpireBox skills.
"""

import asyncio
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

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Maximum number of previous messages sent to Ollama for conversation context
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
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load skill file %s: %s", yaml_file, exc)
    return skills


ALL_SKILLS: list[dict] = _load_skills()


def _match_skill(message: str) -> Optional[dict]:
    """Return the first skill whose keywords match any word in *message*."""
    lower = message.lower()
    for skill in ALL_SKILLS:
        for kw in skill.get("keywords", []):
            if kw.lower() in lower:
                return skill
    return None


def _run_skill(skill: dict) -> str:
    """Execute a skill's shell command and return its stdout."""
    cmd = skill.get("command", "")
    if not cmd:
        return ""
    try:
        # shell=True is required for skill commands that use shell builtins and
        # variable expansion (e.g. $(date)). Skill definitions are developer-
        # controlled YAML files and must not contain untrusted user input.
        result = subprocess.run(
            cmd,
            shell=True,  # noqa: S602
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as exc:  # noqa: BLE001
        logger.error("Skill execution error: %s", exc)
        return f"Error running skill: {exc}"


# ---------------------------------------------------------------------------
# Ollama integration
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are OpenClaw, the AI assistant for EmpireBox — a reselling and e-commerce "
    "management platform. You help the owner (RG) manage sales, shipments, listings, "
    "support tickets, and AI agents across eBay, Poshmark, Mercari, and Etsy. "
    "Be concise, practical, and friendly. Use emojis sparingly."
)


async def _ask_ollama(message: str, history: list[dict]) -> str:
    """Send a message to Ollama and return the response text."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-MAX_HISTORY_CONTEXT:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{OLLAMA_URL}/api/chat", json=payload
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("message", {}).get("content", "No response from model.")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    response: str
    skill_used: Optional[str] = None
    source: str = "ollama"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "openclaw", "version": "1.0.0"}


@app.get("/skills")
async def list_skills():
    """List all loaded skills."""
    return {
        "count": len(ALL_SKILLS),
        "skills": [
            {"name": s.get("name"), "description": s.get("description")}
            for s in ALL_SKILLS
        ],
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Process a chat message.

    1. Check if the message matches a skill keyword → run the skill command.
    2. Send the message (plus skill output as context) to Ollama.
    3. Return the AI response.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    skill = _match_skill(req.message)
    skill_output = ""
    skill_name = None

    if skill:
        skill_name = skill.get("name")
        skill_output = _run_skill(skill)
        logger.info("Skill matched: %s → %s", skill_name, skill_output[:80])

    # Build the final message for Ollama
    augmented_message = req.message
    if skill_output:
        augmented_message = (
            f"{req.message}\n\n"
            f"[EmpireBox system data for context — do not repeat verbatim]:\n{skill_output}"
        )

    try:
        ai_response = await _ask_ollama(augmented_message, req.history)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama unavailable: %s", exc)
        # Fall back to skill output or a canned message
        if skill_output:
            ai_response = skill_output
        else:
            ai_response = (
                "⚠️ AI model (Ollama) is not reachable. "
                "Start Ollama with: `docker compose up ollama`\n"
                "In the meantime, try a quick command like [sales today] or [check health]."
            )

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

    uvicorn.run(
        "server:app",
        host="0.0.0.0",  # noqa: S104
        port=7878,
        reload=False,
        log_level="info",
    )
