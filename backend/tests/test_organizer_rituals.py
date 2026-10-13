"""Evening shutdown and weekly review across every life/business area.

Isolated temp DB only. Never sends. Never writes live quotes.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.services.organizer.review import apply_shutdown_moves, evening_shutdown, weekly_review


client = TestClient(app)


def test_evening_shutdown_across_spaces(isolated_empire_db):
    assert os.environ.get("EMPIRE_TASK_DB") == isolated_empire_db
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat() + "T09:00:00"
    tomorrow = (date.today() + timedelta(days=1)).isoformat() + "T10:00:00"
    family = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "School form", "space_id": "family",
        "due_at": yesterday,
    }).json()["item"]
    work = client.post("/api/v1/organizer/items", json={
        "kind": "call", "title": "Call Nelma", "space_id": "workroom",
        "due_at": today + "T11:00:00",
    }).json()["item"]
    personal = client.post("/api/v1/organizer/items", json={
        "kind": "medical", "title": "Dentist follow-up", "space_id": "personal",
        "due_at": tomorrow,
    }).json()["item"]
    done = client.post("/api/v1/organizer/items", json={
        "kind": "todo", "title": "Pay AMP invoice note", "space_id": "empire",
        "due_at": today + "T08:00:00", "status": "done",
    }).json()["item"]

    pack = client.get(f"/api/v1/organizer/review/shutdown?plan_date={today}")
    assert pack.status_code == 200, pack.text
    body = pack.json()
    assert body["sent"] is False
    assert body["wrote_live"] is False
    assert body["workroom_only"] is False
    assert body["cross_area"] is True
    unfinished_ids = {i["id"] for i in body["unfinished"]}
    assert family["id"] in unfinished_ids
    assert work["id"] in unfinished_ids
    assert personal["id"] not in unfinished_ids
    tomorrow_ids = {i["id"] for i in body["tomorrow_preview"]}
    assert personal["id"] in tomorrow_ids
    completed_ids = {i["id"] for i in body["completed"]}
    assert done["id"] in completed_ids
    assert "family" in body["areas"] and "workroom" in body["areas"]
    assert set(body["steps"]) == {"review", "move", "plan"}

    closed = client.post("/api/v1/organizer/review/shutdown/complete", json={
        "date": today,
        "notes": "Quiet close",
        "tomorrow_focus": "Walk the dogs early",
        "tomorrow_space_id": "family",
        "moves": [
            {"id": family["id"], "destination": "tomorrow"},
            {"id": work["id"], "destination": "keep"},
        ],
    })
    assert closed.status_code == 200, closed.text
    result = closed.json()
    assert result["sent"] is False
    assert result["wrote_live"] is False
    assert result["wrote_quotes"] is False
    moved = next(a for a in result["applied"] if a["id"] == family["id"])
    assert (moved["item"]["due_at"] or "")[:10] == (date.today() + timedelta(days=1)).isoformat()
    assert result["tomorrow_item"]["title"].startswith("Walk the dogs")
    assert result["tomorrow_item"]["space_id"] == "family"


def test_weekly_review_is_not_workroom_only(isolated_empire_db):
    today = date.today()
    slipped = client.post("/api/v1/organizer/items", json={
        "kind": "school", "title": "Recital permission", "space_id": "family",
        "due_at": (today - timedelta(days=3)).isoformat() + "T09:00:00",
    }).json()["item"]
    nextw = client.post("/api/v1/organizer/items", json={
        "kind": "admin", "title": "Empire license renew", "space_id": "empire",
        "due_at": (today + timedelta(days=4)).isoformat() + "T09:00:00",
    }).json()["item"]
    review = client.get("/api/v1/organizer/review/weekly")
    assert review.status_code == 200
    pack = review.json()
    assert pack["sent"] is False
    assert pack["workroom_only"] is False
    assert slipped["id"] in {i["id"] for i in pack["slipped"]}
    assert nextw["id"] in {i["id"] for i in pack["next_week"]}
    assert "family" in pack["by_space"]["slipped"]
    assert "empire" in pack["by_space"]["next_week"]


def test_shutdown_pure_moves_and_weekly_wins():
    today = "2026-10-12"
    items = [
        {"id": "a", "title": "Late bill", "due_at": "2026-10-01T09:00:00", "status": "open", "space_id": "personal"},
        {"id": "b", "title": "Sew", "due_at": "2026-10-12T10:00:00", "status": "open", "space_id": "workroom"},
        {"id": "c", "title": "Done walk", "due_at": "2026-10-12T08:00:00", "status": "done", "last_moved_at": "2026-10-12", "space_id": "family"},
        {"id": "d", "title": "Tomorrow call", "due_at": "2026-10-13T09:00:00", "status": "planned", "space_id": "empire"},
    ]
    pack = evening_shutdown(items, today=today)
    assert [i["id"] for i in pack["unfinished"]] == ["a", "b"]
    assert [i["id"] for i in pack["completed"]] == ["c"]
    assert pack["by_space"]["unfinished"]["personal"][0]["id"] == "a"
    moved = apply_shutdown_moves(items, [
        {"id": "a", "destination": "tomorrow"},
        {"id": "b", "destination": "drop"},
    ], today=today)
    by = {i["id"]: i for i in moved}
    assert by["a"]["due_at"].startswith("2026-10-13")
    assert by["b"]["status"] == "cancelled"
    week = weekly_review(items, today=today)
    assert week["wins"][0]["id"] == "c"
    assert week["workroom_only"] is False
