"""
Empire Inpainting Service — AI mockup generation using customer photos.

Generates per-tier mockups by inpainting the customer's actual photo:
  1. Detect regions (windows / furniture) via xAI Grok Vision (ONE call, cached)
  2. Render PIL masks (white = replace, black = keep)
  3. Stability AI inpainting per tier (3 tiers x N items)
  4. Clean aspirational mockups via Grok image gen (fallback / inspiration)
  5. Quality check, save to disk, return URLs

Fallback chain: Stability AI inpaint -> Grok image gen -> None
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
from typing import Optional

import httpx

logger = logging.getLogger("max.inpaint")

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_DIM = 1024
MASK_PADDING = 0.12
MASK_PADDING_RETRY = 0.20

from app.services.max.inpaint_prompts import (
    build_window_inpaint_prompt,
    build_window_clean_prompt,
    build_upholstery_inpaint_prompt,
    build_upholstery_clean_prompt,
    build_upholstery_details,
    get_negative_prompt,
)


def _save_image(data: bytes, prefix: str = "inpaint") -> str:
    """Save image bytes to disk, return serve URL."""
    fname = f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:6]}.png"
    (GENERATED_DIR / fname).write_bytes(data)
    return f"/api/v1/vision/images/{fname}"


def _save_thumbnail(data: bytes, prefix: str = "thumb", width: int = 400) -> str:
    """Save a resized thumbnail."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        ratio = width / img.width
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return _save_image(buf.getvalue(), prefix)
    except Exception:
        return _save_image(data, prefix)


