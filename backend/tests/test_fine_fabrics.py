"""Empire Fine Fabrics — mock-data only. Never hits live vendors or Stripe live."""

from __future__ import annotations

import importlib
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

EXAMPLE_CSV = Path(__file__).resolve().parents[1] / "app" / "data" / "fine_fabrics" / "example_import.csv"
GREENHOUSE_CSV = Path(__file__).resolve().parents[1] / "app" / "data" / "fine_fabrics" / "greenhouse_prices.csv"
CHARLOTTE_CSV = Path(__file__).resolve().parents[1] / "app" / "data" / "fine_fabrics" / "charlotte_prices.csv"
BASE_SELECTION_CSV = Path(__file__).resolve().parents[1] / "app" / "data" / "fine_fabrics" / "base_selection_import.csv"

MOCK_CSV = """vendor,pattern,color,sku,category,width,content,repeat,net_price,list_price,product_url,notes,durability,care
Sunbrella,Canvas,Navy,5408-0000,Outdoor,54,100% Acrylic,,18.50,36.00,https://example.invalid/navy,mock,15000h,Spot clean
Sunbrella,Heritage,Charcoal,8305-0000,Upholstery,54,100% Acrylic,,22.00,44.00,https://example.invalid/charcoal,mock,30000 rubs,Mild soap
Charlotte,Cuaderno,Spruce,V639,Upholstery,54,Vinyl,,12.00,24.00,https://example.invalid/v639,mock,2M rubs,Wipe
Greenhouse,Botanical Vine,Sage,GH-BV-SAGE,Drapery,54,Linen,27x25,42.00,84.00,https://example.invalid/sage,mock,,Dry clean
"""


@pytest.fixture
def ff_db(monkeypatch, tmp_path):
    db = tmp_path / "empire.db"
    photos = tmp_path / "photos"
    photos.mkdir()
    quotes = tmp_path / "quotes"
    quotes.mkdir()
    monkeypatch.setenv("EMPIRE_TASK_DB", str(db))
    monkeypatch.setenv("EMPIRE_DB_PATH", str(db))
    monkeypatch.setenv("FINE_FABRICS_PHOTOS_DIR", str(photos))
    monkeypatch.setenv("FINE_FABRICS_SEED_DEMO", "0")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    from app.db import database
    importlib.reload(database)

    from app.services.fine_fabrics import schema, catalog, importer, checkout, photos as photo_mod, preview, shipping, seo

    for mod in (schema, catalog, importer, checkout, photo_mod, preview, shipping, seo):
        importlib.reload(mod)

    schema.ensure_fine_fabrics_schema()
    from app.routers import fine_fabrics as router_mod

    importlib.reload(router_mod)
    yield {
        "db": db,
        "photos": photos,
        "quotes": quotes,
        "schema": schema,
        "catalog": catalog,
        "importer": importer,
        "checkout": checkout,
        "photos_mod": photo_mod,
        "preview": preview,
        "shipping": shipping,
        "seo": seo,
        "router": router_mod,
    }


def _client(router_mod) -> TestClient:
    app = FastAPI()
    app.include_router(router_mod.router, prefix="/api/v1")
    return TestClient(app)


def test_example_csv_has_required_columns():
    text = EXAMPLE_CSV.read_text(encoding="utf-8")
    header = text.splitlines()[0]
    for col in (
        "vendor",
        "pattern",
        "color",
        "sku",
        "category",
        "width",
        "content",
        "repeat",
        "net_price",
        "list_price",
        "product_url",
        "notes",
    ):
        assert col in header
    greenhouse = GREENHOUSE_CSV.read_text(encoding="utf-8")
    assert "name_color" in greenhouse.splitlines()[0]
    assert "net_price_per_yd" in greenhouse
    charlotte = CHARLOTTE_CSV.read_text(encoding="utf-8")
    assert "Charlotte" in charlotte
    assert "unit per" in charlotte
    assert "collection-level" in charlotte


