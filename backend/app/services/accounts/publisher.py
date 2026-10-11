"""Publish scheduled posts. Draft-only unless the account auto-publish toggle is on.

Facebook and Instagram go out through the Graph API. Other platforms are
left unsent with an honest error. A pause switch stops the whole tick.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Callable

from app.services.accounts.store import publish_paused
from app.services.accounts.vault import Vault, open_secret

GRAPH = "https://graph.facebook.com/v21.0"
MAX_ATTEMPTS = 3

Transport = Callable[..., dict]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat()


def create_post(
    conn: sqlite3.Connection,
    *,
    business_key: str,
    platform: str,
    content: str,
    scheduled_for: str | None = None,
    media_url: str | None = None,
    status: str = "draft",
) -> dict:
    post_id = uuid.uuid4().hex[:12]
    conn.execute(
        """
        INSERT INTO scheduled_posts (
            id, business_key, platform, content, media_url, scheduled_for,
            status, attempts, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (post_id, business_key, platform, content, media_url, scheduled_for, status, _iso(_now())),
    )
    conn.commit()
    return get_post(conn, post_id)


def get_post(conn: sqlite3.Connection, post_id: str) -> dict:
    row = conn.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,)).fetchone()
    return dict(row) if row else {}


def _due(conn: sqlite3.Connection, now: datetime) -> list[sqlite3.Row]:
    stamp = _iso(now)
    return conn.execute(
        """
        SELECT * FROM scheduled_posts
        WHERE status IN ('scheduled', 'retry')
          AND (scheduled_for IS NULL OR scheduled_for <= ?)
          AND attempts < ?
        ORDER BY scheduled_for
        """,
        (stamp, MAX_ATTEMPTS),
    ).fetchall()


def _account(conn: sqlite3.Connection, business_key: str, platform: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM online_accounts WHERE business_key = ? AND platform = ?",
        (business_key, platform),
    ).fetchone()


def _load_token(conn: sqlite3.Connection, vault: Vault, secret_id: str | None) -> dict | None:
    if not secret_id:
        return None
    raw = open_secret(conn, vault, secret_id)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"access_token": raw}
    if isinstance(payload, dict) and payload.get("access_token"):
        return payload
    return None


def publish_facebook(transport: Transport, page_id: str, token: str, message: str) -> dict:
    response = transport(
        "POST",
        f"{GRAPH}/{page_id}/feed",
        params={"message": message, "access_token": token},
    )
    if response.get("id"):
        return {"ok": True, "external_post_id": response["id"]}
    return {"ok": False, "error": response.get("error") or "Facebook publish failed"}


def publish_instagram(transport: Transport, ig_id: str, token: str, caption: str, media_url: str) -> dict:
    container = transport(
        "POST",
        f"{GRAPH}/{ig_id}/media",
        params={"image_url": media_url, "caption": caption, "access_token": token},
    )
    creation_id = container.get("id")
    if not creation_id:
        return {"ok": False, "error": container.get("error") or "Instagram container failed"}
    published = transport(
        "POST",
        f"{GRAPH}/{ig_id}/media_publish",
        params={"creation_id": creation_id, "access_token": token},
    )
    if published.get("id"):
        return {"ok": True, "external_post_id": published["id"]}
    return {"ok": False, "error": published.get("error") or "Instagram publish failed"}


def _finish(conn: sqlite3.Connection, post_id: str, *, status: str, attempts: int, error: str | None, external_id: str | None) -> None:
    conn.execute(
        """
        UPDATE scheduled_posts
        SET status = ?, attempts = ?, last_error = ?, external_post_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, attempts, error, external_id, _iso(_now()), post_id),
    )
    conn.commit()


def run_publish_tick(
    conn: sqlite3.Connection,
    vault: Vault | None,
    transport: Transport,
    now: datetime | None = None,
) -> dict:
    """Publish due posts. Held when auto-publish is off. Skipped entirely when paused."""
    moment = now or _now()
    if publish_paused(conn):
        return {"ran": False, "reason": "paused", "published": [], "held": [], "failed": []}
    published, held, failed = [], [], []
    for post in _due(conn, moment):
        account = _account(conn, post["business_key"], post["platform"])
        attempts = int(post["attempts"] or 0) + 1
        if account is None or not account["auto_publish"]:
            _finish(conn, post["id"], status="held", attempts=int(post["attempts"] or 0), error="auto-publish is off", external_id=None)
            held.append(post["id"])
            continue
        if post["platform"] not in {"facebook", "instagram"}:
            _finish(conn, post["id"], status="failed", attempts=attempts, error=f"{post['platform']} publisher is not connected", external_id=None)
            failed.append(post["id"])
            continue
        if vault is None or not account["vault_secret_id"]:
            _finish(conn, post["id"], status="failed", attempts=attempts, error="no credentials in the vault", external_id=None)
            failed.append(post["id"])
            continue
        token_payload = _load_token(conn, vault, account["vault_secret_id"])
        token = (token_payload or {}).get("access_token", "")
        page_id = account["external_account_id"] or (token_payload or {}).get("page_id") or (token_payload or {}).get("ig_id") or ""
        if not token or not page_id:
            _finish(conn, post["id"], status="failed", attempts=attempts, error="missing page id or access token", external_id=None)
            failed.append(post["id"])
            continue
        if post["platform"] == "facebook":
            result = publish_facebook(transport, page_id, token, post["content"])
        else:
            if not post["media_url"]:
                result = {"ok": False, "error": "Instagram requires media_url"}
            else:
                result = publish_instagram(transport, page_id, token, post["content"], post["media_url"])
        if result.get("ok"):
            _finish(conn, post["id"], status="published", attempts=attempts, error=None, external_id=result.get("external_post_id"))
            published.append(post["id"])
        elif attempts < MAX_ATTEMPTS:
            _finish(conn, post["id"], status="retry", attempts=attempts, error=result.get("error"), external_id=None)
            failed.append(post["id"])
        else:
            _finish(conn, post["id"], status="failed", attempts=attempts, error=result.get("error"), external_id=None)
            failed.append(post["id"])
    return {"ran": True, "reason": "ok", "published": published, "held": held, "failed": failed}
