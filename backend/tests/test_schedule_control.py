"""
Tests for GOAL B: Schedule Control App & Pickup / Drop-off Log.
Tests CRUD endpoints, date range filtering, today summary, pickup/drop-off custody log,
and Max schedule tools (list_schedule, add_schedule_event, log_pickup_dropoff, propose_schedule_from_text).

Ensures 100% temporary database isolation (NO live DB writes).
"""
import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.max.tool_executor import execute_tool, TOOL_REGISTRY


@pytest.fixture
def client():
    return TestClient(app)


def test_schedule_events_crud_and_isolation(client, isolated_empire_db):
    """Verify schedule events CRUD operations run against isolated DB."""
    assert os.environ.get("EMPIRE_TASK_DB") == isolated_empire_db

    # 1. Create a schedule event
    payload = {
        "title": "Install Drapes at Old Courthouse Rd",
        "type": "install",
        "customer_vendor": "Whittington Design",
        "location_address": "9408 Old Courthouse Rd, Vienna VA",
        "start_time": "2026-10-15T09:00:00",
        "end_time": "2026-10-15T12:00:00",
        "status": "planned",
        "notes": "Bring tall step ladder and brackets",
        "created_by": "manual",
    }
    res = client.post("/api/v1/schedule/events", json=payload)
    assert res.status_code == 200, res.text
    created = res.json()
    event_id = created["id"]
    assert created["title"] == payload["title"]
    assert created["type"] == "install"
    assert created["status"] == "planned"
    assert created["customer_vendor"] == "Whittington Design"

    # 2. List events with date range
    list_res = client.get("/api/v1/schedule/events?start_date=2026-10-01&end_date=2026-10-31")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["count"] >= 1
    found = any(e["id"] == event_id for e in data["events"])
    assert found

    # 3. Get single event
    get_res = client.get(f"/api/v1/schedule/events/{event_id}")
    assert get_res.status_code == 200
    event_data = get_res.json()
    assert event_data["id"] == event_id
    assert event_data["location_address"] == "9408 Old Courthouse Rd, Vienna VA"

    # 4. Update event status to confirmed
    put_res = client.put(f"/api/v1/schedule/events/{event_id}", json={"status": "confirmed", "notes": "Confirmed with designer"})
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["status"] == "confirmed"
    assert updated["notes"] == "Confirmed with designer"

    # 5. Delete event
    del_res = client.delete(f"/api/v1/schedule/events/{event_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 6. Verify deleted
    get_after = client.get(f"/api/v1/schedule/events/{event_id}")
    assert get_after.status_code == 404


def test_pickup_dropoff_custody_log(client, isolated_empire_db):
    """Verify pickup and drop-off log entries record custody changes and link to events."""
    # Create an event first
    ev_res = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Pick up fabrics at Whittington Design",
            "type": "pickup",
            "customer_vendor": "Whittington Design",
            "start_time": "2026-10-12T14:00:00",
            "status": "planned",
        },
    )
    assert ev_res.status_code == 200
    ev_id = ev_res.json()["id"]

    # Post a custody log entry linking to the event
    log_payload = {
        "schedule_event_id": ev_id,
        "direction": "picked_up",
        "items": "3 rolls velvet drapery fabric, 1 box tassels",
        "party": "Whittington Design",
        "notes": "Signed by Sarah at front desk",
        "created_by": "manual",
    }
    log_res = client.post("/api/v1/schedule/pickup-dropoff-logs", json=log_payload)
    assert log_res.status_code == 200, log_res.text
    log_data = log_res.json()
    assert log_data["items"] == "3 rolls velvet drapery fabric, 1 box tassels"
    assert log_data["direction"] == "picked_up"

    # Event status should now be updated to done
    ev_after = client.get(f"/api/v1/schedule/events/{ev_id}").json()
    assert ev_after["status"] == "done"
    assert len(ev_after["logs"]) == 1
    assert ev_after["logs"][0]["id"] == log_data["id"]

    # List logs by direction
    filter_res = client.get("/api/v1/schedule/pickup-dropoff-logs?direction=picked_up")
    assert filter_res.status_code == 200
    logs = filter_res.json()["logs"]
    assert any(l["id"] == log_data["id"] for l in logs)


