"""Per-edition WhatsApp chat log, media, labels, and jobs root.

Family editions (Max-e / Maxine) stay under EMPIRE_DATA_DIR. They never
read repo client_aliases.json or business.json. Draft-only: this module
does not send to clients.

Ported from PR #91/#94 path layout + the founder-only alias gate in
9c34d3eb. The Workroom channel engine is not imported.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from app.edition import (
    EditionPathError,
    assert_under_root,
    is_family_edition,
    is_founder_edition,
    require_data_root,
)


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def whatsapp_data_dir() -> Path:
    """Edition-scoped WhatsApp directory. Family fails closed without a data root."""
    if is_family_edition():
        root = require_data_root()
    else:
        from app.services.data_paths import data_root

        root = data_root()
    base = root / "whatsapp"
    base.mkdir(parents=True, exist_ok=True)
    return base


def media_dir() -> Path:
    path = whatsapp_data_dir() / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def inbox_dir() -> Path:
    path = whatsapp_data_dir() / "inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def labels_path() -> Path:
    env = (os.getenv("WHATSAPP_LABELS") or "").strip()
    if env:
        return Path(os.path.expanduser(env))
    return whatsapp_data_dir() / "labels.json"


def chat_log_path() -> Path:
    return whatsapp_data_dir() / "whatsapp_chat_log.db"


def jobs_root(override: Path | str | None = None) -> Path:
    """Edition-scoped jobs directory. Never defaults to a shared ~/jobs tree."""
    if override:
        path = Path(override)
    else:
        env = (os.getenv("WHATSAPP_JOBS_ROOT") or "").strip()
        path = Path(env) if env else (
            require_data_root() if is_family_edition() else _data_root()
        ) / "jobs"
    path = Path(path)
    if is_family_edition():
        assert_under_root(path if path.is_absolute() else require_data_root() / path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _data_root() -> Path:
    from app.services.data_paths import data_root

    return data_root()


def edition_aliases_path() -> Path:
    if is_family_edition():
        return require_data_root() / "client_aliases.json"
    return _data_root() / "client_aliases.json"


def repo_aliases_path() -> Path:
    env = (os.getenv("MAX_CLIENT_ALIASES_REPO_PATH") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "config" / "client_aliases.json"


def _read_alias_dict(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.is_file():
        return {}, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}, True
    return (data if isinstance(data, dict) else {}), False


def _merge_alias_dicts(repo: dict[str, Any], edition: dict[str, Any]) -> dict[str, Any]:
    clients: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in (repo.get("clients") or [], edition.get("clients") or []):
        if not isinstance(source, list):
            continue
        for row in source:
            if not isinstance(row, dict):
                continue
            slug = str(row.get("slug") or "").strip().lower()
            if not slug or slug in seen:
                continue
            seen.add(slug)
            clients.append(row)
    out = dict(repo)
    out.update(edition)
    out["clients"] = clients
    return out


def load_client_aliases() -> dict[str, Any]:
    """Load this edition's aliases. Founder also merges the repo file.

    Family editions read only $EMPIRE_DATA_DIR/client_aliases.json so
    Rafael's names and addresses never leak (9c34d3eb).
    """
    edition, edition_corrupt = _read_alias_dict(edition_aliases_path())
    if edition_corrupt:
        return {}
    repo: dict[str, Any] = {}
    if is_founder_edition():
        repo, repo_corrupt = _read_alias_dict(repo_aliases_path())
        if repo_corrupt:
            repo = {}
    if not repo and not edition:
        return {}
    return _merge_alias_dicts(repo, edition)


def load_labels() -> list[dict[str, str]]:
    """Edition labels.json or WHATSAPP_LABELS. Never repo business.json."""
    path = labels_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    rows = data.get("phones") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        phone = _digits(str(row.get("phone") or ""))
        if phone:
            out.append({"name": str(row.get("name") or ""), "phone": phone})
    return out


def _connect() -> sqlite3.Connection:
    path = chat_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            kind TEXT NOT NULL,
            body TEXT,
            media_path TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wa_messages ON messages (wa_id, created_at)"
    )
    return conn


def record_message(
    wa_id: str,
    *,
    direction: str,
    kind: str,
    body: str = "",
    media_path: str = "",
    created_at: int | None = None,
) -> int:
    number = _digits(wa_id)
    if not number:
        return 0
    ts = int(created_at or time.time())
    stored_media = ""
    if media_path:
        try:
            resolved = Path(media_path).resolve()
            allowed = [media_dir().resolve(), inbox_dir().resolve(), jobs_root().resolve()]
            if any(resolved == root or root in resolved.parents for root in allowed):
                stored_media = str(resolved)
        except (OSError, EditionPathError):
            stored_media = ""
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO messages (wa_id, direction, kind, body, media_path, created_at) VALUES (?,?,?,?,?,?)",
            (number, direction, kind, body or "", stored_media, ts),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def list_conversations(limit: int = 50) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT wa_id,
                   MAX(created_at) AS last_at,
                   COUNT(*) AS n,
                   MAX(id) AS last_id
            FROM messages
            GROUP BY wa_id
            ORDER BY last_at DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 200)),),
        ).fetchall()
        labels = {row["phone"]: row.get("name") or "" for row in load_labels()}
        out = []
        for row in rows:
            last = conn.execute(
                "SELECT body, kind, direction FROM messages WHERE id = ?",
                (row["last_id"],),
            ).fetchone()
            out.append({
                "wa_id": row["wa_id"],
                "label": labels.get(row["wa_id"]) or "",
                "last4": row["wa_id"][-4:] if len(row["wa_id"]) >= 4 else row["wa_id"],
                "count": row["n"],
                "last_at": row["last_at"],
                "last_kind": (last["kind"] if last else ""),
                "last_direction": (last["direction"] if last else ""),
                "preview": ((last["body"] if last else "") or "")[:160],
            })
        return out
    finally:
        conn.close()


def list_messages(wa_id: str, *, limit: int = 100, before: int | None = None) -> list[dict[str, Any]]:
    number = _digits(wa_id)
    conn = _connect()
    try:
        if before:
            rows = conn.execute(
                """
                SELECT id, wa_id, direction, kind, body, media_path, created_at
                FROM messages WHERE wa_id = ? AND id < ?
                ORDER BY id DESC LIMIT ?
                """,
                (number, int(before), max(1, min(int(limit), 200))),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, wa_id, direction, kind, body, media_path, created_at
                FROM messages WHERE wa_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (number, max(1, min(int(limit), 200))),
            ).fetchall()
        items = [dict(row) for row in rows]
        items.reverse()
        return items
    finally:
        conn.close()


def search_messages(query: str, *, limit: int = 50) -> list[dict[str, Any]]:
    needle = (query or "").strip()
    if not needle:
        return []
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, wa_id, direction, kind, body, media_path, created_at
            FROM messages
            WHERE body LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (f"%{needle}%", max(1, min(int(limit), 100))),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def save_media(content: bytes, filename: str) -> Path:
    dest = media_dir() / Path(filename or "media.bin").name
    if dest.exists():
        dest = media_dir() / f"{int(time.time())}-{dest.name}"
    dest.write_bytes(content or b"")
    return dest
