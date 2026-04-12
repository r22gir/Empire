"""Shared Ollama vision routing with lightweight-first fallback."""
from __future__ import annotations

import os
from typing import Iterable, Optional

import httpx

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
PRIMARY_VISION_MODEL = os.getenv("OLLAMA_VISION_PRIMARY_MODEL", "moondream")
FALLBACK_VISION_MODEL = os.getenv("OLLAMA_VISION_FALLBACK_MODEL", "llava")


def vision_model_order(preferred: Optional[str] = None) -> list[str]:
    """Return vision models in routing order without duplicates."""
    candidates: list[str] = []
    for model in [preferred, PRIMARY_VISION_MODEL, FALLBACK_VISION_MODEL]:
        if model and model not in candidates:
            candidates.append(model)
    return candidates


async def generate_vision_response(
    *,
    prompt: str,
    image_b64: str,
    preferred_model: Optional[str] = None,
    timeout: float = 120.0,
) -> tuple[Optional[str], Optional[str]]:
    """Call Ollama vision using the primary lightweight model first."""
    models = vision_model_order(preferred_model)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for model in models:
            try:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                return resp.json().get("response", ""), model
            except Exception:
                continue
    return None, None
