"""Workroom Organizer: create/move/conflict, day plan, follow-ups, capture, crew."""

from __future__ import annotations

import base64
import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db
from app.services.organizer.conflicts import detect_conflicts
from app.services.organizer.parse import parse_quick_add
from app.services.organizer.followups import detect_followups
from app.services.organizer.dayplan import propose_day
from app.services.max.tool_executor import execute_tool, TOOL_REGISTRY
from app.services.organizer.actions import parse_command, available_actions
from app.services.leadforge.growth import list_queue


@pytest.fixture
def client():
    return TestClient(app)


def _customer_and_job(client, name="Marley"):
    with get_db() as conn:
        cid = f"c_{name.lower()[:6]}"
        conn.execute(
            "INSERT OR IGNORE INTO customers (id, name, phone, address, business) VALUES (?, ?, ?, ?, 'workroom')",
            (cid, name, "2025550199", "1200 Grand Ave, Hyattsville MD"),
        )
    res = client.post(
        "/api/v1/jobs",
        json={
            "title": f"{name} drapery",
            "customer_id": cid,
            "client_name": name,
            "status": "scheduled",
            "business_unit": "workroom",
            "address": "1200 Grand Ave, Hyattsville MD",
        },
    )
    assert res.status_code == 200, res.text
    job = res.json().get("job") or res.json()
    return cid, job.get("id")


def test_schedule_create_move_conflict(client, isolated_empire_db):
    assert os.environ.get("EMPIRE_TASK_DB") == isolated_empire_db
    crew = client.post(
        "/api/v1/organizer/resources",
        json={"name": "Luis", "role": "installer", "phone": "2025550100"},
    )
    assert crew.status_code == 200, crew.text
    rid = crew.json()["id"]

    a = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Install Marley living room",
            "type": "install",
            "start_time": "2026-10-17T10:00:00",
            "end_time": "2026-10-17T12:00:00",
            "location_address": "1200 Grand Ave",
            "assigned_resource_ids": [rid],
        },
    )
    assert a.status_code == 200, a.text
    ev_a = a.json()
    assert ev_a["type"] == "install"
    assert ev_a["call_link"] or ev_a.get("assigned_resource_ids") == [rid]
    assert ev_a["map_link"]

    clash = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Install other house",
            "type": "install",
            "start_time": "2026-10-17T11:00:00",
            "end_time": "2026-10-17T13:00:00",
            "location_address": "500 Park Ave",
            "assigned_resource_ids": [rid],
        },
    )
    assert clash.status_code == 409, clash.text
    detail = clash.json()["detail"]
    assert detail["silent_overwrite"] is False
    assert any(c["code"] == "double_booked_person" for c in detail["conflicts"])

    forced = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Install other house",
            "type": "install",
            "start_time": "2026-10-17T11:00:00",
            "end_time": "2026-10-17T13:00:00",
            "location_address": "500 Park Ave",
            "assigned_resource_ids": [rid],
            "confirm_conflicts": True,
        },
    )
    assert forced.status_code == 200, forced.text

    move = client.post(
        f"/api/v1/schedule/events/{ev_a['id']}/move",
        json={"start_time": "2026-10-17T11:30:00", "end_time": "2026-10-17T13:30:00"},
    )
    assert move.status_code == 409
    ok_move = client.post(
        f"/api/v1/schedule/events/{ev_a['id']}/move",
        json={
            "start_time": "2026-10-18T09:00:00",
            "end_time": "2026-10-18T11:00:00",
            "confirm_conflicts": True,
        },
    )
    assert ok_move.status_code == 200
    assert ok_move.json()["start_time"].startswith("2026-10-18T09:00")


def test_new_event_kinds_and_fitting(client, isolated_empire_db):
    res = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Fitting — Marley",
            "type": "fitting",
            "start_time": "2026-10-20T14:00:00",
            "end_time": "2026-10-20T15:00:00",
            "phone": "2025550199",
            "location_address": "1200 Grand Ave",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["type"] == "fitting"
    assert body["kind"] == "fitting"
    assert body["call_link"] == "tel:2025550199"
    assert "maps.google.com" in (body["map_link"] or "")


