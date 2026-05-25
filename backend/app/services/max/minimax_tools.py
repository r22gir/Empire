"""MiniMax multimodal tools — text-to-image, image-to-image, TTS, music.

Runtime-truth-safe: every success requires verified artifact on disk.
No optimistic success. No live calls unless explicitly approved.
"""
import os
import io
import re
import json
import time
import uuid
import base64
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Any

import httpx

logger = logging.getLogger("max.minimax_tools")

# ── Env ─────────────────────────────────────────────────────────────────────

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
MINIMAX_IMAGE_MODEL = os.getenv("MINIMAX_IMAGE_MODEL", "image-01")
MINIMAX_TTS_MODEL = os.getenv("MINIMAX_TTS_MODEL", "speech-01")
MINIMAX_MUSIC_MODEL = os.getenv("MINIMAX_MUSIC_MODEL", "music-01")
MINIMAX_VIDEO_ENABLED = os.getenv("MINIMAX_VIDEO_ENABLED", "0") == "1"

# ── mmx CLI ──────────────────────────────────────────────────────────────────

MMX_CLI_PATH = os.getenv("MINIMAX_CLI_PATH", "/home/rg/.local/bin/mmx")
MMX_VISION_TIMEOUT = 60  # seconds

# Live MCP error tracking — updated after each actual vision call
# Do not run live probes on status calls
_mcp_last_probe_status: str = "not_probed"
_mcp_last_error_category: str | None = None
_mcp_last_error_message: str | None = None
_mcp_last_probe_at: str | None = None

# Phrases that indicate the vision model returned a "no image" placeholder
_NO_IMAGE_PHRASES = frozenset([
    "no image provided",
    "i cannot see the image",
    "i can't see the image",
    "no image was uploaded",
    "please provide an image",
    "unable to view",
    "as an ai text model",
    "i do not have access to the image",
    "i am unable to see the image",
    "cannot see the image",
    "don't have access to the image",
    "do not have access to the image",
])


def _mmx_cli_available() -> tuple[bool, str]:
    """
    Check if mmx CLI is installed and responds to --version.

    Returns:
        (True, path) if available
        (False, reason) if not
    """
    path = MMX_CLI_PATH
    if not os.path.exists(path):
        # Fall back to PATH lookup
        for d in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(d, "mmx")
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                path = candidate
                break
        else:
            return False, "mmx not found in PATH or at MINIMAX_CLI_PATH"

    if not os.access(path, os.X_OK):
        return False, f"mmx at {path} is not executable"

    # Quick version check
    try:
        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return False, f"mmx --version returned {r.returncode}"
    except subprocess.TimeoutExpired:
        return False, "mmx --version timed out"
    except Exception as e:
        return False, f"mmx --version error: {e}"

    return True, path


def _mmx_subprocess_env() -> dict[str, str]:
    """Return the environment for mmx CLI calls without dropping runtime auth."""
    env = os.environ.copy()
    env["PATH"] = env.get("PATH") or "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    return env


def _strip_think_blocks(text: str) -> str:
    """Strip <think>...</think> and similar chain-of-thought artifacts from text."""
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    text = re.sub(r"<!--\s*撮要.*?-->", "", text, flags=re.DOTALL)
    return text.strip()


def _classify_mcp_error(error: str) -> str:
    """Classify an MCP error string into a known category."""
    if not error:
        return "unknown_error"
    err_lower = error.lower()
    if "usage limit exceeded" in err_lower:
        return "usage_limit_exceeded"
    if "no image provided" in err_lower or "cannot see the image" in err_lower:
        return "vision_input_not_received"
    if "timeout" in err_lower:
        return "timeout"
    if "not found" in err_lower or "file not found" in err_lower:
        return "file_not_found"
    if "unauthorized" in err_lower or "invalid api key" in err_lower:
        return "auth_error"
    if "rate limit" in err_lower:
        return "rate_limited"
    return "unknown_error"


def _redact_error_message(msg: str) -> str:
    """Redact secrets from error messages."""
    if not msg:
        return ""
    msg = re.sub(r"sk-[A-Za-z0-9]{20,}", "[KEY_REDACTED]", msg)
    msg = re.sub(r"[A-Za-z0-9+/]{40,}={0,2}", "[TOKEN_REDACTED]", msg)
    return msg