def test_today_summary_endpoint(client, isolated_empire_db):
    """Verify today's schedule summary endpoint returns correct aggregation."""
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Create one today event
    client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Loading Dock Reservation - Freight Delivery",
            "type": "loading_dock",
            "start_time": f"{today_str}T11:00:00",
            "status": "confirmed",
        },
    )

    summary_res = client.get("/api/v1/schedule/today-summary")
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert data["date"] == today_str
    assert data["total_events_today"] >= 1
    assert "loading_dock" in data["counts_by_type"]


def test_draft_proposal_helper_no_db_write(client, isolated_empire_db):
    """Verify text proposal helper extracts draft events WITHOUT writing to DB."""
    email_text = (
        "Hi Rafael, our client confirmed the measure for next Thursday Oct 15 at 10:30am "
        "at 1200 Grand Ave with Whittington Design. Also reserved the loading dock."
    )
    res = client.post("/api/v1/schedule/propose-events", json={"text": email_text})
    assert res.status_code == 200
    result = res.json()
    assert "proposals" in result
    assert result["is_draft_only"] is True
    assert len(result["proposals"]) >= 1

    # Verify NO events were added to DB
    list_res = client.get("/api/v1/schedule/events")
    events = list_res.json()["events"]
    assert not any("1200 Grand Ave" in (e.get("location_address") or "") for e in events)
    assert not any("1200 Grand Ave" in (e.get("location_address") or "") for e in events)


def test_max_schedule_tools_execution(isolated_empire_db):
    """Verify Max tools: add_schedule_event (with echo), list_schedule, log_pickup_dropoff, and propose."""
    assert "add_schedule_event" in TOOL_REGISTRY
    assert "list_schedule" in TOOL_REGISTRY
    assert "log_pickup_dropoff" in TOOL_REGISTRY
    assert "propose_schedule_from_text" in TOOL_REGISTRY

    # 1. Max adds schedule event
    add_call = {
        "tool": "add_schedule_event",
        "title": "Pick up cushion covers",
        "type": "pickup",
        "customer_vendor": "Whittington Design",
        "start_time": "2026-10-14T15:00:00",
        "location_address": "8400 Westpark Dr, McLean VA",
    }
    result = execute_tool(add_call)
    assert result.success is True, result.error
    assert "echo_confirmation" in result.result
    assert "Scheduled 'Pick up cushion covers'" in result.result["echo_confirmation"]
    assert "2026-10-14T15:00:00" in result.result["echo_confirmation"]
    event_id = result.result["event_id"]

    # 2. Max lists schedule
    list_call = {
        "tool": "list_schedule",
        "type": "pickup",
    }
    list_result = execute_tool(list_call)
    assert list_result.success is True
    assert list_result.result["count"] >= 1
    assert any(e["id"] == event_id for e in list_result.result["events"])

    # 3. Max logs pickup/dropoff custody transfer
    log_call = {
        "tool": "log_pickup_dropoff",
        "direction": "picked_up",
        "items": "fabrics and cushion covers",
        "party": "Whittington Design",
        "notes": "Picked up from front desk",
    }
    log_result = execute_tool(log_call)
    assert log_result.success is True
    assert "Picked up fabrics and cushion covers" in log_result.result["summary"]
    assert log_result.result["party"] == "Whittington Design"

    # 4. Max proposal draft helper
    prop_call = {
        "tool": "propose_schedule_from_text",
        "text": "Please schedule an install with Whittington Design tomorrow at 9am at 500 Park Ave",
    }
    prop_result = execute_tool(prop_call)
    assert prop_result.success is True
    assert "DRAFT ONLY" in prop_result.result["notice"]
    assert prop_result.result["proposals_count"] >= 1
