"""Creating several tasks in the same second must return each new id."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app


def test_create_several_tasks_returns_distinct_real_ids(isolated_empire_db):
    assert os.environ.get("EMPIRE_TASK_DB") == isolated_empire_db
    client = TestClient(app)
    ids = []
    for i in range(5):
        res = client.post(
            "/api/v1/tasks/",
            json={
                "title": f"Same-second task {i}",
                "desk": "code",
                "created_by": "test",
            },
        )
        assert res.status_code == 200, res.text
        task = res.json()["task"]
        assert task["id"], task
        assert task["title"] == f"Same-second task {i}"
        ids.append(task["id"])
    assert len(ids) == 5
    assert len(set(ids)) == 5
