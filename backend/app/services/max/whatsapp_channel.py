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
    customer_window_open, reply_in_window, send_template, process_webhook
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
    }


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
        if isinstance(extra, list):
            raw.extend(str(item) for item in extra if str(item).strip())
    return frozenset(n for n in (normalize_msisdn(item) for item in raw) if n)


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
                found.append(item)
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


async def reply_in_window(
    to: str,
    text: str,
    *,
    http_post: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Session reply to an allowlisted founder number inside the 24h window.

    This is the channel acknowledgement, not delivery of a client draft.
    """
    _require_enabled()
    if not is_allowlisted(to):
        raise WhatsAppSendBlocked("recipient is not on the founder allowlist")
    if not customer_window_open(to):
        raise WhatsAppSendBlocked(
            "outside the 24 hour window; an approved template and explicit confirm are required"
        )
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalize_msisdn(to),
        "type": "text",
        "text": {"preview_url": False, "body": (text or "")[:4096]},
    }
    result = await _post_graph(body, http_post=http_post)
    return {"sent": True, "kind": "session", "draft_sent": False, "graph": _public_graph(result)}


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
                return result.get("reply_text") or "Draft updated. Not sent."
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
            return result.get("reply_text") or "Draft updated. Not sent."
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
        return "\n".join(parts)
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
    messages = parse_inbound(payload if isinstance(payload, dict) else {})
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
        note_customer_window(sender, message.get("timestamp"))
        reply = ""
        route = message["type"]
        try:
            if message["type"] == "text":
                route = "chat"
                reply = await on_text(message["text"], sender)
            elif message["type"] == "audio" or message.get("voice"):
                route = "voice_document"
                audio, mime = await download_media(message["media_id"], http_get=http_get)
                reply = await on_voice(audio, mime or message["mime_type"], sender)
            elif message["type"] == "image":
                route = "photo_quote"
                image, mime = await download_media(message["media_id"], http_get=http_get)
                reply = await on_photo(image, mime or message["mime_type"], message["caption"], sender)
            else:
                reply = "That message type is not handled. Nothing sent."
        except Exception:
            logger.warning("WhatsApp inbound handler failed", exc_info=True)
            reply = "That message failed. Nothing sent."
        reply_sent = False
        reply_error = ""
        if reply:
            try:
                await reply_in_window(sender, reply, http_post=http_post)
                reply_sent = True
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
        })
    return {
        "accepted": True,
        "http_status": 200,
        "enabled": True,
        "status": "enabled",
        "sent": False,
        "results": results,
    }
