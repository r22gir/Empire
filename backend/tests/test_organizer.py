"""Empire Organizer: spaces, editions, create/move/conflict, day plan, capture, crew."""

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
    assert body["drafts"][0]["kind"] == "call"


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
    assert body["edition"] == "main"

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
    family = available_actions({**item, "space_id": "family"}, job)
    assert "send_quote" not in {a["id"] for a in family}
    assert "book_install" not in {a["id"] for a in family}


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

    cmd_again = client.post(
        "/api/v1/organizer/command",
        json={"text": "request deposit for Marley"},
    )
    assert cmd_again.status_code == 200, cmd_again.text
    assert cmd_again.json()["sent"] is False


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


def test_fail_closed_unknown_edition_never_reads_main(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "staging-xyz")
    from app.services.organizer.edition import (
        edition_sql,
        process_edition,
        read_edition_keys,
        ORGANIZER_MODEL,
    )
    assert process_edition() == "unknown"
    assert read_edition_keys() == ("unknown",)
    clause, keys = edition_sql()
    assert "main" not in keys
    assert "workroom" not in keys
    assert keys == ["unknown"]
    assert ORGANIZER_MODEL == "grok-4.6"
    assert "IN" in clause


def test_spaces_unified_view_is_not_job_only(client, isolated_empire_db):
    family = client.post(
        "/api/v1/organizer/items",
        json={"kind": "school", "title": "Kids recital", "space_id": "family", "start_time": "2026-10-22T18:00:00"},
    )
    personal = client.post(
        "/api/v1/organizer/items",
        json={"kind": "medical", "title": "Dentist", "space_id": "personal", "start_time": "2026-10-22T09:00:00"},
    )
    empire = client.post(
        "/api/v1/organizer/items",
        json={"kind": "meeting", "title": "Studio standup", "space_id": "empire", "start_time": "2026-10-22T11:00:00"},
    )
    assert family.status_code == 200, family.text
    assert personal.status_code == 200, personal.text
    assert empire.status_code == 200, empire.text
    board = client.get("/api/v1/organizer/board?start_date=2026-10-22&end_date=2026-10-22")
    assert board.status_code == 200
    items = board.json()["items"]
    titles = [i["title"] for i in items]
    assert "Kids recital" in titles
    assert "Dentist" in titles
    assert "Studio standup" in titles
    recital = next(i for i in items if i["title"] == "Kids recital")
    assert not recital.get("job_id")
    assert recital.get("space_id") == "family"
    assert "send_quote" not in {a["id"] for a in recital.get("actions") or []}
    fam = client.get("/api/v1/organizer/board?space_id=family&start_date=2026-10-22&end_date=2026-10-22").json()
    assert all((i.get("space_id") == "family") or i.get("read_only") for i in fam["items"])
    spaces = client.get("/api/v1/organizer/spaces").json()
    slugs = {s["slug"] for s in spaces["spaces"]}
    assert slugs >= {"workroom", "empire", "family", "personal", "ventures"}
    assert spaces["unified"] is True
    meta = client.get("/api/v1/organizer/meta").json()
    assert meta["model"] == "grok-4.6"
    assert meta["edition"]["edition"] == "main"
    assert meta["edition"]["assistant"] == "Max"