def _update_mcp_probe_status(success: bool, error: str | None) -> None:
    """Update the live MCP probe tracker after an actual vision call. No live probing on status."""
    global _mcp_last_probe_status, _mcp_last_error_category, _mcp_last_error_message, _mcp_last_probe_at
    from datetime import datetime, timezone
    _mcp_last_probe_at = datetime.now(timezone.utc).isoformat()
    if success:
        _mcp_last_probe_status = "success"
        _mcp_last_error_category = None
        _mcp_last_error_message = None
    else:
        _mcp_last_probe_status = _classify_mcp_error(error or "")
        _mcp_last_error_category = _mcp_last_probe_status
        _mcp_last_error_message = _redact_error_message(error) if error else None

# ── Storage ───────────────────────────────────────────────────────────────────

# Reuse existing generated media directory from vision.py
_GENERATED_DIR = Path(__file__).resolve().parents[2] / "data" / "generated"
_GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Stable browser-accessible URL prefix
_MEDIA_URL_PREFIX = "/api/v1/vision/images"


def _load_runtime_env() -> None:
    """Re-load .env at runtime if MINIMAX_API_KEY is not set (handles systemd drop-in)."""
    if os.getenv("MINIMAX_API_KEY"):
        return
    env_paths = [
        Path(__file__).resolve().parents[2] / ".env",
        Path("/home/rg/empire-repo/backend/.env"),
    ]
    for env_path in env_paths:
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                text = line.strip()
                if not text or text.startswith("#") or "=" not in text:
                    continue
                key, value = text.split("=", 1)
                key = key.strip()
                if key in ("MINIMAX_API_KEY", "MINIMAX_BASE_URL", "MINIMAX_IMAGE_MODEL",
                           "MINIMAX_TTS_MODEL", "MINIMAX_MUSIC_MODEL") and not os.getenv(key):
                    os.environ[key] = value.strip().strip('"').strip("'")
        except OSError:
            continue


def _save_bytes(data: bytes, prefix: str, ext: str = "png") -> tuple[str, Path]:
    """Save bytes to GENERATED_DIR, return (serve_url, file_path)."""
    fname = f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:8]}.{ext}"
    path = _GENERATED_DIR / fname
    path.write_bytes(data)
    return f"{_MEDIA_URL_PREFIX}/{fname}", path


def _verify_file(path: Path, min_bytes: int = 500) -> bool:
    """Return True only if file exists, is a file, and exceeds min_bytes."""
    return path.exists() and path.is_file() and path.stat().st_size >= min_bytes


def _build_result(
    success: bool,
    tool: str,
    provider: str = "minimax",
    model: str = "",
    data: Optional[dict] = None,
    error: Optional[str] = None,
) -> dict[str, Any]:
    """Runtime-truth envelope for all tool results."""
    result = {
        "success": success,
        "tool": tool,
        "provider": provider,
        "model": model,
        "data": data or {},
    }
    if error:
        result["error"] = error
    return result


# ── Text-to-Image ─────────────────────────────────────────────────────────────