def test_vendor_seed_flags(ff_db):
    vendors = {v["slug"]: v for v in ff_db["catalog"].list_vendors()}
    for slug in ("charlotte", "greenhouse", "kravet", "keyston", "sunbrella"):
        assert vendors[slug]["online_sale_allowed"] is True
        assert vendors[slug]["brand_display_allowed"] is True


def _hide_vendor(ff_db, slug: str) -> None:
    from app.db.database import get_db

    vendors = {v["slug"]: v for v in ff_db["catalog"].list_vendors()}
    with get_db() as conn:
        conn.execute(
            "UPDATE ff_vendors SET online_sale_allowed=0, brand_display_allowed=0 WHERE id=?",
            (vendors[slug]["id"],),
        )


def test_import_and_public_catalog_shows_starter_mills(ff_db):
    result = ff_db["importer"].import_csv_text(MOCK_CSV)
    assert result["created"] == 4
    public = ff_db["catalog"].list_catalog()
    patterns = {p["pattern"] for p in public}
    assert {"Canvas", "Heritage", "Cuaderno", "Botanical Vine"} <= patterns
    assert all(p["category"] in ff_db["schema"].CATEGORIES for p in public)
    spruce = next(p for p in public if p["pattern"] == "Cuaderno")
    assert spruce["empire_code"] == "V639-Spruce"
    assert spruce["brand"] == "Charlotte"


