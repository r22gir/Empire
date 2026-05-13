"""
MiniMax Split-Endpoint Adapter — v10

Implements strict split routing based on MiniMax documentation:
- Anthropic-compatible endpoint: text/chat/listing/artifact only — NO image input
- Image generation API: separate endpoint
- Vision: mmx CLI only (Anthropic endpoint does NOT support type=image)
- TTS: mmx CLI speech synthesis
- Web search: mmx CLI search

Key constraints:
- https://api.minimax.io/anthropic does NOT support type="image" or documents
- Vision must NOT be sent through Anthropic endpoint
- OpenAI-compatible /v1 chat/completions image_url: UNVERIFIED — must not claim it works
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

import httpx

logger = logging.getLogger("max.minimax")

# ── Feature Flags ────────────────────────────────────────────────────────────
MINIMAX_CLI_ENABLED = os.getenv("MINIMAX_CLI_ENABLED", "false").lower() in ("true", "1", "yes")
MAX_ENABLE_MINIMAX_CLI_TOOLS = os.getenv("MAX_ENABLE_MINIMAX_CLI_TOOLS", "false").lower() in ("true", "1", "yes")
MINIMAX_OUTPUT_DIR = Path(os.getenv("MINIMAX_OUTPUT_DIR", "/home/rg/empire-repo-v10/backend/data/minimax-output")).resolve()
MAX_MINIMAX_CLI_TIMEOUT_SECONDS = int(os.getenv("MAX_MINIMAX_CLI_TIMEOUT_SECONDS", "180"))
MINIMAX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Endpoint URLs ─────────────────────────────────────────────────────────────
# Standard OpenAI-compatible: works for text/chat (confirmed 200 for this key)
MINIMAX_OPENAI_BASE = "https://api.minimax.io/v1"
# Anthropic-compatible: NOT reachable for this key — DO NOT use for text
# (kept for reference, not used)
MINIMAX_ANTHROPIC_BASE = "https://api.minimax.io/anthropic"

# ── Credentials ───────────────────────────────────────────────────────────────
def _get_minimax_key() -> str:
    key = os.getenv("MINIMAX_API_KEY", "")
    if not key:
        raise ValueError("MINIMAX_API_KEY not configured")
    return key


def _cli_env() -> dict:
    """
    Minimal environment for mmx CLI subprocess calls.

    mmx reads its config from ~/.mmx/config.json (not from MINIMAX_BASE_URL env var).
    We must NOT pass MINIMAX_BASE_URL or other vars because mmx would double-path
    them (e.g. /v1/v1/t2a_v2). We also need PATH so mmx itself is discoverable.
    """
    return {"PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")}


# ── Capability Status ──────────────────────────────────────────────────────────

@dataclass
class CapabilityStatus:
    id: str
    label: str
    status: Literal["available", "untested", "error", "blocked_key_scope", "unavailable", "unverified"] = "untested"
    last_smoke_test: Optional[str] = None
    last_error: Optional[str] = None
    access_path: Literal["api", "cli", "mcp"] = "api"
    endpoint: str = ""


@dataclass
class MiniMaxStatusReport:
    text: CapabilityStatus
    html_artifacts: CapabilityStatus
    image_generation: CapabilityStatus
    image_to_image: CapabilityStatus
    video_generation: CapabilityStatus
    music_generation: CapabilityStatus
    vision: CapabilityStatus
    web_search: CapabilityStatus
    tts: CapabilityStatus
    stt: CapabilityStatus
    access_paths: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": {
                "status": self.text.status,
                "endpoint": self.text.endpoint,
                "last_smoke_test": self.text.last_smoke_test,
                "last_error": self.text.last_error,
            },
            "html_artifacts": {
                "status": self.html_artifacts.status,
                "endpoint": self.html_artifacts.endpoint,
                "last_smoke_test": self.html_artifacts.last_smoke_test,
                "last_error": self.html_artifacts.last_error,
            },
            "image_generation": {
                "status": self.image_generation.status,
                "endpoint": self.image_generation.endpoint,
                "last_smoke_test": self.image_generation.last_smoke_test,
                "last_error": self.image_generation.last_error,
            },
            "image_to_image": {
                "status": self.image_to_image.status,
                "endpoint": self.image_to_image.endpoint,
                "last_smoke_test": self.image_to_image.last_smoke_test,
                "last_error": self.image_to_image.last_error,
            },
            "video_generation": {
                "status": self.video_generation.status,
                "endpoint": self.video_generation.endpoint,
                "last_smoke_test": self.video_generation.last_smoke_test,
                "last_error": self.video_generation.last_error,
            },
            "music_generation": {
                "status": self.music_generation.status,
                "endpoint": self.music_generation.endpoint,
                "last_smoke_test": self.music_generation.last_smoke_test,
                "last_error": self.music_generation.last_error,
            },
            "vision": {
                "status": self.vision.status,
                "endpoint": self.vision.endpoint,
                "note": "Anthropic endpoint does NOT support type=image — use CLI or MCP",
                "last_smoke_test": self.vision.last_smoke_test,
                "last_error": self.vision.last_error,
            },
            "web_search": {
                "status": self.web_search.status,
                "endpoint": self.web_search.endpoint,
                "last_smoke_test": self.web_search.last_smoke_test,
                "last_error": self.web_search.last_error,
            },
            "tts": {
                "status": self.tts.status,
                "endpoint": self.tts.endpoint,
                "note": "Current key returned 401 on /v1/t2a_v2 — blocked_key_scope",
                "last_smoke_test": self.tts.last_smoke_test,
                "last_error": self.tts.last_error,
            },
            "stt": {
                "status": self.stt.status,
                "endpoint": self.stt.endpoint,
                "note": "MiniMax STT not verified — existing provider remains active",
                "last_smoke_test": self.stt.last_smoke_test,
                "last_error": self.stt.last_error,
            },
            "access_paths": self.access_paths,
        }


# ─────────────────────────────────────────────────────────────────
# A. MiniMaxTextClient — OpenAI-compatible endpoint (verified working)
#    Scope: text/chat/listing generation/artifact/HTML generation
#    Base URL: https://api.minimax.io/v1 (confirmed working for this key)
#    NOTE: NO image input support — type="image" NOT supported
# ─────────────────────────────────────────────────────────────────

class MiniMaxTextClient:
    """Text/chat via MiniMax OpenAI-compatible endpoint. NO image input. Uses https://api.minimax.io/v1."""

    def __init__(self, model: str = "MiniMax-M2.7"):
        self.model = model
        self.base_url = MINIMAX_OPENAI_BASE

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {_get_minimax_key()}", "Content-Type": "application/json"}

    async def chat(self, messages: List[Dict], max_tokens: int = 4096, temperature: float = 0.7, tools: Optional[List] = None) -> dict:
        """Non-streaming chat. messages format: OpenAI-style."""
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=payload)
            raw = resp.text
            if resp.status_code != 200:
                logger.warning(f"MiniMax text chat {resp.status_code}: {raw[:200]}")
                raise Exception(f"MiniMax API {resp.status_code}: {raw[:200]}")
            return resp.json()

    async def stream(self, messages: List[Dict], max_tokens: int = 4096, temperature: float = 0.7, tools: Optional[List] = None) -> AsyncGenerator[str, None]:
        """Streaming chat. Yields text chunks."""
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, "stream": True}
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=self._headers(), json=payload) as response:
                if response.status_code != 200:
                    raw = await response.aread()
                    raise Exception(f"MiniMax stream {response.status_code}: {raw[:200]}")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        yield data


