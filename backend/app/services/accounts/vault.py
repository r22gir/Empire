"""Credential vault. Refuses to start unless EMPIRE_VAULT_KEY is a Fernet key.

Ciphertext lives in ``credential_vault``. Callers pass secret ids, never
log or return the opened secret to the frontend.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken


class VaultNotConfigured(RuntimeError):
    """The vault process will not start without a usable EMPIRE_VAULT_KEY."""


class Vault:
    def __init__(self, key: str | None = None):
        raw = os.environ.get("EMPIRE_VAULT_KEY", "") if key is None else key
        raw = (raw or "").strip()
        if not raw:
            raise VaultNotConfigured(
                "EMPIRE_VAULT_KEY is unset. The credential vault will not start."
            )
        try:
            self._fernet = Fernet(raw.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise VaultNotConfigured(
                "EMPIRE_VAULT_KEY is not a valid Fernet key. The credential vault will not start."
            ) from exc

    def seal(self, secret: str) -> str:
        if secret is None:
            raise ValueError("refusing to seal an empty credential")
        return self._fernet.encrypt(secret.encode("utf-8")).decode("ascii")

    def open(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise VaultNotConfigured("Stored credential could not be opened.") from exc


def require_vault() -> Vault:
    """Start the vault or raise. Do not call this at import time."""
    return Vault()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def put_secret(conn: sqlite3.Connection, vault: Vault, secret_id: str, secret: str) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS credential_vault (
            secret_id TEXT PRIMARY KEY,
            ciphertext TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    ciphertext = vault.seal(secret)
    conn.execute(
        """
        INSERT INTO credential_vault (secret_id, ciphertext, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(secret_id) DO UPDATE SET ciphertext = excluded.ciphertext, updated_at = excluded.updated_at
        """,
        (secret_id, ciphertext, _now()),
    )
    conn.commit()


def open_secret(conn: sqlite3.Connection, vault: Vault, secret_id: str) -> str | None:
    row = conn.execute(
        "SELECT ciphertext FROM credential_vault WHERE secret_id = ?",
        (secret_id,),
    ).fetchone()
    if not row:
        return None
    return vault.open(row["ciphertext"] if isinstance(row, sqlite3.Row) else row[0])


def migrate_plaintext_social_tokens(conn: sqlite3.Connection, vault: Vault) -> int:
    """Move social_accounts.access_token into the vault and clear the plaintext.

    Rows already marked ``vault:<id>`` are left alone. Returns how many
    tokens were sealed. The plaintext value is never logged.
    """
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "social_accounts" not in tables:
        return 0
    rows = conn.execute(
        "SELECT id, business_unit, platform, access_token FROM social_accounts"
    ).fetchall()
    moved = 0
    for row in rows:
        token = row["access_token"] if isinstance(row, sqlite3.Row) else row[3]
        if not token or str(token).startswith("vault:"):
            continue
        business = row["business_unit"] if isinstance(row, sqlite3.Row) else row[1]
        platform = row["platform"] if isinstance(row, sqlite3.Row) else row[2]
        account_row_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]
        secret_id = f"social:{business}:{platform}"
        put_secret(conn, vault, secret_id, str(token))
        conn.execute(
            "UPDATE social_accounts SET access_token = ? WHERE id = ?",
            (f"vault:{secret_id}", account_row_id),
        )
        from app.services.accounts.store import mark_connected
        try:
            mark_connected(conn, str(business), str(platform), secret_id)
        except Exception:
            pass
        moved += 1
    conn.commit()
    return moved


REDACT_FIELDS = {
    "access_token",
    "refresh_token",
    "token",
    "client_secret",
    "code",
    "code_verifier",
    "ciphertext",
    "page_token",
}


def redact_account(record: dict) -> dict:
    """Copy a row for an API response with every secret field removed."""
    clean = {}
    has_credentials = False
    for key, value in record.items():
        if key in REDACT_FIELDS or "token" in key or "secret" in key or "cipher" in key:
            if value:
                has_credentials = True
            continue
        clean[key] = value
    if "has_credentials" not in clean:
        clean["has_credentials"] = has_credentials or bool(record.get("vault_secret_id"))
    return clean