def test_conflict_helper_travel_gap():
    hits = detect_conflicts(
        {
            "id": "b",
            "start_time": "2026-10-17T13:10:00",
            "end_time": "2026-10-17T14:00:00",
            "location_address": "Vienna VA",
            "assigned_resource_ids": ["r1"],
            "travel_minutes": 30,
        },
        [
            {
                "id": "a",
                "title": "Pickup fabric",
                "start_time": "2026-10-17T12:00:00",
                "end_time": "2026-10-17T13:00:00",
                "location_address": "Hyattsville MD",
                "assigned_resource_ids": ["r1"],
                "assigned_names": ["Luis"],
            }
        ],
    )
    assert any(h["code"] == "travel_gap" for h in hits)


def test_quick_add_and_max_draft(client, isolated_empire_db):
    _customer_and_job(client, "Marley")
    draft = parse_quick_add("call Marley Friday 2pm", today=date(2026, 10, 16))
    assert draft["kind"] == "call"
    assert draft["start_time"].endswith("T14:00:00")
    assert draft["is_draft_only"] is True
    assert "Marley" in (draft.get("subject_name") or "")

    install = parse_quick_add(
        "schedule install for the Marley job Friday 10am",
        today=date(2026, 10, 16),
    )
    assert install["kind"] == "install"
    assert install["start_time"].endswith("T10:00:00")

    res = client.post("/api/v1/organizer/quick-add", json={"text": "call Marley Friday 2pm"})
    assert res.status_code == 200
    body = res.json()
    assert body["is_draft_only"] is True
    assert body["created"] == []
    assert body["drafts"][0]["job_id"]

    assert "draft_organizer_item" in TOOL_REGISTRY
    tool = execute_tool({"tool": "draft_organizer_item", "text": "schedule install for the Marley job Friday 10am"})
    assert tool.success is True
    assert tool.result["saved"] is False
    assert tool.result["sent"] is False
    assert tool.result["draft"]["kind"] == "install"


def test_day_plan_route_followups_ics(client, isolated_empire_db):
    today = date.today().isoformat()
    client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Pickup Whittington",
            "type": "pickup",
            "start_time": f"{today}T09:00:00",
            "end_time": f"{today}T10:00:00",
            "location_address": "8400 Westpark Dr, McLean VA",
        },
    )
    client.post(
        "/api/v1/organizer/items",
        json={"kind": "todo", "title": "Cut lining for Marley", "due_at": f"{today}T17:00:00"},
    )
    plan = client.get("/api/v1/organizer/day-plan")
    assert plan.status_code == 200, plan.text
    data = plan.json()
    assert data["requires_approval"] is True
    assert data["approved"] is False
    approved = client.post("/api/v1/organizer/day-plan/approve")
    assert approved.status_code == 200
    assert approved.json()["approved"] is True
    assert approved.json()["sent"] is False

    route = client.get("/api/v1/organizer/route")
    assert route.status_code == 200
    r = route.json()
    assert r["live_traffic"] is False
    assert r["stops"]

    today_home = client.get("/api/v1/organizer/today")
    assert today_home.status_code == 200
    assert today_home.json()["open_organizer_href"] == "/?screen=calendar"

    ics = client.get("/api/v1/organizer/export.ics")
    assert ics.status_code == 200
    assert "BEGIN:VCALENDAR" in ics.text
    assert "Pickup Whittington" in ics.text

    gcal = client.get("/api/v1/organizer/google-sync/status")
    assert gcal.json()["available"] is False
    assert "No Google Calendar connector" in gcal.json()["note"]

    stale = detect_followups(
        quotes=[{
            "id": "q1",
            "quote_number": "EST-1",
            "status": "sent",
            "customer_name": "Marley",
            "sent_at": (date.today() - timedelta(days=10)).isoformat(),
            "deposit_required": 0,
            "deposit_paid": 0,
        }],
        jobs=[{
            "id": "j1",
            "client_name": "Marley",
            "pipeline_stage": "fabric_ordered",
            "updated_at": (date.today() - timedelta(days=14)).isoformat(),
        }],
    )
    kinds = {d["followup_kind"] for d in stale}
    assert "quote" in kinds
    assert any("fabric" in d["title"].lower() for d in stale)
    assert all(d["sent"] is False for d in stale)