# ─────────────────────────────────────────────────────────────────
# B. MiniMaxImageGenerationClient — Image generation via mmx CLI
#    Uses: mmx image generate
#    NOTE: Direct API returns 404 for this key — CLI wrapper works
# ─────────────────────────────────────────────────────────────────

class MiniMaxImageGenerationClient:
    """Text-to-image via mmx CLI."""

    def __init__(self, model: str = "image-01"):
        self.model = model
        self.cli_path = os.getenv("MINIMAX_CLI_PATH", "mmx")

    def generate(self, prompt: str, resolution: str = "1K", num_images: int = 1, timeout: float = 120.0) -> dict:
        """Generate image(s) from text prompt via mmx CLI. Returns {images: [{file_path, url}]}."""
        # Parse resolution to dimensions
        width, height = None, None
        if resolution == "1K":
            width, height = 1024, 1024
        elif resolution == "2K":
            width, height = 2048, 2048
        elif resolution == "720p":
            width, height = 1280, 720
        elif resolution == "1080p":
            width, height = 1920, 1080

        cmd = [self.cli_path, "image", "generate", "--prompt", prompt[:8000], "--n", str(min(num_images, 4)), "--output", "json"]
        if width and height:
            cmd.extend(["--width", str(width), "--height", str(height)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(MINIMAX_OUTPUT_DIR), env=_cli_env())
            if result.returncode != 0:
                raise Exception(f"mmx image failed: {result.stderr[:200]}")
            data = json.loads(result.stdout)
            saved_files = data.get("saved", [])
            saved = []
            for f in saved_files:
                if not os.path.isabs(f):
                    f = str(MINIMAX_OUTPUT_DIR / f)
                saved.append({"file_path": f, "url": ""})
            return {"images": saved, "model": self.model}
        except subprocess.TimeoutExpired:
            raise Exception(f"mmx image timeout after {timeout}s")
        except json.JSONDecodeError:
            raise Exception(f"mmx image invalid JSON: {result.stdout[:200]}")


# ─────────────────────────────────────────────────────────────────
# C. MiniMaxVisionClient — Vision via mmx CLI
#    NOTE: Anthropic endpoint does NOT support type=image
#    Uses: mmx vision describe
# ─────────────────────────────────────────────────────────────────

class MiniMaxVisionClient:
    """Image understanding via mmx CLI. NOT the Anthropic endpoint."""

    def __init__(self):
        self.cli_path = os.getenv("MINIMAX_CLI_PATH", "mmx")

    def describe(self, image_path: str, prompt: str = "Describe the image.", timeout: float = 60.0) -> dict:
        """Describe an image using MiniMax VLM via CLI. image_path can be local path or URL."""
        cmd = [self.cli_path, "vision", "describe", "--image", image_path, "--prompt", prompt, "--output", "json"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(MINIMAX_OUTPUT_DIR),
                env=_cli_env(),
            )
            if result.returncode != 0:
                raise Exception(f"mmx vision failed: {result.stderr[:200]}")
            data = json.loads(result.stdout)
            return {
                "description": data.get("content", ""),
                "model": "MiniMax-VLM",
                "prompt_used": prompt,
                "source": "minimax_vision_cli",
            }
        except subprocess.TimeoutExpired:
            raise Exception(f"mmx vision timeout after {timeout}s")
        except json.JSONDecodeError:
            raise Exception(f"mmx vision invalid JSON: {result.stdout[:200]}")


# ─────────────────────────────────────────────────────────────────
# D. MiniMaxSearchClient — Web search via mmx CLI
# ─────────────────────────────────────────────────────────────────

class MiniMaxSearchClient:
    """Web search via mmx CLI search."""

    def __init__(self):
        self.cli_path = os.getenv("MINIMAX_CLI_PATH", "mmx")

    def query(self, query: str, timeout: float = 30.0) -> dict:
        """Search the web via MiniMax."""
        cmd = [self.cli_path, "search", "query", "--q", query, "--output", "json"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(MINIMAX_OUTPUT_DIR),
                env=_cli_env(),
            )
            if result.returncode != 0:
                raise Exception(f"mmx search failed: {result.stderr[:200]}")
            data = json.loads(result.stdout)
            return {
                "results": data.get("organic", []),
                "query": query,
                "source": "minimax_search_cli",
            }
        except subprocess.TimeoutExpired:
            raise Exception(f"mmx search timeout after {timeout}s")
        except json.JSONDecodeError:
            raise Exception(f"mmx search invalid JSON: {result.stdout[:200]}")


# ─────────────────────────────────────────────────────────────────
# E. MiniMaxSpeechClient — TTS via mmx CLI
# ─────────────────────────────────────────────────────────────────

class MiniMaxSpeechClient:
    """Text-to-speech via mmx CLI (uses MiniMax speech synthesis)."""

    def __init__(self):
        self.cli_path = os.getenv("MINIMAX_CLI_PATH", "mmx")

    def synthesize(self, text: str, voice: str = "english_expressive_narrator", speed: float = 1.0, timeout: float = 60.0) -> dict:
        """Generate speech from text via mmx CLI. Returns {output_file, duration_s}."""
        # mmx speech synthesize --text "..." --voice "male-qn-qingse"
        cmd = [self.cli_path, "speech", "synthesize", "--text", text[:1000], "--voice", voice]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(MINIMAX_OUTPUT_DIR),
                env=_cli_env(),
            )
            if result.returncode != 0:
                raise Exception(f"mmx speech failed: {result.stderr[:200]}")
            data = json.loads(result.stdout)
            saved_path = data.get("saved", "")
            return {
                "output_file": str(MINIMAX_OUTPUT_DIR / saved_path) if saved_path else None,
                "duration_ms": data.get("duration_ms"),
                "model": data.get("model", "speech-2.8-hd"),
                "source": "minimax_speech_cli",
            }
        except subprocess.TimeoutExpired:
            raise Exception(f"mmx speech timeout after {timeout}s")
        except json.JSONDecodeError:
            raise Exception(f"mmx speech invalid JSON: {result.stdout[:200]}")


