"""
BusinessOps Foundation router (Phase 1, 2026-06-09).

Source of truth:
  - REPORT-businessops-tenantops-design.md
  - REPORT-businessops-design-decisions.md

Scope (Phase 1, gate summary in the closure report):
  - Read-only GET endpoints only
  - No POST / PUT / PATCH / DELETE in Phase 1
  - No customer-facing UI

Tables (bo_ prefix to match VendorOps vo_ pattern):
  bo_businesses
  bo_business_profiles
  bo_packages
  bo_business_subscriptions
  bo_module_entitlements
  bo_provisioning_checklists
  bo_business_users
  bo_business_integrations
  bo_business_audit_events

DB pattern: raw SQLite + CREATE TABLE IF NOT EXISTS on first call.
This matches the VendorOps pattern (vendorops.py::_init_vendorops_schema)
and avoids the empirebox.db vs empire.db split.

Seed data: backend/app/seeds/ (NOT backend/app/data/seed/, which is
gitignored under the repo-wide `data/` rule).

Prefix: /api/v1/businessops
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db import database
from app.services.business.entitlements import check_entitlement


router = APIRouter(prefix="/businessops", tags=["BusinessOps"])


# ──────────────────────────────────────────────────────────────────
# DDL — applied on first request, idempotent (matches VendorOps pattern)
# ──────────────────────────────────────────────────────────────────

_BO_DDL = """
CREATE TABLE IF NOT EXISTS bo_businesses (
    id              TEXT PRIMARY KEY,
    slug            TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    legal_name      TEXT,
    business_type   TEXT NOT NULL DEFAULT 'workroom',
    status          TEXT NOT NULL DEFAULT 'prospect',
    timezone        TEXT NOT NULL DEFAULT 'America/New_York',
    default_locale  TEXT NOT NULL DEFAULT 'en',
    contact_email   TEXT,
    contact_phone   TEXT,
    billing_email   TEXT,
    website         TEXT,
    notes           TEXT,
    metadata        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at    TIMESTAMP,
    canceled_at     TIMESTAMP,
    CHECK (status IN ('prospect', 'active', 'paused', 'canceled'))
);
CREATE INDEX IF NOT EXISTS idx_bo_businesses_status ON bo_businesses(status);
CREATE INDEX IF NOT EXISTS idx_bo_businesses_type ON bo_businesses(business_type);

