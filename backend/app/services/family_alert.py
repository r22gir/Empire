"""Rafael-only family-help alerts: WhatsApp, else SMS.

Fired from the edition that creates the ticket (Max-e / Maxine), next to
``notify_new_ticket``. Off unless ``FAMILY_ALERT_ENABLED=true``. Destination
is Rafael's number from env only — never clients, never Juan, never Camilo.

Graceful no-op when the flag is off or credentials are missing. Tests must
never reach a live WhatsApp / SMS / SMTP host (see tests/_outbound_send_guard.py).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger("empire.family_alert")

DEFAULT_STUDIO_URL = "https://studio.empirebox.store"
ASSIST_PATH = "/?screen=family-help"
TYPE_EN = {"Ajuste": "adjust", "Arreglo": "fix", "Crear": "create"}
TYPE_ES = {"Ajuste": "ajuste", "Arreglo": "arreglo", "Crear": "crear"}
WHO = {
    "amp": ("Juan", "Max-e"),
    "maxine": ("Camilo", "Maxine"),
}


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def alerts_enabled() -> bool:
    return (os.getenv("FAMILY_ALERT_ENABLED") or "").strip().lower() == "true"


def rafael_phone() -> str:
    """Rafael's number from env only. Empty when unset or placeholder."""
    raw = (
        os.getenv("FAMILY_ALERT_PHONE")
        or os.getenv("RAFAEL_ALERT_PHONE")
        or ""
    ).strip()
    if not raw or raw.lower() in {"changeme", "todo", "your-number", "xxx"}:
        return ""
    return _digits(raw)


def studio_assist_url() -> str:
    base = (os.getenv("FAMILY_ALERT_STUDIO_URL") or DEFAULT_STUDIO_URL).strip().rstrip("/")
    if not base:
        base = DEFAULT_STUDIO_URL
    return f"{base}{ASSIST_PATH}"


def edition_who(edition: Optional[str] = None) -> tuple[str, str]:
    key = (edition or "").strip().lower()
    if key in WHO:
        return WHO[key]
    try:
        from app.edition import edition_name

        key = (edition_name() or "").strip().lower()
    except Exception:
        key = ""
    return WHO.get(key, ("Family", "Max"))


def suggested_type_labels(request_type: Optional[str]) -> tuple[str, str]:
    raw = (request_type or "").strip()
    try:
        from app.services.family_help import normalize_request_type

        kind = normalize_request_type(raw) or raw
    except Exception:
        kind = raw
    if kind not in TYPE_EN:
        return ("", "")
    return (TYPE_ES[kind], TYPE_EN[kind])


def _owner_numbers() -> list[str]:
    try:
        from app.services.whatsapp_cloud import owner_numbers

        return list(owner_numbers())
    except Exception:
        return []


def destination_allowed(number: str) -> bool:
    """True only for Rafael's env number, and never a brother/client owner number."""
    dest = _digits(number)
    expected = rafael_phone()
    if not dest or not expected or dest != expected:
        return False
    if dest in set(_owner_numbers()):
        return False
    return True


def build_alert_text(ticket: dict) -> str:
    edition = str(ticket.get("edition") or "")
    person, assistant = edition_who(edition)
    kind_es, kind_en = suggested_type_labels(ticket.get("request_type"))
    summary = " ".join(
        str(ticket.get("message") or ticket.get("transcript") or "").split()
    )[:180]
    if not summary:
        summary = "audio o archivo / audio or file"
    type_line = ""
    if kind_es and kind_en:
        type_line = f"Tipo sugerido / suggested type: {kind_es} ({kind_en}).\n"
    link = studio_assist_url()
    return (
        f"{person} ({assistant}) pidió ayuda / asked for help.\n"
        f"Resumen / summary: {summary}\n"
        f"{type_line}"
        f"Empire Assist: {link}"
    )


def whatsapp_ready() -> bool:
    try:
        from app.services.whatsapp_cloud import configured

        return bool(configured())
    except Exception:
        return False


def sms_ready() -> bool:
    sid = (os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("SMS_ACCOUNT_SID") or "").strip()
    token = (os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("SMS_AUTH_TOKEN") or "").strip()
    sender = (os.getenv("TWILIO_FROM_NUMBER") or os.getenv("SMS_FROM_NUMBER") or "").strip()
    return bool(sid and token and sender)


def send_whatsapp(to: str, text: str) -> dict[str, Any]:
    """WhatsApp Cloud API to Rafael only. No-op when not configured."""
    dest = _digits(to)
    if not destination_allowed(dest):
        return {"sent": False, "reason": "blocked_destination"}
    if not whatsapp_ready():
        return {"sent": False, "reason": "not_configured"}
    try:
        from app.services.whatsapp_cloud import send_alert_text

        return send_alert_text(dest, text)
    except Exception as exc:
        logger.warning("family alert WhatsApp failed: %s", type(exc).__name__)
        return {"sent": False, "reason": f"error:{type(exc).__name__}"}


def send_sms(to: str, text: str) -> dict[str, Any]:
    """Twilio-style SMS to Rafael only. No-op when creds are missing."""
    dest = _digits(to)
    if not destination_allowed(dest):
        return {"sent": False, "reason": "blocked_destination"}
    sid = (os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("SMS_ACCOUNT_SID") or "").strip()
    token = (os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("SMS_AUTH_TOKEN") or "").strip()
    sender = (os.getenv("TWILIO_FROM_NUMBER") or os.getenv("SMS_FROM_NUMBER") or "").strip()
    if not (sid and token and sender):
        return {"sent": False, "reason": "not_configured"}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    body = urlencode({
        "From": sender,
        "To": f"+{dest}" if not str(to).startswith("+") else to,
        "Body": (text or "")[:1600],
    }).encode("utf-8")
    import base64

    auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii")
    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read()
            return {"sent": 200 <= int(resp.status) < 300, "status": int(resp.status), "body": raw[:200]}
    except HTTPError as exc:
        logger.warning("family alert SMS HTTP %s", exc.code)
        return {"sent": False, "reason": f"http:{exc.code}"}
    except URLError:
        logger.warning("family alert SMS network error")
        return {"sent": False, "reason": "network"}
    except Exception as exc:
        logger.warning("family alert SMS failed: %s", type(exc).__name__)
        return {"sent": False, "reason": f"error:{type(exc).__name__}"}


def notify_rafael_alert(ticket: dict) -> dict[str, Any]:
    """Send one WhatsApp (preferred) or SMS to Rafael. Never raises."""
    result: dict[str, Any] = {
        "status": "off",
        "channel": None,
        "to": None,
    }
    if not alerts_enabled():
        return result
    phone = rafael_phone()
    if not phone:
        result["status"] = "no_phone"
        return result
    if not destination_allowed(phone):
        result["status"] = "blocked_destination"
        return result
    text = build_alert_text(ticket)
    result["to"] = f"***{phone[-4:]}" if len(phone) >= 4 else "****"
    if whatsapp_ready():
        sent = send_whatsapp(phone, text)
        if sent.get("sent"):
            result["status"] = "whatsapp"
            result["channel"] = "whatsapp"
            return result
        result["whatsapp"] = sent.get("reason") or "failed"
    if sms_ready():
        sent = send_sms(phone, text)
        if sent.get("sent"):
            result["status"] = "sms"
            result["channel"] = "sms"
            return result
        result["sms"] = sent.get("reason") or "failed"
        result["status"] = "failed"
        return result
    result["status"] = "not_configured"
    return result
