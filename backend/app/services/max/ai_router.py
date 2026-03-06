"""MAX AI Router - Multi-provider: xAI Grok, Claude, OpenClaw, Ollama with streaming & vision."""
import os
import json
import httpx
import base64
import subprocess
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, AsyncGenerator, Tuple
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
        self.upload_dir = Path.home() / "empire-repo" / "backend" / "data" / "uploads"
        model_names = {AIModel.GROK: "xAI Grok", AIModel.CLAUDE: "Claude 4.6 Sonnet", AIModel.OLLAMA: "Ollama"}
        print(f"[MAX] Primary: {model_names[self.primary_model]}")

    def get_available_models(self):
        return [
            {"id": "grok", "name": "xAI Grok", "available": bool(self.xai_key), "primary": self.primary_model == AIModel.GROK, "type": "cloud"},
            {"id": "claude", "name": "Claude 4.6 Sonnet", "available": bool(self.anthropic_key), "primary": self.primary_model == AIModel.CLAUDE, "type": "cloud"},
            {"id": "openclaw", "name": "OpenClaw AI", "available": True, "primary": False, "type": "local"},
            {"id": "ollama-llama", "name": "Ollama LLaMA 3.1", "available": False, "primary": False, "type": "local"},
        ]

    AUDIO_EXTS = {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.wma', '.aac'}
    TEXT_EXTS = {'.txt', '.md', '.csv', '.json'}
    CODE_EXTS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.sh', '.yaml', '.yml'}

    def _find_file(self, filename: str) -> Optional[Path]:
        for cat in ['images', 'documents', 'audio', 'other', 'code']:
            path = self.upload_dir / cat / filename
            if path.exists():
                return path
        return None

    def _find_image(self, filename: str) -> Optional[Path]:
        return self._find_file(filename)

    def _is_image(self, path: Path) -> bool:
        return path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

    def _is_audio(self, path: Path) -> bool:
        return path.suffix.lower() in self.AUDIO_EXTS

    def _is_readable_text(self, path: Path) -> bool:
        return path.suffix.lower() in (self.TEXT_EXTS | self.CODE_EXTS)

    def _is_pdf(self, path: Path) -> bool:
        return path.suffix.lower() == '.pdf'

    def _transcribe_audio(self, path: Path) -> str:
        """Transcribe audio using Whisper CLI. Caches result as .transcript.txt."""
        transcript_path = path.with_suffix(path.suffix + '.transcript.txt')
        if transcript_path.exists():
            return transcript_path.read_text().strip()
        try:
            result = subprocess.run(
                ['whisper', str(path), '--model', 'base', '--output_format', 'txt',
                 '--output_dir', str(path.parent)],
                capture_output=True, text=True, timeout=300
            )
            # Whisper saves as filename_without_ext.txt
            whisper_out = path.with_suffix('.txt')
            if whisper_out.exists():
                transcript = whisper_out.read_text().strip()
                # Rename to .transcript.txt to avoid conflicts
                whisper_out.rename(transcript_path)
                return transcript
            return result.stdout.strip() or "Transcription produced no output."
        except subprocess.TimeoutExpired:
            return "[Transcription timed out — audio file may be too long]"
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return f"[Transcription failed: {e}]"

    def _read_text_file(self, path: Path, max_chars: int = 50000) -> str:
        """Read text content from a file, truncating if too large."""
        try:
            text = path.read_text(errors='replace')
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n[Truncated — file is {len(text)} chars, showing first {max_chars}]"
            return text
        except Exception as e:
            return f"[Could not read file: {e}]"

    def _read_pdf(self, path: Path, max_chars: int = 50000) -> str:
        """Extract text from a PDF file."""
        try:
            from subprocess import run
            result = run(['pdftotext', str(path), '-'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                if len(text) > max_chars:
                    text = text[:max_chars] + f"\n\n[Truncated — showing first {max_chars} chars]"
                return text
        except Exception:
            pass
        return "[Could not extract PDF text — pdftotext not available]"

    def _process_attachment(self, filename: str) -> Tuple[Optional[Path], Optional[str]]:
        """Process an attached file. Returns (image_path, attachment_text).
        For images: returns the path for vision API.
        For audio/docs/code: returns extracted text content."""
        path = self._find_file(filename)
        if not path:
            return None, None

        if self._is_image(path):
            return path, None
        elif self._is_audio(path):
            transcript = self._transcribe_audio(path)
            return None, f"[Audio transcription of {filename}]\n{transcript}"
        elif self._is_pdf(path):
            text = self._read_pdf(path)
            return None, f"[Contents of {filename}]\n{text}"
        elif self._is_readable_text(path):
            text = self._read_text_file(path)
            return None, f"[Contents of {filename}]\n{text}"
        else:
            return None, f"[Unsupported file type: {path.suffix}]"

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

    async def chat(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None, system_prompt: Optional[str] = None) -> AIResponse:
        use_model = model or self.primary_model
        prompt = system_prompt or (get_desk_system_prompt(desk) if desk else self.system_prompt)

        image_path = None
        if image_filename:
            image_path, attachment_text = self._process_attachment(image_filename)
            if attachment_text and messages:
                last = messages[-1]
                messages = list(messages)
                messages[-1] = AIMessage(role=last.role, content=attachment_text + "\n\n" + last.content)

        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        # Build ordered provider chain: requested model first, then full fallback
        providers = []
        if use_model == AIModel.GROK:
            providers = [AIModel.GROK, AIModel.CLAUDE, AIModel.OPENCLAW, AIModel.OLLAMA]
        elif use_model == AIModel.CLAUDE:
            providers = [AIModel.CLAUDE, AIModel.GROK, AIModel.OPENCLAW, AIModel.OLLAMA]
        elif use_model == AIModel.OPENCLAW:
            providers = [AIModel.OPENCLAW, AIModel.GROK, AIModel.CLAUDE, AIModel.OLLAMA]
        else:
            providers = [AIModel.OLLAMA, AIModel.GROK, AIModel.CLAUDE, AIModel.OPENCLAW]

        is_first = True
        for provider in providers:
            fallback = not is_first
            is_first = False

            if provider == AIModel.GROK and self.xai_key:
                try:
                    logger.info(f"[MAX] Chat via xAI Grok{' (fallback)' if fallback else ''}")
                    resp = await self._grok_chat(full_messages, image_path)
                    return AIResponse(content=resp, model_used="grok", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Grok failed: {e}")

            elif provider == AIModel.CLAUDE and self.anthropic_key:
                try:
                    logger.info(f"[MAX] Chat via Claude{' (fallback)' if fallback else ''}")
                    resp = await self._claude_chat(full_messages, image_path)
                    return AIResponse(content=resp, model_used="claude-4.6-sonnet", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Claude failed: {e}")

            elif provider == AIModel.OPENCLAW:
                try:
                    logger.info(f"[MAX] Chat via OpenClaw{' (fallback)' if fallback else ''}")
                    resp = await self._openclaw_chat(messages)
                    return AIResponse(content=resp, model_used="openclaw", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"OpenClaw failed: {e}")

            elif provider == AIModel.OLLAMA:
                try:
                    logger.info(f"[MAX] Chat via Ollama{' (fallback)' if fallback else ''}")
                    resp = await self._ollama_chat(full_messages)
                    return AIResponse(content=resp, model_used="ollama-llama3.1", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Ollama failed: {e}")

        return AIResponse(content="All AI providers are unavailable.", model_used="none", fallback_used=True)

    # ── Streaming chat ──────────────────────────────────────────────────

    async def chat_stream(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None, system_prompt: Optional[str] = None) -> AsyncGenerator[tuple[str, str], None]:
        use_model = model or self.primary_model
        prompt = system_prompt or (get_desk_system_prompt(desk) if desk else self.system_prompt)

        image_path = None
        if image_filename:
            image_path, attachment_text = self._process_attachment(image_filename)
            if attachment_text and messages:
                last = messages[-1]
                messages = list(messages)
                messages[-1] = AIMessage(role=last.role, content=attachment_text + "\n\n" + last.content)

        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        # Build ordered provider chain: requested model first, then full fallback
        providers = []
        if use_model == AIModel.GROK:
            providers = [AIModel.GROK, AIModel.CLAUDE, AIModel.OPENCLAW, AIModel.OLLAMA]
        elif use_model == AIModel.CLAUDE:
            providers = [AIModel.CLAUDE, AIModel.GROK, AIModel.OPENCLAW, AIModel.OLLAMA]
        elif use_model == AIModel.OPENCLAW:
            providers = [AIModel.OPENCLAW, AIModel.GROK, AIModel.CLAUDE, AIModel.OLLAMA]
        else:
            providers = [AIModel.OLLAMA, AIModel.GROK, AIModel.CLAUDE, AIModel.OPENCLAW]

        for provider in providers:
            if provider == AIModel.GROK and self.xai_key:
                try:
                    logger.info("[MAX] Streaming via xAI Grok")
                    async for chunk in self._grok_chat_stream(full_messages, image_path):
                        yield chunk, "grok"
                    return
                except Exception as e:
                    logger.warning(f"Grok stream failed: {e}")

            elif provider == AIModel.CLAUDE and self.anthropic_key:
                try:
                    logger.info("[MAX] Streaming via Claude")
                    async for chunk in self._claude_chat_stream(full_messages, image_path):
                        yield chunk, "claude-4.6-sonnet"
                    return
                except Exception as e:
                    logger.warning(f"Claude stream failed: {e}")

            elif provider == AIModel.OPENCLAW:
                try:
                    logger.info("[MAX] Streaming via OpenClaw")
                    resp = await self._openclaw_chat(messages)
                    yield resp, "openclaw"
                    return
                except Exception as e:
                    logger.warning(f"OpenClaw stream failed: {e}")

            elif provider == AIModel.OLLAMA:
                try:
                    logger.info("[MAX] Streaming via Ollama")
                    async for chunk in self._ollama_chat_stream(full_messages):
                        yield chunk, "ollama-llama3.1"
                    return
                except Exception as e:
                    logger.warning(f"Ollama stream failed: {e}")

        yield "All AI providers are unavailable.", "error"

    # ── xAI Grok (OpenAI-compatible API) ──────────────────────────────

    async def _grok_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=60.0) as client:
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
        async with httpx.AsyncClient(timeout=60.0) as client:
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
        async with httpx.AsyncClient(timeout=60.0) as client:
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
        async with httpx.AsyncClient(timeout=60.0) as client:
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

        async with httpx.AsyncClient(timeout=30.0) as client:
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
            return resp.json().get("response", "No response")

    async def _ollama_chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=60.0) as client:
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
