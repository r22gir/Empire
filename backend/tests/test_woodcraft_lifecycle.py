import asyncio
import importlib
import json


def _load_woodcraft_modules(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import jobs_unified

    importlib.reload(jobs_unified)

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
    return craftforge, database, designs_dir


def test_woodcraft_design_to_invoice_and_job_carries_fields(monkeypatch, tmp_path):
    craftforge, database, designs_dir = _load_woodcraft_modules(monkeypatch, tmp_path)

    design = {
        "id": "design-1",
        "design_number": "CF-2026-001",
        "customer_name": "Willa Wood",
        "customer_email": "willa@example.com",
        "customer_phone": "555-0333",
        "customer_address": "33 CNC Road",
        "name": "Walnut Valance",
        "description": "Custom CNC walnut valance",
        "materials": [{"name": "Walnut", "quantity": 2, "cost_per_unit": 100}],
        "line_items": [{"description": "Finish", "quantity": 1, "unit_price": 50}],
        "cnc_jobs": [{"machine": "x-carve", "operation": "profile", "estimated_time_min": 90}],
        "material_cost": 200,
        "labor_cost": 125,
        "cnc_time_cost": 75,
        "overhead": 25,
        "subtotal": 425,
        "tax_rate": 0.1,
        "tax_amount": 42.5,
        "discount_amount": 25,
        "discount_type": "dollar",
        "deposit_percent": 50,
        "total": 442.5,
        "notes": "Woodcraft handoff notes",
        "status": "accepted",
    }
    (designs_dir / "design-1.json").write_text(json.dumps(design))

    invoice_result = asyncio.run(craftforge.create_invoice_from_design("design-1"))
    invoice = invoice_result["invoice"]

    assert invoice_result["design_id"] == "design-1"
    assert invoice["quote_id"] == "design-1"
    assert invoice["customer_id"]
    assert invoice["client_name"] == "Willa Wood"
    assert invoice["client_email"] == "willa@example.com"
    assert invoice["client_phone"] == "555-0333"
    assert invoice["client_address"] == "33 CNC Road"
    assert invoice["business_unit"] == "woodcraft"
    assert invoice["discount_amount"] == 25
    assert invoice["discount_type"] == "dollar"
    assert invoice["deposit_required"] == 221.25
    assert invoice["deposit_received"] == 0
    assert invoice["total"] == 442.5
    assert invoice["line_items"][0]["description"] == "Walnut"

    saved_design = json.loads((designs_dir / "design-1.json").read_text())
    assert saved_design["status"] == "invoiced"
    assert saved_design["invoice_id"] == invoice["id"]

    job_result = asyncio.run(craftforge.create_job_from_design("design-1"))
    job = job_result["job"]

    assert job_result["design_id"] == "design-1"
    assert job["quote_id"] == "design-1"
    assert job["customer_id"] == invoice["customer_id"]
    assert job["client_name"] == "Willa Wood"
    assert job["client_email"] == "willa@example.com"
    assert job["client_phone"] == "555-0333"
    assert job["client_address"] == "33 CNC Road"
    assert job["business_unit"] == "woodcraft"
    assert job["pipeline_stage"] == "approved"
    assert job["estimated_value"] == 442.5
    assert job["quoted_amount"] == 442.5
    assert job["description"] == "Custom CNC walnut valance"
    assert job["estimated_hours"] == 1.5

    with database.get_db() as conn:
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (invoice["customer_id"],)
        ).fetchone()
        assert customer["name"] == "Willa Wood"
        assert customer["email"] == "willa@example.com"
        assert customer["phone"] == "555-0333"
        assert customer["address"] == "33 CNC Road"
        assert customer["business"] == "woodcraft"
