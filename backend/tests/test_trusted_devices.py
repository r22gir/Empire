"""Trusted-device + Studio sign-in tests.

Uses an isolated temp SQLite file. Never writes to backend/data/empire.db
or any other live database.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.utils.security import get_password_hash


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    from app.db import database
    from app.services import trusted_devices as devices

    db_path = tmp_path / "studio_auth_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(db_path))
    monkeypatch.setenv("FOUNDER_PIN", "2468")
    devices.reset_schema_cache()
    devices.ensure_schema()
    return db_path


def _seed_users():
    from app.db.database import get_db

    founder_hash = get_password_hash("founder-pass")
    viewer_hash = get_password_hash("viewer-pass")
    with get_db() as conn:
        conn.execute(
            """INSERT INTO access_users
               (id, name, role, email, password_hash, tier, is_active)
               VALUES (?, ?, 'founder', ?, ?, 'empire', 1)""",
            ("founder1", "Founder", "owner@empire.example", founder_hash),
        )
        conn.execute(
            """INSERT INTO access_users
               (id, name, role, email, password_hash, tier, is_active)
               VALUES (?, ?, 'viewer', ?, ?, 'lite', 1)""",
            ("viewer1", "Viewer", "viewer@example.com", viewer_hash),
        )


@pytest.fixture
def client(isolated_db):
    """Auth router only — no live DB and no full app side effects."""
    from fastapi import FastAPI
    from app.routers.auth import router

    _seed_users()
    app = FastAPI()
    app.include_router(router, prefix="/auth")
    app.include_router(router, prefix="/api/v1/auth")
    return TestClient(app)


def test_studio_login_pin_success(client):
    r = client.post("/api/v1/auth/studio-login", json={"pin": "2468"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["role"] == "founder"
    assert body["remember_offered"] is True
    assert client.cookies.get("empire_session")


def test_studio_login_bad_pin_rejected(client):
    r = client.post("/api/v1/auth/studio-login", json={"pin": "0000"})
    assert r.status_code == 401
    assert not client.cookies.get("empire_session")


def test_existing_founder_pin_still_required(client):
    r = client.post("/auth/founder-token", json={"pin": "wrong"})
    assert r.status_code == 401
    r = client.post("/auth/founder-token", json={"pin": "2468"})
    assert r.status_code == 200
    assert r.json()["user"]["id"] == "founder1"


def test_viewer_email_cannot_studio_login(client):
    r = client.post(
        "/api/v1/auth/studio-login",
        json={"email": "viewer@example.com", "password": "viewer-pass"},
    )
    assert r.status_code == 403


def test_saas_login_still_works_for_viewer(client):
    r = client.post(
        "/auth/login",
        json={"email": "viewer@example.com", "password": "viewer-pass"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_remember_device_requires_auth(client):
    r = client.post("/api/v1/auth/remember-device", json={})
    assert r.status_code == 401


def test_remember_stores_hash_not_raw_and_sets_httponly(client, isolated_db):
    from app.db.database import get_db
    from app.services.trusted_devices import hash_device_token

    client.post("/api/v1/auth/studio-login", json={"pin": "2468"})
    r = client.post(
        "/api/v1/auth/remember-device",
        json={"device_name": "iPhone Safari"},
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/605.1"},
    )
    assert r.status_code == 200, r.text
    raw = client.cookies.get("empire_device")
    assert raw
    assert len(raw) >= 32

    set_cookie = r.headers.get("set-cookie", "")
    assert "empire_device=" in set_cookie
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    with get_db() as conn:
        row = conn.execute("SELECT token_hash, device_name FROM trusted_devices").fetchone()
    assert row is not None
    assert row[0] != raw
    assert row[0] == hash_device_token(raw)
    assert raw.encode() not in isolated_db.read_bytes()
    assert row[1] == "iPhone Safari"


def test_device_cookie_skips_login_and_rolls(client):
    from app.db.database import get_db

    client.post("/api/v1/auth/studio-login", json={"pin": "2468"})
    client.post("/api/v1/auth/remember-device", json={"device_name": "Mac Chrome"})
    raw = client.cookies.get("empire_device")

    with get_db() as conn:
        before = conn.execute("SELECT expires_at FROM trusted_devices").fetchone()[0]

    client.cookies.clear()
    client.cookies.set("empire_device", raw)
    r = client.get("/api/v1/auth/session")
    assert r.status_code == 200, r.text
    assert r.json()["authenticated"] is True
    assert r.json()["via"] == "device"
    assert r.json()["user"]["role"] == "founder"
    assert client.cookies.get("empire_session")

    with get_db() as conn:
        after = conn.execute("SELECT expires_at, last_used_at FROM trusted_devices").fetchone()
    assert after[0] >= before
    assert after[1]


def test_revoke_invalidates_immediately(client):
    client.post("/api/v1/auth/studio-login", json={"pin": "2468"})
    remember = client.post("/api/v1/auth/remember-device", json={"device_name": "Pixel"})
    device_id = remember.json()["device"]["id"]
    raw = client.cookies.get("empire_device")

    listed = client.get("/api/v1/auth/devices")
    assert listed.status_code == 200
    assert len(listed.json()["devices"]) == 1
    assert listed.json()["devices"][0]["current"] is True

    revoked = client.delete(f"/api/v1/auth/devices/{device_id}")
    assert revoked.status_code == 200

    client.cookies.clear()
    client.cookies.set("empire_device", raw)
    r = client.get("/api/v1/auth/session")
    assert r.status_code == 401


def test_revoke_all_invalidates_every_device(client):
    client.post("/api/v1/auth/studio-login", json={"pin": "2468"})
    client.post("/api/v1/auth/remember-device", json={"device_name": "One"})
    first = client.cookies.get("empire_device")

    from app.services import trusted_devices as devices
    from app.db.database import get_db

    devices.register_device(
        "founder1",
        devices.new_device_token(),
        device_name="Two",
        user_agent="Firefox",
        ip="1.1.1.1",
        location="Washington, US",
    )
    with get_db() as conn:
        live = conn.execute(
            "SELECT COUNT(*) FROM trusted_devices WHERE revoked_at IS NULL"
        ).fetchone()[0]
    assert live == 2

    r = client.post("/api/v1/auth/devices/revoke-all")
    assert r.status_code == 200
    assert r.json()["revoked"] == 2

    client.cookies.clear()
    client.cookies.set("empire_device", first)
    assert client.get("/api/v1/auth/session").status_code == 401


def test_location_and_browser_captured(client):
    client.post("/api/v1/auth/studio-login", json={"pin": "2468"})
    client.post(
        "/api/v1/auth/remember-device",
        json={},
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0",
            "CF-IPCity": "Miami",
            "CF-IPCountry": "US",
            "CF-Connecting-IP": "203.0.113.9",
        },
    )
    items = client.get("/api/v1/auth/devices").json()["devices"]
    assert items[0]["device_name"] == "Chrome on Mac"
    assert items[0]["location"] == "Miami, US"


def test_expired_device_is_rejected(client):
    from app.db.database import get_db
    from app.services.trusted_devices import hash_device_token, new_device_token

    client.post("/api/v1/auth/studio-login", json={"pin": "2468"})
    raw = new_device_token()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0).isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO trusted_devices
               (id, user_id, token_hash, device_name, created_at, expires_at, last_used_at)
               VALUES ('expired1', 'founder1', ?, 'Old', ?, ?, ?)""",
            (hash_device_token(raw), past, past, past),
        )
    client.cookies.clear()
    client.cookies.set("empire_device", raw)
    assert client.get("/api/v1/auth/session").status_code == 401


def test_hash_is_deterministic_and_secret_bound():
    from app.services.trusted_devices import hash_device_token

    a = hash_device_token("abc")
    b = hash_device_token("abc")
    c = hash_device_token("xyz")
    assert a == b
    assert a != c
    assert len(a) == 64