def test_capture_edition_isolation_and_crew(client, isolated_empire_db, tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    ).decode()
    # JPEG-ish bytes with allowed mime
    payload = {
        "filename": "measure.jpg",
        "mime": "image/jpeg",
        "content_b64": base64.b64encode(b"\xff\xd8\xff" + b"x" * 80).decode(),
        "caption": "measure notes for Marley",
        "source": "upload",
    }
    res = client.post("/api/v1/organizer/captures/ingest", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["public_url"] is None
    assert body["public_url_blocked"] is True
    assert body["edition"] == "workroom"

    rejected = client.post(
        "/api/v1/organizer/captures/ingest",
        json={"filename": "hack.exe", "mime": "application/x-msdownload", "content_b64": base64.b64encode(b"MZ").decode()},
    )
    assert rejected.status_code == 400

    crew = client.post("/api/v1/organizer/resources", json={"name": "Ana", "role": "installer"})
    rid = crew.json()["id"]
    ev = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Install Ana only",
            "type": "install",
            "start_time": f"{date.today().isoformat()}T11:00:00",
            "end_time": f"{date.today().isoformat()}T13:00:00",
            "location_address": "9408 Old Courthouse Rd",
            "assigned_resource_ids": [rid],
        },
    ).json()
    other = client.post("/api/v1/organizer/resources", json={"name": "Other", "role": "driver"}).json()
    client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Secret other stop",
            "type": "pickup",
            "start_time": f"{date.today().isoformat()}T15:00:00",
            "assigned_resource_ids": [other["id"]],
        },
    )
    tok = client.post(f"/api/v1/organizer/crew-tokens?resource_id={rid}")
    assert tok.status_code == 200
    token = tok.json()["token"]
    day = client.get(f"/api/v1/organizer/crew/{token}/today")
    assert day.status_code == 200
    titles = [i["title"] for i in day.json()["items"]]
    assert "Install Ana only" in titles
    assert "Secret other stop" not in titles

    check = client.post(f"/api/v1/organizer/crew/{token}/check-in", params={"event_id": ev["id"]})
    assert check.status_code == 200
    done = client.post(
        f"/api/v1/organizer/crew/{token}/done",
        json={
            "event_id": ev["id"],
            "filename": "done.jpg",
            "mime": "image/jpeg",
            "content_b64": base64.b64encode(b"\xff\xd8\xff" + b"y" * 80).decode(),
        },
    )
    assert done.status_code == 200
    assert done.json()["public_url"] is None
    assert client.get(f"/api/v1/schedule/events/{ev['id']}").json()["status"] == "done"


def test_reminder_never_sends(client, isolated_empire_db):
    res = client.post(
        "/api/v1/organizer/reminder-draft",
        json={"title": "Nudge Marley", "body": "Just checking in", "channel": "sms"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["sent"] is False
    assert body["outbound_blocked"] is True
    assert "draft" in body["message"].lower()


def test_parse_command_move_marley():
    cmd = parse_command("move Marley's install to Friday and tell the crew", today=date(2026, 10, 11))
    assert cmd["command"] == "move"
    assert cmd["tell_crew"] is True
    assert (cmd.get("subject_name") or "").lower().startswith("marley")
    assert (cmd.get("start_time") or "").startswith("2026-10-16")


def test_available_actions_stop_and_job():
    item = {
        "id": "e1",
        "kind": "install",
        "title": "Install Marley",
        "phone": "2025550199",
        "location_address": "1200 Grand Ave",
        "start_time": "2026-10-17T10:00:00",
        "job_id": "j1",
    }
    job = {"id": "j1", "client_name": "Marley", "customer_phone": "2025550199", "customer_email": "a@b.com"}
    ids = {a["id"] for a in available_actions(item, job)}
    assert {"navigate", "call", "text", "send_quote", "order_fabric", "request_deposit", "book_install", "notify_crew"} <= ids


def test_board_actions_and_job_buttons(client, isolated_empire_db):
    cid, job_id = _customer_and_job(client, "Marley")
    ev = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Install Marley living room",
            "type": "install",
            "job_id": job_id,
            "start_time": "2026-10-17T10:00:00",
            "end_time": "2026-10-17T12:00:00",
            "location_address": "1200 Grand Ave",
            "phone": "2025550199",
        },
    )
    assert ev.status_code == 200, ev.text
    board = client.get("/api/v1/organizer/board?start_date=2026-10-17&end_date=2026-10-17")
    assert board.status_code == 200
    items = board.json()["items"]
    hit = next(i for i in items if i.get("id") == ev.json()["id"])
    ids = {a["id"] for a in hit.get("actions") or []}
    assert "navigate" in ids
    assert "call" in ids
    assert "text" in ids
    assert "send_quote" in ids
    assert "book_install" in ids


