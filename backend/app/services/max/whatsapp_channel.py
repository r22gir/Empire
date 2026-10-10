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

import hashlib
import hmac
import json
import logging
import os
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
        _save_state({"windows": {}, "seen": []})


def _parse_stamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        stamp = value
    else:
        text = str(value or "").strip()
        if text.isdigit():
            stamp = datetime.fromtimestamp(int(text), tz=timezone.utc)
        else:
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
                kind = str(message.get("type") or "")
                item: dict[str, Any] = {
                    "message_id": str(message.get("id") or ""),
                    "from": str(message.get("from") or ""),
                    "timestamp": message.get("timestamp"),
                    "type": kind,
                    "text": "",
                    "media_id": "",
                    "mime_type": "",
                    "caption": "",
                    "voice": False,
                    "filename": "",
                }
                if kind == "text":
                    item["text"] = str((message.get("text") or {}).get("body") or "")
                elif kind in {"audio", "image", "video", "document", "sticker"}:
                    media = message.get(kind) or {}
                    if isinstance(media, dict):
                        item["media_id"] = str(media.get("id") or "")
                        item["mime_type"] = str(media.get("mime_type") or "")
                        item["caption"] = str(media.get("caption") or "")
                        item["voice"] = bool(media.get("voice"))
                        item["filename"] = str(media.get("filename") or "")
                elif kind == "location":
                    loc = message.get("location") or {}
                    if isinstance(loc, dict):
                        lat = loc.get("latitude")
                        lon = loc.get("longitude")
                        name = loc.get("name") or loc.get("address") or ""
                        item["text"] = f"Location: {lat}, {lon} ({name})".strip()
                        item["location"] = loc
                elif kind in {"system", "button", "interactive"}:
                    item["text"] = str(
                        (message.get("system") or {}).get("body")
                        or (message.get("button") or {}).get("text")
                        or kind
                    )
                found.append(item)
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
) -> list[dict[str, Any]]:
    """Save inbound bytes and file photos/docs when the job is known."""
    from app.services.max.whatsapp_log import prepare_inbound_attachment

    kind = str(message.get("type") or "document")
    media_type = "voice" if (message.get("voice") or kind == "audio") else kind
    if kind == "image":
        media_type = "image"
    hint = str(message.get("caption") or message.get("text") or "")
    fileable = media_type in {"image", "document"}
    if not content and kind != "location":
        return []
    payload = content
    filename = _default_media_name(message)
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
                    "caption": "Draft. Not sent.",
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


async def max_chat(text: str, wa_id: str) -> str:
    """Text adapter. Family editions can replace this without forking the webhook."""
    from app.routers.max.router import ChatRequest, _chat_with_max_service

    response = await _chat_with_max_service(
        ChatRequest(message=text, channel="whatsapp", chat_id=normalize_msisdn(wa_id)),
        canonical_channel="whatsapp",
        canonical_chat_id=normalize_msisdn(wa_id),
        canonical_founder=True,
    )
    reply = getattr(response, "response", None)
    if reply is None and isinstance(response, dict):
        reply = response.get("response")
    return str(reply or "No reply. Nothing sent.")


async def default_text_handler(text: str, wa_id: str) -> str:
    """Quote-shaped text joins the open voice draft. Everything else is Max chat."""
    body = (text or "").strip()
    if not body:
        return "Empty message. Nothing sent."
    try:
        from app.services.voice_documents.extract import extract_transcript
        from app.services.voice_documents.pipeline import ingest_transcript
        from app.services.voice_documents.session import active_session

        probe = extract_transcript(body)
        open_draft = active_session(_session_key(wa_id)) is not None
        if probe.document_intent or probe.done or probe.send_requested or open_draft:
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
        from app.services.voice_documents.pipeline import ingest_audio

        result = await ingest_audio(
            path,
            channel="whatsapp",
            session_key=_session_key(wa_id),
            edition_id="workroom",
        )
        if result.get("handled"):
            return _outbound(result.get("reply_text") or "Draft updated. Not sent.", result)
        transcript = (result.get("transcript") or result.get("transcript_raw") or "").strip()
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
    results: list[dict[str, Any]] = []
    on_text = text_handler or default_text_handler
    on_voice = voice_handler or default_voice_handler
    on_photo = photo_handler or default_photo_handler
    for message in messages:
        message_id = message["message_id"]
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
            JOB_ASK_TEXT,
            consume_job_answer,
            iso_from_wa_timestamp as _iso_wa,
            last_attachment_ids,
            set_pending_filings,
        )

        media_bytes, media_mime = b"", ""
        if message.get("media_id"):
            media_bytes, media_mime = await _safe_download(message["media_id"], http_get)
        inbound_atts = _persist_inbound_media(message, media_bytes, media_mime or message.get("mime_type") or "")

        filed_reply = ""
        if message["type"] == "text":
            answered = consume_job_answer(sender, message.get("text") or "")
            if answered and answered.get("handled"):
                filed_reply = answered.get("reply") or ""

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
                    {"filename": a.get("filename"), "job_slug": a.get("job_slug"), "filed_path": a.get("filed_path"), "filing_status": a.get("filing_status")}
                    for a in inbound_atts
                ],
            },
            attachments=inbound_atts,
        )
        if msg_row_id:
            saved = last_attachment_ids(msg_row_id)
            inbox_ids = [int(a["id"]) for a in saved if a.get("filing_status") == "inbox"]
            if inbox_ids:
                set_pending_filings(sender, inbox_ids)
        note_customer_window(sender, message.get("timestamp"))
        reply = ""
        route = message["type"]
        try:
            if filed_reply:
                route = "job_file"
                reply = filed_reply
            elif message["type"] == "text":
                route = "chat"
                reply = await on_text(message["text"], sender)
            elif message["type"] == "audio" or message.get("voice"):
                route = "voice_document"
                reply = await on_voice(media_bytes, media_mime or message["mime_type"], sender)
            elif message["type"] == "image":
                route = "photo_quote"
                reply = await on_photo(media_bytes, media_mime or message["mime_type"], message["caption"], sender)
            else:
                reply = "That message type is not handled. Nothing sent."
        except Exception:
            logger.warning("WhatsApp inbound handler failed", exc_info=True)
            reply = "That message failed. Nothing sent."
        reply_text, documents = _split_reply(reply)
        if any(a.get("needs_job_ask") or a.get("filing_status") == "inbox" for a in inbound_atts):
            if JOB_ASK_TEXT not in (reply_text or ""):
                reply_text = f"{reply_text}\n{JOB_ASK_TEXT}".strip() if reply_text else JOB_ASK_TEXT
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
    return {
        "accepted": True,
        "http_status": 200,
        "enabled": True,
        "status": "enabled",
        "sent": False,
        "statuses_updated": statuses_updated,
        "results": results,
    }
