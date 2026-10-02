"""WhatsApp Business Cloud API for one Empire instance.

Each process reads its own env. Max-e, Maxine, and Workroom Max do not share
a number or a token. This module never reads a Gmail token or another
instance's config.

Portable files are listed in docs/WHATSAPP_CHANNEL.md.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path

GRAPH = "https://graph.facebook.com/v21.0"
WINDOW_SECONDS = 24 * 60 * 60
REQUIRED_ENV = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
)
_SEND = re.compile(
    r"\b(enviar|envia|envía|envíalo|envialo|manda el pdf|manda el borrador|send the draft|send pdf)\b",
    re.I,
)


class WhatsAppError(Exception):
    pass


def edition_label() -> str:
    try:
        from app.edition import edition_name

        return edition_name() or "workroom"
    except Exception:
        return (os.getenv("EMPIRE_EDITION") or "workroom").strip().lower() or "workroom"


def _present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def owner_numbers() -> list[str]:
    raw = os.getenv("WHATSAPP_OWNER_NUMBERS", "")
    found = []
    for part in raw.split(","):
        number = _digits(part)
        if number and number not in found:
            found.append(number)
    return found


def approved_templates() -> list[str]:
    raw = os.getenv("WHATSAPP_APPROVED_TEMPLATES", "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def reply_mode() -> str:
    mode = os.getenv("WHATSAPP_REPLY_MODE", "voice_text").strip().lower()
    if mode in {"voice_text", "text", "match"}:
        return mode
    return "voice_text"


def reply_language() -> str:
    """Max-e and Maxine speak es-CO. Workroom stays English unless configured."""
    try:
        from app.edition import default_locale, is_family_edition

        if is_family_edition():
            return "es-CO"
        locale = default_locale()
    except Exception:
        locale = os.getenv("EMPIRE_DEFAULT_LOCALE", "en")
    code = (locale or "en").lower()
    if code.startswith("es"):
        return "es-CO"
    if code.startswith("en"):
        return "en"
    return code


def missing_config() -> list[str]:
    return [name for name in REQUIRED_ENV if not _present(name)]


def configured() -> bool:
    return not missing_config()


def channel_status() -> dict:
    missing = missing_config()
    owners = owner_numbers()
    enabled = not missing and bool(owners)
    if missing and len(missing) == len(REQUIRED_ENV):
        code = "disabled"
    elif missing or not owners:
        code = "partial_disabled_gateway" if missing else "closed"
    else:
        code = "ready"
    if missing:
        names = ", ".join(missing)
        reason_es = f"WhatsApp está apagado. Faltan: {names}."
        reason_en = f"WhatsApp is off. Missing: {names}."
    elif not owners:
        reason_es = "La API está configurada, pero no hay números del dueño en WHATSAPP_OWNER_NUMBERS. No acepto mensajes."
        reason_en = "The API is configured, but WHATSAPP_OWNER_NUMBERS is empty. Inbound messages are refused."
    else:
        reason_es = "WhatsApp responde solo a los números del dueño, dentro de las 24 horas. El PDF sale después de confirmar en el chat."
        reason_en = "WhatsApp replies only to the owner's numbers, inside 24 hours. The PDF is sent after a chat confirmation."
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    return {
        "enabled": enabled,
        "configured": not missing,
        "status": code,
        "edition": edition_label(),
        "phone_number_id_set": bool(phone_id),
        "phone_number_id_last4": phone_id[-4:] if len(phone_id) >= 4 else "",
        "owner_count": len(owners),
        "owner_last4": [number[-4:] for number in owners],
        "approved_templates": approved_templates(),
        "service_window_hours": 24,
        "webhook_path": "/api/v1/whatsapp/webhook",
        "documents_auto_send": False,
        "reply_mode": reply_mode(),
        "reply_language": reply_language(),
        "reason_es": reason_es,
        "reason_en": reason_en,
        "reason": reason_es,
    }


def verify_signature(body: bytes, header: str) -> bool:
    secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if not secret or not header:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = "sha256=" + digest
    return hmac.compare_digest(expected, header.strip())


def verify_handshake(mode: str, token: str, challenge: str) -> str | None:
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
    if not expected or mode != "subscribe" or not challenge:
        return None
    if not hmac.compare_digest(expected, token or ""):
        return None
    return challenge


def _state_path() -> str:
    explicit = os.getenv("WHATSAPP_STATE_DB", "").strip()
    if explicit:
        return os.path.expanduser(explicit)
    try:
        from app.edition import data_root_or_none

        root = data_root_or_none()
    except Exception:
        root = None
    if root is None:
        root = Path(os.path.expanduser("~/empire-data"))
    root.mkdir(parents=True, exist_ok=True)
    return str(root / "whatsapp.db")


def _db():
    path = _state_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS wa_contacts (
            wa_id TEXT PRIMARY KEY,
            last_inbound INTEGER
        );
        CREATE TABLE IF NOT EXISTS wa_seen (
            message_id TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS wa_deliveries (
            id TEXT PRIMARY KEY,
            draft_id TEXT,
            wa_id TEXT,
            kind TEXT,
            created_at INTEGER
        );
        """
    )
    return conn


