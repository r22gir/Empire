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
    approval_id: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)
    credential_ref: str = Field(min_length=4)
    credential_owner: str = "founder"
    assisted_signup_state: str = "take_me_to_last_page_ready"
    explicit_founder_confirmation: bool


class SubscriptionCreate(BaseModel):
    tier: TierName = "free"
    vendor_name: str = Field(min_length=1)
    plan_name: str = Field(min_length=1)
    renewal_date: str = Field(description="ISO date/datetime")
    license_ref: str | None = None
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
            tier TEXT NOT NULL,
            account_status TEXT NOT NULL,
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
        """
    )


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
    _require_tier(tier)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        pending = conn.execute("SELECT COUNT(*) AS count FROM vo_approvals WHERE status = 'pending'").fetchone()["count"]
        accounts = _count(conn, "vo_accounts", tier)
        subscriptions = _count(conn, "vo_subscriptions", tier)
        return {
            "status": "active",
            "surface": "standalone_vendorops_add_on",
            "tier": tier,
            "limits": TIERS[tier],
            "pending_approvals": pending,
            "accounts_used": accounts,
            "subscriptions_used": subscriptions,
            "max_can_query": True,
            "max_can_write": False,
            "credential_policy": "credential_ref_only_hash_stored_no_plaintext",
        }


@router.get("/max-summary")
def get_vendorops_max_summary(tier: TierName = Query("free")):
    status = get_vendorops_status(tier=tier)
    return {
        "vendorops": status,
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


@router.post("/accounts")
def create_account(payload: AccountCreate):
    _require_confirmation(payload.explicit_founder_confirmation)
    _reject_plaintext_credential_fields(payload)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        _enforce_limit(conn, payload.tier, "vo_accounts", "account_limit")
        approval = conn.execute("SELECT * FROM vo_approvals WHERE id = ?", (payload.approval_id,)).fetchone()
        if not approval:
            raise HTTPException(status_code=404, detail="VendorOps approval not found")
        if approval["status"] != "approved" or not approval["founder_confirmed"]:
            raise HTTPException(status_code=403, detail="Approved founder confirmation is required before provisioning")
        account_id = _new_id("voacct")
        now = _now()
        trail = {
            "approval_id": payload.approval_id,
            "verification_boundary": approval["verification_boundary"],
            "assisted_signup_state": payload.assisted_signup_state,
            "external_action_status": "founder_confirmed_ready_for_assisted_signup",
        }
        conn.execute(
            """
            INSERT INTO vo_accounts
            (id, approval_id, vendor_name, tier, account_status, credential_ref_hash, credential_ref_masked,
             credential_owner, assisted_signup_state, provisioning_trail, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'provisioning_ready', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                payload.approval_id,
                payload.vendor_name,
                payload.tier,
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
            (id, vendor_name, plan_name, tier, status, license_ref_masked, renewal_date, cancellation_state, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, 'active_monitoring', ?, ?)
            """,
            (sub_id, payload.vendor_name, payload.plan_name, payload.tier, _mask_ref(payload.license_ref), payload.renewal_date, now, now),
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


@router.get("/renewal-alerts")
def get_renewal_alerts(days: int = Query(14, ge=1, le=90)):
    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    with get_db() as conn:
        _init_vendorops_schema(conn)
        rows = _list_rows(
            conn,
            "SELECT * FROM vo_subscriptions WHERE status = 'active' AND datetime(renewal_date) <= datetime(?) ORDER BY datetime(renewal_date) ASC",
            (cutoff.isoformat(),),
        )
        return {"window_days": days, "alerts": rows}


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