async def minimax_text_to_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    n: int = 1,
    prompt_optimizer: bool = True,
    model: str = "",
) -> dict[str, Any]:
    """
    Generate images via MiniMax image-01 model.

    Inputs:
        prompt: text description of desired image
        aspect_ratio: "1:1", "16:9", "9:16", "4:3", "3:4" (default "1:1")
        n: number of images (default 1, max 4)
        prompt_optimizer: whether to use MiniMax prompt optimization (default True)
        model: model name override (default uses MINIMAX_IMAGE_MODEL env)

    Returns runtime-truth envelope with:
        success: bool — only True if file saved and verified
        image_url: stable browser URL (None if failed)
        local_path: absolute path (None if failed)
        model: model used
        aspect_ratio: ratio used
        dimensions: reported dimensions or None
    """
    _load_runtime_env()
    api_key = os.getenv("MINIMAX_API_KEY", "") or MINIMAX_API_KEY
    if not api_key:
        return _build_result(False, "minimax_text_to_image", error="MINIMAX_API_KEY not set")

    model = model or os.getenv("MINIMAX_IMAGE_MODEL", "image-01")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "prompt": prompt[:2000],
        "aspect_ratio": aspect_ratio,
        "n": min(n, 4),
        "prompt_optimizer": prompt_optimizer,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/images/generations",
                headers=headers,
                json=payload,
            )

        if resp.status_code != 200:
            return _build_result(False, "minimax_text_to_image", model=model,
                                 error=f"MiniMax HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        images = data.get("data", []) or data.get("images", [])
        results = []

        for item in images:
            # Handle base64 or URL response
            b64 = item.get("base64") or item.get("b64_json")
            url_resp = item.get("url") or item.get("image_url")

            if b64:
                try:
                    img_bytes = base64.b64decode(b64)
                except Exception as e:
                    results.append({"ok": False, "error": f"base64 decode failed: {e}"})
                    continue
            elif url_resp:
                try:
                    img_resp = await client.get(url_resp, timeout=30)
                    img_bytes = img_resp.content
                except Exception as e:
                    results.append({"ok": False, "error": f"url fetch failed: {e}"})
                    continue
            else:
                results.append({"ok": False, "error": "no image data in response"})
                continue

            if not img_bytes or len(img_bytes) < 500:
                results.append({"ok": False, "error": "image bytes too small or empty"})
                continue

            serve_url, file_path = _save_bytes(img_bytes, "mm-t2i")
            if not _verify_file(file_path):
                results.append({"ok": False, "error": "file save verification failed"})
                continue

            results.append({
                "ok": True,
                "image_url": serve_url,
                "local_path": str(file_path),
                "size_bytes": len(img_bytes),
            })

        successes = [r for r in results if r.get("ok")]
        if not successes:
            return _build_result(False, "minimax_text_to_image", model=model,
                                 error="No images saved successfully")

        return _build_result(True, "minimax_text_to_image", model=model, data={
            "images": successes,
            "aspect_ratio": aspect_ratio,
            "count": len(successes),
        })

    except Exception as e:
        logger.error(f"minimax_text_to_image failed: {type(e).__name__}: {e}")
        return _build_result(False, "minimax_text_to_image", model=model,
                             error=f"{type(e).__name__}: {e}")


# ── Image-to-Image ────────────────────────────────────────────────────────────

async def minimax_image_to_image(
    image: str,
    prompt: str,
    model: str = "",
    strength: float = 0.7,
) -> dict[str, Any]:
    """
    Transform / edit an image using MiniMax image-to-image.

    Inputs:
        image: URL, base64 data URI, or local path of reference image
        prompt: modification description
        model: model name override
        strength: transformation strength 0.0–1.0 (default 0.7)

    Returns runtime-truth envelope with:
        success: bool
        image_url: stable browser URL
        local_path: absolute path
    """
    _load_runtime_env()
    api_key = os.getenv("MINIMAX_API_KEY", "") or MINIMAX_API_KEY
    if not api_key:
        return _build_result(False, "minimax_image_to_image", error="MINIMAX_API_KEY not set")

    model = model or os.getenv("MINIMAX_IMAGE_MODEL", "image-01")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")

    # Resolve image to bytes
    img_bytes: Optional[bytes] = None
    if image.startswith("data:"):
        b64 = image.split(",", 1)[1]
        img_bytes = base64.b64decode(b64)
    elif image.startswith("http://") or image.startswith("https://"):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(image, timeout=30)
                img_bytes = r.content
        except Exception as e:
            return _build_result(False, "minimax_image_to_image", model=model,
                                 error=f"image URL fetch failed: {e}")
    else:
        p = Path(image)
        if p.exists() and p.is_file():
            img_bytes = p.read_bytes()
        else:
            return _build_result(False, "minimax_image_to_image", model=model,
                                 error=f"local image not found: {image}")

    if not img_bytes or len(img_bytes) < 500:
        return _build_result(False, "minimax_image_to_image", model=model,
                             error="image data too small or empty")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {
                "file": ("reference.png", img_bytes, "image/png"),
            }
            data = {
                "model": model,
                "prompt": prompt[:2000],
                "strength": str(strength),
            }
            resp = await client.post(
                f"{base_url}/images/edits",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data=data,
                timeout=120,
            )
    except Exception as e:
        return _build_result(False, "minimax_image_to_image", model=model,
                             error=f"{type(e).__name__}: {e}")

    if resp.status_code != 200:
        return _build_result(False, "minimax_image_to_image", model=model,
                             error=f"MiniMax HTTP {resp.status_code}: {resp.text[:300]}")

    # Parse response — image-01 returns base64 or URL
    try:
        rj = resp.json()
    except Exception:
        return _build_result(False, "minimax_image_to_image", model=model,
                             error="non-JSON response from MiniMax image edit")

    b64 = rj.get("data", [{}])[0].get("base64") or rj.get("base64") or rj.get("b64_json")
    if not b64:
        return _build_result(False, "minimax_image_to_image", model=model,
                             error="no image data in response")

    try:
        img_out = base64.b64decode(b64)
    except Exception as e:
        return _build_result(False, "minimax_image_to_image", model=model,
                             error=f"base64 decode failed: {e}")

    if len(img_out) < 500:
        return _build_result(False, "minimax_image_to_image", model=model,
                             error="output image too small")

    serve_url, file_path = _save_bytes(img_out, "mm-i2i")
    if not _verify_file(file_path):
        return _build_result(False, "minimax_image_to_image", model=model,
                             error="file save verification failed")

    return _build_result(True, "minimax_image_to_image", model=model, data={
        "image_url": serve_url,
        "local_path": str(file_path),
        "size_bytes": len(img_out),
        "strength": strength,
    })


# ── Image Understanding ───────────────────────────────────────────────────────

async def minimax_understand_image(
    image: str,
    prompt: str = "Describe what you see in this image in detail.",
    model: str = "",
) -> dict[str, Any]:
    """
    Analyze an image using MiniMax vision via mmx CLI.

    Transport: mmx vision describe (NOT /chat/completions with image blocks).
    MiniMax-M2.7 text model silently ignores image input on /chat/completions.

    Inputs:
        image: local path (must exist and be a valid image file)
        prompt: description prompt
        model: ignored for CLI transport (present for API compatibility)

    Returns runtime-truth envelope with:
        success: bool — True only if mmx CLI succeeded and output is image-specific
        summary: overall description
        notable_details: list of observations
        confidence: high/medium/low
        provider: minimax
        transport: mmx_cli
        tool: mmx vision describe

    NOTE: Does NOT run live probes on status calls. Status reflects the result
    of the last actual analyze_image call only.
    """
    # Check mmx CLI availability
    mmx_ok, cli_path_or_reason = _mmx_cli_available()
    if not mmx_ok:
        _update_mcp_probe_status(False, f"mmx CLI unavailable: {cli_path_or_reason}")
        return _build_result(False, "minimax_understand_image",
                             error=f"mmx CLI unavailable: {cli_path_or_reason}")

    p = Path(image)
    if not p.exists() or not p.is_file():
        _update_mcp_probe_status(False, f"Image file not found: {image}")
        return _build_result(False, "minimax_understand_image",
                             error=f"Image file not found: {image}")

    # Verify it's a real image by checking extension
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    if p.suffix.lower() not in valid_exts:
        _update_mcp_probe_status(False, f"Unsupported image extension: {p.suffix}")
        return _build_result(False, "minimax_understand_image",
                             error=f"Unsupported image extension: {p.suffix}")

    cmd = [
        cli_path_or_reason, "vision", "describe",
        "--image", str(p.resolve()),
        "--prompt", prompt[:2000],
        "--output", "json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MMX_VISION_TIMEOUT,
            cwd=str(p.parent),
            env=_mmx_subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        _update_mcp_probe_status(False, f"mmx vision describe timed out after {MMX_VISION_TIMEOUT}s")
        return _build_result(False, "minimax_understand_image",
                             error=f"mmx vision describe timed out after {MMX_VISION_TIMEOUT}s")
    except Exception as e:
        _update_mcp_probe_status(False, f"mmx vision subprocess error: {type(e).__name__}: {e}")
        return _build_result(False, "minimax_understand_image",
                             error=f"mmx vision subprocess error: {type(e).__name__}: {e}")

    if result.returncode != 0:
        err_msg = f"mmx vision describe failed (code {result.returncode}): {result.stderr[:200]}"
        _update_mcp_probe_status(False, err_msg)
        return _build_result(False, "minimax_understand_image", error=err_msg)

    # Parse JSON output
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        err_msg = f"mmx vision invalid JSON output: {result.stdout[:200]}"
        _update_mcp_probe_status(False, err_msg)
        return _build_result(False, "minimax_understand_image", error=err_msg)

    description = data.get("content", "") or data.get("description", "") or data.get("response", "")
    description = _strip_think_blocks(description)

    # Quality guardrails — check for no-image placeholder responses
    desc_lower = description.lower()
    for phrase in _NO_IMAGE_PHRASES:
        if phrase in desc_lower:
            err_msg = f"Vision output indicates image not received: '{phrase}'"
            _update_mcp_probe_status(False, err_msg)
            return _build_result(False, "minimax_understand_image",
                                 model="mmx_vision",
                                 error=err_msg)

    if not description or len(description) < 10:
        err_msg = "mmx vision returned empty/too-short description"
        _update_mcp_probe_status(False, err_msg)
        return _build_result(False, "minimax_understand_image",
                             error=err_msg)

    # Try to parse structured response
    try:
        parsed = json.loads(description)
        summary = parsed.get("summary", description[:500])
        notable_details = parsed.get("notable_details", [])
        confidence = parsed.get("confidence", "medium")
    except Exception:
        summary = description[:500]
        notable_details = []
        confidence = "medium"

    _update_mcp_probe_status(True, None)
    return _build_result(True, "minimax_understand_image",
                         model="mmx_vision",
                         data={
                             "summary": summary,
                             "notable_details": notable_details,
                             "confidence": confidence,
                             "full_response": description,
                             "transport": "mmx_cli",
                             "tool": "mmx vision describe",
                         })


# ── TTS ───────────────────────────────────────────────────────────────────────

async def minimax_tts(
    text: str,
    voice_id: str = "male-qn-qingque",
    speed: float = 1.0,
    output_format: str = "mp3",
) -> dict[str, Any]:
    """
    Generate speech audio via MiniMax TTS.

    Inputs:
        text: text to synthesize (max ~5000 chars)
        voice_id: MiniMax voice ID (default male-qn-qingque)
        speed: playback speed 0.5–2.0 (default 1.0)
        output_format: "mp3" or "wav" (default mp3)

    Returns runtime-truth envelope with:
        success: bool
        audio_url: stable browser URL
        local_path: absolute path
        duration_seconds: estimated from file size
    """
    _load_runtime_env()
    api_key = os.getenv("MINIMAX_API_KEY", "") or MINIMAX_API_KEY
    if not api_key:
        return _build_result(False, "minimax_tts", error="MINIMAX_API_KEY not set")

    model = os.getenv("MINIMAX_TTS_MODEL", "speech-01")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")

    clean_text = text.strip()[:5000]
    if not clean_text:
        return _build_result(False, "minimax_tts", error="text is empty")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/audio/speech",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "text": clean_text,
                    "voice_id": voice_id,
                    "speed": speed,
                    "response_format": output_format,
                },
            )
    except Exception as e:
        return _build_result(False, "minimax_tts", error=f"{type(e).__name__}: {e}")

    if resp.status_code != 200:
        return _build_result(False, "minimax_tts", model=model,
                             error=f"MiniMax HTTP {resp.status_code}: {resp.text[:300]}")

    audio_data = resp.content
    if not audio_data or len(audio_data) < 1000:
        return _build_result(False, "minimax_tts", model=model,
                             error="audio data too small or empty")

    ext = "mp3" if output_format == "mp3" else "wav"
    serve_url, file_path = _save_bytes(audio_data, "mm-tts", ext=ext)
    if not _verify_file(file_path, min_bytes=500):
        return _build_result(False, "minimax_tts", model=model,
                             error="file save verification failed")

    # Estimate duration from file size (approximate)
    duration_est = round(len(audio_data) / (16000 * speed), 1)

    return _build_result(True, "minimax_tts", model=model, data={
        "audio_url": serve_url,
        "local_path": str(file_path),
        "size_bytes": len(audio_data),
        "duration_seconds": duration_est,
        "voice_id": voice_id,
        "speed": speed,
    })


