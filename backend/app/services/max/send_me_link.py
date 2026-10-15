"""send_me_link — Maxine owner-only link/document delivery.

Delivers a link or document ONLY to Camilo's WhatsApp and email, read from
EDITION_OWNER_WHATSAPP / EDITION_OWNER_EMAIL. Never Studio send_me_this_link.
Never business.json, FOUNDER_EMAIL, AMP_OWNER_EMAIL, or WHATSAPP_OWNER_NUMBERS.

Tests must mock every send — outbound I/O is isolated in _deliver_* helpers.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.send_me_link")

TOOL_NAME = "send_me_link"
STUDIO_TOOL_NAME = "send_me_this_link"
OWNER_FIRST_NAME = "Camilo"
OWNER_ALIASES = frozenset({
    "me", "myself", "owner", "camilo", "camilo giraldo",
    "founder", "mi correo", "mi email", "my email", "mi whatsapp", "my whatsapp",
})
SIBLING_NAMES = frozenset({
    "juan", "juan diego", "juan diego giraldo",
})
STUDIO_NAMES = frozenset({
    "rafael", "rafa", "rafa22", "rafa22giraldo",
})
MISSING_WHATSAPP_ES = (
    "Manito, todavía no tengo tu WhatsApp configurado. "
    "Pídele a Rafael que ponga EDITION_OWNER_WHATSAPP en esta instancia."
)
MISSING_EMAIL_ES = (
    "Manito, todavía no tengo tu correo configurado. "
    "Pídele a Rafael que ponga EDITION_OWNER_EMAIL en esta instancia."
)
NOT_OWNER_ES = (
    "Manito, solo te puedo mandar a TU WhatsApp y TU correo de esta instancia. "
    "No mando a clientes, al Studio ni al otro hermano."
)
WHATSAPP_NOT_SETUP_ES = (
    "Manito, WhatsApp no está configurado en esta instancia. "
    "Puedo mandártelo por correo si quieres."
)
SEND_VIAS = ("whatsapp", "email")
_EMAIL_IN_BRACKETS = re.compile(r"<([^<>]+@[^<>]+)>")
_BARE_EMAIL = re.compile(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
_URL = re.compile(r"^https?://", re.I)
_EMAIL_VIA = re.compile(r"(?i)\b(?:e-?mails?|correo|mail)\b")
_ASKED_TO_SEND = re.compile(
    r"(?i)(?:"
    r"\b(?:send|sent|resend|forward|e-?mail|whats\s?app)\b|"
    r"\bcorreo\b|"
    r"\benviar(?:me|lo|la|te|nos)?\b|"
    r"\benv[ií]a(?:me|lo|la|nos|melo|mela)?\b|"
    r"\bmandar(?:me|lo|la|te|nos)?\b|"
    r"\bm[aá]nda(?:me|lo|la|nos|melo|mela)?\b|"
    r"\bp[aá]sa(?:me|lo|la|nos|melo|mela)?\b|"
    r"\bme\s+puedes\s+(?:mandar|enviar|pasar)\b|"
    r"\bme\s+lo\s+(?:env[ií]as|pasas|mandas)\b"
    r")"
)


class WhatsAppNotConfigured(RuntimeError):
    """WhatsApp Cloud keys are missing. Caller should offer email instead."""


def is_family_send_me_enabled() -> bool:
    try:
        from app.edition import is_family_edition
        return bool(is_family_edition())
    except Exception:
        return False


def normalize_email(addr: str | None) -> str:
    return (addr or "").strip().lower()


def extract_email(addr: str | None) -> str:
    raw = (addr or "").strip()
    m = _EMAIL_IN_BRACKETS.search(raw)
    if m:
        return normalize_email(m.group(1))
    m = _BARE_EMAIL.search(raw)
    if m:
        return normalize_email(m.group(1))
    return normalize_email(raw)


def digits_only(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _phone_variants(number: str) -> set[str]:
    n = digits_only(number)
    out = {n} if n else set()
    if n.startswith("57") and len(n) >= 12:
        out.add(n[2:])
    elif n.startswith("1") and len(n) == 11:
        out.add(n[1:])
    elif len(n) == 10:
        out.add("1" + n)
        out.add("57" + n)
    return out


def _split_csv(raw: str | None) -> list[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def sibling_deny_emails() -> set[str]:
    """Other brother's emails from EDITION_DENY_EMAIL. Never a send target."""
    out: set[str] = set()
    for part in _split_csv(os.getenv("EDITION_DENY_EMAIL") or ""):
        email = extract_email(part)
        if email:
            out.add(email)
    return out


def sibling_deny_phones() -> set[str]:
    """Other brother's WhatsApp from EDITION_DENY_WHATSAPP. Never a send target."""
    out: set[str] = set()
    for part in _split_csv(os.getenv("EDITION_DENY_WHATSAPP") or ""):
        out |= _phone_variants(part)
    return out


