"""Accumulate voice notes into one draft until the speaker says done."""
from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def _store_path() -> Path:
    override = os.getenv("VOICE_DOC_SESSIONS_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "data" / "voice_document_sessions.json"


_lock = threading.Lock()


@dataclass
class VoiceSession:
    id: str
    key: str
    edition_id: str
    transcripts: list[str] = field(default_factory=list)
    status: str = "accumulating"  # accumulating | finalized
    quote_id: str = ""
    overrides: dict = field(default_factory=dict)
    sent: bool = False
    send_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "edition_id": self.edition_id,
            "transcripts": list(self.transcripts),
            "status": self.status,
            "quote_id": self.quote_id,
            "overrides": dict(self.overrides),
            "sent": self.sent,
            "send_requested": self.send_requested,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceSession":
        return cls(
            id=data["id"],
            key=data.get("key") or data["id"],
            edition_id=data.get("edition_id") or "workroom",
            transcripts=list(data.get("transcripts") or []),
            status=data.get("status") or "accumulating",
            quote_id=data.get("quote_id") or "",
            overrides=dict(data.get("overrides") or {}),
            sent=bool(data.get("sent")),
            send_requested=bool(data.get("send_requested")),
        )


def _load() -> dict:
    path = _store_path()
    if not path.is_file():
        return {"sessions": []}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"sessions": []}


def _save(payload: dict) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def get_session(session_id: str) -> Optional[VoiceSession]:
    with _lock:
        for row in _load().get("sessions") or []:
            if row.get("id") == session_id:
                return VoiceSession.from_dict(row)
    return None


def active_session(key: str) -> Optional[VoiceSession]:
    with _lock:
        rows = [r for r in (_load().get("sessions") or []) if r.get("key") == key]
    for row in reversed(rows):
        if row.get("status") == "accumulating":
            return VoiceSession.from_dict(row)
    return None


def save_session(session: VoiceSession) -> VoiceSession:
    with _lock:
        payload = _load()
        rows = list(payload.get("sessions") or [])
        replaced = False
        for idx, row in enumerate(rows):
            if row.get("id") == session.id:
                rows[idx] = session.to_dict()
                replaced = True
                break
        if not replaced:
            rows.append(session.to_dict())
        payload["sessions"] = rows
        _save(payload)
    return session


def open_session(*, key: str, edition_id: str) -> VoiceSession:
    existing = active_session(key)
    if existing:
        return existing
    session = VoiceSession(
        id=uuid.uuid4().hex[:12],
        key=key,
        edition_id=edition_id,
    )
    return save_session(session)