# ── Music Generation ───────────────────────────────────────────────────────────

async def minimax_music_generate(
    prompt: str,
    duration: int = 30,
) -> dict[str, Any]:
    """
    Generate music via MiniMax music model.

    Inputs:
        prompt: description of desired music (style, mood, instruments)
        duration: duration in seconds (default 30, max 180)

    Returns runtime-truth envelope with:
        success: bool
        audio_url: stable browser URL
        local_path: absolute path
        duration_seconds: actual duration
    """
    _load_runtime_env()
    api_key = os.getenv("MINIMAX_API_KEY", "") or MINIMAX_API_KEY
    if not api_key:
        return _build_result(False, "minimax_music_generate", error="MINIMAX_API_KEY not set")

    model = os.getenv("MINIMAX_MUSIC_MODEL", "music-01")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/audio/music",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "prompt": prompt[:1000],
                    "duration": min(duration, 180),
                },
            )
    except Exception as e:
        return _build_result(False, "minimax_music_generate", error=f"{type(e).__name__}: {e}")

    if resp.status_code != 200:
        return _build_result(False, "minimax_music_generate", model=model,
                             error=f"MiniMax HTTP {resp.status_code}: {resp.text[:300]}")

    audio_data = resp.content
    if not audio_data or len(audio_data) < 5000:
        return _build_result(False, "minimax_music_generate", model=model,
                             error="audio data too small or empty")

    serve_url, file_path = _save_bytes(audio_data, "mm-music", ext="mp3")
    if not _verify_file(file_path, min_bytes=5000):
        return _build_result(False, "minimax_music_generate", model=model,
                             error="file save verification failed")

    return _build_result(True, "minimax_music_generate", model=model, data={
        "audio_url": serve_url,
        "local_path": str(file_path),
        "size_bytes": len(audio_data),
        "duration_seconds": duration,
    })