def test_customer_payload_never_leaks_cost_or_vendor(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    public = ff_db["catalog"].list_catalog()
    leaks = ff_db["catalog"].leaks_cost_or_vendor(public)
    assert leaks == []
    navy = next(p for p in public if p["color"] == "Navy")
    assert navy["price_per_yard"] == round(18.50 * 1.85, 2)
    assert navy["brand"] == "Sunbrella"
    assert "net_price" not in navy
    assert "vendor_name" not in navy
    assert navy["empire_code"].startswith("L") or navy["empire_code"] == "L001-Navy"

    hidden = ff_db["catalog"].list_catalog(include_hidden=True, owner=True)
    spruce = next(p for p in hidden if p["color"] == "Spruce")
    public_spruce = ff_db["catalog"].get_product(spruce["id"], owner=False, allow_hidden=True)
    assert public_spruce["brand"] == "Charlotte"
    assert "net_price" not in public_spruce
    assert "vendor_name" not in public_spruce
    assert public_spruce["price_per_yard"] == round(12.00 * 2.2, 2)
    _hide_vendor(ff_db, "charlotte")
    hidden_spruce = ff_db["catalog"].get_product(spruce["id"], owner=False, allow_hidden=True)
    assert "brand" not in hidden_spruce
    assert "net_price" not in hidden_spruce


def test_per_category_markup_override(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    vendors = {v["slug"]: v for v in ff_db["catalog"].list_vendors()}
    from app.db.database import get_db

    with get_db() as conn:
        conn.execute(
            "INSERT INTO ff_markups (vendor_id, category, markup) VALUES (?, 'Outdoor', 3.0)",
            (vendors["sunbrella"]["id"],),
        )
    navy = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Navy")
    charcoal = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Charcoal")
    assert navy["price_per_yard"] == round(18.50 * 3.0, 2)
    assert charcoal["price_per_yard"] == round(22.00 * 1.85, 2)


def test_router_catalog_and_hidden_product_404(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    client = _client(ff_db["router"])
    catalog = client.get("/api/v1/fine-fabrics/catalog").json()["products"]
    assert len(catalog) == 4
    spruce_id = next(p["id"] for p in catalog if p["color"] == "Spruce")
    spruce = client.get(f"/api/v1/fine-fabrics/products/{spruce_id}").json()
    assert spruce["brand"] == "Charlotte"
    assert "net_price" not in spruce
    _hide_vendor(ff_db, "charlotte")
    assert client.get(f"/api/v1/fine-fabrics/products/{spruce_id}").status_code == 404
    navy_id = next(p["id"] for p in catalog if p["color"] == "Navy")
    body = client.get(f"/api/v1/fine-fabrics/products/{navy_id}").json()
    assert body["empire_code"]
    assert "net_price" not in body
    assert body["brand"] == "Sunbrella"


def test_csv_import_rejects_hand_entry_shape(ff_db):
    client = _client(ff_db["router"])
    bad = client.post(
        "/api/v1/fine-fabrics/import",
        files={"file": ("bad.csv", b"name,price\nFoo,1\n", "text/csv")},
    )
    assert bad.status_code == 400
    ok = client.post(
        "/api/v1/fine-fabrics/import",
        files={"file": ("greenhouse_prices.csv", GREENHOUSE_CSV.read_bytes(), "text/csv")},
    )
    assert ok.status_code == 200
    assert ok.json()["created"] == 3
    assert ok.json()["format"] == "greenhouse"
    greenhouse = client.get("/api/v1/fine-fabrics/catalog").json()["products"]
    assert len(greenhouse) == 3
    assert all(p.get("brand") == "Greenhouse" for p in greenhouse)


def test_owner_photo_slot_not_vendor_url(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    public = ff_db["catalog"].list_catalog()
    navy = next(p for p in public if p["color"] == "Navy")
    assert navy["placeholder"] is True
    assert navy["image_url"] is None
    client = _client(ff_db["router"])
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc``\x00\x00"
        b"\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    up = client.post(
        f"/api/v1/fine-fabrics/products/{navy['id']}/photos",
        files={"file": ("owner-swatch.png", png, "image/png")},
    )
    assert up.status_code == 200
    assert up.json()["has_owner_photo"] is True
    photo = client.get(f"/api/v1/fine-fabrics/photos/{navy['id']}")
    assert photo.status_code == 200
    assert photo.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_samples_and_preview_stub(ff_db, monkeypatch):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    navy = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Navy")
    client = _client(ff_db["router"])

    class Boom:
        def __getattr__(self, name):
            raise RuntimeError("no drawing engine")

    import sys

    monkeypatch.setitem(sys.modules, "app.routers.drawings", Boom())
    preview = client.post("/api/v1/fine-fabrics/preview", json={"product_id": navy["id"]})
    assert preview.status_code == 200
    body = preview.json()
    assert body["stub"] is True
    assert "TODO" in body["todo"]
    assert body["fabric"]["empire_code"] == navy["empire_code"]

    samples = client.post(
        "/api/v1/fine-fabrics/samples",
        json={"name": "Ada", "email": "ada@example.com", "product_ids": [navy["id"]], "notes": "two clips"},
    )
    assert samples.status_code == 200
    body = samples.json()
    assert body["product_ids"] == [navy["id"]]
    assert body["shipping_total"] >= 1
    assert body["shipping"]["never_free"] is True
    assert body["shipping"]["free_shipping"] is False
    assert "net_price" not in str(body)


def test_checkout_uses_quote_deposit_path_test_mode_only(ff_db, monkeypatch):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    navy = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Navy")
    monkeypatch.setattr(ff_db["checkout"], "_quotes_dir", lambda: ff_db["quotes"])

    captured = {}

    def fake_link(quote_id, percent=None, success_url=None, cancel_url=None):
        captured["quote_id"] = quote_id
        captured["percent"] = percent
        quote = (ff_db["quotes"] / f"{quote_id}.json").read_text()
        captured["quote"] = quote
        return {
            "invoice": {"id": "inv-ff", "invoice_stage": "deposit"},
            "pay_link": {
                "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_ff",
                "stripe_configured": True,
                "payment_status": "link_ready",
            },
            "payment_status": "link_ready",
        }

    import sys

    monkeypatch.setitem(
        sys.modules,
        "app.routers.finance",
        SimpleNamespace(create_quote_deposit_pay_link=fake_link, QUOTES_DIR=ff_db["quotes"]),
    )

    result = ff_db["checkout"].checkout_cart(
        {"name": "Ada", "email": "ada@example.com", "phone": "555", "address": "10 Yard St"},
        [{"product_id": navy["id"], "yards": 3}],
    )
    assert captured["percent"] == 100
    assert "cs_test_ff" in result["pay_link"]["checkout_url"]
    assert result["stripe_mode"] == "test"
    assert result["subtotal"] == round(3 * navy["price_per_yard"], 2)
    assert result["shipping_total"] >= 1
    assert result["total"] == round(result["subtotal"] + result["shipping_total"], 2)
    assert result["shipping"]["pass_through"] is True
    assert result["shipping"]["never_free"] is True
    assert result["shipping"]["free_shipping"] is False
    assert "18.50" not in captured["quote"]  # net cost must not ride the quote lines
    assert navy["empire_code"] in captured["quote"]
    assert "never free" in captured["quote"]

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_not_allowed")
    with pytest.raises(PermissionError, match="live"):
        ff_db["checkout"].assert_test_mode()


def test_checkout_refuses_hidden_vendor(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    spruce = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Spruce")
    _hide_vendor(ff_db, "charlotte")
    with pytest.raises(PermissionError):
        ff_db["checkout"].resolve_cart_items([{"product_id": spruce["id"], "yards": 2}])


def test_public_edge_blocks_owner_and_finance(ff_db):
    from app.security.fabrics_public_edge import (
        DENIAL_ERROR,
        fabrics_public_edge_response,
        is_public_fabrics_path_allowed,
    )

    assert is_public_fabrics_path_allowed("GET", "/api/v1/fine-fabrics/catalog")
    assert is_public_fabrics_path_allowed("POST", "/api/v1/fine-fabrics/checkout")
    assert is_public_fabrics_path_allowed("POST", "/api/v1/fine-fabrics/shipping/estimate")
    assert is_public_fabrics_path_allowed("POST", "/api/v1/fine-fabrics/quote")
    assert is_public_fabrics_path_allowed("GET", "/api/v1/fine-fabrics/sitemap.xml")
    assert is_public_fabrics_path_allowed("GET", "/api/v1/fine-fabrics/merchant.xml")
    assert not is_public_fabrics_path_allowed("POST", "/api/v1/fine-fabrics/import")
    assert not is_public_fabrics_path_allowed("GET", "/api/v1/fine-fabrics/admin/unsorted")
    assert not is_public_fabrics_path_allowed("PUT", "/api/v1/fine-fabrics/admin/orders/1/shipping")
    assert not is_public_fabrics_path_allowed("GET", "/api/v1/finance/invoices")
    assert not is_public_fabrics_path_allowed("GET", "/api/v1/max/status")

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/finance/invoices",
            "headers": [(b"host", b"fabrics.empirebox.store")],
        }
    )
    denied = fabrics_public_edge_response(request)
    assert denied.status_code == 401
    assert denied.body  # JSONResponse

    local = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/finance/invoices",
            "headers": [(b"host", b"127.0.0.1:8000")],
        }
    )
    assert fabrics_public_edge_response(local) is None
    assert DENIAL_ERROR == "fabrics_public_edge_denied"


