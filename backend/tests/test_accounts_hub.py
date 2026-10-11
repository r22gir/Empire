"""SocialForge accounts hub lists every platform for every business."""
from __future__ import annotations

import json

from app.services.accounts.catalog import OWNER, PLATFORMS
from app.services.accounts.store import connect, list_hub


def test_hub_lists_every_platform_for_each_business(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.delenv("META_APP_ID", raising=False)
    monkeypatch.delenv("META_APP_SECRET", raising=False)
    monkeypatch.delenv("PINTEREST_APP_ID", raising=False)
    monkeypatch.delenv("PINTEREST_APP_SECRET", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ETSY_CLIENT_ID", raising=False)
    conn = connect()
    try:
        hub = list_hub(conn)
    finally:
        conn.close()

    assert hub["owner"] == OWNER == "socialforge"
    businesses = {item["key"] for item in hub["businesses"]}
    assert businesses == {"workroom", "woodcraft"}
    kinds = {spec.kind for spec in PLATFORMS}
    assert kinds == {"social", "marketplace", "email", "directory", "canva", "domain_email"}
    assert len(hub["accounts"]) == len(PLATFORMS) * 2

    blob = json.dumps(hub)
    assert "access_token" not in blob
    assert "client_secret" not in blob
    for account in hub["accounts"]:
        assert account["owner"] == "socialforge"
        assert "last_sync_at" in account
        assert account["auto_publish"] is False
        assert set(account) == {
            "id", "business_key", "platform", "kind", "display_name", "status",
            "owner", "last_sync_at", "auto_publish", "has_credentials", "external_account_id",
        }

    by_id = {account["id"]: account for account in hub["accounts"]}
    assert by_id["workroom:facebook"]["status"] == "needs_keys"
    assert by_id["woodcraft:instagram"]["kind"] == "social"
    assert by_id["workroom:etsy"]["status"] == "needs_keys"
    assert by_id["workroom:ebay"]["status"] == "not_connected"
    assert by_id["workroom:canva"]["kind"] == "canva"
    assert by_id["woodcraft:domain_email"]["kind"] == "domain_email"
    assert by_id["workroom:business_email"]["kind"] == "email"
    assert by_id["workroom:houzz"]["kind"] == "directory"
