import importlib
import json


def _load_jobs_modules(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import jobs_unified

    importlib.reload(jobs_unified)
    quotes_dir = tmp_path / "quotes"
    quotes_dir.mkdir()
    monkeypatch.setattr(jobs_unified, "QUOTES_DIR", quotes_dir)
    return jobs_unified, database, quotes_dir


def test_job_from_quote_carries_client_business_and_crm_link(monkeypatch, tmp_path):
    jobs_unified, database, quotes_dir = _load_jobs_modules(monkeypatch, tmp_path)

    quote = {
        "id": "quote-job-1",
        "quote_number": "EST-2026-0200",
        "customer_name": "Ada Jobclient",
        "customer_email": "ada.job@example.com",
        "customer_phone": "555-0222",
        "customer_address": "22 Job Lane",
        "project_description": "Fabricate and install workroom treatments",
        "notes": "Preserve client notes",
        "business_unit": "workroom",
        "total": 425,
        "intake_project_id": "intake-job-1",
        "intake_code": "INT-2026-0200",
        "rooms": [
            {
                "id": "room-primary",
                "name": "Primary Bedroom",
                "items": [
                    {
                        "id": "item-east-window",
                        "type": "drapery",
                        "dimensions": {"width": "84", "height": "96", "depth": "6"},
                        "quantity": 1,
                        "notes": "East wall silk panels",
                    },
                    {
                        "id": "item-banquette",
                        "type": "bench_l_shaped",
                        "dimensions": {"width": "120", "height": "36", "depth": "24"},
                        "quantity": 1,
                        "notes": "Shape: l bench | A: 120\" B: 60\" | D: 24\"",
                        "drawings": [
                            {
                                "url": "/api/v1/drawings/files/banquette.svg",
                                "filename": "banquette.svg",
                                "assigned_item_id": "item-banquette",
                            }
                        ],
                    }
                ],
            }
        ],
        "photos": [
            {
                "url": "/uploads/quote/east-window.jpg",
                "original_name": "east-window.jpg",
                "assigned_room_id": "room-primary",
                "assigned_item_id": "item-east-window",
            },
            {
                "url": "/uploads/quote/banquette-ref.jpg",
                "original_name": "banquette-ref.jpg",
                "assigned_room_id": "room-primary",
                "assigned_item_id": "item-banquette",
            },
        ],
    }
    (quotes_dir / "quote-job-1.json").write_text(json.dumps(quote))

    result = jobs_unified.create_job_from_quote("quote-job-1")
    job = result["job"]

    assert result["quote_id"] == "quote-job-1"
    assert job["quote_id"] == "quote-job-1"
    assert job["customer_id"]
    assert job["client_name"] == "Ada Jobclient"
    assert job["client_email"] == "ada.job@example.com"
    assert job["client_phone"] == "555-0222"
    assert job["client_address"] == "22 Job Lane"
    assert job["business_unit"] == "workroom"
    assert job["quoted_amount"] == 425
    assert job["pipeline_stage"] == "quoted"
    assert "Primary Bedroom" in job["description"]
    assert job["metadata"]["source"] == "quote"
    assert job["metadata"]["quote_number"] == "EST-2026-0200"
    assert job["metadata"]["intake_project_id"] == "intake-job-1"
    assert job["metadata"]["intake_code"] == "INT-2026-0200"
    assert job["metadata"]["visual_document_count"] == 3
    assert job["metadata"]["area_item_count"] == 2
    assert job["photos"][0]["assigned_item_id"] == "item-east-window"
    assert job["items"][0]["room"] == "Primary Bedroom"
    assert job["items"][0]["item_key"] == "item-east-window"
    assert job["items"][0]["route_to"] == "workroom"
    assert job["items"][1]["item_key"] == "item-banquette"
    assert job["items"][1]["route_to"] == "woodcraft"

    with database.get_db() as conn:
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (job["customer_id"],)
        ).fetchone()
        assert customer["name"] == "Ada Jobclient"
        assert customer["email"] == "ada.job@example.com"
        assert customer["phone"] == "555-0222"
        assert customer["address"] == "22 Job Lane"
        assert customer["business"] == "workroom"

        job_items = conn.execute(
            "SELECT * FROM job_items WHERE job_id = ? ORDER BY item_key", (job["id"],)
        ).fetchall()
        job_documents = conn.execute(
            "SELECT * FROM job_documents WHERE job_id = ? ORDER BY filename", (job["id"],)
        ).fetchall()

    assert len(job_items) == 2
    job_items_by_key = {item["item_key"]: item for item in job_items}
    assert job_items_by_key["item-east-window"]["room"] == "Primary Bedroom"
    assert json.loads(job_items_by_key["item-east-window"]["measurements"]) == {"width": "84", "height": "96", "depth": "6"}
    assert job_items_by_key["item-east-window"]["route_to"] == "workroom"
    assert job_items_by_key["item-banquette"]["room"] == "Primary Bedroom"
    assert job_items_by_key["item-banquette"]["route_to"] == "woodcraft"
    assert len(job_documents) == 3
    assert {d["item_key"] for d in job_documents} == {"item-east-window", "item-banquette"}
    assert {d["document_type"] for d in job_documents} == {"photo", "drawing"}
    drawing_doc = next(d for d in job_documents if d["document_type"] == "drawing")
    assert drawing_doc["route_to"] == "woodcraft"

    detail = jobs_unified.get_job(job["id"])["job"]
    assert {item["item_key"] for item in detail["items"]} == {"item-east-window", "item-banquette"}
    assert {doc["filename"] for doc in detail["documents"]} == {"east-window.jpg", "banquette-ref.jpg", "banquette.svg"}