def test_main_loads_fine_fabrics_router():
    text = Path(__file__).resolve().parents[1] / "app" / "main.py"
    src = text.read_text(encoding="utf-8")
    assert 'load_router("app.routers.fine_fabrics", "/api/v1", ["fine-fabrics"])' in src
    assert "fabrics_public_edge_response" in src


def test_greenhouse_native_mapping(ff_db):
    fmt, rows = ff_db["importer"].parse_csv(GREENHOUSE_CSV.read_text(encoding="utf-8"), filename="greenhouse_prices.csv")
    assert fmt == "greenhouse"
    brindled = next(r for r in rows if r["sku"] == "S8090")
    assert brindled["pattern"] == "S8090"
    assert brindled["color"] == "BRINDLE"
    assert brindled["vendor"] == "Greenhouse"
    assert brindled["net_price"] == "18.00"
    result = ff_db["importer"].import_csv_text(GREENHOUSE_CSV.read_text(encoding="utf-8"), filename="greenhouse_prices.csv")
    assert result["created"] == 3
    hidden = ff_db["catalog"].list_catalog(include_hidden=True, owner=True)
    row = next(p for p in hidden if p["sku"] == "S8090")
    assert row["pattern"] == "S8090"
    assert row["color"] == "BRINDLE"
    assert row["vendor_slug"] == "greenhouse"
    public = ff_db["catalog"].list_catalog()
    assert any(p["pattern"] == "S8090" for p in public)
    assert any(p.get("brand") == "Greenhouse" for p in public)


