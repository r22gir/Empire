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
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Model selection: moondream (1B, faster) with llava fallback.
# Set OLLAMA_MODEL env var to override, e.g.: OLLAMA_MODEL=llava
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "moondream")
FALLBACK_MODEL = "llava" if OLLAMA_MODEL != "llava" else "moondream"

WORKERS = int(os.environ.get("CLASSIFY_WORKERS", "4"))  # Parallel workers (Xeon has 20 cores)
SAVE_EVERY = 25             # Save progress every N images
PAUSE_BETWEEN = 0.1         # Minimal pause (was 1.0s — thermal OK on Xeon)
CONFIDENCE_THRESHOLD = 0.6  # Below this = ambiguous, goes to Layer 4 (Grok)
IMAGE_MAX_SIZE = int(os.environ.get("IMAGE_MAX_SIZE", "512"))  # Was 768 — smaller = faster

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


def prepare_image(filepath, max_size=None):
    """Resize for Ollama (smaller = faster on CPU)."""
    if max_size is None:
        max_size = IMAGE_MAX_SIZE
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

    for model in [OLLAMA_MODEL, FALLBACK_MODEL] if FALLBACK_MODEL != OLLAMA_MODEL else [OLLAMA_MODEL]:
        payload = {
            "model": model,
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
                "classified_by": f"ollama-{model}",
                "error": None
            }
        except Exception as e:
            last_error = str(e)
            continue

    return {
        "business": "general",
        "category": "misc",
        "description": f"Ollama error: {last_error[:100] if 'last_error' in locals() else 'unknown'}",
        "quality": "low",
        "social_ready": False,
        "confidence": 0.0,
        "classified_by": f"ollama-{OLLAMA_MODEL}",
        "error": last_error[:200] if 'last_error' in locals() else "unknown",
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
    print(f"Model:              {OLLAMA_MODEL}")
    print(f"Workers:            {WORKERS}")
    print(f"Image max size:     {IMAGE_MAX_SIZE}px")
    est_per_img = 10 if OLLAMA_MODEL == "moondream" else 30  # rough estimate
    est_hours = len(todo) * est_per_img / WORKERS / 3600
    print(f"Estimated time:     {est_hours:.1f} hours ({est_hours/24:.1f} days)")
    print(f"{'='*60}")
    print(f"Starting... (safe to Ctrl+C and resume later)\n")

    stats = progress.get("stats", {
        "processed": len(already_done),
        "empire-workroom": 0, "woodcraft": 0, "general": 0,
        "personal": 0, "ambiguous": 0, "errors": 0
    })

    def _process_image(img):
        """Classify one image — called from thread pool."""
        filepath = img["path"]
        if not os.path.exists(filepath):
            return img, None, 0

        start = time.time()
        result = classify_one(filepath)
        elapsed = time.time() - start
        return img, result, elapsed

    processed_count = 0
    batch_start = time.time()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        # Submit work in chunks to allow periodic saves
        chunk_size = max(SAVE_EVERY, WORKERS * 2)
        for chunk_start in range(0, len(todo), chunk_size):
            chunk = todo[chunk_start:chunk_start + chunk_size]
            futures = {executor.submit(_process_image, img): img for img in chunk}

            for future in as_completed(futures):
                img, result, elapsed = future.result()

                if result is None:
                    already_done.add(img["path"])
                    continue

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
                        shutil.copy2(img["path"], dest)
                        img["classified_path"] = dest
                    except (OSError, IOError):
                        pass

                if result.get("error"):
                    stats["errors"] = stats.get("errors", 0) + 1

                already_done.add(img["path"])
                stats["processed"] = len(already_done)
                processed_count += 1

                # Progress output
                done = len(already_done)
                total = len(needs_ai)
                remaining = total - done
                avg_elapsed = (time.time() - batch_start) / max(processed_count, 1)
                eta_hours = remaining * avg_elapsed / WORKERS / 3600
                print(f"[{done}/{total}] {elapsed:.1f}s | {img['filename'][:30]:30s} | "
                      f"{result['business']:16s} | conf={result['confidence']:.2f} | "
                      f"ETA: {eta_hours:.1f}h")

                time.sleep(PAUSE_BETWEEN)

            # Save progress after each chunk
            save_progress(already_done, stats)
            with open(PRESORTED_FILE, "w") as f:
                json.dump(data, f)
            print(f"  >> Progress saved ({len(already_done)} done)")

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