class InpaintService:
    """Smart mockup generation: inpainted customer photos + clean mockups."""

    def __init__(self):
        self._region_cache: dict[str, list] = {}

    # ── Main entry point ─────────────────────────────────────────

    async def generate_all_mockups(
        self,
        photo_b64: str,
        rooms: list,
        style: str = "",
        xai_key: str = "",
        stability_key: str = "",
    ) -> dict:
        """Generate all mockup images for a quote.

        Returns:
            {
                "window_mockups": {
                    "A": {"inpainted_url": ..., "clean_url": ..., "thumb_url": ..., "provider": ...},
                    "B": {...}, "C": {...}
                },
                "furniture_mockups": {
                    "A": {...}, "B": {...}, "C": {...}
                },
                "provider": "stability" | "grok",
                "total_cost": 0.00,
                "images_generated": int,
            }
        """
        if not xai_key:
            xai_key = os.getenv("XAI_API_KEY", "")
        if not stability_key:
            stability_key = os.getenv("STABILITY_API_KEY", "")

        # Decode and preprocess photo
        photo_bytes = self._preprocess_image(photo_b64)
        if not photo_bytes:
            logger.warning("Could not preprocess customer photo")
            return {"window_mockups": {}, "furniture_mockups": {}, "provider": "none", "total_cost": 0, "images_generated": 0}

        # Extract treatment/color/furniture info from rooms
        first_room = rooms[0] if rooms else {}
        windows = first_room.get("windows", [])
        upholstery = first_room.get("upholstery", [])
        first_win = windows[0] if windows else {}
        first_uph = upholstery[0] if upholstery else {}

        treatment = first_win.get("treatmentType", "ripplefold")
        color = first_win.get("fabricColor", "")
        furniture_type = first_uph.get("furnitureType", "sofa")
        uph_color = first_uph.get("fabricColor", color)
        ai_analysis = first_uph.get("aiAnalysis", {})
        uph_details = build_upholstery_details(ai_analysis)

        # Detect regions (ONE Grok call)
        has_windows = bool(windows)
        has_furniture = bool(upholstery)
        regions = await self._detect_regions(photo_bytes, xai_key, has_windows, has_furniture)

        # Build masks
        window_mask = self._render_mask(photo_bytes, regions, "window", MASK_PADDING) if has_windows else None
        furniture_mask = self._render_mask(photo_bytes, regions, "furniture", MASK_PADDING) if has_furniture else None

        # Build all tasks
        tasks = []
        task_keys = []

        for tier in ["A", "B", "C"]:
            if has_windows:
                # Inpainted window
                win_prompt = build_window_inpaint_prompt(treatment, tier, color, style)
                win_neg = get_negative_prompt(treatment)
                tasks.append(self._inpaint_with_fallback(
                    photo_bytes, window_mask, win_prompt, win_neg,
                    stability_key, xai_key,
                    build_window_clean_prompt(treatment, tier, color, style),
                ))
                task_keys.append(("window", tier, "inpainted"))

                # Clean aspirational window
                clean_prompt = build_window_clean_prompt(treatment, tier, color, style)
                tasks.append(self._generate_clean_mockup(clean_prompt, xai_key))
                task_keys.append(("window", tier, "clean"))

            if has_furniture:
                # Inpainted furniture
                furn_prompt = build_upholstery_inpaint_prompt(furniture_type, tier, uph_color, uph_details, style)
                tasks.append(self._inpaint_with_fallback(
                    photo_bytes, furniture_mask, furn_prompt, "",
                    stability_key, xai_key,
                    build_upholstery_clean_prompt(furniture_type, tier, uph_color, uph_details, style),
                ))
                task_keys.append(("furniture", tier, "inpainted"))

                # Clean aspirational furniture
                clean_prompt = build_upholstery_clean_prompt(furniture_type, tier, uph_color, uph_details, style)
                tasks.append(self._generate_clean_mockup(clean_prompt, xai_key))
                task_keys.append(("furniture", tier, "clean"))

        # Run ALL in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Organize results
        window_mockups: dict = {}
        furniture_mockups: dict = {}
        total_cost = 0.0
        images_generated = 0
        primary_provider = "none"

        for (category, tier, img_type), result in zip(task_keys, results):
            if isinstance(result, Exception):
                logger.warning(f"Mockup failed {category}/{tier}/{img_type}: {result}")
                continue
            if not result:
                continue

            img_bytes = result.get("image")
            provider = result.get("provider", "unknown")
            cost = result.get("cost", 0.0)

            if not img_bytes:
                continue

            # Save full + thumbnail
            url = _save_image(img_bytes, f"{category}-{tier.lower()}")
            thumb_url = _save_thumbnail(img_bytes, f"{category}-{tier.lower()}-thumb")

            target = window_mockups if category == "window" else furniture_mockups
            if tier not in target:
                target[tier] = {}

            if img_type == "inpainted":
                target[tier]["inpainted_url"] = url
                target[tier]["inpainted_thumb"] = thumb_url
                target[tier]["provider"] = provider
                if primary_provider == "none":
                    primary_provider = provider
            else:
                target[tier]["clean_url"] = url
                target[tier]["clean_thumb"] = thumb_url

            total_cost += cost
            images_generated += 1

        return {
            "window_mockups": window_mockups,
            "furniture_mockups": furniture_mockups,
            "provider": primary_provider,
            "total_cost": round(total_cost, 4),
            "images_generated": images_generated,
        }

    # ── Image preprocessing ──────────────────────────────────────

    def _preprocess_image(self, b64_data: str) -> Optional[bytes]:
        """Decode base64, resize to max 1024x1024, return PNG bytes."""
        try:
            from PIL import Image

            # Strip data URI prefix
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]

            raw = base64.b64decode(b64_data)
            img = Image.open(io.BytesIO(raw))

            # Convert to RGB (remove alpha)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize if too large
            if img.width > MAX_IMAGE_DIM or img.height > MAX_IMAGE_DIM:
                ratio = min(MAX_IMAGE_DIM / img.width, MAX_IMAGE_DIM / img.height)
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return None

    # ── Region detection (ONE Grok call) ─────────────────────────

    async def _detect_regions(
        self, photo_bytes: bytes, xai_key: str,
        detect_windows: bool = True, detect_furniture: bool = False,
    ) -> list[dict]:
        """Ask Grok Vision to locate windows and/or furniture in the photo.
        Returns list of {label, type, x_pct, y_pct, w_pct, h_pct}.
        """
        if not xai_key:
            return []

        # Build the detection request
        target_desc = []
        if detect_windows:
            target_desc.append(
                "WINDOWS: For each window, return the bounding box of the window OPENING "
                "(glass area, not the wall around it). Type should be 'window'."
            )
        if detect_furniture:
            target_desc.append(
                "FURNITURE FABRIC: For each upholstered furniture piece, return bounding boxes "
                "covering ALL fabric/upholstered surfaces (seat cushions, back, arms). "
                "EXCLUDE legs, frame, floor, walls. Type should be 'furniture'."
            )

        prompt = (
            "Analyze this photo. Identify and locate the following items:\n\n"
            + "\n".join(target_desc) +
            "\n\nReturn coordinates as percentages of image dimensions (0-100).\n"
            "Return JSON ONLY:\n"
            '{"regions": [\n'
            '  {"label": "main window", "type": "window", "x_pct": 30, "y_pct": 15, "w_pct": 40, "h_pct": 55},\n'
            '  {"label": "sofa seat", "type": "furniture", "x_pct": 20, "y_pct": 60, "w_pct": 60, "h_pct": 25}\n'
            "]}"
        )

        img_b64 = base64.b64encode(photo_bytes).decode()
        data_uri = f"data:image/png;base64,{img_b64}"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
                    json={
                        "model": "grok-4-fast-non-reasoning",
                        "messages": [{"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": data_uri}},
                            {"type": "text", "text": prompt},
                        ]}],
                        "max_tokens": 1500,
                        "temperature": 0.2,
                    },
                )

            if resp.status_code != 200:
                logger.warning(f"Region detection API error: {resp.status_code}")
                return []

            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            m = re.search(r"\{[\s\S]*\}", content)
            if not m:
                logger.warning("Could not parse region detection response")
                return []

            data = json.loads(m.group(0))
            regions = data.get("regions", [])
            logger.info(f"Detected {len(regions)} regions: {[r.get('label') for r in regions]}")
            return regions

        except Exception as e:
            logger.error(f"Region detection failed: {e}")
            return []

    # ── Mask rendering (PIL) ─────────────────────────────────────

    def _render_mask(
        self, photo_bytes: bytes, regions: list, target_type: str, padding: float = 0.12
    ) -> Optional[bytes]:
        """Render a binary mask: white rectangles for target regions on black canvas."""
        try:
            from PIL import Image, ImageDraw

            img = Image.open(io.BytesIO(photo_bytes))
            w, h = img.size

            mask = Image.new("L", (w, h), 0)  # black canvas
            draw = ImageDraw.Draw(mask)

            found = False
            for region in regions:
                if region.get("type") != target_type:
                    continue

                # Convert percentages to pixels
                rx = region.get("x_pct", 0) / 100.0
                ry = region.get("y_pct", 0) / 100.0
                rw = region.get("w_pct", 0) / 100.0
                rh = region.get("h_pct", 0) / 100.0

                # Add padding
                pad_w = rw * padding
                pad_h = rh * padding
                x1 = max(0, (rx - pad_w)) * w
                y1 = max(0, (ry - pad_h)) * h
                x2 = min(1.0, (rx + rw + pad_w)) * w
                y2 = min(1.0, (ry + rh + pad_h)) * h

                draw.rectangle([x1, y1, x2, y2], fill=255)
                found = True

            if not found:
                # Fallback: mask center 50% of image
                cx, cy = w * 0.25, h * 0.15
                draw.rectangle([cx, cy, w * 0.75, h * 0.85], fill=255)
                logger.info(f"No {target_type} regions detected, using center fallback mask")

            buf = io.BytesIO()
            mask.save(buf, format="PNG")
            return buf.getvalue()

        except Exception as e:
            logger.error(f"Mask rendering failed: {e}")
            return None

    # ── Inpainting with fallback ─────────────────────────────────

    async def _inpaint_with_fallback(
        self,
        photo_bytes: bytes,
        mask_bytes: Optional[bytes],
        prompt: str,
        negative_prompt: str,
        stability_key: str,
        xai_key: str,
        fallback_prompt: str,
    ) -> Optional[dict]:
        """Try Stability AI inpaint, fall back to Grok image gen."""

        # Try Stability AI inpainting (if we have a mask and key)
        if stability_key and mask_bytes:
            result = await self._try_stability(photo_bytes, mask_bytes, prompt, negative_prompt, stability_key)
            if result:
                return {"image": result, "provider": "stability", "cost": 0.0}

        # Fallback: Grok image generation (no inpainting, new image)
        if xai_key:
            result = await self._try_grok(fallback_prompt, xai_key)
            if result:
                return {"image": result, "provider": "grok", "cost": 0.0}

        return None

    # ── Stability AI inpainting ──────────────────────────────────

    async def _try_stability(
        self,
        photo_bytes: bytes,
        mask_bytes: bytes,
        prompt: str,
        negative_prompt: str,
        api_key: str,
    ) -> Optional[bytes]:
        """Call Stability AI inpainting endpoint. Returns image bytes or None."""
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                files = {
                    "image": ("photo.png", photo_bytes, "image/png"),
                    "mask": ("mask.png", mask_bytes, "image/png"),
                }
                data = {
                    "prompt": prompt[:10000],
                    "output_format": "png",
                }
                if negative_prompt:
                    data["negative_prompt"] = negative_prompt[:10000]

                resp = await client.post(
                    "https://api.stability.ai/v2beta/stable-image/edit/inpaint",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "image/*",
                    },
                    files=files,
                    data=data,
                    timeout=90,
                )

            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                if len(resp.content) > 500:
                    logger.info(f"Stability inpaint success: {len(resp.content)} bytes")
                    return resp.content
                logger.warning("Stability returned tiny image")
                return None

            logger.warning(f"Stability inpaint error {resp.status_code}: {resp.text[:300]}")
            return None

        except Exception as e:
            logger.error(f"Stability inpaint failed: {e}")
            return None

    # ── Grok image generation (fallback) ─────────────────────────

    async def _try_grok(self, prompt: str, xai_key: str) -> Optional[bytes]:
        """Generate image via xAI Grok. Returns image bytes or None."""
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    "https://api.x.ai/v1/images/generations",
                    headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
                    json={"model": "grok-imagine-image", "prompt": prompt, "n": 1, "response_format": "url"},
                    timeout=45,
                )

            if resp.status_code != 200:
                return None

            url = resp.json().get("data", [{}])[0].get("url")
            if not url:
                return None

            # Download the image
            async with httpx.AsyncClient(timeout=30) as client:
                img_resp = await client.get(url)
                if img_resp.status_code == 200 and len(img_resp.content) > 500:
                    return img_resp.content

            return None

        except Exception as e:
            logger.error(f"Grok image gen failed: {e}")
            return None

    # ── Clean mockup generation ──────────────────────────────────

    async def _generate_clean_mockup(self, prompt: str, xai_key: str) -> Optional[dict]:
        """Generate aspirational mockup (NOT using customer photo)."""
        result = await self._try_grok(prompt, xai_key)
        if result:
            return {"image": result, "provider": "grok", "cost": 0.0}
        return None


# Singleton
inpaint_service = InpaintService()
