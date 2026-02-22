import os
import httpx
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class AIModel(Enum):
    OLLAMA = "ollama-llama"
    CLAUDE = "claude"
    XAI = "xai"
    GPT4 = "gpt4"

@dataclass
class AIMessage:
    role: str
    content: str

@dataclass
class AIResponse:
    content: str
    model_used: str
    fallback_used: bool = False

class AIRouter:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.xai_key = os.getenv("XAI_API_KEY", "")
        self.openai_key = os.getenv("OPENA_API_KEY", "")
        self.current_model = AIModel.OLLAMA
    
    def get_available_models(self):
        return [m.value for m in AIModel]
    
    async def chat(self, messages, model=None):
        use_model = model or self.current_model
        last_msg = messages[-1].content if messages else ""
        if use_model == AIModel.CLAUDE:
            resp = await self._claude_chat(last_msg)
        elif use_model == AIModel.XAI:
            resp = await self._xai_chat(last_msg)
        elif use_model == AIModel.GPT4:
            resp = await self._openai_chat(last_msg)
        else:
            resp = await self._ollama_chat(last_msg)
        return AIResponse(content=resp, model_used=use_model.value)
    
    async def _ollama_chat(self, message):
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("http://localhost:11434/api/chat",
                json={"model": "llama3.1:8b", "messages": [{"role": "user", "content": message}], "stream": False})
            return resp.json().get("message", {}).get("content", "No response")
    
    async def _claude_chat(self, message):
        if not self.anthropic_key:
            return "Claude not configured"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-opus-4-5-20251101", "max_tokens": 4096, "messages": [{"role": "user", "content": message}]})
            data = resp.json()
            return data.get("content", [{}])[0].get("text", str(data))
    
    async def _xai_chat(self, message):
        if not self.xai_key:
            return "xAI not configured"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                json={"model": "grok-beta", "messages": [{"role": "user", "content": message}]})
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "No response")
    
    async def _openai_chat(self, message):
        if not self.openai_key:
            return "OpenAI not configured"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                json={"model": "gpt-4", "messages": [{"role": "user", "content": message}]})
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "No response")

ai_router = AIRouter()
