from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_relist_root_is_canonical_active_manifest():
    res = client.get("/api/v1/relist")

    assert res.status_code == 200
    data = res.json()
    assert data["canonical"] is True
    assert data["scope"] == "drop_ship_arbitrage"
    assert "ra_source_products" in data["storage_tables"]
    assert "/api/v1/relist/listings" in data["active_paths"]
    assert data["legacy_path"] == "/api/v1/relist-legacy"


def test_legacy_relist_crud_is_quarantined_under_legacy_prefix():
    legacy = client.get("/api/v1/relist-legacy")
    active_listing_collection = client.get("/api/v1/relist/listings")

    assert legacy.status_code == 200
    assert active_listing_collection.status_code == 200
