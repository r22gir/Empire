"""RelistApp sandbox sale detection — never touches live ra_* tables."""
import os

from app.services import relist_sale_detection as sbx


def _iso_db(tmp_path, monkeypatch):
    db = tmp_path / "relist_sandbox.db"
    monkeypatch.setenv("EMPIRE_RELIST_SANDBOX_DB", str(db))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    return db


def test_owner_confirm_queues_sibling_delist(tmp_path, monkeypatch):
    _iso_db(tmp_path, monkeypatch)
    sbx.update_settings(owner_confirm_required=True)
    ebay = sbx.upsert_listing(source_product_id="sku-1", platform="ebay", title="Lamp")
    posh = sbx.upsert_listing(source_product_id="sku-1", platform="poshmark", title="Lamp")
    sbx.upsert_listing(source_product_id="sku-2", platform="mercari", title="Other")

    result = sbx.record_sale(ebay["id"], sale_price=42)

    assert result["sandbox"] is True
    assert result["marketplace_write"] is False
    assert result["live_tables_written"] is False
    assert result["owner_confirm_required"] is True
    assert len(result["siblings"]) == 1
    assert result["siblings"][0]["listing_id"] == posh["id"]
    assert result["siblings"][0]["status"] == "pending_owner"

    listings = {row["id"]: row for row in sbx.list_listings()}
    assert listings[ebay["id"]]["status"] == "sold"
    assert listings[posh["id"]]["status"] == "active"  # waiting on owner


def test_auto_delist_when_owner_confirm_off(tmp_path, monkeypatch):
    _iso_db(tmp_path, monkeypatch)
    sbx.update_settings(owner_confirm_required=False)
    ebay = sbx.upsert_listing(source_product_id="sku-9", platform="ebay", title="Chair")
    fb = sbx.upsert_listing(source_product_id="sku-9", platform="facebook_marketplace", title="Chair")

    result = sbx.record_sale(ebay["id"], sale_price=80)
    assert result["siblings"][0]["status"] == "delisted_sandbox"
    listings = {row["id"]: row for row in sbx.list_listings()}
    assert listings[fb["id"]]["status"] == "delisted"
    assert listings[fb["id"]]["delisted_at"]


def test_owner_can_confirm_or_reject(tmp_path, monkeypatch):
    _iso_db(tmp_path, monkeypatch)
    sbx.update_settings(True)
    a = sbx.upsert_listing(source_product_id="s", platform="etsy", title="Vase")
    b = sbx.upsert_listing(source_product_id="s", platform="mercari", title="Vase")
    sale = sbx.record_sale(a["id"])
    event_id = sale["siblings"][0]["id"]

    confirmed = sbx.resolve_confirmation(event_id, approve=True)
    assert confirmed["marketplace_write"] is False
    assert confirmed["status"] == "delisted_sandbox"
    listings = {row["id"]: row for row in sbx.list_listings()}
    assert listings[b["id"]]["status"] == "delisted"


def test_settings_cannot_leave_sandbox(tmp_path, monkeypatch):
    _iso_db(tmp_path, monkeypatch)
    settings = sbx.update_settings(False)
    assert settings["sandbox_mode"] is True
    assert settings["live_marketplace_writes"] is False


def test_snapshot_does_not_require_live_db(tmp_path, monkeypatch):
    _iso_db(tmp_path, monkeypatch)
    created = sbx.snapshot_from_live_rows([
        {"id": 101, "source_product_id": 7, "platform": "ebay", "title": "Copy", "status": "active"},
    ])
    assert len(created) == 1
    assert created[0]["snapshot_from_listing_id"] == 101
    assert created[0]["source_product_id"] == "7"