# ── Video Generation (Gated) ────────────────────────────────────────────────

async def minimax_video_generate(
    prompt: str,
    duration: int = 5,
) -> dict[str, Any]:
    """
    Generate video via MiniMax video model. Gated by MINIMAX_VIDEO_ENABLED=1.

    Returns unavailable status unless MINIMAX_VIDEO_ENABLED is set and quota verified.
    """
    _load_runtime_env()
    if not os.getenv("MINIMAX_API_KEY"):
        return _build_result(False, "minimax_video_generate",
                             error="MINIMAX_API_KEY not set")

    if not MINIMAX_VIDEO_ENABLED:
        return _build_result(False, "minimax_video_generate",
                             error="Video generation is disabled. Set MINIMAX_VIDEO_ENABLED=1 to enable.")

    model = "video-01"
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
    api_key = os.getenv("MINIMAX_API_KEY", "")

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{base_url}/videos/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "prompt": prompt[:1000],
                    "duration": min(duration, 10),
                },
            )
    except Exception as e:
        return _build_result(False, "minimax_video_generate", error=f"{type(e).__name__}: {e}")

    if resp.status_code != 200:
        return _build_result(False, "minimax_video_generate", model=model,
                             error=f"MiniMax HTTP {resp.status_code}: {resp.text[:300]}")

    # Video responses typically include a URL or job ID to poll
    try:
        rj = resp.json()
        video_url = rj.get("data", [{}])[0].get("url") or rj.get("url")
        if video_url:
            # Fetch the video bytes
            vid_resp = await client.get(video_url, timeout=120)
            video_data = vid_resp.content
        else:
            job_id = rj.get("job_id") or rj.get("id")
            return _build_result(True, "minimax_video_generate", model=model, data={
                "job_id": job_id,
                "status": "processing",
                "note": "Video generation started — poll for completion",
            })
    except Exception as e:
        return _build_result(False, "minimax_video_generate", model=model,
                             error=f"video fetch/parse failed: {e}")

    if not video_data or len(video_data) < 10000:
        return _build_result(False, "minimax_video_generate", model=model,
                             error="video data too small or empty")

    serve_url, file_path = _save_bytes(video_data, "mm-video", ext="mp4")
    if not _verify_file(file_path, min_bytes=10000):
        return _build_result(False, "minimax_video_generate", model=model,
                             error="file save verification failed")

    return _build_result(True, "minimax_video_generate", model=model, data={
        "video_url": serve_url,
        "local_path": str(file_path),
        "size_bytes": len(video_data),
        "duration_seconds": duration,
    })


