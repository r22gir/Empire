"""Self-serve BusinessOps signup.

Creates (atomically, on one connection):
  - access_users row (SaaS login)
  - bo_businesses (status=prospect)
  - bo_tenants (1:1 isolation record)
  - bo_business_users (owner, active)
  - bo_business_subscriptions (pending)
  - provisioning checklist rows
  - audit event

Never sells pkg_founder or pkg_custom. No live Stripe calls here.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import HTTPException

from app.services.business.ids import new_id, unique_slug
from app.utils.security import create_access_token, create_refresh_token, get_password_hash


SELLABLE_PACKAGE_IDS = (
    "pkg_starter",
    "pkg_growth",
    "pkg_empire",
    "pkg_apostille_only",
)

NEVER_SOLD_PACKAGE_IDS = frozenset({"pkg_founder", "pkg_custom"})

_PROVISIONING_STEPS = [
    ("lead_capture", "Lead capture", "Prospect created from self-serve signup.", True, True),
    ("business_profile", "Business profile", "Display name, contact email, locale.", True, True),
    ("package_selection", "Package selection", "Pending subscription created.", True, True),
    ("payment_or_contract", "Payment", "Stripe TEST checkout (pending until webhook).", True, False),
    ("module_entitlement_assignment", "Entitlements", "Package entitlements become queryable.", False, True),
    ("business_user_invite", "Owner account", "Owner business_user activated.", True, True),
    ("social_account_setup", "Social account", "Required for Growth and Empire.", False, False),
    ("vendor_setup", "Vendor setup", "Required for Apostille-only and Empire.", False, False),
    ("apostille_intake_setup", "Apostille intake", "Required for Apostille-only and Empire.", False, False),
    ("max_desk_routing", "MAX desk routing", "Desk set derived from package.", False, True),
    ("notification_setup", "Notifications", "Owner email on the tenant record.", True, False),
    ("launch_review", "Launch review", "Founder sign-off before customer-facing launch.", True, False),
]


def assert_sellable_package(package: dict) -> None:
    package_id = package.get("id")
    if package_id in NEVER_SOLD_PACKAGE_IDS or package.get("is_internal"):
        raise HTTPException(
            status_code=400,
            detail="That package is not sold. Founder / internal packages cannot be purchased.",
        )
    if package.get("is_custom"):
        raise HTTPException(status_code=400, detail="Custom packages are Founder-priced, not self-serve.")
    if package_id not in SELLABLE_PACKAGE_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"package {package_id!r} is not a self-serve package",
        )
    if not package.get("is_active"):
        raise HTTPException(status_code=400, detail=f"package {package_id!r} is not active")


def _fetch_package(conn: sqlite3.Connection, package_id: str) -> dict:
    row = conn.execute("SELECT * FROM bo_packages WHERE id = ?", (package_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"package {package_id!r} not found")
    return dict(row)


def _ensure_access_users_saas_columns(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS access_users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            password_hash TEXT,
            role TEXT NOT NULL DEFAULT 'viewer',
            tier TEXT DEFAULT 'lite',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(access_users)").fetchall()}
    for col, typ in (
        ("email", "TEXT"),
        ("password_hash", "TEXT"),
        ("tier", "TEXT"),
        ("is_active", "INTEGER"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
    ):
        if col not in existing:
            conn.execute(f"ALTER TABLE access_users ADD COLUMN {col} {typ}")


def _create_access_user(conn: sqlite3.Connection, *, name: str, email: str, password: str, package_id: str) -> str:
    _ensure_access_users_saas_columns(conn)
    existing = conn.execute("SELECT id FROM access_users WHERE email = ?", (email,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = new_id("usr")
    hashed = get_password_hash(password)
    tier = {
        "pkg_starter": "starter",
        "pkg_growth": "growth",
        "pkg_empire": "empire",
        "pkg_apostille_only": "apostille",
    }.get(package_id, "starter")
    conn.execute(
        """
        INSERT INTO access_users
            (id, name, email, password_hash, role, tier, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'viewer', ?, 1, datetime('now'), datetime('now'))
        """,
        (user_id, name, email, hashed, tier),
    )
    return user_id


def _seed_provisioning(conn: sqlite3.Connection, *, business_id: str, package_id: str) -> None:
    required_social = package_id in ("pkg_growth", "pkg_empire")
    required_vendor = package_id in ("pkg_apostille_only", "pkg_empire")
    for idx, (step_key, title, description, default_required, auto_done) in enumerate(_PROVISIONING_STEPS):
        required = default_required
        if step_key == "social_account_setup":
            required = required_social
        elif step_key in ("vendor_setup", "apostille_intake_setup"):
            required = required_vendor
        completed_at = "CURRENT_TIMESTAMP" if auto_done else None
        completed_by = "system" if auto_done else None
        conn.execute(
            """
            INSERT INTO bo_provisioning_checklists
                (id, business_id, package_id, step_key, title, description, required,
                 completed_at, completed_by, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, """
            + ("CURRENT_TIMESTAMP" if auto_done else "NULL")
            + """, ?, ?)
            """,
            (
                new_id("pc"),
                business_id,
                package_id,
                step_key,
                title,
                description,
                1 if required else 0,
                completed_by,
                idx + 1,
            ),
        )


def signup_self_serve(
    conn: sqlite3.Connection,
    *,
    email: str,
    password: str,
    display_name: str,
    business_name: str,
    package_id: str,
) -> dict[str, Any]:
    email = (email or "").strip().lower()
    display_name = (display_name or "").strip()
    business_name = (business_name or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email is required")
    if len(password or "") < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name is required")
    if not business_name:
        raise HTTPException(status_code=400, detail="business_name is required")

    package = _fetch_package(conn, package_id)
    assert_sellable_package(package)

    user_id = _create_access_user(
        conn, name=display_name, email=email, password=password, package_id=package_id
    )
    business_id = new_id("biz")
    tenant_id = new_id("ten")
    subscription_id = new_id("sub")
    owner_id = new_id("bu")
    slug = unique_slug(business_name)

    conn.execute(
        """
        INSERT INTO bo_businesses
            (id, slug, display_name, business_type, status, contact_email, billing_email, default_locale)
        VALUES (?, ?, ?, ?, 'prospect', ?, ?, 'en')
        """,
        (business_id, slug, business_name, "apostille" if package_id == "pkg_apostille_only" else "workroom", email, email),
    )
    conn.execute(
        """
        INSERT INTO bo_tenants (id, business_id, slug, isolation_key, status)
        VALUES (?, ?, ?, ?, 'active')
        """,
        (tenant_id, business_id, slug, tenant_id),
    )
    conn.execute(
        """
        INSERT INTO bo_business_users
            (id, business_id, user_id, email, display_name, role, status, activated_at)
        VALUES (?, ?, ?, ?, ?, 'owner', 'active', CURRENT_TIMESTAMP)
        """,
        (owner_id, business_id, user_id, email, display_name),
    )
    conn.execute(
        """
        INSERT INTO bo_business_subscriptions
            (id, business_id, package_id, status, started_at)
        VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        """,
        (subscription_id, business_id, package_id),
    )
    _seed_provisioning(conn, business_id=business_id, package_id=package_id)
    conn.execute(
        """
        INSERT INTO bo_business_audit_events
            (id, business_id, actor, action, target_type, target_id, payload)
        VALUES (?, ?, ?, 'signup.self_serve', 'subscription', ?, ?)
        """,
        (
            new_id("bae"),
            business_id,
            f"business:{business_id}",
            subscription_id,
            json.dumps({"package_id": package_id, "tenant_id": tenant_id}),
        ),
    )

    token_data = {
        "user_id": user_id,
        "email": email,
        "business_id": business_id,
        "tenant_id": tenant_id,
    }
    return {
        "user": {
            "id": user_id,
            "name": display_name,
            "email": email,
            "role": "owner",
            "package_id": package_id,
        },
        "business": {
            "id": business_id,
            "slug": slug,
            "display_name": business_name,
            "status": "prospect",
        },
        "tenant": {
            "id": tenant_id,
            "business_id": business_id,
            "slug": slug,
            "status": "active",
        },
        "subscription": {
            "id": subscription_id,
            "business_id": business_id,
            "package_id": package_id,
            "status": "pending",
        },
        "next_step": "checkout",
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }
