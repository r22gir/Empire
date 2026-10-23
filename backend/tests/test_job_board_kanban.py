"""
Tests for Job Board Kanban and Per-Job Document Folder endpoints and Max tools.

Uses the session isolated_empire_db (conftest). Do not set EMPIRE_TASK_DB
at import time — that leaks a second SQLite file and breaks other Jobs
tests when the suite is collected together.
"""

import secrets
import pytest
from fastapi.testclient import TestClient

from app.db.init_db import init_database
from app.main import app
from app.db.database import get_db
from app.services.max.tool_executor import (
    set_current_job_id,
    get_current_job_id,
    execute_tool
)


@pytest.fixture(autouse=True)
def setup_test_database(isolated_empire_db):
    """Schema on the isolated session DB. Data is truncated between tests."""
    init_database()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _create_test_job(client, title, client_name, status="lead", estimated_value=1000.0, business_unit="workroom"):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM customers WHERE name = ?", (client_name,)).fetchone()
        if not row:
            cid = f"cust_{secrets.token_hex(4)}"
            conn.execute(
                "INSERT INTO customers (id, name, business) VALUES (?, ?, ?)",
                (cid, client_name, business_unit)
            )
            customer_id = cid
        else:
            customer_id = row["id"]

    resp = client.post("/api/v1/jobs", json={
        "title": title,
        "customer_id": customer_id,
        "client_name": client_name,
        "status": status,
        "pipeline_stage": status,
        "estimated_value": estimated_value,
        "business_unit": business_unit,
    })
    data = resp.json()
    job = data.get("job") or data
    return job.get("id")


def test_kanban_stage_retrieval_and_creation(client):
    """Test retrieving kanban columns and creating a test job."""
    # 1. Fetch kanban before jobs
    resp = client.get("/api/v1/jobs/kanban")
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert len(data["columns"]) == 11
    col_keys = [c["key"] for c in data["columns"]]
    assert "lead" in col_keys
    assert "in_production" in col_keys
    assert "paid_closed" in col_keys

    # 2. Create a test job
    job_id = _create_test_job(client, "Living Room Ripplefold Panels", "Test Client Sarah", "lead", 3500.0)
    assert job_id is not None

    # 3. Verify job shows up in the lead column with computed payment strip
    resp2 = client.get("/api/v1/jobs/kanban")
    assert resp2.status_code == 200
    data2 = resp2.json()
    lead_col = next(c for c in data2["columns"] if c["key"] == "lead")
    found = [j for j in lead_col["jobs"] if j["id"] == job_id]
    assert len(found) == 1
    job_card = found[0]
    assert job_card["client_name"] == "Test Client Sarah"
    assert "payment_strip" in job_card
    assert job_card["payment_strip"]["total"] == 3500.0
    assert job_card["payment_strip"]["paid"] == 0.0
    assert job_card["payment_strip"]["balance"] == 3500.0


def test_kanban_stage_transition(client):
    """Test transitioning a job across stages via PATCH /jobs/{id}/stage and /status."""
    job_id = _create_test_job(client, "Roman Shades Custom", "Marley Cafe", "lead", 2800.0)

    # Transition to fabric_ordered
    patch_resp = client.patch(f"/api/v1/jobs/{job_id}/stage", json={"stage": "fabric_ordered"})
    assert patch_resp.status_code == 200
    res_data = patch_resp.json()
    assert res_data["job"]["canonical_stage"] == "fabric_ordered"

    # Transition to in_production
    patch_resp2 = client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "in_production"})
    assert patch_resp2.status_code == 200

    # Verify kanban reflects the new column
    k_resp = client.get("/api/v1/jobs/kanban")
    in_prod_col = next(c for c in k_resp.json()["columns"] if c["key"] == "in_production")
    in_prod_job_ids = [j["id"] for j in in_prod_col["jobs"]]
    assert job_id in in_prod_job_ids

    timeline = client.get(f"/api/v1/jobs/{job_id}/timeline")
    assert timeline.status_code == 200
    events = timeline.json().get("events") or []
    changes = [e for e in events if e.get("event_type") == "status_change"]
    assert len(changes) >= 2
    assert any((e.get("metadata") or {}).get("to") == "in_production" for e in changes)