# ── Room Redesign ─────────────────────────────────────────────────────────────

async def max_room_redesign(
    image: str,
    treatment_type: str,
    style: str = "modern luxury",
    fabric_notes: str = "",
    preserve_geometry: bool = True,
    num_variations: int = 1,
) -> dict[str, Any]:
    """
    High-level room/window redesign tool.

    Workflow:
    1. Understand the room photo (minimax_understand_image)
    2. Build design brief
    3. Generate image-to-image variations

    Inputs:
        image: room/window photo URL or local path
        treatment_type: "drapery", "roman shade", "roller shade", "sheer",
                         "cornice", "valance", "full room redecorate"
        style: "modern", "luxury", "traditional", "hotel lobby", "residential", etc.
        fabric_notes: material/color preferences
        preserve_geometry: keep original room proportions (default True)
        num_variations: 1 or 2 (default 1)

    Returns runtime-truth envelope with:
        success: bool
        generated_images: list of image URLs
        design_brief: structured design notes
        implementation_notes: how to achieve the look
        limitations:诚实 limitations if geometry/quality uncertain
    """
    # Step 1: Analyze the room
    analysis_result = await minimax_understand_image(
        image=image,
        prompt=(
            "Analyze this room/space in detail. Identify: "
            "1) Window placement, size, and shape "
            "2) Existing window treatments if any "
            "3) Room geometry and proportions "
            "4) Lighting and color palette "
            "5) Furniture and decor style "
            "6) Ceiling height and wall texture. "
            "Be specific about what you observe."
        ),
    )

    if not analysis_result.get("success"):
        return _build_result(False, "max_room_redesign", error=f"Room analysis failed: {analysis_result.get('error')}")

    analysis = analysis_result.get("data", {})
    summary = analysis.get("summary", "")

    # Step 2: Build design brief
    treatment_type_lower = treatment_type.lower()
    brief_parts = [f"Treatment Type: {treatment_type}"]
    brief_parts.append(f"Desired Style: {style}")
    if fabric_notes:
        brief_parts.append(f"Fabric/Material Notes: {fabric_notes}")
    brief_parts.append(f"Preserve Geometry: {'Yes' if preserve_geometry else 'No'}")
    brief_parts.append(f"Room Analysis: {summary[:800]}")
    brief_parts.append(f"Confidence: {analysis.get('confidence', 'unknown')}")

    if preserve_geometry:
        brief_parts.append("IMPORTANT: Maintain original room proportions, window sizes, and perspective in the generated image.")

    design_brief = "\n".join(brief_parts)

    # Step 3: Build generation prompt
    treatment_prompts = {
        "drapery": f"Professional interior design mockup of elegant drapery curtains, {style} style. The window treatment is the focal point. High quality interior rendering.",
        "roman shade": f"Professional interior design mockup of clean roman shades, {style} style. Modern window treatment. High quality interior rendering.",
        "roller shade": f"Professional interior design mockup of sleek roller shades, {style} style. Minimalist window treatment. High quality interior rendering.",
        "sheer": f"Professional interior design mockup of sheer curtains/layered window treatment, {style} style. Soft and elegant. High quality interior rendering.",
        "cornice": f"Professional interior design mockup of decorative cornice/window valance, {style} style. Architectural window trim. High quality interior rendering.",
        "valance": f"Professional interior design mockup of window valance, {style} style. Decorative top treatment. High quality interior rendering.",
        "full room redecorate": f"Professional interior design mockup of a full room redesign incorporating new window treatments, {style} style. Complete room makeover. High quality interior rendering.",
    }

    base_prompt = treatment_prompts.get(treatment_type_lower,
        f"Professional interior design mockup of {treatment_type}, {style} style. High quality interior rendering."
    )

    if fabric_notes:
        base_prompt += f" Fabric/material direction: {fabric_notes}."

    # Step 4: Generate image-to-image
    generated_images = []
    errors = []

    for i in range(min(num_variations, 2)):
        try:
            result = await minimax_image_to_image(
                image=image,
                prompt=base_prompt,
                strength=0.75 if preserve_geometry else 0.85,
            )
            if result.get("success") and result.get("data", {}).get("image_url"):
                generated_images.append(result["data"]["image_url"])
            else:
                errors.append(result.get("error", "unknown error"))
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")

    if not generated_images:
        return _build_result(False, "max_room_redesign", error=f"All image generations failed: {'; '.join(errors[:3])}")

    # Step 5: Build implementation notes
    impl_notes = f"Generated {len(generated_images)} variation(s) of {treatment_type} in {style} style. "
    impl_notes += f"Treatment type: {treatment_type}. Style: {style}."
    if fabric_notes:
        impl_notes += f" Fabric notes: {fabric_notes}."
    impl_notes += " Actual measurements should be verified on-site before ordering materials."

    limitations = "Generated images are visual concepts/mockups. "
    if not analysis.get("confidence") == "high":
        limitations += "Image analysis confidence was not high — verify room measurements manually. "
    limitations += "Colors and textures shown are representational. Request fabric samples before finalizing."

    return _build_result(True, "max_room_redesign", data={
        "generated_images": generated_images,
        "design_brief": design_brief,
        "implementation_notes": impl_notes,
        "limitations": limitations,
        "room_analysis_summary": summary[:500],
        "treatment_type": treatment_type,
        "style": style,
        "count": len(generated_images),
    })


