"""Stripe TEST / sandbox checkout for BusinessOps packages.

Hard rules:
  - TEST / sandbox keys only (`sk_test_`, `rk_test_`). Live keys are refused.
  - pkg_founder is never sold.
  - Checkout Sessions use mode=subscription.
  - Never pass payment_method_types (dynamic payment methods).
  - Fulfillment belongs in the webhook, not the success page.

Inline `price_data` is used when a Dashboard price id is not configured so
local TEST checkout still works without live catalog writes.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Optional

from fastapi import HTTPException

from app.services.business.ids import new_id
from app.services.business.signup import NEVER_SOLD_PACKAGE_IDS, assert_sellable_package


logger = logging.getLogger("empire.businessops.stripe")

PACKAGE_PRICE_ENV = {
    "pkg_starter": "STRIPE_PRICE_STARTER",
    "pkg_growth": "STRIPE_PRICE_GROWTH",
    "pkg_empire": "STRIPE_PRICE_EMPIRE",
    "pkg_apostille_only": "STRIPE_PRICE_APOSTILLE",
}

PACKAGE_AMOUNT_CENTS = {
    "pkg_starter": 2900,
    "pkg_growth": 7900,
    "pkg_empire": 19900,
    "pkg_apostille_only": 4900,
}


def stripe_secret_key() -> str:
    return (os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY") or "").strip()


def stripe_webhook_secret() -> str:
    return (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()


def assert_test_mode_secret(secret: Optional[str] = None) -> str:
    key = (secret if secret is not None else stripe_secret_key()).strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Stripe TEST checkout is not configured — set STRIPE_SECRET_KEY to a sk_test_ / rk_test_ key",
        )
    if key.startswith("sk_live_") or key.startswith("rk_live_"):
        raise HTTPException(
            status_code=403,
            detail="BusinessOps checkout is TEST / sandbox only. Live Stripe keys are refused.",
        )
    if not (key.startswith("sk_test_") or key.startswith("rk_test_")):
        raise HTTPException(
            status_code=503,
            detail="Stripe key must be a TEST / sandbox key (sk_test_ or rk_test_)",
        )
    return key


def _import_stripe(secret: str):
    try:
        import stripe as stripe_mod
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="stripe package is not installed") from exc
    stripe_mod.api_key = secret
    return stripe_mod


def _line_item(package: dict, interval: str) -> dict:
    package_id = package["id"]
    env_name = PACKAGE_PRICE_ENV.get(package_id)
    price_id = (os.getenv(env_name) or "").strip() if env_name else ""
    if interval == "month" and price_id:
        return {"price": price_id, "quantity": 1}

    if interval == "year":
        amount = int(package.get("annual_price_usd") or 0) * 100
        if amount <= 0:
            amount = PACKAGE_AMOUNT_CENTS.get(package_id, 0) * 10
    else:
        amount = int(package.get("monthly_price_usd") or 0) * 100
        if amount <= 0:
            amount = PACKAGE_AMOUNT_CENTS.get(package_id, 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail=f"package {package_id!r} has no sellable price")
    return {
        "price_data": {
            "currency": "usd",
            "unit_amount": amount,
            "recurring": {"interval": interval},
            "product_data": {
                "name": package.get("display_name") or package_id,
                "description": (package.get("description") or "")[:500] or None,
            },
        },
        "quantity": 1,
    }


def create_subscription_checkout(
    conn: sqlite3.Connection,
    *,
    business_id: str,
    package_id: str,
    customer_email: Optional[str],
    success_url: str,
    cancel_url: str,
    interval: str = "month",
    stripe_factory=None,
) -> dict[str, Any]:
    interval = (interval or "month").lower()
    if interval not in ("month", "year"):
        raise HTTPException(status_code=400, detail="interval must be month or year")

    secret = assert_test_mode_secret()
    stripe_mod = stripe_factory(secret) if stripe_factory else _import_stripe(secret)

    business = conn.execute("SELECT * FROM bo_businesses WHERE id = ?", (business_id,)).fetchone()
    if business is None:
        raise HTTPException(status_code=404, detail=f"business {business_id!r} not found")
    package = conn.execute("SELECT * FROM bo_packages WHERE id = ?", (package_id,)).fetchone()
    if package is None:
        raise HTTPException(status_code=404, detail=f"package {package_id!r} not found")
    package = dict(package)
    assert_sellable_package(package)

    sub = conn.execute(
        """
        SELECT * FROM bo_business_subscriptions
        WHERE business_id = ? AND status IN ('pending', 'active', 'paused')
        ORDER BY created_at DESC LIMIT 1
        """,
        (business_id,),
    ).fetchone()
    if sub is None:
        raise HTTPException(status_code=400, detail="No pending subscription — complete signup first")
    if sub["package_id"] != package_id:
        raise HTTPException(
            status_code=400,
            detail=f"Pending subscription is {sub['package_id']}, not {package_id}",
        )

    tenant = conn.execute(
        "SELECT id FROM bo_tenants WHERE business_id = ?",
        (business_id,),
    ).fetchone()
    tenant_id = tenant["id"] if tenant else ""

    params = {
        "mode": "subscription",
        "line_items": [_line_item(package, interval)],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": business_id,
        "metadata": {
            "flow": "businessops_subscription",
            "business_id": business_id,
            "tenant_id": tenant_id,
            "package_id": package_id,
            "subscription_id": sub["id"],
            "interval": interval,
        },
        "subscription_data": {
            "metadata": {
                "flow": "businessops_subscription",
                "business_id": business_id,
                "tenant_id": tenant_id,
                "package_id": package_id,
                "subscription_id": sub["id"],
            }
        },
    }
    email = customer_email or business["contact_email"] or business["billing_email"]
    if email:
        params["customer_email"] = email

    try:
        session = stripe_mod.checkout.Session.create(**params)
    except Exception as exc:
        logger.error("Stripe TEST checkout failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_id = getattr(session, "id", None) or (session.get("id") if isinstance(session, dict) else None)
    checkout_url = getattr(session, "url", None) or (session.get("url") if isinstance(session, dict) else None)
    if not checkout_url:
        raise HTTPException(status_code=502, detail="Stripe did not return a checkout URL")

    conn.execute(
        """
        UPDATE bo_business_subscriptions
        SET stripe_session_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (session_id, sub["id"]),
    )
    conn.execute(
        """
        INSERT INTO bo_business_audit_events
            (id, business_id, actor, action, target_type, target_id, payload)
        VALUES (?, ?, 'system', 'checkout.session_created', 'subscription', ?, ?)
        """,
        (
            new_id("bae"),
            business_id,
            sub["id"],
            json.dumps({"stripe_session_id": session_id, "package_id": package_id, "test_mode": True}),
        ),
    )
    return {
        "checkout_url": checkout_url,
        "session_id": session_id,
        "package_id": package_id,
        "business_id": business_id,
        "tenant_id": tenant_id,
        "subscription_id": sub["id"],
        "test_mode": True,
    }