def runtime_denied_emails() -> set[str]:
    """EDITION_DENY_EMAIL plus FOUNDER_EMAIL / AMP_OWNER_EMAIL from env.

    Family editions do not load business.json, so denial cannot depend on it.
    """
    out = sibling_deny_emails()
    for key in ("FOUNDER_EMAIL", "AMP_OWNER_EMAIL"):
        for part in _split_csv(os.getenv(key) or ""):
            email = extract_email(part)
            if email:
                out.add(email)
    return out


def runtime_denied_phones() -> set[str]:
    """EDITION_DENY_WHATSAPP only. Family editions do not load business.json."""
    return sibling_deny_phones()


def owner_email_env_values() -> list[str]:
    """Raw EDITION_OWNER_EMAIL entries, including any that later get denied."""
    out: list[str] = []
    for part in _split_csv(os.getenv("EDITION_OWNER_EMAIL") or ""):
        email = extract_email(part)
        if email and email not in out:
            out.append(email)
    return out


def owner_email_env_is_denied() -> bool:
    """True when EDITION_OWNER_EMAIL is set but every value is denied."""
    return bool(owner_email_env_values()) and not owner_emails()


def owner_whatsapp_env_is_denied() -> bool:
    """True when EDITION_OWNER_WHATSAPP is set but equals a denied number."""
    raw = digits_only((os.getenv("EDITION_OWNER_WHATSAPP") or "").strip())
    return bool(raw) and not owner_whatsapp()


def owner_env_denied_reason(via: str | None = None) -> str | None:
    """NOT_OWNER_ES when EDITION_OWNER_* equals FOUNDER/AMP_OWNER/EDITION_DENY_*."""
    check_email = via in (None, "email")
    check_wa = via in (None, "whatsapp")
    if check_email and owner_email_env_is_denied():
        return NOT_OWNER_ES
    if check_wa and owner_whatsapp_env_is_denied():
        return NOT_OWNER_ES
    return None


def denylist_emails() -> set[str]:
    return runtime_denied_emails()


def denylist_phones() -> set[str]:
    return runtime_denied_phones()


def is_denied_email(addr: str | None) -> bool:
    email = extract_email(addr)
    return bool(email) and email in denylist_emails()


def is_denied_phone(number: str | None) -> bool:
    variants = _phone_variants(number or "")
    denied = denylist_phones()
    return bool(variants & denied)


def is_sibling_recipient(to: str | None) -> bool:
    raw = (to or "").strip().lower()
    if not raw:
        return False
    if raw in SIBLING_NAMES or raw in STUDIO_NAMES:
        return True
    if re.search(r"\bjuan\b", raw):
        return True
    if re.search(r"\brafael\b|\brafa22\b", raw):
        return True
    email = extract_email(raw)
    if email and email in sibling_deny_emails():
        return True
    if is_denied_phone(raw):
        return True
    return False


def owner_emails() -> list[str]:
    """Camilo's emails for THIS Maxine instance. Comma-separated EDITION_OWNER_EMAIL.

    Never FOUNDER_EMAIL, AMP_OWNER_EMAIL, or denylisted values.
    """
    out: list[str] = []
    for part in _split_csv(os.getenv("EDITION_OWNER_EMAIL") or ""):
        email = extract_email(part)
        if not email or is_denied_email(email) or email in out:
            continue
        out.append(email)
    return out


def owner_email() -> str:
    """Primary owner email (first in EDITION_OWNER_EMAIL)."""
    emails = owner_emails()
    return emails[0] if emails else ""


def owner_whatsapp() -> str:
    """Camilo's WhatsApp from EDITION_OWNER_WHATSAPP only. No WHATSAPP_OWNER_NUMBERS."""
    raw = (os.getenv("EDITION_OWNER_WHATSAPP") or "").strip()
    number = digits_only(raw)
    if number and not is_denied_phone(number):
        return number
    return ""


def _is_owner_alias(raw: str) -> bool:
    return (raw or "").strip().lower() in OWNER_ALIASES or not (raw or "").strip()


def infer_via(user_text: str | None = None, explicit: str | None = None) -> str:
    """correo/email/mail in the owner's text → email; otherwise WhatsApp."""
    blob = user_text or ""
    if _EMAIL_VIA.search(blob):
        return "email"
    via = (explicit or "").strip().lower()
    if via in ("mail", "gmail", "email", "correo"):
        return "email"
    if via in ("wa", "whatsapp", "whats app", "chat"):
        return "whatsapp"
    return "whatsapp"