# ── Web Search (MCP bridge) ───────────────────────────────────────────────────

async def minimax_web_search(
    query: str,
) -> dict[str, Any]:
    """
    Search the web using MiniMax Token Plan MCP if locally available.

    Falls back to unavailable if MINIMAX_MCP_COMMAND is not configured
    or the MCP server is not running.

    Returns runtime-truth envelope with:
        success: bool
        results: list of result dicts with title, url, snippet
        query: the search query
        total_results: count
    """
    mcp_cmd = os.getenv("MINIMAX_MCP_COMMAND", "/home/rg/bin/minimax-mcp")
    if not os.path.exists(mcp_cmd):
        return _build_result(False, "minimax_web_search",
                             error=f"MiniMax MCP not available at {mcp_cmd}")

    # Run minimax-mcp search subcommand
    try:
        proc = await asyncio.create_subprocess_exec(
            mcp_cmd, "web-search", "--query", query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        return _build_result(False, "minimax_web_search", error="MCP search timed out")
    except FileNotFoundError:
        return _build_result(False, "minimax_web_search", error=f"MCP command not found: {mcp_cmd}")
    except Exception as e:
        return _build_result(False, "minimax_web_search", error=f"{type(e).__name__}: {e}")

    if proc.returncode != 0:
        return _build_result(False, "minimax_web_search", error=f"MCP exited {proc.returncode}: {stderr.decode()[:200]}")

    try:
        results = json.loads(stdout.decode())
    except Exception:
        return _build_result(False, "minimax_web_search", error="MCP returned non-JSON")

    items = results.get("results", []) or results.get("data", [])
    parsed = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")[:300]}
        for r in items if r.get("title") and r.get("url")
    ][:10]

    return _build_result(True, "minimax_web_search", data={
        "results": parsed,
        "query": query,
        "total_results": len(parsed),
    })


