#!/usr/bin/env python3
"""
Layer 3: Bulk classify remaining images through Ollama LLaVA.
Reads /data/images/presorted_inventory.json.
Processes images with pre_tag in ('needs-ai', 'unknown').
Saves progress after each batch. Safe to stop and resume.
Run overnight: nohup python3 ollama_bulk_classify.py &
"""
import os
import sys
import json
import base64
import urllib.request
import urllib.error
import shutil
import time
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

PRESORTED_FILE = "/data/images/presorted_inventory.json"
PROGRESS_FILE = "/data/images/ollama_progress.json"
CLASSIFIED_DIR = "/data/images/classified"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llava"

BATCH_SIZE = 1              # One at a time for CPU (no parallelism)
SAVE_EVERY = 25             # Save progress every N images
PAUSE_BETWEEN = 1.0         # Seconds between images (let CPU breathe)
CONFIDENCE_THRESHOLD = 0.6  # Below this = ambiguous, goes to Layer 4 (Grok)

CLASSIFY_PROMPT = """You are an image classifier for two businesses:
1. Empire Workroom - drapery, upholstery, curtains, blinds, fabric work, sewing
2. WoodCraft - woodworking, carpentry, furniture, cabinetry, wood finishing

Analyze this image. Respond with ONLY a JSON object:
{
  "business": "empire-workroom" | "woodcraft" | "general" | "personal",
  "category": "<category>",
  "description": "<1 sentence>",
  "quality": "high" | "medium" | "low",
  "social_ready": true | false,
  "confidence": 0.0 to 1.0
}

Categories:
- empire-workroom: before-after, finished-installs, fabrics-materials, in-progress, workshop, team
- woodcraft: before-after, finished-pieces, raw-materials, in-progress, workshop, team
- general: storefront, branding, events, misc
- personal: (empty string for category)
"""


def prepare_image(filepath, max_size=768):
    """Resize for Ollama (smaller = faster on CPU)."""
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
                img.save(buf, format="JPEG", quality=75)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            pass
    # Fallback: raw base64
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def classify_one(filepath):
    """Classify a single image through Ollama. Synchronous (CPU is the bottleneck)."""
    img_b64 = prepare_image(filepath)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": CLASSIFY_PROMPT,
        "images": [img_b64],
        "stream": False
    }

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = json.loads(resp.read().decode("utf-8")).get("response", "")

        # Parse JSON
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(cleaned)

        return {
            "business": result.get("business", "general"),
            "category": result.get("category", "misc"),
            "description": result.get("description", ""),
            "quality": result.get("quality", "medium"),
            "social_ready": result.get("social_ready", False),
            "confidence": result.get("confidence", 0.5),
            "classified_by": "ollama-llava",
            "error": None
        }
    except Exception as e:
        return {
            "business": "general",
            "category": "misc",
            "description": f"Ollama error: {str(e)[:100]}",
            "quality": "low",
            "social_ready": False,
            "confidence": 0.0,
            "classified_by": "ollama-llava",
            "error": str(e)[:200]
        }


def load_progress():
    """Load progress file to resume interrupted runs."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"processed": [], "stats": {}}


def save_progress(processed_set, stats):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"processed": list(processed_set), "stats": stats}, f)


def run_bulk_classification():
    """Main entry point. Safe to stop (Ctrl+C) and resume."""
    with open(PRESORTED_FILE, "r") as f:
        data = json.load(f)

    images = data["images"]

    # Filter to only images that need AI classification
    needs_ai = [
        img for img in images
        if img.get("pre_tag") in ("needs-ai", "unknown")
        and not img.get("classified_by")
    ]

    # Load progress (for resume)
    progress = load_progress()
    already_done = set(progress.get("processed", []))

    todo = [img for img in needs_ai if img["path"] not in already_done]

    print(f"\n{'='*60}")
    print(f"OLLAMA BULK CLASSIFICATION")
    print(f"{'='*60}")
    print(f"Total needing AI:   {len(needs_ai):,}")
    print(f"Already processed:  {len(already_done):,}")
    print(f"Remaining:          {len(todo):,}")
    est_hours = len(todo) * 45 / 3600  # ~45s average per image
    print(f"Estimated time:     {est_hours:.1f} hours ({est_hours/24:.1f} days)")
    print(f"{'='*60}")
    print(f"Starting... (safe to Ctrl+C and resume later)\n")

    stats = progress.get("stats", {
        "processed": len(already_done),
        "empire-workroom": 0, "woodcraft": 0, "general": 0,
        "personal": 0, "ambiguous": 0, "errors": 0
    })

    for i, img in enumerate(todo):
        filepath = img["path"]
        if not os.path.exists(filepath):
            already_done.add(filepath)
            continue

        start = time.time()
        result = classify_one(filepath)
        elapsed = time.time() - start

        # Update image in the inventory
        img.update(result)
        img["classified_at"] = datetime.now().isoformat()

        # Handle ambiguous
        if result["confidence"] < CONFIDENCE_THRESHOLD:
            img["pre_tag"] = "ambiguous"
            stats["ambiguous"] = stats.get("ambiguous", 0) + 1
        else:
            img["pre_tag"] = result["business"]
            stats[result["business"]] = stats.get(result["business"], 0) + 1

        # Copy to classified folder
        biz = img.get("pre_tag", "general")
        cat = result.get("category", "misc")
        if biz == "ambiguous":
            dest_dir = os.path.join(CLASSIFIED_DIR, "ambiguous")
        elif biz == "personal":
            dest_dir = os.path.join(CLASSIFIED_DIR, "personal")
        else:
            dest_dir = os.path.join(CLASSIFIED_DIR, biz, cat or "misc")

        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, img["filename"])
        if not os.path.exists(dest):
            try:
                shutil.copy2(filepath, dest)
                img["classified_path"] = dest
            except (OSError, IOError):
                pass

        if result.get("error"):
            stats["errors"] = stats.get("errors", 0) + 1

        already_done.add(filepath)
        stats["processed"] = len(already_done)

        # Progress output
        done = len(already_done)
        total = len(needs_ai)
        remaining = total - done
        eta_hours = remaining * elapsed / 3600
        print(f"[{done}/{total}] {elapsed:.1f}s | {img['filename'][:30]:30s} | "
              f"{result['business']:16s} | conf={result['confidence']:.2f} | "
              f"ETA: {eta_hours:.1f}h")

        # Save progress periodically
        if (i + 1) % SAVE_EVERY == 0:
            save_progress(already_done, stats)
            # Also save back to presorted inventory
            with open(PRESORTED_FILE, "w") as f:
                json.dump(data, f)
            print(f"  >> Progress saved ({done} done)")

        time.sleep(PAUSE_BETWEEN)

    # Final save
    save_progress(already_done, stats)
    with open(PRESORTED_FILE, "w") as f:
        json.dump(data, f)

    print(f"\n{'='*60}")
    print(f"BULK CLASSIFICATION COMPLETE")
    print(f"{'='*60}")
    for k, v in stats.items():
        print(f"  {k:20s}: {v}")
    ambiguous = stats.get("ambiguous", 0)
    print(f"\nAmbiguous (need Grok): {ambiguous:,}")
    if ambiguous > 0:
        est_cost = ambiguous * 0.015
        print(f"Estimated Grok cost:   ${est_cost:.2f}")


if __name__ == "__main__":
    run_bulk_classification()