def construct_test_event(payload: bytes, signature: str, stripe_factory=None) -> dict:
    secret = assert_test_mode_secret()
    whsec = stripe_webhook_secret()
    if not whsec:
        raise HTTPException(
            status_code=503,
            detail="Webhook unavailable: STRIPE_WEBHOOK_SECRET not configured",
        )
    stripe_mod = stripe_factory(secret) if stripe_factory else _import_stripe(secret)
    try:
        event = stripe_mod.Webhook.construct_event(payload, signature or "", whsec)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc
    if isinstance(event, dict):
        return event
    if hasattr(event, "to_dict"):
        return event.to_dict()
    return {
        "id": getattr(event, "id", ""),
        "type": getattr(event, "type", ""),
        "data": {"object": getattr(getattr(event, "data", None), "object", {})},
    }


def _session_object(event: dict) -> dict:
    data = event.get("data") or {}
    obj = data.get("object") or {}
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return dict(obj) if obj else {}


def _activate_subscription(
    conn: sqlite3.Connection,
    *,
    business_id: str,
    stripe_subscription_id: Optional[str],
    stripe_customer_id: Optional[str],
    stripe_session_id: Optional[str],
    source: str,
) -> dict:
    sub = conn.execute(
        """
        SELECT * FROM bo_business_subscriptions
        WHERE business_id = ? AND status IN ('pending', 'active', 'paused')
        ORDER BY created_at DESC LIMIT 1
        """,
        (business_id,),
    ).fetchone()
    if sub is None:
        return {"applied": False, "reason": "no_pending_subscription"}
    conn.execute(
        """
        UPDATE bo_business_subscriptions
        SET status = 'active',
            activated_at = COALESCE(activated_at, CURRENT_TIMESTAMP),
            current_period_start = CURRENT_TIMESTAMP,
            stripe_subscription_id = COALESCE(?, stripe_subscription_id),
            stripe_customer_id = COALESCE(?, stripe_customer_id),
            stripe_session_id = COALESCE(?, stripe_session_id),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (stripe_subscription_id, stripe_customer_id, stripe_session_id, sub["id"]),
    )
    conn.execute(
        """
        UPDATE bo_businesses
        SET status = 'active',
            activated_at = COALESCE(activated_at, CURRENT_TIMESTAMP),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (business_id,),
    )
    conn.execute(
        """
        UPDATE bo_provisioning_checklists
        SET completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
            completed_by = COALESCE(completed_by, 'stripe')
        WHERE business_id = ? AND step_key = 'payment_or_contract'
        """,
        (business_id,),
    )
    conn.execute(
        """
        INSERT INTO bo_business_audit_events
            (id, business_id, actor, action, target_type, target_id, payload)
        VALUES (?, ?, 'stripe', 'subscription.activated', 'subscription', ?, ?)
        """,
        (
            new_id("bae"),
            business_id,
            sub["id"],
            json.dumps({"source": source, "stripe_subscription_id": stripe_subscription_id}),
        ),
    )
    return {"applied": True, "subscription_id": sub["id"], "business_id": business_id}