CREATE TABLE IF NOT EXISTS bo_business_profiles (
    business_id            TEXT PRIMARY KEY REFERENCES bo_businesses(id) ON DELETE CASCADE,
    apostille_states       TEXT,
    apostille_languages    TEXT,
    workroom_specialties   TEXT,
    woodcraft_materials    TEXT,
    social_ig_handle       TEXT,
    social_fb_page         TEXT,
    social_linkedin        TEXT,
    extra                  TEXT,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bo_packages (
    id                  TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    description         TEXT,
    monthly_price_usd   INTEGER NOT NULL DEFAULT 0,
    annual_price_usd    INTEGER NOT NULL DEFAULT 0,
    is_custom           BOOLEAN NOT NULL DEFAULT 0,
    is_internal         BOOLEAN NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT 1,
    positioning         TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bo_business_subscriptions (
    id                      TEXT PRIMARY KEY,
    business_id             TEXT NOT NULL REFERENCES bo_businesses(id) ON DELETE RESTRICT,
    package_id              TEXT NOT NULL REFERENCES bo_packages(id) ON DELETE RESTRICT,
    status                  TEXT NOT NULL DEFAULT 'pending',
    started_at              TIMESTAMP,
    activated_at            TIMESTAMP,
    current_period_start    TIMESTAMP,
    current_period_end      TIMESTAMP,
    canceled_at             TIMESTAMP,
    cancellation_reason     TEXT,
    stripe_subscription_id  TEXT,
    notes                   TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('pending', 'active', 'paused', 'canceled', 'expired'))
);
CREATE INDEX IF NOT EXISTS idx_bo_subs_business ON bo_business_subscriptions(business_id);
CREATE INDEX IF NOT EXISTS idx_bo_subs_package  ON bo_business_subscriptions(package_id);
CREATE INDEX IF NOT EXISTS idx_bo_subs_status   ON bo_business_subscriptions(status);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_bo_subs_business_active
    ON bo_business_subscriptions(business_id)
    WHERE status IN ('pending', 'active', 'paused');

CREATE TABLE IF NOT EXISTS bo_module_entitlements (
    id                  TEXT PRIMARY KEY,
    package_id          TEXT NOT NULL REFERENCES bo_packages(id) ON DELETE CASCADE,
    module_id           TEXT NOT NULL,
    access_level        TEXT NOT NULL DEFAULT 'none',
    limits              TEXT,
    requires_approval   BOOLEAN NOT NULL DEFAULT 0,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (package_id, module_id),
    CHECK (access_level IN ('none', 'preview', 'internal', 'standard', 'full', 'founder_only'))
);
CREATE INDEX IF NOT EXISTS idx_bo_module_ent_module ON bo_module_entitlements(module_id);

CREATE TABLE IF NOT EXISTS bo_provisioning_checklists (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL REFERENCES bo_businesses(id) ON DELETE RESTRICT,
    package_id      TEXT NOT NULL REFERENCES bo_packages(id) ON DELETE RESTRICT,
    step_key        TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    required        BOOLEAN NOT NULL DEFAULT 1,
    completed_at    TIMESTAMP,
    completed_by    TEXT,
    notes           TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (business_id, step_key)
);
CREATE INDEX IF NOT EXISTS idx_bo_pc_business ON bo_provisioning_checklists(business_id);

CREATE TABLE IF NOT EXISTS bo_business_users (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL REFERENCES bo_businesses(id) ON DELETE RESTRICT,
    user_id         TEXT,
    email           TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'member',
    status          TEXT NOT NULL DEFAULT 'invited',
    last_active_at  TIMESTAMP,
    invited_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at    TIMESTAMP,
    removed_at      TIMESTAMP,
    UNIQUE (business_id, email),
    CHECK (role IN ('owner', 'admin', 'member', 'vendor', 'customer_contact')),
    CHECK (status IN ('invited', 'active', 'suspended', 'removed'))
);
CREATE INDEX IF NOT EXISTS idx_bo_bu_business ON bo_business_users(business_id);
CREATE INDEX IF NOT EXISTS idx_bo_bu_email    ON bo_business_users(email);

CREATE TABLE IF NOT EXISTS bo_business_integrations (
    id                      TEXT PRIMARY KEY,
    business_id             TEXT NOT NULL REFERENCES bo_businesses(id) ON DELETE RESTRICT,
    provider                TEXT NOT NULL,
    account_ref             TEXT,
    credential_ref_hash     TEXT,
    credential_ref_masked   TEXT,
    status                  TEXT NOT NULL DEFAULT 'active',
    connected_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at              TIMESTAMP,
    last_used_at            TIMESTAMP,
    UNIQUE (business_id, provider),
    CHECK (status IN ('active', 'expired', 'revoked'))
);
CREATE INDEX IF NOT EXISTS idx_bo_bi_business ON bo_business_integrations(business_id);

CREATE TABLE IF NOT EXISTS bo_business_audit_events (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL REFERENCES bo_businesses(id) ON DELETE RESTRICT,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    target_type     TEXT,
    target_id       TEXT,
    payload         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bo_bae_business_time ON bo_business_audit_events(business_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bo_bae_action        ON bo_business_audit_events(action);
"""


_SEED_DIR = Path(__file__).resolve().parent.parent / "seeds"


def _seed_packages_from_json(conn: sqlite3.Connection) -> int:
    """Upsert the 6 seeded packages from data/seed/packages.json. Returns count upserted."""
    path = _SEED_DIR / "packages.json"
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    for r in rows:
        conn.execute(
            """
            INSERT INTO bo_packages
                (id, display_name, description, monthly_price_usd, annual_price_usd,
                 is_custom, is_internal, is_active, positioning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name=excluded.display_name,
                description=excluded.description,
                monthly_price_usd=excluded.monthly_price_usd,
                annual_price_usd=excluded.annual_price_usd,
                is_custom=excluded.is_custom,
                is_internal=excluded.is_internal,
                is_active=excluded.is_active,
                positioning=excluded.positioning,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                r["id"],
                r["display_name"],
                r.get("description"),
                int(r.get("monthly_price_usd", 0)),
                int(r.get("annual_price_usd", 0)),
                bool(r.get("is_custom", False)),
                bool(r.get("is_internal", False)),
                bool(r.get("is_active", True)),
                r.get("positioning"),
            ),
        )
    return len(rows)


def _seed_entitlements_from_json(conn: sqlite3.Connection) -> int:
    """Upsert entitlement rows from data/seed/module_entitlements.json. Returns count upserted."""
    path = _SEED_DIR / "module_entitlements.json"
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    for r in rows:
        limits = r.get("limits")
        limits_json = json.dumps(limits) if limits is not None else None
        conn.execute(
            """
            INSERT INTO bo_module_entitlements
                (id, package_id, module_id, access_level, limits, requires_approval)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(package_id, module_id) DO UPDATE SET
                access_level=excluded.access_level,
                limits=excluded.limits,
                requires_approval=excluded.requires_approval,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                r.get("id") or f"ent_{r['package_id']}_{r['module_id']}",
                r["package_id"],
                r["module_id"],
                r["access_level"],
                limits_json,
                bool(r.get("requires_approval", False)),
            ),
        )
    return len(rows)


def _init_businessops_schema(conn: sqlite3.Connection) -> None:
    """Create all bo_ tables and seed from JSON. Idempotent."""
    conn.executescript(_BO_DDL)
    _seed_packages_from_json(conn)
    _seed_entitlements_from_json(conn)
    conn.commit()


# ──────────────────────────────────────────────────────────────────
# DB dependency (uses app.db.database like VendorOps)
# ──────────────────────────────────────────────────────────────────

@contextmanager
def _bo_db():
    """Get a bo_-scoped DB connection. Initializes schema on first use.

    We use the same DB file as the rest of the empire (empire.db)
    so all bo_ tables sit alongside vo_, sf_, etc. The bo_ prefix
    keeps us isolated.
    """
    conn = database.get_connection()
    try:
        _init_businessops_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row else None


# ──────────────────────────────────────────────────────────────────
# Pydantic response models (for OpenAPI; lightweight)
# ──────────────────────────────────────────────────────────────────

class EntitlementCheckRequest(BaseModel):
    business_id: str
    module_id: str
    action: str
    actor_role: Optional[str] = None


# ──────────────────────────────────────────────────────────────────
# GET endpoints — read-only
# ──────────────────────────────────────────────────────────────────

@router.get("/info")
def businessops_info():
    """Module info. Like VendorOps /info and ApostApp /."""
    return {
        "product": "BusinessOps",
        "module": "businessops",
        "route_prefix": "/api/v1/businessops",
        "db_prefix": "bo_",
        "phase": 1,
        "scope": "read-only foundation (additive; no module rewiring)",
        "source_of_truth": "REPORT-businessops-tenantops-design.md",
    }


@router.get("/health")
def businessops_health():
    """Liveness for the BusinessOps surface. Returns row counts."""
    with _bo_db() as conn:
        return {
            "status": "ok",
            "phase": 1,
            "tables": {
                "bo_businesses": conn.execute("SELECT COUNT(*) AS c FROM bo_businesses").fetchone()["c"],
                "bo_packages": conn.execute("SELECT COUNT(*) AS c FROM bo_packages").fetchone()["c"],
                "bo_module_entitlements": conn.execute("SELECT COUNT(*) AS c FROM bo_module_entitlements").fetchone()["c"],
                "bo_business_subscriptions": conn.execute("SELECT COUNT(*) AS c FROM bo_business_subscriptions").fetchone()["c"],
                "bo_provisioning_checklists": conn.execute("SELECT COUNT(*) AS c FROM bo_provisioning_checklists").fetchone()["c"],
                "bo_business_users": conn.execute("SELECT COUNT(*) AS c FROM bo_business_users").fetchone()["c"],
                "bo_business_integrations": conn.execute("SELECT COUNT(*) AS c FROM bo_business_integrations").fetchone()["c"],
                "bo_business_audit_events": conn.execute("SELECT COUNT(*) AS c FROM bo_business_audit_events").fetchone()["c"],
            },
        }


# ── /businesses ────────────────────────────────────────────────

@router.get("/businesses")
def list_businesses(
    status: Optional[str] = Query(None, description="Filter by status (prospect/active/paused/canceled)"),
    business_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List businesses. Read-only."""
    where = []
    params: list = []
    if status is not None:
        where.append("status = ?")
        params.append(status)
    if business_type is not None:
        where.append("business_type = ?")
        params.append(business_type)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_businesses{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        total = conn.execute(f"SELECT COUNT(*) AS c FROM bo_businesses{where_sql}", params).fetchone()["c"]
    return {"total": total, "limit": limit, "offset": offset, "items": [_row_to_dict(r) for r in rows]}


@router.get("/businesses/{business_id}")
def get_business(business_id: str):
    """Get one business. Read-only."""
    with _bo_db() as conn:
        row = conn.execute("SELECT * FROM bo_businesses WHERE id = ?", (business_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"business {business_id!r} not found")
    return _row_to_dict(row)


@router.get("/businesses/{business_id}/profile")
def get_business_profile(business_id: str):
    """Get the 1:1 profile for a business. Read-only."""
    with _bo_db() as conn:
        row = conn.execute(
            "SELECT * FROM bo_business_profiles WHERE business_id = ?",
            (business_id,),
        ).fetchone()
    if row is None:
        # Profile is optional; return null with 200 (caller can decide)
        return {"business_id": business_id, "profile": None}
    return {"business_id": business_id, "profile": _row_to_dict(row)}


# ── /packages ──────────────────────────────────────────────────

@router.get("/packages")
def list_packages(
    is_active: Optional[bool] = Query(None),
    is_internal: Optional[bool] = Query(None),
):
    """List packages. Read-only."""
    where = []
    params: list = []
    if is_active is not None:
        where.append("is_active = ?")
        params.append(1 if is_active else 0)
    if is_internal is not None:
        where.append("is_internal = ?")
        params.append(1 if is_internal else 0)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_packages{where_sql} ORDER BY monthly_price_usd ASC, id ASC",
            params,
        ).fetchall()
    return {"items": [_row_to_dict(r) for r in rows]}


@router.get("/packages/{package_id}")
def get_package(package_id: str):
    """Get one package. Read-only."""
    with _bo_db() as conn:
        row = conn.execute("SELECT * FROM bo_packages WHERE id = ?", (package_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"package {package_id!r} not found")
    return _row_to_dict(row)


# ── /entitlements ──────────────────────────────────────────────

@router.get("/entitlements")
def list_module_entitlements(
    package_id: Optional[str] = Query(None),
    module_id: Optional[str] = Query(None),
):
    """List module entitlements. Read-only."""
    where = []
    params: list = []
    if package_id is not None:
        where.append("package_id = ?")
        params.append(package_id)
    if module_id is not None:
        where.append("module_id = ?")
        params.append(module_id)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_module_entitlements{where_sql} ORDER BY package_id, module_id",
            params,
        ).fetchall()
    items = []
    for r in rows:
        d = _row_to_dict(r)
        # Parse limits JSON for the response
        if d.get("limits"):
            try:
                d["limits"] = json.loads(d["limits"])
            except (TypeError, ValueError):
                pass
        items.append(d)
    return {"items": items}


@router.get("/entitlements/matrix")
def get_entitlement_matrix():
    """The full 35-row (or however many) entitlement matrix, grouped by package.

    Read-only. Useful for the Founder admin UI (Phase 6).
    """
    with _bo_db() as conn:
        rows = conn.execute(
            """
            SELECT package_id, module_id, access_level, requires_approval, limits
            FROM bo_module_entitlements
            ORDER BY package_id, module_id
            """
        ).fetchall()
    matrix: dict = {}
    for r in rows:
        matrix.setdefault(r["package_id"], {})
        limits = {}
        if r["limits"]:
            try:
                limits = json.loads(r["limits"])
            except (TypeError, ValueError):
                limits = {}
        matrix[r["package_id"]][r["module_id"]] = {
            "access_level": r["access_level"],
            "requires_approval": bool(r["requires_approval"]),
            "limits": limits,
        }
    return {"matrix": matrix}


@router.post("/entitlements/check")
def check_entitlement_endpoint(req: EntitlementCheckRequest):
    """Read-only entitlement check. POST because it takes a body.

    This is the public gate. Returns the spec dict (allowed, access_level,
    requires_approval, limits, reason). The caller (MAX desk router,
    a router helper, a Founder admin tool) is responsible for enforcing
    approval gates and the auto-publish refusal.
    """
    with _bo_db() as conn:
        result = check_entitlement(
            business_id=req.business_id,
            module_id=req.module_id,
            action=req.action,
            actor_role=req.actor_role,
            conn=conn,
        )
    return result


# ── /subscriptions ─────────────────────────────────────────────

@router.get("/subscriptions")
def list_subscriptions(
    business_id: Optional[str] = Query(None),
    package_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """List subscriptions. Read-only."""
    where = []
    params: list = []
    if business_id is not None:
        where.append("business_id = ?")
        params.append(business_id)
    if package_id is not None:
        where.append("package_id = ?")
        params.append(package_id)
    if status is not None:
        where.append("status = ?")
        params.append(status)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_business_subscriptions{where_sql} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return {"items": [_row_to_dict(r) for r in rows]}


@router.get("/subscriptions/{subscription_id}")
def get_subscription(subscription_id: str):
    with _bo_db() as conn:
        row = conn.execute(
            "SELECT * FROM bo_business_subscriptions WHERE id = ?",
            (subscription_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"subscription {subscription_id!r} not found")
    return _row_to_dict(row)


# ── /provisioning-checklists ──────────────────────────────────

@router.get("/provisioning-checklists")
def list_provisioning_checklists(
    business_id: Optional[str] = Query(None),
    step_key: Optional[str] = Query(None),
    completed: Optional[bool] = Query(None),
):
    where = []
    params: list = []
    if business_id is not None:
        where.append("business_id = ?")
        params.append(business_id)
    if step_key is not None:
        where.append("step_key = ?")
        params.append(step_key)
    if completed is True:
        where.append("completed_at IS NOT NULL")
    elif completed is False:
        where.append("completed_at IS NULL")
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_provisioning_checklists{where_sql} ORDER BY business_id, sort_order, step_key",
            params,
        ).fetchall()
    return {"items": [_row_to_dict(r) for r in rows]}


# ── /business-users ────────────────────────────────────────────

@router.get("/business-users")
def list_business_users(
    business_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    where = []
    params: list = []
    if business_id is not None:
        where.append("business_id = ?")
        params.append(business_id)
    if role is not None:
        where.append("role = ?")
        params.append(role)
    if status is not None:
        where.append("status = ?")
        params.append(status)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_business_users{where_sql} ORDER BY business_id, role, email",
            params,
        ).fetchall()
    return {"items": [_row_to_dict(r) for r in rows]}


# ── /integrations ──────────────────────────────────────────────

@router.get("/integrations")
def list_integrations(
    business_id: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    where = []
    params: list = []
    if business_id is not None:
        where.append("business_id = ?")
        params.append(business_id)
    if provider is not None:
        where.append("provider = ?")
        params.append(provider)
    if status is not None:
        where.append("status = ?")
        params.append(status)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_business_integrations{where_sql} ORDER BY business_id, provider",
            params,
        ).fetchall()
    return {"items": [_row_to_dict(r) for r in rows]}


# ── /audit-events ──────────────────────────────────────────────

@router.get("/audit-events")
def list_audit_events(
    business_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    where = []
    params: list = []
    if business_id is not None:
        where.append("business_id = ?")
        params.append(business_id)
    if action is not None:
        where.append("action = ?")
        params.append(action)
    if actor is not None:
        where.append("actor = ?")
        params.append(actor)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with _bo_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM bo_business_audit_events{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM bo_business_audit_events{where_sql}",
            params,
        ).fetchone()["c"]
    return {"total": total, "limit": limit, "offset": offset, "items": [_row_to_dict(r) for r in rows]}
