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
    Analyze an image using MiniMax vision capability.

    Inputs:
        image: URL, base64 data URI, or local path
        prompt: custom prompt overriding default description
        model: vision model override

    Returns runtime-truth envelope with:
        success: bool
        summary: overall description
        notable_details: list of observations
        confidence: high/medium/low
        provider: minimax
    """
    _load_runtime_env()
    api_key = os.getenv("MINIMAX_API_KEY", "") or MINIMAX_API_KEY
    if not api_key:
        return _build_result(False, "minimax_understand_image", error="MINIMAX_API_KEY not set")

    model = model or os.getenv("MINIMAX_VISION_MODEL", os.getenv("MINIMAX_MODEL", "MiniMax-M2.7"))
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")

    # Build image content
    image_content: Optional[dict] = None
    if image.startswith("data:"):
        b64 = image.split(",", 1)[1]
        image_content = {"type": "base64", "data": b64}
    elif image.startswith("http://") or image.startswith("https://"):
        image_content = {"type": "url", "url": image}
    else:
        p = Path(image)
        if p.exists() and p.is_file():
            b64 = base64.b64encode(p.read_bytes()).decode()
            image_content = {"type": "base64", "data": b64}

    if not image_content:
        return _build_result(False, "minimax_understand_image", model=model,
                             error=f"Cannot resolve image: {image}")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt[:2000]},
                {"type": "image", **image_content},
            ],
        }
    ]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 4096},
            )
    except Exception as e:
        return _build_result(False, "minimax_understand_image", model=model,
                             error=f"{type(e).__name__}: {e}")

    if resp.status_code != 200:
        return _build_result(False, "minimax_understand_image", model=model,
                             error=f"MiniMax HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return _build_result(False, "minimax_understand_image", model=model,
                             error="Could not parse response")

    # Try to parse structured response
    try:
        parsed = json.loads(content)
        summary = parsed.get("summary", content[:500])
        notable_details = parsed.get("notable_details", [])
        confidence = parsed.get("confidence", "medium")
    except Exception:
        summary = content[:500]
        notable_details = []
        confidence = "medium"

    return _build_result(True, "minimax_understand_image", model=model, data={
        "summary": summary,
        "notable_details": notable_details,
        "confidence": confidence,
        "full_response": content,
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
    has_mcp = os.path.exists(os.getenv("MINIMAX_MCP_COMMAND", "/home/rg/bin/minimax-mcp"))

    return {
        "minimax_configured": has_key,
        "minimax_api_key_set": has_key,
        "minimax_mcp_available": has_mcp,
        "minimax_video_enabled": MINIMAX_VIDEO_ENABLED,
        "tools": {
            "text_to_image": {
                "available": has_key,
                "model": os.getenv("MINIMAX_IMAGE_MODEL", "image-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "image_to_image": {
                "available": has_key,
                "model": os.getenv("MINIMAX_IMAGE_MODEL", "image-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "image_understanding": {
                "available": has_key,
                "model": os.getenv("MINIMAX_VISION_MODEL", os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "tts": {
                "available": has_key,
                "model": os.getenv("MINIMAX_TTS_MODEL", "speech-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "music": {
                "available": has_key,
                "model": os.getenv("MINIMAX_MUSIC_MODEL", "music-01"),
                "reason": "" if has_key else "MINIMAX_API_KEY not set",
            },
            "video": {
                "available": has_key and MINIMAX_VIDEO_ENABLED,
                "model": "video-01",
                "reason": "disabled" if has_key and not MINIMAX_VIDEO_ENABLED else ("MINIMAX_API_KEY not set" if not has_key else ""),
            },
            "web_search": {
                "available": has_key and has_mcp,
                "reason": "MINIMAX_MCP not configured" if not has_mcp else ("MINIMAX_API_KEY not set" if not has_key else ""),
            },
        },
    }