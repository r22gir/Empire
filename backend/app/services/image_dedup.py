#!/usr/bin/env python3
"""
Layer 1b: Dedup and filter the master inventory.
Reads /data/images/inventory.json, outputs /data/images/filtered_inventory.json.
Also outputs /data/images/dedup_report.json with stats.
"""
import json
import os
from collections import defaultdict

INVENTORY_FILE = "/data/images/inventory.json"
FILTERED_FILE = "/data/images/filtered_inventory.json"
REPORT_FILE = "/data/images/dedup_report.json"

# ============================================================
# JUNK FILTERS
# ============================================================

# Minimum dimensions (pixels) - below this is a thumbnail/icon
MIN_WIDTH = 200
MIN_HEIGHT = 200

# Minimum file size (bytes) - below this is corrupt or icon
MIN_FILE_SIZE = 15_000  # 15KB

# Maximum file size (bytes) - above this might be a raw/scan (keep but flag)
MAX_FILE_SIZE = 50_000_000  # 50MB

# Folder names that are almost certainly junk/personal
JUNK_FOLDERS = {
    ".thumbnails", "thumbnails", "thumb", "thumbs",
    ".cache", "cache", "temp", "tmp",
    "stickers", "sent", ".sent",
    "emoji", "emoticons", "avatars",
    ".trash", "trash", "recycle",
}

# Folder names that are almost certainly personal (not business)
PERSONAL_FOLDERS = {
    "whatsapp images", "whatsapp video", "whatsapp",
    "telegram", "signal", "messenger",
    "snapchat", "instagram",  # personal social, not business
    "screenshots", "screen recordings",
    "memes", "funny", "gifs",
    "selfies", "family", "vacation", "holiday", "trip",
    "facebook", "download", "downloads",
}

# Filename patterns that are junk
JUNK_FILENAME_PATTERNS = [
    "thumb_", "thumbnail_", "icon_",
    ".nomedia", "albumart", "folder.jpg",
    "cover.jpg", "poster.jpg",
]


def load_inventory():
    with open(INVENTORY_FILE, "r") as f:
        return json.load(f)


def run_dedup_and_filter():
    data = load_inventory()
    images = data["images"]
    total_start = len(images)

    removed = {
        "duplicates": 0,
        "too_small_dimensions": 0,
        "too_small_filesize": 0,
        "corrupt_no_dimensions": 0,
        "junk_folder": 0,
        "junk_filename": 0,
    }
    tagged = {
        "personal_folder": 0,
    }

    # PASS 1: Dedup by hash (keep the one on the largest/most-accessible drive)
    hash_groups = defaultdict(list)
    for img in images:
        if img["hash"]:
            hash_groups[img["hash"]].append(img)

    # Drive priority: /data > /home > BACKUP1 > BACK UP NW
    drive_priority = {
        "/data/images": 0,
        "/home/rg": 1,
        "/media/rg/BACKUP1": 2,
        "/media/rg/BACK UP NW": 3,
    }

    def drive_rank(img):
        for prefix, rank in drive_priority.items():
            if img["path"].startswith(prefix):
                return rank
        return 99

    unique_images = []
    for fhash, group in hash_groups.items():
        if len(group) == 1:
            unique_images.append(group[0])
        else:
            # Keep the best copy (highest drive priority, then largest file)
            group.sort(key=lambda x: (drive_rank(x), -x["size"]))
            unique_images.append(group[0])
            removed["duplicates"] += len(group) - 1

    # Add images with no hash (couldn't read)
    no_hash = [img for img in images if not img["hash"]]
    unique_images.extend(no_hash)

    # PASS 2: Filter junk
    filtered = []
    for img in unique_images:
        fname_lower = img["filename"].lower()
        folder_lower = img.get("folder_path", "").lower()
        folder_parts_lower = [p.lower() for p in img.get("folder_parts", [])]

        # Check filename junk patterns
        if any(pat in fname_lower for pat in JUNK_FILENAME_PATTERNS):
            removed["junk_filename"] += 1
            continue

        # Check junk folders
        if any(part in JUNK_FOLDERS for part in folder_parts_lower):
            removed["junk_folder"] += 1
            continue

        # Check file size
        if img["size"] < MIN_FILE_SIZE:
            removed["too_small_filesize"] += 1
            continue

        # Check dimensions (if we have them)
        if img["width"] > 0 and img["height"] > 0:
            if img["width"] < MIN_WIDTH and img["height"] < MIN_HEIGHT:
                removed["too_small_dimensions"] += 1
                continue
        elif img["width"] == 0 and img["height"] == 0 and img["size"] < 50000:
            # No dimensions AND small file = probably corrupt
            removed["corrupt_no_dimensions"] += 1
            continue

        # Tag personal folder images (don't remove, just tag)
        if any(part in PERSONAL_FOLDERS for part in folder_parts_lower):
            img["pre_tag"] = "personal"
            tagged["personal_folder"] += 1

        filtered.append(img)

    # Save filtered inventory
    output = {
        "filtered_at": data.get("scanned_at"),
        "total_before": total_start,
        "total_after": len(filtered),
        "removed": removed,
        "tagged": tagged,
        "total_removed": sum(removed.values()),
        "reduction_pct": round((1 - len(filtered) / total_start) * 100, 1) if total_start > 0 else 0,
        "images": filtered
    }
    with open(FILTERED_FILE, "w") as f:
        json.dump(output, f)

    # Save report
    report = {k: v for k, v in output.items() if k != "images"}
    report["unique_hashes"] = len(hash_groups)
    report["duplicate_groups"] = sum(1 for g in hash_groups.values() if len(g) > 1)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print(f"DEDUP & FILTER REPORT")
    print(f"{'='*60}")
    print(f"Started with:          {total_start:,} images")
    print(f"Duplicates removed:    {removed['duplicates']:,}")
    print(f"Junk folders removed:  {removed['junk_folder']:,}")
    print(f"Junk filenames:        {removed['junk_filename']:,}")
    print(f"Too small (filesize):  {removed['too_small_filesize']:,}")
    print(f"Too small (dims):      {removed['too_small_dimensions']:,}")
    print(f"Corrupt (no dims):     {removed['corrupt_no_dimensions']:,}")
    print(f"Total removed:         {sum(removed.values()):,}")
    print(f"Pre-tagged personal:   {tagged['personal_folder']:,}")
    print(f"{'='*60}")
    print(f"REMAINING:             {len(filtered):,} images ({output['reduction_pct']}% reduction)")
    print(f"Saved to {FILTERED_FILE}")

    return output


if __name__ == "__main__":
    run_dedup_and_filter()
