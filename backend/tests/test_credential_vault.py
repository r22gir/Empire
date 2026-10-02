"""Credential vault seals social_accounts tokens and stays founder-only."""
from __future__ import annotations

import json
import logging
import sqlite3

import pytest
from cryptography.fernet import Fernet

from app.services.accounts.founder import FounderAuthError, assert_founder
from app.services.accounts.store import connect
from app.services.accounts.vault import (
    Vault,
    VaultNotConfigured,
    migrate_plaintext_social_tokens,
    open_secret,
    redact_account,
)


def test_vault_refuses_to_start_without_a_key(monkeypatch):
    monkeypatch.delenv("EMPIRE_VAULT_KEY", raising=False)
    with pytest.raises(VaultNotConfigured):
        Vault()


def test_vault_refuses_a_bad_key(monkeypatch):
    monkeypatch.setenv("EMPIRE_VAULT_KEY", "not-a-fernet-key")
    with pytest.raises(VaultNotConfigured):
        Vault()


def test_plaintext_social_tokens_move_into_the_vault(monkeypatch, tmp_path, caplog):
    db_path = tmp_path / "empire.db"
    monkeypatch.setenv("EMPIRE_DB", str(db_path))
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("EMPIRE_VAULT_KEY", key)
    secret = "page-token-do-not-leak"
    conn = connect()
    conn.execute(
        """
        CREATE TABLE social_accounts (
            id INTEGER PRIMARY KEY,
            business_unit TEXT,
            platform TEXT,
            access_token TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO social_accounts (business_unit, platform, access_token) VALUES ('workroom', 'facebook', ?)",
        (secret,),
    )
    conn.commit()
    vault = Vault()
    with caplog.at_level(logging.DEBUG):
        moved = migrate_plaintext_social_tokens(conn, vault)
    assert moved == 1
    stored = conn.execute("SELECT access_token FROM social_accounts").fetchone()[0]
    assert stored == "vault:social:workroom:facebook"
    assert secret not in db_path.read_bytes().decode("utf-8", "ignore")
    assert secret not in caplog.text
    opened = open_secret(conn, vault, "social:workroom:facebook")
    assert opened == secret
    public = redact_account({"business_unit": "workroom", "access_token": stored, "status": "connected"})
    assert "access_token" not in public
    assert secret not in json.dumps(public)
    conn.close()


def test_founder_gate_rejects_a_missing_or_wrong_pin(monkeypatch):
    monkeypatch.delenv("FOUNDER_PIN", raising=False)
    with pytest.raises(FounderAuthError) as missing:
        assert_founder("1234")
    assert missing.value.status_code == 503
    monkeypatch.setenv("FOUNDER_PIN", "246810")
    with pytest.raises(FounderAuthError) as wrong:
        assert_founder("0000")
    assert wrong.value.status_code == 403
    assert "246810" not in wrong.value.detail
    assert_founder("246810")


def test_second_migration_does_not_reseal(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_VAULT_KEY", Fernet.generate_key().decode())
    conn = connect()
    conn.execute(
        """
        CREATE TABLE social_accounts (
            id INTEGER PRIMARY KEY, business_unit TEXT, platform TEXT, access_token TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO social_accounts (business_unit, platform, access_token) VALUES ('woodcraft', 'instagram', 'tok')"
    )
    conn.commit()
    vault = Vault()
    assert migrate_plaintext_social_tokens(conn, vault) == 1
    assert migrate_plaintext_social_tokens(conn, vault) == 0
    conn.close()