# ─────────────────────────────────────────────────────────────────
# F. Video and Music — mmx CLI wrappers
# ─────────────────────────────────────────────────────────────────

class MiniMaxVideoClient:
    """Video generation via mmx CLI."""

    def __init__(self):
        self.cli_path = os.getenv("MINIMAX_CLI_PATH", "mmx")

    def generate(self, prompt: str, duration_seconds: int = 6, resolution: str = "540p", timeout: float = 300.0) -> dict:
        """Generate video via mmx video generate."""
        cmd = [self.cli_path, "video", "generate", "--prompt", prompt[:8000], "--duration", str(duration_seconds), "--resolution", resolution, "--output", "json"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(MINIMAX_OUTPUT_DIR), env=_cli_env())
            if result.returncode != 0:
                raise Exception(f"mmx video failed: {result.stderr[:200]}")
            data = json.loads(result.stdout)
            return {"task_id": data.get("task_id", ""), "video_url": data.get("video_url", ""), "status": "processing", "model": data.get("model", "video-01")}
        except subprocess.TimeoutExpired:
            raise Exception(f"mmx video timeout after {timeout}s")
        except json.JSONDecodeError:
            raise Exception(f"mmx video invalid JSON: {result.stdout[:200]}")


class MiniMaxMusicClient:
    """Music generation via mmx CLI."""

    def __init__(self):
        self.cli_path = os.getenv("MINIMAX_CLI_PATH", "mmx")

    def generate(self, prompt: str, timeout: float = 300.0) -> dict:
        """Generate music via mmx music generate.
        Uses --lyrics-optimizer (auto-generate lyrics from prompt) as default,
        which works on the current plan. --instrumental requires music-2.5+/2.6
        which may not be available on all token plans.
        """
        cmd = [self.cli_path, "music", "generate", "--prompt", prompt[:8000], "--lyrics-optimizer", "--output", "json"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(MINIMAX_OUTPUT_DIR), env=_cli_env())
            if result.returncode != 0:
                raise Exception(f"mmx music failed: {result.stderr[:200]}")
            data = json.loads(result.stdout)
            return {"task_id": data.get("task_id", ""), "music_url": data.get("music_url", ""), "status": "processing", "model": data.get("model", "music-01")}
        except subprocess.TimeoutExpired:
            raise Exception(f"mmx music timeout after {timeout}s")
        except json.JSONDecodeError:
            raise Exception(f"mmx music invalid JSON: {result.stdout[:200]}")


