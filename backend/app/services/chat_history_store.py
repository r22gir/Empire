"""Per-user chat history files.

One JSON record per conversation, named with the full chat id (never the
first 8 characters). Family editions isolate files by the logged-in
allowlisted email. Workroom keeps the founder bucket.

Timestamps are America/New_York with an explicit offset.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

CHAT_TZ_NAME = "America/New_York"
CHAT_TZ = ZoneInfo(CHAT_TZ_NAME)
WORKROOM_USER = "founder"
# Founder/Workroom checkout path. Tests may pass a replacement via
# chats_dir(workroom_dir=...). Family editions never mkdir or read it.
CHATS_DIR = Path(__file__).resolve().parents[2] / "data" / "chats"

_UNSAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


class ChatHistoryOwnerError(Exception):
    """Family edition request has no allowlisted session email."""


class ChatHistoryIdError(ValueError):
    """Chat id is empty or not a safe filename."""


class LegacyChatReadOnlyError(Exception):
    """A pre-isolation founder chat cannot be mutated until migration --apply."""


def now_iso() -> str:
    """Wall-clock time in America/New_York, including the zone offset."""
    return datetime.now(CHAT_TZ).isoformat()


def chats_dir(workroom_dir: Optional[Path] = None) -> Path:
    try:
        from app.edition import is_family_edition, require_data_root

        if is_family_edition():
            path = require_data_root() / "chats"
            path.mkdir(parents=True, exist_ok=True)
            return path
    except Exception:
        pass
    path = Path(workroom_dir or CHATS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_key_from_email(email: str) -> str:
    raw = (email or "").strip().lower()
    raw = raw.replace("@", "_at_")
    cleaned = _UNSAFE_ID.sub("_", raw).strip("._-")
    return cleaned or "unknown"


def primary_legacy_email(edition: Optional[str] = None) -> str:
    """Allowlisted user who should still see pre-isolation ``founder/`` chats.

    Max-e (amp) has one family user — Juan — identified by
    ``AMP_OWNER_EMAIL`` unless an edition override is set:

    * ``FAMILY_LEGACY_CHAT_EMAIL`` (any family edition)
    * ``AMP_LEGACY_CHAT_EMAIL`` (Max-e)
    * ``MAXINE_LEGACY_CHAT_EMAIL`` (Maxine)
    """
    try:
        from app.edition import edition_name

        name = (edition or edition_name()).strip().lower()
    except Exception:
        name = (edition or "").strip().lower()
    override = (os.getenv("FAMILY_LEGACY_CHAT_EMAIL") or "").strip()
    if not override and name == "amp":
        override = (os.getenv("AMP_LEGACY_CHAT_EMAIL") or "").strip()
    if not override and name == "maxine":
        override = (os.getenv("MAXINE_LEGACY_CHAT_EMAIL") or "").strip()
    if override:
        return override.lower()
    return (
        (os.getenv("AMP_OWNER_EMAIL") or "").strip()
        or (os.getenv("FOUNDER_EMAIL") or "").strip()
    ).lower()


def primary_legacy_owner_key(edition: Optional[str] = None) -> str:
    email = primary_legacy_email(edition)
    return user_key_from_email(email) if email else ""


def is_primary_legacy_viewer(owner_key: str, edition: Optional[str] = None) -> bool:
    primary = primary_legacy_owner_key(edition)
    return bool(primary) and owner_key == primary


def owner_key_for_request(request: Any = None, claimed_user_id: Optional[str] = None) -> str:
    """Resolve the on-disk user folder.

    Family editions ignore client-supplied user_id and use the session
    email set by the edition gate. Workroom keeps ``founder`` unless a
    claimed id is passed (legacy query param).
    """
    try:
        from app.edition import is_family_edition
        family = is_family_edition()
    except Exception:
        family = False

    if family:
        email = getattr(getattr(request, "state", None), "amp_email", None)
        if not email:
            raise ChatHistoryOwnerError("missing family session")
        return user_key_from_email(str(email))
    claimed = (claimed_user_id or "").strip()
    return claimed or WORKROOM_USER


def safe_chat_id(chat_id: Optional[str], *, generate: bool = False) -> str:
    raw = (chat_id or "").strip()
    if not raw:
        if generate:
            return str(uuid.uuid4())
        raise ChatHistoryIdError("empty chat id")
    if raw in {".", ".."} or "/" in raw or "\\" in raw:
        raise ChatHistoryIdError("unsafe chat id")
    if len(raw) < 8:
        raise ChatHistoryIdError("chat id too short")
    return raw


def user_dir(owner_key: str, *, workroom_dir: Optional[Path] = None) -> Path:
    key = user_key_from_email(owner_key) if "@" in owner_key else _UNSAFE_ID.sub("_", owner_key).strip("._-")
    if not key:
        key = WORKROOM_USER
    path = chats_dir(workroom_dir=workroom_dir) / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def chat_path(owner_key: str, chat_id: str, *, workroom_dir: Optional[Path] = None) -> Path:
    return user_dir(owner_key, workroom_dir=workroom_dir) / f"{safe_chat_id(chat_id)}.json"


def founder_chats_dir(workroom_dir: Optional[Path] = None) -> Path:
    """Legacy pre-isolation bucket. Does not create the folder."""
    return chats_dir(workroom_dir=workroom_dir) / WORKROOM_USER


def _chat_summary(data: dict, *, legacy: bool = False) -> dict:
    item = {
        "id": data["id"],
        "title": data.get("title", "Untitled"),
        "updated_at": data.get("updated_at", ""),
        "created_at": data.get("created_at", ""),
        "timezone": data.get("timezone") or CHAT_TZ_NAME,
        "message_count": len(data.get("messages") or []),
        "preview": data.get("preview") or preview_from(data.get("messages") or []),
        "pinned": data.get("pinned", False),
    }
    if legacy:
        item["legacy"] = True
        item["read_only"] = True
    return item


def _iter_folder_chats(folder: Path):
    if not folder.exists():
        return
    for f in folder.glob("*.json"):
        data = _read_json(f)
        if data.get("id"):
            yield f, data


def _dumps(data: dict) -> str:
    return json.dumps(data, indent=2, default=str, ensure_ascii=False) + "\n"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def preview_from(messages: list, max_len: int = 120) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")
            if isinstance(text, str) and text.strip():
                return text.strip()[:max_len]
    return ""


def title_from(messages: list) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")
            if isinstance(text, str) and text.strip():
                first_line = text.strip().split("\n")[0]
                if len(first_line) > 60:
                    return first_line[:57] + "..."
                return first_line
    return f"Chat {datetime.now(CHAT_TZ).strftime('%m/%d %H:%M')}"


def persist_exchange(
    *,
    chat_id: str,
    user_message: str,
    assistant_message: str,
    model: Optional[str] = None,
    request: Any = None,
    claimed_user_id: Optional[str] = None,
    workroom_dir: Optional[Path] = None,
) -> dict:
    """Upsert one full-id record for a user/assistant turn.

    Same file the frontend PUT uses. Never writes ``<8-char-id>.json``.
    """
    owner = owner_key_for_request(request, claimed_user_id)
    cid = safe_chat_id(chat_id)
    path = chat_path(owner, cid, workroom_dir=workroom_dir)
    existing = _read_json(path) if path.exists() else {}
    messages = list(existing.get("messages") or [])
    already = (
        messages
        and messages[-1].get("role") == "user"
        and messages[-1].get("content") == user_message
    )
    stamp = now_iso()
    try:
        from app.services.max.thinking import strip_thinking
        assistant_message = strip_thinking(assistant_message)
    except Exception:
        pass
    new_msgs = [
        {"role": "user", "content": user_message, "timestamp": stamp},
        {"role": "assistant", "content": assistant_message, "timestamp": stamp, "model": model},
    ]
    all_msgs = messages if already else (messages + new_msgs)
    data = {
        "id": cid,
        "owner": owner,
        "title": existing.get("title") or title_from(new_msgs),
        "created_at": existing.get("created_at") or stamp,
        "updated_at": stamp,
        "timezone": CHAT_TZ_NAME,
        "pinned": existing.get("pinned", False),
        "preview": (user_message[:120]).strip(),
        "messages": all_msgs,
    }
    path.write_text(_dumps(data), encoding="utf-8")
    return data


def upsert_chat(
    *,
    chat_id: Optional[str],
    messages: list,
    title: Optional[str] = None,
    request: Any = None,
    claimed_user_id: Optional[str] = None,
    workroom_dir: Optional[Path] = None,
    generate_id: bool = False,
) -> tuple[dict, str]:
    owner = owner_key_for_request(request, claimed_user_id)
    cid = safe_chat_id(chat_id, generate=generate_id)
    path = chat_path(owner, cid, workroom_dir=workroom_dir)
    existing = _read_json(path) if path.exists() else {}
    stamp = now_iso()
    status = "updated" if existing else "created"
    data = {
        "id": cid,
        "owner": owner,
        "title": title or existing.get("title") or title_from(messages),
        "created_at": existing.get("created_at") or stamp,
        "updated_at": stamp,
        "timezone": CHAT_TZ_NAME,
        "pinned": existing.get("pinned", False),
        "preview": preview_from(messages),
        "messages": messages,
    }
    path.write_text(_dumps(data), encoding="utf-8")
    return data, status


def list_chats_for_owner(
    *,
    request: Any = None,
    claimed_user_id: Optional[str] = None,
    workroom_dir: Optional[Path] = None,
) -> list[dict]:
    owner = owner_key_for_request(request, claimed_user_id)
    folder = user_dir(owner, workroom_dir=workroom_dir)
    chats: list[dict] = []
    seen: set[str] = set()
    for _path, data in _iter_folder_chats(folder):
        chats.append(_chat_summary(data))
        seen.add(str(data["id"]))
    # Until migrate_founder_chats.py --apply, the edition primary user
    # (Juan on Max-e) still sees the old founder/ files, read-only.
    if is_primary_legacy_viewer(owner):
        for _path, data in _iter_folder_chats(founder_chats_dir(workroom_dir)):
            cid = str(data["id"])
            if cid in seen:
                continue
            chats.append(_chat_summary(data, legacy=True))
            seen.add(cid)
    chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    chats.sort(key=lambda x: x.get("pinned", False), reverse=True)
    return chats


def load_chat_for_owner(
    chat_id: str,
    *,
    request: Any = None,
    claimed_user_id: Optional[str] = None,
    workroom_dir: Optional[Path] = None,
) -> Optional[dict]:
    owner = owner_key_for_request(request, claimed_user_id)
    path = chat_path(owner, chat_id, workroom_dir=workroom_dir)
    if path.exists():
        data = _read_json(path)
        return data or None
    if is_primary_legacy_viewer(owner):
        try:
            legacy_path = founder_chats_dir(workroom_dir) / f"{safe_chat_id(chat_id)}.json"
        except ChatHistoryIdError:
            return None
        if legacy_path.exists():
            data = _read_json(legacy_path)
            if data:
                data = dict(data)
                data["legacy"] = True
                data["read_only"] = True
                return data
    return None


def update_meta(
    chat_id: str,
    *,
    title: Optional[str] = None,
    pinned: Optional[bool] = None,
    request: Any = None,
    claimed_user_id: Optional[str] = None,
    workroom_dir: Optional[Path] = None,
) -> Optional[dict]:
    owner = owner_key_for_request(request, claimed_user_id)
    path = chat_path(owner, chat_id, workroom_dir=workroom_dir)
    if not path.exists():
        if is_primary_legacy_viewer(owner):
            legacy_path = founder_chats_dir(workroom_dir) / f"{safe_chat_id(chat_id)}.json"
            if legacy_path.exists():
                raise LegacyChatReadOnlyError(chat_id)
        return None
    existing = _read_json(path)
    if not existing:
        return None
    if title is not None:
        existing["title"] = title
    if pinned is not None:
        existing["pinned"] = pinned
    existing["updated_at"] = now_iso()
    existing["timezone"] = CHAT_TZ_NAME
    path.write_text(_dumps(existing), encoding="utf-8")
    return existing


def iter_searchable_chats(
    *,
    request: Any = None,
    claimed_user_id: Optional[str] = None,
    workroom_dir: Optional[Path] = None,
):
    """Yield (data, legacy) pairs the current user is allowed to search."""
    owner = owner_key_for_request(request, claimed_user_id)
    seen: set[str] = set()
    for _path, data in _iter_folder_chats(user_dir(owner, workroom_dir=workroom_dir)):
        seen.add(str(data["id"]))
        yield data, False
    if is_primary_legacy_viewer(owner):
        for _path, data in _iter_folder_chats(founder_chats_dir(workroom_dir)):
            cid = str(data["id"])
            if cid in seen:
                continue
            seen.add(cid)
            yield data, True


def plan_founder_migration(
    root: Path,
    target_email: Optional[str] = None,
    edition: Optional[str] = None,
) -> dict:
    """Describe founder/ → allowlisted-user copies. Never writes."""
    email = (target_email or primary_legacy_email(edition) or "").strip().lower()
    dest_key = user_key_from_email(email) if email else ""
    founder = Path(root) / WORKROOM_USER
    dest = Path(root) / dest_key if dest_key else None
    items = []
    for path, data in _iter_folder_chats(founder):
        cid = str(data.get("id") or path.stem)
        dest_path = dest / f"{path.name}" if dest else None
        exists = bool(dest_path and dest_path.exists())
        items.append(
            {
                "id": cid,
                "source": str(path),
                "dest": str(dest_path) if dest_path else None,
                "title": data.get("title") or title_from(data.get("messages") or []),
                "already_copied": exists,
                "would_copy": bool(dest_key) and not exists,
            }
        )
    return {
        "dry_run": True,
        "applied": False,
        "edition": edition,
        "target_email": email or None,
        "target_owner": dest_key or None,
        "source_dir": str(founder),
        "dest_dir": str(dest) if dest else None,
        "count": len(items),
        "would_copy": sum(1 for item in items if item["would_copy"]),
        "items": items,
        "note": "Dry-run. Pass --apply to copy into the allowlisted user folder. founder/ files are not deleted.",
    }


def apply_founder_migration(
    root: Path,
    target_email: Optional[str] = None,
    edition: Optional[str] = None,
) -> dict:
    """Copy founder chats into the configured user folder. Leaves founder/ in place."""
    plan = plan_founder_migration(root, target_email=target_email, edition=edition)
    email = plan["target_email"]
    dest_key = plan["target_owner"]
    if not email or not dest_key:
        raise ChatHistoryOwnerError("no primary allowlisted email configured")
    dest = Path(root) / dest_key
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    skipped = []
    for item in plan["items"]:
        source = Path(item["source"])
        dest_path = Path(item["dest"])
        if dest_path.exists():
            item["copied"] = False
            item["skipped"] = True
            skipped.append(item)
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest_path)
        data = _read_json(dest_path)
        data["id"] = data.get("id") or source.stem
        data["owner"] = dest_key
        data["timezone"] = data.get("timezone") or CHAT_TZ_NAME
        dest_path.write_text(_dumps(data), encoding="utf-8")
        item["copied"] = True
        item["skipped"] = False
        copied.append(item)
    plan["dry_run"] = False
    plan["applied"] = True
    plan["copied"] = len(copied)
    plan["skipped"] = len(skipped)
    plan["note"] = "Copied into the allowlisted user folder. founder/ files were left in place."
    return plan


def find_short_id_duplicates(root: Path) -> list[dict]:
    """Dry-run report: 8-char files that sit beside a longer full-id copy.

    Never deletes. Used by the cleanup script and tests.
    """
    report = []
    if not root.exists():
        return report
    for user_folder in sorted(p for p in root.iterdir() if p.is_dir()):
        files = {p.stem: p for p in user_folder.glob("*.json")}
        shorts = [stem for stem in files if len(stem) == 8]
        longs = [stem for stem in files if len(stem) > 8]
        for short in shorts:
            matches = [long for long in longs if long.startswith(short)]
            report.append(
                {
                    "user": user_folder.name,
                    "short_id": short,
                    "short_path": str(files[short]),
                    "full_ids": matches,
                    "would_delete": False,
                    "note": (
                        "short-id duplicate of full record"
                        if matches
                        else "orphan short-id file; not deleted"
                    ),
                }
            )
    return report
