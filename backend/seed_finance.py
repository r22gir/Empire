"""
Seed script for Empire finance system.
Run: cd /home/rg/empire-repo/backend && python3 seed_finance.py

1. Initializes database tables
2. Imports customers from quote JSON files
3. Seeds sample expenses
4. Seeds sample inventory items
"""
import json
import os
import sys

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(__file__))

from app.db.init_db import init_database
from app.db.database import get_db, dict_row, dict_rows
from pathlib import Path

QUOTES_DIR = Path(__file__).resolve().parent / "data" / "quotes"


def import_customers_from_quotes():
    """Scan quote JSON files, extract unique customers, insert into DB."""
    customer_map = {}

    for quote_file in QUOTES_DIR.glob("*.json"):
        if quote_file.name.startswith("_"):
            continue
        try:
            with open(quote_file) as f:
                quote = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        name = quote.get("customer_name", "").strip()
        if not name or name.lower() in ("", "customer", "unknown", "unnamed customer",
                                         "new customer", "new client", "default customer",
                                         "sample customer", "test client"):
            continue

        email = (quote.get("customer_email") or "").strip()
        phone = (quote.get("customer_phone") or "").strip()
        address = (quote.get("customer_address") or "").strip()

        key = (name.lower(), email.lower() if email else "")
        if key not in customer_map:
            customer_map[key] = {
                "name": name,
                "email": email or None,
                "phone": phone or None,
                "address": address or None,
                "quotes": [],
                "total_revenue": 0,
            }

        quote_total = quote.get("total", 0) or quote.get("subtotal", 0) or 0
        if quote_total == 0:
            proposal_totals = quote.get("proposal_totals", {})
            if proposal_totals:
                quote_total = proposal_totals.get("A", 0) or proposal_totals.get("B", 0) or 0

        customer_map[key]["quotes"].append(quote.get("id"))
        customer_map[key]["total_revenue"] += quote_total

        if phone and not customer_map[key]["phone"]:
            customer_map[key]["phone"] = phone
        if address and not customer_map[key]["address"]:
            customer_map[key]["address"] = address

    created = 0
    with get_db() as conn:
        for key, cust_data in customer_map.items():
            existing = None
            if cust_data["email"]:
                existing = conn.execute(
                    "SELECT id FROM customers WHERE email = ?", (cust_data["email"],)
                ).fetchone()
            if not existing:
                existing = conn.execute(
                    "SELECT id FROM customers WHERE lower(name) = ?", (cust_data["name"].lower(),)
                ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE customers SET total_revenue = ?, lifetime_quotes = ?,
                       updated_at = datetime('now') WHERE id = ?""",
                    (cust_data["total_revenue"], len(cust_data["quotes"]), existing["id"])
                )
            else:
                conn.execute(
                    """INSERT INTO customers
                       (id, name, email, phone, address, type, total_revenue, lifetime_quotes, source)
                       VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, 'residential', ?, ?, 'direct')""",
                    (
                        cust_data["name"],
                        cust_data["email"],
                        cust_data["phone"],
                        cust_data["address"],
                        cust_data["total_revenue"],
                        len(cust_data["quotes"]),
                    )
                )
                created += 1

    print(f"  Imported {created} customers from {len(customer_map)} unique entries")
    return created


def seed_expenses():
    """Add sample expenses."""
    expenses = [
        ("fabric", "Rowley Company", "Fabric order - Belgian linen and silk dupioni", 1250.00, "2026-03-01"),
        ("hardware", "Somfy", "Somfy motors (2x) for motorized shades", 570.00, "2026-03-02"),
        ("hardware", "Lutron", "Lutron Caseta smart home kit", 425.00, "2026-03-03"),
        ("rent", None, "Monthly rent - March 2026", 2800.00, "2026-03-01"),
        ("utilities", None, "Electric bill - March 2026", 185.00, "2026-03-05"),
        ("marketing", None, "Instagram ads - March campaign", 150.00, "2026-03-01"),
    ]

    with get_db() as conn:
        # Check if we already seeded
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        if count > 0:
            print(f"  Expenses already seeded ({count} rows), skipping")
            return

        for cat, vendor, desc, amount, exp_date in expenses:
            conn.execute(
                """INSERT INTO expenses (id, category, vendor, description, amount, expense_date)
                   VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?)""",
                (cat, vendor, desc, amount, exp_date)
            )

    print(f"  Seeded {len(expenses)} sample expenses")


def seed_inventory():
    """Add sample inventory items."""
    items = [
        ("Belgian Linen (White)", "FAB-BL-WHT", "fabric", 45, "yards", 10, 28.00, 45.00, "Rowley Company", "workroom"),
        ("Silk Dupioni (Gold)", "FAB-SD-GLD", "fabric", 22, "yards", 5, 45.00, 72.00, "Rowley Company", "workroom"),
        ("Blackout Lining", "LIN-BLK-001", "lining", 60, "yards", 20, 8.00, 14.00, "Rowley Company", "workroom"),
        ("Somfy Motor RTS", "MOT-SMF-RTS", "motors", 8, "units", 3, 285.00, 425.00, "Somfy", "workroom"),
        ("Lutron Caseta", "HW-LUT-CAS", "hardware", 4, "units", 2, 425.00, 650.00, "Lutron", "workroom"),
        ("Kirsch Traverse Rod", "HW-KIR-TRV", "hardware", 12, "units", 5, 45.00, 75.00, "Kirsch", "workroom"),
        ("Decorative Rings (Brass)", "HW-RING-BRS", "hardware", 200, "units", 50, 3.50, 6.00, "Various", "workroom"),
    ]

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM inventory_items").fetchone()[0]
        if count > 0:
            print(f"  Inventory already seeded ({count} rows), skipping")
            return

        for name, sku, cat, qty, unit, min_s, cost, sell, vendor, biz in items:
            conn.execute(
                """INSERT INTO inventory_items
                   (id, name, sku, category, quantity, unit, min_stock, cost_per_unit, sell_price, vendor, business)
                   VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, sku, cat, qty, unit, min_s, cost, sell, vendor, biz)
            )

    print(f"  Seeded {len(items)} inventory items")


