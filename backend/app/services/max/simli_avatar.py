"""Simli face renderer. Self-contained; feature/amp-edition copies this module as-is.

The API key stays on the server. The browser receives a short-lived session
token only. Each edition has a non-secret default face id. SIMLI_FACE_ID
(and the per-edition SIMLI_FACE_ID_* names) override that default. When
SIMLI_API_KEY is unset, status says so and the UI keeps TalkingHead.

Public API (keep identical across editions):
    simli_status, create_session, record_usage, usage_card,
    normalize_edition, face_env_name, edition_avatar
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("max.simli")

ENV_API_KEY = "SIMLI_API_KEY"
TOKEN_URL = "https://api.simli.ai/compose/token"
ICE_URL = "https://api.simli.ai/compose/ice"
WEBRTC_URL = "wss://api.simli.ai/compose/webrtc/p2p"

# Hard caps so a forgotten tab cannot run the meter.
MAX_SESSION_LENGTH_SECONDS = 600
MAX_IDLE_SECONDS = 60
AUDIO_FORMAT = "pcm16"
SAMPLE_RATE = 16000

EDITIONS = ("workroom", "max_e", "maxine")

# Non-secret face ids. Env overrides the edition it names; these are the fallback.
DEFAULT_FACE_IDS = {
    "workroom": "7e74d6e7-d559-4394-bd56-4923a3ab75ad",
    "max_e": "dd10cb5a-d31d-4f12-b69f-6db3383c006e",
    "maxine": "cace3ef7-a4c4-425d-a8cf-a5358eb0c427",
}

# GLB files are added later. Until a file exists, TalkingHead uses the
# brunette sample shipped at /max-avatar.glb with body M.
EDITION_GLB = {
    "workroom": {"glb": "/avatars/workroom.glb", "body": "M"},
    "max_e": {"glb": "/avatars/max-e.glb", "body": "M"},
    "maxine": {"glb": "/avatars/maxine.glb", "body": "F"},
}

PLACEHOLDER = {
    "file": "/max-avatar.glb",
    "model": "brunette",
    "body": "M",
    "license": "CC BY-NC 4.0",
    "commercial_use": False,
    "note": (
        "Placeholder. This is TalkingHead's female brunette sample "
        "(CC BY-NC 4.0, non-commercial), loaded with body M. "
        "Edition GLB files are not installed yet."
    ),
}

_DEFAULT_STUN = [{"urls": "stun:stun.l.google.com:19302"}]


def _usage_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "simli_usage.json"


def _public_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "empire-command-center" / "public"


def normalize_edition(edition: str | None) -> str:
    key = (edition or "workroom").strip().lower().replace("-", "_")
    if key in {"maxe", "max_e", "amp"}:
        return "max_e"
    if key in EDITIONS:
        return key
    return "workroom"


def face_env_name(edition: str | None) -> str:
    _face, name = _face_id(edition)
    return name


def _face_id(edition: str | None) -> tuple[str, str]:
    """Return (face id, source). Source is the env name, or "default"."""
    key = normalize_edition(edition)
    names = ("SIMLI_FACE_ID_WORKROOM", "SIMLI_FACE_ID") if key == "workroom" else (f"SIMLI_FACE_ID_{key.upper()}",)
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value, name
    return DEFAULT_FACE_IDS[key], "default"


def _api_key() -> str:
    return (os.getenv(ENV_API_KEY) or "").strip()


def edition_avatar(edition: str | None) -> dict[str, Any]:
    key = normalize_edition(edition)
    spec = EDITION_GLB[key]
    path = _public_dir() / spec["glb"].lstrip("/")
    installed = path.is_file()
    return {
        "edition": key,
        "glb": spec["glb"],
        "body": spec["body"],
        "installed": installed,
        "placeholder": not installed,
    }


def simli_status(edition: str | None = None) -> dict[str, Any]:
    """Honest status. Never includes the API key or the face id value."""
    key = normalize_edition(edition)
    face, face_env = _face_id(key)
    missing = []
    if not _api_key():
        missing.append(ENV_API_KEY)
    if not face:
        missing.append(face_env)
    enabled = not missing
    if enabled:
        reason = (
            "Simli is on for this edition. It renders the face only. "
            f"Sessions stop after {MAX_SESSION_LENGTH_SECONDS}s "
            f"or {MAX_IDLE_SECONDS}s of silence."
        )
        status = "enabled"
        renderer = "simli"
    else:
        reason = (
            "Simli is unset (" + ", ".join(missing) + "). "
            "TalkingHead is the avatar."
        )
        status = "disabled"
        renderer = "talkinghead"
    avatar = edition_avatar(key)
    return {
        "enabled": enabled,
        "status": status,
        "renderer": renderer,
        "edition": key,
        "missing": missing,
        "reason": reason,
        "face_id_set": bool(face),
        "face_env": face_env,
        "face_only": True,
        "max_session_length": MAX_SESSION_LENGTH_SECONDS,
        "max_idle_time": MAX_IDLE_SECONDS,
        "audio_format": AUDIO_FORMAT,
        "sample_rate": SAMPLE_RATE,
        "fallback": "talkinghead",
        "edition_avatar": avatar,
        "talkinghead_placeholder": dict(PLACEHOLDER),
    }


def _public_session(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop anything that is not the session token or ice server list."""
    token = ""
    if isinstance(payload, dict):
        token = str(payload.get("session_token") or "")
    return {"session_token": token}


def _ice_servers(payload: Any) -> list:
    if not isinstance(payload, dict):
        return list(_DEFAULT_STUN)
    raw = payload.get("iceServers") or payload.get("ice_servers") or payload.get("ice")
    if isinstance(raw, list) and raw:
        return raw
    return list(_DEFAULT_STUN)