def test_jobs_invoice_compatibility_uses_crm_and_canonical_payments(monkeypatch, tmp_path):
    jobs_unified, database, _quotes_dir = _load_jobs_modules(monkeypatch, tmp_path)

    invoice_response = jobs_unified.create_invoice(
        jobs_unified.InvoiceCreateSchema(
            client_name="Pay Client",
            client_email="pay@example.com",
            client_phone="555-0555",
            client_address="55 Payment Path",
            business_unit="workroom",
            subtotal=150,
            tax_rate=0,
            line_items=[{"description": "Workroom service", "quantity": 1, "unit_price": 150, "total": 150}],
        )
    )
    invoice = invoice_response["invoice"]

    assert invoice["customer_id"]
    assert invoice["customer_name"] == "Pay Client"
    assert invoice["amount"] == 150
    assert invoice["balance"] == 150

    payment_response = jobs_unified.record_payment(
        invoice["id"],
        jobs_unified.PaymentRecord(amount=50, method="bank_transfer", reference="BT-50", notes="Bridge proof"),
    )
    payment = payment_response["payment"]

    assert payment_response["invoice"]["amount_paid"] == 50
    assert payment_response["invoice"]["balance_due"] == 100
    assert payment["method"] == "bank_transfer"

    detail = jobs_unified.get_invoice(invoice["id"])["invoice"]
    listed_payments = jobs_unified.list_payments(invoice["id"])

    assert detail["payments"][0]["id"] == payment["id"]
    assert detail["payments"][0]["method"] == "other"
    assert listed_payments["items"] == listed_payments["payments"]
    assert listed_payments["payments"][0]["id"] == payment["id"]
    assert listed_payments["payments"][0]["method"] == "other"

    with database.get_db() as conn:
        invoice_payment = conn.execute(
            "SELECT * FROM invoice_payments WHERE invoice_id = ?", (invoice["id"],)
        ).fetchone()
        canonical_payment = conn.execute(
            "SELECT * FROM payments WHERE invoice_id = ?", (invoice["id"],)
        ).fetchone()
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (invoice["customer_id"],)
        ).fetchone()

    assert invoice_payment["id"] == payment["id"]
    assert canonical_payment["id"] == payment["id"]
    assert canonical_payment["customer_id"] == invoice["customer_id"]
    assert canonical_payment["amount"] == 50
    assert canonical_payment["method"] == "other"
    assert canonical_payment["reference"] == "BT-50"
    assert customer["name"] == "Pay Client"
    assert customer["email"] == "pay@example.com"
    assert customer["phone"] == "555-0555"
    assert customer["address"] == "55 Payment Path"
    assert customer["business"] == "workroom"
    assert customer["total_revenue"] == 50
