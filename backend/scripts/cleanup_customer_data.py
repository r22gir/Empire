#!/usr/bin/env python3
"""
cleanup_customer_data.py
Cleans up QuickBooks-imported customer data in the empire.db SQLite database.

Fixes:
  1. Names/companies with escaped quotes: \"Name\" → Name
  2. Normalize phone formats to (XXX) XXX-XXXX
  3. Auto-fill customer type based on company name keywords
  4. Remove garbage customer records (single digit, empty names)
"""

import sqlite3
import re
import os
import shutil
from datetime import datetime

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")
BACKUP_DIR = os.path.expanduser("~/empire-repo/backend/data/backups")

# --- Type classification rules ---
TYPE_RULES = [
    (["design", "interior", "decor"], "designer"),
    (["build", "construct", "contract"], "contractor"),
    (["hotel", "office", "corp", "llc", "inc"], "commercial"),
]


def classify_type(company: str | None, current_type: str) -> str:
    """Determine customer type from company name keywords."""
    if not company:
        return current_type
    lower = company.lower()
    for keywords, ctype in TYPE_RULES:
        for kw in keywords:
            if kw in lower:
                return ctype
    return current_type


def clean_escaped_quotes(value: str | None) -> str | None:
    """Remove leading/trailing escaped quotes from a string."""
    if value is None:
        return None
    # Strip outer escaped quotes: "\"Foo\"" → Foo
    cleaned = value.strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 1:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def normalize_phone(phone: str | None) -> str | None:
    """Normalize phone to (XXX) XXX-XXXX format where possible.
    Preserves extensions and non-standard numbers."""
    if not phone:
        return phone

    original = phone.strip()
    if not original:
        return original

    # Skip test/placeholder numbers
    if re.search(r'[A-Za-z]', original):
        return original

    # Extract extension if present
    ext = ""
    ext_match = re.search(r'\s*(?:x|ext\.?)\s*(\d+)', original, re.IGNORECASE)
    if ext_match:
        ext = f" x {ext_match.group(1)}"
        original = original[:ext_match.start()]

    # Extract just digits
    digits = re.sub(r'\D', '', original)

    # Handle 10-digit US numbers
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}{ext}"
    # Handle 11-digit with leading 1
    if len(digits) == 11 and digits[0] == '1':
        d = digits[1:]
        return f"({d[:3]}) {d[3:6]}-{d[6:]}{ext}"

    # Can't normalize — return cleaned original
    return phone.strip()


def is_garbage_name(name: str | None) -> bool:
    """Check if a customer name is garbage (single digit, empty, etc.)."""
    if not name:
        return True
    stripped = name.strip()
    if not stripped:
        return True
    # Single character that's a digit
    if len(stripped) <= 2 and stripped.isdigit():
        return True
    return False


def main():
    # Back up database first
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = os.path.join(BACKUP_DIR, f"empire_pre-cleanup_{timestamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM customers")
    total_before = cur.fetchone()[0]
    print(f"Total customers before cleanup: {total_before}\n")

    stats = {
        "names_fixed": 0,
        "companies_fixed": 0,
        "phones_normalized": 0,
        "types_updated": 0,
        "garbage_deleted": 0,
    }

    # --- Pass 1: Delete garbage names ---
    print("=" * 60)
    print("PASS 1: Removing garbage customer records")
    print("=" * 60)
    cur.execute("SELECT id, name FROM customers")
    garbage_ids = []
    for row in cur.fetchall():
        if is_garbage_name(row["name"]):
            garbage_ids.append(row["id"])
            print(f"  DELETE  id={row['id']}  name={repr(row['name'])}")

    if garbage_ids:
        placeholders = ",".join("?" * len(garbage_ids))
        cur.execute(f"DELETE FROM customers WHERE id IN ({placeholders})", garbage_ids)
        stats["garbage_deleted"] = len(garbage_ids)
    else:
        print("  (none found)")
    print()

    # --- Pass 2: Fix escaped quotes in names and companies ---
    print("=" * 60)
    print("PASS 2: Fixing escaped quotes in names and companies")
    print("=" * 60)
    cur.execute("SELECT id, name, company FROM customers")
    for row in cur.fetchall():
        rid, name, company = row["id"], row["name"], row["company"]
        new_name = clean_escaped_quotes(name)
        new_company = clean_escaped_quotes(company)

        if new_name != name:
            print(f"  NAME   {repr(name)} → {repr(new_name)}")
            cur.execute("UPDATE customers SET name = ?, updated_at = datetime('now') WHERE id = ?",
                        (new_name, rid))
            stats["names_fixed"] += 1

        if new_company != company:
            print(f"  COMPANY {repr(company)} → {repr(new_company)}")
            cur.execute("UPDATE customers SET company = ?, updated_at = datetime('now') WHERE id = ?",
                        (new_company, rid))
            stats["companies_fixed"] += 1
    if stats["names_fixed"] == 0 and stats["companies_fixed"] == 0:
        print("  (none found)")
    print()

    # --- Pass 3: Normalize phone numbers ---
    print("=" * 60)
    print("PASS 3: Normalizing phone numbers")
    print("=" * 60)
    cur.execute("SELECT id, name, phone FROM customers WHERE phone IS NOT NULL AND phone != ''")
    for row in cur.fetchall():
        rid, name, phone = row["id"], row["name"], row["phone"]
        new_phone = normalize_phone(phone)
        if new_phone != phone:
            print(f"  {name}: {repr(phone)} → {repr(new_phone)}")
            cur.execute("UPDATE customers SET phone = ?, updated_at = datetime('now') WHERE id = ?",
                        (new_phone, rid))
            stats["phones_normalized"] += 1
    if stats["phones_normalized"] == 0:
        print("  (none found)")
    print()

    # --- Pass 4: Auto-classify customer type from company name ---
    print("=" * 60)
    print("PASS 4: Classifying customer types from company names")
    print("=" * 60)
    cur.execute("SELECT id, name, company, type FROM customers")
    for row in cur.fetchall():
        rid, name, company, ctype = row["id"], row["name"], row["company"], row["type"]
        new_type = classify_type(company, ctype)
        # Also check the customer name itself for clues
        if new_type == ctype:
            new_type = classify_type(name, ctype)
        if new_type != ctype:
            print(f"  {name} ({company or 'no company'}): {ctype} → {new_type}")
            cur.execute("UPDATE customers SET type = ?, updated_at = datetime('now') WHERE id = ?",
                        (new_type, rid))
            stats["types_updated"] += 1
    if stats["types_updated"] == 0:
        print("  (none found)")
    print()

    # --- Commit ---
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM customers")
    total_after = cur.fetchone()[0]

    # --- Summary ---
    print("=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"  Customers before:     {total_before}")
    print(f"  Customers after:      {total_after}")
    print(f"  Garbage deleted:      {stats['garbage_deleted']}")
    print(f"  Names fixed:          {stats['names_fixed']}")
    print(f"  Companies fixed:      {stats['companies_fixed']}")
    print(f"  Phones normalized:    {stats['phones_normalized']}")
    print(f"  Types reclassified:   {stats['types_updated']}")
    print(f"\n  Backup at: {backup_path}")
    print("  Done.")

    conn.close()


if __name__ == "__main__":
    main()
