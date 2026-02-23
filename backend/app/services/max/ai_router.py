"""MAX AI Router - Claude Opus 4.5 primary with Vision, Ollama fallback."""
import os
import httpx
import base64
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger("max.ai_router")

class AIModel(Enum):
    CLAUDE = "claude"
    OLLAMA = "ollama-llama"

@dataclass
class AIMessage:
    role: str
    content: str
    image_path: Optional[str] = None

@dataclass
class AIResponse:
    content: str
    model_used: str
    fallback_used: bool = False

from .system_prompt import get_system_prompt

class AIRouter:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.primary_model = AIModel.CLAUDE if self.anthropic_key else AIModel.OLLAMA
        self.system_prompt = get_system_prompt()
        self.upload_dir = Path.home() / "Empire" / "uploads"
        print(f"[MAX] Primary: {'Claude Opus 4.5' if self.anthropic_key else 'Ollama'}")
    
    def get_available_models(self):
        return [
            {"id": "claude", "name": "Claude Opus 4.5", "available": bool(self.anthropic_key), "primary": bool(self.anthropic_key), "type": "cloud"},
            {"id": "ollama-llama", "name": "Ollama LLaMA 3.1", "available": True, "primary": not bool(self.anthropic_key), "type": "local"},
        ]
    
    def _find_image(self, filename: str) -> Optional[Path]:
        for cat in ['images', 'documents', 'other', 'code']:
            path = self.upload_dir / cat / filename
            if path.exists():
                return path
        return None
    
    def _encode_image(self, path: Path) -> tuple:
        ext = path.suffix.lower()
        media_types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp'}
        media_type = media_types.get(ext, 'image/png')
        with open(path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode('utf-8')
        return media_type, data
    
    async def chat(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None) -> AIResponse:
        use_model = model or self.primary_model
        full_messages = [AIMessage(role="system", content=self.system_prompt)] + list(messages)
        
        image_path = None
        if image_filename:
            image_path = self._find_image(image_filename)
        
        if use_model == AIModel.CLAUDE and self.anthropic_key:
            try:
                resp = await self._claude_chat(full_messages, image_path)
                return AIResponse(content=resp, model_used="claude-opus-4.5")
            except Exception as e:
                logger.warning(f"Claude failed: {e}")
                print(f"[MAX] Claude failed: {e}, using Ollama")
        
        resp = await self._ollama_chat(full_messages)
        return AIResponse(content=resp, model_used="ollama-llama3.1", fallback_used=(use_model != AIModel.OLLAMA))
    
    async def _claude_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        system_msg = ""
        api_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})
        
        if image_path and api_messages:
            media_type, image_data = self._encode_image(image_path)
            last_msg = api_messages[-1]
            api_messages[-1] = {
                "role": last_msg["role"],
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                    {"type": "text", "text": last_msg["content"]}
                ]
            }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 8192,
                    "system": system_msg,
                    "messages": api_messages
                }
            )
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json().get("content", [{}])[0].get("text", "No response")
    
    async def _ollama_chat(self, messages: List[AIMessage]) -> str:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
            return resp.json().get("response", "No response")

ai_router = AIRouter()
