#!/usr/bin/env python3
"""
Layer 2: Pre-classify images by folder path.
Reads /data/images/filtered_inventory.json, adds pre_tag and pre_category fields.
Outputs /data/images/presorted_inventory.json.
"""
import json
import os
import re
import shutil

FILTERED_FILE = "/data/images/filtered_inventory.json"
PRESORTED_FILE = "/data/images/presorted_inventory.json"
CLASSIFIED_DIR = "/data/images/classified"

# ============================================================
# FOLDER KEYWORD MAPPINGS
# ============================================================
# Maps folder keywords to (business, category) tuples
# Checked in order - first match wins

BUSINESS_KEYWORDS = {
    # Empire Workroom (drapery/upholstery)
    "empire": ("empire-workroom", None),
    "workroom": ("empire-workroom", None),
    "drapery": ("empire-workroom", "fabrics-materials"),
    "drapes": ("empire-workroom", "fabrics-materials"),
    "curtain": ("empire-workroom", "fabrics-materials"),
    "upholster": ("empire-workroom", None),
    "fabric": ("empire-workroom", "fabrics-materials"),
    "sewing": ("empire-workroom", "in-progress"),
    "blinds": ("empire-workroom", "finished-installs"),
    "cushion": ("empire-workroom", None),
    "slipcover": ("empire-workroom", None),

    # WoodCraft (woodworking)
    "woodcraft": ("woodcraft", None),
    "woodwork": ("woodcraft", None),
    "carpentry": ("woodcraft", None),
    "cabinet": ("woodcraft", "finished-pieces"),
    "furniture": ("woodcraft", "finished-pieces"),
    "lumber": ("woodcraft", "raw-materials"),
    "woodshop": ("woodcraft", "workshop"),
    "sawdust": ("woodcraft", "workshop"),

    # General business
    "storefront": ("general", "storefront"),
    "shop front": ("general", "storefront"),
    "showroom": ("general", "storefront"),
    "branding": ("general", "branding"),
    "logo": ("general", "branding"),
    "event": ("general", "events"),
    "trade show": ("general", "events"),

    # Work/business (generic - needs AI for specific business)
    "work photo": ("needs-ai", "business"),
    "job site": ("needs-ai", "business"),
    "project": ("needs-ai", "business"),
    "install": ("needs-ai", "business"),
    "client": ("needs-ai", "business"),
    "customer": ("needs-ai", "business"),
    "before": ("needs-ai", "before-after"),
    "after": ("needs-ai", "before-after"),
}

PERSONAL_KEYWORDS = {
    "whatsapp", "telegram", "signal", "messenger", "snapchat",
    "selfie", "family", "vacation", "holiday", "birthday", "wedding",
    "party", "christmas", "thanksgiving", "easter",
    "pet", "dog", "cat", "food", "recipe", "cooking",
    "gaming", "meme", "funny", "tiktok",
    "download", "screenshot", "screen recording",
}

CATEGORY_KEYWORDS = {
    "before": "before-after",
    "after": "before-after",
    "install": "finished-installs",
    "finish": "finished-installs",
    "complete": "finished-installs",
    "progress": "in-progress",
    "wip": "in-progress",
    "workshop": "workshop",
    "shop": "workshop",
    "team": "team",
    "staff": "team",
    "crew": "team",
    "material": "fabrics-materials",
    "sample": "fabrics-materials",
    "swatch": "fabrics-materials",
}


def presort():
    with open(FILTERED_FILE, "r") as f:
        data = json.load(f)

    images = data["images"]
    stats = {
        "empire-workroom": 0, "woodcraft": 0, "general": 0,
        "personal": 0, "needs-ai": 0, "unknown": 0
    }

    for img in images:
        # Already tagged as personal by dedup layer
        if img.get("pre_tag") == "personal":
            stats["personal"] += 1
            continue

        folder_str = " ".join(img.get("folder_parts", [])).lower()
        fname_lower = img["filename"].lower()
        search_str = folder_str + " " + fname_lower

        matched = False

        # Check business keywords
        for keyword, (business, category) in BUSINESS_KEYWORDS.items():
            if keyword in search_str:
                img["pre_tag"] = business
                if category:
                    img["pre_category"] = category
                stats[business] = stats.get(business, 0) + 1
                matched = True
                break

        if not matched:
            # Check personal keywords
            for keyword in PERSONAL_KEYWORDS:
                if keyword in search_str:
                    img["pre_tag"] = "personal"
                    stats["personal"] += 1
                    matched = True
                    break

        if not matched:
            # Check DCIM (camera photos - could be work or personal, needs AI)
            if "dcim" in search_str or "camera" in search_str:
                img["pre_tag"] = "needs-ai"
                img["pre_note"] = "camera-roll"
                stats["needs-ai"] += 1
                matched = True

        if not matched:
            img["pre_tag"] = "unknown"
            stats["unknown"] += 1

        # Try to assign category if we have a business but no category
        if img.get("pre_tag") not in ("personal", "unknown", "needs-ai", None) and not img.get("pre_category"):
            for keyword, category in CATEGORY_KEYWORDS.items():
                if keyword in search_str:
                    img["pre_category"] = category
                    break

    # Copy pre-sorted images to classified folders
    copied = 0
    for img in images:
        tag = img.get("pre_tag", "unknown")
        if tag in ("unknown", "needs-ai"):
            continue  # These go to Layer 3 (Ollama)
        if tag == "personal":
            dest_dir = os.path.join(CLASSIFIED_DIR, "personal")
        else:
            cat = img.get("pre_category", "misc")
            dest_dir = os.path.join(CLASSIFIED_DIR, tag, cat)

        os.makedirs(dest_dir, exist_ok=True)
        src = img["path"]
        dest = os.path.join(dest_dir, img["filename"])
        if os.path.exists(src) and not os.path.exists(dest):
            try:
                shutil.copy2(src, dest)
                img["classified_path"] = dest
                img["classified_by"] = "folder-presort"
                copied += 1
            except (OSError, IOError):
                pass

    # Save
    output = {
        "presorted_at": data.get("filtered_at"),
        "total_images": len(images),
        "stats": stats,
        "copied_to_folders": copied,
        "needs_ai_classification": stats["needs-ai"] + stats["unknown"],
        "images": images
    }
    with open(PRESORTED_FILE, "w") as f:
        json.dump(output, f)

    print(f"\n{'='*60}")
    print(f"FOLDER PRE-SORT REPORT")
    print(f"{'='*60}")
    for key, count in stats.items():
        pct = round(count / len(images) * 100, 1) if images else 0
        print(f"  {key:20s}: {count:6,} ({pct}%)")
    print(f"{'='*60}")
    print(f"  Copied to folders:   {copied:,}")
    print(f"  Need AI (Layer 3):   {stats['needs-ai'] + stats['unknown']:,}")
    print(f"Saved to {PRESORTED_FILE}")

    return output


if __name__ == "__main__":
    presort()
