import asyncio
import importlib
import json
from pathlib import Path

import pytest
from starlette.requests import Request

from app.services.pricing import (
    PRICING_ENGINE_VERSION,
    PricingClassificationError,
    PricingInputError,
    build_quote_invoice_source,
    canonical_tax_policy,
    price_woodcraft_item,
    price_workroom_item,
)


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/test", "headers": []})


def _load_finance(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import finance

    importlib.reload(finance)
    quotes_dir = tmp_path / "quotes"
    designs_dir = tmp_path / "craftforge" / "designs"
    quotes_dir.mkdir(parents=True)
    designs_dir.mkdir(parents=True)
    monkeypatch.setattr(finance, "QUOTES_DIR", quotes_dir)
    monkeypatch.setattr(finance, "DESIGNS_DIR", designs_dir)
    return finance, quotes_dir, designs_dir


def _load_craftforge(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import craftforge

    importlib.reload(craftforge)
    data_dir = tmp_path / "craftforge"
    designs_dir = data_dir / "designs"
    jobs_dir = data_dir / "jobs"
    inventory_dir = data_dir / "inventory"
    templates_dir = data_dir / "templates"
    for path in [designs_dir, jobs_dir, inventory_dir, templates_dir]:
        path.mkdir(parents=True)
    monkeypatch.setattr(craftforge, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(craftforge, "DESIGNS_DIR", str(designs_dir))
    monkeypatch.setattr(craftforge, "JOBS_DIR", str(jobs_dir))
    monkeypatch.setattr(craftforge, "INVENTORY_DIR", str(inventory_dir))
    monkeypatch.setattr(craftforge, "TEMPLATES_DIR", str(templates_dir))
    monkeypatch.setattr(craftforge, "COUNTER_FILE", str(data_dir / "_counter.json"))
    return craftforge, designs_dir


def test_workroom_cushion_quote_pricing():
    result = price_workroom_item(
        "cushion",
        {"fabric_yards": 2, "fabric_price_per_yard": 40, "labor_hours": 3, "labor_rate": 65},
        tax_policy=canonical_tax_policy(name="non_taxable_service", tax_rate=0, taxable=False),
    )

    assert result["business_unit"] == "workroom"
    assert result["product_category"] == "cushions"
    assert result["calculated_subtotal"] == 275
    assert result["tax_amount"] == 0
    assert result["final_price"] == 275
    assert result["deposit_amount"] == 137.5
    assert result["pricing_engine_version"] == PRICING_ENGINE_VERSION


def test_workroom_drapery_window_treatment_quote_pricing():
    result = price_workroom_item(
        "drapery",
        {
            "fabric_yards": 8,
            "fabric_price_per_yard": 55,
            "labor_hours": 6,
            "labor_rate": 65,
            "hardware_cost": 120,
            "install_cost": 150,
        },
        tax_policy=canonical_tax_policy(name="va_retail_rate", tax_rate=0.053, taxable=True),
    )

    assert result["product_category"] == "drapery_window_treatments"
    assert result["calculated_subtotal"] == 1100
    assert result["tax_policy"]["name"] == "va_retail_rate"
    assert result["tax_amount"] == 58.3
    assert result["final_price"] == 1158.3


def test_workroom_upholstery_quote_pricing():
    result = price_workroom_item(
        "upholstery",
        {
            "fabric_yards": 12,
            "fabric_price_per_yard": 65,
            "labor_hours": 10,
            "labor_rate": 75,
            "material_cost": 120,
            "markup_percent": 25,
            "complexity_multiplier": 1.1,
        },
        deposit_percent=40,
    )

    assert result["product_category"] == "upholstery"
    assert result["calculated_subtotal"] == 1848
    assert result["deposit_amount"] == 739.2
    assert result["balance_due"] == 1108.8


def test_woodcraft_cnc_quote_pricing():
    result = price_woodcraft_item(
        "cnc",
        {"machine_minutes": 90, "machine_rate_per_hour": 120, "design_hours": 1, "design_rate": 85},
        deposit_required=False,
    )

    assert result["business_unit"] == "woodcraft"
    assert result["product_category"] == "cnc_router_time"
    assert result["calculated_subtotal"] == 265
    assert result["deposit_required"] is False


def test_woodcraft_custom_build_cabinet_pricing():
    result = price_woodcraft_item(
        "cabinet",
        {
            "sheet_count": 3,
            "cost_per_sheet": 80,
            "waste_factor": 0.15,
            "markup_percent": 30,
            "assembly_hours": 10,
            "assembly_rate": 75,
            "finishing_square_feet": 80,
            "finishing_square_foot_rate": 8,
            "hardware_cost": 200,
        },
    )

    assert result["product_category"] == "custom_build"
    assert result["calculated_subtotal"] == 2008.8
    assert any(step["label"] == "sheet goods" for step in result["calculation_steps"])


def test_unknown_product_category_does_not_fall_back():
    with pytest.raises(PricingClassificationError):
        price_workroom_item("mystery_large_item", {"labor_hours": 1, "labor_rate": 1})


def test_manual_override_requires_reason():
    with pytest.raises(PricingInputError):
        price_workroom_item("pillow", {"fixed_price": 120}, override_amount=99)

    result = price_workroom_item("pillow", {"fixed_price": 120}, override_amount=99, override_reason="Founder approved")
    assert result["final_price"] == 99
    assert result["override_reason"] == "Founder approved"


def test_boolean_deposit_required_does_not_become_one_dollar():
    source_snapshot = price_workroom_item("cushion", {"fixed_price": 200}, deposit_percent=40)
    quote = {
        "id": "quote-bool-deposit",
        "business_unit": "workroom",
        "line_items": [{
            "description": "Window seat cushion",
            "quantity": 1,
            "rate": 200,
            "amount": 200,
            "pricing_snapshot_json": source_snapshot,
        }],
        "subtotal": 200,
        "tax_rate": 0,
        "total": 200,
        "deposit_required": True,
        "pricing_snapshot_json": source_snapshot,
    }

    source = build_quote_invoice_source(quote, "quote-bool-deposit")

    assert source["deposit_required"] == 80
    assert source["pricing_snapshot_json"]["deposit_amount"] == 80
    assert source["pricing_snapshot_json"]["balance_due"] == 120


def test_quote_to_invoice_preserves_pricing_snapshot(monkeypatch, tmp_path):
    finance, quotes_dir, _ = _load_finance(monkeypatch, tmp_path)
    source_snapshot = price_workroom_item("cushion", {"fixed_price": 300}, source_quote_id="quote-1", source_line_item_id="li-1")
    quote = {
        "id": "quote-1",
        "quote_number": "EST-2026-001",
        "customer_name": "Snapshot Client",
        "customer_email": "snap@example.com",
        "customer_phone": "555-1111",
        "customer_address": "1 Snapshot Way",
        "business_unit": "workroom",
        "line_items": [{
            "id": "li-1",
            "description": "Bench cushion",
            "quantity": 3,
            "rate": 100,
            "amount": 300,
            "pricing_snapshot_json": source_snapshot,
        }],
        "subtotal": 300,
        "tax_rate": 0.1,
        "tax_amount": 30,
        "discount_amount": 20,
        "discount_type": "dollar",
        "total": 310,
        "deposit": {"deposit_percent": 50, "deposit_amount": 155},
        "terms": "50% deposit",
        "notes": "Approved pricing",
    }
    (quotes_dir / "quote-1.json").write_text(json.dumps(quote))

    invoice = finance.create_invoice_from_quote(_request(), "quote-1")["invoice"]

    assert invoice["total"] == 310
    assert invoice["deposit_required"] == 155
    assert invoice["pricing_snapshot_json"]["pricing_method"] == "approved_quote_snapshot"
    assert invoice["line_items"][0]["quantity"] == 3
    assert invoice["line_items"][0]["unit_price"] == 100
    assert invoice["line_items"][0]["pricing_snapshot_json"]["final_price"] == 300


def test_craftforge_design_to_invoice_preserves_pricing_snapshot(monkeypatch, tmp_path):
    craftforge, designs_dir = _load_craftforge(monkeypatch, tmp_path)
    design_snapshot = price_woodcraft_item("cabinet", {"fixed_price": 900}, source_quote_id="design-1")
    design = {
        "id": "design-1",
        "design_number": "CF-2026-001",
        "customer_name": "Wood Snapshot",
        "customer_email": "woodsnap@example.com",
        "customer_phone": "555-2222",
        "customer_address": "2 Router Road",
        "name": "Cabinet",
        "category": "cabinet",
        "materials": [{"name": "Plywood", "quantity": 2, "cost_per_unit": 100}],
        "line_items": [{"description": "Assembly", "quantity": 4, "unit_price": 75, "pricing_snapshot_json": design_snapshot}],
        "subtotal": 500,
        "tax_rate": 0,
        "tax_amount": 0,
        "total": 500,
        "deposit_percent": 50,
        "pricing_snapshot_json": design_snapshot,
        "status": "accepted",
    }
    (designs_dir / "design-1.json").write_text(json.dumps(design))

    invoice = asyncio.run(craftforge.create_invoice_from_design("design-1"))["invoice"]

    assert invoice["business_unit"] == "woodcraft"
    assert invoice["total"] == 500
    assert invoice["deposit_required"] == 250
    assert invoice["pricing_snapshot_json"]["pricing_method"] == "approved_design_snapshot"
    assert invoice["line_items"][0]["pricing_snapshot_json"]["preserved_from_source"] is True
    assert any(line["description"] == "Assembly" for line in invoice["line_items"])


def test_deposit_and_tax_policy_behavior():
    result = price_workroom_item(
        "labor",
        {"labor_hours": 2, "labor_rate": 100},
        discount_type="percent",
        discount_amount=10,
        tax_policy=canonical_tax_policy(name="explicit_dc_rate", tax_rate=0.06, taxable=True),
        deposit_percent=25,
    )

    assert result["calculated_subtotal"] == 200
    assert result["discount_amount"] == 10
    assert result["tax_amount"] == 10.8
    assert result["final_price"] == 190.8
    assert result["deposit_amount"] == 47.7
    assert result["balance_due"] == 143.1


def test_no_hardcoded_old_quote_path_in_canonical_pricing_flow():
    backend_root = Path(__file__).resolve().parents[1]
    paths = [
        backend_root / "app" / "routers" / "quotes.py",
        backend_root / "app" / "routers" / "finance.py",
        backend_root / "app" / "routers" / "craftforge.py",
        backend_root / "app" / "services" / "quote_engine" / "quote_assembler.py",
        backend_root / "app" / "services" / "quote_engine" / "quote_phases.py",
        backend_root / "app" / "services" / "quote_engine" / "verification.py",
    ]
    for path in paths:
        source = path.read_text()
        assert "~/empire-repo/backend/data/quotes" not in source
        assert 'get("type", "accent_chair")' not in source
        assert 'get("item_type", "accent_chair")' not in source