async def create_session(
    edition: str | None = None,
    *,
    http_post: Optional[Callable[..., Any]] = None,
    http_get: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Mint a Simli session token. The API key is not returned."""
    status = simli_status(edition)
    if not status["enabled"]:
        return {**status, "session_token": "", "ice_servers": []}
    face, _env_name = _face_id(status["edition"])
    headers = {"x-simli-api-key": _api_key(), "Content-Type": "application/json"}
    body = {
        "faceId": face,
        "apiVersion": "v2",
        "handleSilence": True,
        "maxSessionLength": MAX_SESSION_LENGTH_SECONDS,
        "maxIdleTime": MAX_IDLE_SECONDS,
        "audioInputFormat": AUDIO_FORMAT,
    }
    try:
        token_payload = await _request_json("POST", TOKEN_URL, headers, body, http_post, http_get)
        ice_payload = await _request_json("GET", ICE_URL, headers, None, http_post, http_get)
    except Exception:
        logger.warning("Simli session request failed")
        failed = dict(status)
        failed.update({
            "enabled": False,
            "status": "disabled",
            "renderer": "talkinghead",
            "reason": "Simli session was refused. TalkingHead is the avatar.",
            "session_token": "",
            "ice_servers": [],
        })
        return failed
    public = _public_session(token_payload)
    if not public["session_token"]:
        failed = dict(status)
        failed.update({
            "enabled": False,
            "status": "disabled",
            "renderer": "talkinghead",
            "reason": "Simli did not return a session token. TalkingHead is the avatar.",
            "session_token": "",
            "ice_servers": [],
        })
        return failed
    return {
        **status,
        "session_token": public["session_token"],
        "webrtc_url": WEBRTC_URL,
        "ice_servers": _ice_servers(ice_payload),
        "audio_source": "max_tts_and_live_voice",
    }


async def _request_json(method, url, headers, body, http_post, http_get) -> dict:
    if method == "POST":
        if http_post is None:
            import httpx

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=body, headers=headers)
            status = response.status_code
            try:
                payload = response.json()
            except Exception:
                payload = {}
        else:
            response = http_post(url, body, headers)
            if hasattr(response, "__await__"):
                response = await response
            status = getattr(response, "status_code", 200)
            payload = response.json() if hasattr(response, "json") else (response or {})
            if hasattr(payload, "__await__"):
                payload = await payload
    else:
        if http_get is None:
            import httpx

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers)
            status = response.status_code
            try:
                payload = response.json()
            except Exception:
                payload = {}
        else:
            response = http_get(url, headers)
            if hasattr(response, "__await__"):
                response = await response
            status = getattr(response, "status_code", 200)
            payload = response.json() if hasattr(response, "json") else (response or {})
            if hasattr(payload, "__await__"):
                payload = await payload
    if status >= 400:
        logger.warning("Simli %s failed status=%s", method, status)
        raise RuntimeError(f"simli http {status}")
    return payload if isinstance(payload, dict) else {}


def _load_usage() -> dict:
    path = _usage_path()
    if not path.is_file():
        return {"entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"entries": []}
    if not isinstance(data, dict):
        return {"entries": []}
    data.setdefault("entries", [])
    return data


def _save_usage(data: dict) -> None:
    path = _usage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_usage(edition: str | None, seconds: float, source: str = "simli") -> dict[str, Any]:
    """Log minutes for the usage card. Seconds are capped at the session limit."""
    try:
        raw = float(seconds)
    except (TypeError, ValueError):
        raw = 0.0
    if raw < 0:
        raw = 0.0
    capped = min(raw, float(MAX_SESSION_LENGTH_SECONDS))
    minutes = round(capped / 60.0, 3)
    key = normalize_edition(edition)
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "edition": key,
        "seconds": round(capped, 3),
        "minutes": minutes,
        "capped": capped != raw,
        "source": (source or "simli")[:40],
    }
    data = _load_usage()
    rows = list(data.get("entries") or [])
    rows.append(entry)
    data["entries"] = rows[-500:]
    _save_usage(data)
    try:
        from app.services.max.token_tracker import token_tracker

        token_tracker.log_usage(
            model="simli-avatar",
            provider="simli",
            input_tokens=0,
            output_tokens=int(capped),
            endpoint="avatar/simli/usage",
            feature="avatar",
            business=key,
            source="simli_avatar",
            source_module="simli_avatar",
            route_name="avatar/simli/usage",
        )
    except Exception:
        logger.debug("simli usage tracker write skipped", exc_info=True)
    card = usage_card(key)
    return {**entry, "total_minutes": card["minutes"]}


def usage_card(edition: str | None = None) -> dict[str, Any]:
    rows = list(_load_usage().get("entries") or [])
    key = None
    if edition:
        key = normalize_edition(edition)
        rows = [row for row in rows if row.get("edition") == key]
    seconds = 0.0
    for row in rows:
        try:
            seconds += float(row.get("seconds") or 0)
        except (TypeError, ValueError):
            continue
    status = simli_status(key or "workroom")
    return {
        "edition": key or "all",
        "seconds": round(seconds, 3),
        "minutes": round(seconds / 60.0, 2),
        "sessions": len(rows),
        "simli_enabled": status["enabled"],
        "renderer": status["renderer"],
        "status": status["status"],
        "reason": status["reason"],
        "max_session_length": MAX_SESSION_LENGTH_SECONDS,
        "max_idle_time": MAX_IDLE_SECONDS,
    }