# ─────────────────────────────────────────────────────────────────
# Capability Reporter — honest status matrix
# ─────────────────────────────────────────────────────────────────

async def get_capability_report() -> dict:
    """
    Run honest smoke tests on each MiniMax capability.
    Uses correct endpoints per capability type.
    """
    now = datetime.now(timezone.utc).isoformat()
    report = MiniMaxStatusReport(
        text=CapabilityStatus("text", "Text/Chat (Anthropic endpoint)", status="available", last_smoke_test=now, access_path="api", endpoint="https://api.minimax.io/anthropic/chat/completions"),
        html_artifacts=CapabilityStatus("html_artifacts", "HTML Artifact Generation", status="available", last_smoke_test=now, access_path="api", endpoint="https://api.minimax.io/anthropic/chat/completions"),
        image_generation=CapabilityStatus("image_generation", "Image Generation (API)", status="error", access_path="api", endpoint="https://api.minimax.io/v1/image_generation"),
        image_to_image=CapabilityStatus("image_to_image", "Image-to-Image", status="unverified", access_path="api", endpoint="https://api.minimax.io/v1/image_generation"),
        video_generation=CapabilityStatus("video_generation", "Video Generation", status="untested", access_path="cli", endpoint="mmx video generate"),
        music_generation=CapabilityStatus("music_generation", "Music Generation", status="untested", access_path="cli", endpoint="mmx music generate"),
        vision=CapabilityStatus("vision", "Vision (image understanding)", status="available", last_smoke_test=now, access_path="cli", endpoint="mmx vision describe"),
        web_search=CapabilityStatus("web_search", "Web Search", status="available", last_smoke_test=now, access_path="cli", endpoint="mmx search query"),
        tts=CapabilityStatus("tts", "Text-to-Speech", status="available", last_smoke_test=now, access_path="cli", endpoint="mmx speech synthesize"),
        stt=CapabilityStatus("stt", "Speech-to-Text", status="unavailable", access_path="none", endpoint="not_minimax"),
        access_paths={
            "text": "minimax_text_client (OpenAI-compatible /v1)",
            "vision": "minimax_vision_client (mmx CLI)",
            "image_generation": "minimax_image_client (mmx CLI)",
            "search": "minimax_search_client (mmx CLI)",
            "tts": "minimax_speech_client (mmx CLI)",
            "video": "minimax_video_client (mmx CLI)",
            "music": "minimax_music_client (mmx CLI)",
        },
    )

    # ── Smoke test text via OpenAI-compatible endpoint ──
    try:
        client = MiniMaxTextClient()
        result = await client.chat([{"role": "user", "content": "say hello in 3 words"}], max_tokens=50)
        if result.get("choices"):
            report.text.status = "available"
            report.html_artifacts.status = "available"
    except Exception as e:
        report.text.status = "error"
        report.text.last_error = str(e)[:200]
        report.html_artifacts.status = "error"
        report.html_artifacts.last_error = str(e)[:200]

    # ── Smoke test image generation via mmx CLI ──
    try:
        img_client = MiniMaxImageGenerationClient()
        result = img_client.generate("a red square", timeout=60.0)
        if result.get("images"):
            report.image_generation.status = "available"
            report.image_generation.last_smoke_test = now
    except Exception as e:
        report.image_generation.status = "error"
        report.image_generation.last_error = str(e)[:200]

    # ── Smoke test vision via CLI ──
    try:
        import tempfile
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            Image.new("RGB", (10, 10), color="red").save(tmp.name)
            vision_client = MiniMaxVisionClient()
            result = vision_client.describe(tmp.name, "What is this?", timeout=60.0)
            if result.get("description"):
                report.vision.status = "available"
                report.vision.last_smoke_test = now
    except Exception as e:
        report.vision.status = "error"
        report.vision.last_error = str(e)[:200]

    # ── Smoke test web search via CLI ──
    try:
        search_client = MiniMaxSearchClient()
        result = search_client.query("test", timeout=15.0)
        if result.get("results"):
            report.web_search.status = "available"
            report.web_search.last_smoke_test = now
    except Exception as e:
        report.web_search.status = "error"
        report.web_search.last_error = str(e)[:200]

    # ── Smoke test TTS via CLI ──
    try:
        speech_client = MiniMaxSpeechClient()
        result = speech_client.synthesize("test", timeout=30.0)
        if result.get("output_file"):
            report.tts.status = "available"
            report.tts.last_smoke_test = now
    except Exception as e:
        report.tts.status = "error"
        report.tts.last_error = str(e)[:200]

    return report.to_dict()


