"""WhatsApp Business Cloud API channel for Workroom Max.

Self-contained on purpose. feature/amp-edition carries the same module
and the same public functions. Edition-specific work (voice drafts, photo
quotes, Max chat) is reached through the default handlers below; the
webhook, signature check, allowlist, 24-hour window, and send gate do not
change between editions.

Config is env-only. When any of the four variables is unset the channel
stays disabled and status says so. This module never logs those values.

Public API (keep identical across editions):
    channel_status, verify_signature, subscription_challenge, parse_inbound,
    founder_allowlist, is_allowlisted, note_customer_window,
    customer_window_open, reply_mode, reply_in_window, send_template, process_webhook
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("max.whatsapp")

ENV_ACCESS_TOKEN = "WHATSAPP_ACCESS_TOKEN"
ENV_PHONE_NUMBER_ID = "WHATSAPP_PHONE_NUMBER_ID"
ENV_APP_SECRET = "WHATSAPP_APP_SECRET"
ENV_VERIFY_TOKEN = "WHATSAPP_VERIFY_TOKEN"
REQUIRED_ENV = (
    ENV_ACCESS_TOKEN,
    ENV_PHONE_NUMBER_ID,
    ENV_APP_SECRET,
    ENV_VERIFY_TOKEN,
)

GRAPH_VERSION = "v21.0"
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"
WINDOW_HOURS = 24
ENV_REPLY_MODE = "WHATSAPP_REPLY_MODE"
REPLY_MODES = ("voice_text", "text", "match")
VOICE_FALLBACK_NOTE = "Voice note unavailable (TTS failed). Text only."

_lock = threading.Lock()


class WhatsAppSendBlocked(PermissionError):
    """Outbound WhatsApp send refused."""


def _state_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "whatsapp_channel_state.json"


def _blank(name: str) -> bool:
    return not (os.getenv(name) or "").strip()


def _secret(name: str) -> str:
    return (os.getenv(name) or "").strip()


def channel_status() -> dict[str, Any]:
    """Honest status. Names of missing env vars only — never their values."""
    missing = [name for name in REQUIRED_ENV if _blank(name)]
    enabled = not missing
    allow_count = len(founder_allowlist())
    if enabled and allow_count == 0:
        reason = (
            "WhatsApp credentials are set, but the founder allowlist is empty, "
            "so every inbound message is ignored and nothing is sent."
        )
    elif enabled:
        reason = (
            "WhatsApp Business Cloud API is on for founder numbers only. "
            "Session replies stay inside the 24 hour window. "
            "Approved templates are the only send outside that window. "
            "Draft quotes are not sent until an explicit confirm."
        )
    else:
        reason = (
            "WhatsApp is disabled until "
            + ", ".join(REQUIRED_ENV)
            + " are all set."
        )
    return {
        "channel": "whatsapp",
        "enabled": enabled,
        "configured": enabled,
        "status": "enabled" if enabled else "disabled",
        "missing": missing,
        "reason": reason,
        "webhook": "/api/v1/whatsapp/webhook",
        "allowlist": "founder_numbers_only",
        "allowlist_count": allow_count,
        "customer_care_window_hours": WINDOW_HOURS,
        "drafts_require_explicit_confirm": True,
        "autonomous_messaging_allowed": False,
        "interface_point": "whatsapp_cloud_api",
        "graph_version": GRAPH_VERSION,
        "reply_mode": reply_mode(),
        "calling_enabled": bool((os.getenv("WHATSAPP_CALLING_ENABLED") or "").strip().lower() in ("1", "true", "yes", "on")),
    }


def reply_mode() -> str:
    """voice_text (default), text, or match. Anything else stays voice_text."""
    raw = (os.getenv(ENV_REPLY_MODE) or "voice_text").strip().lower().replace("-", "_")
    if raw in REPLY_MODES:
        return raw
    return "voice_text"


def wants_voice(mode: str | None = None, *, inbound_type: str = "", inbound_voice: bool = False) -> bool:
    chosen = mode or reply_mode()
    if chosen == "text":
        return False
    if chosen == "match":
        return inbound_voice or (inbound_type or "") == "audio"
    return True


def summarize_reply(text: str) -> str:
    """Short text twin of a voice note. Short replies stay whole."""
    raw = (text or "").strip()
    if not raw:
        return ""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(raw) <= 400 and len(lines) <= 6:
        return raw
    picked: list[str] = []
    for line in lines:
        low = line.lower()
        if not picked:
            picked.append(line)
            continue
        if any(token in low for token in ("total", "not sent", "not emailed", "missing", "draft")):
            picked.append(line)
    if len(picked) == 1 and len(lines) > 1:
        picked.append(lines[1])
    summary = "\n".join(picked[:8])
    if len(summary) > 500:
        summary = summary[:497].rstrip() + "..."
    return summary


def _eq(left: str, right: str) -> bool:
    if not left or not right:
        return False
    a = left.encode()
    b = right.encode()
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """True only when X-Hub-Signature-256 matches the app secret."""
    secret = _secret(ENV_APP_SECRET)
    header = (signature_header or "").strip()
    if not secret or not header.startswith("sha256=") or not raw_body:
        return False
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return _eq(header[7:], digest)


def subscription_challenge(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    """Return the hub challenge when the verify token matches. None otherwise."""
    if _blank(ENV_VERIFY_TOKEN):
        return None
    if (mode or "") != "subscribe":
        return None
    if not challenge:
        return None
    if not _eq(token or "", _secret(ENV_VERIFY_TOKEN)):
        return None
    return str(challenge)


def normalize_msisdn(value: str | None) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return digits
    return digits


def founder_allowlist() -> frozenset[str]:
    """Rafael's numbers on file. Not an env secret.

    The workroom phone in business.json is the only founder number stored
    in this repo. Optional founder_phones / owner_phones lists are honored
    when present. Local and E.164 forms collapse to one key.
    """
    path = Path(__file__).resolve().parents[2] / "config" / "business.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        data = {}
    raw: list[str] = []
    phone = str(data.get("business_phone") or "").strip()
    if phone:
        raw.append(phone)
    for key in ("founder_phones", "owner_phones"):
        extra = data.get(key) or []
        if isinstance(extra, str):
            extra = [extra]
        if isinstance(extra, dict):
            extra = list(extra.values())
        if isinstance(extra, list):
            for item in extra:
                if isinstance(item, dict):
                    raw.append(str(item.get("phone") or item.get("number") or item.get("wa_id") or ""))
                else:
                    raw.append(str(item))
    env_phones = os.getenv("WHATSAPP_FOUNDER_PHONES") or ""
    if env_phones.strip():
        raw.extend(part.strip() for part in env_phones.split(",") if part.strip())
    try:
        from app.services.max.whatsapp_log import load_whatsapp_phonebook

        for row in load_whatsapp_phonebook():
            raw.append(str(row.get("phone") or ""))
    except Exception:
        logger.debug("WhatsApp phonebook unavailable for allowlist")
    return frozenset(n for n in (normalize_msisdn(item) for item in raw if str(item).strip()) if n)


def is_allowlisted(wa_id: str | None) -> bool:
    number = normalize_msisdn(wa_id)
    if not number:
        return False
    allowed = founder_allowlist()
    if number in allowed:
        return True
    tail = number[-10:]
    return any(item.endswith(tail) and len(tail) == 10 for item in allowed)


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return {"windows": {}, "seen": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"windows": {}, "seen": []}
    if not isinstance(data, dict):
        return {"windows": {}, "seen": []}
    data.setdefault("windows", {})
    data.setdefault("seen", [])
    return data


def _save_state(data: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_runtime_state() -> None:
    with _lock:
        _save_state({"windows": {}, "seen": [], "conversations": {}})


def _parse_stamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        stamp = value
    else:
        text = str(value or "").strip()
        if text.isdigit():
            stamp = datetime.fromtimestamp(int(text), tz=timezone.utc)
        else:
            try:
                stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                stamp = datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def note_customer_window(wa_id: str, at: Any = None) -> None:
    number = normalize_msisdn(wa_id)
    if not number:
        return
    stamp = _parse_stamp(at if at is not None else datetime.now(timezone.utc))
    with _lock:
        data = _load_state()
        data["windows"][number] = stamp.isoformat()
        _save_state(data)


def customer_window_open(wa_id: str, now: datetime | None = None) -> bool:
    number = normalize_msisdn(wa_id)
    if not number:
        return False
    with _lock:
        raw = (_load_state().get("windows") or {}).get(number)
    if not raw:
        return False
    try:
        opened = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if opened.tzinfo is None:
        opened = opened.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc) - opened <= timedelta(hours=WINDOW_HOURS)


def _seen(message_id: str) -> bool:
    if not message_id:
        return False
    with _lock:
        data = _load_state()
        return message_id in (data.get("seen") or [])


def _mark_seen(message_id: str) -> None:
    if not message_id:
        return
    with _lock:
        data = _load_state()
        seen = list(data.get("seen") or [])
        if message_id not in seen:
            seen.append(message_id)
        data["seen"] = seen[-500:]
        _save_state(data)


def parse_inbound(payload: dict | None) -> list[dict[str, Any]]:
    """Flatten a Cloud API webhook into one dict per inbound message."""
    if not isinstance(payload, dict):
        return []
    if payload.get("object") not in (None, "whatsapp_business_account"):
        return []
    found: list[dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            value = (change or {}).get("value") or {}
            if not isinstance(value, dict):
                continue
            for message in value.get("messages") or []:
                if not isinstance(message, dict):
                    continue
                found.append(_normalize_inbound_message(message))
            for call in value.get("calls") or []:
                if not isinstance(call, dict):
                    continue
                event = str(call.get("event") or call.get("status") or "event")
                found.append({
                    "message_id": str(call.get("id") or ""),
                    "from": str(call.get("from") or call.get("to") or ""),
                    "timestamp": call.get("timestamp"),
                    "type": "call",
                    "text": f"Call {event}",
                    "media_id": "",
                    "mime_type": "",
                    "caption": "",
                    "voice": False,
                    "filename": "",
                    "call_event": event,
                })
    return found


def _interactive_text(message: dict[str, Any]) -> str:
    inter = message.get("interactive") or {}
    if not isinstance(inter, dict):
        return ""
    for key in ("nfm_reply", "button_reply", "list_reply"):
        part = inter.get(key) or {}
        if isinstance(part, dict):
            text = str(part.get("body") or part.get("title") or part.get("description") or "").strip()
            if text:
                return text
    return str(inter.get("body") or "").strip()


def _raw_text_body(message: dict[str, Any]) -> str:
    raw = message.get("text")
    if isinstance(raw, dict):
        return str(raw.get("body") or raw.get("text") or "").strip()
    if raw:
        return str(raw).strip()
    return ""


def _extract_inbound_text(message: dict[str, Any]) -> str:
    """Pull a usable body from text, replies, albums, interactive, or unknown types."""
    return (
        _raw_text_body(message)
        or _interactive_text(message)
        or str((message.get("button") or {}).get("text") or "").strip()
        or str((message.get("system") or {}).get("body") or "").strip()
        or str((message.get("reaction") or {}).get("emoji") or "").strip()
    )


def _normalize_inbound_message(message: dict[str, Any]) -> dict[str, Any]:
    """Flatten one Cloud API message. Album captions, context replies, and
    unknown/interactive types with a body become normal text so they are not
    answered with 'That message type is not handled.'
    """
    raw_type = str(message.get("type") or "").strip().lower()
    ctx = message.get("context") if isinstance(message.get("context"), dict) else {}
    item: dict[str, Any] = {
        "message_id": str(message.get("id") or ""),
        "from": str(message.get("from") or ""),
        "timestamp": message.get("timestamp"),
        "type": raw_type,
        "raw_type": raw_type,
        "text": "",
        "media_id": "",
        "mime_type": "",
        "caption": "",
        "voice": False,
        "filename": "",
        "context_id": str(ctx.get("id") or ""),
        "context_from": str(ctx.get("from") or ""),
    }
    extracted = _extract_inbound_text(message)
    if raw_type in {"audio", "image", "video", "document", "sticker"}:
        media = message.get(raw_type) or {}
        if isinstance(media, dict):
            item["media_id"] = str(media.get("id") or "")
            item["mime_type"] = str(media.get("mime_type") or "")
            item["caption"] = str(media.get("caption") or "")
            item["voice"] = bool(media.get("voice"))
            item["filename"] = str(media.get("filename") or "")
        if extracted and not item["caption"]:
            item["caption"] = extracted
    elif raw_type == "location":
        loc = message.get("location") or {}
        if isinstance(loc, dict):
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            name = loc.get("name") or loc.get("address") or ""
            item["text"] = extracted or f"Location: {lat}, {lon} ({name})".strip()
            item["location"] = loc
    else:
        # text, button, interactive, system, unknown, unsupported, empty,
        # album companion comments, and replies that carry context.
        item["text"] = extracted
        placeholder = raw_type in {"", "unknown", "unsupported", "interactive", "button", "system"}
        if item["text"] and (placeholder or raw_type not in {"call", "contacts", "order", "reaction"}):
            item["type"] = "text"
        elif raw_type in {"unknown", "unsupported", ""}:
            item["type"] = "text" if item["text"] else "ignored"
    return item


async def _safe_download(
    media_id: str,
    http_get: Optional[Callable[..., Any]] = None,
) -> tuple[bytes, str]:
    if not media_id:
        return b"", ""
    try:
        return await download_media(media_id, http_get=http_get)
    except Exception:
        logger.warning("WhatsApp media download failed", exc_info=True)
        return b"", ""


def _default_media_name(message: dict[str, Any]) -> str:
    if message.get("filename"):
        return str(message["filename"])
    kind = str(message.get("type") or "file")
    voice = bool(message.get("voice") or kind == "audio")
    if voice:
        return "voice.ogg"
    if kind == "image":
        return "photo.jpg"
    if kind == "sticker":
        return "sticker.webp"
    if kind == "video":
        return "video.mp4"
    if kind == "document":
        return "document.bin"
    if kind == "location":
        return "location.json"
    return f"{kind or 'file'}.bin"


def _persist_inbound_media(
    message: dict[str, Any],
    content: bytes,
    mime: str,
    *,
    hint_text: str = "",
) -> list[dict[str, Any]]:
    """Save inbound bytes and file photos/docs when the job is known."""
    from app.services.max.whatsapp_log import prepare_inbound_attachment

    from app.services.max.whatsapp_folders import FILEABLE_MEDIA, classify_media_type

    kind = str(message.get("type") or "document")
    filename = _default_media_name(message)
    mime_name = mime or str(message.get("mime_type") or "")
    media_type = "voice" if (message.get("voice") or kind == "audio") else kind
    if kind == "image":
        media_type = "image"
    else:
        media_type = classify_media_type(kind, filename, mime_name)
    hint = hint_text or str(message.get("caption") or message.get("text") or "")
    fileable = media_type in FILEABLE_MEDIA
    if not content and kind != "location":
        return []
    payload = content
    if kind == "location":
        loc = message.get("location") or {}
        payload = json.dumps(loc, default=str).encode()
        mime = mime or "application/json"
    return [prepare_inbound_attachment(
        payload,
        filename=filename,
        mime_type=mime or message.get("mime_type") or "application/octet-stream",
        media_type=media_type,
        wa_id=str(message.get("from") or ""),
        hint_text=hint,
        wa_media_id=str(message.get("media_id") or ""),
        file_to_job=fileable,
    )]


def _log_chat(**kwargs: Any) -> int:
    """Best-effort durable log. Failures never block send or webhook ack."""
    try:
        from app.services.max.whatsapp_log import log_message

        return int(log_message(**kwargs) or 0)
    except Exception:
        logger.warning("WhatsApp chat log write failed", exc_info=True)
        return 0


def _apply_status_updates(payload: dict | None) -> int:
    updated = 0
    try:
        from app.services.max.whatsapp_log import update_delivery_status

        for st in parse_statuses(payload):
            if update_delivery_status(
                st.get("id") or "",
                st.get("status") or "",
                error_code=st.get("error_code") or "",
                error_message=st.get("error_message") or "",
            ):
                updated += 1
    except Exception:
        logger.warning("WhatsApp delivery status update failed", exc_info=True)
    return updated


def _inbound_log_fields(message: dict[str, Any]) -> dict[str, Any]:
    kind = str(message.get("type") or "text")
    voice = bool(message.get("voice") or kind == "audio")
    caption = str(message.get("caption") or "")
    filename = str(message.get("filename") or "")
    text = str(message.get("text") or "")
    if voice:
        body = text or "[voice note]"
        msg_type = "voice"
    elif kind == "image":
        body = caption or text or "[photo]"
        msg_type = "image"
    elif kind == "document":
        label = filename or "document"
        extra = caption or text
        body = f"[document: {label}]" + (f" {extra}" if extra else "")
        msg_type = "document"
    elif kind == "call":
        body = text or "[call]"
        msg_type = "call"
    elif kind == "location":
        body = text or "[location]"
        msg_type = "location"
    elif kind in {"video", "sticker"}:
        body = caption or text or f"[{kind}]"
        msg_type = kind
    else:
        body = text or caption or f"[{kind or 'message'}]"
        msg_type = kind or "text"
    metadata: dict[str, Any] = {}
    if filename:
        metadata["filename"] = filename
    if message.get("media_id"):
        metadata["media_id"] = message.get("media_id")
    if message.get("call_event"):
        metadata["call_event"] = message.get("call_event")
    return {
        "message_type": msg_type,
        "body": body,
        "caption": caption,
        "metadata": metadata,
    }


def parse_statuses(payload: dict | None) -> list[dict[str, Any]]:
    """Flatten Cloud API status updates into dicts."""
    if not isinstance(payload, dict):
        return []
    found: list[dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            value = (change or {}).get("value") or {}
            if not isinstance(value, dict):
                continue
            for st in value.get("statuses") or []:
                if not isinstance(st, dict):
                    continue
                err = (st.get("errors") or [{}])[0] if st.get("errors") else {}
                found.append({
                    "id": str(st.get("id") or ""),
                    "status": str(st.get("status") or ""),
                    "timestamp": st.get("timestamp"),
                    "recipient_id": str(st.get("recipient_id") or ""),
                    "error_code": str(err.get("code") or ""),
                    "error_message": str(err.get("title") or err.get("message") or ""),
                })
    return found


def parse_inbound_calls(payload: dict | None) -> list[dict[str, Any]]:
    """Flatten a Cloud API webhook into inbound call events."""
    if not isinstance(payload, dict):
        return []
    if payload.get("object") not in (None, "whatsapp_business_account"):
        return []
    calls: list[dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            field = change.get("field")
            value = (change or {}).get("value") or {}
            if not isinstance(value, dict):
                continue
            # Meta may send calls under changes with field == 'calls' or value having 'calls'
            raw_calls = value.get("calls") or []
            if not isinstance(raw_calls, list) and isinstance(raw_calls, dict):
                raw_calls = [raw_calls]
            for call_ev in raw_calls:
                if not isinstance(call_ev, dict):
                    continue
                call_id = str(call_ev.get("id") or call_ev.get("call_id") or "")
                caller = str(call_ev.get("from") or "")
                event = str(call_ev.get("event") or "")
                session = call_ev.get("session") or {}
                sdp = ""
                if isinstance(session, dict):
                    sdp = session.get("sdp") or ""
                calls.append({
                    "call_id": call_id,
                    "from": caller,
                    "event": event,
                    "sdp": sdp,
                    "timestamp": call_ev.get("timestamp"),
                    "raw": call_ev,
                })
    return calls



def _require_enabled() -> None:
    if not channel_status()["enabled"]:
        raise WhatsAppSendBlocked("WhatsApp is disabled")


def _graph_messages_url() -> str:
    phone_id = _secret(ENV_PHONE_NUMBER_ID)
    return f"{GRAPH_ROOT}/{phone_id}/messages"


async def _post_graph(body: dict, http_post: Optional[Callable[..., Any]] = None) -> dict:
    _require_enabled()
    token = _secret(ENV_ACCESS_TOKEN)
    url = _graph_messages_url()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if http_post is None:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
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
    if status >= 400:
        logger.warning("WhatsApp graph send failed status=%s", status)
        raise WhatsAppSendBlocked(f"WhatsApp graph rejected the send ({status})")
    return payload if isinstance(payload, dict) else {"ok": True}


def _media_url() -> str:
    phone_id = _secret(ENV_PHONE_NUMBER_ID)
    return f"{GRAPH_ROOT}/{phone_id}/media"


async def upload_media(
    data: bytes,
    mime: str,
    filename: str,
    *,
    http_upload: Optional[Callable[..., Any]] = None,
) -> str:
    """Upload one media file. Returns the Graph media id. Never logs the token."""
    _require_enabled()
    if not data:
        raise WhatsAppSendBlocked("empty media")
    url = _media_url()
    headers = {"Authorization": f"Bearer {_secret(ENV_ACCESS_TOKEN)}"}
    if http_upload is None:
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=headers,
                data={"messaging_product": "whatsapp"},
                files={"file": (filename, data, mime)},
            )
        status = response.status_code
        try:
            payload = response.json()
        except Exception:
            payload = {}
    else:
        response = http_upload(url, data, mime, filename, headers)
        if hasattr(response, "__await__"):
            response = await response
        status = getattr(response, "status_code", 200)
        payload = response.json() if hasattr(response, "json") else (response or {})
        if hasattr(payload, "__await__"):
            payload = await payload
    if status >= 400 or not isinstance(payload, dict) or not payload.get("id"):
        logger.warning("WhatsApp media upload failed status=%s", status)
        raise WhatsAppSendBlocked(f"WhatsApp media upload failed ({status})")
    return str(payload["id"])


def _pdf_filename(name: str) -> str:
    base = Path(name or "document.pdf").name.replace(" ", "_")
    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"
    return base[:80] or "document.pdf"


async def _voice_ogg(
    text: str,
    synthesize: Optional[Callable[..., Any]],
) -> tuple[bytes, str]:
    """Return OGG/Opus bytes, or empty bytes and a short reason."""
    try:
        if synthesize is None:
            from app.services.max.tts_service import tts_service

            path = await tts_service.synthesize_for_whatsapp(text)
            if path is None:
                reason = (tts_service.last_error or "TTS failed").split("\n")[0][:180]
                return b"", reason or "TTS failed"
            data = Path(path).read_bytes()
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        else:
            produced = synthesize(text)
            if hasattr(produced, "__await__"):
                produced = await produced
            if isinstance(produced, Path):
                data = produced.read_bytes()
            else:
                data = bytes(produced or b"")
    except Exception:
        logger.warning("WhatsApp TTS failed", exc_info=True)
        return b"", "TTS failed"
    if not data.startswith(b"OggS"):
        return b"", "audio was not OGG/Opus"
    return data, ""


def founder_documents(pipeline: dict | None) -> tuple[list[dict[str, Any]], str]:
    """Quote and drawing PDFs for the founder. Failures stay in the note."""
    if not pipeline or not pipeline.get("handled"):
        return [], ""
    docs: list[dict[str, Any]] = []
    notes: list[str] = []
    quote_id = str(pipeline.get("quote_id") or "").strip()
    if quote_id:
        try:
            from app.services.quote_pdf_service import generate_quote_pdf

            data = generate_quote_pdf(quote_id)
            if not data:
                raise RuntimeError("empty pdf")
            number = pipeline.get("quote_number") or "quote"
            docs.append({
                "filename": _pdf_filename(f"{number}.pdf"),
                "data": data,
                "mime": "application/pdf",
                "kind": "quote",
            })
        except Exception:
            logger.warning("WhatsApp quote PDF skipped", exc_info=True)
            notes.append("Quote PDF was not attached.")
    drawing = pipeline.get("drawing") or {}
    if isinstance(drawing, dict):
        pdf_path = str(drawing.get("pdf_path") or (drawing.get("persist") or {}).get("pdf_path") or "")
        svg = drawing.get("svg") or ""
        try:
            if pdf_path and Path(pdf_path).is_file() and pdf_path.lower().endswith(".pdf"):
                docs.append({
                    "filename": _pdf_filename(Path(pdf_path).name),
                    "data": Path(pdf_path).read_bytes(),
                    "mime": "application/pdf",
                    "kind": "drawing",
                })
            elif svg:
                from app.services.vision.bench_renderer import drawings_to_pdf

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
                    dest = Path(handle.name)
                drawings_to_pdf([{"svg": svg, "title": "Drawing"}], str(dest))
                docs.append({
                    "filename": "drawing.pdf",
                    "data": dest.read_bytes(),
                    "mime": "application/pdf",
                    "kind": "drawing",
                })
                dest.unlink(missing_ok=True)
        except Exception:
            logger.warning("WhatsApp drawing PDF skipped", exc_info=True)
            notes.append("Drawing PDF was not attached.")
    return docs, " ".join(notes)


def _split_reply(reply: Any) -> tuple[str, list]:
    if isinstance(reply, dict):
        return str(reply.get("text") or ""), list(reply.get("documents") or [])
    return str(reply or ""), []


def _outbound(text: str, pipeline: dict | None = None):
    documents, note = founder_documents(pipeline)
    body = (text or "").strip()
    if note:
        body = f"{body}\n{note}".strip()
    if documents:
        return {"text": body, "documents": documents}
    return body


async def reply_in_window(
    to: str,
    text: str,
    *,
    http_post: Optional[Callable[..., Any]] = None,
    http_upload: Optional[Callable[..., Any]] = None,
    inbound_type: str = "",
    inbound_voice: bool = False,
    documents: Optional[list[dict[str, Any]]] = None,
    synthesize: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Session reply inside the 24h window.

    voice_text sends an OGG/Opus voice note plus a text summary.
    text sends the words only. match follows the inbound message.
    A TTS failure sends the full text and says the voice note was skipped.
    PDFs ride along as document messages. This does not email a client.
    """
    _require_enabled()
    if not is_allowlisted(to):
        raise WhatsAppSendBlocked("recipient is not on the founder allowlist")
    if not customer_window_open(to):
        raise WhatsAppSendBlocked(
            "outside the 24 hour window; an approved template and explicit confirm are required"
        )
    mode = reply_mode()
    number = normalize_msisdn(to)
    original = (text or "").strip()
    voice_sent = False
    voice_fallback = ""
    graph: dict[str, Any] = {}
    if wants_voice(mode, inbound_type=inbound_type, inbound_voice=inbound_voice) and original:
        audio, reason = await _voice_ogg(original, synthesize)
        if audio:
            try:
                media_id = await upload_media(
                    audio, "audio/ogg", "voice.ogg", http_upload=http_upload,
                )
                graph = await _post_graph({
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": number,
                    "type": "audio",
                    "audio": {"id": media_id, "voice": True},
                }, http_post=http_post)
                voice_sent = True
            except WhatsAppSendBlocked:
                voice_fallback = VOICE_FALLBACK_NOTE
        else:
            voice_fallback = VOICE_FALLBACK_NOTE
            if reason and reason not in voice_fallback:
                logger.info("WhatsApp voice fallback: %s", reason[:120])
    if voice_sent:
        shown = summarize_reply(original)
    else:
        shown = original
        if voice_fallback:
            shown = f"{voice_fallback}\n{shown}".strip()
    text_graph = await _post_graph({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "text",
        "text": {"preview_url": False, "body": shown[:4096]},
    }, http_post=http_post)
    if not graph:
        graph = text_graph
    outbound_msg_id = _public_graph(graph).get("message_id", "")
    attached: list[dict[str, str]] = []
    for doc in documents or []:
        if not isinstance(doc, dict):
            continue
        payload = doc.get("data") or b""
        if isinstance(payload, str):
            payload = payload.encode()
        if not payload:
            continue
        filename = _pdf_filename(str(doc.get("filename") or "document.pdf"))
        doc_id = str(doc.get("doc_id") or doc.get("quote_id") or doc.get("quote_number") or "")
        try:
            media_id = await upload_media(
                bytes(payload), "application/pdf", filename, http_upload=http_upload,
            )
            await _post_graph({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": number,
                "type": "document",
                "document": {
                    "id": media_id,
                    "filename": filename,
                    "caption": str(doc.get("caption") or "Draft. Not sent.")[:1024],
                },
            }, http_post=http_post)
            attached.append({"filename": filename, "media_id": media_id, "doc_id": doc_id, "data": bytes(payload)})
        except WhatsAppSendBlocked:
            logger.warning("WhatsApp PDF attach failed for %s", filename)

    outbound_atts: list[dict[str, Any]] = []
    try:
        from app.services.max.whatsapp_log import store_edition_media

        for row in attached:
            stored = store_edition_media(
                row.get("data") or b"",
                row.get("filename") or "document.pdf",
                "application/pdf",
                "document",
            )
            outbound_atts.append({
                "wa_media_id": row.get("media_id", ""),
                "filename": stored.get("filename") or row.get("filename"),
                "mime_type": "application/pdf",
                "size_bytes": stored.get("size_bytes") or 0,
                "local_path": stored.get("local_path") or "",
                "media_type": "document",
                "doc_id": row.get("doc_id") or "",
                "filing_status": "outbound",
            })
    except Exception:
        logger.warning("WhatsApp outbound document copy failed", exc_info=True)

    log_body = shown
    if attached:
        markers = ", ".join(
            f"{row['filename']}" + (f" ({row['doc_id']})" if row.get("doc_id") else "")
            for row in attached
        )
        log_body = f"{shown}\n[document: {markers}]".strip() if shown else f"[document: {markers}]"
    _log_chat(
        wa_id=number,
        direction="outbound",
        message_type="voice" if voice_sent else ("document" if attached else "text"),
        body=log_body,
        wa_message_id=outbound_msg_id,
        delivery_status="sent",
        metadata={
            "voice_sent": voice_sent,
            "voice_fallback": voice_fallback,
            "reply_mode": mode,
            "documents": [{"filename": d.get("filename", ""), "doc_id": d.get("doc_id", "")} for d in attached],
        },
        attachments=outbound_atts,
    )

    return {
        "sent": True,
        "kind": "session",
        "draft_sent": False,
        "reply_mode": mode,
        "voice_sent": voice_sent,
        "voice_fallback": voice_fallback,
        "documents": [{"filename": d.get("filename", ""), "media_id": d.get("media_id", ""), "doc_id": d.get("doc_id", "")} for d in attached],
        "graph": _public_graph(graph),
    }


