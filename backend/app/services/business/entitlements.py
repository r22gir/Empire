"""
BusinessOps entitlement helper (Phase 1).

Source of truth: REPORT-businessops-tenantops-design.md §2.5 and §8,
and REPORT-businessops-design-decisions.md D8 / D9.

Public API:
  check_entitlement(business_id, module_id, action, actor_role=None)
  -> dict

Return shape (per design doc gate summary):
  {
      "allowed": bool,
      "access_level": str,   # one of: none, preview, internal, standard, full, founder_only
      "requires_approval": bool,
      "limits": dict,        # parsed from module_entitlements.limits JSON
      "reason": str,         # human-readable; safe to surface in API responses
  }

Access level semantics (per design doc §2.5):
  none         - module is hidden from this business; refuses
  preview      - read-only / sample data
  internal     - founder's own staff, not exposed to customer
  standard     - customer's own users, with limits
  full         - usable without limits (Founder-tier on pkg_founder)
  founder_only - only the founder can use it on behalf of this business

Rules enforced here:
  - 'none' refuses, always
  - 'founder_only' refuses unless actor_role is Founder/admin equivalent
  - requires_approval actions are flagged in the response; the caller
    decides whether to proceed. The helper returns allowed=True and the
    caller is responsible for the approval gate. (See design doc §8:
    "blocks unauthorized module use".)
  - No module should auto-publish through this helper in v1.
    action='auto_publish' is refused for any non-Founder actor,
    even on 'full' / 'founder_only'.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


# Allowed access levels (mirrors the CheckConstraint in business.py)
_ACCESS_LEVELS = (
    "none", "preview", "internal", "standard", "full", "founder_only",
)

# Actor roles that can act on founder_only modules.
# In v1 there is no customer auth — actor_role is a parameter the
# caller (e.g. MAX desk router, a Founder-only admin endpoint) supplies.
# A real "customer_contact" actor never satisfies founder_only.
_FOUNDER_EQUIVALENT_ROLES = frozenset({
    "founder",
    "admin",
    "owner",          # business_users.role='owner' is also Founder-side
    "system",         # system-initiated actions are Founder-mediated
})

# Actions that are never allowed through the helper in v1.
# Auto-publish is the #1 accidental-revenue risk per
# REPORT-module-widget-crosswalk.md top risk #5.
# Decision D8: blocked by default for every business.
_REFUSED_ACTIONS = frozenset({
    "auto_publish",
    "self_heal",
    "git_operations",
    "max_code_mode",
})


def _parse_limits(limits_raw: Any) -> dict:
    """Parse the limits JSON column safely. Returns {} on missing/invalid."""
    if not limits_raw:
        return {}
    if isinstance(limits_raw, dict):
        return limits_raw
    try:
        return json.loads(limits_raw)
    except (TypeError, ValueError):
        return {}


def _fetch_entitlement_row(conn: sqlite3.Connection, business_id: str, module_id: str):
    """Look up the active entitlement row for (business, module).

    Joins:
      bo_business_subscriptions (active row)
      -> bo_packages
      -> bo_module_entitlements (one row per (package_id, module_id))

    Returns sqlite3.Row or None.
    """
    return conn.execute(
        """
        SELECT
            me.access_level       AS access_level,
            me.requires_approval  AS requires_approval,
            me.limits             AS limits,
            b.status              AS business_status,
            bs.status             AS subscription_status,
            p.is_internal         AS package_is_internal
        FROM bo_module_entitlements me
        JOIN bo_packages p
          ON p.id = me.package_id
        JOIN bo_business_subscriptions bs
          ON bs.package_id = p.id
        JOIN bo_businesses b
          ON b.id = bs.business_id
        WHERE b.id = ?
          AND me.module_id = ?
          AND bs.status IN ('active', 'paused')
        ORDER BY bs.activated_at DESC
        LIMIT 1
        """,
        (business_id, module_id),
    ).fetchone()


def check_entitlement(
    business_id: str,
    module_id: str,
    action: str,
    actor_role: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """Check whether `actor_role` can perform `action` against `module_id`
    on behalf of `business_id`.

    Parameters
    ----------
    business_id : str
        The customer's organization id. May be the founder's
        `biz_founder_default` sentinel.
    module_id : str
        The module being accessed. Must match a `bo_module_entitlements.module_id`
        value (e.g. 'apostapp', 'vendorops', 'socialforge', 'workroom').
    action : str
        The action being attempted (e.g. 'create_order', 'publish_post',
        'view_status', 'auto_publish'). Use 'auto_publish' for any
        SocialForge publish action that is not Founder-clicked.
    actor_role : str, optional
        The role of the caller. One of:
          - 'founder' / 'admin' / 'owner' / 'system' (Founder-equivalent)
          - 'member' / 'customer_contact' / 'vendor' (non-Founder)
          - None (unknown caller; treated as non-Founder)
    conn : sqlite3.Connection, optional
        A live connection. Required — pass `app.db.database.get_db()`
        or a test connection. The helper does NOT open its own
        connection (per project pattern of single-conn-per-request).

    Returns
    -------
    dict
        {allowed, access_level, requires_approval, limits, reason}
    """
    if conn is None:
        return {
            "allowed": False,
            "access_level": "none",
            "requires_approval": False,
            "limits": {},
            "reason": "no_db_connection_passed",
        }

    # 1. Refuse auto-publish and other v1-blocked actions for any
    #    non-Founder caller. This is the D8 guard.
    if action in _REFUSED_ACTIONS and actor_role not in _FOUNDER_EQUIVALENT_ROLES:
        return {
            "allowed": False,
            "access_level": "none",
            "requires_approval": True,
            "limits": {},
            "reason": f"action '{action}' is v1-blocked for non-Founder actors (D8)",
        }

    # 2. Look up the entitlement row.
    row = _fetch_entitlement_row(conn, business_id, module_id)
    if row is None:
        return {
            "allowed": False,
            "access_level": "none",
            "requires_approval": False,
            "limits": {},
            "reason": (
                f"no entitlement row for (business_id={business_id}, "
                f"module_id={module_id})"
            ),
        }

    access_level = row["access_level"]
    requires_approval = bool(row["requires_approval"])
    limits = _parse_limits(row["limits"])

    # 3. Apply access-level rules.
    if access_level == "none":
        return {
            "allowed": False,
            "access_level": "none",
            "requires_approval": False,
            "limits": {},
            "reason": (
                f"module '{module_id}' is not in package for business '{business_id}'"
            ),
        }

    if access_level == "founder_only":
        if actor_role in _FOUNDER_EQUIVALENT_ROLES:
            return {
                "allowed": True,
                "access_level": "founder_only",
                "requires_approval": False,  # founder_only is already the gate
                "limits": limits,
                "reason": "founder_only access (Founder-equivalent actor)",
            }
        return {
            "allowed": False,
            "access_level": "founder_only",
            "requires_approval": False,
            "limits": {},
            "reason": (
                f"module '{module_id}' is founder_only; "
                f"actor_role={actor_role!r} is not Founder-equivalent"
            ),
        }

    if access_level == "internal":
        # Internal is for the founder's own staff; non-Founder refused.
        if actor_role in _FOUNDER_EQUIVALENT_ROLES:
            return {
                "allowed": True,
                "access_level": "internal",
                "requires_approval": requires_approval,
                "limits": limits,
                "reason": "internal access (Founder-equivalent actor)",
            }
        return {
            "allowed": False,
            "access_level": "internal",
            "requires_approval": False,
            "limits": {},
            "reason": f"module '{module_id}' is internal; non-Founder refused",
        }

    # 4. preview / standard / full — all allow the action subject to
    #    requires_approval.
    return {
        "allowed": True,
        "access_level": access_level,
        "requires_approval": requires_approval,
        "limits": limits,
        "reason": (
            f"{access_level} access"
            + (" (requires_approval=True; caller must enforce approval gate)" if requires_approval else "")
        ),
    }


__all__ = [
    "check_entitlement",
    "_ACCESS_LEVELS",
    "_FOUNDER_EQUIVALENT_ROLES",
    "_REFUSED_ACTIONS",
]
