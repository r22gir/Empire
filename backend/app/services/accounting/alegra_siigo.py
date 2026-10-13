"""
Alegra / Siigo connector stub — Maxine edition, DIAN e-invoicing.

This is a sandbox-only stub. It stores local drafts and refuses every
path that would submit to DIAN, Alegra production, or Siigo production.
"""
from __future__ import annotations

import json
from typing import Optional

from app.db.database import dict_row, dict_rows
from app.services.accounting.guards import (
    ALEGRA_SANDBOX_HOSTS,
    SIIGO_SANDBOX_HOSTS,
    SandboxOnlyError,
    assert_sandbox_credentials,
    assert_sandbox_url,
    refuse_live_write,
)
from app.services.feature_flags import alegra_siigo_enabled, get_edition

PROVIDERS = frozenset({"alegra", "siigo"})

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS acct_dian_drafts (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    provider TEXT NOT NULL CHECK (provider IN ('alegra', 'siigo')),
    document_type TEXT NOT NULL DEFAULT 'invoice',
    customer_name TEXT,
    amount REAL DEFAULT 0,
    currency TEXT DEFAULT 'COP',
    payload TEXT,
    status TEXT NOT NULL DEFAULT 'local_draft',
    live_submitted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)


def require_enabled() -> None:
    if not alegra_siigo_enabled():
        raise SandboxOnlyError(
            "Alegra/Siigo DIAN connector is disabled. Enable FEATURE_ALEGRA_SIIGO "
            "on the Maxine edition (EMPIRE_EDITION=maxine).",
            403,
        )


def status_payload() -> dict:
    require_enabled()
    alegra_creds = assert_sandbox_credentials(prefix="ALEGRA", required=("TOKEN", "EMAIL"))
    siigo_creds = assert_sandbox_credentials(prefix="SIIGO", required=("USERNAME", "ACCESS_KEY"))
    alegra_base = (os_env("ALEGRA_API_BASE") or "https://api.sandbox.alegra.com")
    siigo_base = (os_env("SIIGO_API_BASE") or "https://api-sandbox.siigo.com")
    assert_sandbox_url(alegra_base, allowed_hosts=ALEGRA_SANDBOX_HOSTS, connector="alegra")
    assert_sandbox_url(siigo_base, allowed_hosts=SIIGO_SANDBOX_HOSTS, connector="siigo")
    return {
        "connector": "alegra_siigo",
        "edition": get_edition(),
        "line": "maxine",
        "mode": "sandbox_stub",
        "capability": "dian_e_invoicing",
        "live_writes": False,
        "live_submit": False,
        "dian_submit_enabled": False,
        "providers": {
            "alegra": {
                "configured": bool(alegra_creds),
                "sandbox_only": True,
                "status": "stub",
            },
            "siigo": {
                "configured": bool(siigo_creds),
                "sandbox_only": True,
                "status": "stub",
            },
        },
        "notes": (
            "Local DIAN drafts only. No CUFE, no DIAN SOAP/REST submit, "
            "no Alegra/Siigo live invoice create."
        ),
    }


def os_env(name: str) -> str:
    import os

    return (os.getenv(name) or "").strip()


def create_local_draft(
    conn,
    *,
    provider: str,
    customer_name: str,
    amount: float,
    currency: str = "COP",
    document_type: str = "invoice",
    payload: Optional[dict] = None,
) -> dict:
    require_enabled()
    ensure_schema(conn)
    provider = (provider or "").strip().lower()
    if provider not in PROVIDERS:
        raise SandboxOnlyError("provider must be alegra or siigo")
    conn.execute(
        """INSERT INTO acct_dian_drafts
           (id, provider, document_type, customer_name, amount, currency, payload, status, live_submitted)
           VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, 'local_draft', 0)""",
        (
            provider,
            document_type,
            customer_name,
            float(amount or 0),
            currency or "COP",
            json.dumps(payload or {}),
        ),
    )
    row = dict_row(
        conn.execute(
            "SELECT * FROM acct_dian_drafts ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    )
    return {
        "draft": _public(row),
        "live_submitted": False,
        "dian_cufe": None,
    }


def list_drafts(conn) -> list[dict]:
    ensure_schema(conn)
    return [_public(r) for r in dict_rows(conn.execute(
        "SELECT * FROM acct_dian_drafts ORDER BY created_at DESC"
    ).fetchall())]


def submit_to_dian(_draft_id: str) -> None:
    refuse_live_write("dian_electronic_invoice_submit", "alegra_siigo")


def push_to_provider(_draft_id: str, _provider: str) -> None:
    refuse_live_write("create_remote_invoice", "alegra_siigo")


def _public(row: dict) -> dict:
    return {
        "id": row["id"],
        "provider": row["provider"],
        "document_type": row.get("document_type"),
        "customer_name": row.get("customer_name"),
        "amount": row.get("amount"),
        "currency": row.get("currency"),
        "status": row.get("status"),
        "live_submitted": bool(row.get("live_submitted")),
        "created_at": row.get("created_at"),
    }