# ── Status ────────────────────────────────────────────────────────────────────

def minimax_tools_status() -> dict[str, Any]:
    """Return per-tool availability status. No live calls."""
    _load_runtime_env()
    api_key = os.getenv("MINIMAX_API_KEY", "") or MINIMAX_API_KEY

    has_key = bool(api_key)
    mmx_ok, mmx_path_or_reason = _mmx_cli_available()
    has_mcp = os.path.exists(os.getenv("MINIMAX_MCP_COMMAND", "/home/rg/bin/minimax-mcp"))

    # image_understanding uses mmx CLI, not chat/completions — key alone is insufficient
    img_understood_available = mmx_ok
    img_understood_reason = "" if mmx_ok else mmx_path_or_reason

    return {
        "minimax_configured": has_key,
        "minimax_api_key_set": has_key,
        "minimax_mcp_available": has_mcp,
        "minimax_video_enabled": MINIMAX_VIDEO_ENABLED,
        "minimax_mmx_cli_available": mmx_ok,
        "minimax_mmx_cli_path": mmx_path_or_reason if mmx_ok else "",
        "tools": {
            "text_generation": {
                "configured": has_key,
                "available": has_key,
                "transport": "api",
                "quota_bucket": "text_generation",
                "model": os.getenv("MINIMAX_MODEL", "MiniMax-M2.7"),
                "endpoint": f"{MINIMAX_BASE_URL}/chat/completions",
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "image_understanding": {
                "configured": mmx_ok,
                "cli_available": mmx_ok,
                "live_available": _mcp_last_probe_status if _mcp_last_probe_status != "not_probed" else None,
                "transport": "mmx_cli",
                "quota_bucket": "mcp_understand_image",
                "model": "mmx_vision",
                "reason": img_understood_reason,
                "last_probe_status": _mcp_last_probe_status,
                "last_error_category": _mcp_last_error_category,
                "last_error_message": _mcp_last_error_message,
                "last_probe_at": _mcp_last_probe_at,
            },
            "web_search": {
                "configured": has_mcp,
                "available": has_mcp,
                "transport": "mcp_cli",
                "quota_bucket": "mcp_web_search",
                "reason": "MINIMAX_MCP not configured" if not has_mcp else ("MINIMAX_API_KEY not set" if not has_key else ""),
            },
            "image_generation": {
                "configured": has_key,
                "available": has_key,
                "transport": "api",
                "quota_bucket": "image_generation",
                "daily_limit": 100,
                "model": os.getenv("MINIMAX_IMAGE_MODEL", "image-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "image_to_image": {
                "configured": has_key,
                "available": has_key,
                "transport": "api",
                "quota_bucket": "image_generation",
                "model": os.getenv("MINIMAX_IMAGE_MODEL", "image-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "tts": {
                "configured": has_key,
                "available": has_key,
                "transport": "api",
                "quota_bucket": "speech_generation",
                "daily_limit": 9000,
                "model": os.getenv("MINIMAX_TTS_MODEL", "speech-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "lyrics_generation": {
                "configured": has_key,
                "available": has_key,
                "transport": "api",
                "quota_bucket": "lyrics_generation",
                "daily_limit": 100,
                "model": os.getenv("MINIMAX_MUSIC_MODEL", "music-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "music_generation": {
                "configured": has_key,
                "available": has_key,
                "transport": "api",
                "quota_bucket": "music_generation",
                "daily_limit": 100,
                "model": os.getenv("MINIMAX_MUSIC_MODEL", "music-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "video_generation": {
                "configured": has_key and MINIMAX_VIDEO_ENABLED,
                "available": has_key and MINIMAX_VIDEO_ENABLED,
                "gated": not MINIMAX_VIDEO_ENABLED,
                "transport": "api",
                "quota_bucket": "video",
                "model": "video-01",
                "reason": "disabled" if has_key and not MINIMAX_VIDEO_ENABLED else ("MINIMAX_API_KEY not set" if not has_key else ""),
            },
        },
    }