def test_charlotte_collection_unit_and_unsorted(ff_db):
    result = ff_db["importer"].import_csv_text(CHARLOTTE_CSV.read_text(encoding="utf-8"), filename="charlotte_prices.csv")
    assert result["format"] == "charlotte"
    assert result["created"] == 3
    assert result["unsorted"] == 1
    hidden = ff_db["catalog"].list_catalog(include_hidden=True, owner=True)
    book = next(p for p in hidden if p["pattern"] == "Cuaderno Book")
    assert book["product_type"] == "collection"
    assert book["unit"] == "yard"
    assert book["color"] == ""
    tile = next(p for p in hidden if p["pattern"] == "Hearth Tile")
    assert tile["unit"] == "sq_ft"
    assert tile["unit_label"] == "sq ft"
    mystery = next(p for p in hidden if p["pattern"] == "Mystery Book")
    assert mystery["is_unsorted"] is True
    assert mystery["category"] == "Unsorted"
    assert mystery["unit"] == "roll"
    public = ff_db["catalog"].list_catalog()
    assert {p["pattern"] for p in public} == {"Cuaderno Book", "Hearth Tile"}
    assert all(p.get("brand") == "Charlotte" for p in public)
    queue = ff_db["catalog"].list_unsorted()
    assert [p["pattern"] for p in queue] == ["Mystery Book"]


def test_unsorted_never_public_even_for_open_vendor(ff_db):
    csv = """vendor,pattern,color,sku,category,width,content,repeat,net_price,list_price,product_url,notes
Sunbrella,Lost Cloth,Fog,LOST-1,,54,Acrylic,,19.00,38.00,,blank category
Sunbrella,Canvas,Navy,5408-0000,Outdoor,54,Acrylic,,18.50,36.00,,ok
"""
    ff_db["importer"].import_csv_text(csv)
    public = ff_db["catalog"].list_catalog()
    assert [p["pattern"] for p in public] == ["Canvas"]
    lost = next(p for p in ff_db["catalog"].list_unsorted() if p["pattern"] == "Lost Cloth")
    assert ff_db["catalog"].get_product(lost["id"], owner=False) is None
    client = _client(ff_db["router"])
    assert client.get(f"/api/v1/fine-fabrics/products/{lost['id']}").status_code == 404
    assigned = ff_db["catalog"].assign_category(lost["id"], "Outdoor")
    assert assigned["is_unsorted"] is False
    assert assigned["category"] == "Outdoor"
    assert ff_db["catalog"].get_product(lost["id"], owner=False)["pattern"] == "Lost Cloth"