def remember_inbound(wa_id: str, timestamp: int) -> None:
    conn = _db()
    try:
        conn.execute(
            """
            INSERT INTO wa_contacts (wa_id, last_inbound) VALUES (?, ?)
            ON CONFLICT(wa_id) DO UPDATE SET last_inbound = excluded.last_inbound
            """,
            (wa_id, int(timestamp)),
        )
        conn.commit()
    finally:
        conn.close()


def within_service_window(wa_id: str, now: int | None = None) -> bool:
    conn = _db()
    try:
        row = conn.execute("SELECT last_inbound FROM wa_contacts WHERE wa_id = ?", (wa_id,)).fetchone()
    finally:
        conn.close()
    if not row or row["last_inbound"] is None:
        return False
    moment = int(now if now is not None else time.time())
    return moment - int(row["last_inbound"]) <= WINDOW_SECONDS


def _already_seen(message_id: str) -> bool:
    conn = _db()
    try:
        row = conn.execute("SELECT message_id FROM wa_seen WHERE message_id = ?", (message_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def _mark_seen(message_id: str) -> None:
    conn = _db()
    try:
        conn.execute("INSERT OR IGNORE INTO wa_seen (message_id) VALUES (?)", (message_id,))
        conn.commit()
    finally:
        conn.close()


def graph_request(method: str, url: str, *, token: str = "", body: bytes | None = None, headers: dict | None = None) -> tuple[int, bytes]:
    """The only Meta call. Uses the token argument for this instance."""
    import urllib.error
    import urllib.request

    if not url.startswith("https://"):
        raise WhatsAppError("Solo llamo a Meta por https")
    hdrs = dict(headers or {})
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        raise WhatsAppError(f"Meta respondió {exc.code}") from None
    except urllib.error.URLError:
        raise WhatsAppError("No hay red hacia Meta") from None


def _graph_json(method: str, url: str, payload: dict | None, token: str) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    _status, raw = graph_request(method, url, token=token, body=body, headers=headers)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        raise WhatsAppError("Meta no devolvió JSON") from None
    if not isinstance(parsed, dict):
        raise WhatsAppError("Meta no devolvió JSON")
    return parsed


def _token() -> str:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    if not token:
        raise WhatsAppError("WhatsApp está apagado")
    return token


def _phone_id() -> str:
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    if not phone_id:
        raise WhatsAppError("Falta WHATSAPP_PHONE_NUMBER_ID")
    return phone_id


def send_session_text(wa_id: str, text: str, *, now: int | None = None) -> dict:
    number = _digits(wa_id)
    if number not in owner_numbers():
        return {"sent": False, "reason": "Ese número no está en la lista del dueño."}
    if not within_service_window(number, now):
        return {"sent": False, "reason": "Fuera de la ventana de 24 horas. Solo una plantilla aprobada puede salir."}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "text",
        "text": {"body": text[:4000]},
    }
    url = f"{GRAPH}/{_phone_id()}/messages"
    result = _graph_json("POST", url, payload, _token())
    return {"sent": True, "id": ((result.get("messages") or [{}])[0].get("id")), "kind": "text"}


def summarize_reply(text: str, limit: int = 240) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    cut = compact[:limit]
    pause = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if pause >= 80:
        return cut[: pause + 1]
    space = cut.rfind(" ")
    if space > 40:
        return cut[:space] + "…"
    return cut + "…"


def _voice_failed_note(language: str) -> str:
    if (language or "").lower().startswith("es"):
        return "No pude generar la nota de voz. Sigue el texto."
    return "I could not make the voice note. The text follows."


def _wants_voice(mode: str, inbound_kind: str) -> bool:
    if mode == "voice_text":
        return True
    if mode == "match" and inbound_kind in {"audio", "voice"}:
        return True
    return False


def _as_ogg_opus(data: bytes) -> bytes | None:
    if data.startswith(b"OggS") and len(data) >= 64:
        return data
    import shutil
    import subprocess
    import tempfile

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not data:
        return None
    src = Path(tempfile.mktemp(suffix=".audio"))
    dest = Path(tempfile.mktemp(suffix=".ogg"))
    try:
        src.write_bytes(data)
        done = subprocess.run(
            [ffmpeg, "-y", "-i", str(src), "-c:a", "libopus", "-f", "ogg", str(dest)],
            capture_output=True,
            timeout=30,
        )
        if done.returncode != 0 or not dest.is_file():
            return None
        encoded = dest.read_bytes()
        if encoded.startswith(b"OggS"):
            return encoded
        return None
    except Exception:
        return None
    finally:
        src.unlink(missing_ok=True)
        dest.unlink(missing_ok=True)


def _default_synthesize(text: str, language: str) -> bytes | None:
    try:
        import asyncio

        from app.services.max.tts_service import tts_service
    except Exception:
        return None

    async def _go() -> bytes | None:
        path = await tts_service.synthesize(text, output_format="opus", language=language)
        if path is None:
            return None
        try:
            return Path(path).read_bytes()
        finally:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

    try:
        raw = asyncio.run(_go())
    except RuntimeError:
        return None
    except Exception:
        return None
    if not raw:
        return None
    return _as_ogg_opus(raw)


def _upload_audio(data: bytes) -> str:
    token = _token()
    boundary = "wa" + uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"messaging_product\"\r\n\r\nwhatsapp\r\n".encode("utf-8"),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"nota.ogg\"\r\n"
            "Content-Type: audio/ogg; codecs=opus\r\n\r\n"
        ).encode("utf-8"),
        data,
        f"\r\n--{boundary}--".encode("utf-8"),
    ])
    _status, raw = graph_request(
        "POST",
        f"{GRAPH}/{_phone_id()}/media",
        token=token,
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        raise WhatsAppError("Meta no recibió la nota de voz") from None
    media_id = parsed.get("id") if isinstance(parsed, dict) else None
    if not media_id:
        raise WhatsAppError("Meta no recibió la nota de voz")
    return media_id


def _send_audio(number: str, media_id: str) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "audio",
        "audio": {"id": media_id, "voice": True},
    }
    result = _graph_json("POST", f"{GRAPH}/{_phone_id()}/messages", payload, _token())
    return {"sent": True, "id": ((result.get("messages") or [{}])[0].get("id")), "kind": "audio"}