def _cancel_subscription(conn: sqlite3.Connection, *, stripe_subscription_id: str, source: str) -> dict:
    sub = conn.execute(
        "SELECT * FROM bo_business_subscriptions WHERE stripe_subscription_id = ?",
        (stripe_subscription_id,),
    ).fetchone()
    if sub is None:
        return {"applied": False, "reason": "subscription_not_found"}
    conn.execute(
        """
        UPDATE bo_business_subscriptions
        SET status = 'canceled',
            canceled_at = CURRENT_TIMESTAMP,
            cancellation_reason = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (source, sub["id"]),
    )
    conn.execute(
        """
        UPDATE bo_businesses
        SET status = 'canceled',
            canceled_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (sub["business_id"],),
    )
    return {"applied": True, "subscription_id": sub["id"], "business_id": sub["business_id"]}


def process_stripe_event(conn: sqlite3.Connection, event: dict) -> dict[str, Any]:
    event_id = event.get("id") or new_id("evt")
    event_type = event.get("type") or ""
    existing = conn.execute(
        "SELECT event_id, result FROM bo_stripe_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    if existing:
        return {"duplicate": True, "event_id": event_id, "result": existing["result"]}

    obj = _session_object(event)
    result: dict[str, Any] = {"event_type": event_type, "applied": False}

    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        payment_status = obj.get("payment_status")
        if event_type == "checkout.session.completed" and payment_status and payment_status not in ("paid", "no_payment_required"):
            result["reason"] = f"payment_status={payment_status}"
        else:
            metadata = obj.get("metadata") or {}
            business_id = obj.get("client_reference_id") or metadata.get("business_id")
            if not business_id:
                result["reason"] = "missing_business_id"
            else:
                result = _activate_subscription(
                    conn,
                    business_id=business_id,
                    stripe_subscription_id=obj.get("subscription"),
                    stripe_customer_id=obj.get("customer"),
                    stripe_session_id=obj.get("id"),
                    source=event_type,
                )
                result["event_type"] = event_type
    elif event_type == "customer.subscription.deleted":
        sub_id = obj.get("id")
        result = _cancel_subscription(conn, stripe_subscription_id=sub_id, source=event_type) if sub_id else result
        result["event_type"] = event_type
    elif event_type == "invoice.payment_failed":
        parent = (obj.get("parent") or {}).get("subscription_details") or {}
        sub_id = obj.get("subscription") or parent.get("subscription")
        if sub_id:
            conn.execute(
                """
                UPDATE bo_business_subscriptions
                SET status = 'paused', updated_at = CURRENT_TIMESTAMP
                WHERE stripe_subscription_id = ? AND status = 'active'
                """,
                (sub_id,),
            )
            result = {"applied": True, "event_type": event_type, "stripe_subscription_id": sub_id}
    elif event_type in ("customer.subscription.updated", "invoice.paid"):
        result = {"applied": True, "event_type": event_type, "ignored_detail": "status_sync"}
    else:
        result = {"applied": False, "event_type": event_type, "ignored": True}

    conn.execute(
        """
        INSERT INTO bo_stripe_events
            (event_id, event_type, business_id, stripe_session_id, result, payload_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            event_type,
            obj.get("client_reference_id") or (obj.get("metadata") or {}).get("business_id"),
            obj.get("id") if obj.get("object") == "checkout.session" else None,
            json.dumps(result),
            json.dumps({"type": event_type, "object": obj.get("object")}),
        ),
    )
    return {"duplicate": False, "event_id": event_id, "result": result}


# Silence unused import lint for NEVER_SOLD — used by tests via re-export
__all__ = [
    "PACKAGE_AMOUNT_CENTS",
    "PACKAGE_PRICE_ENV",
    "NEVER_SOLD_PACKAGE_IDS",
    "assert_test_mode_secret",
    "construct_test_event",
    "create_subscription_checkout",
    "process_stripe_event",
    "stripe_secret_key",
    "stripe_webhook_secret",
]