def test_import_from_configurable_data_dir(ff_db, tmp_path, monkeypatch):
    drop = tmp_path / "fine_fabrics_vendor"
    drop.mkdir()
    (drop / "greenhouse_prices.csv").write_text(GREENHOUSE_CSV.read_text(encoding="utf-8"), encoding="utf-8")
    (drop / "charlotte_prices.csv").write_text(CHARLOTTE_CSV.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("FINE_FABRICS_DATA_DIR", str(drop))
    import importlib

    importlib.reload(ff_db["importer"])
    listed = ff_db["importer"].list_import_files()
    assert {f["name"] for f in listed} == {"greenhouse_prices.csv", "charlotte_prices.csv"}
    report = ff_db["importer"].import_from_dir()
    created = sum(item["created"] for item in report["files"])
    assert created == 6
    assert ff_db["catalog"].list_unsorted()


def test_pass_through_shipping_never_free(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    navy = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Navy")
    estimate = ff_db["shipping"].estimate_shipping([{"product_id": navy["id"], "yards": 3}])
    assert estimate["pass_through"] is True
    assert estimate["never_free"] is True
    assert estimate["free_shipping"] is False
    assert estimate["shipping_total"] == 15.50  # min 12 freight + 3.50 handling
    assert estimate["shipping_total"] > 0
    big = ff_db["shipping"].estimate_shipping([{"product_id": navy["id"], "yards": 100}])
    assert big["shipping_total"] == round(100 * 1.50 + 3.50, 2)
    assert big["free_shipping"] is False
    vendors = {v["slug"]: v for v in ff_db["catalog"].list_vendors()}
    ff_db["shipping"].update_shipping_rules(
        vendors["sunbrella"]["id"],
        {"ship_per_yard": 0, "ship_per_sample": 0, "ship_minimum": 0, "handling_fee": 0},
    )
    floored = ff_db["shipping"].estimate_shipping([{"product_id": navy["id"], "yards": 2}])
    assert floored["shipping_total"] == 1.0
    assert floored["floor_applied"] is True
    public = ff_db["shipping"].customer_shipping_view(estimate)
    assert "vendor_id" not in public
    assert "Charlotte" not in str(public)
    assert "Greenhouse" not in str(public)
    assert public["shipments"][0]["label"] == "Shipment 1"


def test_sample_and_checkout_shipping_and_shortfall(ff_db, monkeypatch):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    navy = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Navy")
    samples = ff_db["checkout"].request_samples(
        {"name": "Ada", "email": "ada@example.com"},
        [navy["id"]],
    )
    assert samples["shipping_total"] == 15.50
    monkeypatch.setattr(ff_db["checkout"], "_quotes_dir", lambda: ff_db["quotes"])
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.routers.finance",
        SimpleNamespace(
            create_quote_deposit_pay_link=lambda *a, **k: {
                "invoice": {"id": "inv-ship"},
                "pay_link": {"checkout_url": "https://checkout.stripe.com/c/pay/cs_test_ship"},
                "payment_status": "link_ready",
            },
            QUOTES_DIR=ff_db["quotes"],
        ),
    )
    order = ff_db["checkout"].checkout_cart(
        {"name": "Ada", "email": "ada@example.com"},
        [{"product_id": navy["id"], "yards": 3}],
    )
    billed = ff_db["shipping"].record_actual_shipping("order", order["order_id"], 40.00)
    assert billed["bill_shortfall"] is True
    assert billed["shipping_flag"] == "shortfall"
    assert billed["shipping_shortfall"] == round(40.00 - order["shipping_total"], 2)
    ok = ff_db["shipping"].record_actual_shipping("order", order["order_id"], order["shipping_total"])
    assert ok["bill_shortfall"] is False
    assert ff_db["shipping"].list_shortfalls() == []
    ff_db["shipping"].record_actual_shipping("sample", samples["id"], 99.00)
    flags = ff_db["shipping"].list_shortfalls()
    assert any(row["kind"] == "sample" and row["id"] == samples["id"] for row in flags)


def test_sitemap_and_merchant_exclude_hidden_and_unsorted(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    extra = """vendor,pattern,color,sku,category,width,content,repeat,net_price,list_price,product_url,notes
Sunbrella,Lost Cloth,Fog,LOST-1,,54,Acrylic,,19.00,38.00,,blank category
"""
    ff_db["importer"].import_csv_text(extra)
    public = ff_db["catalog"].list_catalog()
    navy = next(p for p in public if p["color"] == "Navy")
    spruce = next(p for p in public if p["color"] == "Spruce")
    lost = next(p for p in ff_db["catalog"].list_unsorted() if p["pattern"] == "Lost Cloth")
    sitemap = ff_db["seo"].sitemap_xml()
    merchant = ff_db["seo"].merchant_xml()
    assert f"/fine-fabrics/{navy['id']}" in sitemap
    assert f"/fine-fabrics/{spruce['id']}" in sitemap
    assert f"/fine-fabrics/{lost['id']}" not in sitemap
    assert navy["empire_code"] in merchant
    assert "Cuaderno" in merchant
    assert "Lost Cloth" not in merchant
    assert "Charlotte" in merchant
    assert "Sunbrella" in merchant
    assert f"<g:mpn>{navy['sku']}</g:mpn>" in merchant
    assert f"<g:brand>{navy['brand']}</g:brand>" in merchant
    public = ff_db["seo"].get_public_product(navy["id"])
    assert public["seo"]["json_ld"]["@type"] == "Product"
    assert public["seo"]["json_ld"]["sku"] == navy["sku"]
    assert public["seo"]["json_ld"]["mpn"] == navy["sku"]
    assert public["seo"]["json_ld"]["brand"]["name"] == "Sunbrella"
    assert navy["sku"] in public["seo"]["title"]
    assert "Sunbrella" in public["seo"]["title"]
    assert "net_price" not in public
    _hide_vendor(ff_db, "greenhouse")
    hidden_feed = ff_db["seo"].merchant_xml()
    assert "Botanical Vine" not in hidden_feed
    assert "Greenhouse" not in hidden_feed
    client = _client(ff_db["router"])
    sm = client.get("/api/v1/fine-fabrics/sitemap.xml")
    assert sm.status_code == 200
    assert "urlset" in sm.text
    feed = client.get("/api/v1/fine-fabrics/merchant.xml")
    assert feed.status_code == 200
    assert "g:price" in feed.text
    est = client.post(
        "/api/v1/fine-fabrics/shipping/estimate",
        json={"items": [{"product_id": navy["id"], "yards": 2}]},
    )
    assert est.status_code == 200
    assert est.json()["shipping_total"] >= 1
    assert "vendor_id" not in est.json()


def test_admin_actual_shipping_endpoint(ff_db, monkeypatch):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    navy = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Navy")
    monkeypatch.setattr(ff_db["checkout"], "_quotes_dir", lambda: ff_db["quotes"])
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.routers.finance",
        SimpleNamespace(
            create_quote_deposit_pay_link=lambda *a, **k: {
                "invoice": {"id": "inv-admin"},
                "pay_link": {"checkout_url": "https://checkout.stripe.com/c/pay/cs_test_admin"},
                "payment_status": "link_ready",
            },
            QUOTES_DIR=ff_db["quotes"],
        ),
    )
    order = ff_db["checkout"].checkout_cart(
        {"name": "Ada", "email": "ada@example.com"},
        [{"product_id": navy["id"], "yards": 1}],
    )
    client = _client(ff_db["router"])
    denied = client.put(
        f"/api/v1/fine-fabrics/admin/orders/{order['order_id']}/shipping",
        json={"actual_vendor_shipping": 50},
        headers={"host": "fabrics.empirebox.store"},
    )
    assert denied.status_code == 401
    ok = client.put(
        f"/api/v1/fine-fabrics/admin/orders/{order['order_id']}/shipping",
        json={"actual_vendor_shipping": 50},
        headers={"host": "127.0.0.1:8000"},
    )
    assert ok.status_code == 200
    assert ok.json()["bill_shortfall"] is True
    shorts = client.get("/api/v1/fine-fabrics/admin/shortfalls", headers={"host": "127.0.0.1:8000"})
    assert shorts.json()["shortfalls"]


def test_display_title_and_folded_sku_search(ff_db):
    csv = """vendor,brand,pattern,color,sku,category,width,content,repeat,net_price,list_price,product_url,notes
Kravet,Kravet,Indienne,Fennel,PEF100019.34,Drapery,54,Linen,,48.00,96.00,,mock
"""
    ff_db["importer"].import_csv_text(csv)
    catalog = ff_db["catalog"]
    assert catalog.fold_sku("PEF100019.34") == "pef10001934"
    assert catalog.fold_sku("PEF-100019-34") == "pef10001934"
    assert catalog.display_title(
        {"sku": "PEF100019.34", "pattern": "Indienne", "color": "Fennel"},
        "Kravet",
    ) == "Kravet PEF100019.34 Indienne Fennel"
    row = next(p for p in catalog.list_catalog() if p["sku"] == "PEF100019.34")
    assert row["display_title"] == "Kravet PEF100019.34 Indienne Fennel"
    assert row["brand"] == "Kravet"
    for needle in ("PEF100019.34", "PEF10001934", "pef-100019-34", "Indienne", "Kravet"):
        hits = catalog.list_catalog(search=needle)
        assert hits and hits[0]["sku"] == "PEF100019.34", needle
    client = _client(ff_db["router"])
    found = client.get("/api/v1/fine-fabrics/catalog?search=PEF10001934").json()["products"]
    assert found[0]["display_title"] == "Kravet PEF100019.34 Indienne Fennel"
    seo = ff_db["seo"].get_public_product(row["id"])["seo"]
    assert seo["title"].startswith("Kravet PEF100019.34 Indienne Fennel")
    assert seo["json_ld"]["sku"] == "PEF100019.34"
    assert seo["json_ld"]["mpn"] == "PEF100019.34"
    assert seo["json_ld"]["brand"]["name"] == "Kravet"
    assert "PEF100019.34" in seo["description"]
    merchant = ff_db["seo"].merchant_xml()
    assert "<g:mpn>PEF100019.34</g:mpn>" in merchant
    assert "<g:brand>Kravet</g:brand>" in merchant


def test_base_selection_import_empire_code_and_vendor_image(ff_db):
    text = BASE_SELECTION_CSV.read_text(encoding="utf-8")
    fmt, rows = ff_db["importer"].parse_csv(text, filename="base_selection_import.csv")
    assert fmt == "canonical"
    assert "empire_code" in text.splitlines()[0]
    result = ff_db["importer"].import_csv_text(text, filename="base_selection_import.csv")
    assert result["created"] == 5
    public = ff_db["catalog"].list_catalog()
    book = next(p for p in public if p["product_type"] == "collection")
    assert book["empire_code"] == "C-CUADERNO-BOOK"
    assert book["has_vendor_image"] is True
    brindled = next(p for p in public if p["sku"] == "S8090")
    assert brindled["empire_code"] == "GH-S8090-BRINDLE"
    assert brindled["brand"] == "Greenhouse"
    assert brindled["display_title"] == "Greenhouse S8090 BRINDLE"


def test_item_quote_stub_and_preview_mockup_items(ff_db):
    ff_db["importer"].import_csv_text(MOCK_CSV)
    navy = next(p for p in ff_db["catalog"].list_catalog() if p["color"] == "Navy")
    quoted = ff_db["checkout"].request_item_quote(
        {"name": "Ada", "email": "ada@example.com", "message": "roman shade"},
        product_id=navy["id"],
        item_type="roman_shade",
    )
    assert quoted["engine"] in {"stub", "leadforge"}
    assert quoted["item_type"] == "roman_shade"
    assert quoted["empire_code"] == navy["empire_code"]
    assert quoted["status"] == "new"
    preview = ff_db["preview"].preview_fabric(navy["id"], item_type="pillow")
    assert preview["fabric"]["mockup_items"] == [
        "pillow",
        "drapery_panel",
        "roman_shade",
        "sofa",
        "accent_chair",
        "bench",
    ]
    client = _client(ff_db["router"])
    body = client.post(
        "/api/v1/fine-fabrics/quote",
        json={"product_id": navy["id"], "item_type": "pillow", "name": "Ada", "email": "ada@example.com"},
    )
    assert body.status_code == 200
    assert body.json()["item_type"] == "pillow"
    assert body.json()["engine"] in {"stub", "leadforge"}


def test_preview_catalog_has_twenty_mock_skus():
    text = Path(__file__).resolve().parents[1] / "app" / "data" / "fine_fabrics" / "preview_catalog.csv"
    rows = [line for line in text.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    assert len(rows) >= 20
    assert "PEF100019.34" in text.read_text(encoding="utf-8")
    assert "Indienne" in text.read_text(encoding="utf-8")
