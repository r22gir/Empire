#!/usr/bin/env python3
"""
Layer 4: Grok Vision precision pass for ambiguous images.
Only processes images tagged 'ambiguous' by Ollama.
Costs ~$0.015/image. Check budget before running.
"""
import os
import sys
import json
import base64
import httpx
import asyncio
import shutil
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

PRESORTED_FILE = "/data/images/presorted_inventory.json"
CLASSIFIED_DIR = "/data/images/classified"
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_API_KEY = os.getenv("XAI_API_KEY")
GROK_MODEL = "grok-2-vision-1212"
COST_TRACKER_DB = os.getenv("COST_TRACKER_DB", "/home/rg/empire-repo/backend/data/token_usage.db")

BATCH_SIZE = 5
BATCH_DELAY = 2.0

CLASSIFY_PROMPT = """You are an expert image classifier for two businesses:
1. Empire Workroom - drapery, upholstery, curtains, blinds, fabric work, sewing
2. WoodCraft - woodworking, carpentry, furniture, cabinetry, wood finishing

A previous AI was not confident about this image. Please examine it carefully.

Respond with ONLY a JSON object:
{
  "business": "empire-workroom" | "woodcraft" | "general" | "personal",
  "category": "<category>",
  "description": "<1-2 detailed sentences>",
  "quality": "high" | "medium" | "low",
  "social_ready": true | false,
  "confidence": 0.0 to 1.0,
  "reasoning": "<why you chose this classification>"
}

Categories:
- empire-workroom: before-after, finished-installs, fabrics-materials, in-progress, workshop, team
- woodcraft: before-after, finished-pieces, raw-materials, in-progress, workshop, team
- general: storefront, branding, events, misc
- personal: (empty string)
"""


def prepare_image(filepath, max_size=1024):
    if HAS_PIL:
        try:
            with Image.open(filepath) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                w, h = img.size
                if max(w, h) > max_size:
                    ratio = max_size / max(w, h)
                    img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                return base64.b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"
        except Exception:
            pass
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), "image/jpeg"


async def log_cost(model, provider, input_tokens, output_tokens, cost):
    try:
        import sqlite3
        conn = sqlite3.connect(COST_TRACKER_DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO token_usage (timestamp, model, provider, input_tokens, output_tokens, cost_usd, endpoint, feature) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), model, provider, input_tokens, output_tokens, cost, "recovery-forge", "image_classification")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cost log failed: {e}")


async def classify_with_grok(filepath, client):
    img_b64, mime = prepare_image(filepath)
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": "Expert image classifier. JSON only."},
            {"role": "user", "content": [
                {"type": "text", "text": CLASSIFY_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
            ]}
        ],
        "max_tokens": 500,
        "temperature": 0.1
    }
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    resp = await client.post(GROK_API_URL, json=payload, headers=headers, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()

    raw = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    inp = usage.get("prompt_tokens", 0)
    out = usage.get("completion_tokens", 0)
    cost = (inp * 0.002 / 1000) + (out * 0.01 / 1000)
    await log_cost(GROK_MODEL, "xai", inp, out, cost)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    result = json.loads(cleaned)
    result["classified_by"] = "grok-vision"
    result["cost"] = cost
    return result


async def run_precision_pass():
    if not GROK_API_KEY:
        print("ERROR: XAI_API_KEY not set. Export it or add to backend/.env")
        sys.exit(1)

    with open(PRESORTED_FILE, "r") as f:
        data = json.load(f)

    ambiguous = [img for img in data["images"] if img.get("pre_tag") == "ambiguous"]

    if not ambiguous:
        print("No ambiguous images to process.")
        return

    est_cost = len(ambiguous) * 0.015
    print(f"Ambiguous images: {len(ambiguous):,}")
    print(f"Estimated cost:   ${est_cost:.2f}")
    print(f"Starting Grok precision pass...\n")

    total_cost = 0.0
    processed = 0

    async with httpx.AsyncClient() as client:
        for i in range(0, len(ambiguous), BATCH_SIZE):
            batch = ambiguous[i:i+BATCH_SIZE]
            for img in batch:
                if not os.path.exists(img["path"]):
                    continue
                try:
                    result = await classify_with_grok(img["path"], client)
                    img.update(result)
                    img["pre_tag"] = result.get("business", "general")
                    img["classified_at"] = datetime.now().isoformat()
                    total_cost += result.get("cost", 0)

                    # Copy to folder
                    biz = img["pre_tag"]
                    cat = result.get("category", "misc")
                    if biz == "personal":
                        dest_dir = os.path.join(CLASSIFIED_DIR, "personal")
                    else:
                        dest_dir = os.path.join(CLASSIFIED_DIR, biz, cat or "misc")
                    os.makedirs(dest_dir, exist_ok=True)
                    dest = os.path.join(dest_dir, img["filename"])
                    if not os.path.exists(dest):
                        shutil.copy2(img["path"], dest)
                        img["classified_path"] = dest

                    processed += 1
                    print(f"[{processed}/{len(ambiguous)}] {img['filename'][:30]:30s} | "
                          f"{result.get('business','?'):16s} | conf={result.get('confidence',0):.2f} | "
                          f"cost=${total_cost:.4f}")

                except Exception as e:
                    print(f"ERROR: {img['filename']}: {e}")

            if i + BATCH_SIZE < len(ambiguous):
                await asyncio.sleep(BATCH_DELAY)

    # Save
    with open(PRESORTED_FILE, "w") as f:
        json.dump(data, f)

    print(f"\n{'='*60}")
    print(f"GROK PRECISION PASS COMPLETE")
    print(f"Processed: {processed:,}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run_precision_pass())