def seed_vendors():
    """Add sample vendors."""
    vendors = [
        ("Rowley Company", "Customer Service", "orders@rowleycompany.com", "800-343-4542", None, 5),
        ("Somfy", "Sales Team", "sales@somfysystems.com", "800-229-7234", None, 14),
        ("Lutron", "Pro Support", "pro@lutron.com", "888-588-7661", None, 7),
        ("Kirsch", None, None, "800-817-6344", None, 10),
    ]

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
        if count > 0:
            print(f"  Vendors already seeded ({count} rows), skipping")
            return

        for name, contact, email, phone, addr, lead in vendors:
            conn.execute(
                """INSERT INTO vendors
                   (id, name, contact_name, email, phone, address, lead_time_days)
                   VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?)""",
                (name, contact, email, phone, addr, lead)
            )

    print(f"  Seeded {len(vendors)} vendors")


if __name__ == "__main__":
    print("Empire Finance System - Database Setup & Seed")
    print("=" * 50)

    # Step 1: Init tables
    print("\n1. Initializing database tables...")
    init_database()

    # Step 2: Import customers from quotes
    print("\n2. Importing customers from quote files...")
    import_customers_from_quotes()

    # Step 3: Seed expenses
    print("\n3. Seeding sample expenses...")
    seed_expenses()

    # Step 4: Seed inventory
    print("\n4. Seeding sample inventory items...")
    seed_inventory()

    # Step 5: Seed vendors
    print("\n5. Seeding sample vendors...")
    seed_vendors()

    # Summary
    print("\n" + "=" * 50)
    with get_db() as conn:
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        expenses = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        items = conn.execute("SELECT COUNT(*) FROM inventory_items").fetchone()[0]
        vendors = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]

    print(f"Database summary:")
    print(f"  Customers:  {customers}")
    print(f"  Invoices:   {invoices}")
    print(f"  Expenses:   {expenses}")
    print(f"  Inventory:  {items}")
    print(f"  Vendors:    {vendors}")
    print("\nDone!")
