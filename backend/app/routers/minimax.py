"""
MiniMax Router — capability status and tool endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import logging
import asyncio

logger = logging.getLogger("max.minimax.api")

router = APIRouter(prefix="/minimax", tags=["MiniMax Capabilities"])


class CapabilityReportResponse(BaseModel):
    text: str
    tts: str
    image_generation: str
    image_to_image: str
    video_generation: str
    music_generation: str
    stt: str
    vision: str
    web_search: str
    access_paths: Dict[str, str]
    details: Optional[Dict[str, Any]] = None


@router.get("/status")
async def minimax_status():
    """
    Returns MiniMax capability status report with smoke-test results.
    No secrets exposed.
    """
    try:
        from app.services.max.minimax_adapter import get_capability_report
        report = await asyncio.wait_for(get_capability_report(), timeout=30.0)
        return {"status": "success", "report": report}
    except Exception as e:
        logger.warning(f"MiniMax status check failed: {e}")
        return {"status": "error", "error": str(e)[:200]}


@router.post("/tts")
async def minimax_tts(text: str, voice_id: str = "male-qn-qingse", speed: float = 1.0):
    """
    Generate TTS audio from text.
    Returns: {task_id, file_url, output_file}
    """
    try:
        from app.services.max.minimax_adapter import tts_synthesize
        result = await asyncio.wait_for(
            tts_synthesize(text=text, voice_id=voice_id, speed=speed, timeout=60.0),
            timeout=60.0
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.warning(f"MiniMax TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/image")
async def minimax_image(prompt: str, model: str = "image-01", resolution: str = "1K", num_images: int = 1):
    """
    Generate image(s) from text prompt.
    Returns: {task_id, images: [{file_path, url}]}
    """
    try:
        from app.services.max.minimax_adapter import image_generate
        result = await asyncio.wait_for(
            image_generate(prompt=prompt, model=model, resolution=resolution, num_images=num_images, timeout=120.0),
            timeout=120.0
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.warning(f"MiniMax image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/video")
async def minimax_video(prompt: str, model: str = "video-01", duration_seconds: int = 6, resolution: str = "540p"):
    """
    Generate video from text prompt.
    Returns: {task_id, video_url, status}
    """
    try:
        from app.services.max.minimax_adapter import video_generate
        result = await asyncio.wait_for(
            video_generate(prompt=prompt, model=model, duration_seconds=duration_seconds, resolution=resolution, timeout=300.0),
            timeout=300.0
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.warning(f"MiniMax video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/music")
async def minimax_music(prompt: str, model: str = "music-01"):
    """
    Generate music from text prompt.
    Returns: {task_id, music_url, status}
    """
    try:
        from app.services.max.minimax_adapter import music_generate
        result = await asyncio.wait_for(
            music_generate(prompt=prompt, model=model, timeout=300.0),
            timeout=300.0
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.warning(f"MiniMax music generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])