def test_maxine_hides_argos_and_workroom(client, isolated_empire_db, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    _customer_and_job(client, "Argos")
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    blocked = client.post(
        "/api/v1/organizer/items",
        json={"kind": "todo", "title": "Argos Campestre legal filing"},
    )
    assert blocked.status_code == 400
    ok = client.post(
        "/api/v1/organizer/items",
        json={"kind": "todo", "title": "School pickup", "space_id": "family"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["item"]["space_id"] == "family"
    board = client.get("/api/v1/organizer/board").json()
    blob = str(board).lower()
    assert "argos" not in blob
    assert "campestre" not in blob
    titles = [i["title"] for i in board["items"]]
    assert "School pickup" in titles
    resources = client.get("/api/v1/organizer/resources").json()
    assert resources["directory"] == []
    follow = client.get("/api/v1/organizer/follow-ups").json()
    assert follow["drafts"] == []
    meta = client.get("/api/v1/organizer/meta").json()
    assert meta["edition"]["edition"] == "maxine"
    assert meta["edition"]["allows_workroom_jobs"] is False
    slugs = {s["slug"] for s in meta["spaces"]}
    assert "workroom" not in slugs
    assert "argos" not in slugs
    assert meta["model"] == "grok-4.6"


def test_cross_edition_isolation(client, isolated_empire_db, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    main_item = client.post(
        "/api/v1/organizer/items",
        json={"kind": "todo", "title": "Workroom fabric order", "space_id": "workroom"},
    )
    assert main_item.status_code == 200, main_item.text
    from app.db.database import get_db
    from app.services.organizer.store import new_id, now_iso
    stamp = now_iso()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO organizer_items
               (id, kind, title, status, outbound_blocked, created_by, created_at, updated_at, edition, space_id)
               VALUES (?, 'todo', ?, 'open', 1, 'manual', ?, ?, 'maxine', 'personal')""",
            (new_id(), "Maxine dentist", stamp, stamp),
        )
        conn.execute(
            """INSERT INTO schedule_events
               (id, type, title, start_time, status, created_by, created_at, updated_at, edition, space_id, event_kind)
               VALUES (?, 'other', ?, '2026-10-20T10:00:00', 'planned', 'manual', ?, ?, 'maxine', 'personal', 'legal')""",
            (new_id(), "Argos Campestre legal", stamp, stamp),
        )
    board = client.get("/api/v1/organizer/board").json()["items"]
    titles = [i["title"] for i in board]
    assert "Workroom fabric order" in titles
    assert "Maxine dentist" not in titles
    assert "Argos Campestre legal" not in titles
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    board2 = client.get("/api/v1/organizer/board").json()
    titles2 = [i["title"] for i in board2["items"]]
    assert "Workroom fabric order" not in titles2
    assert "Maxine dentist" in titles2
    assert "argos" not in str(board2).lower()
    assert "campestre" not in str(board2).lower()


def test_max_e_has_full_organizer(client, isolated_empire_db, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "max_e")
    meta = client.get("/api/v1/organizer/meta").json()
    assert meta["edition"]["assistant"] == "Max-e"
    assert meta["edition"]["owner"] == "Juan"
    assert meta["edition"]["allows_workroom_jobs"] is False
    slugs = {s["slug"] for s in meta["spaces"]}
    assert "amp" in slugs
    assert "workroom" not in slugs
    res = client.post(
        "/api/v1/organizer/items",
        json={"kind": "todo", "title": "AMP coaching prep", "space_id": "amp"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["item"]["space_id"] == "amp"
    board = client.get("/api/v1/organizer/board").json()
    assert any(i["title"] == "AMP coaching prep" for i in board["items"])


def test_usage_cap_returns_429(client, isolated_empire_db, monkeypatch):
    from app.services.organizer import edition as edmod
    monkeypatch.setitem(edmod.USAGE_CAPS, "main", {"items": 1, "captures": 1, "actions": 1})
    first = client.post("/api/v1/organizer/items", json={"kind": "todo", "title": "one"})
    assert first.status_code == 200, first.text
    second = client.post("/api/v1/organizer/items", json={"kind": "todo", "title": "two"})
    assert second.status_code == 429
    detail = second.json()["detail"]
    assert detail["code"] == "usage_cap"
    assert detail["bucket"] == "items"


def _seed_inbox(rows):
    import app.services.organizer.mail as mailmod
    mailmod.TEST_INBOX = rows
    return mailmod


def _clear_inbox():
    import app.services.organizer.mail as mailmod
    mailmod.TEST_INBOX = None


def _sample_inbox():
    return [
        {
            "source": "gmail",
            "message_id": "m1",
            "from": "Marley <marley@example.com>",
            "to": "rafael@example.com",
            "subject": "Install date?",
            "date": "2026-10-10T12:00:00",
            "preview": "Can we move the drapery install?",
            "unread": True,
            "account": "gmail",
        },
        {
            "source": "outlook",
            "message_id": "o1",
            "from": "School Office <office@school.edu>",
            "subject": "Permission slip",
            "date": "2026-10-09T09:00:00",
            "preview": "Please sign for the kids field trip.",
            "unread": False,
            "account": "outlook",
        },
        {
            "source": "gmail",
            "message_id": "argos1",
            "from": "Counsel <legal@argos-campestre.com>",
            "subject": "Argos Campestre filing",
            "date": "2026-10-08T08:00:00",
            "preview": "Legal packet for Campestre",
            "unread": True,
            "account": "gmail",
        },
    ]


def test_pending_mail_lists_and_links_job(client, isolated_empire_db):
    _customer_and_job(client, "Marley")
    mailmod = _seed_inbox(_sample_inbox())
    try:
        meta = client.get("/api/v1/organizer/meta").json()
        assert meta["mail"]["read_only"] is True
        assert meta["mail"]["pending_path"] == "/api/v1/organizer/pending-mail"
        res = client.get("/api/v1/organizer/pending-mail")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["read_only"] is True
        assert body["sent"] is False
        ids = {i["message_id"] for i in body["items"]}
        assert ids == {"m1", "o1", "argos1"}
        marley = next(i for i in body["items"] if i["message_id"] == "m1")
        assert marley["job_title"]
        assert marley["space_id"] == "workroom"
        assert marley["waiting"] == "unanswered"
        assert "sent" not in (marley.get("suggested_reply") or "").lower()
        assert marley["suggested_reply"].startswith("Hi Marley")
        assert "Rafael" in marley["suggested_reply"]
        assert {a["id"] for a in marley["actions"]} == {"open", "draft_reply", "snooze", "todo", "followup"}
        school = next(i for i in body["items"] if i["message_id"] == "o1")
        assert school["space_id"] == "family"
        assert school["waiting"] == "waiting"
    finally:
        mailmod.TEST_INBOX = None


def test_draft_reply_goes_to_approval_queue_not_sent(client, isolated_empire_db):
    mailmod = _seed_inbox(_sample_inbox())
    try:
        res = client.post(
            "/api/v1/organizer/pending-mail/actions",
            json={
                "action": "draft_reply",
                "source": "gmail",
                "message_id": "m1",
                "confirm": True,
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["sent"] is False
        assert body["requires_confirm"] is True
        assert body["approval"]["status"] == "pending"
        assert body["approval"]["source"] == "organizer_mail"
        queue = list_queue()
        drafts = [i for i in queue["items"] if i.get("source") == "organizer_mail"]
        assert drafts
        assert all(i["status"] == "pending" for i in drafts)
        assert all(i.get("sent_at") in (None, "") for i in drafts)
        assert "install" in (drafts[0].get("body") or "").lower()
    finally:
        mailmod.TEST_INBOX = None


def test_snooze_hides_and_todo_creates_item(client, isolated_empire_db):
    mailmod = _seed_inbox(_sample_inbox())
    try:
        snooze = client.post(
            "/api/v1/organizer/pending-mail/actions",
            json={
                "action": "snooze",
                "source": "gmail",
                "message_id": "m1",
                "snooze_until": "2099-01-01T00:00:00",
            },
        )
        assert snooze.status_code == 200, snooze.text
        assert snooze.json()["sent"] is False
        listed = client.get("/api/v1/organizer/pending-mail").json()
        assert "m1" not in {i["message_id"] for i in listed["items"]}

        todo = client.post(
            "/api/v1/organizer/pending-mail/actions",
            json={"action": "todo", "source": "outlook", "message_id": "o1"},
        )
        assert todo.status_code == 200, todo.text
        created = todo.json()["created"]
        assert created["kind"] == "todo"
        assert "Permission slip" in created["title"]
        assert todo.json()["sent"] is False
        listed2 = client.get("/api/v1/organizer/pending-mail").json()
        assert "o1" not in {i["message_id"] for i in listed2["items"]}
        board = client.get("/api/v1/organizer/board").json()
        assert any(i["title"] == created["title"] for i in board["items"])

        follow = client.post(
            "/api/v1/organizer/pending-mail/actions",
            json={"action": "followup", "source": "gmail", "message_id": "argos1"},
        )
        assert follow.status_code == 200, follow.text
        assert follow.json()["created"]["kind"] == "followup"
        missing = client.post(
            "/api/v1/organizer/pending-mail/actions",
            json={"action": "todo", "source": "gmail", "message_id": "nope"},
        )
        assert missing.status_code == 404
    finally:
        mailmod.TEST_INBOX = None


def test_maxine_pending_mail_drops_argos_and_never_reads_main(client, isolated_empire_db, monkeypatch):
    called = {"gmail": 0, "outlook": 0}

    def fake_gmail(**_kw):
        called["gmail"] += 1
        return {"success": True, "emails": [{"id": "r1", "from": "Rafael", "subject": "Workroom", "preview": "x"}]}

    def fake_outlook(**_kw):
        called["outlook"] += 1
        return {"success": True, "emails": []}

    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.delenv("GMAIL_TOKEN_PATH_MAXINE", raising=False)
    monkeypatch.delenv("OUTLOOK_TOKEN_PATH_MAXINE", raising=False)
    monkeypatch.setattr("app.services.max.gmail_reader.check_inbox", fake_gmail)
    monkeypatch.setattr("app.services.max.outlook_reader.search_messages", fake_outlook)
    _clear_inbox()
    empty = client.get("/api/v1/organizer/pending-mail")
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["accounts"]["edition"] == "maxine"
    assert empty.json()["accounts"]["connected"] == []
    assert called["gmail"] == 0
    assert called["outlook"] == 0

    mailmod = _seed_inbox(_sample_inbox())
    try:
        body = client.get("/api/v1/organizer/pending-mail").json()
        blob = str(body).lower()
        assert "argos" not in blob
        assert "campestre" not in blob
        ids = {i["message_id"] for i in body["items"]}
        assert "argos1" not in ids
        assert "o1" in ids
        assert body["read_only"] is True
        assert called["gmail"] == 0
    finally:
        mailmod.TEST_INBOX = None


def test_mailbox_token_paths_refuse_main_token(tmp_path, monkeypatch):
    main_token = tmp_path / "rafael_gmail.json"
    main_token.write_text("{}")
    family_token = tmp_path / "camilo_gmail.json"
    family_token.write_text("{}")
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(main_token))
    monkeypatch.setenv("GMAIL_TOKEN_PATH_MAXINE", str(main_token))
    from app.services.organizer.edition import mailbox_token_paths
    leaked = mailbox_token_paths("maxine")
    assert leaked["gmail"] is None
    assert "gmail" not in leaked["sources"]
    assert leaked["edition"] == "maxine"

    monkeypatch.setenv("GMAIL_TOKEN_PATH_MAXINE", str(family_token))
    own = mailbox_token_paths("maxine")
    assert own["gmail"] == family_token.resolve()
    assert "gmail" in own["sources"]

    unknown = mailbox_token_paths("staging-xyz")
    assert unknown["edition"] == "unknown"
    assert unknown["sources"] == []
    assert unknown["gmail"] is None

    main = mailbox_token_paths("main")
    assert main["gmail"] == main_token.resolve()


def test_event_select_sql_nulls_missing_job_columns(isolated_empire_db):
    """init_db jobs may lack client_name — listing events must not SELECT a missing col."""
    import sqlite3
    from app.services.organizer.store import event_select_sql

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE jobs (id TEXT, title TEXT)")
    sql = event_select_sql(conn)
    assert "j.client_name" not in sql
    assert "NULL as client_name" in sql
    assert "j.title as job_title" in sql
    conn.close()


def test_today_and_schedule_list_ok_on_isolated_schema(client, isolated_empire_db):
    ev = client.post("/api/v1/schedule/events", json={
        "title": "Lean-schema install",
        "type": "install",
        "start_time": date.today().isoformat() + "T09:00:00",
        "end_time": date.today().isoformat() + "T10:00:00",
        "status": "planned",
    })
    assert ev.status_code == 200, ev.text
    today = client.get("/api/v1/organizer/today")
    assert today.status_code == 200, today.text
    listed = client.get("/api/v1/schedule/events")
    assert listed.status_code == 200, listed.text
    assert listed.json()["count"] >= 1


def test_spaces_have_icon_color_and_are_configurable(client, isolated_empire_db):
    spaces = client.get("/api/v1/organizer/spaces").json()["spaces"]
    slugs = {s["slug"]: s for s in spaces}
    assert slugs["family"]["icon"]
    assert slugs["family"]["accent_color"].startswith("#")
    assert slugs["workroom"]["accent_color"].startswith("#")
    patched = client.patch(
        "/api/v1/organizer/spaces/family",
        json={"icon": "🎈", "accent_color": "#db2777"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["space"]["icon"] == "🎈"
    assert patched.json()["space"]["accent_color"] == "#db2777"
    meta = client.get("/api/v1/organizer/meta").json()
    assert "overdue" in meta["today_columns"]
    assert {c["id"] for c in meta["columns"]} == {"open", "doing", "done"}


def test_today_buckets_across_all_spaces(client, isolated_empire_db):
    today = date.today()
    client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Late family form", "space_id": "family",
        "due_at": (today - timedelta(days=2)).isoformat() + "T09:00:00",
    })
    client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Empire standup", "space_id": "empire",
        "due_at": today.isoformat() + "T10:00:00",
    })
    client.post("/api/v1/organizer/items", json={
        "kind": "medical", "title": "Personal checkup", "space_id": "personal",
        "start_time": (today + timedelta(days=3)).isoformat() + "T15:00:00",
    })
    body = client.get("/api/v1/organizer/today").json()
    assert {i["title"] for i in body["overdue"]} >= {"Late family form"}
    assert {i["title"] for i in body["today"]} >= {"Empire standup"}
    assert {i["title"] for i in body["upcoming"]} >= {"Personal checkup"}
    assert body["open_organizer_href"] == "/?screen=calendar"
    assert any(s.get("icon") for s in body["spaces"])


def test_create_several_items_returns_distinct_ids(client, isolated_empire_db):
    ids = []
    for i in range(5):
        res = client.post("/api/v1/organizer/items", json={"kind": "todo", "title": f"Burst {i}"})
        assert res.status_code == 200, res.text
        item = res.json()["item"]
        assert item["id"]
        ids.append(item["id"])
    assert len(set(ids)) == 5


def test_column_move_and_job_progress_and_links(client, isolated_empire_db):
    cid, job_id = _customer_and_job(client, "Marley")
    a = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Cut fabric", "job_id": job_id, "space_id": "workroom",
    })
    b = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Sew panels", "job_id": job_id, "space_id": "workroom",
    })
    assert a.status_code == 200 and b.status_code == 200
    aid, bid = a.json()["item"]["id"], b.json()["item"]["id"]
    assert aid != bid
    moved = client.post(f"/api/v1/organizer/items/{aid}/move", json={"column": "done"})
    assert moved.status_code == 200
    assert moved.json()["item"]["status"] == "done"
    prog = client.get(f"/api/v1/organizer/jobs/{job_id}/progress").json()
    assert prog["fraction"] == "1/2"
    assert prog["percent"] == 50
    item = b.json()["item"]
    kinds = {l["kind"] for l in item.get("record_links") or []}
    assert "job" in kinds
    assert "client" in kinds
    job_link = next(l for l in item["record_links"] if l["kind"] == "job")
    assert "job=" in job_link["href"]
    today_move = client.post(f"/api/v1/organizer/items/{bid}/move", json={"column": "today"})
    assert today_move.status_code == 200
    assert today_move.json()["item"]["due_at"].startswith(date.today().isoformat())


def test_reminder_persisted_and_dispatched_through_notifications(client, isolated_empire_db):
    past = (date.today() - timedelta(days=1)).isoformat() + "T08:00:00"
    res = client.post("/api/v1/organizer/reminder-draft", json={
        "title": "Call the school",
        "due_at": past,
        "body": "Remind Rafael",
        "channel": "max",
        "space_id": "family",
    })
    assert res.status_code == 200, res.text
    assert res.json()["sent"] is False
    assert res.json()["reminder"]["id"]
    listed = client.get("/api/v1/organizer/reminders?status=pending").json()["reminders"]
    assert any(r["title"] == "Call the school" for r in listed)
    fired = client.post("/api/v1/organizer/reminders/dispatch").json()
    assert fired["dispatched"] >= 1
    assert fired["outbound_sent"] is False
    from app.routers.notifications import notifications_db
    assert any("Call the school" in (n.get("title") or "") for n in notifications_db)


def test_quick_add_photo_attaches_capture(client, isolated_empire_db):
    import base64
    png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    ).decode()
    draft = client.post("/api/v1/organizer/quick-add", json={"text": "dentist Thursday 3pm"})
    assert draft.status_code == 200
    saved = client.post("/api/v1/organizer/quick-add", json={
        "text": "dentist Thursday 3pm",
        "confirm": True,
        "photo_b64": png,
        "filename": "tooth.png",
        "mime": "image/png",
    })
    assert saved.status_code == 200, saved.text
    created = saved.json()["created"]
    assert created[0]["id"]
    assert created[0]["item"]["id"] == created[0]["id"]
    assert created[0].get("capture", {}).get("id")


def test_organizer_package_uses_grok_46_only():
    from pathlib import Path
    from app.services.organizer.edition import ORGANIZER_MODEL
    assert ORGANIZER_MODEL == "grok-4.6"
    root = Path(__file__).resolve().parents[1] / "app" / "services" / "organizer"
    banned = ("gpt-", "claude-", "grok-3", "grok-4-fast", "llama", "gemini")
    for path in root.glob("*.py"):
        text = path.read_text()
        for needle in banned:
            assert needle not in text, f"{path.name} mentions {needle}"
        if "model" in text.lower() and "ORGANIZER_MODEL" in text:
            assert "grok-4.6" in text