def authorize_recipient(via: str, to: str | None) -> dict[str, Any]:
    """Allowlist: only this edition owner's WhatsApp / email."""
    via = infer_via(None, via)
    raw = (to or "").strip()
    email = extract_email(raw)

    if is_sibling_recipient(raw) or is_denied_email(raw) or (digits_only(raw) and is_denied_phone(raw)):
        return {"authorized": False, "via": via, "to": raw, "error": NOT_OWNER_ES}

    denied_cfg = owner_env_denied_reason(via)
    if denied_cfg:
        logger.error(
            "EDITION_OWNER_* equals FOUNDER_EMAIL, AMP_OWNER_EMAIL, or EDITION_DENY_*; refusing send"
        )
        return {"authorized": False, "via": via, "to": email or raw, "error": denied_cfg}

    if via == "email":
        allowed = owner_emails()
        if not allowed:
            return {"authorized": False, "via": "email", "to": email or raw, "error": MISSING_EMAIL_ES}
        if _is_owner_alias(raw):
            return {"authorized": True, "via": "email", "to": allowed[0], "error": None}
        asked = extract_email(raw)
        if asked and asked in allowed:
            return {"authorized": True, "via": "email", "to": asked, "error": None}
        return {"authorized": False, "via": "email", "to": email or raw, "error": NOT_OWNER_ES}

    if via == "whatsapp":
        configured_wa = owner_whatsapp()
        if owner_whatsapp_env_is_denied():
            return {"authorized": False, "via": "whatsapp", "to": digits_only(raw) or raw, "error": NOT_OWNER_ES}
        if not configured_wa:
            return {"authorized": False, "via": "whatsapp", "to": digits_only(raw) or raw, "error": MISSING_WHATSAPP_ES}
        if _is_owner_alias(raw):
            return {"authorized": True, "via": "whatsapp", "to": configured_wa, "error": None}
        asked = digits_only(raw)
        if asked and (_phone_variants(asked) & _phone_variants(configured_wa)):
            return {"authorized": True, "via": "whatsapp", "to": configured_wa, "error": None}
        return {"authorized": False, "via": "whatsapp", "to": asked or raw, "error": NOT_OWNER_ES}

    return {
        "authorized": False,
        "via": via,
        "to": raw,
        "error": f"via must be one of {', '.join(SEND_VIAS)}",
    }


def asked_to_send(message: Optional[str]) -> bool:
    """True only from the owner's own words. Ignore model caption/subject."""
    t = (message or "").strip()
    if not t:
        return False
    return bool(_ASKED_TO_SEND.search(t))


def whatsapp_cloud_ready() -> bool:
    try:
        from app.services.whatsapp_cloud import configured
        return bool(configured())
    except Exception:
        return False


