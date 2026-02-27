"""MAX AI Router - Multi-provider: xAI Grok, Claude, OpenClaw, Ollama with streaming & vision."""
import os
import json
import httpx
import base64
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, AsyncGenerator
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger("max.ai_router")

class AIModel(Enum):
    GROK = "grok"
    CLAUDE = "claude"
    OPENCLAW = "openclaw"
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
from .desk_prompt import get_desk_system_prompt

class AIRouter:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.xai_key = os.getenv("XAI_API_KEY", "")
        # Priority: xAI Grok > Claude > Ollama
        if self.xai_key:
            self.primary_model = AIModel.GROK
        elif self.anthropic_key:
            self.primary_model = AIModel.CLAUDE
        else:
            self.primary_model = AIModel.OLLAMA
        self.system_prompt = get_system_prompt()
        self.upload_dir = Path.home() / "Empire" / "uploads"
        model_names = {AIModel.GROK: "xAI Grok", AIModel.CLAUDE: "Claude 4.6 Sonnet", AIModel.OLLAMA: "Ollama"}
        print(f"[MAX] Primary: {model_names[self.primary_model]}")

    def get_available_models(self):
        return [
            {"id": "grok", "name": "xAI Grok", "available": bool(self.xai_key), "primary": self.primary_model == AIModel.GROK, "type": "cloud"},
            {"id": "claude", "name": "Claude 4.6 Sonnet", "available": bool(self.anthropic_key), "primary": self.primary_model == AIModel.CLAUDE, "type": "cloud"},
            {"id": "openclaw", "name": "OpenClaw AI", "available": True, "primary": False, "type": "local"},
            {"id": "ollama-llama", "name": "Ollama LLaMA 3.1", "available": True, "primary": self.primary_model == AIModel.OLLAMA, "type": "local"},
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

    def _prepare_messages(self, messages: List[AIMessage], image_path: Optional[Path] = None):
        """Prepare system message and API messages for Claude."""
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
        return system_msg, api_messages

    def _prepare_openai_messages(self, messages: List[AIMessage], image_path: Optional[Path] = None):
        """Prepare messages in OpenAI-compatible format (used by xAI Grok)."""
        api_messages = []
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        if image_path and api_messages:
            media_type, image_data = self._encode_image(image_path)
            last_msg = api_messages[-1]
            api_messages[-1] = {
                "role": last_msg["role"],
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                    {"type": "text", "text": last_msg["content"]}
                ]
            }
        return api_messages

    # ── Non-streaming chat ──────────────────────────────────────────────

    async def chat(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None) -> AIResponse:
        use_model = model or self.primary_model
        prompt = get_desk_system_prompt(desk) if desk else self.system_prompt
        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        image_path = None
        if image_filename:
            image_path = self._find_image(image_filename)

        # Try requested model first
        if use_model == AIModel.GROK and self.xai_key:
            try:
                resp = await self._grok_chat(full_messages, image_path)
                return AIResponse(content=resp, model_used="grok")
            except Exception as e:
                logger.warning(f"Grok failed: {e}")

        if use_model == AIModel.CLAUDE and self.anthropic_key:
            try:
                resp = await self._claude_chat(full_messages, image_path)
                return AIResponse(content=resp, model_used="claude-4.6-sonnet")
            except Exception as e:
                logger.warning(f"Claude failed: {e}")

        if use_model == AIModel.OPENCLAW:
            try:
                resp = await self._openclaw_chat(messages)
                return AIResponse(content=resp, model_used="openclaw")
            except Exception as e:
                logger.warning(f"OpenClaw failed: {e}")

        # Fallback chain: Grok -> Claude -> OpenClaw -> Ollama
        if use_model != AIModel.GROK and self.xai_key:
            try:
                resp = await self._grok_chat(full_messages, image_path)
                return AIResponse(content=resp, model_used="grok", fallback_used=True)
            except Exception as e:
                logger.warning(f"Grok fallback failed: {e}")

        if use_model != AIModel.CLAUDE and self.anthropic_key:
            try:
                resp = await self._claude_chat(full_messages, image_path)
                return AIResponse(content=resp, model_used="claude-4.6-sonnet", fallback_used=True)
            except Exception as e:
                logger.warning(f"Claude fallback failed: {e}")

        if use_model != AIModel.OPENCLAW:
            try:
                resp = await self._openclaw_chat(messages)
                return AIResponse(content=resp, model_used="openclaw", fallback_used=True)
            except Exception as e:
                logger.warning(f"OpenClaw fallback failed: {e}")

        resp = await self._ollama_chat(full_messages)
        return AIResponse(content=resp, model_used="ollama-llama3.1", fallback_used=(use_model != AIModel.OLLAMA))

    # ── Streaming chat ──────────────────────────────────────────────────

    async def chat_stream(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None) -> AsyncGenerator[tuple[str, str], None]:
        use_model = model or self.primary_model
        prompt = get_desk_system_prompt(desk) if desk else self.system_prompt
        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        image_path = None
        if image_filename:
            image_path = self._find_image(image_filename)

        # Try Grok streaming
        if use_model == AIModel.GROK and self.xai_key:
            try:
                async for chunk in self._grok_chat_stream(full_messages, image_path):
                    yield chunk, "grok"
                return
            except Exception as e:
                logger.warning(f"Grok stream failed: {e}")

        # Try Claude streaming
        if use_model == AIModel.CLAUDE and self.anthropic_key:
            try:
                async for chunk in self._claude_chat_stream(full_messages, image_path):
                    yield chunk, "claude-4.6-sonnet"
                return
            except Exception as e:
                logger.warning(f"Claude stream failed: {e}")

        # Try OpenClaw (non-streaming)
        if use_model == AIModel.OPENCLAW:
            try:
                resp = await self._openclaw_chat(messages)
                yield resp, "openclaw"
                return
            except Exception as e:
                logger.warning(f"OpenClaw stream failed: {e}")

        # Fallback chain for streaming
        if use_model != AIModel.GROK and self.xai_key:
            try:
                async for chunk in self._grok_chat_stream(full_messages, image_path):
                    yield chunk, "grok"
                return
            except Exception as e:
                logger.warning(f"Grok stream fallback failed: {e}")

        if use_model != AIModel.CLAUDE and self.anthropic_key:
            try:
                async for chunk in self._claude_chat_stream(full_messages, image_path):
                    yield chunk, "claude-4.6-sonnet"
                return
            except Exception as e:
                logger.warning(f"Claude stream fallback failed: {e}")

        try:
            resp = await self._openclaw_chat(messages)
            yield resp, "openclaw"
            return
        except Exception as e:
            logger.warning(f"OpenClaw fallback failed: {e}")

        async for chunk in self._ollama_chat_stream(full_messages):
            yield chunk, "ollama-llama3.1"

    # ── xAI Grok (OpenAI-compatible API) ──────────────────────────────

    async def _grok_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                json={"model": "grok-3-fast", "messages": api_messages, "max_tokens": 8192}
            )
            if resp.status_code != 200:
                raise Exception(f"xAI HTTP {resp.status_code}: {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _grok_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                json={"model": "grok-3-fast", "messages": api_messages, "max_tokens": 8192, "stream": True}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"xAI HTTP {response.status_code}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    # ── Claude (Anthropic API) ────────────────────────────────────────

    async def _claude_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        system_msg, api_messages = self._prepare_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 8192, "system": system_msg, "messages": api_messages}
            )
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json().get("content", [{}])[0].get("text", "No response")

    async def _claude_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        system_msg, api_messages = self._prepare_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 8192, "stream": True, "system": system_msg, "messages": api_messages}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"HTTP {response.status_code}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "content_block_delta":
                        text = data.get("delta", {}).get("text", "")
                        if text:
                            yield text
                    elif data.get("type") == "message_stop":
                        return

    # ── OpenClaw ──────────────────────────────────────────────────────

    async def _openclaw_chat(self, messages: List[AIMessage]) -> str:
        last_user_msg = ""
        history = []
        for msg in messages:
            if msg.role == "user":
                last_user_msg = msg.content
            history.append({"role": msg.role, "content": msg.content})

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "http://localhost:7878/chat",
                json={"message": last_user_msg, "history": history[:-1], "system_prompt": self.system_prompt},
            )
            if resp.status_code != 200:
                raise Exception(f"OpenClaw HTTP {resp.status_code}: {resp.text}")
            return resp.json().get("response", "No response from OpenClaw")

    # ── Ollama ────────────────────────────────────────────────────────

    async def _ollama_chat(self, messages: List[AIMessage]) -> str:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
            return resp.json().get("response", "No response")

    async def _ollama_chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = data.get("response", "")
                    if text:
                        yield text
                    if data.get("done", False):
                        return

ai_router = AIRouter()