def send_reply(wa_id: str, text: str, *, now: int | None = None, inbound_kind: str = "text", synthesize=None) -> dict:
    """Voice note plus a short text copy, unless this instance asks for text only."""
    language = reply_language()
    mode = reply_mode()
    number = _digits(wa_id)
    if number not in owner_numbers():
        return {"sent": False, "voice": False, "fallback": False, "mode": mode, "language": language, "reason": "Ese número no está en la lista del dueño."}
    if not within_service_window(number, now):
        return {"sent": False, "voice": False, "fallback": False, "mode": mode, "language": language, "reason": "Fuera de la ventana de 24 horas. Solo una plantilla aprobada puede salir."}
    use_voice = _wants_voice(mode, inbound_kind)
    voice_sent = False
    if use_voice:
        maker = synthesize or _default_synthesize
        try:
            audio = maker(text, language)
        except Exception:
            audio = None
        if audio:
            audio = _as_ogg_opus(audio)
        if audio:
            try:
                media_id = _upload_audio(audio)
                _send_audio(_digits(wa_id), media_id)
                voice_sent = True
            except WhatsAppError:
                voice_sent = False
    if voice_sent:
        body = summarize_reply(text)
    elif use_voice:
        body = _voice_failed_note(language) + "\n\n" + text
    else:
        body = text
    delivered = send_session_text(wa_id, body, now=now)
    return {
        "sent": bool(delivered.get("sent")),
        "voice": voice_sent,
        "fallback": bool(use_voice and not voice_sent),
        "mode": mode,
        "language": language,
        "kind": "voice_text" if voice_sent else "text",
        "reason": delivered.get("reason"),
    }


