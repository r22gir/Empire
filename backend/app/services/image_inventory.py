#!/usr/bin/env python3
"""
Layer 1: Build master inventory of all images across all drives.
Generates /data/images/inventory.json with hash, size, dimensions, EXIF date, source path.
Run once, takes 30-60 min for 67K images.
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    from PIL.ExifTags import Base as ExifBase
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: Pillow not installed. Dimensions/EXIF will be skipped.")
    print("Run: pip install Pillow")

SCAN_DIRS = [
    "/media/rg/BACKUP1",        # 45,482 images
    "/media/rg/BACK UP NW",     # 21,479 images
    "/home/rg",                 # 578 images
    "/data/images",             # 139 images
]

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp",
    ".tiff", ".tif", ".gif", ".heic", ".heif"
}

OUTPUT_FILE = "/data/images/inventory.json"


def file_hash(filepath, chunk_size=8192):
    """Fast MD5 hash of file contents."""
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError):
        return None


def get_image_info(filepath):
    """Get dimensions and EXIF date if available."""
    width, height, date_taken = 0, 0, None
    if HAS_PIL:
        try:
            with Image.open(filepath) as img:
                width, height = img.size
                exif = img.getexif()
                if exif:
                    # Try DateTimeOriginal (36867), then DateTime (306)
                    date_taken = exif.get(36867) or exif.get(306)
        except Exception:
            pass
    return width, height, date_taken


def scan_all_drives():
    """Scan all configured drives and build master inventory."""
    inventory = []
    seen_count = 0
    error_count = 0

    for scan_dir in SCAN_DIRS:
        if not os.path.exists(scan_dir):
            print(f"SKIP: {scan_dir} (not found/mounted)")
            continue

        print(f"SCANNING: {scan_dir}")
        dir_count = 0

        for root, dirs, files in os.walk(scan_dir):
            # Skip system/hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in (
                '__pycache__', 'node_modules', '.git', 'Thumbs.db', '.Trash'
            )]

            for fname in files:
                ext = Path(fname).suffix.lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue

                filepath = os.path.join(root, fname)
                try:
                    stat = os.stat(filepath)
                    fsize = stat.st_size

                    # Get hash
                    fhash = file_hash(filepath)
                    if not fhash:
                        error_count += 1
                        continue

                    # Get dimensions and EXIF
                    width, height, date_taken = get_image_info(filepath)

                    # Extract folder context (parent dirs)
                    rel_path = os.path.relpath(filepath, scan_dir)
                    folder_parts = Path(rel_path).parts[:-1]  # dirs without filename

                    inventory.append({
                        "path": filepath,
                        "filename": fname,
                        "hash": fhash,
                        "size": fsize,
                        "width": width,
                        "height": height,
                        "date_taken": str(date_taken) if date_taken else None,
                        "source_drive": scan_dir,
                        "folder_path": "/".join(folder_parts),
                        "folder_parts": list(folder_parts),
                        "ext": ext,
                    })

                    dir_count += 1
                    seen_count += 1
                    if seen_count % 1000 == 0:
                        print(f"  ...scanned {seen_count} images")

                except (OSError, IOError) as e:
                    error_count += 1

        print(f"  Found {dir_count} images in {scan_dir}")

    # Save inventory
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    output = {
        "scanned_at": datetime.now().isoformat(),
        "total_images": len(inventory),
        "errors": error_count,
        "drives_scanned": [d for d in SCAN_DIRS if os.path.exists(d)],
        "images": inventory
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f)

    print(f"\nDONE: {len(inventory)} images inventoried, {error_count} errors")
    print(f"Saved to {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    scan_all_drives()
