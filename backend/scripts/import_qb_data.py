#!/usr/bin/env python3
"""
Import QuickBooks data into Empire Workroom.
Sources: IIF file (items, vendors, customers), PDF vendor/customer lists.
Imports into: customers table, inventory items table, vendors table.
Skips duplicates by name.
"""

import sqlite3
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / "empire-repo" / "backend" / "data" / "empire.db"
IIF_PATH = Path.home() / "empire-repo" / "backend" / "data" / "uploads" / "other" / "NW QB Items Vendors and Customers.IIF"

def short_id():
    return uuid.uuid4().hex[:16]

def connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

# ── Parse IIF Items ──────────────────────────────────────────────────

def parse_iif_items():
    """Parse INVITEM lines from the IIF file into structured items."""
    items = []
    headers = None

    with open(IIF_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n\r')
            parts = line.split('\t')
            if not parts:
                continue

            # Header line for INVITEM
            if parts[0] == '!INVITEM':
                headers = parts
                continue

            if parts[0] == 'INVITEM' and headers:
                row = {}
                for i, h in enumerate(headers):
                    row[h] = parts[i] if i < len(parts) else ''

                name_raw = row.get('NAME', '').strip()
                if not name_raw:
                    continue

                # Skip parent-only categories (ones that are just headers with no price and no description)
                desc = row.get('DESC', '').strip().replace('\\n', ' ').replace('\n', ' ')
                price_raw = (row.get('PRICE', '0') or '0').strip().rstrip('%')
                cost_raw = (row.get('COST', '0') or '0').strip().rstrip('%')
                try:
                    price = float(price_raw)
                except ValueError:
                    price = 0.0
                try:
                    cost = float(cost_raw)
                except ValueError:
                    cost = 0.0
                vendor = row.get('PREFVEND', '').strip().strip('"')
                item_type = row.get('INVITEMTYPE', 'SERV')
                hidden = row.get('HIDDEN', 'N') == 'Y'
                del_count = int(row.get('DELCOUNT', '0') or '0')

                if hidden or del_count > 0:
                    continue

                # Parse hierarchy: "01. DRAPERY:01. Drapes" → category="Drapery", name="Drapes Standard"
                if ':' in name_raw:
                    parts_name = name_raw.split(':')
                    category_raw = parts_name[0].strip()
                    item_name = parts_name[-1].strip()
                else:
                    category_raw = name_raw
                    item_name = name_raw

                # Clean category: remove number prefix "01. DRAPERY" → "Drapery"
                category = re.sub(r'^\d+\.\s*', '', category_raw).title()
                # Clean item name: remove number prefix
                item_name = re.sub(r'^\d+\.\s*', '', item_name).strip()

                # Map categories — consolidate QB fragments into clean groups
                cat_map = {
                    'Drapery': 'Drapery',
                    'Shades': 'Shades',
                    'Bedding And Others': 'Bedding',
                    'Bedding': 'Bedding',
                    'Valances': 'Valances',
                    'Pillows And Cushions': 'Pillows & Cushions',
                    'Pillows': 'Pillows & Cushions',
                    'Upholstery': 'Upholstery',
                    'Covers': 'Upholstery',
                    'Seat Covers': 'Upholstery',
                    'Accessories': 'Accessories',
                    'Fabrics And Linings': 'Fabrics & Linings',
                    'Fabrics': 'Fabrics & Linings',
                    'Custom Furniture': 'Furniture',
                    'Furniture': 'Furniture',
                    'Furniture Items': 'Furniture',
                    'Wall Panels': 'Wall Panels',
                    'Wall Unit': 'Furniture',
                    'Drapery Hardware': 'Hardware',
                    'Hardware': 'Hardware',
                    'Hardware And Materials': 'Hardware',
                    'Miscelaneus Hardware': 'Hardware',
                    'Foam': 'Foam & Padding',
                    'Installation': 'Professional Services',
                    'Measurements': 'Professional Services',
                    'Design Fee': 'Professional Services',
                    'Consulting': 'Professional Services',
                    'Consulting Services': 'Professional Services',
                    'Interior Paint': 'Professional Services',
                    'Paint': 'Professional Services',
                    'Paint Stripping': 'Professional Services',
                    'Staging': 'Professional Services',
                    'Art Work': 'Professional Services',
                    'Woodwork': 'Professional Services',
                    'Repairs': 'Professional Services',
                    'Pick Up': 'Professional Services',
                    'Miscelaneous': 'Professional Services',
                    'Otww': 'OTWW Wholesale',
                    'Ez Rise': 'Shades',
                    'Merchandise': 'Shades',
                }
                category = cat_map.get(category, category)

                # Map to allowed DB categories: fabric, hardware, motors, lining, thread, trim, wood, tools, other
                db_cat_map = {
                    'Drapery': 'fabric',
                    'Shades': 'fabric',
                    'Bedding': 'fabric',
                    'Valances': 'fabric',
                    'Pillows & Cushions': 'fabric',
                    'Upholstery': 'fabric',
                    'Fabrics & Linings': 'fabric',
                    'Accessories': 'trim',
                    'Hardware': 'hardware',
                    'Furniture': 'wood',
                    'Wall Panels': 'wood',
                    'Foam & Padding': 'other',
                    'Professional Services': 'other',
                    'OTWW Wholesale': 'other',
                }
                db_category = db_cat_map.get(category, 'other')

                # Skip QB accounting artifacts — not real items/services
                skip_cats = {
                    'Commission', 'Credit', 'Discount', 'Markup', 'Subtotal',
                    'Total', 'Upfront Deposit', 'Out Of State', 'Md Sales Tax',
                    'Mileage', 'Drive Time', 'Delivery Fee', 'Shipping',
                    'Shipping And Handling', 'Other Charges', 'Miscelaneous Charges',
                    'Contractor',
                }
                if category in skip_cats:
                    continue

                # Use description as the display name if item_name is too generic
                display_name = item_name
                if desc and len(desc) > len(item_name) and not desc.startswith(item_name):
                    display_name = f"{item_name} — {desc[:80]}"
                elif desc and not display_name:
                    display_name = desc[:80]

                if not display_name:
                    display_name = name_raw

                # Determine unit based on description and category
                unit = 'each'
                desc_lower = (desc or '').lower()
                if 'per width' in desc_lower or 'per sq' in desc_lower:
                    unit = 'each'
                elif 'per yard' in desc_lower or 'yard' in desc_lower:
                    unit = 'yards'
                elif 'per linear foot' in desc_lower or 'per foot' in desc_lower:
                    unit = 'feet'
                elif 'per unit' in desc_lower:
                    unit = 'each'
                elif category in ('Fabrics', 'Foam'):
                    unit = 'yards'
                elif category == 'Hardware':
                    unit = 'pieces'

                items.append({
                    'name': display_name,
                    'sku': name_raw[:40].replace(' ', '-').replace(':', '-').upper()[:40],
                    'category': db_category,
                    'qb_category': category,
                    'description': desc,
                    'sell_price': price,
                    'cost_per_unit': cost,
                    'vendor': vendor,
                    'unit': unit,
                    'item_type': 'service' if item_type == 'SERV' else 'product',
                })

    return items


# ── Parse IIF Vendors ────────────────────────────────────────────────

def parse_iif_vendors():
    """Parse VEND lines from the IIF file."""
    vendors = []
    headers = None

    with open(IIF_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n\r')
            parts = line.split('\t')
            if not parts:
                continue

            if parts[0] == '!VEND':
                headers = parts
                continue

            if parts[0] == 'VEND' and headers:
                row = {}
                for i, h in enumerate(headers):
                    row[h] = parts[i] if i < len(parts) else ''

                name = row.get('NAME', '').strip()
                if not name:
                    continue

                hidden = row.get('HIDDEN', 'N') == 'Y'
                if hidden:
                    continue

                vendors.append({
                    'name': name,
                    'email': row.get('EMAIL', '').strip(),
                    'phone': row.get('PHONE1', '').strip(),
                    'address': row.get('ADDR1', '').strip(),
                    'contact': row.get('CONT1', '').strip(),
                    'account_number': row.get('ACCNUM', '').strip(),
                })

    return vendors


# ── Parse IIF Customers ──────────────────────────────────────────────

def parse_iif_customers():
    """Parse CUST lines from the IIF file (parent customers only)."""
    customers = []
    headers = None

    with open(IIF_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n\r')
            parts = line.split('\t')
            if not parts:
                continue

            if parts[0] == '!CUST':
                headers = parts
                continue

            if parts[0] == 'CUST' and headers:
                row = {}
                for i, h in enumerate(headers):
                    row[h] = parts[i] if i < len(parts) else ''

                name = row.get('NAME', '').strip()
                if not name or ':' in name:  # Skip sub-jobs
                    continue

                hidden = row.get('HIDDEN', 'N') == 'Y'
                if hidden:
                    continue

                phone = row.get('PHONE1', '').strip()
                email = row.get('EMAIL', '').strip()
                addr1 = row.get('ADDR1', '').strip()
                addr2 = row.get('ADDR2', '').strip()
                addr3 = row.get('ADDR3', '').strip()
                address = ', '.join(a for a in [addr1, addr2, addr3] if a)
                contact = row.get('CONT1', '').strip()
                company = row.get('COMPANYNAME', '').strip()
                balance = float(row.get('BALANCEDUE', '0') or '0')

                # Determine type
                cust_type = 'residential'
                name_lower = name.lower()
                if any(w in name_lower for w in ['design', 'studio', 'interiors', 'associates', 'inc', 'llc', 'company']):
                    cust_type = 'designer'
                elif any(w in name_lower for w in ['restaurant', 'bar', 'hotel', 'church', 'bible', 'theater', 'university']):
                    cust_type = 'commercial'
                elif any(w in name_lower for w in ['contractor', 'construction', 'building']):
                    cust_type = 'contractor'

                customers.append({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'address': address,
                    'company': company or (contact if contact != name else ''),
                    'type': cust_type,
                    'source': 'quickbooks',
                    'notes': f"Imported from QB. Balance: ${balance:,.2f}" if balance > 0 else "Imported from QB",
                    'balance': balance,
                })

    return customers


# ── Hardcoded vendor list from PDF (supplements IIF) ─────────────────

PDF_VENDORS = [
    {"name": "Abraham Romero"},
    {"name": "Amazon"},
    {"name": "American Foam Centers", "phone": "703-241-7400", "address": "2799-D Merrilee Dr"},
    {"name": "American Stage"},
    {"name": "Andres Alvarez", "address": "Alvarez Contractor Co"},
    {"name": "Angel's Distributing", "phone": "1-800-450-9368", "contact": "Ana", "address": "P.O. Box 609 Indian Trail NC"},
    {"name": "Benjamin Moore"},
    {"name": "BJ's Wholesale"},
    {"name": "Fashion Fabrics"},
    {"name": "Foam Factory"},
    {"name": "Greenhouse Fabrics"},
    {"name": "Harold Palacios R"},
    {"name": "Herrera Contracting Co"},
    {"name": "Home Depot"},
    {"name": "Kravet"},
    {"name": "Lowes"},
    {"name": "Rowley Company", "phone": "1-800-343-4542", "account_number": "102179", "address": "PO BOX 6010 Gastonia NC"},
    {"name": "Royal Cortina"},
    {"name": "Saldarriaga Sewing"},
    {"name": "The Shade Store"},
    {"name": "U.S. Thread", "address": "400 Smith Street"},
    {"name": "WAWAK"},
    {"name": "Webb Co"},
]


# ── Import Functions ─────────────────────────────────────────────────

def import_items(conn, items):
    """Import items into the inventory_items table."""
    existing = {r[0].lower() for r in conn.execute("SELECT name FROM inventory_items").fetchall()}
    inserted = 0
    skipped = 0

    for item in items:
        if item['name'].lower() in existing:
            skipped += 1
            continue

        try:
            conn.execute(
                """INSERT INTO inventory_items
                   (id, name, sku, category, quantity, unit, min_stock,
                    cost_per_unit, sell_price, vendor, location, notes, business, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    short_id(),
                    item['name'],
                    item['sku'],
                    item['category'],
                    0,  # quantity — services don't have stock
                    item['unit'],
                    0,  # min_stock
                    item['cost_per_unit'],
                    item['sell_price'],
                    item['vendor'],
                    '',  # location
                    f"QB: {item.get('qb_category','')}. {item.get('description', '')}".strip(),
                    'workroom',
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                )
            )
            existing.add(item['name'].lower())
            inserted += 1
        except Exception as e:
            print(f"  ERROR inserting item '{item['name']}': {e}")

    return inserted, skipped


def import_customers(conn, customers):
    """Import customers into the customers table."""
    existing = {r[0].lower() for r in conn.execute("SELECT name FROM customers").fetchall()}
    inserted = 0
    skipped = 0

    for cust in customers:
        if cust['name'].lower() in existing:
            skipped += 1
            continue

        try:
            conn.execute(
                """INSERT INTO customers
                   (id, name, email, phone, address, company, type, tags, notes, source, business, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    short_id(),
                    cust['name'],
                    cust.get('email', ''),
                    cust.get('phone', ''),
                    cust.get('address', ''),
                    cust.get('company', ''),
                    cust.get('type', 'residential'),
                    json.dumps([cust['type'], 'qb-import']),
                    cust.get('notes', ''),
                    cust.get('source', 'quickbooks'),
                    'workroom',
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                )
            )
            existing.add(cust['name'].lower())
            inserted += 1
        except Exception as e:
            print(f"  ERROR inserting customer '{cust['name']}': {e}")

    return inserted, skipped


def import_vendors(conn, vendors):
    """Import vendors into the vendors table (create if not exists)."""
    # Ensure vendors table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            contact_name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            account_number TEXT,
            lead_time_days INTEGER DEFAULT 7,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing = {r[0].lower() for r in conn.execute("SELECT name FROM vendors").fetchall()}
    inserted = 0
    skipped = 0

    for v in vendors:
        if v['name'].lower() in existing:
            skipped += 1
            continue

        try:
            conn.execute(
                """INSERT INTO vendors
                   (id, name, contact_name, email, phone, address, account_number, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    short_id(),
                    v['name'],
                    v.get('contact', ''),
                    v.get('email', ''),
                    v.get('phone', ''),
                    v.get('address', ''),
                    v.get('account_number', ''),
                    'Imported from QB',
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                )
            )
            existing.add(v['name'].lower())
            inserted += 1
        except Exception as e:
            print(f"  ERROR inserting vendor '{v['name']}': {e}")

    return inserted, skipped


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Empire Workroom — QuickBooks Data Import")
    print("=" * 60)

    conn = connect()

    # 1. Parse IIF
    print("\n📋 Parsing IIF file...")
    iif_items = parse_iif_items()
    iif_vendors = parse_iif_vendors()
    iif_customers = parse_iif_customers()
    print(f"   Found: {len(iif_items)} items, {len(iif_vendors)} vendors, {len(iif_customers)} customers")

    # 2. Merge PDF vendors with IIF vendors
    all_vendors = list(iif_vendors)
    iif_vendor_names = {v['name'].lower() for v in iif_vendors}
    for pv in PDF_VENDORS:
        if pv['name'].lower() not in iif_vendor_names:
            all_vendors.append(pv)
    print(f"   Total vendors (IIF + PDF): {len(all_vendors)}")

    # 3. Import
    print("\n📦 Importing items into inventory...")
    i_ins, i_skip = import_items(conn, iif_items)
    print(f"   ✅ Inserted: {i_ins}, Skipped (existing): {i_skip}")

    print("\n👥 Importing customers...")
    c_ins, c_skip = import_customers(conn, iif_customers)
    print(f"   ✅ Inserted: {c_ins}, Skipped (existing): {c_skip}")

    print("\n🏭 Importing vendors...")
    v_ins, v_skip = import_vendors(conn, all_vendors)
    print(f"   ✅ Inserted: {v_ins}, Skipped (existing): {v_skip}")

    conn.commit()
    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print(f"  Items:     {i_ins} new  ({i_skip} existed)")
    print(f"  Customers: {c_ins} new  ({c_skip} existed)")
    print(f"  Vendors:   {v_ins} new  ({v_skip} existed)")
    print("=" * 60)

    # Print categories breakdown
    cats = {}
    for item in iif_items:
        c = item['category']
        cats[c] = cats.get(c, 0) + 1
    print("\nItem categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == '__main__':
    main()