def test_per_job_document_folder_endpoints(client):
    """Test file upload, change order creation, and email thread logging."""
    job_id = _create_test_job(client, "Dahlia Design Hotel Suite", "Nehal Elrefai", "deposit_paid", 3904.28)

    # 1. File Upload (e.g. PDF or photo)
    file_content = b"%PDF-1.4 test estimate mockup"
    upload_resp = client.post(
        f"/api/v1/jobs/{job_id}/upload",
        files={"file": ("estimate_mockup.pdf", file_content, "application/pdf")},
        data={"document_type": "estimate"}
    )
    assert upload_resp.status_code == 200
    up_data = upload_resp.json()
    assert "document" in up_data

    # 2. Add Change Order
    co_resp = client.post(
        f"/api/v1/jobs/{job_id}/change-orders",
        json={
            "title": "Add blackout lining to drapery",
            "amount": 420.50,
            "description": "Client requested 100% blackout pass",
            "status": "approved"
        }
    )
    assert co_resp.status_code == 200
    assert "change_order" in co_resp.json()

    # 3. Log Email Thread
    email_resp = client.post(
        f"/api/v1/jobs/{job_id}/emails",
        json={
            "subject": "Pickup schedule for Monday",
            "sender": "rafael@empireworkroom.com",
            "recipient": "nehal@dahliadesign.com",
            "body": "Hi Nehal, we will pick up the drapery fabrics Monday 10am."
        }
    )
    assert email_resp.status_code == 200
    assert "email" in email_resp.json()

    # 4. Fetch job details and verify documents, change orders, emails are included
    detail_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert "documents" in detail
    docs = detail["documents"]
    doc_types = [d.get("document_type") for d in docs]
    assert "estimate" in doc_types
    assert "change_order" in doc_types
    assert "email" in doc_types


def test_max_chat_job_context_and_tools():
    """Test Max tool executor with active job ID context variable and tools."""
    # Create an actual test job in DB
    with get_db() as conn:
        cid = "cust_max_test"
        conn.execute("INSERT OR IGNORE INTO customers (id, name, business) VALUES (?, ?, 'workroom')", (cid, "Max Test Client"))
        conn.execute("""
            INSERT INTO jobs (id, job_number, title, customer_id, client_name, status, pipeline_stage, estimated_value)
            VALUES ('job_test_max_42', 'JOB-TEST-42', 'Living Room Custom Romans', ?, 'Max Test Client', 'pending', 'lead', 1200)
        """, (cid,))

    # 1. Set current job ID context
    set_current_job_id("job_test_max_42")
    assert get_current_job_id() == "job_test_max_42"

    # 2. Verify get_current_job tool execution
    res = execute_tool("get_current_job", {})
    assert res.success is True
    assert "job" in res.result
    assert res.result["job"]["client_name"] == "Max Test Client"

    # 3. Verify attach_job_document
    attach_res = execute_tool("attach_job_document", {
        "job_id": "job_test_max_42",
        "title": "Fabric swatch note",
        "category": "note",
        "description": "Velvet 30 yards picked up"
    })
    assert attach_res.success is True

    # 4. Verify list_job_documents
    docs_res = execute_tool("list_job_documents", {"job_id": "job_test_max_42"})
    assert docs_res.success is True
    assert docs_res.result["count"] >= 1


def test_active_jobs_include_every_business_and_skip_closed(client):
    wr = _create_test_job(client, "Living room drapery", "Client A", "in_production", 4200, "workroom")
    wc = _create_test_job(client, "CNC panel set", "Client D", "ready", 1800, "woodcraft")
    closed = _create_test_job(client, "Closed drapery", "Client F", "lead", 900, "workroom")
    assert wr and wc and closed
    closed_move = client.patch(f"/api/v1/jobs/{closed}/stage", json={"stage": "paid_closed"})
    assert closed_move.status_code == 200
    assert closed_move.json()["job"]["canonical_stage"] == "paid_closed"

    active = client.get("/api/v1/jobs/active")
    assert active.status_code == 200
    jobs = active.json()["jobs"]
    ids = {j["id"] for j in jobs}
    assert wr in ids
    assert wc in ids
    assert closed not in ids
    units = {j.get("business_unit") for j in jobs if j["id"] in {wr, wc}}
    assert units == {"workroom", "woodcraft"}
    wr_row = next(j for j in jobs if j["id"] == wr)
    assert wr_row["canonical_stage"] == "in_production"


def test_move_to_next_phase_persists_and_logs_history(client):
    job_id = _create_test_job(client, "Banquette", "Client B", "lead", 1200, "workroom")
    first = client.patch(f"/api/v1/jobs/{job_id}/stage", json={"stage": "estimate_sent"})
    assert first.status_code == 200
    assert first.json()["job"]["canonical_stage"] == "estimate_sent"
    second = client.patch(f"/api/v1/jobs/{job_id}/stage", json={"stage": "deposit_paid"})
    assert second.status_code == 200

    timeline = client.get(f"/api/v1/jobs/{job_id}/timeline")
    changes = [e for e in timeline.json()["events"] if e.get("event_type") == "status_change"]
    assert len(changes) >= 2
    tos = [(e.get("metadata") or {}).get("to") for e in changes]
    assert "estimate_sent" in tos
    assert "deposit_paid" in tos

    detail = client.get(f"/api/v1/jobs/{job_id}")
    assert detail.json()["job"]["pipeline_stage"] == "deposit_paid"