def test_send_quote_and_deposit_are_drafts(client, isolated_empire_db):
    cid, job_id = _customer_and_job(client, "Marley")
    quote = client.post(
        "/api/v1/organizer/actions",
        json={"action": "send_quote", "item": {"title": "Marley drapery", "job_id": job_id}, "job_id": job_id},
    )
    assert quote.status_code == 200, quote.text
    body = quote.json()
    assert body["sent"] is False
    assert body["approval"]
    assert body["approval"].get("status") in (None, "pending") or body["approval"].get("id")

    deposit = client.post(
        "/api/v1/organizer/actions",
        json={"action": "request_deposit", "item": {"title": "Marley drapery", "job_id": job_id}, "job_id": job_id},
    )
    assert deposit.status_code == 200, deposit.text
    assert deposit.json()["sent"] is False
    queued = list_queue(status="pending")
    assert queued["items"]
    assert all(i.get("status") == "pending" for i in queued["items"])


def test_approve_send_without_confirm_does_not_send(client, isolated_empire_db):
    res = client.post(
        "/api/v1/organizer/actions",
        json={
            "action": "approve_send",
            "confirm": False,
            "item": {
                "kind": "followup",
                "title": "Nudge Marley",
                "reminder_draft": "Hi Marley, just checking in.",
            },
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["sent"] is False
    assert body["requires_confirm"] is True
    assert "draft" in (body.get("message") or "").lower() or body["approval"]
    queued = list_queue(status="pending")
    assert any("Marley" in (i.get("body") or "") or "checking" in (i.get("body") or "") for i in queued["items"])


def test_command_move_and_crew_draft(client, isolated_empire_db):
    cid, job_id = _customer_and_job(client, "Marley")
    ev = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Install Marley living room",
            "type": "install",
            "job_id": job_id,
            "start_time": "2026-10-12T10:00:00",
            "end_time": "2026-10-12T12:00:00",
            "location_address": "1200 Grand Ave",
        },
    )
    assert ev.status_code == 200, ev.text
    ev_id = ev.json()["id"]
    moved = client.post(
        "/api/v1/organizer/command",
        json={"text": "move Marley's install to Friday and tell the crew"},
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["ok"] is True
    assert body["sent"] is False
    assert body["event_id"] == ev_id
    assert body["crew_draft"]
    assert body["crew_draft"]["sent"] is False
    fresh = client.get(f"/api/v1/schedule/events/{ev_id}")
    assert fresh.status_code == 200
    # Friday relative to "today" (2026-10-11 in this environment) or the next Friday.
    assert fresh.json()["start_time"] != "2026-10-12T10:00:00"

    tool = execute_tool({"tool": "run_organizer_command", "text": "request deposit for Marley"})
    assert tool.success is True
    assert tool.result["sent"] is False


def test_move_with_notify_crew_flag(client, isolated_empire_db):
    ev = client.post(
        "/api/v1/schedule/events",
        json={
            "title": "Pickup fabric",
            "type": "pickup",
            "start_time": "2026-10-19T09:00:00",
            "end_time": "2026-10-19T10:00:00",
            "location_address": "Whittington",
        },
    ).json()
    moved = client.post(
        f"/api/v1/schedule/events/{ev['id']}/move",
        json={"start_time": "2026-10-20T09:00:00", "end_time": "2026-10-20T10:00:00", "notify_crew": True},
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["start_time"].startswith("2026-10-20T09:00")
    assert body.get("crew_draft")
    assert body.get("sent") is False
