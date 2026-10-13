"""Test-mode-only Stripe Checkout helper for ApostApp public intake.

This module never accepts a live Stripe secret key. Public ApostApp checkout
is Stripe test mode only — real charges are out of scope for this surface.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("empire.apostapp.checkout")

APOSTAPP_PUBLIC_HOST = "apostapp.empirebox.store"


class LiveStripeKeyRefused(ValueError):
    """Raised when a live Stripe key is presented to the public checkout."""


def stripe_key_mode(key: Optional[str] = None) -> str:
    """Return missing | test | live | unknown for a Stripe secret key."""
    secret = key if key is not None else os.getenv("STRIPE_SECRET_KEY", "")
    if not secret:
        return "missing"
    if secret.startswith("sk_live_"):
        return "live"
    if secret.startswith("sk_test_"):
        return "test"
    return "unknown"


def refuse_live_stripe_key(key: Optional[str] = None) -> None:
    if stripe_key_mode(key) == "live":
        raise LiveStripeKeyRefused(
            "ApostApp public checkout is test-mode only; live Stripe keys are refused"
        )


def default_success_url(order_id: str) -> str:
    return (
        f"https://{APOSTAPP_PUBLIC_HOST}/apostille/confirmation"
        f"?order_id={order_id}&session_id={{CHECKOUT_SESSION_ID}}"
    )


def default_cancel_url(order_id: str) -> str:
    return f"https://{APOSTAPP_PUBLIC_HOST}/apostille?canceled=1&order_id={order_id}"


def create_test_checkout_session(
    *,
    order_id: str,
    package_id: str,
    amount_cents: int,
    customer_email: Optional[str] = None,
    stripe_client: Any = None,
) -> dict:
    """Create a Stripe Checkout session using a test key only.

    If no test key is configured and no client is injected, intake still
    succeeds and checkout_available is False. A live key always errors.
    """
    refuse_live_stripe_key()
    mode = stripe_key_mode()
    if stripe_client is None and mode != "test":
        logger.info("ApostApp checkout skipped — no sk_test_ key configured")
        return {
            "checkout_url": None,
            "session_id": None,
            "checkout_available": False,
            "reason": "stripe_test_key_missing",
            "test_mode": True,
        }

    client = stripe_client
    if client is None:
        try:
            import stripe as stripe_mod
        except ImportError:
            return {
                "checkout_url": None,
                "session_id": None,
                "checkout_available": False,
                "reason": "stripe_sdk_missing",
                "test_mode": True,
            }
        stripe_mod.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        client = stripe_mod

    session = client.checkout.Session.create(
        mode="payment",
        customer_email=customer_email or None,
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": f"Apostille — Order {order_id}",
                        "description": (
                            f"EmpireBox Apostille Fast Lane — {package_id} package (TEST MODE)"
                        ),
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=default_success_url(order_id),
        cancel_url=default_cancel_url(order_id),
        metadata={
            "apostille_order_id": order_id,
            "apostille_package_id": package_id,
            "flow": "apostille_one_time",
            "test_mode": "1",
        },
    )
    return {
        "checkout_url": getattr(session, "url", None) or session.get("url"),
        "session_id": getattr(session, "id", None) or session.get("id"),
        "checkout_available": True,
        "reason": None,
        "test_mode": True,
    }
