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
                "name": "Primary Bedroom",
                "windows": [
                    {
                        "name": "East Window",
                        "treatment_type": "drapery",
                    }
                ],
            }
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

    with database.get_db() as conn:
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (job["customer_id"],)
        ).fetchone()
        assert customer["name"] == "Ada Jobclient"
        assert customer["email"] == "ada.job@example.com"
        assert customer["phone"] == "555-0222"
        assert customer["address"] == "22 Job Lane"
        assert customer["business"] == "workroom"
