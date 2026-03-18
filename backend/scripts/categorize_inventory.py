#!/usr/bin/env python3
"""
One-time migration: auto-categorize all Empire Workroom inventory items.

Usage:
    cd ~/empire-repo/backend
    python3 scripts/categorize_inventory.py

This script:
1. Adds a 'subcategory' column if missing
2. Removes the old CHECK constraint on 'category' (old values: fabric, hardware, etc.)
3. Applies workroom-specific keyword rules to assign proper categories
4. Prints a summary of changes
"""

import sqlite3
import os
import sys
from pathlib import Path

# Resolve DB path (same as backend/app/db/database.py)
DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path(__file__).resolve().parent.parent / "data" / "empire.db")
)

# ── Category rules (same as inventory router) ─────────────────────

CATEGORY_RULES = [
    (["roman shade", "roman blind"],                          "Roman Shades", None),
    (["cornice", "pelmet", "lambrequin"],                     "Cornices & Valances", None),
    (["valance", "swag", "jabots", "cascade"],                "Cornices & Valances", None),
    (["drape", "curtain", "panel", "rod pocket", "pinch pleat",
      "grommet", "tab top", "ripple fold", "ripplefold",
      "sheers", "sheer", "goblet", "shower curtain",
      "stationary panel"],                                    "Drapery", None),
    (["pillow", "cushion", "bolster", "throw", "pouffe"],     "Pillows & Cushions", None),
    (["duvet", "comforter", "coverlet", "bed sheet",
      "bed skirt", "sham", "bedspread", "bedding",
      "crib sheet", "foot"],                                  "Bedding", None),
    (["shade", "roller shade", "flat shade", "blind",
      "wood shade"],                                          "Roman Shades", None),
    (["upholster", "sofa", "chair", "bench", "ottoman",
      "headboard", "arm cover", "slipcover", "slip cover",
      "reupholster", "booth", "seat cover", "carpeting",
      "lamp", "down envelope", "covers", "wall panel",
      "wall upholstery"],                                     "Upholstery", None),
    (["fabric", "lining", "linen", "silk", "velvet",
      "cotton", "material", "blackout", "interlining",
      "sateen", "batiste", "voile", "flannel", "bump",
      "english bump", "dupioni", "raffia"],                   "Fabric & Materials", None),
    (["rod", "bracket", "finial", "ring", "track",
      "motor", "clip", "hook", "mount", "baton",
      "clutch", "traverse", "elbow", "lutron",
      "somfy", "motorized", "ripplefold hardware"],           "Hardware", None),
    (["cord", "fringe", "tape", "trim", "tassel",
      "welt", "gimp", "braid", "insert", "accessori"],       "Trim & Notions", None),
    (["install", "delivery", "pickup", "pick up",
      "removal", "takedown"],                                 "Installation", None),
    (["alter", "repair", "hem", "shorten", "resize",
      "fix", "modification"],                                 "Alterations & Repairs", None),
    (["foam", "padding"],                                     "Foam & Padding", None),
    (["table cloth"],                                         "Bedding", "Table Linens"),
    (["furniture", "table", "built in", "wall unit",
      "woodwork", "custom furniture"],                        "Custom Furniture", None),
    (["consult", "design fee", "staging", "draftsperson",
      "interior designer", "interior paint", "paint",
      "art work", "measurement", "miscelaneous",
      "merchandise"],                                         "Other Services", None),
    (["otww", "wholesale"],                                   "OTWW Wholesale", None),
]


def categorize_item(name, sku, notes):
    """Return (category, subcategory) using keyword matching."""
    search_text = " ".join([
        (name or ""),
        (sku or ""),
        (notes or ""),
    ]).lower()

    for keywords, category, subcategory in CATEGORY_RULES:
        for kw in keywords:
            if kw in search_text:
                return category, subcategory

    return "Other Services", None


def main():
    print(f"Database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Step 1: Check columns
    cols = [r[1] for r in conn.execute("PRAGMA table_info(inventory_items)").fetchall()]
    print(f"Existing columns: {cols}")

    # Step 2: Add subcategory column if missing
    if "subcategory" not in cols:
        print("Adding 'subcategory' column...")
        conn.execute("ALTER TABLE inventory_items ADD COLUMN subcategory TEXT")
        conn.commit()

    # Step 3: Remove CHECK constraint on category (requires table recreation)
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='inventory_items'"
    ).fetchone()[0]

    if "CHECK" in schema and "category IN" in schema:
        print("Removing old CHECK constraint on category...")
        conn.execute("""CREATE TABLE inventory_items_new (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category TEXT NOT NULL,
            subcategory TEXT,
            quantity REAL DEFAULT 0,
            unit TEXT DEFAULT 'yards',
            min_stock REAL DEFAULT 0,
            cost_per_unit REAL DEFAULT 0,
            sell_price REAL DEFAULT 0,
            vendor TEXT,
            location TEXT,
            notes TEXT,
            business TEXT DEFAULT 'workroom' CHECK (business IN ('workroom', 'craftforge')),
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )""")
        conn.execute("""INSERT INTO inventory_items_new
            (id, name, sku, category, quantity, unit, min_stock,
             cost_per_unit, sell_price, vendor, location, notes, business,
             created_at, updated_at)
            SELECT id, name, sku, category, quantity, unit, min_stock,
             cost_per_unit, sell_price, vendor, location, notes, business,
             created_at, updated_at
            FROM inventory_items""")
        conn.execute("DROP TABLE inventory_items")
        conn.execute("ALTER TABLE inventory_items_new RENAME TO inventory_items")
        conn.commit()
        print("CHECK constraint removed.")

    # Step 4: Read all items
    items = conn.execute(
        "SELECT id, name, sku, category, notes FROM inventory_items"
    ).fetchall()
    print(f"\nTotal items: {len(items)}")

    # Step 5: Categorize and update
    old_cats = {}
    new_cats = {}
    changes = []

    for item in items:
        old_cat = item["category"]
        old_cats[old_cat] = old_cats.get(old_cat, 0) + 1

        new_cat, subcat = categorize_item(item["name"], item["sku"], item["notes"])
        new_cats[new_cat] = new_cats.get(new_cat, 0) + 1

        conn.execute(
            "UPDATE inventory_items SET category = ?, subcategory = ?, updated_at = datetime('now') WHERE id = ?",
            (new_cat, subcat, item["id"])
        )
        if old_cat != new_cat:
            changes.append((item["name"], old_cat, new_cat, subcat))

    conn.commit()
    conn.close()

    # Step 6: Print summary
    print("\n" + "=" * 60)
    print("BEFORE (old categories):")
    for cat, cnt in sorted(old_cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:20s} : {cnt}")

    print("\nAFTER (new categories):")
    for cat, cnt in sorted(new_cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:20s} : {cnt}")

    print(f"\nItems re-categorized: {len(changes)}")
    if changes:
        print("\nSample changes (up to 30):")
        for name, old, new, sub in changes[:30]:
            sub_str = f" > {sub}" if sub else ""
            print(f"  {name[:40]:40s}  {old:10s} -> {new}{sub_str}")

    print("\nDone.")


if __name__ == "__main__":
    main()