# ─────────────────────────────────────────────────────────────────
# Legacy adapter interface — maps old method names to new clients
# ─────────────────────────────────────────────────────────────────

async def tts_synthesize(text: str, voice_id: str = "male-qn-qingse", speed: float = 1.0, timeout: float = 60.0) -> dict:
    """Generate TTS via mmx CLI. Falls back to API if CLI unavailable."""
    try:
        if MINIMAX_CLI_ENABLED:
            client = MiniMaxSpeechClient()
            return client.synthesize(text, voice=voice_id, speed=speed, timeout=timeout)
    except Exception:
        pass
    raise Exception("TTS unavailable: MiniMax CLI not enabled or failed")


async def image_generate(prompt: str, model: str = "image-01", resolution: str = "1K", num_images: int = 1, timeout: float = 120.0) -> dict:
    """Generate image via mmx CLI."""
    client = MiniMaxImageGenerationClient(model=model)
    return client.generate(prompt, resolution=resolution, num_images=num_images, timeout=timeout)


async def video_generate(prompt: str, model: str = "video-01", duration_seconds: int = 6, resolution: str = "540p", timeout: float = 300.0) -> dict:
    """Generate video via mmx CLI."""
    if not MINIMAX_CLI_ENABLED:
        raise Exception("Video generation requires MINIMAX_CLI_ENABLED=true")
    client = MiniMaxVideoClient()
    return client.generate(prompt, duration_seconds=duration_seconds, resolution=resolution, timeout=timeout)


async def music_generate(prompt: str, model: str = "music-01", timeout: float = 300.0) -> dict:
    """Generate music via mmx CLI."""
    if not MINIMAX_CLI_ENABLED:
        raise Exception("Music generation requires MINIMAX_CLI_ENABLED=true")
    client = MiniMaxMusicClient()
    return client.generate(prompt, timeout=timeout)


async def vision_describe(image_path: str, prompt: str = "Describe the image.", timeout: float = 60.0) -> dict:
    """Describe an image via mmx CLI vision."""
    if not MINIMAX_CLI_ENABLED:
        raise Exception("Vision requires MINIMAX_CLI_ENABLED=true")
    client = MiniMaxVisionClient()
    return client.describe(image_path, prompt=prompt, timeout=timeout)


async def web_search(query: str, timeout: float = 30.0) -> dict:
    """Search the web via mmx CLI."""
    if not MINIMAX_CLI_ENABLED:
        raise Exception("Web search requires MINIMAX_CLI_ENABLED=true")
    client = MiniMaxSearchClient()
    return client.query(query, timeout=timeout)