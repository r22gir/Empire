"""Scheduled posts stay drafts until auto-publish is on, then retry failures."""
from __future__ import annotations

from datetime import datetime, timezone

from cryptography.fernet import Fernet

from app.services.accounts.publisher import create_post, get_post, run_publish_tick
from app.services.accounts.store import connect, set_auto_publish, set_publish_paused
from app.services.accounts.vault import Vault, put_secret


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_VAULT_KEY", Fernet.generate_key().decode())
    conn = connect()
    vault = Vault()
    put_secret(conn, vault, "oauth:workroom:facebook", '{"access_token":"page-token","page_id":"55"}')
    conn.execute(
        """
        UPDATE online_accounts
        SET vault_secret_id = ?, external_account_id = ?
        WHERE business_key = 'workroom' AND platform = 'facebook'
        """,
        ("oauth:workroom:facebook", "55"),
    )
    conn.commit()
    return conn, vault


def test_scheduled_post_is_held_until_auto_publish(monkeypatch, tmp_path):
    conn, vault = _setup(monkeypatch, tmp_path)
    create_post(
        conn,
        business_key="workroom",
        platform="facebook",
        content="Hello",
        scheduled_for="2020-01-01T00:00:00+00:00",
        status="scheduled",
    )
    calls = []

    def transport(method, url, **kwargs):
        calls.append(url)
        return {"id": "fb-1"}

    result = run_publish_tick(conn, vault, transport, now=datetime(2026, 10, 2, tzinfo=timezone.utc))
    assert result["published"] == []
    assert result["held"]
    assert calls == []
    assert get_post(conn, result["held"][0])["status"] == "held"
    assert get_post(conn, result["held"][0])["last_error"] == "auto-publish is off"
    conn.close()


def test_auto_publish_posts_then_pause_stops_the_tick(monkeypatch, tmp_path):
    conn, vault = _setup(monkeypatch, tmp_path)
    set_auto_publish(conn, "workroom", "facebook", True)
    post = create_post(
        conn,
        business_key="workroom",
        platform="facebook",
        content="Ship it",
        scheduled_for="2020-01-01T00:00:00+00:00",
        status="scheduled",
    )
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs.get("params", {}).get("message")))
        return {"id": "fb-9"}

    now = datetime(2026, 10, 2, tzinfo=timezone.utc)
    result = run_publish_tick(conn, vault, transport, now=now)
    assert result["published"] == [post["id"]]
    assert get_post(conn, post["id"])["status"] == "published"
    assert get_post(conn, post["id"])["external_post_id"] == "fb-9"
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/55/feed")

    second = create_post(
        conn,
        business_key="workroom",
        platform="facebook",
        content="Not yet",
        scheduled_for="2020-01-01T00:00:00+00:00",
        status="scheduled",
    )
    set_publish_paused(conn, True)
    paused = run_publish_tick(conn, vault, transport, now=now)
    assert paused["ran"] is False
    assert paused["reason"] == "paused"
    assert get_post(conn, second["id"])["status"] == "scheduled"
    conn.close()


def test_failures_retry_then_stop(monkeypatch, tmp_path):
    conn, vault = _setup(monkeypatch, tmp_path)
    set_auto_publish(conn, "workroom", "facebook", True)
    post = create_post(
        conn,
        business_key="workroom",
        platform="facebook",
        content="Retry me",
        scheduled_for="2020-01-01T00:00:00+00:00",
        status="scheduled",
    )

    def transport(method, url, **kwargs):
        return {"error": "graph down"}

    now = datetime(2026, 10, 2, tzinfo=timezone.utc)
    run_publish_tick(conn, vault, transport, now=now)
    assert get_post(conn, post["id"])["status"] == "retry"
    assert get_post(conn, post["id"])["attempts"] == 1
    run_publish_tick(conn, vault, transport, now=now)
    run_publish_tick(conn, vault, transport, now=now)
    final = get_post(conn, post["id"])
    assert final["status"] == "failed"
    assert final["attempts"] == 3
    conn.close()