def _refuse_live_send(channel: str) -> None:
    """Tests must mock _deliver_*. Never hit WhatsApp or SMTP from pytest."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        raise RuntimeError(
            f"{TOOL_NAME} {channel} send blocked under pytest — mock _deliver_{channel}"
        )


def _under_data_dir(path: str) -> Optional[str]:
    raw = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    if not raw or not path:
        return None
    try:
        root = Path(raw).expanduser().resolve()
        resolved = Path(path).expanduser().resolve()
        resolved.relative_to(root)
    except Exception:
        return None
    if not resolved.is_file():
        return None
    return str(resolved)


def resolve_payload(params: dict) -> dict[str, Any]:
    url = str(params.get("url") or params.get("link") or "").strip()
    query = str(params.get("query") or params.get("what") or params.get("ref") or "").strip()
    path = str(params.get("path") or params.get("file") or params.get("file_id") or "").strip()
    if not url and _URL.match(query):
        url = query
    safe_path = _under_data_dir(path) if path else None
    return {"url": url, "path": safe_path, "query": query}


def _assert_email_still_allowed(to: str) -> None:
    email = extract_email(to)
    if not email or email not in owner_emails() or is_denied_email(email):
        raise PermissionError(NOT_OWNER_ES)


def _assert_whatsapp_still_allowed(to: str) -> None:
    configured_wa = owner_whatsapp()
    asked = digits_only(to)
    if not configured_wa or not asked or is_denied_phone(asked):
        raise PermissionError(NOT_OWNER_ES)
    if not (_phone_variants(asked) & _phone_variants(configured_wa)):
        raise PermissionError(NOT_OWNER_ES)


def _deliver_email(payload: str, *, to: str, subject: str, body: str) -> dict[str, Any]:
    """Outbound email via EmailService.send with no cc. Never send_email (that CCs Rafael)."""
    _assert_email_still_allowed(to)
    _refuse_live_send("email")
    from app.services.max.email_service import EmailService
    svc = EmailService()
    sent = svc.send(
        to=to,
        subject=subject,
        body_text=body or payload,
        cc=None,
    )
    if not sent:
        raise RuntimeError("Email provider did not verify send acceptance")
    return {"message_id": svc.last_message_id, "cc": None}


def _deliver_whatsapp(payload: str, *, to: str, caption: str) -> dict[str, Any]:
    """Outbound WhatsApp via whatsapp_cloud Graph send."""
    _assert_whatsapp_still_allowed(to)
    from app.services import whatsapp_cloud as wa
    if not wa.configured():
        raise WhatsAppNotConfigured(WHATSAPP_NOT_SETUP_ES)
    _refuse_live_send("whatsapp")
    number = digits_only(to)
    text = "\n".join(part for part in (caption, payload) if part).strip()[:4000]
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "text",
        "text": {"body": text},
    }
    url = f"{wa.GRAPH}/{wa._phone_id()}/messages"
    result = wa._graph_json("POST", url, body, wa._token())
    msg_id = ((result.get("messages") or [{}])[0] or {}).get("id")
    return {"media_id": msg_id, "id": msg_id}


def send_me_link(params: dict) -> dict[str, Any]:
    """Core send. Returns {success, result?, error?}. Tests mock _deliver_*."""
    if not is_family_send_me_enabled():
        return {
            "success": False,
            "error": "send_me_link only runs on this family instance.",
        }
    user_text = str(params.get("user_text") or params.get("asked") or "").strip()
    via = infer_via(user_text, params.get("via") or params.get("channel"))
    gate = authorize_recipient(via, params.get("to"))
    if not gate["authorized"]:
        return {"success": False, "error": gate["error"]}

    looked = resolve_payload(params)
    payload = looked["url"] or looked["path"] or looked["query"]
    if not payload:
        return {
            "success": False,
            "error": "No encontré un enlace o archivo para mandarte.",
        }

    name = Path(looked["path"]).name if looked["path"] else (looked["url"] or payload)
    if via == "email":
        try:
            _assert_email_still_allowed(gate["to"])
            sent = _deliver_email(
                payload,
                to=gate["to"],
                subject=str(params.get("subject") or f"Para ti: {name}"),
                body=str(params.get("body") or payload),
            )
        except PermissionError:
            return {"success": False, "error": NOT_OWNER_ES}
        except Exception as exc:
            return {"success": False, "error": f"Email not sent: {exc}"}
        return {"success": True, "result": {
            "via": "email",
            "sent_to": gate["to"],
            "name": name,
            "payload": payload,
            "cc": None,
            "message_id": (sent or {}).get("message_id"),
            "message": f"Te mandé {name} a tu correo.",
        }}

    if not whatsapp_cloud_ready():
        return {"success": False, "error": WHATSAPP_NOT_SETUP_ES}
    try:
        _assert_whatsapp_still_allowed(gate["to"])
        sent = _deliver_whatsapp(
            payload,
            to=gate["to"],
            caption=str(params.get("caption") or f"{name} — para ti, manito"),
        )
    except WhatsAppNotConfigured:
        return {"success": False, "error": WHATSAPP_NOT_SETUP_ES}
    except PermissionError:
        return {"success": False, "error": NOT_OWNER_ES}
    except Exception as exc:
        return {"success": False, "error": f"WhatsApp not sent: {exc}"}
    return {"success": True, "result": {
        "via": "whatsapp",
        "sent_to": "owner_whatsapp",
        "name": name,
        "payload": payload,
        "media_id": (sent or {}).get("media_id"),
        "message": f"Te mandé {name} a tu WhatsApp.",
    }}


def register_tools(tool, ToolResult) -> None:
    @tool(TOOL_NAME)
    def _send_me_link(params: dict, desk: Optional[str] = None):
        data = send_me_link(params)
        return ToolResult(
            tool=TOOL_NAME,
            success=bool(data.get("success")),
            result=data.get("result"),
            error=data.get("error"),
        )


def send_me_link_doc() -> str:
    if not is_family_send_me_enabled():
        return ""
    return f"""
### Mandarme este enlace (solo {OWNER_FIRST_NAME})
- **{TOOL_NAME}** — Manda un enlace o documento SOLO al WhatsApp y correo del dueño
  de ESTA instancia (EDITION_OWNER_WHATSAPP / EDITION_OWNER_EMAIL). Nunca clientes,
  nunca el Studio, nunca el otro hermano. Nunca uses send_me_this_link.
  Si el dueño dice correo/email/mail, via=email; si no, WhatsApp.
  `{{"tool": "{TOOL_NAME}", "query": "https://ejemplo.com/agenda", "via": "whatsapp"}}`
  `{{"tool": "{TOOL_NAME}", "url": "https://ejemplo.com/doc", "via": "email"}}`
"""


class _SendMeDoc(str):
    def __new__(cls):
        return str.__new__(cls, send_me_link_doc())

    def __str__(self) -> str:
        return send_me_link_doc()

    def __add__(self, other):
        return send_me_link_doc() + other

    def __radd__(self, other):
        return other + send_me_link_doc()


SEND_ME_LINK_DOC = _SendMeDoc()