def send_template(wa_id: str, template_name: str, *, language: str = "es") -> dict:
    number = _digits(wa_id)
    if number not in owner_numbers():
        return {"sent": False, "reason": "Ese número no está en la lista del dueño."}
    if template_name not in approved_templates():
        return {"sent": False, "reason": "Esa plantilla no está en WHATSAPP_APPROVED_TEMPLATES."}
    payload = {
        "messaging_product": "whatsapp",
        "to": number,
        "type": "template",
        "template": {"name": template_name, "language": {"code": language}},
    }
    result = _graph_json("POST", f"{GRAPH}/{_phone_id()}/messages", payload, _token())
    return {"sent": True, "id": ((result.get("messages") or [{}])[0].get("id")), "kind": "template"}


def _upload_pdf(data: bytes, filename: str) -> str:
    token = _token()
    boundary = "wa" + uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"messaging_product\"\r\n\r\nwhatsapp\r\n".encode("utf-8"),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8"),
        data,
        f"\r\n--{boundary}--".encode("utf-8"),
    ])
    _status, raw = graph_request(
        "POST",
        f"{GRAPH}/{_phone_id()}/media",
        token=token,
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        raise WhatsAppError("Meta no recibió el PDF") from None
    media_id = parsed.get("id") if isinstance(parsed, dict) else None
    if not media_id:
        raise WhatsAppError("Meta no recibió el PDF")
    return media_id


def send_draft_document(wa_id: str, draft: dict, *, now: int | None = None) -> dict:
    """Send the draft PDF only when the caller already recorded a chat confirmation."""
    number = _digits(wa_id)
    if number not in owner_numbers():
        return {"sent": False, "document": False, "reason": "Ese número no está en la lista del dueño."}
    if not within_service_window(number, now):
        return {"sent": False, "document": False, "reason": "Fuera de la ventana de 24 horas."}
    from app.services.voice_doc.store import render_draft_pdf

    payload = draft.get("payload") or {}
    pdf = render_draft_pdf(payload, [payload.get("transcript") or ""])
    filename = f"{draft.get('id') or 'borrador'}.pdf"
    media_id = _upload_pdf(pdf, filename)
    message = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "document",
        "document": {"id": media_id, "filename": filename, "caption": "BORRADOR"},
    }
    result = _graph_json("POST", f"{GRAPH}/{_phone_id()}/messages", message, _token())
    conn = _db()
    try:
        conn.execute(
            "INSERT INTO wa_deliveries (id, draft_id, wa_id, kind, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), draft.get("id"), number, "document", int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "sent": True,
        "document": True,
        "id": ((result.get("messages") or [{}])[0].get("id")),
        "emailed": False,
    }


def _download_media(media_id: str) -> bytes:
    meta = _graph_json("GET", f"{GRAPH}/{media_id}", None, _token())
    url = meta.get("url") or ""
    if not url.startswith("https://"):
        raise WhatsAppError("Meta no entregó la dirección del archivo")
    _status, raw = graph_request("GET", url, token=_token())
    return raw


def _photo_tags(caption: str) -> tuple[str, str, str]:
    text = caption or ""
    project = "whatsapp"
    lot = ""
    stage = ""
    found_project = re.search(r"proyecto\s+(.+?)(?=\s+lote\b|\s+etapa\b|$)", text, re.I)
    found_lot = re.search(r"lote\s+([A-Za-z0-9_-]+)", text, re.I)
    found_stage = re.search(r"etapa\s+([^,\n]+)", text, re.I)
    if found_project:
        project = found_project.group(1).strip()
    if found_lot:
        lot = found_lot.group(1).strip()
    if found_stage:
        stage = found_stage.group(1).strip()
    return project, lot, stage


def _default_transcribe(path: Path) -> str:
    from app.services.max.stt_service import stt_service

    return stt_service.transcribe_sync(path, language=None)


