"""Home center lists: per-user storage, field cleaning. Runs on its own temp DB."""
from __future__ import annotations

import asyncio
import sqlite3

import pytest


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "home_center.db"
    sqlite3.connect(path).close()
    from app.db import database
    monkeypatch.setattr(database, "DB_PATH", str(path))
    assert database.DB_PATH == str(path)
    return path


def test_clean_items_drops_unknown_fields_and_clamps():
    from app.routers.home_center import clean_items
    items = clean_items([
        {"name": "  AI & Tech ", "icon": "cpu", "secret": "x", "progress": 140},
        {"name": ""},
        "nope",
        {"name": "Read 12 books", "done": 8, "total": 12, "progress": "abc"},
    ])
    assert [i["name"] for i in items] == ["AI & Tech", "Read 12 books"]
    assert "secret" not in items[0] and items[0]["progress"] == 100.0 and items[0]["id"] == "ai-tech"
    assert items[1]["done"] == 8 and items[1]["total"] == 12 and "progress" not in items[1]


def test_get_is_read_only(tmp_db):
    """Opening the home must not write: GET on a fresh DB returns empty lists and creates nothing."""
    from app.routers.home_center import get_state
    state = asyncio.run(get_state(user="owner"))
    assert state["interests"] == [] and state["projects"] == []
    tables = {r[0] for r in sqlite3.connect(tmp_db).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "home_center_state" not in tables


def test_state_round_trip_is_per_user(tmp_db):
    from app.routers.home_center import ItemsBody, get_state, put_state
    empty = asyncio.run(get_state(user="owner"))
    assert empty["interests"] == [] and empty["goals"] == []
    asyncio.run(put_state("interests", ItemsBody(items=[{"name": "Markets", "icon": "trend"}]), user="owner"))
    asyncio.run(put_state("goals", ItemsBody(items=[{"name": "Ship v3", "progress": 40}]), user="juan"))
    owner = asyncio.run(get_state(user="owner"))
    juan = asyncio.run(get_state(user="juan"))
    assert [i["name"] for i in owner["interests"]] == ["Markets"] and owner["goals"] == []
    assert juan["interests"] == [] and juan["goals"][0]["progress"] == 40.0


def test_bad_kind_and_user_are_refused(tmp_db):
    from fastapi import HTTPException
    from app.routers.home_center import ItemsBody, get_state, put_state
    with pytest.raises(HTTPException):
        asyncio.run(put_state("secrets", ItemsBody(items=[]), user="owner"))
    with pytest.raises(HTTPException):
        asyncio.run(get_state(user="../etc"))
