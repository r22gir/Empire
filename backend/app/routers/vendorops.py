"""VendorOps standalone add-on routes.

VendorOps is intentionally isolated from payments and RelistApp. It owns the
`/api/v1/vendorops` prefix and `vo_` database tables.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.db.database import get_db


router = APIRouter(prefix="/vendorops", tags=["VendorOps"])

TierName = Literal["free", "starter", "pro"]

TIERS: dict[str, dict[str, Any]] = {
    "free": {
        "monthly_price_usd": 0,
        "approval_limit": 3,
        "account_limit": 1,
        "subscription_limit": 1,
        "automation": "query_only",
        "positioning": "Useful trial for tracking one vendor workflow.",
    },
    "starter": {
        "monthly_price_usd": 19,
        "approval_limit": 25,
        "account_limit": 5,
        "subscription_limit": 10,
        "automation": "assisted_signup",
        "positioning": "Founder-managed vendor account setup and renewal tracking.",
    },
    "pro": {
        "monthly_price_usd": 79,
        "approval_limit": 250,
        "account_limit": 25,
        "subscription_limit": 100,
        "automation": "advanced_querying_with_write_gates",
        "positioning": "Stronger querying, monitoring, and approval-bound automation.",
    },
}

FORBIDDEN_CREDENTIAL_KEYS = {
    "password",
    "passcode",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "credential",
    "credentials",
}


class ApprovalCreate(BaseModel):
    tier: TierName = "free"
    vendor_name: str = Field(min_length=1)
    requested_action: str = Field(min_length=1)
    verification_boundary: str = "founder_approval_required_before_external_action"
    assisted_signup_state: str = "not_started"


class FounderConfirmation(BaseModel):
    explicit_founder_confirmation: bool
    actor: str = "founder"


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="allow")

    tier: TierName = "free"
    approval_id: str | None = None
    vendor_name: str = Field(min_length=1)
    category: str = "vendor"
    purpose: str | None = None
    vendor_url: str | None = None
    notes: str | None = None
    monthly_cost_usd: float = Field(default=0, ge=0)
    renewal_date: str | None = None
    renewal_cadence: str = "monthly"
    status: str = "active"
    credential_ref: str = Field(min_length=4)
    credential_owner: str = "founder"
    assisted_signup_state: str = "take_me_to_last_page_ready"
    explicit_founder_confirmation: bool


class AccountUpdate(BaseModel):
    vendor_name: str | None = None
    category: str | None = None
    purpose: str | None = None
    vendor_url: str | None = None
    notes: str | None = None
    monthly_cost_usd: float | None = Field(default=None, ge=0)
    renewal_date: str | None = None
    renewal_cadence: str | None = None
    status: str | None = None
    credential_owner: str | None = None
    explicit_founder_confirmation: bool


class SubscriptionCreate(BaseModel):
    tier: TierName = "free"
    vendor_name: str = Field(min_length=1)
    plan_name: str = Field(min_length=1)
    monthly_cost_usd: float = Field(default=0, ge=0)
    renewal_cadence: str = "monthly"
    renewal_date: str = Field(description="ISO date/datetime")
    license_ref: str | None = None
    explicit_founder_confirmation: bool


class SubscriptionUpdate(BaseModel):
    vendor_name: str | None = None
    plan_name: str | None = None
    tier: TierName | None = None
    monthly_cost_usd: float | None = Field(default=None, ge=0)
    renewal_cadence: str | None = None
    renewal_date: str | None = None
    status: str | None = None
    explicit_founder_confirmation: bool


class ActivationRequest(BaseModel):
    requested_tier: TierName
    explicit_founder_confirmation: bool


class MaxActionRequest(BaseModel):
    action: str
    target_type: str | None = None
    target_id: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _json(data: Any) -> str:
    return json.dumps(data or {}, sort_keys=True)


def _parse_json(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _mask_ref(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return value[:1] + "***" + value[-1:]
    return value[:4] + "***" + value[-4:]


def _hash_ref(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_tier(tier: str) -> dict[str, Any]:
    if tier not in TIERS:
        raise HTTPException(status_code=400, detail=f"Unknown VendorOps tier: {tier}")
    return TIERS[tier]


def _require_confirmation(value: bool):
    if not value:
        raise HTTPException(status_code=403, detail="Explicit founder confirmation required")


def _reject_plaintext_credential_fields(payload: BaseModel):
    extras = getattr(payload, "__pydantic_extra__", None) or {}
    forbidden = sorted(set(extras) & FORBIDDEN_CREDENTIAL_KEYS)
    if forbidden:
        raise HTTPException(status_code=400, detail=f"Plaintext credential fields are forbidden: {', '.join(forbidden)}")


def _init_vendorops_schema(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS vo_approvals (
            id TEXT PRIMARY KEY,
            tier TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            requested_action TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            founder_confirmed INTEGER NOT NULL DEFAULT 0,
            verification_boundary TEXT NOT NULL,
            assisted_signup_state TEXT,
            created_at TEXT NOT NULL,
            approved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS vo_accounts (
            id TEXT PRIMARY KEY,
            approval_id TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'vendor',
            purpose TEXT,
            vendor_url TEXT,
            notes TEXT,
            tier TEXT NOT NULL,
            account_status TEXT NOT NULL,
            monthly_cost_usd REAL NOT NULL DEFAULT 0,
            renewal_date TEXT,
            renewal_cadence TEXT NOT NULL DEFAULT 'monthly',
            credential_ref_hash TEXT NOT NULL,
            credential_ref_masked TEXT NOT NULL,
            credential_owner TEXT NOT NULL,
            assisted_signup_state TEXT,
            provisioning_trail TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vo_subscriptions (
            id TEXT PRIMARY KEY,
            vendor_name TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            tier TEXT NOT NULL,
            status TEXT NOT NULL,
            monthly_cost_usd REAL NOT NULL DEFAULT 0,
            renewal_cadence TEXT NOT NULL DEFAULT 'monthly',
            license_ref_masked TEXT,
            renewal_date TEXT NOT NULL,
            cancellation_state TEXT NOT NULL DEFAULT 'active_monitoring',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vo_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            metadata TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vo_activation (
            id TEXT PRIMARY KEY,
            activation_state TEXT NOT NULL,
            tier TEXT NOT NULL,
            billing_status TEXT NOT NULL,
            checkout_status TEXT NOT NULL,
            requested_tier TEXT,
            requested_at TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vo_renewal_alerts (
            id TEXT PRIMARY KEY,
            subscription_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            renewal_date TEXT NOT NULL,
            estimated_cost_usd REAL NOT NULL DEFAULT 0,
            suggested_action TEXT NOT NULL,
            delivery_status TEXT NOT NULL,
            telegram_status TEXT NOT NULL,
            email_status TEXT NOT NULL,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(subscription_id, alert_type)
        );
        """
    )
    _ensure_column(conn, "vo_accounts", "category", "TEXT NOT NULL DEFAULT 'vendor'")
    _ensure_column(conn, "vo_accounts", "purpose", "TEXT")
    _ensure_column(conn, "vo_accounts", "vendor_url", "TEXT")
    _ensure_column(conn, "vo_accounts", "notes", "TEXT")
    _ensure_column(conn, "vo_accounts", "monthly_cost_usd", "REAL NOT NULL DEFAULT 0")
    _ensure_column(conn, "vo_accounts", "renewal_date", "TEXT")
    _ensure_column(conn, "vo_accounts", "renewal_cadence", "TEXT NOT NULL DEFAULT 'monthly'")
    _ensure_column(conn, "vo_subscriptions", "monthly_cost_usd", "REAL NOT NULL DEFAULT 0")
    _ensure_column(conn, "vo_subscriptions", "renewal_cadence", "TEXT NOT NULL DEFAULT 'monthly'")
    if conn.execute("SELECT COUNT(*) AS count FROM vo_activation WHERE id = 'default'").fetchone()["count"] == 0:
        conn.execute(
            """
            INSERT INTO vo_activation (id, activation_state, tier, billing_status, checkout_status, updated_at)
            VALUES ('default', 'active_free', 'free', 'free_no_billing_required', 'not_started', ?)
            """,
            (_now(),),
        )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str):
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _audit(conn: sqlite3.Connection, event_type: str, entity_type: str, entity_id: str, actor: str = "system", metadata: dict[str, Any] | None = None):
    conn.execute(
        """
        INSERT INTO vo_audit_events (event_type, entity_type, entity_id, actor, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (event_type, entity_type, entity_id, actor, _json(metadata), _now()),
    )


def _count(conn: sqlite3.Connection, table: str, tier: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE tier = ?", (tier,)).fetchone()
    return int(row["count"] if row else 0)


def _enforce_limit(conn: sqlite3.Connection, tier: str, table: str, limit_key: str):
    limit = int(_require_tier(tier)[limit_key])
    if _count(conn, table, tier) >= limit:
        raise HTTPException(status_code=402, detail=f"VendorOps {tier} tier {limit_key} reached")


def _serialize_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    if "metadata" in data:
        data["metadata"] = _parse_json(data["metadata"])
    if "provisioning_trail" in data:
        data["provisioning_trail"] = _parse_json(data["provisioning_trail"])
    return data


def _list_rows(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [_serialize_row(row) for row in conn.execute(query, params).fetchall()]


def _activation(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM vo_activation WHERE id = 'default'").fetchone()
    return _serialize_row(row) or {
        "activation_state": "inactive",
        "tier": "free",
        "billing_status": "not_configured",
        "checkout_status": "not_started",
    }


def _alert_type_for(renewal_date: str, now: datetime | None = None) -> str | None:
    now = now or datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(renewal_date.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    days = (parsed.date() - now.date()).days
    if days < 0:
        return "overdue"
    if days <= 1:
        return "1_day"
    if days <= 7:
        return "7_day"
    if days <= 30:
        return "30_day"
    return None


def _suggested_action(alert_type: str) -> str:
    if alert_type == "overdue":
        return "Review immediately: renewal date has passed."
    if alert_type == "1_day":
        return "Confirm renewal or cancel today."
    if alert_type == "7_day":
        return "Decide whether to renew, downgrade, or cancel this week."
    return "Review usage and decide before the renewal window tightens."


def _generate_alerts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    now = _now()
    created: list[dict[str, Any]] = []
    rows = conn.execute("SELECT * FROM vo_subscriptions WHERE status = 'active'").fetchall()
    for row in rows:
        try:
            alert_type = _alert_type_for(row["renewal_date"])
        except Exception:
            continue
        if not alert_type:
            continue
        alert_id = _new_id("voalert")
        conn.execute(
            """
            INSERT OR IGNORE INTO vo_renewal_alerts
            (id, subscription_id, alert_type, vendor_name, renewal_date, estimated_cost_usd,
             suggested_action, delivery_status, telegram_status, email_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', 'queued_not_sent', 'queued_not_sent', ?, ?)
            """,
            (
                alert_id,
                row["id"],
                alert_type,
                row["vendor_name"],
                row["renewal_date"],
                float(row["monthly_cost_usd"] or 0),
                _suggested_action(alert_type),
                now,
                now,
            ),
        )
    return _list_rows(conn, "SELECT * FROM vo_renewal_alerts ORDER BY datetime(renewal_date) ASC, created_at DESC")


@router.get("/plans")
def get_vendorops_plans():
    return {
        "product": "VendorOps",
        "standalone_add_on": True,
        "route_prefix": "/api/v1/vendorops",
        "db_prefix": "vo_",
        "max_policy": "query_only_initially_write_gate_enforced",
        "tiers": TIERS,
    }


@router.get("/status")
def get_vendorops_status(tier: TierName = Query("free")):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        activation = _activation(conn)
        effective_tier = activation.get("tier") or tier
        _require_tier(effective_tier)
        pending = conn.execute("SELECT COUNT(*) AS count FROM vo_approvals WHERE status = 'pending'").fetchone()["count"]
        accounts = _count(conn, "vo_accounts", effective_tier)
        subscriptions = _count(conn, "vo_subscriptions", effective_tier)
        return {
            "status": "active",
            "surface": "standalone_vendorops_add_on",
            "activation": activation,
            "activation_state": activation.get("activation_state"),
            "tier": effective_tier,
            "limits": TIERS[effective_tier],
            "pending_approvals": pending,
            "accounts_used": accounts,
            "subscriptions_used": subscriptions,
            "max_can_query": True,
            "max_can_write": False,
            "credential_policy": "credential_ref_only_hash_stored_no_plaintext",
        }


@router.get("/activation")
def get_vendorops_activation():
    with get_db() as conn:
        _init_vendorops_schema(conn)
        activation = _activation(conn)
        return {
            "activation": activation,
            "available_states": ["inactive", "active_free", "active_starter", "active_pro"],
            "billing_hookup": "pending",
            "checkout_available": False,
            "upgrade_path": "request_upgrade_records_intent_billing_checkout_pending",
            "tiers": TIERS,
        }


@router.post("/activation/request-upgrade")
def request_vendorops_upgrade(payload: ActivationRequest):
    _require_confirmation(payload.explicit_founder_confirmation)
    _require_tier(payload.requested_tier)
    if payload.requested_tier == "free":
        raise HTTPException(status_code=400, detail="Free tier is already active; paid checkout is not required.")
    with get_db() as conn:
        _init_vendorops_schema(conn)
        now = _now()
        conn.execute(
            """
            UPDATE vo_activation
            SET billing_status = 'billing_hookup_pending',
                checkout_status = 'upgrade_requested_checkout_not_wired',
                requested_tier = ?,
                requested_at = ?,
                updated_at = ?
            WHERE id = 'default'
            """,
            (payload.requested_tier, now, now),
        )
        _audit(
            conn,
            "activation_upgrade_requested",
            "activation",
            "default",
            actor="founder",
            metadata={"requested_tier": payload.requested_tier, "checkout_available": False},
        )
        return {
            "activation": _activation(conn),
            "checkout_available": False,
            "message": "VendorOps upgrade recorded. Billing checkout hookup is pending; no paid activation was faked.",
        }


@router.get("/dashboard")
def get_vendorops_dashboard(tier: TierName = Query("free")):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        activation = _activation(conn)
        effective_tier = activation.get("tier") or tier
        _require_tier(effective_tier)
        _generate_alerts(conn)
        total_accounts = conn.execute("SELECT COUNT(*) AS count FROM vo_accounts").fetchone()["count"]
        active_subscriptions = conn.execute("SELECT COUNT(*) AS count FROM vo_subscriptions WHERE status = 'active'").fetchone()["count"]
        monthly_cost = conn.execute(
            "SELECT COALESCE(SUM(monthly_cost_usd), 0) AS total FROM vo_subscriptions WHERE status = 'active'"
        ).fetchone()["total"]
        upcoming_renewals = conn.execute(
            """
            SELECT COUNT(*) AS count FROM vo_subscriptions
            WHERE status = 'active' AND datetime(renewal_date) <= datetime(?)
            """,
            ((datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),),
        ).fetchone()["count"]
        pending_approvals = conn.execute("SELECT COUNT(*) AS count FROM vo_approvals WHERE status = 'pending'").fetchone()["count"]
        return {
            "tier": effective_tier,
            "activation_state": activation.get("activation_state"),
            "kpis": {
                "total_accounts": total_accounts,
                "active_subscriptions": active_subscriptions,
                "monthly_cost_total_usd": float(monthly_cost or 0),
                "upcoming_renewals_30d": upcoming_renewals,
                "pending_approvals": pending_approvals,
            },
            "max_policy": "query_only_initially_write_gate_enforced",
        }


@router.get("/max-summary")
def get_vendorops_max_summary(tier: TierName = Query("free")):
    status = get_vendorops_status(tier=tier)
    dashboard = get_vendorops_dashboard(tier=tier)
    alerts = get_renewal_alerts(days=30, include_reviewed=False)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        pending = _list_rows(conn, "SELECT * FROM vo_approvals WHERE status = 'pending' ORDER BY created_at DESC")
        active_subscriptions = _list_rows(conn, "SELECT * FROM vo_subscriptions WHERE status = 'active' ORDER BY datetime(renewal_date) ASC")
    return {
        "vendorops": status,
        "dashboard": dashboard,
        "pending_approvals": pending,
        "active_subscriptions": active_subscriptions,
        "renewal_alerts": alerts,
        "source_of_truth": "/api/v1/vendorops/status",
        "write_gate": "MAX query-only. Founder confirmation is required for approvals/provisioning/cancellations.",
    }


@router.post("/max-action")
def reject_max_write_action(_: MaxActionRequest):
    raise HTTPException(status_code=403, detail="VendorOps MAX integration is query-only. Founder-confirmed route required.")


@router.post("/approvals")
def create_approval(payload: ApprovalCreate):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        _enforce_limit(conn, payload.tier, "vo_approvals", "approval_limit")
        approval_id = _new_id("voap")
        conn.execute(
            """
            INSERT INTO vo_approvals
            (id, tier, vendor_name, requested_action, status, founder_confirmed, verification_boundary, assisted_signup_state, created_at)
            VALUES (?, ?, ?, ?, 'pending', 0, ?, ?, ?)
            """,
            (
                approval_id,
                payload.tier,
                payload.vendor_name,
                payload.requested_action,
                payload.verification_boundary,
                payload.assisted_signup_state,
                _now(),
            ),
        )
        _audit(conn, "approval_requested", "approval", approval_id, metadata=payload.model_dump())
        row = conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (approval_id,)).fetchone()
        return {"approval": _serialize_row(row)}


@router.post("/approvals/{approval_id}/approve")
def approve_request(approval_id: str, payload: FounderConfirmation):
    _require_confirmation(payload.explicit_founder_confirmation)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        row = conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (approval_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="VendorOps approval not found")
        conn.execute(
            "UPDATE vo_approvals SET status = 'approved', founder_confirmed = 1, approved_at = ? WHERE id = ?",
            (_now(), approval_id),
        )
        _audit(conn, "approval_confirmed", "approval", approval_id, actor=payload.actor, metadata={"explicit_founder_confirmation": True})
        return {"approval": _serialize_row(conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (approval_id,)).fetchone())}


@router.post("/approvals/{approval_id}/reject")
def reject_request(approval_id: str, payload: FounderConfirmation):
    _require_confirmation(payload.explicit_founder_confirmation)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        row = conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (approval_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="VendorOps approval not found")
        conn.execute(
            "UPDATE vo_approvals SET status = 'rejected', founder_confirmed = 1, approved_at = ? WHERE id = ?",
            (_now(), approval_id),
        )
        _audit(conn, "approval_rejected", "approval", approval_id, actor=payload.actor, metadata={"explicit_founder_confirmation": True})
        return {"approval": _serialize_row(conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (approval_id,)).fetchone())}


@router.get("/approvals")
def list_approvals(status: str | None = None, limit: int = Query(100, ge=1, le=250)):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        if status:
            rows = _list_rows(conn, "SELECT * FROM vo_approvals WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
        else:
            rows = _list_rows(conn, "SELECT * FROM vo_approvals ORDER BY created_at DESC LIMIT ?", (limit,))
        return {"approvals": rows}


@router.post("/accounts")
def create_account(payload: AccountCreate):
    _require_confirmation(payload.explicit_founder_confirmation)
    _reject_plaintext_credential_fields(payload)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        _enforce_limit(conn, payload.tier, "vo_accounts", "account_limit")
        now = _now()
        approval = conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (payload.approval_id,)).fetchone()
        if not approval and payload.approval_id is None:
            approval_id = _new_id("voap")
            conn.execute(
                """
                INSERT INTO vo_approvals
                (id, tier, vendor_name, requested_action, status, founder_confirmed, verification_boundary, assisted_signup_state, created_at, approved_at)
                VALUES (?, ?, ?, 'founder direct account create', 'approved', 1, 'founder_direct_ui_confirmation', ?, ?, ?)
                """,
                (approval_id, payload.tier, payload.vendor_name, payload.assisted_signup_state, now, now),
            )
            _audit(conn, "founder_direct_account_create_approved", "approval", approval_id, actor="founder", metadata={"vendor_name": payload.vendor_name})
            approval = conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (approval_id,)).fetchone()
            payload.approval_id = approval_id
        if not approval:
            raise HTTPException(status_code=404, detail="VendorOps approval not found")
        if approval["status"] != "approved" or not approval["founder_confirmed"]:
            raise HTTPException(status_code=403, detail="Approved founder confirmation is required before provisioning")
        account_id = _new_id("voacct")
        trail = {
            "approval_id": payload.approval_id,
            "verification_boundary": approval["verification_boundary"],
            "assisted_signup_state": payload.assisted_signup_state,
            "external_action_status": "founder_confirmed_ready_for_assisted_signup",
        }
        conn.execute(
            """
            INSERT INTO vo_accounts
            (id, approval_id, vendor_name, category, purpose, vendor_url, notes, tier, account_status, monthly_cost_usd, renewal_date, renewal_cadence, credential_ref_hash, credential_ref_masked,
             credential_owner, assisted_signup_state, provisioning_trail, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                payload.approval_id,
                payload.vendor_name,
                payload.category,
                payload.purpose,
                payload.vendor_url,
                payload.notes,
                payload.tier,
                payload.status,
                payload.monthly_cost_usd,
                payload.renewal_date,
                payload.renewal_cadence,
                _hash_ref(payload.credential_ref),
                _mask_ref(payload.credential_ref),
                payload.credential_owner,
                payload.assisted_signup_state,
                _json(trail),
                now,
                now,
            ),
        )
        _audit(
            conn,
            "account_provisioning_trail_created",
            "account",
            account_id,
            actor="founder",
            metadata={**trail, "credential_owner": payload.credential_owner, "credential_ref_masked": _mask_ref(payload.credential_ref)},
        )
        return {"account": _serialize_row(conn.execute("SELECT * FROM vo_accounts WHERE id = ?", (account_id,)).fetchone())}


@router.get("/accounts")
def list_accounts(tier: TierName | None = None):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        if tier:
            _require_tier(tier)
            rows = _list_rows(conn, "SELECT * FROM vo_accounts WHERE tier = ? ORDER BY created_at DESC", (tier,))
        else:
            rows = _list_rows(conn, "SELECT * FROM vo_accounts ORDER BY created_at DESC")
        return {"accounts": rows}


@router.patch("/accounts/{account_id}")
def update_account(account_id: str, payload: AccountUpdate):
    _require_confirmation(payload.explicit_founder_confirmation)
    fields = payload.model_dump(exclude_unset=True, exclude={"explicit_founder_confirmation"})
    mapping = {"status": "account_status", "owner": "credential_owner"}
    updates: list[str] = []
    params: list[Any] = []
    allowed = {"vendor_name", "category", "purpose", "vendor_url", "notes", "monthly_cost_usd", "renewal_date", "renewal_cadence", "status", "credential_owner"}
    for key, value in fields.items():
        if key not in allowed:
            continue
        column = mapping.get(key, key)
        updates.append(f"{column} = ?")
        params.append(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No editable account fields supplied")
    updates.append("updated_at = ?")
    params.append(_now())
    params.append(account_id)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        existing = conn.execute("SELECT * FROM vo_accounts WHERE id = ?", (account_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="VendorOps account not found")
        conn.execute(f"UPDATE vo_accounts SET {', '.join(updates)} WHERE id = ?", tuple(params))
        _audit(conn, "account_updated", "account", account_id, actor="founder", metadata=fields)
        return {"account": _serialize_row(conn.execute("SELECT * FROM vo_accounts WHERE id = ?", (account_id,)).fetchone())}


@router.post("/subscriptions")
def create_subscription(payload: SubscriptionCreate):
    _require_confirmation(payload.explicit_founder_confirmation)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        _enforce_limit(conn, payload.tier, "vo_subscriptions", "subscription_limit")
        sub_id = _new_id("vosub")
        now = _now()
        conn.execute(
            """
            INSERT INTO vo_subscriptions
            (id, vendor_name, plan_name, tier, status, monthly_cost_usd, renewal_cadence, license_ref_masked, renewal_date, cancellation_state, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, 'active_monitoring', ?, ?)
            """,
            (
                sub_id,
                payload.vendor_name,
                payload.plan_name,
                payload.tier,
                payload.monthly_cost_usd,
                payload.renewal_cadence,
                _mask_ref(payload.license_ref),
                payload.renewal_date,
                now,
                now,
            ),
        )
        _audit(conn, "subscription_tracked", "subscription", sub_id, actor="founder", metadata={"vendor_name": payload.vendor_name, "renewal_date": payload.renewal_date})
        return {"subscription": _serialize_row(conn.execute("SELECT * FROM vo_subscriptions WHERE id = ?", (sub_id,)).fetchone())}


@router.get("/subscriptions")
def list_subscriptions(tier: TierName | None = None):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        if tier:
            _require_tier(tier)
            rows = _list_rows(conn, "SELECT * FROM vo_subscriptions WHERE tier = ? ORDER BY renewal_date ASC", (tier,))
        else:
            rows = _list_rows(conn, "SELECT * FROM vo_subscriptions ORDER BY renewal_date ASC")
        return {"subscriptions": rows}


@router.patch("/subscriptions/{subscription_id}")
def update_subscription(subscription_id: str, payload: SubscriptionUpdate):
    _require_confirmation(payload.explicit_founder_confirmation)
    fields = payload.model_dump(exclude_unset=True, exclude={"explicit_founder_confirmation"})
    allowed = {"vendor_name", "plan_name", "tier", "monthly_cost_usd", "renewal_cadence", "renewal_date", "status"}
    updates: list[str] = []
    params: list[Any] = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "tier" and value is not None:
            _require_tier(value)
        updates.append(f"{key} = ?")
        params.append(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No editable subscription fields supplied")
    updates.append("updated_at = ?")
    params.append(_now())
    params.append(subscription_id)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        existing = conn.execute("SELECT * FROM vo_subscriptions WHERE id = ?", (subscription_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="VendorOps subscription not found")
        conn.execute(f"UPDATE vo_subscriptions SET {', '.join(updates)} WHERE id = ?", tuple(params))
        _audit(conn, "subscription_updated", "subscription", subscription_id, actor="founder", metadata=fields)
        conn.execute("DELETE FROM vo_renewal_alerts WHERE subscription_id = ? AND reviewed_at IS NULL", (subscription_id,))
        _generate_alerts(conn)
        return {"subscription": _serialize_row(conn.execute("SELECT * FROM vo_subscriptions WHERE id = ?", (subscription_id,)).fetchone())}


@router.get("/renewal-alerts")
def get_renewal_alerts(days: int = Query(30, ge=1, le=90), include_reviewed: bool = False):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        _generate_alerts(conn)
        cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        query = """
            SELECT * FROM vo_renewal_alerts
            WHERE datetime(renewal_date) <= datetime(?)
        """
        params: list[Any] = [cutoff]
        if not include_reviewed:
            query += " AND reviewed_at IS NULL"
        query += " ORDER BY CASE alert_type WHEN 'overdue' THEN 0 WHEN '1_day' THEN 1 WHEN '7_day' THEN 2 ELSE 3 END, datetime(renewal_date) ASC"
        rows = _list_rows(conn, query, tuple(params))
        return {"window_days": days, "alerts": rows}


@router.post("/renewal-alerts/generate")
def generate_renewal_alerts():
    with get_db() as conn:
        _init_vendorops_schema(conn)
        alerts = _generate_alerts(conn)
        _audit(conn, "renewal_alerts_generated", "alert", "batch", metadata={"count": len(alerts), "delivery": "queued_not_sent"})
        return {
            "alerts": alerts,
            "delivery_truth": "Dashboard alerts are durable. Telegram/email delivery is queued_not_sent until dedicated delivery is wired.",
        }


@router.patch("/renewal-alerts/{alert_id}/review")
def review_renewal_alert(alert_id: str, payload: FounderConfirmation):
    _require_confirmation(payload.explicit_founder_confirmation)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        row = conn.execute("SELECT * FROM vo_renewal_alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="VendorOps renewal alert not found")
        now = _now()
        conn.execute(
            "UPDATE vo_renewal_alerts SET delivery_status = 'reviewed', reviewed_at = ?, updated_at = ? WHERE id = ?",
            (now, now, alert_id),
        )
        _audit(conn, "renewal_alert_reviewed", "alert", alert_id, actor=payload.actor, metadata={"subscription_id": row["subscription_id"]})
        return {"alert": _serialize_row(conn.execute("SELECT * FROM vo_renewal_alerts WHERE id = ?", (alert_id,)).fetchone())}


@router.post("/subscriptions/{subscription_id}/cancel")
def request_cancellation(subscription_id: str, payload: FounderConfirmation):
    _require_confirmation(payload.explicit_founder_confirmation)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        row = conn.execute("SELECT * FROM vo_subscriptions WHERE id = ?", (subscription_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="VendorOps subscription not found")
        conn.execute(
            "UPDATE vo_subscriptions SET status = 'cancellation_requested', cancellation_state = 'founder_confirmed_monitoring', updated_at = ? WHERE id = ?",
            (_now(), subscription_id),
        )
        _audit(conn, "subscription_cancellation_requested", "subscription", subscription_id, actor=payload.actor, metadata={"monitoring": True})
        return {"subscription": _serialize_row(conn.execute("SELECT * FROM vo_subscriptions WHERE id = ?", (subscription_id,)).fetchone())}


@router.get("/audit")
def list_audit_events(limit: int = Query(50, ge=1, le=200)):
    with get_db() as conn:
        _init_vendorops_schema(conn)
        return {"events": _list_rows(conn, "SELECT * FROM vo_audit_events ORDER BY id DESC LIMIT ?", (limit,))}