def _reply_pipeline(wa_id: str, transcript: str, *, now: int, inbound_kind: str = "text", synthesize=None) -> dict:
    from app.services.voice_doc import format_session_reply, ingest_transcript
    from app.services.voice_doc.extract import choice_from_text
    from app.services.voice_doc.store import latest_draft_for_channel

    if _SEND.search(transcript or ""):
        draft = latest_draft_for_channel("whatsapp")
        if not draft:
            text = "No hay un borrador para enviar. Dicta el documento y di listo."
            send_reply(wa_id, text, now=now, inbound_kind=inbound_kind, synthesize=synthesize)
            return {"handled": True, "document": False, "reply": text}
        delivered = send_draft_document(wa_id, draft, now=now)
        text = "Envié el PDF por este chat. No se envió correo. Sigue marcado BORRADOR."
        if not delivered.get("sent"):
            text = delivered.get("reason") or "No envié el PDF."
        send_reply(wa_id, text, now=now, inbound_kind=inbound_kind, synthesize=synthesize)
        return {"handled": True, "document": bool(delivered.get("document")), "reply": text, "draft_id": draft.get("id")}
    view = ingest_transcript(transcript, channel="whatsapp", edition=edition_label(), choice_id=choice_from_text(transcript))
    reply = format_session_reply(view)
    send_reply(wa_id, reply, now=now, inbound_kind=inbound_kind, synthesize=synthesize)
    return {"handled": True, "document": False, "reply": reply, "draft_id": (view.get("draft") or {}).get("id")}


def handle_webhook(body: bytes, signature: str, *, transcribe=None, synthesize=None) -> dict:
    if not configured():
        return {"ok": False, "http_status": 503, "status": channel_status()["status"], "processed": 0}
    if not verify_signature(body, signature):
        return {"ok": False, "http_status": 403, "processed": 0, "reason": "Firma inválida"}
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "http_status": 400, "processed": 0}
    expected_phone = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    processed = 0
    ignored = 0
    last: dict = {}
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            phone_id = ((value.get("metadata") or {}).get("phone_number_id") or "").strip()
            if phone_id and phone_id != expected_phone:
                ignored += 1
                continue
            for message in value.get("messages") or []:
                message_id = str(message.get("id") or "")
                if message_id and _already_seen(message_id):
                    continue
                sender = _digits(str(message.get("from") or ""))
                timestamp = int(message.get("timestamp") or time.time())
                if sender not in owner_numbers():
                    ignored += 1
                    continue
                remember_inbound(sender, timestamp)
                kind = message.get("type")
                if kind == "text":
                    last = _reply_pipeline(sender, ((message.get("text") or {}).get("body") or ""), now=timestamp, inbound_kind="text", synthesize=synthesize)
                    processed += 1
                elif kind in {"audio", "voice"}:
                    media = message.get("audio") or message.get("voice") or {}
                    raw = _download_media(str(media.get("id") or ""))
                    folder = Path(_state_path()).parent / "wa-media"
                    folder.mkdir(parents=True, exist_ok=True)
                    path = folder / f"{uuid.uuid4().hex}.ogg"
                    path.write_bytes(raw)
                    try:
                        reader = transcribe or _default_transcribe
                        transcript = reader(path)
                    finally:
                        path.unlink(missing_ok=True)
                    if not transcript or str(transcript).startswith("["):
                        send_reply(sender, "No pude transcribir la nota.", now=timestamp, inbound_kind=kind, synthesize=synthesize)
                        last = {"handled": False, "document": False}
                    else:
                        last = _reply_pipeline(sender, str(transcript), now=timestamp, inbound_kind=kind, synthesize=synthesize)
                    processed += 1
                elif kind == "image":
                    media = message.get("image") or {}
                    raw = _download_media(str(media.get("id") or ""))
                    project, lot, stage = _photo_tags(media.get("caption") or "")
                    from app.services.instance_files import save_photo

                    save_photo(
                        data=raw,
                        filename="whatsapp.jpg",
                        project=project,
                        lot=lot,
                        stage=stage,
                        source="whatsapp",
                    )
                    send_reply(sender, f"Foto guardada en {project}. Lote {lot or '—'} · etapa {stage or '—'}.", now=timestamp, inbound_kind="image", synthesize=synthesize)
                    processed += 1
                else:
                    send_reply(sender, "Puedo leer texto, notas de voz y fotos.", now=timestamp, inbound_kind=kind or "text", synthesize=synthesize)
                    processed += 1
                if message_id:
                    _mark_seen(message_id)
    return {
        "ok": True,
        "http_status": 200,
        "processed": processed,
        "ignored": ignored,
        "edition": edition_label(),
        "document": bool(last.get("document")),
        "draft_id": last.get("draft_id"),
    }
