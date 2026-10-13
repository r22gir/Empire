"""Tenant data isolation helpers.

A tenant is 1:1 with a business. Customer-scoped reads must pass
`tenant_id` (header `X-Empire-Tenant-Id` or query). A mismatch is a
404 so we do not leak whether the other tenant exists.

Unscoped founder/admin list endpoints stay available when no tenant
id is provided (Phase 1 compatibility). Passing a tenant id always
narrows the result set.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import HTTPException, Request


TENANT_HEADER = "X-Empire-Tenant-Id"


def tenant_id_from_request(request: Request, query_tenant_id: Optional[str] = None) -> Optional[str]:
    if query_tenant_id:
        return query_tenant_id.strip()
    header = request.headers.get(TENANT_HEADER) if request is not None else None
    if header:
        return header.strip()
    return None


def resolve_tenant(conn: sqlite3.Connection, tenant_id: str) -> dict:
    row = conn.execute(
        """
        SELECT t.id AS tenant_id, t.business_id, t.slug, t.isolation_key, t.status,
               b.display_name, b.status AS business_status
        FROM bo_tenants t
        JOIN bo_businesses b ON b.id = t.business_id
        WHERE t.id = ?
        """,
        (tenant_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    return dict(row)


def resolve_tenant_business_id(conn: sqlite3.Connection, tenant_id: Optional[str]) -> Optional[str]:
    """If tenant_id is set, return its business_id or 404. Unscoped → None."""
    if not tenant_id:
        return None
    tenant = resolve_tenant(conn, tenant_id)
    return tenant["business_id"]


def assert_tenant_owns_business(conn: sqlite3.Connection, tenant_id: Optional[str], business_id: str) -> None:
    scoped = resolve_tenant_business_id(conn, tenant_id)
    if scoped is None:
        return
    if scoped != business_id:
        raise HTTPException(status_code=404, detail="business not found")


def assert_tenant_owns_subscription(
    conn: sqlite3.Connection, tenant_id: Optional[str], subscription_id: str
) -> dict:
    row = conn.execute(
        "SELECT * FROM bo_business_subscriptions WHERE id = ?",
        (subscription_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"subscription {subscription_id!r} not found")
    assert_tenant_owns_business(conn, tenant_id, row["business_id"])
    return dict(row)