async def send_template(
    to: str,
    template_name: str,
    *,
    confirmed: bool,
    language: str = "en",
    components: Optional[list] = None,
    http_post: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Send one already-approved template. Refused unless confirmed is True."""
    _require_enabled()
    if confirmed is not True:
        raise WhatsAppSendBlocked("drafts are not sent without explicit confirmation")
    if not is_allowlisted(to):
        raise WhatsAppSendBlocked("recipient is not on the founder allowlist")
    name = (template_name or "").strip()
    if not name:
        raise WhatsAppSendBlocked("an approved template name is required outside the session window")
    template: dict[str, Any] = {
        "name": name,
        "language": {"code": language or "en"},
    }
    if components:
        template["components"] = components
    body = {
        "messaging_product": "whatsapp",
        "to": normalize_msisdn(to),
        "type": "template",
        "template": template,
    }
    result = await _post_graph(body, http_post=http_post)
    return {
        "sent": True,
        "kind": "template",
        "template_name": name,
        "confirmed": True,
        "graph": _public_graph(result),
    }


def _public_graph(payload: dict) -> dict:
    """Drop anything that could echo credentials. Keep the message id only."""
    messages = payload.get("messages") if isinstance(payload, dict) else None
    message_id = ""
    if isinstance(messages, list) and messages and isinstance(messages[0], dict):
        message_id = str(messages[0].get("id") or "")
    return {"message_id": message_id}


async def download_media(
    media_id: str,
    *,
    http_get: Optional[Callable[..., Any]] = None,
) -> tuple[bytes, str]:
    _require_enabled()
    token = _secret(ENV_ACCESS_TOKEN)
    meta_url = f"{GRAPH_ROOT}/{media_id}"
    headers = {"Authorization": f"Bearer {token}"}
    if http_get is None:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            meta_res = await client.get(meta_url, headers=headers)
            meta_res.raise_for_status()
            meta = meta_res.json()
            file_url = str(meta.get("url") or "")
            mime = str(meta.get("mime_type") or "application/octet-stream")
            file_res = await client.get(file_url, headers=headers)
            file_res.raise_for_status()
            return file_res.content, mime
    meta = http_get(meta_url, headers)
    if hasattr(meta, "__await__"):
        meta = await meta
    if hasattr(meta, "json"):
        meta_body = meta.json()
        if hasattr(meta_body, "__await__"):
            meta_body = await meta_body
    else:
        meta_body = meta
    file_url = str((meta_body or {}).get("url") or "")
    mime = str((meta_body or {}).get("mime_type") or "")
    downloaded = http_get(file_url, headers)
    if hasattr(downloaded, "__await__"):
        downloaded = await downloaded
    content = getattr(downloaded, "content", downloaded)
    if isinstance(content, str):
        content = content.encode()
    return bytes(content or b""), mime or "application/octet-stream"


def _session_key(wa_id: str) -> str:
    return f"whatsapp:{normalize_msisdn(wa_id)}"


# ── One rolling conversation per WhatsApp sender ───────────────────
# 2026-10-04: every inbound message got a fresh studio-<uuid> conversation, so Max
# forgot the previous message ("Send me a pdf here" -> "which document?"). Now one
# conversation_id per wa_id, reused until WHATSAPP_CONVERSATION_IDLE_HOURS (12h)
# of silence, with the recent turns passed as history and the last documents shown.

ENV_CONVERSATION_IDLE_HOURS = "WHATSAPP_CONVERSATION_IDLE_HOURS"
DEFAULT_CONVERSATION_IDLE_HOURS = 12.0
HISTORY_MESSAGES = 12
HISTORY_CHARS = 1500
MAX_ATTACHED_DOCS = 3

WHATSAPP_DIRECTIVE = (
    "\n\n## CHANNEL: WHATSAPP (chat with Rafael, the founder)\n"
    "- This is Rafael's own WhatsApp chat with you. 'here', 'aquí', 'por aquí', 'en este chat' mean: "
    "attach it in THIS WhatsApp chat to Rafael. That is a reply to him, not an outbound send, so it is "
    "allowed without a confirm. Never offer to email it instead, and never call an email tool for it.\n"
    "- To deliver a saved document, call open_final_doc (client name, nickname or job address is fine, "
    "e.g. 'Dahlia last 2 docs'). The channel attaches the PDFs of the documents that tool returns as "
    "WhatsApp documents. Say 'PDF attached'.\n"
    "- Never paste studio.empirebox.store or /docs/view links: they need a login and do not open on "
    "his phone.\n"
    "- If open_final_doc did not find the document, say so plainly and name the closest matches it "
    "returned. Never describe a document as found, opened or attached when the tool failed.\n"
    "- Short, plain text. No markdown headers or tables."
)


def _conversation_idle_hours() -> float:
    try:
        return max(0.5, float(os.getenv(ENV_CONVERSATION_IDLE_HOURS) or DEFAULT_CONVERSATION_IDLE_HOURS))
    except ValueError:
        return DEFAULT_CONVERSATION_IDLE_HOURS


def whatsapp_conversation(wa_id: str, now: datetime | None = None) -> dict[str, Any]:
    """The sender's current conversation (created or rolled over after the idle window)."""
    number = normalize_msisdn(wa_id)
    now = now or datetime.now(timezone.utc)
    with _lock:
        data = _load_state()
        convs = data.setdefault("conversations", {})
        entry = convs.get(number) if isinstance(convs.get(number), dict) else None
        if entry:
            idle = now - _parse_stamp(entry.get("last_at"))
            if idle > timedelta(hours=_conversation_idle_hours()):
                entry = None
        if not entry:
            entry = {
                "conversation_id": f"whatsapp-{number}-{now.strftime('%Y%m%d%H%M%S')}",
                "started_at": now.isoformat(),
                "last_at": now.isoformat(),
                "history": [],
                "last_docs": [],
            }
            convs[number] = entry
            _save_state(data)
        return json.loads(json.dumps(entry))


def remember_whatsapp_turn(
    wa_id: str,
    user_text: str,
    assistant_text: str,
    *,
    docs: Optional[list[dict[str, Any]]] = None,
    now: datetime | None = None,
) -> None:
    number = normalize_msisdn(wa_id)
    now = now or datetime.now(timezone.utc)
    with _lock:
        data = _load_state()
        convs = data.setdefault("conversations", {})
        entry = convs.get(number)
        if not isinstance(entry, dict):
            return
        hist = list(entry.get("history") or [])
        if user_text:
            hist.append({"role": "user", "content": str(user_text)[:HISTORY_CHARS]})
        if assistant_text:
            hist.append({"role": "assistant", "content": str(assistant_text)[:HISTORY_CHARS]})
        entry["history"] = hist[-HISTORY_MESSAGES:]
        entry["last_at"] = now.isoformat()
        if docs:
            entry["last_docs"] = [
                {k: d.get(k) for k in ("doc_id", "title", "version", "type", "filename", "client")}
                for d in docs[:MAX_ATTACHED_DOCS]
            ]
        _save_state(data)


_STUDIO_LINK_MD = re.compile(r"\[([^\]]*)\]\((?:https?://[^)\s]*empirebox\.store[^)\s]*|/docs/view[^)\s]*|/docs-hub[^)\s]*)\)")
_STUDIO_URL = re.compile(r"(?:https?://\S*empirebox\.store\S*|(?<![\w/])/docs/view\?id=[\w-]+|(?<![\w/])/api/v1/docs-hub/\S+)")


def strip_studio_links(text: str) -> str:
    """Studio/viewer links need a login and do not open on the phone."""
    def _md(m: re.Match) -> str:
        label = m.group(1).strip()
        return "" if re.fullmatch(r"\d+", label or "") else label

    out = _STUDIO_LINK_MD.sub(_md, text or "")
    out = _STUDIO_URL.sub("", out)
    out = re.sub(r"[ \t]+([,.;:)])", r"\1", out)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"`\s*`", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip()


def _docs_from_tool_results(tool_results: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(found docs, failed open_final_doc calls) from a chat turn's tool results."""
    found: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in tool_results or []:
        if not isinstance(row, dict) or row.get("tool") != "open_final_doc":
            continue
        if not row.get("success"):
            failed.append(row)
            continue
        res = row.get("result") or {}
        docs = res.get("docs") or [res]
        for d in docs:
            doc_id = str(d.get("doc_id") or "")
            if doc_id and doc_id not in seen:
                seen.add(doc_id)
                found.append(d)
    return found, failed


def _attach_final_docs(
    docs: list[dict[str, Any]],
    *,
    fetch: Optional[Callable[[str], bytes]] = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """PDF bytes for Final Docs, ready for reply_in_window(documents=...)."""
    from app.services.max.doc_lookup import fetch_pdf

    get = fetch or (lambda doc_id: fetch_pdf(doc_id))
    out: list[dict[str, Any]] = []
    missing: list[str] = []
    for d in docs[:MAX_ATTACHED_DOCS]:
        title = str(d.get("title") or d.get("doc_id") or "document")
        try:
            data = get(str(d.get("doc_id") or ""))
        except Exception:
            logger.warning("WhatsApp final doc fetch failed", exc_info=True)
            data = b""
        if not data:
            missing.append(title)
            continue
        name = d.get("filename") or f"{title}.pdf"
        out.append({"filename": _pdf_filename(str(name)), "data": data, "mime": "application/pdf", "kind": "final_doc",
                    "caption": f"{title}. For you; not sent to the client."})
    return out, missing


def _doc_lines(docs: list[dict[str, Any]]) -> str:
    rows = []
    for i, d in enumerate(docs[:MAX_ATTACHED_DOCS], 1):
        ver = f" ({d.get('version')}{', FINAL' if d.get('is_final') else ''})" if d.get("version") else ""
        mod = str(d.get("modified") or "")[:10]
        rows.append(f"{i}. {d.get('title')}{ver}" + (f", updated {mod}" if mod else ""))
    return "\n".join(rows)


def _no_doc_reply(failed: list[dict[str, Any]]) -> str:
    """Honest reply when every open_final_doc call failed."""
    first = failed[0] if failed else {}
    err = str(first.get("error") or "")
    m = re.search(r'matched "([^"]+)"', err)
    asked = m.group(1) if m else "that"
    closest = ((first.get("result") or {}).get("closest")) or []
    lines = [f'I could not find a saved document for "{asked}". Nothing attached.']
    if closest:
        lines.append("Closest matches:")
        for c in closest[:4]:
            latest = c.get("latest") or {}
            extra = f" (latest: {latest.get('title')})" if latest.get("title") else ""
            lines.append(f"- {c.get('client')}{extra}")
    else:
        lines.append("No close client names either. Tell me the client, nickname or job address.")
    return "\n".join(lines)


def _finish_doc_reply(
    wa_id: str,
    user_text: str,
    text: str,
    docs: list[dict[str, Any]],
    *,
    fetch: Optional[Callable[[str], bytes]] = None,
):
    documents, missing = _attach_final_docs(docs, fetch=fetch)
    body = strip_studio_links(text)
    if documents:
        body = f"{body}\nPDF attached ({len(documents)}). For you only; nothing was sent to the client.".strip()
    if missing:
        body = f"{body}\nCould not attach: {', '.join(missing)}.".strip()
    remember_whatsapp_turn(wa_id, user_text, body, docs=docs if documents else None)
    if documents:
        return {"text": body, "documents": documents}
    return body


async def max_chat(text: str, wa_id: str, *, fetch: Optional[Callable[[str], bytes]] = None):
    """Text adapter. Family editions can replace this without forking the webhook.

    One conversation per sender (history + conversation_id), Final Docs PDFs found in
    this turn ride along as WhatsApp documents, studio links are stripped, and a turn
    where every doc lookup failed gets an honest 'not found' reply."""
    from app.routers.max.router import ChatRequest, _chat_with_max_service

    number = normalize_msisdn(wa_id)
    conv = whatsapp_conversation(wa_id)
    response = await _chat_with_max_service(
        ChatRequest(
            message=text,
            channel="whatsapp",
            chat_id=number,
            conversation_id=conv["conversation_id"],
            history=conv.get("history") or [],
        ),
        canonical_channel="whatsapp",
        canonical_chat_id=number,
        canonical_founder=True,
    )
    reply = getattr(response, "response", None)
    tool_results = getattr(response, "tool_results", None)
    if isinstance(response, dict):
        reply = response.get("response") if reply is None else reply
        tool_results = response.get("tool_results") if tool_results is None else tool_results
    reply = str(reply or "No reply. Nothing sent.")
    docs, failed = _docs_from_tool_results(tool_results)
    if failed and not docs:
        honest = _no_doc_reply(failed)
        remember_whatsapp_turn(wa_id, text, honest)
        return honest
    if docs:
        return _finish_doc_reply(wa_id, text, reply, docs, fetch=fetch)
    clean = strip_studio_links(reply)
    remember_whatsapp_turn(wa_id, text, clean)
    return clean


_SEND_VERB = re.compile(
    r"\b(?:send|sent|attach|share|give|forward|pass|show|m[aá]nd\w*|env[ií]\w*|p[aá]sa\w*|mu[eé]str\w*|adjunt\w*|comparte\w*)\b",
    re.IGNORECASE,
)
_PDF_WORD = re.compile(r"\b(?:pdfs?|docs?|documents?|documentos?|files?|archivos?)\b", re.IGNORECASE)
_PRONOUN = re.compile(r"\b(?:it|them|those|these|that|this|eso|esos|esas|ese|esa|los|las|lo|la)\b", re.IGNORECASE)
_HERE = re.compile(r"\b(?:here|aqu[ií]|ac[aá]|in this chat|en este chat|on whatsapp|por whatsapp)\b", re.IGNORECASE)


async def whatsapp_doc_request(
    body: str,
    wa_id: str,
    *,
    hub_get: Optional[Callable[[str, dict], dict]] = None,
    fetch: Optional[Callable[[str], bytes]] = None,
):
    """'Show me Dahlia's last 2 docs here' / 'send me the pdf here' answered directly:
    resolve the Final Docs (aliases, addresses, last N) or reuse the documents shown last
    in this conversation, and attach the PDFs. None when the message is something else."""
    t = (body or "").strip()
    if not t or len(t) > 240 or t.endswith("?") and not _HERE.search(t):
        return None
    if not _SEND_VERB.search(t):
        return None
    wants_doc = bool(_PDF_WORD.search(t))
    if not wants_doc and not (_PRONOUN.search(t) and _HERE.search(t)):
        return None
    from app.services.max.doc_lookup import find_docs, parse_request

    req = parse_request(t)
    conv = whatsapp_conversation(wa_id)
    specific = bool(req["terms"] or req["quote_number"] or req["type"])
    if specific:
        try:
            found = await asyncio.to_thread(find_docs, t, hub_get=hub_get)
        except Exception:
            logger.warning("WhatsApp doc lookup failed", exc_info=True)
            return None
        if found.get("found") and (found.get("client") or found.get("type") or req["quote_number"]):
            docs = found["docs"]
            who = found.get("client") or "that"
            head = f"{who}: {len(docs)} latest final document(s), newest first:" if len(docs) > 1 else f"{who}:"
            return _finish_doc_reply(wa_id, t, f"{head}\n{_doc_lines(docs)}", docs, fetch=fetch)
        if not found.get("found") and (found.get("client") or req["terms"]):
            if found.get("client") is None and not _HERE.search(t):
                return None  # not clearly a doc request for here; let Max chat handle it
            honest = _no_doc_reply([{"error": f'No saved document matched "{t}"', "result": {"closest": found.get("closest") or []}}])
            remember_whatsapp_turn(wa_id, t, honest)
            return honest
        return None
    last = conv.get("last_docs") or []
    if not last:
        return None  # nothing shown yet in this conversation; Max will ask which one
    return _finish_doc_reply(
        wa_id, t, f"Here {'they are' if len(last) > 1 else 'it is'}:\n{_doc_lines(last)}", last, fetch=fetch,
    )


_DICTATION_DETAIL = re.compile(
    r"\d|\b(?:inch|inches|foot|feet|yard|yards|fabric|cushion|bench|pillow|drape|drapes|drapery|shade|shades|"
    r"valance|cornice|headboard|upholster\w*|foam|welt|tuft\w*|channel|piping|lining|pleat\w*|ripplefold|track|rod|"
    r"client|customer|address|deposit|quantity|qty|price|rate|color|colour)\b",
    re.IGNORECASE,
)
_SEND_IT = re.compile(r"^\W*(?:ok[, ]+)?(?:send it|send the quote|email it|email the quote)\W*$", re.IGNORECASE)


def _belongs_to_voice_draft(body: str, probe: Any, open_draft: bool) -> bool:
    """New-document dictation (or a follow-up to the open draft) vs. a normal message.

    2026-10-04: every WhatsApp voice note and, once a draft was open, every text (even "Hi")
    went into quote intake. Greetings, questions and requests about EXISTING quotes/jobs now
    go to Max chat; only dictation joins the draft.
    """
    from app.services.max.quick_replies import is_greeting, parse_quote_lookup

    t = body.strip()
    if is_greeting(t) or parse_quote_lookup(t):
        return False
    question = bool(re.match(
        r"^\W*(?:can|could|would|will|do|does|did|is|are|what|what's|whats|where|when|which|who|how|why|"
        r"show|tell|give|find|check|pull|open|list)\b", t, re.IGNORECASE)) or t.endswith("?")
    creating = bool(re.search(
        r"\b(?:new|make|create|start|draft|build|prepare|write up)\b[^.?!]{0,40}\b(?:quote|estimate|invoice|drawing)\b",
        t, re.IGNORECASE))
    if question and not creating:
        return False
    if open_draft:
        return bool(probe.done or _SEND_IT.match(t) or probe.document_intent or _DICTATION_DETAIL.search(t))
    return bool(probe.document_intent or probe.done)


async def _quick_whatsapp_reply(body: str):
    """Greeting / docs / existing-quote status, answered without the model. The quote PDF rides
    along in this chat with Rafael: a reply to the founder, not an outbound send."""
    from app.services.max.quick_replies import direct_reply

    hit = direct_reply(body, channel="whatsapp")
    if not hit:
        return None
    text = hit["text"]
    q = hit.get("quote") or None
    if q and hit.get("want_pdf"):
        try:
            from app.services.quote_pdf_service import generate_quote_pdf

            data = generate_quote_pdf(q.get("id"))
            if data:
                text = f"{text}\nPDF below (for you; nothing was sent to the client)."
                return {"text": text, "documents": [{
                    "filename": _pdf_filename(f"{q.get('quote_number') or 'quote'}.pdf"),
                    "data": data, "mime": "application/pdf", "kind": "quote",
                }]}
        except Exception:
            logger.warning("WhatsApp quote lookup PDF skipped", exc_info=True)
            text = f"{text}\nThe PDF could not be attached right now."
    return text


async def default_text_handler(text: str, wa_id: str) -> str:
    """Dictation joins the open voice draft. Everything else is Max chat."""
    body = (text or "").strip()
    if not body:
        return "Empty message. Nothing sent."
    try:
        quick = await _quick_whatsapp_reply(body)
        if quick:
            whatsapp_conversation(wa_id)
            q_text, _q_docs = _split_reply(quick)
            remember_whatsapp_turn(wa_id, body, q_text)
            return quick
    except Exception:
        logger.warning("WhatsApp quick reply failed", exc_info=True)
    try:
        doc_reply = await whatsapp_doc_request(body, wa_id)
        if doc_reply:
            return doc_reply
    except Exception:
        logger.warning("WhatsApp doc request failed", exc_info=True)
    try:
        from app.services.voice_documents.extract import extract_transcript
        from app.services.voice_documents.pipeline import ingest_transcript
        from app.services.voice_documents.session import active_session

        probe = extract_transcript(body)
        open_draft = active_session(_session_key(wa_id)) is not None
        if _belongs_to_voice_draft(body, probe, open_draft):
            result = ingest_transcript(
                body,
                channel="whatsapp",
                session_key=_session_key(wa_id),
                edition_id="workroom",
            )
            if result.get("handled"):
                return _outbound(result.get("reply_text") or "Draft updated. Not sent.", result)
    except Exception:
        logger.warning("WhatsApp text document route failed", exc_info=True)
    try:
        from app.services.max.whatsapp_log import photo_status_reply

        photo_reply = photo_status_reply(wa_id, body)
        if photo_reply:
            whatsapp_conversation(wa_id)
            remember_whatsapp_turn(wa_id, body, photo_reply)
            return photo_reply
    except Exception:
        logger.warning("WhatsApp photo-status reply failed", exc_info=True)
    try:
        return await max_chat(body, wa_id)
    except Exception:
        logger.warning("WhatsApp Max chat failed", exc_info=True)
        return "Max chat failed. Nothing sent."


async def default_voice_handler(audio: bytes, mime: str, wa_id: str) -> str:
    """Transcribe with the existing STT service and run the voice-to-document pipeline."""
    suffix = ".ogg" if "ogg" in (mime or "") else ".webm"
    path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(audio)
            path = handle.name
        # 2026-10-04: transcribe first, then route like a typed message (dictation -> draft,
        # everything else -> Max chat). The reply goes back as a voice note when the reply
        # mode follows the inbound message.
        from app.services.max.stt_service import stt_service

        transcript = (await stt_service.transcribe(path, language="en") or "").strip()
        if transcript:
            return await default_text_handler(transcript, wa_id)
        return "No transcript. Nothing sent."
    except Exception:
        logger.warning("WhatsApp voice note failed", exc_info=True)
        return "Voice note failed. Nothing sent."
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


async def default_photo_handler(image: bytes, mime: str, caption: str, wa_id: str) -> str:
    """Photo Analyzer, then a draft quote. Never emails."""
    import base64

    clean_mime = (mime or "image/jpeg").split(";")[0].strip() or "image/jpeg"
    data_uri = f"data:{clean_mime};base64,{base64.b64encode(image).decode()}"
    try:
        from app.services.quote_engine.item_analyzer import analyze_photo_items
        from app.services.quote_engine.photo_quote_lines import lines_from_analyzed_items
        from app.services.quote_engine.quote_assembler import assemble_quote
        from app.services.quote_service import create_quote

        analysis = await analyze_photo_items(data_uri, caption or "")
        items = [row for row in (analysis.get("items") or []) if isinstance(row, dict)]
        preview = None
        try:
            preview = assemble_quote(
                analyzed_items=items,
                customer_name="Photo",
                location="DC",
            )
        except Exception:
            logger.info("Photo Analyzer preview skipped; quote lines still use the photo rate card")
        lines = lines_from_analyzed_items(items, preview)
        if not lines:
            return "Photo analyzed. No items to price. Nothing sent."
        quote = create_quote({
            "customer_name": "Photo",
            "business_unit": "workroom",
            "project_name": "WhatsApp photo",
            "notes": "whatsapp photo draft — not sent",
            "line_items": lines,
            "ai_outlines": items,
        })
        number = quote.get("quote_number") or quote.get("id") or "draft"
        parts = [f"Photo draft {number}. Not sent."]
        for line in lines:
            amount = line.get("amount")
            try:
                shown = f"${float(amount):,.2f}"
            except (TypeError, ValueError):
                shown = ""
            parts.append(f"{line.get('description')}: {shown}".rstrip())
        return _outbound("\n".join(parts), {
            "handled": True,
            "quote_id": quote.get("id"),
            "quote_number": number,
        })
    except Exception:
        logger.warning("WhatsApp photo quote failed", exc_info=True)
        return "Photo analysis failed. Nothing sent."



_SENDER_LOCKS: dict[str, asyncio.Lock] = {}
_BATCH_FLUSH_TASKS: dict[str, asyncio.Task] = {}


def _sender_lock(sender: str) -> asyncio.Lock:
    """Per-sender lock so inbound WhatsApp messages are handled one at a time, in arrival order."""
    key = normalize_msisdn(sender) or str(sender or "")
    lock = _SENDER_LOCKS.get(key)
    if lock is None:
        lock = _SENDER_LOCKS[key] = asyncio.Lock()
    return lock


def _schedule_batch_flush(
    sender: str,
    *,
    http_post: Optional[Callable[..., Any]] = None,
    http_upload: Optional[Callable[..., Any]] = None,
) -> None:
    # In-memory debounce only. SQLite last_at/asked_at on whatsapp_media_batches
    # (see _load_batch) is the TTL that survives restart. Single-worker:
    # two processes would each schedule a flush and could double-ask.
    from app.services.max.whatsapp_log import finalize_photo_batch, photo_batch_window_seconds

    delay = photo_batch_window_seconds()
    key = normalize_msisdn(sender) or str(sender or "")
    prev = _BATCH_FLUSH_TASKS.pop(key, None)
    if prev and not prev.done():
        prev.cancel()
    if delay <= 0:
        return

    async def _run() -> None:
        try:
            await asyncio.sleep(delay)
            note = finalize_photo_batch(sender)
            reply = (note or {}).get("reply") or ""
            if reply:
                await reply_in_window(
                    sender,
                    reply,
                    http_post=http_post,
                    http_upload=http_upload,
                    inbound_type="image",
                )
        except asyncio.CancelledError:
            return
        except Exception:
            logger.warning("WhatsApp photo-batch flush failed", exc_info=True)
        finally:
            _BATCH_FLUSH_TASKS.pop(key, None)

    _BATCH_FLUSH_TASKS[key] = asyncio.create_task(_run())


async def process_webhook(
    raw_body: bytes,
    signature_header: str | None,
    *,
    text_handler: Optional[Callable[[str, str], Awaitable[str]]] = None,
    voice_handler: Optional[Callable[[bytes, str, str], Awaitable[str]]] = None,
    photo_handler: Optional[Callable[[bytes, str, str, str], Awaitable[str]]] = None,
    http_get: Optional[Callable[..., Any]] = None,
    http_post: Optional[Callable[..., Any]] = None,
    http_upload: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Verify, route, and reply inside the window. Does not send client drafts."""
    status = channel_status()
    if not status["enabled"]:
        return {**status, "accepted": False, "http_status": 503, "results": []}
    if not verify_signature(raw_body, signature_header):
        return {
            "accepted": False,
            "http_status": 403,
            "enabled": True,
            "reason": "signature rejected",
            "results": [],
        }
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "accepted": False,
            "http_status": 400,
            "enabled": True,
            "reason": "invalid json",
            "results": [],
        }
    parsed = payload if isinstance(payload, dict) else {}
    statuses_updated = _apply_status_updates(parsed)
    messages = parse_inbound(parsed)
    payload_texts: dict[str, list[str]] = {}
    for preview in messages:
        if (preview.get("type") == "text" or preview.get("text")) and preview.get("from"):
            body = str(preview.get("text") or "").strip()
            if body:
                payload_texts.setdefault(str(preview["from"]), []).append(body)
    batch_senders: set[str] = set()
    job_replied: set[str] = set()
    quoted_senders: set[str] = set()
    immediate_ack: set[str] = set()
    results: list[dict[str, Any]] = []
    on_text = text_handler or default_text_handler
    on_voice = voice_handler or default_voice_handler
    on_photo = photo_handler or default_photo_handler
    for message in messages:
        message_id = message["message_id"]
        # Dedup Meta redeliveries of the same wa message id before persist,
        # photo-batch aggregation, job-answer, or any handler.
        if message_id and _seen(message_id):
            results.append({
                "message_id": message_id,
                "type": message["type"],
                "duplicate": True,
                "sent": False,
            })
            continue
        sender = message["from"]
        if message_id:
            _mark_seen(message_id)
        if not is_allowlisted(sender):
            results.append({
                "message_id": message_id,
                "type": message["type"],
                "allowlisted": False,
                "ignored": True,
                "sent": False,
            })
            continue
        fields = _inbound_log_fields(message)
        from app.services.max.whatsapp_log import (
            combined_job_hint,
            consume_job_answer,
            finalize_photo_batch,
            is_job_hint_text,
            iso_from_wa_timestamp as _iso_wa,
            last_attachment_ids,
            mark_photo_batch_quoted,
            photo_batch_quoted,
            photo_batch_window_seconds,
            record_media_batch,
            set_pending_filings,
            wants_photo_quote,
        )
        from app.services.max.whatsapp_folders import (
            folder_allows_quote,
            resolve_folder,
            resolve_or_create_folder,
        )

        hint_bits = [
            message.get("caption") or "",
            message.get("text") or "",
            *[t for t in payload_texts.get(sender, []) if is_job_hint_text(t)],
        ]
        hint = combined_job_hint(sender, *hint_bits)

        # 2026-10-08 queueing: one sender's messages are answered in order.
        async with _sender_lock(sender):
            media_bytes, media_mime = b"", ""
            inbound_atts: list[dict[str, Any]] = []
            filed_reply = ""
            persist_failed = False
            try:
                if message.get("media_id"):
                    media_bytes, media_mime = await _safe_download(message["media_id"], http_get)
                inbound_atts = _persist_inbound_media(
                    message,
                    media_bytes,
                    media_mime or message.get("mime_type") or "",
                    hint_text=hint,
                )
                if message["type"] == "text":
                    answered = consume_job_answer(sender, message.get("text") or "")
                    if answered and answered.get("handled"):
                        filed_reply = answered.get("reply") or ""
                        job_replied.add(sender)
                msg_row_id = _log_chat(
                    wa_id=sender,
                    direction="inbound",
                    message_type=fields["message_type"],
                    body=fields["body"],
                    caption=fields["caption"],
                    wa_message_id=message_id,
                    delivery_status="received",
                    timestamp=_iso_wa(message.get("timestamp")),
                    metadata={
                        **fields["metadata"],
                        "filed": [
                            {
                                "filename": a.get("filename"),
                                "job_slug": a.get("job_slug"),
                                "folder_kind": a.get("folder_kind") or "",
                                "filed_path": a.get("filed_path"),
                                "filing_status": a.get("filing_status"),
                            }
                            for a in inbound_atts
                        ],
                    },
                    attachments=inbound_atts,
                )
                if msg_row_id:
                    saved = last_attachment_ids(msg_row_id)
                    fileable_ids = [
                        int(a["id"])
                        for a in saved
                        if a.get("media_type") in {"image", "photo", "document", "scan", "model"}
                    ]
                    inbox_ids = [int(a["id"]) for a in saved if a.get("filing_status") == "inbox"]
                    if inbox_ids:
                        set_pending_filings(sender, inbox_ids)
                    if fileable_ids:
                        record_media_batch(sender, fileable_ids, hint)
                        batch_senders.add(sender)
                        caption_only = str(message.get("caption") or "").strip()
                        if caption_only and resolve_or_create_folder(caption_only):
                            immediate_ack.add(sender)
            except Exception:
                persist_failed = True
                inbound_atts = []
                filed_reply = ""
                logger.warning(
                    "WhatsApp persist/file/job-answer failed; falling back to handler",
                    exc_info=True,
                )
            note_customer_window(sender, message.get("timestamp"))
            reply = ""
            route = message["type"]
            try:
                if filed_reply and not persist_failed:
                    route = "job_file"
                    reply = filed_reply
                elif message["type"] == "text":
                    album_mate = any(
                        other.get("type") == "image" and other.get("from") == sender
                        for other in messages
                    )
                    if album_mate:
                        route = "job_hint"
                        reply = ""
                    else:
                        route = "chat"
                        reply = await on_text(message["text"], sender)
                elif message["type"] == "audio" or message.get("voice"):
                    route = "voice_document"
                    audio, mime = media_bytes, media_mime
                    if not audio and message.get("media_id"):
                        audio, mime = await download_media(message["media_id"], http_get=http_get)
                    reply = await on_voice(audio, mime or message["mime_type"], sender)
                elif message["type"] == "image":
                    # File-only default. One draft only when THIS photo's
                    # caption (same message) asks to quote, and only once
                    # per open batch.
                    caption_asks = wants_photo_quote(message.get("caption") or "")
                    already_quoted = sender in quoted_senders or photo_batch_quoted(sender)
                    folder = resolve_folder(hint)
                    client_folder = folder_allows_quote((folder or {}).get("slug"))
                    if caption_asks and not already_quoted and client_folder:
                        route = "photo_quote"
                        image, mime = media_bytes, media_mime
                        if not image and message.get("media_id"):
                            image, mime = await download_media(message["media_id"], http_get=http_get)
                        reply = await on_photo(image, mime or message["mime_type"], message["caption"], sender)
                        quoted_senders.add(sender)
                        mark_photo_batch_quoted(sender)
                    else:
                        route = "file_photo"
                        reply = ""
                elif message["type"] == "document":
                    route = "file_document"
                    reply = ""
                elif message["type"] == "call":
                    route = "call"
                    reply = ""
                elif message["type"] == "ignored":
                    route = "ignored"
                    reply = ""
                else:
                    reply = "That message type is not handled. Nothing sent."
            except Exception:
                logger.warning("WhatsApp inbound handler failed", exc_info=True)
                reply = "That message failed. Nothing sent."
            reply_text, documents = _split_reply(reply)
            reply_sent = False
            reply_error = ""
            voice_sent = False
            voice_fallback = ""
            if reply_text or documents:
                try:
                    delivered = await reply_in_window(
                        sender,
                        reply_text,
                        http_post=http_post,
                        http_upload=http_upload,
                        inbound_type=message["type"],
                        inbound_voice=bool(message.get("voice")),
                        documents=documents,
                    )
                    reply_sent = True
                    voice_sent = bool(delivered.get("voice_sent"))
                    voice_fallback = delivered.get("voice_fallback") or ""
                except WhatsAppSendBlocked as exc:
                    reply_error = str(exc)
        results.append({
            "message_id": message_id,
            "type": message["type"],
            "route": route,
            "allowlisted": True,
            "sent": False,
            "reply_sent": reply_sent,
            "reply_error": reply_error,
            "voice_sent": voice_sent,
            "voice_fallback": voice_fallback,
        })
    for sender in batch_senders:
        key = normalize_msisdn(sender) or sender
        if sender in job_replied:
            prev = _BATCH_FLUSH_TASKS.pop(key, None)
            if prev and not prev.done():
                prev.cancel()
            continue
        if sender in immediate_ack or photo_batch_window_seconds() <= 0:
            note = finalize_photo_batch(sender)
            reply = (note or {}).get("reply") or ""
            if reply:
                try:
                    delivered = await reply_in_window(
                        sender,
                        reply,
                        http_post=http_post,
                        http_upload=http_upload,
                        inbound_type="image",
                    )
                    results.append({
                        "message_id": "",
                        "type": "image",
                        "route": "file_photo_batch",
                        "allowlisted": True,
                        "sent": False,
                        "reply_sent": True,
                        "reply_error": "",
                        "voice_sent": bool(delivered.get("voice_sent")),
                        "voice_fallback": delivered.get("voice_fallback") or "",
                    })
                except WhatsAppSendBlocked as exc:
                    results.append({
                        "message_id": "",
                        "type": "image",
                        "route": "file_photo_batch",
                        "allowlisted": True,
                        "sent": False,
                        "reply_sent": False,
                        "reply_error": str(exc),
                        "voice_sent": False,
                        "voice_fallback": "",
                    })
        else:
            _schedule_batch_flush(sender, http_post=http_post, http_upload=http_upload)
    # Check for calls field events (connect, terminate, status)
    calls = parse_inbound_calls(payload if isinstance(payload, dict) else {})
    if calls:
        try:
            from app.services.max.whatsapp_calling import (
                handle_call_terminate,
                schedule_call_connect,
            )
        except ImportError:
            logging.getLogger("max.whatsapp_calling").warning(
                "whatsapp_calling unavailable; reject-only fallback for %s call event(s)",
                len(calls),
            )

            async def schedule_call_connect(c_id, c_from, sdp, http_post=None):  # type: ignore[misc]
                if not is_allowlisted(c_from):
                    return {"action": "rejected", "call_id": c_id, "reason": "not_allowlisted"}
                if not channel_status().get("calling_enabled"):
                    return {"action": "rejected", "call_id": c_id, "reason": "calling_disabled"}
                return {"action": "noted", "call_id": c_id, "reason": "calling_unavailable"}

            async def handle_call_terminate(c_id, reason="webhook_terminate"):  # type: ignore[misc]
                return {"action": "noted", "call_id": c_id, "reason": reason}
        for call_item in calls:
            c_id = call_item["call_id"]
            c_from = call_item["from"]
            c_event = call_item["event"]
            c_res: dict[str, Any] = {
                "call_id": c_id,
                "type": "call",
                "event": c_event,
                "from": c_from,
            }
            logging.getLogger("max.whatsapp_calling").info(
                "whatsapp_call[%s] webhook event=%s from=%s sdp=%s",
                c_id, c_event, c_from, "yes" if call_item["sdp"] else "no",
            )
            if c_event == "connect":
                # Allowlisted calls are set up in the background so Meta gets
                # its 200 immediately (WHATSAPP_CALL_SETUP_INLINE=1 awaits).
                res = await schedule_call_connect(
                    c_id,
                    c_from,
                    call_item["sdp"],
                    http_post=http_post,
                )
                c_res.update(res)
            elif c_event == "terminate":
                res = await handle_call_terminate(c_id, reason="webhook_terminate")
                c_res.update(res)
            else:
                # status or other call event (e.g., ringing)
                c_res["action"] = "noted"
            results.append(c_res)

    return {
        "accepted": True,
        "http_status": 200,
        "enabled": True,
        "status": "enabled",
        "sent": False,
        "statuses_updated": statuses_updated,
        "results": results,
    }
